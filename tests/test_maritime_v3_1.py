import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/rs-paper-pipeline/scripts'))
from services import maritime as m, maritime_v2 as v, maritime_metadata as metadata, maritime_update as update, maritime_reading as reading
import update_maritime as launcher
from test_maritime_v2 import paper


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.rules = m.load_maritime_assets()
        self.preprint = {**paper(title='Cross-modal Vessel Detection'), 'paper_id':'2610.00001', 'metadata_source':['arXiv'],
                         'reading':{'analysis':'Original notes','state':'已精读'}, 'translation':{'status':'manual','zh':'人工译文'}}
        self.formal = {**paper(title='Cross Modal Vessel Detection'), 'arxiv_id':None,'paper_id':'doi:10.1234/a','doi':'10.1234/a',
                       'abstract':'','venue':'IEEE Transactions on Intelligent Transportation Systems', 'venue_type':'journal',
                       'publication_status':'published','published':'2026-10','publication_date':'2026-10','metadata_source':['Crossref'],
                       'publication_evidence':{'source':'Crossref','type':'journal-article','url':'https://api.crossref.org/works/10.1234/a'},
                       'reading':{'analysis':'Separate notes','state':'值得精读'}}

    def test_historical_merge_links_abstract_formal_metadata_and_conflicts(self):
        lib={'papers':{p['paper_id']:copy.deepcopy(p) for p in [self.preprint,self.formal]},'days':{'2026-10-10':{'candidate_ids':[self.formal['paper_id']],'searched_topics':[]}}}
        result=v.deduplicate_library(lib,self.rules)
        self.assertEqual(result['merged'],1)
        p=lib['papers']['2610.00001']
        self.assertEqual(p['doi'],'10.1234/a')
        self.assertEqual(p['abstract'],self.preprint['abstract'])
        self.assertEqual(p['publication_date'],'2026-10')
        self.assertEqual(p['translation']['status'],'manual')
        self.assertEqual(lib['aliases'][self.formal['paper_id']],'2610.00001')
        self.assertTrue(any(c['value'].get('analysis')=='Separate notes' for c in p['merge_conflicts']))
        self.assertEqual(lib['days']['2026-10-10']['candidate_ids'],['2610.00001'])
        v.merge_records(lib,[{**self.formal,'reading':{},'abstract':'short'}],self.rules)
        self.assertEqual(lib['papers']['2610.00001']['abstract'],self.preprint['abstract'])

    def test_full_title_author_requirement_and_distinct_formal_dois(self):
        self.assertTrue(v.same_title_authors(self.preprint,self.formal))
        self.assertFalse(v.same_title_authors(self.preprint,{**self.formal,'title':'Cross Modal Vessel Detection II'}))
        self.assertFalse(v.same_title_authors(self.preprint,{**self.formal,'authors':['Different Person']}))
        self.assertFalse(v.title_identity({**self.formal,'arxiv_id':'2610.00001'}, {**self.formal,'doi':'10.1234/b'}))

    def test_journal_name_fallback_is_exact_and_all_papers_share_metrics(self):
        venues,policy=v.assets()
        p={**self.formal,'issn':[]}
        q=v.venue_quality(p,venues,policy)
        self.assertEqual(q['jif'],9.1)
        self.assertTrue(q['jcr_q1'])
        self.assertFalse(q['cas_one'])
        self.assertEqual(v.venue_quality({**p,'venue':'IEEE Transactions on Intelligent Transportation Systems Letters'},venues,policy)['jif'],None)
        self.assertIsNone(v.venue_quality({**p,'issn':['0000-0000']},venues,policy)['jif'])

    def test_cached_source_fills_missing_only_and_keeps_manual_translation(self):
        lib={'papers':{self.formal['paper_id']:copy.deepcopy(self.formal)},'days':{}}
        lib['papers'][self.formal['paper_id']]['translation']={'status':'manual','zh':'keep'}
        with tempfile.TemporaryDirectory() as root, patch.object(metadata,'cached_abstracts',return_value=[{**self.formal,'abstract':'A complete true abstract.'}]):
            result=metadata.enrich_missing(lib,self.rules,Path(root),network=False)
        self.assertEqual(result['filled'],1)
        self.assertEqual(lib['papers'][self.formal['paper_id']]['translation']['zh'],'keep')

    def test_backup_alias_conflicts_preserved_and_validation_atomic(self):
        lib={'papers':{'2610.00001':copy.deepcopy(self.preprint)},'aliases':{'doi:10.1234/a':'2610.00001'}}
        original=copy.deepcopy(lib)
        with self.assertRaises(ValueError):
            m.import_backup(lib,{'schema_version':1,'readings':{'doi:10.1234/a':{'state':'待读','analysis':'new'},'2610.00001':{'state':'bad'}}})
        self.assertEqual(lib,original)
        m.import_backup(lib,{'schema_version':1,'readings':{'doi:10.1234/a':{'state':'已精读','analysis':'new'}}})
        self.assertTrue(lib['papers']['2610.00001']['merge_conflicts'])

    def test_month_precision_retained_and_current_journal_in_window(self):
        p={**self.formal,'recommendation':{'bucket':'water'},'resource_type':'journal_article'}
        _,policy=v.assets()
        self.assertEqual(v.recommendation_view([p],policy,'2026-10-13')['paper_ids'],[p['paper_id']])
        self.assertEqual(p['publication_date'],'2026-10')

    def test_all_success_partial_failure_and_all_failure_final_status(self):
        jobs=[{'source':'openalex','direction':'land','days':30,'journal':None,'query':'q'}]*2
        for responses,code,status in [([([],True),([],True)],2,'success'),([([],True),RuntimeError('timeout')],2,'partial'),([RuntimeError('timeout'),RuntimeError('HTTP500')],1,'failed')]:
            with tempfile.TemporaryDirectory() as root, patch.object(update,'update_jobs',return_value=jobs),patch.object(update,'bounded_fetch',side_effect=responses),redirect_stdout(io.StringIO()) as output:
                result=m.main(['--root',root,'--action','update','--limit','0'])
                summary=json.loads((Path(root)/'papers/maritime/logs/latest-update.json').read_text())
            self.assertEqual(result,code)
            self.assertEqual(summary['local_update'],status)
            self.assertIn('[4/4]',output.getvalue())
            self.assertTrue(summary['completed_at'])

    def test_translation_failure_has_category_without_losing_english(self):
        p=copy.deepcopy(self.preprint);p.pop('translation')
        result=reading.translate_one(p,lambda _: (_ for _ in ()).throw(RuntimeError('Model crashed')))
        self.assertEqual(result['error_type'],'model_runtime_error')
        self.assertEqual(p['abstract'],self.preprint['abstract'])

    def test_real_local_file_lock_refuses_duplicate(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'update.lock'
            with launcher.update_lock(path):
                with self.assertRaises(launcher.UpdateAlreadyRunning):
                    with launcher.update_lock(path):
                        self.fail('Second update started')
            with launcher.update_lock(path):
                pass


if __name__=='__main__':
    unittest.main()
