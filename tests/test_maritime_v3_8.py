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
            self.assertFalse(refresh_reserve(root,lib,date(2026,10,28))['records'][p['paper_id']]['available'])
            p['abstract']='Changed actual abstract'
            self.assertFalse(refresh_reserve(root,lib,date(2026,10,28))['records'][p['paper_id']]['qualified'])

    def test_desktop_default_dispatches_cloud_without_local_update_or_git_sync(self):
        with patch.object(sys,'argv',['update_maritime.py','--no-open','--cloud-no-wait']),patch('services.cloud_update.cloud_update',return_value=0) as cloud,patch.object(update_maritime,'execute_update') as local:
            self.assertEqual(update_maritime.main(),0);cloud.assert_called_once();local.assert_not_called()
            self.assertFalse(cloud.call_args.kwargs['wait'])

    def test_local_maintenance_is_nonpaying_and_not_a_second_cloud_writer(self):
        with patch.object(sys,'argv',['update_maritime.py','--local','--no-open']),patch('services.cloud_update.cloud_update') as cloud,patch.object(update_maritime,'execute_update',return_value=0) as local:
            self.assertEqual(update_maritime.main(),0);cloud.assert_not_called()
            self.assertIn('--no-ai',local.call_args.args[2])

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

    def test_dirty_local_checkout_never_fetches_or_blocks_cloud_result(self):
        from types import SimpleNamespace
        def fake(command,**kwargs):
            self.assertNotIn('fetch',command)
            output=' M local-code.py' if 'status' in command else 'main' if 'branch' in command else 'https://github.com/'+cloud_update.REPOSITORY+'.git'
            return SimpleNamespace(returncode=0,stdout=output,stderr='')
        with patch('subprocess.run',side_effect=fake):
            self.assertIn('保留本地开发修改',cloud_update.pull_public(Path('.')))

    def test_legacy_argos_resources_do_not_initialize_incompatible_stanza(self):
        from types import SimpleNamespace
        from services.maritime_reading import argos_translator
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);(directory/'stanza').mkdir()
            (directory/'stanza/resources.json').write_text(json.dumps({'en':{'tokenize':{'ewt':{}}}}))
            pair=SimpleNamespace(pkg=SimpleNamespace(package_path=directory),sentencizer=SimpleNamespace(stanza_pipeline=None,stanza_lang_code='en'))
            pair.hypotheses=lambda text,num_hypotheses:[SimpleNamespace(value='中文译文')]
            langs=[SimpleNamespace(code='en',get_translation=lambda zh:pair),SimpleNamespace(code='zh')]
            stanza=SimpleNamespace(Pipeline=__import__('unittest.mock',fromlist=['Mock']).Mock())
            fake=SimpleNamespace(translate=SimpleNamespace(get_installed_languages=lambda:langs))
            with patch.dict(sys.modules,{'argostranslate':fake,'stanza':stanza}):
                translator=argos_translator();self.assertEqual(translator('English'),'中文译文')
                self.assertEqual(pair.sentencizer.split_sentences('First sentence. Second sentence.'),['First sentence.','Second sentence.'])
                stanza.Pipeline.assert_not_called()

    def test_unsynced_artifact_recovery_is_idempotent_and_preserves_manual_translation(self):
        from services.cloud_recovery import restore
        from services.maritime import write_json,read_json
        p=self.make('2610.30001','2026-10-19');p['translation']={'status':'manual','zh':'人工修订摘要'}
        fresh=self.make('2610.30002','2026-10-19')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);artifact=root/'private-recovery'
            write_json(root/'papers/maritime/library.json',{'papers':{p['paper_id']:p},'days':{}})
            write_json(artifact/'papers/maritime/library.json',{'papers':{fresh['paper_id']:fresh},'days':{}})
            self.assertEqual(restore(root,artifact)['added'],1)
            self.assertEqual(restore(root,artifact)['added'],0)
            actual=read_json(root/'papers/maritime/library.json',{})
            self.assertEqual(actual['papers'][p['paper_id']]['translation']['zh'],'人工修订摘要')
            self.assertEqual(len(actual['papers']),2)

    def test_broken_translation_environment_cannot_replace_a_complete_daily(self):
        from datetime import date
        from services.mobile_digest import build_mobile_digest
        from services.maritime import read_json
        ps=[self.make(f'2610.{31000+i}','2026-10-19') for i in range(5)]
        lib={'papers':{p['paper_id']:p for p in ps}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);first=build_mobile_digest(root,lib,date(2026,10,19))
            for p in ps:p['translation']={'status':'failed','error_type':'model_runtime_error','error':'Tokenizer environment failure'}
            failed=build_mobile_digest(root,lib,date(2026,10,19))
            self.assertEqual(len(failed['papers']),5);self.assertEqual(failed['publication_status'],'partial')
            self.assertEqual(len(failed['selection_audit']['translation_environment_errors']),5)
            self.assertEqual(read_json(root/'docs/maritime-data/mobile/latest.json',{})['papers'],first['papers'])
