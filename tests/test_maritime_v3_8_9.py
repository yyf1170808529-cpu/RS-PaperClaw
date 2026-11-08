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
