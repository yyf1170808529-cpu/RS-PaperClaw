import unittest,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services.reading_translation import validate,cached,settings
class TranslationTests(unittest.TestCase):
 def test_identity_numbers_and_one_sentence(self):
  p={'paper_id':'2610.12345','abstract':'A method improves 12.5% with 3D data.'}
  v={'paper_id':p['paper_id'],'summary_zh':'本文研究三维数据。','migration_zh':'研究推断：可调整输入。','abstract_zh':'该方法使用3D数据取得12.5%的提升。'}
  self.assertEqual(validate(v,p),v)
  with self.assertRaises(ValueError):validate({**v,'paper_id':'wrong'},p)
  with self.assertRaises(ValueError):validate({**v,'abstract_zh':'方法提高了百分之十。'},p)
  p['reading_enrichment']={'status':'success','english_hash':hashlib.sha256(p['abstract'].encode()).hexdigest(),'prompt_version':settings()['version'],'content':v}
  self.assertTrue(cached(p));p['abstract']+=' Changed.';self.assertIsNone(cached(p))
