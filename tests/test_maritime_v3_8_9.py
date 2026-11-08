import unittest,sys,tempfile,json
from pathlib import Path
from unittest.mock import patch
from datetime import date
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services import adaptive_discovery as a
from services.domain_exclusion import exclusion
class RecoveryTests(unittest.TestCase):
 def test_shortage_rounds(self):
  for initial,counts in [(5,[]),(4,[5]),(2,[5]),(2,[4,4]),(0,[0,0])]:
   with self.subTest(initial=initial),tempfile.TemporaryDirectory() as d:
    values=iter([initial,initial]+sum(([initial,n] for n in counts),[]));last=[initial]
    def count(*args):
     try:last[0]=next(values)
     except StopIteration:pass
     return last[0]
    args=SimpleNamespace(root=Path(d),translation_timeout=1,timeout=1,no_ai=True)
    with patch.object(a,'complete_count',side_effect=count),patch.object(a,'jobs_for',return_value=[]),patch('services.semantic_evaluation.daily_evaluate',return_value={}),patch('services.selected_translation.translate_selected',return_value={}):
     rows=a.recover(args,{'papers':{},'supplement_cursor':0},{},date(2026,11,8),lambda:None)
    self.assertEqual(len(rows),len(counts))
 def test_cursor_changes_between_runs_and_domain_gates(self):
  lib={'papers':{}};v={'journals':[]};c=a.settings();one=a.jobs_for(Path('.'),lib,v,0,c);two=a.jobs_for(Path('.'),lib,v,0,c);self.assertNotEqual(one,two)
  for title in ['Perception-Aware Communication Middleware for Distributed Visual Perception','Benchmarking 4D Radar for Ego-Trajectory Planning']:self.assertTrue(exclusion({'title':title}))
 def test_anonymous_openalex_has_no_cursor(self):
  from clients.scholarly_client import fetch_openalex
  with patch('clients.scholarly_client.openalex_key',return_value=None),patch('clients.scholarly_client.json_request',return_value={'results':[],'meta':{}}) as request:
   self.assertEqual(fetch_openalex('2026-01-01','2026-11-08','vision',None),([],True));self.assertNotIn('cursor',request.call_args.args[1])
 def test_exact_quantity_conversion_reuses_paid_response(self):
  from services.reading_translation import validate,enrich,key
  p={'paper_id':'2611.04034','title':'Sparse multimodal pretraining','abstract':'We collect $2.82M$ images from 16 datasets.'}
  v={'paper_id':p['paper_id'],'summary_zh':'本文研究多模态预训练。','migration_zh':'研究推断：可调整输入以融合传感器。','abstract_zh':'我们收集16个数据集的282万图像，用于多模态预训练。'}
  self.assertIn('$2.82M$',validate(v,p)['abstract_zh'])
  with self.assertRaises(ValueError):validate({**v,'abstract_zh':v['abstract_zh'].replace('282','281')},p)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'docs/maritime-data/reading-enrichment.json';path.parent.mkdir(parents=True);path.write_text(json.dumps({'records':{key(p):{'status':'audit_required','candidate':v,'cost_upper_cny':.01}}}),encoding='utf8')
   with patch('clients.deepseek_client.complete') as api:
    self.assertEqual(enrich(root,p)['status'],'success');api.assert_not_called()
 def test_source_count_is_separate_from_research_scope(self):
  p={'title':'Clinical cancer diagnosis','abstract':'Patient study','resource_type':'journal_article','quality':{'high_journal':True}}
  self.assertTrue(a.source_allowed(p));self.assertTrue(exclusion(p))
 def test_conference_prefix_is_not_ccfa_and_water_surface_is_maritime(self):
  from services.maritime_v2 import venue_quality,assets
  from services.abstract_quality import application
  venues,policy=assets();p={'venue':'2026 11th International Conference on Machine Learning Technologies (ICMLT)','venue_type':'conference','publication_status':'published','doi':'10.1234/test','publication_evidence':{'source':'Crossref'}}
  self.assertFalse(venue_quality(p,venues,policy)['ccf_a']);p['venue']='2026 International Conference on Machine Learning (ICML)';self.assertTrue(venue_quality(p,venues,policy)['ccf_a'])
  self.assertEqual(application({'title':'Radar camera fusion in Water-Surface Environments'},policy),'water')
 def test_malformed_paid_batch_does_not_stop_different_candidates(self):
  import subprocess
  from services.semantic_evaluation import daily_evaluate,settings
  ps=[{'paper_id':f'2611.{10000+i}','title':f'Vehicle detection {i}','abstract':'We propose feature alignment for vehicle detection.'} for i in range(8)]
  def result(p):
   return {'paper_id':p['paper_id'],'task_type':'detection','direct_relevance':3,'transferability':3,'confidence':.8,'decision':'候选','reason_zh':'具备感知方法证据','limitations':[], 'method_evidence':[{'quote_en':p['abstract'],'interpretation_zh':'特征对齐','inference':False}],'transfer_path':None,'primary_domain':'traffic_perception','primary_problem':'detection','target_task':'detection','core_contribution':'feature alignment','application_context':'traffic','security_centric':False,'communication_centric':False}
  def response(text):return ({'id':'test-response','created':1794110400,'model':'deepseek-flash','usage':{'total_tokens':100},'choices':[{'finish_reason':'stop','message':{'content':text}}]},.001)
  def git(args,**kw):
   out='https://github.com/yyf1170808529-cpu/RS-PaperClaw' if 'get-url' in args else '{"records":{}}' if 'show' in args else 'same'
   return subprocess.CompletedProcess(args,0,out,'')
  audit={'qualified_count':0,'ai_reviewed':0,'shortfall':5,'ai_states':{}}
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'skills/rs-paper-pipeline/scripts/config/maritime/publication.json';path.parent.mkdir(parents=True);path.write_text(json.dumps({'repository':'yyf1170808529-cpu/RS-PaperClaw','branch':'main'}))
   with patch('services.mobile_digest.candidate_pool',return_value=[(p,0) for p in ps]),patch('services.mobile_digest.select_daily',return_value=([],audit)),patch('services.mobile_digest.refresh_reserve',return_value={'available_count':0}),patch('clients.deepseek_client.api_key',return_value='unused'),patch('clients.deepseek_client.complete',side_effect=[response('invalid JSON'),response(json.dumps({'evaluations':[result(p) for p in ps[4:]]}))]) as api,patch('services.maritime_sync.api',return_value={'workflow_runs':[]}),patch('subprocess.run',side_effect=git):
    value=daily_evaluate(root,{'papers':{p['paper_id']:p for p in ps}},[],date(2026,11,8),limit=8)
   self.assertEqual(api.call_count,2);self.assertEqual(value['failed'],4);self.assertEqual(value['processed'],4);self.assertAlmostEqual(value['cost_upper_cny'],.002)
   ids=[{p['paper_id'] for p in json.loads(call.args[1]['messages'][1]['content'])['papers']} for call in api.call_args_list];self.assertFalse(ids[0]&ids[1])
