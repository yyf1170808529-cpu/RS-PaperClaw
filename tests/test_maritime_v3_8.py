import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
import test_maritime_v3_7 as fixtures
from services.mobile_digest import refresh_reserve
from services import semantic_evaluation as ai
from services import cloud_update
import update_maritime


class CloudReserveTests(unittest.TestCase):
    make=fixtures.DailyStrictTests.make
    def setUp(self):self.config=ai.settings()

    def test_reserve_carries_identity_fingerprint_history_and_invalidates_changed_abstract(self):
        p=self.make('2610.30001','2026-10-19');lib={'papers':{p['paper_id']:p}}
        from datetime import date
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'docs/maritime-data/mobile';folder.mkdir(parents=True)
            (folder/'2026-10-18.json').write_text(json.dumps({'date':'2026-10-18','papers':[{'paper_id':p['paper_id']}]}))
            queue=refresh_reserve(root,lib,date(2026,10,19));r=queue['records'][p['paper_id']]
            self.assertEqual(r['fingerprint'],p['semantic']['fingerprint']);self.assertFalse(r['available'])
            self.assertEqual(r['pushed_dates'],['2026-10-18'])
            self.assertTrue(refresh_reserve(root,lib,date(2026,10,28))['records'][p['paper_id']]['available'])
            p['abstract']='Changed actual abstract'
            self.assertFalse(refresh_reserve(root,lib,date(2026,10,28))['records'][p['paper_id']]['qualified'])

    def test_desktop_default_dispatches_cloud_without_local_update_or_git_sync(self):
        with patch.object(sys,'argv',['update_maritime.py','--no-open','--cloud-no-wait']),patch('services.cloud_update.cloud_update',return_value=0) as cloud,patch.object(update_maritime,'execute_update') as local:
            self.assertEqual(update_maritime.main(),0);cloud.assert_called_once();local.assert_not_called()
            self.assertFalse(cloud.call_args.kwargs['wait'])

    def test_dispatch_uses_request_identity_and_resume_same_workflow(self):
        with patch.object(cloud_update,'credential',return_value='unit-test-only'),patch.object(cloud_update,'api') as api:
            request_id,_=cloud_update.dispatch(['--date','20261019','--resume'])
            path,payload,token=api.call_args.args
            self.assertEqual(path,'actions/workflows/maritime-no-api.yml/dispatches')
            self.assertEqual(payload['inputs'],{'request_id':request_id,'date':'20261019','resume':'true'})
            self.assertNotIn('unit-test-only',json.dumps(payload))

    def test_failed_same_fingerprint_is_not_paid_again_today(self):
        p=self.make('2610.30001','2026-10-19');p.pop('semantic');lib={'papers':{p['paper_id']:p}}
        from services.maritime import write_json,today
        with tempfile.TemporaryDirectory() as d,patch('clients.deepseek_client.complete') as call:
            root=Path(d);write_json(root/'docs/maritime-data/semantic-attempts.json',{'records':{ai.fingerprint(p,self.config):{'date':str(today()),'status':'attempted'}}})
            result=ai.daily_evaluate(root,lib,[],today())
            self.assertEqual(result['already_attempted_today'],1);self.assertEqual(result['processed'],0);call.assert_not_called()
