"""Official API only; environment credentials and conservative paid-request ledger."""
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import urllib.request
from urllib.error import HTTPError

BASE='https://api.deepseek.com'
TZ=timezone(timedelta(hours=8))

def api_key():
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key and os.name=='nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as handle:key=winreg.QueryValueEx(handle,'DEEPSEEK_API_KEY')[0]
        except OSError:pass
    if not key:raise RuntimeError('DEEPSEEK_API_KEY is not configured')
    return key

def request(path, payload=None, timeout=60):
    body=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
    req=urllib.request.Request(BASE+path,data=body,headers={'Authorization':'Bearer '+api_key(),'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'DeepSeek HTTP {exc.code}; no automatic paid retry') from None
    except Exception as exc:
        raise RuntimeError('DeepSeek request failed: '+type(exc).__name__+'; billing may be uncertain') from None

def balance():
    result=request('/user/balance')
    return next((b for b in result.get('balance_infos',[]) if b.get('currency')=='CNY'),None)

def complete(root, payload, config):
    from services.maritime import read_json,write_json
    from update_maritime import update_lock
    path=root/'papers/maritime/private/deepseek/usage.json'
    lock=path.with_suffix('.lock')
    day=str(datetime.now(TZ).date())
    prices=config['pricing']['peak_cny_per_million']
    # UTF-8 byte count bounds the text token count; JSON adds further margin.
    ceiling=(len(json.dumps(payload,ensure_ascii=False).encode())*prices['cache_miss']+payload['max_tokens']*prices['output'])/1e6
    with update_lock(lock):
        ledger=read_json(path,{'days':{}})
        account=ledger['days'].setdefault(day,{'charged_upper_cny':0,'reserved_cny':0,'requests':[]})
        if account['charged_upper_cny']+account['reserved_cny']+ceiling>config['daily_budget_cny']:
            raise RuntimeError('Daily DeepSeek budget reached; ordinary archive unchanged')
        account['reserved_cny']+=ceiling
        account['requests'].append({'status':'pending','reservation_cny':ceiling})
        index=len(account['requests'])-1
        write_json(path,ledger)
    try:
        result=request('/chat/completions',payload,config['timeout_seconds'])
        usage=result.get('usage',{})
        prompt=usage.get('prompt_tokens'); output=usage.get('completion_tokens')
        if not isinstance(prompt,int) or not isinstance(output,int):raise RuntimeError('Missing usage; reservation retained')
        hit=usage.get('prompt_cache_hit_tokens',0)
        miss=usage.get('prompt_cache_miss_tokens',prompt-hit)
        if any(not isinstance(v,int) or v<0 for v in (hit,miss,output)) or hit+miss!=prompt:
            raise RuntimeError('Invalid usage; reservation retained')
        charged=(hit*prices['cache_hit']+miss*prices['cache_miss']+output*prices['output'])/1e6
        with update_lock(lock):
            ledger=read_json(path,{})
            account=ledger['days'][day]
            account['reserved_cny']=max(0,account['reserved_cny']-ceiling)
            account['charged_upper_cny']+=charged
            account['requests'][index]={'status':'completed','id':result.get('id'),'model':result.get('model'),
                'created':result.get('created'),'usage':usage,'cost_upper_cny':charged,'reservation_cny':ceiling}
            write_json(path,ledger)
        return result,charged
    except Exception:
        # An interrupted POST can have been billed. Keep its worst-case reservation.
        with update_lock(lock):
            ledger=read_json(path,{})
            ledger['days'][day]['requests'][index]['status']='uncertain'
            write_json(path,ledger)
        raise
