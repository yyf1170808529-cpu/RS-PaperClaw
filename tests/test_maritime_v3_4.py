import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services import semantic_evaluation as semantic, maritime as m
from clients import deepseek_client as ds

class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(semantic.CONFIG.read_text(encoding='utf8'))
        self.paper={'paper_id':'2601.00001','title':'Radar AIS association','abstract':'We align radar observations with AIS trajectories using temporal matching.',
                    'quality':{'high_journal':False},'publication_status':'unknown','assessment':{'score':25},'recommendation':{'bucket':'candidate'}}
        self.result={'paper_id':'2601.00001','task_type':'Radar AIS匹配','direct_relevance':5,'transferability':4,
            'method_evidence':[{'quote_en':'align radar observations with AIS trajectories','interpretation_zh':'摘要明确给出关联任务','inference':False}],
            'transfer_path':None,'limitations':['摘要无法确认具体实验'],'decision':'重点推荐','reason_zh':'关注Radar AIS关联','confidence':0.8}
    def test_schema_and_exact_evidence_reject_hallucination_or_quality_fields(self):
        self.assertEqual(semantic.validate(self.result,self.paper),self.result)
        for change in [{'direct_relevance':True},{'reason_zh':'x'*101},{'quality':{'high_journal':True}},{'confidence':2},
                       {'method_evidence':[{'quote_en':'invented attention module','interpretation_zh':'fake','inference':False}]}]:
            with self.assertRaises(ValueError):semantic.validate({**self.result,**change},self.paper)
    def test_cache_changes_for_abstract_preferences_model_or_verified_quality(self):
        first=semantic.fingerprint(self.paper,self.config)
        for p,c in [({**self.paper,'abstract':'changed'},self.config),(self.paper,{**self.config,'model':'deepseek-v4-pro'}),
                    (self.paper,{**self.config,'preferences':{}}),({**self.paper,'quality':{'high_journal':True}},self.config)]:
            self.assertNotEqual(first,semantic.fingerprint(p,c))
    def test_budget_denies_request_and_timeout_retains_reservation(self):
        payload={'max_tokens':3000,'messages':[{'content':'test'}]}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(ds,'request') as request:
                with self.assertRaises(RuntimeError):ds.complete(root,payload,{**self.config,'daily_budget_cny':0.000001})
                request.assert_not_called()
            with patch.object(ds,'request',side_effect=RuntimeError('timeout')):
                with self.assertRaises(RuntimeError):ds.complete(root,payload,self.config)
            ledger=m.read_json(root/'papers/maritime/private/deepseek/usage.json',{})
            today=next(iter(ledger['days'].values()))
            self.assertGreater(today['reserved_cny'],0)
            self.assertEqual(today['requests'][0]['status'],'uncertain')
    def test_usage_meter_accounts_cache_hits_and_misses(self):
        response={'id':'unit-test','usage':{'prompt_tokens':100,'completion_tokens':50,'prompt_cache_hit_tokens':80,'prompt_cache_miss_tokens':20}}
        with tempfile.TemporaryDirectory() as directory,patch.object(ds,'request',return_value=response):
            _,cost=ds.complete(Path(directory),{'max_tokens':300,'messages':[{'content':'test'}]},self.config)
            self.assertAlmostEqual(cost,(80*.04+20*2+50*8)/1e6)
    def test_daily_is_limited_and_stage_two_disabled(self):
        self.assertTrue(self.config['enabled'])
        self.assertEqual(self.config['daily_limit'],20)
        self.assertFalse(self.config['stage_two']['enabled'])

    def test_human_precision_requires_labels_not_ai_ground_truth(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);export=root/'evaluations/maritime-v3-4';export.mkdir(parents=True)
            m.write_json(export/'results.json',{'rule_top10':[f'a{i}' for i in range(10)],'ai_top10':[f'b{i}' for i in range(10)]})
            path=export/'human-labels.csv';path.write_text('paper_id,human_relevant_0_or_1\n'+''.join(f'a{i},1\nb{i},\n' for i in range(10)),encoding='utf-8-sig')
            result=semantic.label_metrics(root)
            self.assertEqual(result['rule_precision_at_5'],1)
            self.assertIsNone(result['ai_precision_at_5'])

if __name__=='__main__':unittest.main()
