"""Desktop dispatches the single cloud writer; credentials stay in the OS store."""
import json
import os
import subprocess
import time
import urllib.request
import uuid
import html
import urllib.error
import ssl
import http.client
import base64
from datetime import datetime, timezone

REPOSITORY='yyf1170808529-cpu/RS-PaperClaw'
WORKFLOW='maritime-no-api.yml'
SITE='https://yyf1170808529-cpu.github.io/RS-PaperClaw/'
ACTIONS='https://github.com/'+REPOSITORY+'/actions'


class CloudError(RuntimeError):
    def __init__(self,kind,message,status=None):
        super().__init__(message)
        self.kind=kind
        self.status=status


def request_bytes(request):
    """Retry reads only. A failed POST may already have started paid work."""
    read=request.get_method()=='GET'
    for attempt in range(3 if read else 1):
        cooldown=0
        try:
            with urllib.request.urlopen(request,timeout=25) as response:return response.read()
        except urllib.error.HTTPError as exc:
            limited=exc.code==429 or (exc.code==403 and
                (exc.headers.get('X-RateLimit-Remaining')=='0' or exc.headers.get('Retry-After')))
            kind='rate_limit' if limited else 'authentication' if exc.code in (401,403) else 'connection' if exc.code in (408,500,502,503,504) else 'http'
            message={'rate_limit':'GitHub/API限流，请稍后继续查询原任务',
                     'authentication':'GitHub认证或权限失败，请检查本机授权',
                     'connection':'远端服务暂时不可用'}.get(kind,'远端HTTP请求失败')
            error=CloudError(kind,f'{message}（HTTP {exc.code}）',exc.code)
            retry=kind in ('rate_limit','connection')
            # Do not retry before a long server-advertised cooldown; next launch resumes.
            retry_after=exc.headers.get('Retry-After','0')
            try:cooldown=float(retry_after)
            except ValueError:cooldown=61
            if limited and (cooldown>8 or exc.headers.get('X-RateLimit-Remaining')=='0'):retry=False
        except (urllib.error.URLError,ssl.SSLError,OSError,http.client.HTTPException):
            error=CloudError('connection','网络连接失败或SSL连接中断；未判定云端任务失败')
            retry=True
        if not read or not retry or attempt==2:raise error
        delay=min(2**(attempt+1),8)
        delay=max(delay,min(cooldown,8))
        print(f'网络查询暂未成功，{delay:g}秒后重试（{attempt+1}/2）。',flush=True)
        time.sleep(delay)


def save_state(path,state):
    from services.maritime import write_json
    if path is not None:write_json(path,state)


def credential():
    if os.environ.get('GITHUB_TOKEN'):return os.environ['GITHUB_TOKEN']
    gh=__import__('shutil').which('gh')
    if gh:
        result=subprocess.run([gh,'auth','token'],capture_output=True,text=True,timeout=15)
        if result.returncode==0:return result.stdout.strip()
    result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',
        capture_output=True,text=True,timeout=20,env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'Never'})
    values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode==0 and values.get('password'):return values['password']
    raise RuntimeError('GitHub未授权。请先运行 git credential-manager github login 完成一次浏览器授权，再双击论文更新；不要把Token发到聊天或写入仓库。')


def api(path, payload=None, token=None):
    request=urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+'/'+path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization':'Bearer '+(token or credential()),'Accept':'application/vnd.github+json',
                 'Content-Type':'application/json','User-Agent':'RS-PaperClaw'})
    body=request_bytes(request)
    return json.loads(body) if body else None


def dispatch(arguments=(),state_path=None):
    inputs={'request_id':uuid.uuid4().hex[:12]}
    if '--date' in arguments:inputs['date']=arguments[arguments.index('--date')+1]
    if '--bootstrap' in arguments:inputs['bootstrap']='true'
    if '--resume' in arguments:inputs['resume']='true'
    token=credential()
    state={'request_id':inputs['request_id'],'status':'dispatching',
           'submitted_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}
    # Persist before sending: even a process crash or TLS failure must never cause a repeat POST.
    save_state(state_path,state)
    try:
        api('actions/workflows/'+WORKFLOW+'/dispatches',{'ref':'main','inputs':inputs},token)
    except CloudError as exc:
        state['status']='rejected' if exc.status in (401,403,404,422,429) else 'dispatch_unknown'
        save_state(state_path,state)
        if state['status']=='rejected':raise
        print('触发请求响应中断，服务器可能已经接受；仅查找原request_id，不重复触发。',flush=True)
    else:
        state['status']='submitted';save_state(state_path,state)
    return inputs['request_id'],token


def wait_for_run(request_id,token,wait=True,state_path=None,state=None):
    state=state if state is not None else {'request_id':request_id}
    deadline=time.monotonic()+(4200 if wait else 45)
    discovery_deadline=time.monotonic()+45
    seen=None
    while time.monotonic()<deadline:
        if state.get('run_id'):
            run=api('actions/runs/'+str(state['run_id']),token=token)
        else:
            run=None
            for page in range(1,11):
                runs=api(f'actions/workflows/{WORKFLOW}/runs?event=workflow_dispatch&per_page=100&page={page}',token=token)['workflow_runs']
                run=next((r for r in runs if r.get('display_title','')=='Paper update '+request_id),None)
                if run or len(runs)<100 or not state.get('submitted_at') or runs[-1]['created_at']<state['submitted_at']:break
        if run:
            state.update(run_id=run['id'],run=run,status='found');save_state(state_path,state)
            observed=(run['status'],run.get('conclusion'))
            if observed!=seen:print('云端更新：',*observed,run['html_url'],flush=True);seen=observed
            if not wait or run['status']=='completed':return run
        elif time.monotonic()>=discovery_deadline:break
        time.sleep(30 if run and wait else 5)
    raise CloudError('pending','尚未确认原任务结果；云端仍可能继续运行，下次双击将继续查询，不重复触发。')


def repository_json(path,ref,token=None):
    record=api('contents/docs/maritime-data/'+path+'?ref='+ref,token=token)
    return json.loads(base64.b64decode(record['content']))


def public_result(run,wait=True):
    url=SITE+'maritime-data/'
    def get(name):
        return json.loads(request_bytes(urllib.request.Request(url+name+'?run='+str(run['id']))))
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        pages=api('actions/workflows/maritime-pages.yml/runs?per_page=10')['workflow_runs']
        matching=[p for p in pages if p['created_at']>=run['created_at'] and p['status']=='completed']
        for deployment in matching:
            # Timestamp alone can select an unrelated deployment. Check the committed run identity.
            summary=repository_json('update-result.json',deployment['head_sha'])
            if str(summary.get('github_run_id'))!=str(run['id']):continue
            if deployment['conclusion']!='success':raise CloudError('pages_failed','Pages部署失败：'+deployment['html_url'])
            try:
                publication=get('mobile/publication-status.json')
                live_summary=get('update-result.json')
                latest=get('mobile/latest.json')
                page=request_bytes(urllib.request.Request(SITE+'maritime-daily.html?run='+str(run['id']))).decode('utf8')
            except CloudError as exc:
                if exc.kind not in ('connection','http','rate_limit','authentication'):raise
                print('Pages发布成功，当前网络无法验证网页访问。\n任务：'+run['html_url']+'\n部署：'+deployment['html_url']+
                      '\n日报源文件：https://github.com/'+REPOSITORY+'/blob/'+deployment['head_sha']+'/docs/maritime-data/mobile/latest.json',flush=True)
                return {**summary,'pages_publish':'success','web_access':'unverified_network','pages_run_id':deployment['id']}
            superseded=str(live_summary.get('github_run_id'))!=str(run['id'])
            if superseded:
                # A later scheduled update may have published while this desktop was offline.
                # Verify the original deployment, and compare current live files with the repo.
                current=repository_json('update-result.json','main')
                if current.get('github_run_id')!=live_summary.get('github_run_id'):continue
                if repository_json('mobile/latest.json','main')!=latest:continue
            if len(latest.get('papers',[]))!=5 or latest.get('date')!=publication['published_date'] or not all(html.escape(p['title']) in page for p in latest['papers']):
                continue
            ai=summary.get('ai',{});translation=summary.get('translation',{})
            if superseded:
                print('原任务Pages发布成功；线上已由后续任务更新。以下为原任务统计；当前网页日期 '+latest['date']+'。',flush=True)
            source=summary.get('retrieval_status',summary.get('local_update'))
            source={'success':'完成','partial':'部分来源未成功，其余数据已保存','failed':'来源失败','not_run_resume':'恢复模式，未重新检索'}.get(source,source)
            daily={'complete':'完整五篇','partial':'部分完成，保留最近完整日报','failed':'本次无新日报，保留最近完整日报'}.get(publication['status'],publication['status'])
            print(f"检索：{source}；新增 {summary.get('added',0)} 篇。",flush=True)
            print(f"AI：新评价 {ai.get('processed',0)}，复用 {ai.get('cached',0)}，校验拒收 {ai.get('failed',0)}；本次计价约 ¥{ai.get('priced_cost_cny',0):.6f}。",flush=True)
            print(f"Argos：新译 {translation.get('translated',0)}，缓存 {translation.get('cached',0)}，失败 {translation.get('failed',0)}。",flush=True)
            print(f"精选：{daily}；展示日期 {publication['published_date']}；后备 {ai.get('reserve_available',0)} 篇。",flush=True)
            print('GitHub同步：成功；Pages发布：成功。\n阅读：https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html',flush=True)
            if ai.get('unsettled_upper_cny'):print('存在未决API计费，请查看详细日志。',flush=True)
            return {**summary,'pages_publish':'success','web_access':'verified','pages_run_id':deployment['id'],
                    'live_github_run_id':live_summary.get('github_run_id')}
        if not wait:break
        time.sleep(30)
    raise CloudError('pages_pending','云端更新已结束，但尚未核实本次Pages内容；下次继续核验原任务。')


def cloud_update(root,arguments,wait=True):
    from services.maritime import write_json
    path=root/'papers/maritime/private/cloud-request.json'
    # Do not discard malformed state and risk creating another paid task.
    state=json.loads(path.read_text(encoding='utf8')) if path.exists() else {}
    try:
        token=credential()
        if not state or state.get('status') in ('verified','rejected'):
            runs=api('actions/workflows/'+WORKFLOW+'/runs?event=workflow_dispatch&per_page=100',token=token)['workflow_runs']
            active=next((r for r in runs if r['status']!='completed'),None)
            # First upgrade: the old client may have lost its receipt before persisting anything.
            if not state and runs:active=active or runs[0]
            if active:
                state={'request_id':active['display_title'].removeprefix('Paper update '),'run_id':active['id'],'run':active,'status':'found'}
                save_state(path,state)
                print('恢复最近的桌面任务，继续查询：'+active['html_url'],flush=True)
            else:
                dispatch(arguments,state_path=path)
                state=json.loads(path.read_text(encoding='utf8'))
        else:print('继续上次任务：'+state['request_id']+'；不重新触发或付费。',flush=True)
        run=wait_for_run(state['request_id'],token,wait,state_path=path,state=state)
        write_json(root/'papers/maritime/logs/latest-cloud.json',{'request_id':state['request_id'],'run':run})
        if not wait:return 0
        if run.get('conclusion')!='success':
            print('云端任务失败或未完成（'+str(run.get('conclusion'))+'）：'+run['html_url']+'；继续单独核验已保存数据及Pages。',flush=True)
        summary=public_result(run)
        state['status']='verified' if summary['web_access']=='verified' else 'awaiting_web'
        state['result']=summary;save_state(path,state)
        write_json(root/'papers/maritime/logs/latest-cloud-result.json',summary)
        print('本地公共副本：'+pull_public(root),flush=True)
        return 0 if run.get('conclusion')=='success' and summary['web_access']=='verified' else 2
    except CloudError as exc:
        print(str(exc),flush=True)
        if path.exists():state=json.loads(path.read_text(encoding='utf8'))
        link=state.get('run',{}).get('html_url',ACTIONS+'/workflows/'+WORKFLOW)
        print(f"查询状态：{exc.kind}；request_id={state.get('request_id','尚未触发')}；run_id={state.get('run_id','尚未确认')}。\n任务：{link}",flush=True)
        print('最新日报源文件：https://github.com/'+REPOSITORY+'/blob/main/docs/maritime-data/mobile/latest.json',flush=True)
        if state and state.get('status') not in ('verified','rejected'):
            print('本地尚未核验完成，云端仍可能继续运行；下次双击继续查询同一任务，不重复触发。',flush=True)
        return 2


def pull_public(root):
    """A dirty development checkout never prevents the cloud publication."""
    prefix=['git']+(['-c','http.proxy='+os.environ['HTTPS_PROXY']] if os.environ.get('HTTPS_PROXY') else [])
    def git(*args):
        p=subprocess.run(prefix+list(args),cwd=root,capture_output=True,text=True,timeout=40)
        if p.returncode:raise RuntimeError(p.stderr.strip())
        return p.stdout.strip()
    try:
        if git('remote','get-url','origin').removesuffix('.git')!='https://github.com/'+REPOSITORY:return '未拉取：仓库地址不匹配'
        if git('branch','--show-current')!='main':return '未拉取：当前是开发分支'
        if git('status','--porcelain'):return '未拉取：保留本地开发修改；云端结果已独立保存'
        git('fetch','origin','main');git('merge','--ff-only','origin/main')
        return '已安全快进到云端最新数据'
    except Exception:
        return '未拉取：不能安全快进；保留本地文件，云端更新不受影响'
