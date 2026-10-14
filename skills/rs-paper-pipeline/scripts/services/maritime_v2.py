"""Small V2 extension: evidence-controlled venues and independent recommendation."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone, timedelta
import copy
import json
from pathlib import Path
import re
import html
import unicodedata

from clients.scholarly_client import doi_id
from services.maritime_validity import resource_type, formal_evidence, eligible_paper, LABELS

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
    if not matched and not issns:
        name = " ".join(paper.get("venue", "").casefold().split())
        matched = [j for j in venues["journals"] if name in [" ".join(n.casefold().split()) for n in [j["name"], *j.get("verified_aliases", [])]]]
    journal = matched[0] if len(matched) == 1 else {}
    cas = [r for r in journal.get("cas_records", []) if r.get("scheme") == "CAS" and r.get("scope") == "major"
           and r.get("official_table") is True and r.get("year") == policy["cas_year"] and evidence_valid(r)]
    cas_ok = any(r.get("partition") == 1 for r in cas) and len({r.get("partition") for r in cas}) == 1
    jcr = [r for r in journal.get("jcr_records", []) if r.get("scheme") == "JCR" and r.get("metric") == "JIF Quartile"
           and isinstance(r.get("year"), int) and (r.get("category") or r.get("scope") == "journal_overall") and r.get("quartile") in ("Q1", "Q2", "Q3", "Q4") and evidence_valid(r)]
    latest = max((r["year"] for r in jcr), default=None)
    current = [r for r in jcr if r["year"] == latest]
    categories = {}
    for r in current:
        categories.setdefault(r.get("category") or "institutional journal-level JIF summary", set()).add(r["quartile"])
    jcr_ok = any(values == {"Q1"} for values in categories.values())
    catalog = policy.get("ccf", {})
    matches = [r for r in catalog.get("conferences", []) if any(re.search(r"\b" + re.escape(alias) + r"\b", paper.get("venue", ""), re.I) for alias in r["aliases"])]
    conference_record = matches[0] if len(matches) == 1 else {}
    conference = False
    if (paper.get("venue_type") == "conference" and paper.get("publication_status") == "published"
            and (paper.get("doi") or any(evidence_valid(r) for r in paper.get("conference_evidence", [])))):
        source = paper.get("publication_evidence", {}).get("source")
        conference = ((source in ("Crossref", "OpenAlex") or any(evidence_valid(r) for r in paper.get("conference_evidence", [])))
                      and not re.search(r"\b(workshops?|symposium|short|demo|findings|technical brief|summary)\b",
                                        " ".join(str(paper.get(k, "")) for k in ("venue", "paper_type", "conference_track")) + " " + str(paper.get("publication_evidence", {}).get("track", "")), re.I)
                      and bool(conference_record))
    ccf_a = bool(conference and conference_record.get("grade") == "A")
    jifs = [r for r in journal.get("jif_records", []) if r.get("metric") == "Journal Impact Factor" and evidence_valid(r)
            and isinstance(r.get("value"), (int, float)) and not isinstance(r["value"], bool) and r["value"] > 0]
    jif = max(jifs, key=lambda r: (r.get("year") or 0, r["evidence"]["checked_at"]), default=None)
    journal_eligible = bool(formal_evidence(paper, "journal") and (cas_ok or jcr_ok))
    return {"cas_one": bool(cas_ok), "jcr_q1": bool(jcr_ok), "both": bool(cas_ok and jcr_ok),
        "high_journal": journal_eligible, "high_conference": ccf_a, "ccf_a": ccf_a,
        "conference_name": conference_record.get("name"), "ccf_grade": conference_record.get("grade"),
        "ccf_evidence": catalog if conference_record else None, "cas_year": policy["cas_year"],
        "one_type": "双一区" if cas_ok and jcr_ok else "中科院一区" if cas_ok else "JCR一区" if jcr_ok else "待核验",
        "jif": jif["value"] if jif else None, "jif_record": jif,
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
    if paper.get("first_seen"):
        try:
            paper["discovery_date"] = datetime.fromisoformat(paper["first_seen"]).astimezone(timezone(timedelta(hours=8))).date().isoformat()
        except ValueError:
            pass
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
    paper["resource_type"] = resource_type(paper)
    paper["resource_type_label"] = LABELS[paper["resource_type"]]
    paper.setdefault("validity", {"status": "unverified", "reason": "尚未核验"})
    if paper.get("is_retracted") is True:
        paper["validity"].update(status="withdrawn", reason="来源元数据明确标记撤回")
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
    from services.abstract_quality import application
    paper['application_bucket'] = application(paper, policy)
    maritime = paper['application_bucket'] == 'water'
    low = bool(signals["low"] or (signals["trajectory"] and not perception))
    method = bool(signals["method"])
    related = paper.get("assessment", {}).get("level") != "excluded" and eligible_paper(paper)
    direct = 3 if perception and maritime else 2 if perception else 1 if method else 0
    q = paper["quality"]
    formal = q["high_journal"] or q["ccf_a"]
    frontier = bool(arxiv and paper["publication_status"] != "published")
    section = "candidate"
    if related and not low:
        if direct == 3 and formal:
            section = "maritime"
        elif direct >= 2 and formal:
            section = "methods"
        elif arxiv and paper["publication_status"] != "published" and (direct == 3 or (direct == 2 and paper["assessment"]["level"] == "high")):
            section = "preprints"
    paper["recommendation"] = {"section": section, "direct_relevance": direct, "maritime": maritime,
        "bucket": ("water" if related and not low and maritime and perception and q["high_journal"] else
                   "land" if related and not low and signals["traffic"] and perception and paper["assessment"]["level"] == "high" and (formal or frontier) else
                   "general" if related and not low and not maritime and not signals["traffic"] and (formal or frontier) and (perception or method) and paper["assessment"]["level"] == "high" else "candidate"),
        "application": "maritime" if maritime else "traffic" if signals["traffic"] else "general",
        "publication_quality": "high_journal" if q["high_journal"] else "high_conference" if q["high_conference"] else "unverified",
        "method_transfer_signal": method, "low_priority": low,
        "reasons": [f"感知联系={signals['perception']}", f"海事场景={signals['maritime']}",
            f"方法证据={signals['method']}", f"低优先级={signals['low'] or (signals['trajectory'] if low else [])}",
            f"陆上场景={signals['traffic']}；已核验CCF A正式会议={q['ccf_a']}",
            f"发表质量={q['status']}；CAS一区={q['cas_one']}，JIF Q1={q['jcr_q1']}"],
        "notice": "方法借鉴仅是关键词证据，不判断真实创新性；机构不参与排名"}
    return paper


def compact_source(paper):
    q = paper.get("quality", {})
    if paper.get("venue_type") == "journal":
        value = str(float(q["jif"])) if q.get("jif") is not None else "暂无"
        return f'{paper.get("venue") or "期刊"} · {q.get("one_type", "待核验")} · IF {value}'
    if paper.get("publication_status") == "published" and paper.get("venue_type") == "conference":
        label = q.get("conference_name") or paper.get("venue") or "会议"
        year = (paper.get("publication_date") or paper.get("published", ""))[:4]
        grade = " · CCF A" if q.get("ccf_a") else " · CCF " + q["ccf_grade"] if q.get("ccf_grade") in ("B", "C") else ""
        return f"{label} {year}{grade}"
    return "arXiv" if paper.get("arxiv_id") else paper.get("venue") or "其他来源"


def rank_key(paper):
    r = paper.get("recommendation", {})
    q = paper.get("quality", {})
    return (not r.get("low_priority", False), bool(q.get("ccf_a")),
            bool(q.get("high_journal") or q.get("high_conference")), r.get("direct_relevance", 0), r.get("maritime", False), r.get("method_transfer_signal", False),
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
                     if p.get("recommendation", {}).get("bucket") == bucket and p.get("validity", {}).get("status") not in {"deleted", "withdrawn", "invalid"} and p.get("resource_type", "preprint") in {"journal_article", "conference_paper", "preprint"}][:limit]
            for bucket, limit in policy["quotas"].items()}


def recommendation_view(papers, policy, end, window="recent"):
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d").date()
    limits = policy["quotas"]
    windows = {k: days if k == "water" or window == "recent" else min(days, int(window))
               for k, days in policy["windows"].items()}
    eligible = []
    for p in papers:
        bucket = p.get("recommendation", {}).get("bucket")
        date = p.get("publication_date") or p.get("published", "")
        if re.fullmatch(r"\d{4}-\d{2}", date) and p.get("publication_status") == "published":
            # Eligibility interval only: never write an invented publication day.
            date = date + "-01"
        if bucket not in windows or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            continue
        if str(end - timedelta(days=windows[bucket] - 1)) <= date <= str(end):
            eligible.append(p)
    groups = select_recommendations(eligible, policy)
    return {"paper_ids": [aid for ids in groups.values() for aid in ids], "groups": groups,
            "counts": {k: len(v) for k, v in groups.items()}, "limits": limits, "windows": windows, "as_of": str(end)}


def normalize_library(library, rules):
    from services.maritime import score_paper
    venues, policy = assets()
    for key, paper in library["papers"].items():
        from services.abstract_quality import apply_quality
        changed = apply_quality(paper)
        if changed or 'assessment' not in paper:
            paper['assessment'] = score_paper(paper, rules)
        annotate(paper, key, venues, policy)
    library["schema_version"] = 2
    return library


def normalized_identity(value):
    value = unicodedata.normalize("NFKD", value or "").casefold()
    return "".join(c for c in value if c.isalnum())


def same_title_authors(a, b):
    if not normalized_identity(a.get("title", "")) or normalized_identity(a.get("title", "")) != normalized_identity(b.get("title", "")):
        return False
    aa = {normalized_identity(n) for n in a.get("authors", []) if n and n.strip()}
    bb = {normalized_identity(n) for n in b.get("authors", []) if n and n.strip()}
    return bool(aa and bb and len(aa & bb) / max(len(aa), len(bb)) >= .8 and
                normalized_identity(a["authors"][0]) == normalized_identity(b["authors"][0]))


def title_identity(a, b):
    # Exact full title AND full author agreement. Distinct formal DOIs are ambiguous.
    if not same_title_authors(a, b) or not (a.get("arxiv_id") or b.get("arxiv_id")):
        return False
    if not (eligible_paper(a) and eligible_paper(b)):
        return False
    da, db = doi_id(a.get("doi")), doi_id(b.get("doi"))
    if a.get("publication_status") == b.get("publication_status") == "published" and da and db and da != db:
        return False
    return a.get("publication_status") == "published" or b.get("publication_status") == "published"


def retain_protected(current, incoming, old_id):
    for field in ("reading", "translation"):
        old, new = current.get(field), incoming.get(field)
        if not new:
            continue
        if old and old != new:
            conflict = {"from": old_id, "field": field, "value": copy.deepcopy(new)}
            if conflict not in current.setdefault("merge_conflicts", []):
                current["merge_conflicts"].append(conflict)
            if field == "translation" and new.get("status") == "manual" and old.get("status") != "manual":
                current["merge_conflicts"].append({"from": current.get("paper_id"), "field": field, "value": old})
                current[field] = copy.deepcopy(new)
            elif field == "reading" and not old.get("analysis") and new.get("analysis"):
                current[field] = copy.deepcopy(new)
        elif not old:
            current[field] = copy.deepcopy(new)


def merge_records(library, records, rules, touch=True):
    """Preserve identity aliases, formal metadata, abstracts and personal content."""
    from services.maritime import score_paper
    from clients.arxiv_client import canonical_arxiv_id
    stamp = datetime.now(timezone.utc).isoformat()
    removed = 0
    title_index = {}
    for k, p in library["papers"].items():
        title_index.setdefault(normalized_identity(p.get("title", "")), set()).add(k)
    for incoming in records:
        incoming = copy.deepcopy(incoming)
        doi = doi_id(incoming.get("doi"))
        arxiv = canonical_arxiv_id(incoming["arxiv_id"]) if incoming.get("arxiv_id") else None
        incoming["doi"] = doi
        if arxiv:
            incoming["arxiv_id"] = arxiv
        title_matches = {k for k in title_index.get(normalized_identity(incoming.get("title", "")), []) if k in library["papers"] and title_identity(incoming, library["papers"][k])}
        matches = [k for k, p in library["papers"].items() if k == incoming.get("paper_id") or
                   (doi and doi_id(p.get("doi")) == doi) or (arxiv and p.get("arxiv_id") == arxiv) or k in title_matches]
        arxiv_keys = [k for k in matches if library["papers"][k].get("arxiv_id") == k]
        key = arxiv_keys[0] if arxiv_keys else matches[0] if matches else arxiv or incoming["paper_id"]
        current = copy.deepcopy(library["papers"].get(key, {}))
        all_versions = [library["papers"][k] for k in matches if k != key] + [incoming]
        for version in all_versions:
            source_id = version.get("paper_id") or version.get("arxiv_id")
            retain_protected(current, version, source_id)
            formal = version.get("publication_status") == "published"
            newer_arxiv = not formal and current.get("publication_status") != "published" and "arXiv" in version.get("metadata_source", []) and version.get("updated", "") >= current.get("updated", "")
            prefer_formal = formal and (current.get("publication_status") != "published" or
                            version.get("publication_evidence", {}).get("source") == "Crossref")
            snapshot = {f: copy.deepcopy(version.get(f)) for f in ("doi", "arxiv_id", "title", "authors", "abstract", "metadata_source", "publication_date", "venue", "first_author_affiliations", "publication_evidence")}
            for history in [*version.get("metadata_records", []), snapshot]:
                if history not in current.setdefault("metadata_records", []):
                    current["metadata_records"].append(history)
            current["metadata_source"] = sorted(set(current.get("metadata_source", [])) | set(version.get("metadata_source", [])))
            for field, value in version.items():
                if field in ("reading", "translation", "paper_id", "metadata_source", "metadata_records", "assessment", "quality", "recommendation", "merge_conflicts") or value in (None, "", [], {}):
                    continue
                if field == "abstract":
                    if len(value.strip()) > len(current.get("abstract", "").strip()):
                        current[field] = value
                        current["abstract_source"] = version.get("abstract_source") or {"sources": version.get("metadata_source", []), "url": version.get("arxiv_url") or version.get("publication_evidence", {}).get("url", "")}
                elif field in ("first_seen", "last_seen"):
                    prior = current.get(field)
                    current[field] = (min(prior, value) if field == "first_seen" else max(prior, value)) if prior else value
                elif field == "validity":
                    prior = current.get(field, {})
                    if value.get("status") in {"deleted", "withdrawn", "invalid"} or prior.get("status", "unverified") == "unverified":
                        current[field] = value
                elif field == "issn":
                    current[field] = sorted(set(current.get(field, [])) | set(value)) if formal else current.get(field) or value
                elif field in ("doi", "title", "authors", "venue", "venue_type", "publication_status", "source_type", "publication_date", "published", "publication_evidence", "original_url", "first_author", "first_author_affiliations", "affiliation_source", "affiliation_verified"):
                    if prefer_formal or (newer_arxiv and field != "doi") or not current.get(field) or current.get(field) == "unknown":
                        # Do not turn month/year-only formal dates into a guessed first day.
                        if field in ("publication_date", "published") and len(current.get(field, "")) in (4, 7) and str(value).startswith(current[field]) and str(value).endswith("-01") and "Crossref" in current.get("metadata_source", []):
                            continue
                        current[field] = value
                else:
                    current[field] = value
            for conflict in version.get("merge_conflicts", []):
                if conflict not in current.setdefault("merge_conflicts", []):
                    current["merge_conflicts"].append(conflict)
        for other in matches:
            if other != key:
                library["papers"].pop(other)
                library.setdefault("aliases", {})[other] = key
                removed += 1
                for day in library["days"].values():
                    day["candidate_ids"] = sorted({key if i == other else i for i in day["candidate_ids"]})
        old_id = incoming.get("paper_id")
        if old_id and old_id != key:
            library.setdefault("aliases", {})[old_id] = key
        for alias, destination in library.get("aliases", {}).items():
            if destination in matches:
                library["aliases"][alias] = key
        current.setdefault("title", "")
        current.setdefault("authors", [])
        current.setdefault("abstract", "")
        current["paper_id"] = key
        current.setdefault("first_seen", stamp)
        if touch:
            current["last_seen"] = stamp
        current["assessment"] = score_paper(current, rules)
        library["papers"][key] = current
        title_index.setdefault(normalized_identity(current.get("title", "")), set()).add(key)
        date = current.get("publication_date", "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            day = library["days"].setdefault(date, {"candidate_ids": [], "searched_topics": []})
            day["candidate_ids"] = sorted(set(day["candidate_ids"]) | {key})
    normalize_library(library, rules)
    return removed


def deduplicate_library(library, rules):
    records = copy.deepcopy(list(library["papers"].values()))
    removed = merge_records(library, records, rules, touch=False)
    titles = {}
    for p in library["papers"].values():
        titles.setdefault(normalized_identity(p.get("title", "")), []).append(p["paper_id"])
    suspected = [ids for title, ids in titles.items() if title and len(ids) > 1]
    return {"merged": removed, "suspected": suspected}


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
