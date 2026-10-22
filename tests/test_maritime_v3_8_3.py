import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_maritime_v3_7 as fixtures
from services import maritime_reading as reading
from services import semantic_evaluation as ai
from services.mobile_digest import candidate_pool,select_daily,build_mobile_digest,refresh_reserve,render_mobile_page
from services.mobile_history import PublishedHistory
from services.maritime import write_json
from services.maritime_metadata import enrich_first_affiliations


class PermanentDailyTests(unittest.TestCase):
    make=fixtures.DailyStrictTests.make
    def setUp(self):self.config=ai.settings()

    def test_permanent_arxiv_version_doi_and_alias_history_survives_repair(self):
        p=self.make('2610.30001','2026-10-14');lib={'papers':{p['paper_id']:p},'aliases':{'doi:10.9999/OLD':'2610.30001'}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/'docs/maritime-data/mobile/2026-10-14.json'
            write_json(archive,{'papers':[{'paper_id':'doi:10.9999/OLD'}]})
            self.assertEqual(candidate_pool(root,lib,date(2027,1,1)),[])
            self.assertFalse(refresh_reserve(root,lib,date(2027,1,1))['records'][p['paper_id']]['available'])
            archive.unlink()  # repair of an archive must not forget the persisted history
            self.assertEqual(candidate_pool(root,lib,date(2027,2,1)),[])
            write_json(archive,{'papers':[{'paper_id':'https://arxiv.org/abs/2610.30001v3'}]})
            self.assertTrue(PublishedHistory(root,lib).pushed_dates(p))

    def test_replace_prior_duplicates_retain_same_day_valid_paper_and_never_recycle(self):
        ps=[self.make(f'2610.{32000+i}','2026-10-14') for i in range(10)]
        lib={'papers':{p['paper_id']:p for p in ps}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'docs/maritime-data/mobile'
            write_json(folder/'2026-10-14.json',{'papers':[{'paper_id':p['paper_id']} for p in ps[:4]]})
            write_json(folder/'2026-10-22.json',{'papers':[{'paper_id':p['paper_id']} for p in ps[:5]],'publication_status':'complete'})
            first=build_mobile_digest(root,lib,date(2026,10,22))
            ids=[p['paper_id'] for p in first['papers']]
            self.assertEqual(len(ids),5);self.assertIn(ps[4]['paper_id'],ids)
            self.assertFalse(set(ids)&{p['paper_id'] for p in ps[:4]})
            self.assertEqual(ids,[p['paper_id'] for p in build_mobile_digest(root,lib,date(2026,10,22))['papers']])
            self.assertTrue(all(not r['available'] for k,r in refresh_reserve(root,lib,date(2026,10,22))['records'].items() if k in ids))

    def test_two_versions_of_the_same_unpushed_paper_use_one_slot(self):
        a=self.make('2610.33001','2026-10-20');b=copy.deepcopy(a);b['paper_id']='doi:'+a['doi']
        with tempfile.TemporaryDirectory() as d:
            rows=candidate_pool(Path(d),{'papers':{a['paper_id']:a,b['paper_id']:b}},date(2026,10,22))
            self.assertEqual(len(rows),1)

    def test_missing_chinese_cannot_publish_complete_or_replace_last_complete(self):
        ps=[self.make(f'2610.{34000+i}','2026-10-20') for i in range(5)]
        lib={'papers':{p['paper_id']:p for p in ps}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);first=build_mobile_digest(root,lib,date(2026,10,22))
            ps[0]['translation']={'status':'failed','error_type':'translation_validation_failed','error':'numeric_mismatch'}
            failed=build_mobile_digest(root,lib,date(2026,10,22))
            self.assertEqual(failed['publication_status'],'partial');self.assertEqual(len(failed['selection_audit']['translation_errors']),1)
            self.assertEqual(json.loads((root/'docs/maritime-data/mobile/latest.json').read_text(encoding='utf8'))['papers'],first['papers'])

    def test_formulas_metrics_and_derived_words(self):
        pairs=[('We use AIS-derived features.','我们使用AIS衍生的特征。'),
               ('We improve AP@0.5/AP@0.7 by +20.15/+11.79.','我们将AP@0.5/AP@0.7提升+20.15/+11.79。'),
               ('We use $k$NN for classification.','我们使用$k$NN进行分类。'),
               ('We compare AP and mAP.','我们比较平均精度和平均精度均值。')]
        for en,zh in pairs:self.assertIsNone(reading.translation_error(en,zh),(en,reading.translation_error(en,zh)))
        self.assertIn('protected_formula_missing',reading.translation_error('We use $k$NN.','我们使用NN。'))
        self.assertIn('numeric_mismatch',reading.translation_error('We improve AP@0.5 by 20%.','我们将AP@0.5提升21%。'))
        self.assertIn('protected_token_missing',reading.translation_error('We use an AP access point for communication.','我们使用平均精度进行通信。'))
        english=r'We optimize $k$NN and \(x_1+x_2\) with 20% gain at https://example.org/code.'
        result=reading.translate_one({'abstract':english},lambda text:'我们研究'+text)
        self.assertEqual(result['status'],'machine',result)
        for literal in ('$k$',r'\(x_1+x_2\)','20%','https://example.org/code.'):self.assertIn(literal,result['zh'])
        result=reading.translate_one({'abstract':'We compare MoCo-v2 and DenseCL for object detection.'},lambda text:'我们研究'+text)
        self.assertEqual(result['status'],'machine',result);self.assertIn('MoCo-v2',result['zh'])

    def test_first_author_affiliation_identity_and_ai_cache_are_preserved(self):
        p=self.make('2610.35001','2026-10-20');p.update(authors=['Alice','Bob'],first_author='Alice',affiliation_verified=False)
        before=ai.fingerprint(p,self.config)
        candidate={**p,'first_author_affiliations':['First Institute','Second Institute'],'affiliation_source':'Crossref first author','affiliation_verified':True}
        with tempfile.TemporaryDirectory() as d,patch('clients.scholarly_client.fetch_doi',return_value=candidate) as fetch:
            root=Path(d);lib={'papers':{p['paper_id']:p}}
            enrich_first_affiliations(root,lib,[p['paper_id']]);enrich_first_affiliations(root,lib,[p['paper_id']])
            self.assertEqual(fetch.call_count,1);self.assertEqual(p['first_author_affiliations'][0],'First Institute')
            self.assertEqual(ai.fingerprint(p,self.config),before)
        bad={**candidate,'first_author':'Bob'};p.update(affiliation_verified=False);p.pop('affiliation_check')
        with tempfile.TemporaryDirectory() as d,patch('clients.scholarly_client.fetch_doi',return_value=bad),patch('clients.arxiv_client.fetch_maritime_metadata',return_value=bad):
            enrich_first_affiliations(Path(d),{'papers':{p['paper_id']:p}},[p['paper_id']]);self.assertFalse(p['affiliation_verified'])


if __name__=='__main__':unittest.main()
