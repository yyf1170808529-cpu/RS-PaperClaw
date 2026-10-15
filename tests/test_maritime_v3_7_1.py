from datetime import date
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/rs-paper-pipeline/scripts'))
from services import maritime_reading as reading
from services import selected_translation as selected
from services.mobile_digest import build_mobile_digest


class OfflineTranslationTests(unittest.TestCase):
    def paper(self, id='2610.00001'):
        return {'paper_id':id, 'title':'Cross-modal object tracking',
                'abstract':'Cross-modal object tracking with AIS improves by 23.4%.',
                'assessment':{'score':20,'level':'high'}, 'recommendation':{'bucket':'general'},
                'arxiv_id':id,'arxiv_url':'https://arxiv.org/abs/'+id}

    def local(self, p):
        return {'status':'machine','english_hash':hashlib.sha256(p['abstract'].encode()).hexdigest(),
                'zh':'跨模态目标跟踪结合AIS，效果提升23.4%。'}

    def test_daily_and_library_reuse_local_translation_over_old_deepseek(self):
        p=self.paper();p['translation']=self.local(p)
        old={'status':'deepseek','zh':'历史DeepSeek译文'}
        p['selected_translation']=old.copy()
        self.assertEqual(selected.chosen_zh(p),selected.chosen_zh(p,daily=True))
        self.assertEqual(selected.chosen_zh(p)[1],'argos')
        self.assertEqual(reading.translate_one(p,lambda _:self.fail('Valid cache translated again')),p['translation'])
        self.assertEqual(p['selected_translation'],old)
        p['translation']={'status':'manual','zh':'人工修订摘要'}
        self.assertEqual(reading.translate_one(p,lambda _:self.fail('Manual overwritten')),p['translation'])
        self.assertEqual(selected.chosen_zh(p,daily=True),('人工修订摘要','manual'))

    def test_selected_five_use_local_worker_without_history_limit_or_api(self):
        ps=[self.paper(f'2610.{10000+i}') for i in range(5)]
        lib={'papers':{p['paper_id']:p for p in ps}}
        def budget(library,keys,limit,seconds,save):
            self.assertEqual(keys,[p['paper_id'] for p in ps])
            self.assertEqual(limit,5)
            for p in ps:p['translation']=self.local(p)
            save()
            return {'translated':5,'cached':0,'manual':0,'failed':0}
        with tempfile.TemporaryDirectory() as d,patch('services.mobile_digest.select_daily',return_value=([(p,0,{}) for p in ps],{})),patch('services.maritime_update.translate_budget',side_effect=budget),patch('clients.deepseek_client.complete') as api:
            result=selected.translate_selected(Path(d),lib,date(2026,10,15))
            self.assertEqual(result['translated'],5)
            self.assertEqual(result['api_calls'],0)
            self.assertTrue(all(p['source']=='argos' and not p['error'] for p in result['papers']))
            api.assert_not_called()

    def test_checks_reject_numbers_bad_terms_repetition_and_omission(self):
        p=self.paper();zh=self.local(p)['zh']
        self.assertIsNone(reading.translation_error(p['abstract'],zh))
        self.assertIn('numeric_mismatch',reading.translation_error(p['abstract'],zh.replace('23.4','24.3')))
        self.assertIn('terminology',reading.translation_error(p['abstract'],zh+'保险丝'))
        self.assertIsNone(reading.translation_error('We tested 5 benchmarks.', '我们在5个基准上进行了测试。'))
        self.assertIsNone(reading.translation_error('We tested five benchmarks.', '我们在5个基准上进行了测试。'))
        self.assertIn('numeric_mismatch',reading.translation_error('We tested five benchmarks.', '我们在6个基准上进行了测试。'))
        self.assertIsNone(reading.translation_error('RGB and RGB-T are used by ESMTrack.', 'RGB和RGB-T由ESMTrack使用。'))
        self.assertIn('protected_token_missing',reading.translation_error('RGB and RGB-T are used by ESMTrack.', 'RGB和RGB-T由EMETrack使用。'))
        english='This is a long description of an approach for associating objects in time. '*5
        sentence='这是一段足够长的中文完整句子，用来检查翻译输出是否出现了重复的长段落和重复描述'
        self.assertIn('repeated_sentence',reading.translation_error(english,sentence+'。'+sentence+'。'))
        self.assertIn('repeated_sentence',reading.translation_error(english,'方法可以'+ '不合理，'*20+'影响结果。'))
        self.assertEqual(reading.translate_one({'abstract':english},lambda _:'')['status'],'failed')

    def test_failure_is_explicit_in_daily_and_english_is_preserved(self):
        p=self.paper();p['translation']={'status':'failed','error_type':'model_missing','error':'Install the optional en→zh Argos model first'}
        choices=[(p,0,{'path':'transfer','reason':'方法借鉴','score':40})]
        with tempfile.TemporaryDirectory() as d,patch('services.mobile_digest.select_daily',return_value=(choices,{})):
            result=build_mobile_digest(Path(d),{'papers':{p['paper_id']:p}},date(2026,10,15))
            item=result['papers'][0]
            self.assertEqual(item['abstract'],p['abstract'])
            self.assertIn('英译中模型未安装',item['translation_error'])
            self.assertIn('英译中模型未安装',(Path(d)/'docs/maritime-daily.html').read_text(encoding='utf8'))


if __name__=='__main__':unittest.main()
