"""Licensed, cached DeepSeek translations for the small AI-reviewed daily selection."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import re
import urllib.request

ALLOWED_LICENSE=re.compile(r'^https?://creativecommons\.org/(?:licenses/(?:by|by-sa)/[34]\.0|publicdomain/zero/1\.0)/?$',re.I)
VERSION=1

def source_license(paper,timeout=8):
    source=paper.get('abstract_source') or {}
    license_url=source.get('license_url','') if isinstance(source,dict) else ''
    if ALLOWED_LICENSE.fullmatch(license_url):return license_url
    aid=paper.get('arxiv_id')
    if not aid:return None
    request=urllib.request.Request('https://arxiv.org/abs/'+aid,headers={'User-Agent':'RS-PaperClaw-Maritime/2.0'})
    try:
        with urllib.request.urlopen(request,timeout=timeout) as response:
            if response.url.rstrip('/')!='https://arxiv.org/abs/'+aid:return None
            page=response.read(400000).decode('utf8','replace')
    except Exception:return None
    marker=re.search(r'<div class="abs-license"[^>]*>',page,re.I)
    match=re.search(r'https?://creativecommons\.org/(?:licenses/[a-z-]+/[34]\.0|publicdomain/zero/1\.0)/?',
                    page[marker.end():marker.end()+400],re.I) if marker else None
    if not match or not ALLOWED_LICENSE.fullmatch(match.group()):return None
    paper['abstract_source']={**source,'sources':source.get('sources',['arXiv']),'url':'https://arxiv.org/abs/'+aid,'license_url':match.group()}
    return match.group()

def valid_translation(english,chinese):
    if not isinstance(chinese,str) or len(chinese.strip())<20:return False
    if re.search(r'保险丝|硬底片|变压器|硬负面|硬负片',chinese):return False
    for source,expected in (('hard negative','困难负样本'),('cross-modal','跨模态'),('contrastive learning','对比学习'),('trajectory association','轨迹关联'),('object detection','目标检测')):
        if source in english.casefold() and expected not in chinese:return False
    if 'Transformer' in english and 'Transformer' not in chinese:return False
    numbers=lambda s:Counter(re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?%?',s))
    if numbers(english)!=numbers(chinese):return False
    terms=set(re.findall(r'\b[A-Z][A-Z0-9+/-]{1,}\b',english))
    return all(term in chinese for term in terms)

def chosen_zh(paper,daily=False):
    english=paper.get('abstract','')
    translation=paper.get('translation') or {}
    if translation.get('status')=='manual' and translation.get('zh'):return translation['zh'],'manual'
    selected=paper.get('selected_translation') or {}
    digest=hashlib.sha256(english.encode()).hexdigest()
    if selected.get('status')=='deepseek' and selected.get('english_hash')==digest and selected.get('version')==VERSION and valid_translation(english,selected.get('zh')):
        return selected['zh'],'deepseek'
    if not daily and translation.get('status')=='machine' and translation.get('english_hash')==digest and valid_translation(english,translation.get('zh')):
        return translation['zh'],'argos'
    return '', 'english_only'

def translate_selected(root,library,day,config=None):
    from clients.deepseek_client import api_key,complete,TZ
    from services.mobile_digest import select_daily
    from services.semantic_evaluation import settings
    config=config or settings()
    chosen,_=select_daily(root,library,day,config=config)
    summary={'selected':len(chosen),'translated':0,'cached':0,'manual':0,'unlicensed':0,'failed':0,'tokens':0,'cost_upper_cny':0.0,'priced_cost_cny':0.0}
    if not config.get('enabled') or not library.get('semantic_enabled',True):return summary
    try:api_key()
    except RuntimeError:
        summary['reason']='DeepSeek key unavailable; existing translations and English retained'
        return summary
    for paper,_,_ in chosen:
        text,status=chosen_zh(paper,daily=True)
        if status=='manual':summary['manual']+=1;continue
        if status=='deepseek':summary['cached']+=1;continue
        license_url=source_license(paper)
        if not license_url:summary['unlicensed']+=1;continue
        prompt={'model':config['model'],'thinking':{'type':'disabled'},'response_format':{'type':'json_object'},'max_tokens':min(2000,config['max_tokens']),
                'messages':[{'role':'system','content':'将英文论文摘要忠实译为学术中文。只返回JSON对象{paper_id,translation_zh}。不得增加原文没有的内容。保留模块、缩写、公式、数据集及全部数字和百分比。cross-modal译为跨模态，contrastive learning译为对比学习，trajectory association译为轨迹关联，object detection译为目标检测，fusion译为融合；fuse不是保险丝，hard negative不是硬底片，Transformer不是变压器。'},
                            {'role':'user','content':json.dumps({'paper_id':paper['paper_id'],'title':paper['title'],'abstract':paper['abstract']},ensure_ascii=False)}]}
        try:
            response,cost=complete(root,prompt,config)
            summary['cost_upper_cny']+=cost;summary['tokens']+=response['usage']['total_tokens']
            created=datetime.fromtimestamp(response['created'],TZ)
            peak=created.weekday()<5 and (9<=created.hour<12 or 14<=created.hour<18)
            summary['priced_cost_cny']+=cost*(1 if peak else .5)
            if response['choices'][0]['finish_reason']!='stop':raise ValueError('Incomplete translation')
            value=json.loads(response['choices'][0]['message']['content'])
            if set(value)!={'paper_id','translation_zh'} or value['paper_id']!=paper['paper_id'] or not valid_translation(paper['abstract'],value['translation_zh']):raise ValueError('Translation consistency check failed')
            paper['selected_translation']={'status':'deepseek','version':VERSION,'english_hash':hashlib.sha256(paper['abstract'].encode()).hexdigest(),
                                           'zh':value['translation_zh'],'license_url':license_url,'updated_at':datetime.now(timezone.utc).isoformat()}
            summary['translated']+=1
        except Exception:
            summary['failed']+=1
    return summary
