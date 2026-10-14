"""Small daily selection using existing eligibility and rank; no new model."""
from datetime import timedelta
import html
import json
from pathlib import Path

BASE = 'https://yyf1170808529-cpu.github.io/RS-PaperClaw/'

def build_mobile_digest(root, library, date):
    from services.maritime import write_json, LEVELS
    from services.maritime_v2 import assets, recommendation_view, rank_key, compact_source
    from services.semantic_evaluation import ranking_info,settings
    semantic_settings=settings()
    directory=root/'docs/maritime-data/mobile'
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/(str(date)+'.json')
    seen=set()
    # Today's own file is replaceable. Previous days are never overwritten.
    for path in directory.glob('????-??-??.json'):
        if str(date-timedelta(days=7))<=path.stem<str(date):
            seen.update(p['paper_id'] for p in json.loads(path.read_text(encoding='utf8'))['papers'])
    _,policy=assets()
    ids=recommendation_view(list(library['papers'].values()),policy,date)['paper_ids']
    use_ai=library.get('semantic_enabled',True) and semantic_settings['mobile_ai_enabled']
    info=lambda p:ranking_info(p,semantic_settings) if use_ai else {'score':None,'demoted':False,'reason':None}
    chosen=[library['papers'][k] for k in ids if k not in seen and library['papers'][k].get('abstract') and not info(library['papers'][k])['demoted']]
    # Keep today's existing choices stable during repeat builds if still eligible.
    old=json.loads(target.read_text(encoding='utf8'))['papers'] if target.exists() else []
    chosen_ids={p['paper_id'] for p in chosen}
    stable=[library['papers'][p['paper_id']] for p in old if p['paper_id'] in chosen_ids]
    order=lambda p:(info(p)['score'] if info(p)['score'] is not None else 50,rank_key(p))
    pool=sorted(chosen,key=order,reverse=True)
    # Same-day repeat builds stay stable unless new valid AI evidence is available.
    if not any(info(p)['score'] is not None for p in chosen):pool=stable+[p for p in pool if p['paper_id'] not in {s['paper_id'] for s in stable}]
    choices=[];counts={k:0 for k in policy['quotas']};total=sum(policy['quotas'].values())
    while pool and len(choices)<5:
        available={p['recommendation']['bucket'] for p in pool}
        bucket=max((k for k in counts if k in available),key=lambda k:(policy['quotas'][k]/total*(len(choices)+1)-counts[k],policy['quotas'][k]))
        candidate=next(p for p in pool if p['recommendation']['bucket']==bucket)
        choices.append(candidate);counts[bucket]+=1;pool.remove(candidate)
    items=[]
    for p in choices:
        bucket=p['recommendation']['bucket']
        reason={'water':'海事感知方向；已核验一区/Q1正式期刊','land':'陆上感知强相关；符合当前来源门槛','general':'通用方法与感知任务强相关；符合当前来源门槛'}[bucket]
        topic=p.get('assessment',{}).get('primary_topic')
        reason=info(p)['reason'] or reason+(f'；专题{topic}' if topic else '')
        items.append({'paper_id':p['paper_id'],'title':p['title'],'source':compact_source(p),'reason':reason,
                      'original_url':p.get('original_url') or p.get('arxiv_url'),'reading_url':BASE+'maritime.html?paper='+p['paper_id'],
                      'score':p.get('assessment',{}).get('score',0),'level':LEVELS.get(p.get('assessment',{}).get('level'),'待评估'),
                      'ai_score':info(p)['score'],
                      'abstract':p.get('abstract') or '', 'abstract_zh':p.get('translation',{}).get('zh','') if p.get('translation',{}).get('status') in ('machine','manual') else ''})
    payload={'date':str(date),'notice':'规则推荐供阅读参考，不评价真实创新性；7天内避免重复，质量不足不凑数','papers':items}
    write_json(target,payload)
    write_json(directory/'latest.json',payload)
    esc=html.escape
    entries=''.join(f'<article><h2>{esc(p["title"])}</h2><p>{esc(p["source"])}</p><p>推荐评分：{p["score"]} · {esc(p["level"])}'+(f' · AI相关分 {p["ai_score"]}/100' if p['ai_score'] is not None else '')+f'</p><p>{esc(p["reason"])}</p><details><summary>查看摘要（中文 / English）</summary><p>{esc(p["abstract_zh"] or "中文译文暂未完成，先看下方英文摘要。")}</p><p lang="en">{esc(p["abstract"] or "英文摘要暂未获取。")}</p></details><p><a href="{esc(p["original_url"] or "",quote=True)}">原文</a> · <a href="{esc(p["reading_url"],quote=True)}">阅读与笔记</a></p></article>' for p in items)
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>每日精选 {date}</title><style>body{{max-width:720px;margin:auto;padding:18px;font:16px/1.6 system-ui;background:#fffbf5;color:#2d2419}}h2{{font-size:18px}}article{{border-top:1px solid #ddd;padding:12px 0}}a{{color:#a54f2b}}p{{overflow-wrap:anywhere}}</style><h1>每日精选 {date}</h1>{entries or "<p>今天暂无新的合格精选。</p>"}<p><a href="maritime.html">完整论文库</a></p></html>'
    (root/'docs/maritime-daily.html').write_text(page,encoding='utf8')
    (directory/(str(date)+'.html')).write_text(page.replace('href="maritime.html"','href="../../maritime.html"'),encoding='utf8')
    markdown=f'# 每日精选 {date}\n\n'+ '\n\n'.join(f'## {p["title"]}\n\n{p["source"]}\n\n{p["reason"]}\n\n[原文]({p["original_url"]}) · [阅读页]({p["reading_url"]})' for p in items)
    (directory/(str(date)+'.md')).write_text(markdown,encoding='utf8')
    return payload
