"""Small V2 extension: evidence-controlled venues and independent recommendation."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import re
import html

from clients.scholarly_client import doi_id

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config/maritime"


def assets():
    return tuple(json.loads((CONFIG_DIR / name).read_text(encoding="utf-8")) for name in ("venues.json", "recommendation.json"))


def evidence_valid(record):
    evidence = record.get("evidence") or {}
    return (record.get("verified") is True and bool(evidence.get("url") or evidence.get("local_file"))
            and bool(evidence.get("checked_at")) and evidence.get("kind") in ("official", "publisher", "institution", "user_verified"))


def venue_quality(paper, venues, policy):
    issns = set(paper.get("issn") or [])
    matched = [j for j in venues["journals"] if issns.intersection(j["issn"])]
    journal = matched[0] if len(matched) == 1 else {}
    cas = [r for r in journal.get("cas_records", []) if r.get("scheme") == "CAS" and r.get("scope") == "major"
           and r.get("official_table") is True and r.get("year") == policy["cas_year"] and evidence_valid(r)]
    cas_ok = any(r.get("partition") == 1 for r in cas) and len({r.get("partition") for r in cas}) == 1
    jcr = [r for r in journal.get("jcr_records", []) if r.get("scheme") == "JCR" and r.get("metric") == "JIF Quartile"
           and isinstance(r.get("year"), int) and r.get("category") and r.get("quartile") in ("Q1", "Q2", "Q3", "Q4") and evidence_valid(r)]
    latest = max((r["year"] for r in jcr), default=None)
    current = [r for r in jcr if r["year"] == latest]
    categories = {}
    for r in current:
        categories.setdefault(r["category"], set()).add(r["quartile"])
    jcr_ok = any(values == {"Q1"} for values in categories.values())
    conference = False
    if (paper.get("venue_type") == "conference" and paper.get("publication_status") == "published"
            and (paper.get("doi") or any(evidence_valid(r) for r in paper.get("conference_evidence", [])))):
        source = paper.get("publication_evidence", {}).get("source")
        conference = ((source in ("Crossref", "OpenAlex") or any(evidence_valid(r) for r in paper.get("conference_evidence", [])))
                      and not re.search(r"\b(workshops?|symposium)\b", paper.get("venue", ""), re.I)
                      and any(re.search(r"\b" + re.escape(name) + r"\b", paper.get("venue", ""), re.I) for name in policy["conference_names"]))
    journal_eligible = bool(paper.get("venue_type") == "journal" and paper.get("publication_status") == "published" and (cas_ok or jcr_ok))
    return {"cas_one": bool(cas_ok), "jcr_q1": bool(jcr_ok), "both": bool(cas_ok and jcr_ok),
        "high_journal": journal_eligible, "high_conference": bool(conference), "cas_year": policy["cas_year"],
        "cas_records": cas, "jcr_records": jcr, "jcr_latest_year": latest,
        "status": "verified" if cas or jcr else "unverified", "venue_id": journal.get("id"),
        "note": "CAS官方大类一区 OR 已核验最新JCR JIF学科Q1；缺少证据不补猜"}


def annotate(paper, key, venues, policy):
    from services.maritime import has
    paper["paper_id"] = key
    arxiv = paper.get("arxiv_id")
    paper.setdefault("source_type", "preprint" if arxiv else "metadata")
    paper.setdefault("publication_status", "unknown")
    paper.setdefault("venue_type", "unknown")
    paper.setdefault("venue", "")
    paper.setdefault("doi", "")
    paper.setdefault("issn", [])
    paper.setdefault("original_url", paper.get("arxiv_url", ""))
    paper.setdefault("open_access_url", paper.get("pdf_url", "") if arxiv else "")
    paper.setdefault("publication_date", paper.get("published", ""))
    paper.setdefault("first_author", (paper.get("authors") or [""])[0])
    paper.setdefault("first_author_affiliations", [])
    paper.setdefault("affiliation_source", "")
    paper.setdefault("affiliation_verified", False)
    paper.setdefault("metadata_source", ["arXiv"] if arxiv else [])
    if "Crossref" in paper["metadata_source"]:
        from clients.scholarly_client import strip_markup
        paper["title"] = strip_markup(paper["title"])
        paper["first_author_affiliations"] = [html.unescape(a) for a in paper["first_author_affiliations"]]
    proceedings = [r for r in venues.get("conference_records", [])
                   if ((r.get("doi") and r.get("doi") == paper.get("doi")) or (r.get("paper_id") and r["paper_id"] == key))
                   and r.get("scheme") == "official_proceedings" and evidence_valid(r)]
    if proceedings:
        paper.update({"publication_status": "published", "venue_type": "conference", "source_type": "conference",
                      "venue": proceedings[0]["venue"], "conference_evidence": proceedings})
        if proceedings[0].get("open_access_url"):
            paper["open_access_url"] = proceedings[0]["open_access_url"]
            paper["oa_evidence"] = proceedings[0]["evidence"]
    paper["quality"] = venue_quality(paper, venues, policy)
    # Both schemes remain separately available. Legacy single CAS fields describe CAS only.
    paper["cas_partition"] = paper["quality"]["cas_records"][0]["partition"] if paper["quality"]["cas_records"] else None
    paper["partition_scheme"] = "CAS official major" if paper["cas_partition"] is not None else None
    paper["partition_year"] = policy["cas_year"] if paper["cas_partition"] is not None else None
    paper["partition_evidence"] = [r["evidence"] for r in paper["quality"]["cas_records"]]
    paper["jcr_partitions"] = paper["quality"]["jcr_records"]
    text = paper.get("title", "") + "\n" + paper.get("abstract", "")
    signals = {kind: [term for term in terms if has(text, term)] for kind, terms in policy["signals"].items()}
    perception = bool(signals["perception"])
    maritime = bool(signals["maritime"])
    low = bool(signals["low"] or (signals["trajectory"] and not perception))
    method = bool(signals["method"])
    related = paper.get("assessment", {}).get("level") != "excluded"
    direct = 3 if perception and maritime else 2 if perception else 1 if method else 0
    q = paper["quality"]
    formal = q["high_journal"] or q["high_conference"]
    section = "candidate"
    if related and not low:
        if direct == 3 and formal:
            section = "maritime"
        elif direct >= 2 and formal:
            section = "methods"
        elif arxiv and paper["publication_status"] != "published" and (direct == 3 or (direct == 2 and paper["assessment"]["level"] == "high")):
            section = "preprints"
    paper["recommendation"] = {"section": section, "direct_relevance": direct, "maritime": maritime,
        "bucket": ("water" if related and not low and maritime and perception else
                   "land" if related and not low and signals["traffic"] and perception and paper["assessment"]["level"] == "high" else
                   "general" if related and not low and not maritime and not signals["traffic"] and formal and (perception or method) else "candidate"),
        "application": "maritime" if maritime else "traffic" if signals["traffic"] else "general",
        "publication_quality": "high_journal" if q["high_journal"] else "high_conference" if q["high_conference"] else "unverified",
        "method_transfer_signal": method, "low_priority": low,
        "reasons": [f"感知联系={signals['perception']}", f"海事场景={signals['maritime']}",
            f"方法证据={signals['method']}", f"低优先级={signals['low'] or (signals['trajectory'] if low else [])}",
            f"发表质量={q['status']}；CAS一区={q['cas_one']}，JIF Q1={q['jcr_q1']}"],
        "notice": "方法借鉴仅是关键词证据，不判断真实创新性；机构不参与排名"}
    return paper


def rank_key(paper):
    r = paper.get("recommendation", {})
    q = paper.get("quality", {})
    return (not r.get("low_priority", False), r.get("direct_relevance", 0), r.get("maritime", False),
            bool(q.get("high_journal") or q.get("high_conference")), r.get("method_transfer_signal", False),
            paper.get("publication_date") or paper.get("published", ""), paper.get("assessment", {}).get("score", 0))


def select_sections(papers, policy):
    sections = {}
    for name, limit in policy["limits"].items():
        sections[name] = [p["paper_id"] for p in sorted(papers, key=rank_key, reverse=True) if p.get("recommendation", {}).get("section") == name][:limit]
    sections["candidate"] = [p["paper_id"] for p in papers if p["paper_id"] not in {i for ids in sections.values() for i in ids}]
    return sections


def select_recommendations(papers, policy):
    """Independent quotas; a shortage never borrows places from another bucket."""
    return {bucket: [p["paper_id"] for p in sorted(papers, key=rank_key, reverse=True)
                     if p.get("recommendation", {}).get("bucket") == bucket][:limit]
            for bucket, limit in policy["quotas"].items()}


def normalize_library(library, rules):
    from services.maritime import score_paper
    venues, policy = assets()
    for key, paper in library["papers"].items():
        paper.setdefault("assessment", score_paper(paper, rules))
        annotate(paper, key, venues, policy)
    library["schema_version"] = 2
    return library


def merge_records(library, records, rules):
    """Only DOI, arXiv, and explicit OpenAlex locations identify the same paper."""
    from services.maritime import score_paper
    from clients.arxiv_client import canonical_arxiv_id
    stamp = datetime.now(timezone.utc).isoformat()
    for incoming in records:
        incoming = copy.deepcopy(incoming)
        doi = doi_id(incoming.get("doi"))
        arxiv = canonical_arxiv_id(incoming["arxiv_id"]) if incoming.get("arxiv_id") else None
        matches = [k for k, p in library["papers"].items() if (doi and doi_id(p.get("doi")) == doi) or (arxiv and p.get("arxiv_id") == arxiv)]
        # Preserve the legacy arXiv identity to retain browser reading keys.
        key = arxiv if arxiv in matches else matches[0] if matches else arxiv or incoming["paper_id"]
        current = copy.deepcopy(library["papers"].get(key, {}))
        snapshot = {"sources": incoming.get("metadata_source", []), "publication_date": incoming.get("publication_date"),
                    "venue": incoming.get("venue"), "first_author": incoming.get("first_author"),
                    "affiliations": incoming.get("first_author_affiliations", []), "evidence": incoming.get("publication_evidence", {})}
        provenance = current.setdefault("metadata_records", [])
        if snapshot not in provenance:
            provenance.append(snapshot)
        if (incoming.get("metadata_source") == ["OpenAlex"] and len(current.get("publication_date", "")) in (4, 7)
                and incoming.get("publication_date", "").startswith(current["publication_date"])
                and incoming.get("publication_date", "").endswith("-01")
                and "Crossref" in current.get("metadata_source", [])):
            incoming["publication_date"] = current["publication_date"]
            incoming["published"] = current["publication_date"]
            incoming["date_note"] = "Crossref仅提供年月精度；OpenAlex首日日期不提升为已核实准确日，原来源日期保留在metadata_records"
        for other in matches:
            if other != key:
                old = library["papers"].pop(other)
                library.setdefault("aliases", {})[other] = key
                for protected in ("reading", "translation"):
                    if old.get(protected) and current.get(protected) and old[protected] != current[protected]:
                        current.setdefault("merge_conflicts", []).append({"from": other, "field": protected, "value": old[protected]})
                    elif old.get(protected):
                        current[protected] = old[protected]
                for day in library["days"].values():
                    day["candidate_ids"] = sorted({key if i == other else i for i in day["candidate_ids"]})
        sources = sorted(set(current.get("metadata_source", [])) | set(incoming.get("metadata_source", [])))
        formal = incoming.get("publication_status") == "published"
        for field, value in incoming.items():
            if field in ("reading", "translation", "paper_id", "metadata_source") or value in (None, "", [], {}):
                continue
            if field in ("venue", "venue_type", "publication_status", "source_type", "publication_date", "published", "publication_evidence"):
                if formal or not current.get(field):
                    current[field] = value
            elif field in ("first_author", "first_author_affiliations", "affiliation_source", "affiliation_verified"):
                if incoming.get("affiliation_verified") or not current.get(field):
                    current[field] = value
            else:
                current[field] = value
        current.setdefault("authors", [])
        current.setdefault("abstract", "")
        current["paper_id"] = key
        current["metadata_source"] = sources
        current.setdefault("first_seen", stamp)
        current["last_seen"] = stamp
        current["assessment"] = score_paper(current, rules)
        library["papers"][key] = current
        date = current.get("publication_date", "")
        if not arxiv:
            for old_date, day in library["days"].items():
                if old_date != date and key in day["candidate_ids"]:
                    day["candidate_ids"] = [aid for aid in day["candidate_ids"] if aid != key]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            day = library["days"].setdefault(date, {"candidate_ids": [], "searched_topics": []})
            day["candidate_ids"] = sorted(set(day["candidate_ids"]) | {key})
    normalize_library(library, rules)


def import_venues(path):
    # Import only explicitly audited records; identifiers must match existing journal.
    from services.maritime import write_json
    incoming = json.loads(path.read_text(encoding="utf-8"))
    venues, _ = assets()
    for record in incoming.get("journals", []):
        match = next((j for j in venues["journals"] if j["id"] == record.get("id") and set(j["issn"]).intersection(record.get("issn", []))), None)
        if not match:
            raise ValueError("Journal id and ISSN must match the editable venue pool")
        for field in ("cas_records", "jcr_records"):
            if field not in record:
                continue
            values = record.get(field, [])
            if not isinstance(values, list):
                raise ValueError("Partition records must be lists")
            match[field] = values
    write_json(CONFIG_DIR / "venues.json", venues)


def fetch_sources(args, library, rules):
    from clients import scholarly_client as client
    from services.maritime import write_json, library_path, build, today
    from datetime import timedelta
    venues, policy = assets()
    end = datetime.strptime(args.date.replace("-", ""), "%Y%m%d").date() if args.date else today()
    start = end if args.date else end - timedelta(days=args.days - 1)
    sources = args.source or (["crossref", "openalex", "arxiv"] if args.action == "fetch-all" else ["crossref"] if args.action == "fetch-journals" else ["openalex"])
    results = []
    run_id = datetime.now(timezone.utc).isoformat()
    for source in sources:
        jobs = [j for j in venues["journals"] if j["enabled"] and (not args.journal or j["id"] in args.journal)] if source == "crossref" and not args.doi else [None]
        for journal in jobs:
            status = {"run_id": run_id, "source": source, "journal": journal["id"] if journal else None, "start": str(start), "end": str(end), "time": datetime.now(timezone.utc).isoformat()}
            status.update({"mode": "doi_lookup" if args.doi else "date_search", "doi": args.doi, "query": args.query})
            if args.doi:
                status["start"] = status["end"] = None
            try:
                if source == "arxiv":
                    from services.maritime import main, load_library
                    code = main(["--root", str(args.root), "--days", str(args.days), "--retries", str(args.retries), "--timeout", str(args.timeout),
                        "--max-pages", str(args.max_pages)] + (["--date", args.date] if args.date else []))
                    if code:
                        raise RuntimeError("arXiv retrieval failed; see errors.jsonl")
                    library.clear()
                    library.update(load_library(args.root))
                    batch, complete = [], True
                elif args.doi:
                    batch, complete = [client.fetch_doi(args.doi, source, args.root, args.timeout, args.retries)], True
                elif source == "crossref":
                    batch, complete = client.fetch_crossref(journal, str(start), str(end), args.query or policy["query_terms"][0], args.root,
                        args.max_pages, min(args.page_size, 100), args.timeout, args.retries)
                else:
                    batch, complete = client.fetch_openalex(str(start), str(end), args.query or "maritime ship detection sensor fusion", args.root,
                        args.max_pages, min(args.page_size, 100), args.timeout, args.retries)
                merge_records(library, batch, rules)
                from services.maritime_reading import translate_available
                batch_dois = {p.get("doi") for p in batch if p.get("doi")}
                batch_arxiv = {p.get("arxiv_id") for p in batch if p.get("arxiv_id")}
                translate_available(library, [k for k, p in library["papers"].items() if p.get("doi") in batch_dois or p.get("arxiv_id") in batch_arxiv])
                status.update({"status": "success" if complete else "incomplete", "candidate_count": len(batch)})
            except Exception as exc:
                status.update({"status": "failed", "error": str(exc)})
            library.setdefault("source_runs", []).append(status)
            # Successful source/journal results survive any later source failure.
            write_json(library_path(args.root), library)
            build(args.root, library, rules)
            results.append(status)
            print(json.dumps(status, ensure_ascii=False), flush=True)
    return 0 if results and all(r["status"] == "success" for r in results) else 1
