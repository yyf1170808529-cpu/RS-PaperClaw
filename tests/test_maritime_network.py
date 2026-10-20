"""Desktop network recovery must not create duplicate paid cloud tasks."""
import io
import json
from pathlib import Path
import ssl
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services import cloud_update as cloud


def response(value):
    obj=MagicMock()
    obj.__enter__.return_value.read.return_value=value
    return obj


def run(status='completed'):
    return {'id':123,'status':status,'conclusion':'success' if status=='completed' else None,
            'created_at':'2026-10-20T01:00:00Z','display_title':'Paper update abc123',
            'html_url':cloud.ACTIONS+'/runs/123'}


class NetworkRecoveryTests(unittest.TestCase):
    def test_get_ssl_failure_before_connection_and_during_read_retries(self):
        broken=response(b'')
        broken.__enter__.return_value.read.side_effect=ssl.SSLEOFError('EOF')
        with patch.object(urllib.request,'urlopen',side_effect=[ssl.SSLEOFError('EOF'),broken,response(b'OK')]) as call,patch.object(cloud.time,'sleep') as sleep:
            self.assertEqual(cloud.request_bytes(urllib.request.Request('https://api.github.com/test')),b'OK')
            self.assertEqual(call.call_count,3)
            self.assertEqual([c.args[0] for c in sleep.call_args_list],[2,4])

    def test_temporary_http_errors_retry_but_authentication_does_not(self):
        for status in (429,502,503):
            with self.subTest(status=status),patch.object(urllib.request,'urlopen',side_effect=[urllib.error.HTTPError('https://api.github.com',status,'temporary',{},None),response(b'OK')]) as call,patch.object(cloud.time,'sleep'):
                self.assertEqual(cloud.request_bytes(urllib.request.Request('https://api.github.com/test')),b'OK')
                self.assertEqual(call.call_count,2)
        for status in (401,403):
            with self.subTest(status=status),patch.object(urllib.request,'urlopen',side_effect=urllib.error.HTTPError('https://api.github.com',status,'private-token-must-not-print',{},None)) as call:
                with self.assertRaises(cloud.CloudError) as caught:cloud.request_bytes(urllib.request.Request('https://api.github.com/test'))
                self.assertEqual(caught.exception.kind,'authentication')
                self.assertNotIn('private-token',str(caught.exception))
                self.assertEqual(call.call_count,1)

    def test_rate_limit_long_cooldown_is_preserved_for_next_launch(self):
        error=urllib.error.HTTPError('https://api.github.com',403,'limited',{'X-RateLimit-Remaining':'0','Retry-After':'120'},None)
        with patch.object(urllib.request,'urlopen',side_effect=error) as call,patch.object(cloud.time,'sleep') as sleep:
            with self.assertRaises(cloud.CloudError) as caught:cloud.request_bytes(urllib.request.Request('https://api.github.com/test'))
            self.assertEqual(caught.exception.kind,'rate_limit');self.assertEqual(call.call_count,1);sleep.assert_not_called()

    def test_dispatch_ssl_uncertainty_persists_before_post_and_restart_never_reposts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'papers/maritime/private/cloud-request.json'
            def failed_post(*args,**kwargs):
                self.assertEqual(json.loads(path.read_text())['status'],'dispatching')
                raise ssl.SSLEOFError('EOF')
            with patch.object(cloud,'credential',return_value='secret-not-for-state'),patch.object(urllib.request,'urlopen',side_effect=failed_post) as call,redirect_stdout(io.StringIO()):
                identity,_=cloud.dispatch(state_path=path)
                self.assertEqual(call.call_count,1)
            state=json.loads(path.read_text());self.assertEqual(state['status'],'dispatch_unknown')
            self.assertNotIn('secret-not-for-state',path.read_text())
            with patch.object(cloud,'credential',return_value='secret'),patch.object(cloud,'dispatch') as post,patch.object(cloud,'wait_for_run',return_value=run()) as wait,patch.object(cloud,'public_result',return_value={'web_access':'verified'}),patch.object(cloud,'pull_public',return_value='retained'),redirect_stdout(io.StringIO()):
                self.assertEqual(cloud.cloud_update(root,[]),0)
                post.assert_not_called();self.assertEqual(wait.call_args.args[0],identity)
            self.assertEqual(json.loads(path.read_text())['status'],'verified')

    def test_dispatch_5xx_is_not_retried_even_if_server_may_have_accepted_it(self):
        for status in (502,503):
            with self.subTest(status=status),tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'state.json'
                with patch.object(cloud,'credential',return_value='secret'),patch.object(urllib.request,'urlopen',side_effect=urllib.error.HTTPError('https://api.github.com',status,'temporary',{},None)) as call,redirect_stdout(io.StringIO()):
                    cloud.dispatch(state_path=path)
                self.assertEqual(call.call_count,1)
                self.assertEqual(json.loads(path.read_text())['status'],'dispatch_unknown')

    def test_query_disconnect_after_dispatch_then_resume_exact_run_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'papers/maritime/private/cloud-request.json'
            cloud.save_state(path,{'request_id':'abc123','status':'submitted'})
            output=io.StringIO()
            with patch.object(cloud,'credential',return_value='secret'),patch.object(cloud,'api',side_effect=[{'workflow_runs':[run('in_progress')]},cloud.CloudError('connection','SSL中断')]),patch.object(cloud.time,'sleep'),redirect_stdout(output):
                self.assertEqual(cloud.cloud_update(root,[]),2)
            self.assertEqual(json.loads(path.read_text())['run_id'],123)
            self.assertIn('云端仍可能继续运行',output.getvalue());self.assertIn('/runs/123',output.getvalue())
            with patch.object(cloud,'credential',return_value='secret'),patch.object(cloud,'api',return_value=run()) as api,patch.object(cloud,'dispatch') as post,patch.object(cloud,'public_result',return_value={'web_access':'verified'}),patch.object(cloud,'pull_public',return_value='retained'),redirect_stdout(io.StringIO()):
                self.assertEqual(cloud.cloud_update(root,[]),0)
                api.assert_called_once_with('actions/runs/123',token='secret');post.assert_not_called()

    def test_repeated_transient_poll_failures_recover_without_new_post(self):
        states=[response(json.dumps(run('in_progress')).encode()),ssl.SSLEOFError('EOF'),ssl.SSLEOFError('EOF'),response(json.dumps(run()).encode())]
        with patch.object(urllib.request,'urlopen',side_effect=states) as call,patch.object(cloud.time,'sleep'),redirect_stdout(io.StringIO()):
            self.assertEqual(cloud.wait_for_run('abc123','secret',state={'run_id':123})['conclusion'],'success')
            self.assertTrue(all(c.args[0].get_method()=='GET' for c in call.call_args_list))

    def test_first_upgrade_adopts_existing_task_instead_of_dispatching(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(cloud,'credential',return_value='secret'),patch.object(cloud,'api',return_value={'workflow_runs':[run()]}),patch.object(cloud,'dispatch') as post,patch.object(cloud,'wait_for_run',return_value=run()),patch.object(cloud,'public_result',return_value={'web_access':'verified'}),patch.object(cloud,'pull_public',return_value='retained'),redirect_stdout(io.StringIO()):
            self.assertEqual(cloud.cloud_update(Path(directory),[]),0);post.assert_not_called()

    def test_pages_success_but_site_network_failure_is_not_deployment_failure(self):
        deployment={**run(),'id':456,'head_sha':'commit','conclusion':'success'}
        with patch.object(cloud,'api',return_value={'workflow_runs':[deployment]}),patch.object(cloud,'repository_json',return_value={'github_run_id':'123'}),patch.object(cloud,'request_bytes',side_effect=cloud.CloudError('connection','SSL中断')),redirect_stdout(io.StringIO()) as output:
            result=cloud.public_result(run())
            self.assertEqual(result['pages_publish'],'success');self.assertEqual(result['web_access'],'unverified_network')
            self.assertIn('Pages发布成功，当前网络无法验证网页访问',output.getvalue())
            self.assertIn('/blob/commit/',output.getvalue())

    def test_unrelated_pages_deployment_cannot_confirm_current_task(self):
        wrong={**run(),'id':455,'head_sha':'wrong'}
        right={**run(),'id':456,'head_sha':'right'}
        payloads=[{'published_date':'2026-10-20','status':'complete'},{'github_run_id':'123'},
                  {'date':'2026-10-20','papers':[{'title':'Paper '+str(n)} for n in range(5)]}]
        with patch.object(cloud,'api',return_value={'workflow_runs':[wrong,right]}),patch.object(cloud,'repository_json',side_effect=[{'github_run_id':'999'},{'github_run_id':'123'}]),patch.object(cloud,'request_bytes',side_effect=[json.dumps(p).encode() for p in payloads]+[b'Paper 0 Paper 1 Paper 2 Paper 3 Paper 4']),redirect_stdout(io.StringIO()):
            self.assertEqual(cloud.public_result(run())['pages_run_id'],456)

    def test_pages_real_failure_remains_distinct(self):
        deployment={**run(),'id':456,'head_sha':'commit','conclusion':'failure'}
        with patch.object(cloud,'api',return_value={'workflow_runs':[deployment]}),patch.object(cloud,'repository_json',return_value={'github_run_id':'123'}):
            with self.assertRaises(cloud.CloudError) as caught:cloud.public_result(run())
            self.assertEqual(caught.exception.kind,'pages_failed')

    def test_restart_after_later_publication_verifies_original_without_getting_stuck(self):
        deployment={**run(),'id':456,'head_sha':'original'}
        live={'date':'2026-10-21','papers':[{'title':'Paper '+str(n)} for n in range(5)]}
        payloads=[{'published_date':'2026-10-21','status':'complete'},{'github_run_id':'999'},live]
        with patch.object(cloud,'api',return_value={'workflow_runs':[deployment]}),patch.object(cloud,'repository_json',side_effect=[{'github_run_id':'123'},{'github_run_id':'999'},live]),patch.object(cloud,'request_bytes',side_effect=[json.dumps(p).encode() for p in payloads]+[b'Paper 0 Paper 1 Paper 2 Paper 3 Paper 4']),redirect_stdout(io.StringIO()) as output:
            result=cloud.public_result(run(),wait=False)
            self.assertEqual(result['web_access'],'verified');self.assertEqual(result['live_github_run_id'],'999')
            self.assertIn('线上已由后续任务更新',output.getvalue())

    def test_successful_dispatch_receipt_is_saved_before_any_query(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(cloud,'credential',return_value='secret'),patch.object(cloud,'api') as api:
            path=Path(directory)/'state.json'
            identity,_=cloud.dispatch(state_path=path)
            api.assert_called_once()
            self.assertEqual(json.loads(path.read_text())['status'],'submitted')
            self.assertEqual(json.loads(path.read_text())['request_id'],identity)

    def test_ambiguous_dispatch_lookup_has_a_bound_and_never_posts_again(self):
        with patch.object(cloud,'api',return_value={'workflow_runs':[]}) as api,patch.object(cloud.time,'monotonic',side_effect=[0,0,1,46]),patch.object(cloud.time,'sleep') as sleep:
            with self.assertRaises(cloud.CloudError) as caught:cloud.wait_for_run('unknown','secret')
            self.assertEqual(caught.exception.kind,'pending');self.assertEqual(api.call_count,1)
            self.assertNotIn('dispatches',api.call_args.args[0]);sleep.assert_not_called()

    def test_two_desktop_windows_cannot_dispatch_concurrently(self):
        import update_maritime
        with patch.object(sys,'argv',['update_maritime.py','--no-open']),patch.object(update_maritime,'update_lock',side_effect=update_maritime.UpdateAlreadyRunning),patch.object(cloud,'cloud_update') as update,redirect_stdout(io.StringIO()):
            self.assertEqual(update_maritime.main(),3);update.assert_not_called()


if __name__=='__main__':unittest.main()
