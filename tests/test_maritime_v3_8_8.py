import unittest,sys,json,copy,tempfile
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services.relevance_scope import primary_scope_exclusion,traffic_task,research_directions
from services.semantic_evaluation import ranking_info,validate,payload_for,settings,current_evaluation,direct_task
from services.mobile_digest import hard_eligible,candidate_pool,select_daily,refresh_reserve,reading_index,render_mobile_page
from services.author_display import author_label
ROOT=Path(__file__).resolve().parents[1]
class Scope388Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.lib=json.loads((ROOT/'papers/maritime/library.json').read_text(encoding='utf8'))
 def test_actual_two_negative_chains(self):
  for key in ['2609.30891','2609.16336']:
   p=self.lib['papers'][key];self.assertIsNotNone(current_evaluation(p));self.assertTrue(primary_scope_exclusion(p));self.assertFalse(hard_eligible(p));self.assertEqual(ranking_info(p)['state'],'domain_excluded');self.assertEqual(p['application_bucket'],'other');self.assertEqual(p['recommendation']['bucket'],'candidate')
 def test_primary_object_not_validation_scene(self):
  for title in ['OFDM Pilot Allocation for Vehicle Segmentation','Wireless Communication Protocols for Object Detection','Physical Adversarial Attacks on Stereo Depth Estimation','Industrial Surface Defect Inspection','Adversarial Robustness Assessment Framework for LiDAR Perception','TACTIC: Temporal and Context-Aware LLM Tactical Planning for Roadside LiDAR Attacks']:
   p={'title':title,'abstract':''};self.assertTrue(primary_scope_exclusion(p));self.assertFalse(traffic_task(p))
  for title in ['ISAC Radar Target Recognition and Localization','Robust Cross-modal Representation Learning under Physical Adversarial Attacks','Robust Multimodal Fusion for Autonomous Driving Perception','Vessel Instance Segmentation','Radar-AIS Association','Vision-AIS Cross-modal Matching','Maritime Depth Estimation','Traffic Multi-object Tracking']:
   self.assertFalse(primary_scope_exclusion({'title':title}),title)
  self.assertTrue(direct_task({'title':'Vessel Instance Segmentation','abstract':'Visual perception for ships.'}))
  self.assertFalse(direct_task({'title':'Blood vessel segmentation','abstract':'Clinical imaging.'}))
  self.assertFalse(primary_scope_exclusion({'title':'Robust Cross-modal Representation Learning','abstract':'We propose cross-modal alignment against physical adversarial attacks as a reusable perception learning mechanism.'}))
 def test_actual_positive_metadata_and_evidence_fixture(self):
  p=copy.deepcopy(self.lib['papers']['doi:10.1016/j.inffus.2026.104909']);self.assertEqual(p['application_bucket'],'water');self.assertTrue(p['quality']['high_journal']);self.assertEqual(p['publication_date'],'2026-10-28')
  from services.maritime_v2 import merge_records
  from services.filter_assets import load_maritime_assets
  mini={'papers':{p['paper_id']:copy.deepcopy(p)},'aliases':{},'days':{}}
  incoming={**copy.deepcopy(p),'published':'2026-10','publication_date':'2026-10','publication_date_source':'published'}
  merge_records(mini,[incoming],load_maritime_assets());self.assertEqual(mini['papers'][p['paper_id']]['publication_date'],'2026-10-28')
  # The following is a clearly labelled unit-test abstract, never real library data.
  p['abstract']='We project AIS signals into image space and integrate them through adaptive gated fusion for vessel instance segmentation.';p['abstract_quality']={'status':'validated'}
  p['semantic']=None;self.assertTrue(hard_eligible(p));self.assertEqual(research_directions(p),['A','B'])
 def test_scope_schema_new_required_old_cache_compatible(self):
  p=self.lib['papers']['2610.09700'];v=copy.deepcopy(p['semantic']['evaluation']);self.assertEqual(validate(v,p),v)
  with self.assertRaises(ValueError):validate(v,p,require_scope=True)
  v.update(primary_domain='general_visual_method',primary_problem='hard negatives',target_task='representation',core_contribution='negative construction',application_context='vision language',security_centric=False,communication_centric=False)
  self.assertEqual(validate(v,p,require_scope=True),v)
  flagged=copy.deepcopy(p);flagged['semantic']['evaluation']={**v,'security_centric':True,'confidence':1,'transferability':5}
  self.assertFalse(ranking_info(flagged)['eligible'])
  flagged['semantic']['evaluation']={**v,'primary_domain':'communication_engineering','security_centric':False,'communication_centric':False,'confidence':1,'transferability':5}
  self.assertFalse(ranking_info(flagged)['eligible'])
  self.assertIn('primary_problem',payload_for([p],settings())['messages'][0]['content'])
 def test_real_pool_reserve_reading_index_and_generic_examples(self):
  for k in ['2610.09700','2610.12871']:self.assertTrue(ranking_info(self.lib['papers'][k])['eligible'])
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);chosen,audit=select_daily(root,self.lib,date(2026,11,5));ids={p['paper_id'] for p,_ in candidate_pool(root,self.lib,date(2026,11,5))};self.assertFalse({'2609.30891','2609.16336'}&ids)
   reserve=refresh_reserve(root,self.lib,date(2026,11,5));self.assertFalse(reserve['records'].get('2609.30891',{}).get('available'))
   reading_index(root,self.lib);self.assertTrue((root/'docs/maritime-data/mobile/reading-index.json').exists())
   folder=root/'docs/maritime-data/mobile';rows=[{**self.lib['papers'][k],'abstract_zh':'中文译文'} for k in ['2610.09700','2610.12871','2609.30891','2609.16336','doi:10.1016/j.inffus.2026.104909']]
   (folder/'2026-11-04.json').write_text(json.dumps({'date':'2026-11-04','publication_status':'complete','papers':rows}),encoding='utf8');reading_index(root,self.lib)
   self.assertEqual(json.loads((folder/'reading-index.json').read_text(encoding='utf8'))['batches'],[])
 def test_authors_explicit_only(self):
  p={'authors':['First','Middle','Last']};original=copy.deepcopy(p);self.assertEqual(author_label(p),'First');p.update(corresponding_authors=['Last'],corresponding_author_verified=True,corresponding_author_source='Official flag');self.assertEqual(author_label(p),'First · Corresponding: Last');p['corresponding_authors']=['First','Middle','Last','Last'];self.assertEqual(author_label(p),'First（通讯作者） · Corresponding: Middle、Last');self.assertEqual(p['authors'],original['authors'])
if __name__=='__main__':unittest.main()
