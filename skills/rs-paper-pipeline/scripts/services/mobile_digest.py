"""Small daily selection using existing eligibility and rank; no new model."""
from datetime import date as calendar_date, timedelta
import html
import json
import hashlib
from pathlib import Path
from urllib.parse import quote

BASE = 'https://yyf1170808529-cpu.github.io/RS-PaperClaw/'

PROMPT_FIELDS=('paper_id','title','authors','published','arxiv_url','doi','original_url',
               'pdf_url','open_access_url','venue','abstract','resource_type')

def prompt_metadata(paper, papers=None, aliases=None):
    """Small public snapshot; enrich legacy archives only by their own stable identity."""
    key=(aliases or {}).get(paper['paper_id'],paper['paper_id'])
    original=(papers or {}).get(key,{})
    values={field:paper.get(field) or original.get(field) or '' for field in PROMPT_FIELDS}
    values['authors']=values['authors'] if isinstance(values['authors'],list) else []
    values['oa_evidence']=bool(paper.get('oa_evidence') or original.get('oa_evidence'))
    values['validity']={'status':(paper.get('validity') or original.get('validity') or {}).get('status')}
    for field in ('first_author','first_author_affiliations','affiliation_source','affiliation_verified','affiliation_evidence'):
        values[field]=paper[field] if field in paper else original.get(field)
    return values

def archive_mobile_page(page):
    return page.replace('href="maritime.html?', 'href="../../maritime.html?').replace('href="maritime-daily.html?', 'href="../../maritime-daily.html?').replace('src="maritime_', 'src="../../maritime_')

def refresh_mobile_pages(root, library):
    """Upgrade saved HTML only: do not reselect, translate or change archived JSON."""
    directory=root/'docs/maritime-data/mobile'
    count=0
    for path in sorted(directory.glob('????-??-??.json')):
        payload=json.loads(path.read_text(encoding='utf8'))
        page=render_mobile_page(payload,library.get('aliases',{}),library['papers'])
        path.with_suffix('.html').write_text(archive_mobile_page(page),encoding='utf8')
        count+=1
    latest=directory/'latest.json'
    if latest.exists():
        payload=json.loads(latest.read_text(encoding='utf8'))
        (root/'docs/maritime-daily.html').write_text(render_mobile_page(payload,library.get('aliases',{}),library['papers']),encoding='utf8')
    return count

def digest_revision(payload):
    return hashlib.sha256(json.dumps({'date':payload['date'],'papers':payload['papers']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]

def refresh_reserve(root,library,day,config=None):
    """Persist verified identities and push history; always revalidate before use."""
    from services.semantic_evaluation import ranking_info,settings,fingerprint
    from services.maritime import read_json,write_json
    config=config or settings()
    path=root/'docs/maritime-data/ai-reserve.json'
    records=read_json(path,{'records':{}})['records']
    from services.mobile_history import PublishedHistory
    history=PublishedHistory(root,library)
    for key,p in library['papers'].items():
        info=ranking_info(p,config)
        if not info['eligible'] or not hard_eligible(p):
            if key in records:records[key].update(qualified=False,available=False,pushed_dates=sorted(history.pushed_dates(p)))
            continue
        dates=sorted(history.pushed_dates(p))
        records[key]={'paper_id':key,'fingerprint':fingerprint(p,config),'review_version':2,
                      'qualified':not dates,'pushed_dates':dates,'available':not dates}
    for key in set(records)-set(library['papers']):records[key].update(qualified=False,available=False)
    payload={'as_of':str(day),'target':config.get('reserve_target',15),'records':records,
             'available_count':sum(r['qualified'] and r.get('available',False) for r in records.values())}
    write_json(path,payload)
    return payload

def review_bucket(p):
    application=p.get('application_bucket')
    if application=='water' or p.get('recommendation',{}).get('application')=='maritime':return 'water'
    bucket=p.get('recommendation',{}).get('bucket')
    return bucket if bucket in ('water','land','general') else 'land' if application=='land' else 'general'

def hard_eligible(p):
    r=p.get('recommendation',{});q=p.get('quality',{});bucket=review_bucket(p)
    if p.get('validity',{}).get('status') in ('deleted','withdrawn','invalid'):
        return False
    if not p.get('abstract') or p.get('abstract_quality',{}).get('status') in ('review','missing'):
        return False
    kind=p.get('resource_type')
    # A maritime preprint can be placed in a cross-domain bucket by older rules;
    # that placement must not bypass the existing water publication threshold.
    if p.get('application_bucket')=='water' or r.get('application')=='maritime':
        return kind=='journal_article' and bool(q.get('high_journal'))
    if bucket=='water':return kind=='journal_article' and bool(q.get('high_journal'))
    # Keyword scores determine review priority, not the final AI publication gate.
    return bool((kind=='journal_article' and q.get('high_journal')) or
                (kind=='conference_paper' and q.get('ccf_a')) or
                (kind=='preprint' and p.get('publication_status')!='published'))

def candidate_pool(root,library,day,new_keys=()):
    """Ordered stages for both the desktop and cloud update paths."""
    from services.semantic_evaluation import direct_task,ranking_info
    from services.mobile_history import PublishedHistory
    history=PublishedHistory(root,library)
    newly=set(new_keys)
    rows=[]
    for p in library['papers'].values():
        key=p['paper_id']
        if history.prior(p,day) or not hard_eligible(p):continue
        if p.get('assessment',{}).get('level')=='excluded' and not direct_task(p) and not ranking_info(p)['eligible']:continue
        raw=p.get('publication_date') or p.get('published') or ''
        try:published=calendar_date.fromisoformat(raw[:10] if len(raw)>=10 else raw[:7]+'-01')
        except ValueError:published=None
        age=(day-published).days if published else 99999
        stage=0 if key in newly or p.get('discovery_date')==str(day) else 1 if 0<=age<=7 else 2 if 0<=age<=90 else 3
        rows.append((p,stage))
    from services.maritime_v2 import rank_key
    from services.semantic_evaluation import ranking_info,direct_task
    ordered=sorted(rows,key=lambda row:(ranking_info(row[0])['eligible'],-row[1],direct_task(row[0]),rank_key(row[0])),reverse=True)
    unique=[];seen=set()
    for row in ordered:
        key=history.canonical(row[0])
        if key not in seen:unique.append(row);seen.add(key)
    return unique

def select_daily(root,library,day,new_keys=(),config=None):
    from services.maritime_v2 import assets,rank_key
    from services.semantic_evaluation import ranking_info,settings
    config=config or settings()
    candidates=candidate_pool(root,library,day,new_keys)
    eligible=[(p,stage,ranking_info(p,config)) for p,stage in candidates]
    eligible=[row for row in eligible if row[2]['state']=='evaluated' and row[2]['eligible']]
    _,policy=assets();quotas=policy['quotas'];total=sum(quotas.values())
    today=root/'docs/maritime-data/mobile'/(str(day)+'.json')
    saved=json.loads(today.read_text(encoding='utf8')) if today.exists() else {}
    from services.mobile_history import PublishedHistory
    history=PublishedHistory(root,library)
    retained={history.canonical(p) for p in saved.get('papers',[])}
    chosen=[row for row in eligible if history.canonical(row[0]) in retained][:5]
    counts={k:sum(review_bucket(row[0])==k for row in chosen) for k in quotas}
    chosen_ids={row[0]['paper_id'] for row in chosen}
    for stage in range(4):
        pool=sorted((row for row in eligible if row[1]==stage and row[0]['paper_id'] not in chosen_ids),key=lambda row:(row[2]['score'],rank_key(row[0])),reverse=True)
        while pool and len(chosen)<5:
            available={review_bucket(row[0]) for row in pool}
            bucket=max((k for k in quotas if k in available),key=lambda k:(quotas[k]/total*(len(chosen)+1)-counts[k],quotas[k]))
            row=next(row for row in pool if review_bucket(row[0])==bucket)
            chosen.append(row);counts[bucket]+=1;pool.remove(row)
        if len(chosen)==5:break
    from collections import Counter
    states=Counter(ranking_info(p,config)['state'] for p,_ in candidates)
    return chosen,{'candidate_count':len(candidates),'ai_reviewed':states['evaluated'],
                   'ai_states':dict(states),'stage_counts':dict(Counter(str(s) for _,s in candidates)),
                   'ai_rejected':states['evaluated']-len(eligible),
                   'qualified_count':len(eligible),'selected_count':len(chosen),'shortfall':max(0,5-len(chosen))}

def build_mobile_digest(root, library, date):
    from services.maritime import write_json, LEVELS
    from services.maritime_v2 import compact_source
    from services.semantic_evaluation import settings
    from services.selected_translation import chosen_zh,translation_issue
    semantic_settings=settings()
    directory=root/'docs/maritime-data/mobile'
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/(str(date)+'.json')
    config=semantic_settings if library.get('semantic_enabled',True) and semantic_settings.get('mobile_ai_enabled') else {**semantic_settings,'enabled':False}
    choices,audit=select_daily(root,library,date,config=config)
    items=[]
    for p,stage,assessment in choices:
        bucket=review_bucket(p)
        reason={'water':'海事感知方向；已核验一区/Q1正式期刊','land':'陆上感知强相关；符合当前来源门槛','general':'通用方法与感知任务强相关；符合当前来源门槛'}[bucket]
        topic=p.get('assessment',{}).get('primary_topic')
        reason=assessment['reason'] or reason+(f'；专题{topic}' if topic else '')
        final_level='直接相关' if assessment['path']=='direct' else '方法值得关注'
        items.append({**prompt_metadata(p),'paper_id':p['paper_id'],'title':p['title'],'source':compact_source(p),'reason':reason,
                      'original_url':p.get('original_url') or p.get('arxiv_url'),'reading_url':BASE+'maritime.html?paper='+quote(p['paper_id'],safe=''),
                      'score':p.get('assessment',{}).get('score',0),'rule_level':LEVELS.get(p.get('assessment',{}).get('level'),'待评估'),'level':final_level,
                      'ai_score':assessment['score'],'selection_source':'近期新论文' if stage==0 else '历史补荐' if stage==3 else '近期候选',
                      'abstract':p.get('abstract') or '', 'abstract_zh':chosen_zh(p,daily=True)[0],'translation_source':chosen_zh(p,daily=True)[1],
                      'translation_error':translation_issue(p)})
    environment_errors=[p['paper_id'] for p,_,_ in choices
                        if not chosen_zh(p,daily=True)[0] and p.get('translation',{}).get('error_type') in
                        ('dependency_missing','model_missing','model_runtime_error')]
    audit['translation_environment_errors']=environment_errors
    audit['translation_errors']=[{'paper_id':p['paper_id'],'reason':p['translation_error'] or '尚无有效中文译文'} for p in items if not p['abstract_zh']]
    status='complete' if len(items)==5 and not audit['translation_errors'] else 'partial' if items else 'failed'
    payload={'date':str(date),'papers':items,'selection_audit':audit,'publication_status':status}
    # Pending batches are recoverable but never count as previously pushed papers.
    pending_path=directory/'pending'/target.name
    prior=json.loads(pending_path.read_text(encoding='utf8')) if pending_path.exists() else {}
    retained={p['paper_id']:p for p in prior.get('reserve_papers',prior.get('papers',[]))}
    retained.update({p['paper_id']:p for p in items})
    write_json(pending_path,{**payload,'reserve_papers':list(retained.values())})
    if status!='complete':
        previous=[]
        for path in directory.glob('????-??-??.json'):
            if path.stem>str(date):continue
            try:
                saved=json.loads(path.read_text(encoding='utf8'))
                if len(saved.get('papers',[]))!=5 or len({p['paper_id'] for p in saved['papers']})!=5:continue
                if not all(isinstance(p.get('ai_score'),(int,float)) for p in saved['papers']):continue
                # Legacy complete archives were published by the strict V3.7 gate.
                if saved.get('publication_status','complete')!='complete':continue
                if not all(p.get('abstract_zh') for p in saved['papers']):continue
                previous.append(saved)
            except (ValueError,KeyError,TypeError):continue
        published=max(previous,key=lambda p:p['date']) if previous else None
    else:
        write_json(target,payload)
        published=payload
    payload['published_date']=published['date'] if published else None
    write_json(directory/'publication-status.json',{'attempt_date':str(date),'status':status,
               'published_date':payload['published_date'],'published_revision':digest_revision(published) if published else None,'selection_audit':audit})
    refresh_reserve(root,library,date,config)
    if published:
        write_json(directory/'latest.json',published)
        (root/'docs/maritime-daily.html').write_text(render_mobile_page(published,library.get('aliases',{}),library['papers']),encoding='utf8')
    if status!='complete':return payload
    page=render_mobile_page(payload,library.get('aliases',{}))
    (directory/(str(date)+'.html')).write_text(archive_mobile_page(page),encoding='utf8')
    markdown=f'# 每日精选 {date}\n\n'+ '\n\n'.join(f'## {p["title"]}\n\n{p["source"]}\n\n{p["reason"]}\n\n[原文]({p["original_url"]}) · [阅读页]({p["reading_url"]})' for p in items)
    (directory/(str(date)+'.md')).write_text(markdown,encoding='utf8')
    return payload


def render_mobile_page(payload, aliases=None, papers=None):
    """Render saved picks without retrieving, ranking or translating papers."""
    esc=html.escape
    date=payload['date'];items=payload['papers']
    def score_label(p):
        return ' · AI相关分 '+str(p['ai_score'])+'/100' if isinstance(p.get('ai_score'),(int,float)) else ''
    def author_label(p):
        metadata=prompt_metadata(p,papers,aliases)
        authors=metadata['authors']
        label='<p>作者：'+esc('、'.join(authors[:5]) or '待核实')+'</p>'
        if len(authors)>5:label+='<details><summary>查看全部作者</summary><p>'+esc('、'.join(authors))+'</p></details>'
        from services.maritime_v2 import normalized_identity
        verified=metadata.get('affiliation_verified') and metadata.get('affiliation_source') and authors and normalized_identity(metadata.get('first_author'))==normalized_identity(authors[0])
        affiliations=metadata.get('first_author_affiliations') or []
        label+='<p>第一作者单位：'+esc(affiliations[0] if verified and affiliations else '待核实')
        if verified and affiliations:label+=' <small>（'+esc(metadata['affiliation_source'])+'）</small>'
        return label+'</p>'
    entries=''.join(f'<article><h2>{esc(p["title"])}</h2>{author_label(p)}<p>{esc(p["source"])}</p><p>{esc(p["level"])}{score_label(p)} {esc(p.get("selection_source",""))}</p><p>{esc(p["reason"])}</p><details><summary>查看摘要（中文 / English）</summary><p>{esc(p["abstract_zh"] or "本地中文翻译未完成：" + p.get("translation_error", "尚未生成") + "。英文摘要保留如下。")}</p><p lang="en">{esc(p["abstract"] or "英文摘要暂未获取。")}</p></details><div class="paper-actions"><a href="{esc(p["original_url"] or "",quote=True)}">原文</a><span>·</span><a href="{esc(p["reading_url"]+("&" if "?" in p["reading_url"] else "?")+"v=3.8.1",quote=True)}">阅读与笔记</a><span>·</span><button type="button" data-prompt-paper="{esc(p["paper_id"],quote=True)}">Prompt</button><span>·</span><span data-favorite-inline="1" data-favorite-paper="{esc(p["paper_id"],quote=True)}"></span></div><div class="paper-panels" data-paper-panels="{esc(p["paper_id"],quote=True)}"></div></article>' for p in items)
    snapshots={'date':date,'revision':digest_revision(payload),'papers':[{k:p.get(k,'') for k in ('paper_id','title','original_url','reading_url')} for p in items],'aliases':aliases or {}}
    data=json.dumps(snapshots,ensure_ascii=False).replace('<',r'\u003c')
    template=(Path(__file__).resolve().parents[1]/'prompts/maritime_analysis.md').read_text(encoding='utf8')
    prompts=json.dumps({'prompt_template':template,'papers':[prompt_metadata(p,papers,aliases) for p in items]},ensure_ascii=False).replace('<',r'\u003c')
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>每日精选 {date}</title><style>body{{max-width:720px;margin:auto;padding:18px;font:16px/1.6 system-ui;background:#fffbf5;color:#2d2419}}h2{{font-size:18px}}article{{border-top:1px solid #ddd;padding:12px 0}}a{{color:#a54f2b}}p{{overflow-wrap:anywhere}}button,input,textarea{{font:inherit;background:#fffbf5;border:1px solid #aaa;border-radius:4px;padding:6px;margin:3px}}textarea{{width:95%}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}.paper-actions{{display:flex;align-items:center;flex-wrap:nowrap;gap:5px;font-size:14px;white-space:nowrap;min-width:0}}.paper-actions button{{border:0;padding:0;margin:0;background:none;color:#a54f2b;white-space:nowrap}}.paper-actions [data-favorite-paper]{{display:inline-flex}}.paper-panels textarea{{box-sizing:border-box;max-width:100%}}input[type=file]{{display:block;max-width:100%;width:100%;box-sizing:border-box;margin:3px 0}}@media(max-width:360px){{.paper-actions{{font-size:12px;gap:3px}}}}</style><nav><a href="maritime-daily.html?v=3.8.1">每日精选</a> | <a href="maritime.html?v=3.8.1">完整论文库</a> | <a href="maritime.html?view=favorites&amp;v=3.8.1">我的收藏</a></nav><h1>每日精选 {date}</h1><div id="daily-favorites" aria-label="收藏导出与恢复"></div><p id="favorite-message" role="status"></p>{entries or "<p>今天没有完成AI审核的合格精选。</p>"}<p>收藏和笔记仅保存在当前浏览器。Safari、Chrome、应用内浏览器及不同设备默认不共享；请用同一浏览器打开，或导出/导入 JSON。</p><script id="daily-favorites-data" type="application/json">{data}</script><script src="maritime_favorites.js?v=3.8.3"></script><script id="daily-prompt-data" type="application/json">{prompts}</script><script src="maritime_prompt.js?v=3.8.2"></script><script src="maritime_daily_prompt.js?v=3.8.3"></script></html>'''
