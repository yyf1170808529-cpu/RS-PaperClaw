import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/rs-paper-pipeline/scripts'))
from services import semantic_evaluation as ai
from services.mobile_digest import build_mobile_digest, candidate_pool, select_daily
from services.selected_translation import chosen_zh, translate_selected, valid_translation
from test_maritime_v2 import paper


class DailyStrictTests(unittest.TestCase):
    def setUp(self):
        self.config=ai.settings()

    def make(self, id, published, direct=5):
        p=paper(title='Radar AIS association for ship tracking')
        p.update(paper_id=id, arxiv_id=id, published=published, publication_date=published,
                 abstract='We propose radar AIS association for ship tracking with cross-modal matching and target detection.',
                 resource_type='journal_article', recommendation={'bucket':'water'},
                 quality={'high_journal':True}, assessment={'level':'high','score':30})
        if direct is not None:
            evaluation={'paper_id':id,'task_type':'Radar AIS association','direct_relevance':direct,
                        'transferability':2,'method_evidence':[{'quote_en':'radar AIS association for ship tracking',
                        'interpretation_zh':'雷达与AIS关联','inference':False}], 'transfer_path':None,
                        'limitations':[],'decision':'重点推荐','reason_zh':'雷达与AIS目标关联','confidence':.9}
            p['semantic']={'paper_id':id,'fingerprint':ai.fingerprint(p,self.config),'evaluation':evaluation}
        return p

    def test_four_stages_and_unreviewed_never_publish(self):
        ps=[self.make('2610.10001','2026-10-15'),self.make('2610.10002','2026-10-10'),
            self.make('2610.10003','2026-09-20'),self.make('2610.10004','2025-01-01'),
            self.make('2610.10005','2026-10-15',None)]
        lib={'papers':{p['paper_id']:p for p in ps},'days':{}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rows=candidate_pool(root,lib,date(2026,10,15),['2610.10001','2610.10005'])
            self.assertEqual({s for _,s in rows},{0,1,2,3})
            result=build_mobile_digest(root,lib,date(2026,10,15))
            self.assertEqual(len(result['papers']),4)
            self.assertNotIn('2610.10005',[p['paper_id'] for p in result['papers']])
            self.assertEqual(result['selection_audit']['shortfall'],1)
            self.assertTrue(all(ai.ranking_info(lib['papers'][p['paper_id']])['state']=='evaluated' for p in result['papers']))
            self.assertIn('maritime.html?paper=2610.10001',result['papers'][0]['reading_url'])
            old=root/'docs/maritime-data/mobile/2026-10-14.json'
            old.write_text(json.dumps({'papers':[{'paper_id':'2610.10002'}]}),encoding='utf8')
            self.assertNotIn('2610.10002',[p['paper_id'] for p,_ in candidate_pool(root,lib,date(2026,10,15))])

    def test_translation_numbers_manual_priority_and_local_cache(self):
        p=self.make('2610.10001','2026-10-15')
        p['abstract']='We propose radar AIS association for ship tracking with 23.4% gain.'
        p['semantic']['fingerprint']=ai.fingerprint(p,self.config)
        lib={'papers':{p['paper_id']:p},'days':{}}
        self.assertFalse(valid_translation(p['abstract'],'我们提出雷达与AIS关联，提升24.4%。'))
        self.assertTrue(valid_translation(p['abstract'],'我们提出雷达与AIS关联，用于船舶跟踪，提升23.4%。'))
        p['translation']={'status':'manual','zh':'人工校订的摘要'}
        self.assertEqual(chosen_zh(p),('人工校订的摘要','manual'))
        p['translation']={'status':'machine','english_hash':hashlib.sha256(p['abstract'].encode()).hexdigest(),
                          'zh':'我们提出雷达与AIS关联，用于船舶跟踪，提升23.4%。'}
        self.assertEqual(chosen_zh(p)[1],'argos')
        self.assertEqual(chosen_zh(p,daily=True)[1],'argos')
        with tempfile.TemporaryDirectory() as d,patch('clients.deepseek_client.complete') as call:
            summary=translate_selected(Path(d),lib,date(2026,10,15),self.config)
            self.assertEqual(summary['cached'],1)
            self.assertEqual(summary['api_calls'],0)
            call.assert_not_called()

    def test_maritime_preprint_cannot_bypass_water_gate_as_land(self):
        p=self.make('2610.10009','2026-10-15')
        p.update(resource_type='preprint',application_bucket='water',quality={'high_journal':False},
                 recommendation={'bucket':'land','application':'maritime'})
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(candidate_pool(Path(d),{'papers':{p['paper_id']:p}},date(2026,10,15)),[])


if __name__=='__main__':unittest.main()
