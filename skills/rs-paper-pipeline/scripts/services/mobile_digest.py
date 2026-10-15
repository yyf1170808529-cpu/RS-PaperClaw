"""Small daily selection using existing eligibility and rank; no new model."""
from datetime import date as calendar_date, timedelta
import html
import json
from pathlib import Path
from urllib.parse import quote

BASE = 'https://yyf1170808529-cpu.github.io/RS-PaperClaw/'

def hard_eligible(p):
    r=p.get('recommendation',{});q=p.get('quality',{});bucket=r.get('bucket')
    if bucket not in ('water','land','general') or p.get('validity',{}).get('status') in ('deleted','withdrawn','invalid'):
        return False
    if not p.get('abstract') or p.get('abstract_quality',{}).get('status') in ('review','missing'):
        return False
    kind=p.get('resource_type')
    if bucket=='water':return kind=='journal_article' and bool(q.get('high_journal'))
    if p.get('assessment',{}).get('level')!='high' or r.get('low_priority'):return False
    return bool((kind=='journal_article' and q.get('high_journal')) or
                (kind=='conference_paper' and q.get('ccf_a')) or
                (kind=='preprint' and p.get('publication_status')!='published'))

def candidate_pool(root,library,day,new_keys=()):
    """Ordered stages for both the desktop and cloud update paths."""
    directory=root/'docs/maritime-data/mobile'
    recent=set();ever=set();aliases=library.get('aliases',{})
    for path in directory.glob('????-??-??.json'):
        if path.stem>=str(day) or path.name=='latest.json':continue
        try:ids=[aliases.get(x['paper_id'],x['paper_id']) for x in json.loads(path.read_text(encoding='utf8'))['papers']]
        except (ValueError,KeyError,TypeError):continue
        ever.update(ids)
        if str(day-timedelta(days=7))<=path.stem:recent.update(ids)
    newly=set(new_keys)
    rows=[]
    for p in library['papers'].values():
        key=p['paper_id']
        if key in recent or not hard_eligible(p):continue
        raw=p.get('publication_date') or p.get('published') or ''
        try:published=calendar_date.fromisoformat(raw[:10] if len(raw)>=10 else raw[:7]+'-01')
        except ValueError:published=None
        age=(day-published).days if published else 99999
        stage=0 if key in newly or p.get('discovery_date')==str(day) else 1 if 0<=age<=7 else 2 if 0<=age<=90 else 3
        if stage==3 and key in ever:continue
        rows.append((p,stage))
    from services.maritime_v2 import rank_key
    return sorted(rows,key=lambda row:(-row[1],rank_key(row[0])),reverse=True)

def select_daily(root,library,day,new_keys=(),config=None):
    from services.maritime_v2 import assets,rank_key
    from services.semantic_evaluation import ranking_info,settings
    config=config or settings()
    candidates=candidate_pool(root,library,day,new_keys)
    eligible=[(p,stage,ranking_info(p,config)) for p,stage in candidates]
    eligible=[row for row in eligible if row[2]['state']=='evaluated' and row[2]['eligible']]
    _,policy=assets();quotas=policy['quotas'];total=sum(quotas.values())
    chosen=[];counts={k:0 for k in quotas}
    for stage in range(4):
        pool=sorted((row for row in eligible if row[1]==stage),key=lambda row:(row[2]['score'],rank_key(row[0])),reverse=True)
        while pool and len(chosen)<5:
            available={row[0]['recommendation']['bucket'] for row in pool}
            bucket=max((k for k in quotas if k in available),key=lambda k:(quotas[k]/total*(len(chosen)+1)-counts[k],quotas[k]))
            row=next(row for row in pool if row[0]['recommendation']['bucket']==bucket)
            chosen.append(row);counts[bucket]+=1;pool.remove(row)
        if len(chosen)==5:break
    return chosen,{'candidate_count':len(candidates),'ai_reviewed':sum(ranking_info(p,config)['state']=='evaluated' for p,_ in candidates),
                   'qualified_count':len(eligible),'selected_count':len(chosen),'shortfall':max(0,5-len(chosen))}

def build_mobile_digest(root, library, date):
    from services.maritime import write_json, LEVELS
    from services.maritime_v2 import compact_source
    from services.semantic_evaluation import settings
    from services.selected_translation import chosen_zh
    semantic_settings=settings()
    directory=root/'docs/maritime-data/mobile'
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/(str(date)+'.json')
    config=semantic_settings if library.get('semantic_enabled',True) and semantic_settings.get('mobile_ai_enabled') else {**semantic_settings,'enabled':False}
    choices,audit=select_daily(root,library,date,config=config)
    items=[]
    for p,stage,assessment in choices:
        bucket=p['recommendation']['bucket']
        reason={'water':'海事感知方向；已核验一区/Q1正式期刊','land':'陆上感知强相关；符合当前来源门槛','general':'通用方法与感知任务强相关；符合当前来源门槛'}[bucket]
        topic=p.get('assessment',{}).get('primary_topic')
        reason=assessment['reason'] or reason+(f'；专题{topic}' if topic else '')
        final_level='直接相关' if assessment['path']=='direct' else '方法值得关注'
        items.append({'paper_id':p['paper_id'],'title':p['title'],'source':compact_source(p),'reason':reason,
                      'original_url':p.get('original_url') or p.get('arxiv_url'),'reading_url':BASE+'maritime.html?paper='+quote(p['paper_id'],safe=''),
                      'score':p.get('assessment',{}).get('score',0),'rule_level':LEVELS.get(p.get('assessment',{}).get('level'),'待评估'),'level':final_level,
                      'ai_score':assessment['score'],'selection_source':'近期新论文' if stage==0 else '历史补荐' if stage==3 else '近期候选',
                      'abstract':p.get('abstract') or '', 'abstract_zh':chosen_zh(p,daily=True)[0],'translation_source':chosen_zh(p,daily=True)[1]})
    payload={'date':str(date),'papers':items,'selection_audit':audit}
    write_json(target,payload)
    write_json(directory/'latest.json',payload)
    esc=html.escape
    entries=''.join(f'<article><h2>{esc(p["title"])}</h2><p>{esc(p["source"])}</p><p>{esc(p["level"])} · AI相关分 {p["ai_score"]}/100 · {esc(p["selection_source"])}</p><p>{esc(p["reason"])}</p><details><summary>查看摘要（中文 / English）</summary><p>{esc(p["abstract_zh"] or "中文译文暂未完成，先看下方英文摘要。")}</p><p lang="en">{esc(p["abstract"] or "英文摘要暂未获取。")}</p></details><p><a href="{esc(p["original_url"] or "",quote=True)}">原文</a> · <a href="{esc(p["reading_url"],quote=True)}">阅读与笔记</a> · <button data-paper-id="{esc(p["paper_id"],quote=True)}">收藏</button></p></article>' for p in items)
    bookmark_script="""<script>const key='rs-paperclaw-maritime-readings-v1';let saved;try{saved=JSON.parse(localStorage.getItem(key)||'{"schema_version":1,"readings":{}}');if(saved.schema_version!==1||!saved.readings||typeof saved.readings!=='object'||Array.isArray(saved.readings))throw Error('bad backup')}catch{saved=null}for(const button of document.querySelectorAll('button[data-paper-id]')){const id=button.dataset.paperId;const update=()=>button.textContent=saved?.favorites?.includes(id)?'取消收藏':'收藏';update();button.onclick=()=>{if(!saved){alert('本地备份格式异常，请到完整论文库导出并修复');return}const favorites=new Set(saved.favorites||[]);if(favorites.has(id))favorites.delete(id);else favorites.add(id);const next={...saved,favorites:[...favorites]};try{localStorage.setItem(key,JSON.stringify(next));saved=next;update()}catch{alert('收藏保存失败')}}}</script>"""
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>每日精选 {date}</title><style>body{{max-width:720px;margin:auto;padding:18px;font:16px/1.6 system-ui;background:#fffbf5;color:#2d2419}}h2{{font-size:18px}}article{{border-top:1px solid #ddd;padding:12px 0}}a{{color:#a54f2b}}p{{overflow-wrap:anywhere}}button{{font:inherit;background:#fffbf5;border:1px solid #aaa;border-radius:4px}}</style><nav><a href="maritime-daily.html">每日精选</a> | <a href="maritime.html">完整论文库</a></nav><h1>每日精选 {date}</h1>{entries or "<p>今天没有完成AI审核的合格精选。</p>"}<p>收藏仅保存在本浏览器；换设备请在完整论文库导出、导入备份。</p>{bookmark_script}</html>'
    (root/'docs/maritime-daily.html').write_text(page,encoding='utf8')
    (directory/(str(date)+'.html')).write_text(page.replace('href="maritime.html"','href="../../maritime.html"').replace('href="maritime-daily.html"','href="../../maritime-daily.html"'),encoding='utf8')
    markdown=f'# 每日精选 {date}\n\n'+ '\n\n'.join(f'## {p["title"]}\n\n{p["source"]}\n\n{p["reason"]}\n\n[原文]({p["original_url"]}) · [阅读页]({p["reading_url"]})' for p in items)
    (directory/(str(date)+'.md')).write_text(markdown,encoding='utf8')
    return payload
