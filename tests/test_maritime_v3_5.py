import copy
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services import semantic_evaluation as ai, maritime as m
from services.mobile_digest import build_mobile_digest
from test_maritime_v2 import paper

class DailyTests(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads(ai.CONFIG.read_text(encoding='utf8'))
        self.p=paper(title='Maritime infrared ship detection')
        self.p.update(paper_id=self.p['arxiv_id'],abstract='We propose a ship detection model with regional segmentation for maritime infrared images.',
                      recommendation={'bucket':'water'},quality={'high_journal':True},resource_type='journal_article',published='2026-10-14',publication_date='2026-10-14')
        self.e={'paper_id':self.p['paper_id'],'task_type':'Ship detection','direct_relevance':0,'transferability':2,
                'confidence':.9,'decision':'不推荐','reason_zh':'没有AIS关联','limitations':[],
                'method_evidence':[{'quote_en':'ship detection model with regional segmentation','interpretation_zh':'船舶检测','inference':False}]}
    def attach(self,p,e):
        p['semantic']={'fingerprint':ai.fingerprint(p,self.cfg),'evaluation':copy.deepcopy(e),'paper_id':p['paper_id']}
    def test_ship_vision_is_not_vetoed_by_missing_ais_or_decision_label(self):
        self.attach(self.p,self.e)
        self.assertFalse(ai.ranking_info(self.p)['demoted'])
        self.assertGreaterEqual(ai.ranking_info(self.p)['score'],60)
        self.assertIsNone(ai.ranking_info(self.p)['reason'])
    def test_high_confidence_medical_and_unrelated_language_are_demoted(self):
        for title,abstract in [('Blood vessel segmentation','We segment vascular tissue for a clinical study.'),('Linguistic landscape of shipping vessels','We study linguistic signs for monolingual schools.')]:
            p={**self.p,'title':title,'abstract':abstract}
            e={**self.e,'method_evidence':[],'reason_zh':'无关研究'}
            self.attach(p,e)
            self.assertTrue(ai.ranking_info(p)['demoted'])
    def test_uncertain_or_changed_abstract_falls_back(self):
        self.attach(self.p,{**self.e,'confidence':.3})
        self.assertIsNone(ai.ranking_info(self.p)['score'])
        self.attach(self.p,self.e);self.p['abstract']='Changed'
        self.assertIsNone(ai.ranking_info(self.p)['score'])
    def test_disabled_and_missing_key_do_not_call_api_or_change_quality(self):
        lib={'papers':{self.p['paper_id']:self.p},'days':{}}
        old=copy.deepcopy(self.p['quality'])
        with tempfile.TemporaryDirectory() as directory,patch('clients.deepseek_client.api_key',side_effect=RuntimeError('missing key')),patch('clients.deepseek_client.complete') as call:
            root=Path(directory)
            result=ai.daily_evaluate(root,lib,[],date(2026,10,14))
            self.assertEqual(result['status'],'fallback');call.assert_not_called()
            self.assertEqual(self.p['quality'],old)
            self.assertEqual(len(build_mobile_digest(root,lib,date(2026,10,14))['papers']),1)
    def test_shared_cache_reused_without_key_or_new_paid_requests(self):
        self.attach(self.p,self.e)
        lib={'papers':{self.p['paper_id']:self.p},'days':{}}
        with tempfile.TemporaryDirectory() as directory,patch('clients.deepseek_client.complete') as call:
            root=Path(directory)
            m.write_json(root/'docs/maritime-data/semantic-cache.json',{'schema_version':1,'records':{ai.fingerprint(self.p,self.cfg):self.p['semantic']}})
            self.p.pop('semantic')
            result=ai.daily_evaluate(root,lib,[],date(2026,10,14))
            self.assertEqual(result['cached'],1);self.assertEqual(result['processed'],0);call.assert_not_called()
    def test_ai_cannot_put_unverified_journal_into_daily(self):
        self.attach(self.p,{**self.e,'decision':'重点推荐','direct_relevance':5})
        self.p['recommendation']['bucket']='candidate';self.p['quality']['high_journal']=False
        self.attach(self.p,{**self.e,'decision':'重点推荐','direct_relevance':5})
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(build_mobile_digest(Path(directory),{'papers':{self.p['paper_id']:self.p},'days':{}},date(2026,10,14))['papers'],[])
    def test_soft_quotas_do_not_borrow_from_ineligible_papers(self):
        ps={}
        for i,bucket in enumerate(['water']*4+['land']*4+['general']*4):
            p=copy.deepcopy(self.p);p['paper_id']=p['arxiv_id']=f'2610.{10000+i}';p['recommendation']['bucket']=bucket
            ps[p['paper_id']]=p
        with tempfile.TemporaryDirectory() as directory:
            payload=build_mobile_digest(Path(directory),{'papers':ps,'days':{}},date(2026,10,14))
        counts={b:sum(ps[p['paper_id']]['recommendation']['bucket']==b for p in payload['papers']) for b in ('water','land','general')}
        self.assertEqual(counts,{'water':3,'land':1,'general':1})

    def fake_git(self,command,**kwargs):
        from types import SimpleNamespace
        if 'get-url' in command:out='https://github.com/yyf1170808529-cpu/RS-PaperClaw.git'
        elif 'rev-parse' in command:out='same-head'
        else:out=''
        return SimpleNamespace(returncode=1 if 'show' in command else 0,stdout=out,stderr='')
    def prepare_repository(self,root):
        m.write_json(root/'skills/rs-paper-pipeline/scripts/config/maritime/publication.json',{'repository':'yyf1170808529-cpu/RS-PaperClaw','branch':'main'})
    def test_timeout_still_produces_daily_and_keeps_quality(self):
        lib={'papers':{self.p['paper_id']:self.p},'days':{}}
        old=copy.deepcopy(self.p['quality'])
        with tempfile.TemporaryDirectory() as directory,patch('subprocess.run',side_effect=self.fake_git),patch('clients.deepseek_client.api_key',return_value='unit-test'),patch('services.maritime_sync.api',return_value={'workflow_runs':[]}),patch('clients.deepseek_client.complete',side_effect=RuntimeError('timeout')):
            root=Path(directory);self.prepare_repository(root)
            outcome=ai.daily_evaluate(root,lib,[],date(2026,10,14))
            self.assertEqual(outcome['status'],'fallback')
            self.assertEqual(len(build_mobile_digest(root,lib,date(2026,10,14))['papers']),1)
        self.assertEqual(old,self.p['quality'])
    def test_remote_update_or_active_cloud_prevents_duplicate_paid_work(self):
        lib={'papers':{self.p['paper_id']:self.p},'days':{}}
        with tempfile.TemporaryDirectory() as directory,patch('subprocess.run',side_effect=self.fake_git),patch('clients.deepseek_client.api_key',return_value='unit-test'),patch('services.maritime_sync.api',return_value={'workflow_runs':[{'id':999,'path':'.github/workflows/maritime-no-api.yml'}]}),patch('clients.deepseek_client.complete') as call:
            root=Path(directory);self.prepare_repository(root)
            outcome=ai.daily_evaluate(root,lib,[],date(2026,10,14))
            self.assertEqual(outcome['status'],'fallback');call.assert_not_called()

if __name__=='__main__':unittest.main()
