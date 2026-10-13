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
    stamp = datetime.now(timezone.utc).isoformat()
    identity_keys = {p["arxiv_id"]: key for key, p in library["papers"].items() if p.get("arxiv_id")}
    for paper in candidates:
        aid = canonical_arxiv_id(paper["arxiv_id"])
        key = identity_keys.get(aid, aid)
        identity_keys[aid] = key
        previous = library["papers"].get(key, {})
        merged = dict(previous)
        # An older version from a date replay must not replace newer metadata.
        if not previous or paper.get("updated", "") >= previous.get("updated", ""):
            merged.update({k: v for k, v in paper.items() if v not in (None, "", [], {})
                           and not (previous.get("publication_status") == "published" and k == "published")})
        merged["arxiv_id"] = aid
        merged["assessment"] = score_paper(merged, rules)
        merged["first_seen"] = previous.get("first_seen", stamp)
        merged["last_seen"] = stamp
        merged["retrieved_dates"] = sorted(set(previous.get("retrieved_dates", [])) | {today().isoformat()})
        merged["retrieved_topics"] = sorted(set(previous.get("retrieved_topics", [])) | set(source_topics))
        library["papers"][key] = merged
    for date in dates:
        day = library["days"].setdefault(date, {"candidate_ids": [], "searched_topics": []})
        day["candidate_ids"] = sorted(set(day["candidate_ids"]) | {identity_keys[canonical_arxiv_id(p["arxiv_id"])] for p in candidates if p["published"] == date})
        day["searched_topics"] = sorted(set(day["searched_topics"]) | set(source_topics))
        day["last_success"] = stamp


def daily_data(library, date, rules):
    day = library["days"][date]
    candidates = [library["papers"][aid] for aid in day["candidate_ids"]]
    selected = [p for p in candidates if p["assessment"]["level"] != "excluded"]
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
        from services.maritime_v2 import assets, select_sections, select_recommendations
        _, policy = assets()
        data["sections"] = select_sections(selected, policy)
        data["recommendations"] = select_recommendations(selected, policy)
        data["recommendation_shortfalls"] = {k: limit - len(data["recommendations"][k]) for k, limit in policy["quotas"].items()}
        data["paper_ids"] = [aid for ids in data["recommendations"].values() for aid in ids]
        data["omitted_count"] = len(selected) - len(data["paper_ids"])
    return data


def render_daily(data, library):
    lines = [f'# 论文日报 {data["date"]}', "", "规则相关性仅用于启发式排序，不代表创新性或学术价值判断。", "",
        f'候选 {data["candidate_count"]}；入选 {data["selected_count"]}；高度相关 {data["high_count"]}；主专题统计 {data["topic_counts"]}。',
        f'检索范围：{", ".join(data["searched_topics"])}；日报最多展示 {len(data["paper_ids"])} 篇，其余 {data["omitted_count"]} 篇可在候选库查看。', ""]
    if not data["paper_ids"]:
        lines.append("本次重点推荐无入选论文；一般候选可在网页查看。" if "sections" in data else "本次成功检索范围内无入选论文。")
    if "recommendations" in data:
        lines.extend(["重点推荐目标：水路60% / 陆上强相关30% / 通用高水平10%（12/6/2篇）。不足不补位。",
                      f'实际数量：{ {k: len(v) for k, v in data["recommendations"].items()} }；缺口：{data["recommendation_shortfalls"]}。', ""])
    last_section = None
    for aid in data["paper_ids"]:
        p = library["papers"][aid]
        a = p["assessment"]
        if "recommendations" in data:
            section = p["recommendation"]["bucket"]
            if section != last_section:
                lines.extend(["## " + {"water": "水路感知与关联", "land": "陆上强相关", "general": "通用方法（顶会优先，含arXiv）"}[section], ""])
                last_section = section
        lines.extend([f'### {html.escape(p["title"])}', "", f'[原文]({p.get("original_url") or p.get("arxiv_url", "")}) · [PDF]({p.get("pdf_url", "")})',
            f'作者：{html.escape(", ".join(p["authors"]))}  ', f'发布日期：{p["published"]}  ',
            f'主专题：{a["primary_topic"]}；专题：{", ".join(a["topics"])}；场景：{", ".join(a["applications"])}  ',
            f'相关性：{LEVELS[a["level"]]} ({a["score"]})  ', html.escape("；".join(a["reasons"])), "",
            html.escape(p["abstract"]), "", "<details><summary>中文阅读提示</summary>", "",
            "请先核查研究问题与命中理由，再阅读方法和实验。此处未翻译摘要。若需深入分析，请在阅读页复制 Prompt 并向 DeepSeek 上传 PDF。", "", "</details>", ""])
        if "quality" in p:
            q = p["quality"]
            lines.extend([f'发表：{html.escape(p.get("venue") or "未确认来源")}；状态 {p["publication_status"]}；DOI {p.get("doi") or "暂无"}',
                f'中科院大类：{p.get("cas_partition") or "待核验"}（2025）；JCR JIF：' + ("；".join(f'{r["year"]} {r["category"]} {r["quartile"]}' for r in q["jcr_records"]) or "待核验"),
                "第一作者单位：" + html.escape("；".join(p.get("first_author_affiliations", [])) or "暂未获取"), ""])
            translation = p.get("translation", {})
            if translation.get("zh") and translation.get("status") in ("machine", "manual"):
                lines.extend(["中文摘要（" + ("机器翻译" if translation["status"] == "machine" else "人工修订") + "）：", html.escape(translation["zh"]), ""])
    return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"


def build(root, library, rules):
    from services.maritime_v2 import normalize_library, assets, select_sections
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
    payload = {"schema_version": 2, "topics": {k: v["name"] for k, v in rules["topics"].items()},
               "papers": list(library["papers"].values()), "days": days,
               "aliases": library.get("aliases", {}), "source_runs": library.get("source_runs", []),
               "recommendation_policy": policy,
               "prompt_template": (Path(__file__).resolve().parents[1] / "prompts/maritime_analysis.md").read_text(encoding="utf-8")}
    write_json(root / "docs/maritime-data/library.json", payload)


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
    for raw_id, value in backup["readings"].items():
        aid = resolve_paper_id(library, raw_id)
        if aid not in library["papers"]:
            raise ValueError(f"Unknown paper {aid}; retrieve it first (nothing imported)")
        records[aid] = validate_reading(value)
    for aid, value in records.items():
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
    parser.add_argument("--action", choices=["fetch", "rescore", "digest", "site", "import", "export", "doctor", "fetch-journals", "fetch-openalex", "fetch-all", "import-venues", "venue-audit", "translate", "install-model", "revise-translation", "prepare-pdf", "review-audit"], default="fetch")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--date", help="指定一天 YYYYMMDD 或 YYYY-MM-DD")
    parser.add_argument("--topic", choices=list("ABCD"), action="append", help="可重复，默认全部")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--file", type=Path, help="import/export 文件；import 支持网页 JSON 或单篇 Markdown")
    parser.add_argument("--id", help="导入 Markdown 的 arXiv ID")
    parser.add_argument("--source", choices=["crossref", "openalex", "arxiv"], action="append")
    parser.add_argument("--journal", action="append", help="候选池中的期刊 id，可重复")
    parser.add_argument("--query", help="正式来源关键词组合")
    parser.add_argument("--doi", help="按 DOI 获取正式元信息；仍独立核验质量")
    parser.add_argument("--limit", type=int, default=5, help="翻译/人工审查导出数量")
    parser.add_argument("--extract-text", action="store_true", help="prepare-pdf 时使用 pdftotext")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    args.root = root
    rules = load_maritime_assets()
    library = load_library(root)
    try:
        from services import maritime_v2 as v2
        if args.action.startswith("fetch-"):
            if not (1 <= args.days <= 366 and 1 <= args.page_size <= 2000 and args.max_pages > 0 and args.retries > 0 and args.timeout > 0):
                raise ValueError("Invalid date/paging/retry limits")
            return v2.fetch_sources(args, library, rules)
        if args.action == "import-venues":
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
