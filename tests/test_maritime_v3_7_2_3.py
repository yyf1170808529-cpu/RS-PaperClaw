import copy
from datetime import date
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest
import test_maritime_v3_7 as fixtures
from services.mobile_digest import build_mobile_digest,candidate_pool,render_mobile_page
from services import semantic_evaluation as ai


class PublicationProtectionTests(unittest.TestCase):
    make=fixtures.DailyStrictTests.make

    def setUp(self):self.config=ai.settings()
    def test_complete_partial_empty_and_same_day_recovery(self):
        ps=[self.make(f'2610.{20000+i}','2026-10-16') for i in range(7)]
        lib={'papers':{p['paper_id']:p for p in ps}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);first=build_mobile_digest(root,lib,date(2026,10,16))
            self.assertEqual(first['publication_status'],'complete')
            old=(root/'docs/maritime-data/mobile/2026-10-16.json').read_bytes()
            partial=build_mobile_digest(root,lib,date(2026,10,17))
            self.assertEqual(partial['publication_status'],'partial')
            self.assertEqual(len(partial['papers']),2)
            self.assertEqual(partial['published_date'],'2026-10-16')
            self.assertEqual(json.loads((root/'docs/maritime-data/mobile/latest.json').read_text(encoding="utf8"))['date'],'2026-10-16')
            self.assertIn('每日精选 2026-10-16',(root/'docs/maritime-daily.html').read_text(encoding='utf8'))
            self.assertEqual((root/'docs/maritime-data/mobile/2026-10-16.json').read_bytes(),old)
            again=build_mobile_digest(root,lib,date(2026,10,17))
            self.assertEqual([p['paper_id'] for p in partial['papers']],[p['paper_id'] for p in again['papers']])
            self.assertTrue((root/'docs/maritime-data/mobile/pending/2026-10-17.json').exists())
            empty=build_mobile_digest(root,{'papers':{}},date(2026,10,18))
            self.assertEqual(empty['publication_status'],'failed')
            self.assertEqual(empty['published_date'],'2026-10-16')

    def test_rule_candidate_review_and_old_pushed_history_are_available_without_lowering_sources(self):
        p=self.make('2610.20000','2025-01-01')
        p.update(resource_type='preprint',application_bucket='general',publication_status='preprint',recommendation={'bucket':'candidate'},assessment={'level':'transfer','score':12})
        p['semantic']['fingerprint']=ai.fingerprint(p,ai.settings())
        lib={'papers':{p['paper_id']:p}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'docs/maritime-data/mobile';folder.mkdir(parents=True)
            (folder/'2026-10-01.json').write_text(json.dumps({'papers':[{'paper_id':p['paper_id']}]}))
            self.assertEqual(len(candidate_pool(root,lib,date(2026,10,17))),1)
            selected=build_mobile_digest(root,lib,date(2026,10,17))
            self.assertEqual(len(selected['papers']),1)
            p.update(application_bucket='water')
            self.assertEqual(candidate_pool(root,lib,date(2026,10,17)),[])

    def test_no_visible_favorites_debug_text(self):
        page=render_mobile_page({'date':'2026-10-16','papers':[]})
        self.assertNotIn('收藏已就绪',page)
        self.assertNotIn('版本 3.',page)
        self.assertIn('maritime_favorites.js?v=3.7.2.3',page)
