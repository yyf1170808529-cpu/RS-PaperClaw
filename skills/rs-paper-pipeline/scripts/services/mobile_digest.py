"""Small daily selection using existing eligibility and rank; no new model."""
from datetime import timedelta
import html
import json
from pathlib import Path

BASE = 'https://yyf1170808529-cpu.github.io/RS-PaperClaw/'

def build_mobile_digest(root, library, date):
    from services.maritime import write_json
    from services.maritime_v2 import assets, recommendation_view, rank_key, compact_source
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
    chosen=[library['papers'][k] for k in ids if k not in seen]
    # Keep today's existing choices stable during repeat builds if still eligible.
    old=json.loads(target.read_text(encoding='utf8'))['papers'] if target.exists() else []
    stable=[library['papers'][p['paper_id']] for p in old if p['paper_id'] in ids and p['paper_id'] not in seen]
    choices=(stable+[p for p in sorted(chosen,key=lambda p:(p.get('application_bucket')=='water',rank_key(p)),reverse=True) if p['paper_id'] not in {s['paper_id'] for s in stable}])[:5]
    items=[]
    for p in choices:
        bucket=p['recommendation']['bucket']
        reason={'water':'海事感知方向；已核验一区/Q1正式期刊','land':'陆上感知强相关；符合当前来源门槛','general':'通用方法与感知任务强相关；符合当前来源门槛'}[bucket]
        topic=p.get('assessment',{}).get('primary_topic')
        items.append({'paper_id':p['paper_id'],'title':p['title'],'source':compact_source(p),'reason':reason+(f'；专题{topic}' if topic else ''),
                      'original_url':p.get('original_url') or p.get('arxiv_url'),'reading_url':BASE+'maritime.html?paper='+p['paper_id'],
                      'abstract':p.get('abstract') or '', 'abstract_zh':p.get('translation',{}).get('zh','') if p.get('translation',{}).get('status') in ('machine','manual') else ''})
    payload={'date':str(date),'notice':'规则推荐供阅读参考，不评价真实创新性；7天内避免重复，质量不足不凑数','papers':items}
    write_json(target,payload)
    write_json(directory/'latest.json',payload)
    esc=html.escape
    entries=''.join(f'<article><h2>{esc(p["title"])}</h2><p>{esc(p["source"])}</p><p>{esc(p["reason"])}</p><details><summary>查看摘要（中文 / English）</summary><p>{esc(p["abstract_zh"] or "中文译文暂未完成，先看下方英文摘要。")}</p><p lang="en">{esc(p["abstract"] or "英文摘要暂未获取。")}</p></details><p><a href="{esc(p["original_url"] or "",quote=True)}">原文</a> · <a href="{esc(p["reading_url"],quote=True)}">阅读与笔记</a></p></article>' for p in items)
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>每日精选 {date}</title><style>body{{max-width:720px;margin:auto;padding:18px;font:16px/1.6 system-ui;background:#fffbf5;color:#2d2419}}h2{{font-size:18px}}article{{border-top:1px solid #ddd;padding:12px 0}}a{{color:#a54f2b}}p{{overflow-wrap:anywhere}}</style><h1>每日精选 {date}</h1><p>{len(items)}篇 · {esc(payload["notice"])}</p>{entries or "<p>今天暂无新的合格精选。</p>"}<p><a href="maritime.html">完整论文库</a></p></html>'
    (root/'docs/maritime-daily.html').write_text(page,encoding='utf8')
    (directory/(str(date)+'.html')).write_text(page.replace('href="maritime.html"','href="../../maritime.html"'),encoding='utf8')
    markdown=f'# 每日精选 {date}\n\n'+ '\n\n'.join(f'## {p["title"]}\n\n{p["source"]}\n\n{p["reason"]}\n\n[原文]({p["original_url"]}) · [阅读页]({p["reading_url"]})' for p in items)
    (directory/(str(date)+'.md')).write_text(markdown,encoding='utf8')
    return payload
