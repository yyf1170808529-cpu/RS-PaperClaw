"""No-API mode: original arXiv transport, explainable rules, local archives."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import time

from clients.arxiv_client import canonical_arxiv_id, fetch_topic_candidates
from services.filter_assets import load_maritime_assets

REPO = Path(__file__).resolve().parents[4]
STATES = ["待读", "已浏览", "值得精读", "已精读", "值得复现"]
LEVELS = {"high": "高度相关", "transfer": "方法可借鉴", "general": "一般相关", "excluded": "不相关"}


def today():
    return datetime.now(timezone(timedelta(hours=8))).date()


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def has(text, phrase):
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I))


def score_paper(paper, rules):
    from services.abstract_quality import apply_quality
    apply_quality(paper)
    title, abstract = paper["title"], paper["abstract"]
    text = title + "\n" + abstract
    excluded = [term for term in rules["exclude"] if has(text, term)]
    scores, reasons = {}, []
    for key, topic in rules["topics"].items():
        groups, evidence = {}, []
        for group, terms in topic["groups"].items():
            hits = []
            value = 0
            for term in terms:
                if has(title, term):
                    value += rules["title_weight"]
                    hits.append(f"标题:{term}")
                elif has(abstract, term):
                    value += rules["abstract_weight"]
                    hits.append(f"摘要:{term}")
            if hits:
                groups[group] = min(value, rules["group_cap"])
                evidence.extend(hits)
        if (len(groups) >= topic["min_groups"] and any(g in groups for g in topic["required"])
                and all(g in groups for g in topic.get("must_groups", []))):
            scores[key] = sum(groups.values()) + (len(groups) - 1) * rules["cooccurrence_bonus"]
            reasons.append(f"专题 {key}: " + ", ".join(evidence) + f"；独立概念组={len(groups)}，分数={scores[key]}")
    applications = [name for name, terms in rules["applications"].items() if any(has(text, t) for t in terms)]
    if not applications:
        applications = ["其他相关应用"]
    primary = max(scores, key=scores.get) if scores else None
    value = scores.get(primary, 0)
    boost = max([rules["application_boost"].get(a, 0) for a in applications], default=0) if primary else 0
    value += boost
    if boost:
        reasons.append(f"应用优先级加分 +{boost}")
    level = "excluded"
    if excluded:
        reasons.append("排除规则: " + ", ".join(excluded))
    elif primary:
        for name in ("high", "transfer", "general"):
            if value >= rules["thresholds"][name]:
                level = name
                break
    return {"score": value, "topic_scores": scores, "primary_topic": primary,
            "topics": sorted(scores, key=lambda k: -scores[k]), "applications": applications,
            "level": level, "reasons": reasons or ["缺少明确研究问题或方法联系"],
            "scoring_version": hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()[:12]}


def library_path(root):
    return root / "papers/maritime/library.json"


def load_library(root):
    return read_json(library_path(root), {"schema_version": 1, "papers": {}, "days": {}})


def merge_candidates(library, candidates, dates, rules, source_topics):
    from services.maritime_v2 import merge_records
    stamp = datetime.now(timezone.utc).isoformat()
    prepared = []
    for paper in candidates:
        aid = canonical_arxiv_id(paper["arxiv_id"])
        previous = next((p for p in library["papers"].values() if p.get("arxiv_id") == aid), {})
        # Preserve newer arXiv versions during date replay.
        record = dict(previous) if previous and paper.get("updated", "") < previous.get("updated", "") else dict(paper)
        record.update(paper_id=aid, arxiv_id=aid, metadata_source=sorted(set(record.get("metadata_source", [])) | {"arXiv"}))
        record.setdefault("publication_date", paper["published"])
        prepared.append(record)
    original_schema = library.get("schema_version", 1)
    merge_records(library, prepared, rules)
    library["schema_version"] = original_schema
    identities = {p["arxiv_id"]: k for k, p in library["papers"].items() if p.get("arxiv_id")}
    for paper in candidates:
        p = library["papers"][identities[canonical_arxiv_id(paper["arxiv_id"])]]
        p["retrieved_dates"] = sorted(set(p.get("retrieved_dates", [])) | {today().isoformat()})
        p["retrieved_topics"] = sorted(set(p.get("retrieved_topics", [])) | set(source_topics))
    for date in dates:
        day = library["days"].setdefault(date, {"candidate_ids": [], "searched_topics": []})
        day["candidate_ids"] = sorted(set(day["candidate_ids"]) | {identities[canonical_arxiv_id(p["arxiv_id"])] for p in candidates if p["published"] == date})
        day["searched_topics"] = sorted(set(day["searched_topics"]) | set(source_topics))
        day["last_success"] = stamp


def daily_data(library, date, rules):
    day = library["days"][date]
    candidates = [library["papers"][aid] for aid in day["candidate_ids"]]
    from services.maritime_validity import eligible_paper
    selected = [p for p in candidates if p["assessment"]["level"] != "excluded" and eligible_paper(p)]
    selected.sort(key=lambda p: (-p["assessment"]["score"], p.get("paper_id") or p["arxiv_id"]))
    counts = Counter(p["assessment"]["primary_topic"] for p in selected)
    data = {"date": date, "candidate_count": len(candidates), "selected_count": len(selected),
            "topic_counts": {k: counts[k] for k in rules["topics"]},
            "high_count": sum(p["assessment"]["level"] == "high" for p in selected),
            "searched_topics": day["searched_topics"], "last_success": day.get("last_success"),
            "candidate_ids": day["candidate_ids"],
            "paper_ids": [p.get("paper_id") or p["arxiv_id"] for p in selected[:rules["daily_limit"]]],
            "omitted_count": max(0, len(selected) - rules["daily_limit"])}
    if library.get("schema_version") == 2:
        from services.maritime_v2 import assets, select_sections, recommendation_view
        _, policy = assets()
        data["sections"] = select_sections(selected, policy)
        view = recommendation_view(list(library["papers"].values()), policy, date)
        data["recommendation_view"] = view
        data["recommendations"] = view["groups"]
        data["recommendation_shortfalls"] = {k: limit - len(data["recommendations"][k]) for k, limit in policy["quotas"].items()}
        data["paper_ids"] = [aid for ids in data["recommendations"].values() for aid in ids]
        data["omitted_count"] = sum(p.get("paper_id") not in data["paper_ids"] for p in selected)
    return data


def render_daily(data, library):
    lines = [f'# 论文日报 {data["date"]}', "", "规则相关性仅用于启发式排序，不代表创新性或学术价值判断。", "",
        f'候选 {data["candidate_count"]}；入选 {data["selected_count"]}；高度相关 {data["high_count"]}；主专题统计 {data["topic_counts"]}。',
        f'当日发表检索范围：{", ".join(data["searched_topics"])}；近期精选展示 {len(data["paper_ids"])} 篇，完整库仍保留。', ""]
    if not data["paper_ids"]:
        lines.append("本次重点推荐无入选论文；一般候选可在网页查看。" if "sections" in data else "本次成功检索范围内无入选论文。")
    if "recommendations" in data:
        lines.extend(["重点推荐目标：水上交通50% / 陆上交通30% / 通用视觉多模态20%（10/6/4篇）。不足不补位。水上90天，陆上/通用30天；历史回溯按真实发表日期，不代表当日新发表。",
                      f'实际数量：{ {k: len(v) for k, v in data["recommendations"].items()} }；缺口：{data["recommendation_shortfalls"]}。', ""])
    last_section = None
    for aid in data["paper_ids"]:
        p = library["papers"][aid]
        a = p["assessment"]
        if "recommendations" in data:
            section = p["recommendation"]["bucket"]
            if section != last_section:
                lines.extend(["## " + {"water": "水路高水平期刊", "land": "陆上交通高水平期刊 / CCF A / arXiv", "general": "通用视觉多模态高水平期刊 / CCF A / arXiv"}[section], ""])
                last_section = section
        lines.extend([f'### {html.escape(p["title"])}', "", f'[原文]({p.get("original_url") or p.get("arxiv_url", "")}) · [PDF]({p.get("pdf_url", "")})',
            f'作者：{html.escape(", ".join(p["authors"]))}  ', f'发布日期：{p["published"]}  ',
            f'主专题：{a["primary_topic"]}；专题：{", ".join(a["topics"])}；场景：{", ".join(a["applications"])}  ',
            f'相关性：{LEVELS[a["level"]]} ({a["score"]})  ', html.escape("；".join(a["reasons"])), "",
            html.escape(p["abstract"]), "", "<details><summary>中文阅读提示</summary>", "",
            "请核查研究问题和命中理由，再阅读方法和实验。中文如提供，为机器翻译或人工修订，英文原文保留。精读可复制Prompt到ChatGPT或DeepSeek，并确认实际读到PDF全文。", "", "</details>", ""])
        if p.get("abstract_source", {}).get("license_url"):
            lines.extend([f'[摘要许可]({p["abstract_source"]["license_url"]})', ""])
        if "quality" in p:
            from services.maritime_v2 import compact_source
            lines.extend([compact_source(p), f'DOI：{p.get("doi") or "暂无"}',
                "第一作者单位：" + html.escape("；".join(p.get("first_author_affiliations", [])) or "暂未获取"), ""])
            translation = p.get("translation", {})
            if translation.get("zh") and translation.get("status") in ("machine", "manual"):
                lines.extend(["中文摘要（" + ("机器翻译" if translation["status"] == "machine" else "人工修订") + "）：", html.escape(translation["zh"]), ""])
    return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"


def build(root, library, rules, mobile_date=None):
    from services.maritime_v2 import normalize_library, assets, recommendation_view
    normalize_library(library, rules)
    days = {}
    for date in sorted(library["days"], reverse=True):
        data = daily_data(library, date, rules)
        days[date] = data
        relative = Path(date[:7].replace("-", "")) / (date.replace("-", "") + ".md")
        for directory in (root / "daily_reports/maritime", root / "docs/maritime-data/reports"):
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_daily(data, library), encoding="utf-8")
    _, policy = assets()
    from services.semantic_evaluation import ranking_info,settings
    from services.selected_translation import chosen_zh,translation_issue
    semantic_settings=settings()
    public_papers=[]
    for p in library['papers'].values():
        item={k:v for k,v in p.items() if k not in ('raw_abstract','abstract_history','translation_history','metadata_records','merge_conflicts')}
        info=ranking_info(p,semantic_settings if library.get('semantic_enabled',True) else {**semantic_settings,'enabled':False})
        item.update(ai_score=info['score'],ai_demoted=info['demoted'],recommendation_status=info['path'] or 'candidate',ai_state=info['state'],display_abstract_zh=chosen_zh(p)[0],display_translation_source=chosen_zh(p)[1],display_translation_error=translation_issue(p))
        public_papers.append(item)
    payload = {"schema_version": 2, "topics": {k: v["name"] for k, v in rules["topics"].items()},
               "papers": public_papers, "days": days,
               "aliases": library.get("aliases", {}), "source_runs": library.get("source_runs", []),
               "update_summary": read_json(root / "papers/maritime/logs/latest-update.json", None),
               "recommendation_policy": policy,
               "recommendation_views": {window: recommendation_view(list(library["papers"].values()), policy, today(), window)
                                        for window in ("recent", "7", "14")},
               "prompt_template": (Path(__file__).resolve().parents[1] / "prompts/maritime_analysis.md").read_text(encoding="utf-8")}
    write_json(root / "docs/maritime-data/library.json", payload)
    from services.mobile_digest import build_mobile_digest
    build_mobile_digest(root, library, mobile_date or today())


def validate_reading(value):
    if (not isinstance(value, dict) or not isinstance(value.get("analysis", ""), str)
            or value.get("state", "待读") not in STATES
            or ("updated_at" in value and not isinstance(value["updated_at"], str))):
        raise ValueError("Invalid reading record (analysis must be Markdown text; state must be known)")
    return {"analysis": value.get("analysis", ""), "state": value.get("state", "待读"),
            "updated_at": value.get("updated_at", datetime.now(timezone.utc).isoformat())}


def import_backup(library, backup):
    if backup.get("schema_version") != 1 or not isinstance(backup.get("readings"), dict):
        raise ValueError("Expected schema_version=1 and readings object")
    records = {}
    conflicts = []
    record_sources = {}
    for raw_id, value in backup["readings"].items():
        aid = resolve_paper_id(library, raw_id)
        if aid not in library["papers"]:
            raise ValueError(f"Unknown paper {aid}; retrieve it first (nothing imported)")
        validated = validate_reading(value)
        if aid in records and records[aid] != validated:
            conflicts.append((aid, {"from": record_sources[aid], "field": "reading", "value": records[aid]}))
        records[aid] = validated
        record_sources[aid] = raw_id
    for aid, conflict in conflicts:
        library["papers"][aid].setdefault("merge_conflicts", []).append(conflict)
    for aid, value in records.items():
        prior = library["papers"][aid].get("reading")
        if prior and prior != value:
            library["papers"][aid].setdefault("merge_conflicts", []).append({"from": aid, "field": "reading", "value": prior})
        library["papers"][aid]["reading"] = value


def resolve_paper_id(library, value):
    if value in library["papers"]:
        return value
    if value in library.get("aliases", {}):
        return library["aliases"][value]
    from clients.scholarly_client import doi_id
    if value.startswith(("doi:", "https://doi.org/", "10.")):
        doi = doi_id(value)
        return next((k for k, p in library["papers"].items() if p.get("doi") == doi), "doi:" + doi)
    aid = canonical_arxiv_id(value)
    return next((k for k, p in library["papers"].items() if p.get("arxiv_id") == aid), aid)


def main(argv=None):
    parser = argparse.ArgumentParser(description="个人论文库（无 API Key，无第三方 Python 依赖）")
    parser.add_argument("--root", type=Path, default=REPO, help="归档根目录，默认仓库根目录")
    parser.add_argument("--action", choices=["fetch", "update", "rescore", "digest", "site", "import", "export", "doctor", "fetch-journals", "fetch-openalex", "fetch-all", "import-venues", "venue-audit", "translate", "install-model", "revise-translation", "prepare-pdf", "review-audit", "verify", "dedup", "enrich", "translate-history", "evaluate-ai", "score-ai-labels"], default="fetch")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument('--sample-size',type=int,default=50,help='独立AI评估试验样本数')
    parser.add_argument('--ai-budget',type=float,help='本日DeepSeek预算上限人民币，默认2元')
    parser.add_argument('--ai-limit',type=int,help='本次日更最多新评价篇数，默认20')
    parser.add_argument('--no-ai',action='store_true',help='本次更新完全使用规则排序，不调用AI')
    parser.add_argument("--date", help="指定一天 YYYYMMDD 或 YYYY-MM-DD")
    parser.add_argument("--topic", choices=list("ABCD"), action="append", help="可重复，默认全部")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--task-timeout", type=int, default=180, help="单来源任务总上限秒；0仅用于明确禁用")
    parser.add_argument("--translation-limit", type=int, help="覆盖配置中的每批最大翻译篇数")
    parser.add_argument("--batches", type=int, default=1, help="历史翻译批次数；成功缓存自动断点续跑")
    parser.add_argument("--retry-failed", action="store_true", help="将既往失败摘要重新纳入翻译队列")
    parser.add_argument("--translation-timeout", type=int, help="中文翻译阶段总上限秒")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--file", type=Path, help="import/export 文件；import 支持网页 JSON 或单篇 Markdown")
    parser.add_argument("--id", help="导入 Markdown 的 arXiv ID")
    parser.add_argument("--source", choices=["crossref", "openalex", "arxiv"], action="append")
    parser.add_argument("--journal", action="append", help="候选池中的期刊 id，可重复")
    parser.add_argument("--query", help="正式来源关键词组合")
    parser.add_argument("--doi", help="按 DOI 获取正式元信息；仍独立核验质量")
    parser.add_argument("--limit", type=int, default=5, help="翻译/人工审查导出数量")
    parser.add_argument("--extract-text", action="store_true", help="prepare-pdf 时使用 pdftotext")
    parser.add_argument("--all-history", action="store_true", help="verify 可选历史批量复查，仍受 --limit 限制")
    parser.add_argument("--bootstrap", action="store_true", help="首次水上期刊回溯12个月")
    args = parser.parse_args(argv)
    settings = read_json(Path(__file__).resolve().parents[1] / "config/maritime/translation.json", {})
    mode = "history" if args.action == "translate-history" else "daily"
    defaults = settings.get(mode, {"max_papers": 5, "seconds": 180})
    args.translation_limit = args.translation_limit if args.translation_limit is not None else args.limit if args.limit != 5 else defaults["max_papers"]
    args.translation_timeout = args.translation_timeout or defaults["seconds"]
    args.retry_failed = args.retry_failed or settings.get("retry_failed", False)
    root = args.root.resolve()
    args.root = root
    rules = load_maritime_assets()
    library = load_library(root)
    try:
        from services import maritime_v2 as v2
        if args.action=='score-ai-labels':
            from services.semantic_evaluation import label_metrics
            print(json.dumps(label_metrics(root),ensure_ascii=False))
            return 0
        if args.action=='evaluate-ai':
            from services.semantic_evaluation import evaluate
            if not 1<=args.sample_size<=50:raise ValueError('Experiment size must be 1..50')
            result=evaluate(root,library,args.sample_size,args.ai_budget)
            print(json.dumps({'evaluated':len(result['records']),'errors':len(result['errors']),
                              'cost_upper_cny':result['cost_upper_cny'],'balance_delta_cny':result['balance_delta_cny']},ensure_ascii=False))
            return 0 if len(result['records'])==args.sample_size else 2
        if args.action == "update":
            if not (1 <= args.page_size <= 100 and args.max_pages > 0 and args.retries > 0 and args.timeout > 0 and args.task_timeout >= 0 and args.translation_timeout > 0 and args.limit >= 0 and args.translation_limit >= 0):
                raise ValueError("Invalid update paging/retry limits")
            from services.maritime_update import run_update
            return run_update(args, library, rules)
        if args.action.startswith("fetch-"):
            if not (1 <= args.days <= 366 and 1 <= args.page_size <= 2000 and args.max_pages > 0 and args.retries > 0 and args.timeout > 0):
                raise ValueError("Invalid date/paging/retry limits")
            return v2.fetch_sources(args, library, rules)
        if args.action == "translate-history":
            if args.translation_limit < 1 or args.translation_timeout <= 0 or args.batches < 1:
                raise ValueError("Positive translation limit/time/batches required")
            from services.maritime_reading import translate_history
            results = translate_history(root, library, rules, args.translation_limit, args.translation_timeout, args.batches, args.retry_failed)
            print(json.dumps(results, ensure_ascii=False))
            return 2 if any(r["failed"] for r in results) else 0
        if args.action == "dedup":
            print(json.dumps(v2.deduplicate_library(library, rules), ensure_ascii=False))
        elif args.action == "enrich":
            from services.maritime_metadata import enrich_missing
            keys = [resolve_paper_id(library, args.id)] if args.id else None
            print(json.dumps(enrich_missing(library, rules, root, keys, args.limit, args.timeout, args.retries), ensure_ascii=False))
        elif args.action == "verify":
            from services.maritime_validity import verify_records
            v2.normalize_library(library, rules)
            _, policy = v2.assets()
            keys = [resolve_paper_id(library, args.id)] if args.id else (list(library["papers"]) if args.all_history else v2.recommendation_view(list(library["papers"].values()), policy, today())["paper_ids"])
            checked = verify_records(library, keys, args.timeout, force=True, limit=args.limit)
            print(json.dumps({"verified_count": len(checked), "records": {k: library["papers"][k]["validity"] for k in checked}}, ensure_ascii=False))
        elif args.action == "import-venues":
            if not args.file:
                raise ValueError("--file required")
            v2.import_venues(args.file)
        elif args.action == "venue-audit":
            venues, policy = v2.assets()
            for journal in venues["journals"]:
                quality = v2.venue_quality({"issn": journal["issn"], "venue_type": "journal", "publication_status": "published"}, venues, policy)
                print(json.dumps({"id": journal["id"], "name": journal["name"], "quality": quality}, ensure_ascii=False))
            return 0
        elif args.action in ("translate", "install-model", "revise-translation", "prepare-pdf", "review-audit"):
            from services import maritime_reading as reading
            v2.normalize_library(library, rules)
            if args.action == "install-model":
                reading.install_model(args.file)
                return 0
            ordered = sorted(library["papers"].values(), key=v2.rank_key, reverse=True)
            if args.action == "translate":
                ordered = [p for p in ordered if p.get("abstract")]
            chosen = [library["papers"][resolve_paper_id(library, args.id)]] if args.id else ordered[:args.limit]
            if args.action == "translate":
                for paper in chosen:
                    paper["translation"] = reading.translate_one(paper)
                    print(f'{paper["paper_id"]}: {paper["translation"]["status"]}', flush=True)
            elif args.action == "revise-translation":
                if not args.id or not args.file:
                    raise ValueError("--id and --file required")
                chosen[0]["translation"] = {"status": "manual", "zh": args.file.read_text(encoding="utf-8"), "updated_at": datetime.now(timezone.utc).isoformat()}
            elif args.action == "prepare-pdf":
                if not args.id:
                    raise ValueError("--id required; PDF preparation is single-paper only")
                reading.prepare_pdf(chosen[0], root, args.file, args.extract_text, args.timeout)
                return 0
            else:
                target = args.file or root / "papers/maritime/private/recommendation-audit.json"
                write_json(target, {"notice": "待人工核查，不是模型审稿", "papers": [{"paper_id": p["paper_id"], "title": p["title"], "abstract": p["abstract"], "recommendation": p["recommendation"], "quality": p["quality"], "human_relevant": None, "notes": ""} for p in chosen]})
                print(target)
                return 0
        if args.action == "doctor":
            if sys.version_info < (3, 10):
                raise RuntimeError("Python 3.10+ required")
            for topic in rules["topics"].values():
                for terms in topic["groups"].values():
                    for term in terms:
                        has("", term)
            print(f"OK: Python {sys.version.split()[0]}, A/B/C/D 配置、Prompt、标准库可用。无须 LLM/GitHub Token。归档: {root}")
            import importlib.util
            import shutil
            venues, policy = v2.assets()
            print(f"V2 来源候选={len(venues['journals'])}；CAS年份={policy['cas_year']}；Argos已安装={importlib.util.find_spec('argostranslate') is not None}；pdftotext可用={shutil.which('pdftotext') is not None}")
            return 0
        if args.action == "fetch":
            if not (1 <= args.days <= 366 and 1 <= args.page_size <= 2000 and args.max_pages > 0 and args.retries > 0 and args.timeout > 0):
                raise ValueError("Invalid days/paging/retry/timeout limits")
            end = datetime.strptime(args.date.replace("-", ""), "%Y%m%d").date() if args.date else today()
            start = end if args.date else end - timedelta(days=args.days - 1)
            dates = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
            topics = args.topic or list("ABCD")
            candidates = []
            topics = list(dict.fromkeys(topics))
            # Smaller topical queries avoid one complex request for the whole library.
            # Only publish after all requested topics complete, never a partial daily success.
            for index, key in enumerate(topics):
                if index:
                    time.sleep(3)
                query = " OR ".join(f"({q})" for q in rules["topics"][key]["queries"])
                print(f"[arXiv] 专题 {key} ({index + 1}/{len(topics)}): {start} 至 {end}", flush=True)
                batch = fetch_topic_candidates(query, start.isoformat(), end.isoformat(),
                    args.page_size, args.max_pages, args.retries, args.timeout)
                print(f"[arXiv] 专题 {key}: {len(batch)} 篇候选", flush=True)
                candidates.extend(batch)
            merge_candidates(library, candidates, dates, rules, topics)
            from services.maritime_reading import translate_available
            translate_available(library, {resolve_paper_id(library, p["arxiv_id"]) for p in candidates})
        elif args.action == "rescore":
            for paper in library["papers"].values():
                paper["assessment"] = score_paper(paper, rules)
        elif args.action == "import":
            if not args.file:
                raise ValueError("--file required")
            if args.file.suffix.lower() == ".json":
                import_backup(library, read_json(args.file, {}))
            else:
                if not args.id:
                    raise ValueError("Markdown import requires --id")
                aid = resolve_paper_id(library, args.id)
                current = library["papers"].get(aid, {}).get("reading", {})
                import_backup(library, {"schema_version": 1, "readings": {aid: {
                    "analysis": args.file.read_text(encoding="utf-8"), "state": current.get("state", "待读")}}})
        elif args.action == "export":
            if not args.file:
                raise ValueError("--file required")
            write_json(args.file, {"schema_version": 1, "readings": {aid: p["reading"] for aid, p in library["papers"].items() if "reading" in p}})
            return 0
        v2.normalize_library(library, rules)
        write_json(library_path(root), library)
        build(root, library, rules)
        summaries = {d: {k: v for k, v in daily_data(library, d, rules).items()
                        if k not in ("candidate_ids", "paper_ids", "sections")} for d in library["days"]}
        print(json.dumps({"action": args.action, "library_count": len(library["papers"]),
            "days": summaries}, ensure_ascii=False))
        if args.action == "translate" and any(p.get("translation", {}).get("status") not in ("machine", "manual") for p in chosen):
            return 1
        return 0
    except Exception as exc:
        log = root / "papers/maritime/logs/errors.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "action": args.action,
                "date": args.date, "error": str(exc)}, ensure_ascii=False) + "\n")
        print(f"ERROR: {exc}. See {log}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
