"""Explicit public-file allowlist, no force/rebase/reset, conservative remote checks."""
import fnmatch
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request

def allowed(path, config):
    return not any(part in {'private','backups','.venv-maritime','logs'} for part in Path(path).parts) and any(fnmatch.fnmatchcase(path,pattern) for pattern in config['paths'])

def api(url, timeout=20):
    request=urllib.request.Request(url,headers={'User-Agent':'RS-PaperClaw','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=timeout) as response:return json.load(response)

def sync(root, wait_seconds=180):
    config=json.loads((root/'skills/rs-paper-pipeline/scripts/config/maritime/publication.json').read_text(encoding='utf8'))
    result={'github_sync':'not_attempted','pages_publish':'not_attempted'}
    proxy=os.environ.get('RS_PROXY_URL') or os.environ.get('HTTPS_PROXY')
    prefix=['git']+(['-c','http.proxy='+proxy] if proxy else [])
    def git(*args):
        p=subprocess.run(prefix+list(args),cwd=root,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=60)
        if p.returncode:raise RuntimeError(p.stderr.strip() or p.stdout.strip())
        return p.stdout.rstrip('\r\n')
    try:
        if not config.get('enabled'):return {**result,'reason':'自动同步未启用'}
        expected='https://github.com/'+config['repository']
        remote=git('remote','get-url','origin').removesuffix('.git')
        if remote != expected or 'thinson/' in remote:raise RuntimeError('origin不是配置的用户Fork，停止发布')
        if git('branch','--show-current')!=config['branch']:raise RuntimeError('当前分支不匹配，停止发布')
        if git('diff','--cached','--name-only'):raise RuntimeError('已有暂存修改，停止自动提交')
        changed=git('status','--porcelain','-z','--untracked-files=all').split('\x00')
        if any(line[:2].strip().startswith('R') for line in changed if line):raise RuntimeError('存在重命名，停止自动同步')
        paths=[line[3:] for line in changed if line]
        blocked=[p for p in paths if not allowed(p,config)]
        if blocked:raise RuntimeError('存在未提交代码或非白名单修改，先人工处理：'+', '.join(blocked[:8]))
        git('fetch','origin',config['branch'])
        before=git('rev-parse','HEAD')
        if before!=git('rev-parse','origin/'+config['branch']):raise RuntimeError('远端已有更新或本地未同步提交，停止；不自动合并或丢弃数据')
        if paths:
            for path in paths:
                content=(root/path).read_bytes() if (root/path).is_file() else b''
                if re.search(rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{24,}',content):raise RuntimeError('检测到疑似密钥，停止发布')
                if path=='papers/maritime/library.json':
                    library=json.loads(content)
                    if any(p.get('reading') or any(c.get('field')=='reading' for c in p.get('merge_conflicts',[])) for p in library['papers'].values()):
                        raise RuntimeError('主库含私人阅读记录，停止发布；需先分离私有阅读记录')
            git('add','--',*paths)
            git('commit','-m','Update public paper data and mobile digest')
        sha=git('rev-parse','HEAD')
        git('push','origin',config['branch'])
        result.update(github_sync='success',commit=sha)
        print('GitHub推送成功：'+sha,flush=True)
        if os.environ.get('GITHUB_ACTIONS')=='true':
            result['pages_publish']='workflow_run_pending'
            from services.maritime import write_json
            write_json(root/'papers/maritime/logs/latest-sync.json',result)
            print(json.dumps(result,ensure_ascii=False),flush=True)
            return result
        deadline=time.monotonic()+wait_seconds
        url='https://api.github.com/repos/'+config['repository']+'/actions/runs?head_sha='+sha+'&per_page=20'
        while time.monotonic()<deadline:
            runs=api(url)['workflow_runs']
            run=next((r for r in runs if r.get('path')=='.github/workflows/'+config['pages_workflow']),None)
            if run:
                result['deployment_url']=run['html_url']
                if run['status']=='completed':
                    result['pages_publish']=run['conclusion']
                    break
            time.sleep(20)
        else:result['pages_publish']='pending'
    except Exception as exc:
        result['reason']=str(exc)
        if result['github_sync']!='success':result['github_sync']='stopped'
    from services.maritime import write_json
    write_json(root/'papers/maritime/logs/latest-sync.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return result
