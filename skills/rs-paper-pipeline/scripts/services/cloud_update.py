"""Desktop dispatches the single cloud writer; credentials stay in the OS store."""
import json
import os
import subprocess
import time
import urllib.request
import uuid

REPOSITORY='yyf1170808529-cpu/RS-PaperClaw'
WORKFLOW='maritime-no-api.yml'


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
    with urllib.request.urlopen(request,timeout=25) as response:
        body=response.read()
        return json.loads(body) if body else None


def dispatch(arguments=()):
    inputs={'request_id':uuid.uuid4().hex[:12]}
    if '--date' in arguments:inputs['date']=arguments[arguments.index('--date')+1]
    if '--bootstrap' in arguments:inputs['bootstrap']='true'
    if '--resume' in arguments:inputs['resume']='true'
    token=credential()
    api('actions/workflows/'+WORKFLOW+'/dispatches',{'ref':'main','inputs':inputs},token)
    return inputs['request_id'],token


def wait_for_run(request_id,token,wait=True):
    deadline=time.monotonic()+(4200 if wait else 45)
    seen=None
    while time.monotonic()<deadline:
        runs=api('actions/workflows/'+WORKFLOW+'/runs?event=workflow_dispatch&per_page=15',token=token)['workflow_runs']
        run=next((r for r in runs if request_id in r.get('display_title','')),None)
        if run:
            state=(run['status'],run.get('conclusion'))
            if state!=seen:print('云端更新：',*state,run['html_url'],flush=True);seen=state
            if not wait or run['status']=='completed':return run
        time.sleep(30 if run and wait else 5)
    raise TimeoutError('云端任务仍未结束；本地未重新检索或付费。请到仓库Actions查看原任务。')


def public_result(run):
    url='https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-data/'
    def get(name):
        with urllib.request.urlopen(url+name+'?run='+str(run['id']),timeout=25) as response:return json.load(response)
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        pages=api('actions/workflows/maritime-pages.yml/runs?per_page=10')['workflow_runs']
        matching=[p for p in pages if p['created_at']>=run['created_at'] and p['status']=='completed']
        if matching:
            page=matching[0]
            if page['conclusion']!='success':raise RuntimeError('Pages发布失败：'+page['html_url'])
            publication=get('mobile/publication-status.json')
            summary=get('update-result.json')
            if str(summary.get('github_run_id'))!=str(run['id']):
                time.sleep(30);continue
            print(json.dumps({'检索':summary.get('retrieval_status',summary.get('local_update')),'新增':summary.get('added'),
                'AI':summary.get('ai'),'翻译':summary.get('translation'),
                '本次日报':publication['status'],'发布日期':publication['published_date'],
                'GitHub同步':'success','Pages':'success'},ensure_ascii=False),flush=True)
            return summary
        time.sleep(30)
    raise TimeoutError('云端更新已结束，但尚未核实本次Pages内容；不能报告发布成功。')


def cloud_update(root,arguments,wait=True):
    request_id,token=dispatch(arguments)
    run=wait_for_run(request_id,token,wait)
    from services.maritime import write_json
    write_json(root/'papers/maritime/logs/latest-cloud.json',{'request_id':request_id,'run':run})
    if not wait:return 0
    if run.get('conclusion')!='success':
        print('云端存在未完成阶段，请查看：'+run['html_url'],flush=True)
    public_result(run)
    print('本地公共副本：'+pull_public(root),flush=True)
    return 0 if run.get('conclusion')=='success' else 2


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
