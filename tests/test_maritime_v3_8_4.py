from datetime import date
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
import test_maritime_v3_7 as fixtures
from services.selected_translation import translate_selected
from services.mobile_digest import select_daily,build_mobile_digest,render_mobile_page
from services.maritime_reading import translate_one,translation_error


class RecoveryTests(unittest.TestCase):
    def test_incomplete_legacy_archive_keeps_legacy_favorites_bootstrap(self):
        page=render_mobile_page({'date':'2026-10-17','papers':[],'publication_status':'partial'})
        self.assertNotIn('id="daily-reading-data"',page)
        self.assertIn('id="daily-favorites"',page)
        self.assertIn('id="daily-prompt-data"',page)

    def test_failed_selected_replaced_not_pushed_and_repair_can_return(self):
        fixture=fixtures.DailyStrictTests();fixture.setUp()
        ps=[fixture.make(f'2610.{20000+i}','2026-10-24') for i in range(7)]
        lib={'papers':{p['paper_id']:p for p in ps},'days':{}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);chosen,_=select_daily(root,lib,date(2026,10,24));bad=chosen[0][0]
            bad['translation']={}
            def worker(library,keys,*args,**kwargs):
                if bad['paper_id'] in keys:bad['translation']={'status':'failed','error':'numeric_mismatch'}
                return {'translated':0,'failed':int(bad['paper_id'] in keys),'cached':sum(k!=bad['paper_id'] for k in keys)}
            with patch('services.maritime_update.translate_budget',side_effect=worker):
                result=translate_selected(root,lib,date(2026,10,24))
            self.assertEqual(result['failed'],0)
            self.assertEqual(len(result['replacement_failures']),1)
            published=build_mobile_digest(root,lib,date(2026,10,24))
            self.assertEqual(published['publication_status'],'complete')
            self.assertNotIn(bad['paper_id'],[p['paper_id'] for p in published['papers']])
            self.assertIn(bad['paper_id'],lib['selected_translation_repairs'])
            # Failed paper was not published and remains recoverable on next day.
            rows,_=select_daily(root,lib,date(2026,10,25))
            self.assertIn(bad['paper_id'],[p['paper_id'] for p,_,_ in rows])

    def test_respectively_protected_without_disabling_numeric_check(self):
        p={'abstract':'Gains are 1.6 and 2.9, respectively. The source code will be publicly available.'}
        def model(text):return '中文'+text.replace('respectively','1')
        result=translate_one(p,model)
        self.assertEqual(result['status'],'machine')
        self.assertIn('分别',result['zh'])
        self.assertEqual(result['english_hash'],hashlib.sha256(p['abstract'].encode()).hexdigest())
        self.assertIn('numeric_mismatch',translation_error(p['abstract'],result['zh'].replace('1.6','1.7')))

    def test_exhausted_reserve_keeps_last_complete_and_pending_failure(self):
        fixture=fixtures.DailyStrictTests();fixture.setUp()
        ps=[fixture.make(f'2610.{30000+i}','2026-10-23') for i in range(5)]
        lib={'papers':{p['paper_id']:p for p in ps}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);build_mobile_digest(root,lib,date(2026,10,23))
            result=build_mobile_digest(root,lib,date(2026,10,24))
            self.assertEqual(result['published_date'],'2026-10-23')
            self.assertNotEqual(result['publication_status'],'complete')


if __name__=='__main__':unittest.main()
