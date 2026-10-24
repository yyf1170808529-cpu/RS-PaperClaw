import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/rs-paper-pipeline/scripts'))
from services import maritime_v2 as v, maritime as m, maritime_update as u
import preview_maritime
from test_maritime_v2 import paper, record


class V3Tests(unittest.TestCase):
    def setUp(self):
        self.venues, self.policy = v.assets()
        self.rules = m.load_maritime_assets()

    def conference(self, venue, track=''):
        p = {**paper(title='Vehicle object detection', abstract=''), 'venue': venue, 'paper_type': track,
             'doi': '10.1234/test', 'publication_status': 'published', 'venue_type': 'conference',
             'publication_evidence': {'source': 'Crossref'}, 'assessment': {'level': 'high'}}
        return v.annotate(p, p['arxiv_id'], self.venues, self.policy)

    def test_ccf_2026_grades_and_no_arxiv_bypass(self):
        for venue in ('CVPR', 'ICCV', 'ICML', 'NeurIPS', 'ICLR', 'AAAI', 'ACM MM'):
            p = self.conference(venue)
            self.assertTrue(p['quality']['ccf_a'], venue)
            self.assertEqual(p['recommendation']['bucket'], 'land')
        for venue in ('ECCV', 'IJCAI'):
            p = self.conference(venue)
            self.assertEqual(p['quality']['ccf_grade'], 'B')
            self.assertFalse(p['quality']['ccf_a'])
            self.assertEqual(p['recommendation']['bucket'], 'candidate')
        for track in ('Workshop', 'Demo', 'Short Paper', 'Findings'):
            p = self.conference('CVPR', track)
            self.assertFalse(p['quality']['ccf_a'])
            self.assertEqual(p['recommendation']['bucket'], 'candidate')

    def test_full_name_aliases(self):
        self.assertTrue(self.conference('IEEE/CVF Conference on Computer Vision and Pattern Recognition')['quality']['ccf_a'])
        self.assertFalse(self.conference('Unverified vision conference')['quality']['ccf_a'])

    def test_metric_labels_and_no_guessing(self):
        venues = {'journals': [{'id':'j','issn':['1234-5678'],'cas_records':[record('CAS')], 'jcr_records':[],
                               'jif_records':[{'metric':'CiteScore','value':20,'verified':True,'evidence':record()['evidence']}]}]}
        p = {'issn':['1234-5678'], 'venue_type':'journal', 'publication_status':'published'}
        q = v.venue_quality(p, venues, self.policy)
        self.assertEqual(q['one_type'], '中科院一区')
        self.assertIsNone(q['jif'])
        venues['journals'][0]['jcr_records'] = [record()]
        self.assertEqual(v.venue_quality(p, venues, self.policy)['one_type'], '双一区')
        venues['journals'][0]['cas_records'] = []
        self.assertEqual(v.venue_quality(p, venues, self.policy)['one_type'], 'JCR一区')
        venues['journals'][0]['jcr_records'] = []
        self.assertEqual(v.venue_quality(p, venues, self.policy)['one_type'], '待核验')
        self.assertGreaterEqual(sum(bool(j.get('jif_records')) for j in self.venues['journals']),5)

    def test_windows_and_identical_backend_selection(self):
        ps = [{'paper_id':'water','publication_date':'2026-08-01','recommendation':{'bucket':'water'}},
              {'paper_id':'land','publication_date':'2026-08-01','recommendation':{'bucket':'land'}},
              {'paper_id':'general','publication_date':'2026-10-10','recommendation':{'bucket':'general'}}]
        result = v.recommendation_view(ps, self.policy, '2026-10-13', '7')
        self.assertEqual(result['paper_ids'], ['water','general'])
        self.assertEqual(result['windows'], {'water':90,'land':7,'general':7})

    def test_update_plan_windows_bootstrap_and_source_filters(self):
        args = type('Args',(),{'bootstrap':False,'source':None,'journal':None,'query':None})()
        jobs = u.update_jobs(args,self.venues)
        self.assertEqual({j['source'] for j in jobs},{'arxiv','openalex','crossref'})
        self.assertEqual({j['days'] for j in jobs if j['direction']=='water'}, {90})
        args.bootstrap=True
        self.assertEqual({j['days'] for j in u.update_jobs(args,self.venues) if j['direction']=='water'}, {365})

    @patch.object(u.scholarly_client,'fetch_openalex')
    def test_partial_update_keeps_history_and_status(self, fetch):
        p = {**paper(), 'paper_id':'2610.00001', 'publication_date':'2026-10-10', 'metadata_source':['arXiv']}
        fetch.side_effect=[([p],True),RuntimeError('network failure')]
        jobs=[{'source':'openalex','direction':'land','days':30,'journal':None,'query':'q'}]*2
        with tempfile.TemporaryDirectory() as temp, patch.object(u,'update_jobs',return_value=jobs), patch('services.maritime_validity.verify_records',return_value=[]):
            code=m.main(['--root',temp,'--action','update','--task-timeout','0','--limit','0'])
            self.assertEqual(code,2)
            library=m.load_library(Path(temp))
            self.assertIn('2610.00001',library['papers'])
            status=json.loads((Path(temp)/'papers/maritime/logs/latest-update.json').read_text(encoding='utf-8'))
            self.assertEqual(status['local_update'],'partial')
            self.assertEqual(status['github_sync'],'not_attempted')

    def test_preview_reuses_running_service(self):
        from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
        from functools import partial
        import threading
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT/'docs')))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            self.assertTrue(preview_maritime.existing_service(server.server_port))
            with patch('sys.argv',['preview','--port',str(server.server_port),'--check']):
                preview_maritime.main()
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__ == '__main__':
    unittest.main()
