import unittest,sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services.relevance_scope import infrastructure,traffic_task,arxiv_preprint,generic_method
from services.semantic_evaluation import ranking_info
from services.mobile_digest import hard_eligible
class ScopeTests(unittest.TestCase):
 def test_negative_domains(self):
  for t in ['CFUNet RGB-D Pavement Crack Segmentation','Pavement crack segmentation','Bridge crack detection','Road surface defect detection','Road infrastructure inspection','Concrete defect detection','Asphalt maintenance']:
   p={'title':t,'abstract':''};self.assertTrue(infrastructure(p),t);self.assertFalse(traffic_task(p));self.assertFalse(hard_eligible(p));self.assertFalse(ranking_info(p)['eligible'])
 def test_traffic_not_road_word(self):
  for t in ['Autonomous driving vehicle detection','Traffic scene multi-object tracking','Multimodal fusion for traffic monitoring','Road user segmentation']:
   self.assertTrue(traffic_task({'title':t}),t)
  self.assertFalse(traffic_task({'title':'Road inspection'}))
 def test_arxiv_evidence_not_preprint_label(self):
  self.assertFalse(arxiv_preprint({'paper_id':'doi:10.21203/x','resource_type':'preprint','metadata_source':['OpenAlex']}))
  self.assertTrue(arxiv_preprint({'arxiv_id':'2610.12345v2'}))
  p={'resource_type':'conference_paper','quality':{'ccf_a':True},'abstract':'Visual matching methods.'};self.assertTrue(hard_eligible(p))
 def test_actual_cached_general_examples_and_cfunet(self):
  lib=json.loads((Path(__file__).resolve().parents[1]/'papers/maritime/library.json').read_text(encoding='utf8'))
  for k in ['2610.09700','2610.12871']:
   p=lib['papers'][k];self.assertTrue(ranking_info(p)['eligible'],k)
  p=lib['papers']['doi:10.21203/rs.3.rs-11121422/v1'];self.assertFalse(ranking_info(p)['eligible']);self.assertFalse(hard_eligible(p))

 def test_direct_tasks_need_no_ais_and_zero_cannot_be_rescued(self):
  from services.semantic_evaluation import direct_task
  for title in ['Ship visual detection and segmentation','Radar AIS association','Visual AIS cross-modal matching','Autonomous driving vehicle detection','Traffic scene multi-object tracking','Multimodal fusion for traffic monitoring']:
   self.assertTrue(direct_task({'title':title}) or traffic_task({'title':title}),title)
  lib=json.loads((Path(__file__).resolve().parents[1]/'papers/maritime/library.json').read_text(encoding='utf8'))
  p=copy.deepcopy(lib['papers']['2610.09700']);p['semantic']['evaluation'].update(direct_relevance=0,transferability=5,confidence=1)
  self.assertFalse(ranking_info(p)['eligible'])
