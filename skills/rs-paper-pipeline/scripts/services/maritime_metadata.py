"""Fill missing abstracts using existing cached or bounded source metadata."""
import json
from pathlib import Path
from datetime import datetime, timezone

from clients import scholarly_client as scholarly, arxiv_client as arxiv
from services import maritime_v2 as v2


def cached_abstracts(root):
    records = []
    for path in (Path(root) / "papers/maritime/private/metadata-cache").glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if "results" in data:
                records.extend(scholarly.openalex_paper(p) for p in data["results"])
            elif "abstract_inverted_index" in data:
                records.append(scholarly.openalex_paper(data))
            elif isinstance(data.get("message"), dict):
                message = data["message"]
                records.extend(scholarly.crossref_paper(p) for p in message.get("items", [message]) if p.get("DOI"))
        except (ValueError, KeyError, TypeError):
            continue
    return [r for r in records if r.get("abstract")]


def _accept_abstract(paper, candidate, source):
    if v2.normalized_identity(paper.get("title", "")) != v2.normalized_identity(candidate.get("title", "")):
        raise ValueError("Complete title mismatch")
    if paper.get("authors") and candidate.get("authors") and not v2.same_title_authors(paper, candidate):
        raise ValueError("Author mismatch")
    abstract = candidate.get("abstract", "").strip()
    if not abstract:
        return False
    paper["abstract"] = abstract
    paper["abstract_source"] = candidate.get("abstract_source") or source
    paper.pop("abstract_access", None)
    paper["translation_pending"] = paper.get("translation", {}).get("status") != "manual"
    return True


def enrich_missing(library, rules, root, keys=None, limit=5, timeout=15, retries=1, network=True, publishers=True):
    before = {k for k, p in library["papers"].items() if not p.get("abstract", "").strip()}
    errors, attempts = [], []
    # Own version history first, without reopening or downloading PDF files.
    for key in before:
        paper = library["papers"][key]
        for record in paper.get("metadata_records", []):
            if record.get("abstract") and record.get("title"):
                try:
                    if _accept_abstract(paper, record, {"sources": record.get("metadata_source") or record.get("sources", []), "url": record.get("publication_evidence", {}).get("url", ""), "kind": "local_version"}):
                        break
                except ValueError:
                    continue
    for candidate in cached_abstracts(root):
        for key in before:
            paper = library["papers"][key]
            if not paper.get("abstract") and ((candidate.get("doi") and paper.get("doi") == candidate["doi"]) or
                    (candidate.get("arxiv_id") and paper.get("arxiv_id") == candidate["arxiv_id"])):
                try:
                    _accept_abstract(paper, candidate, {"sources": candidate.get("metadata_source", []), "url": candidate.get("publication_evidence", {}).get("url", ""), "kind": "metadata_cache"})
                except ValueError:
                    continue
    ordered = keys if keys is not None else sorted(library["papers"], key=lambda k: (library["papers"][k].get("assessment", {}).get("level") == "high", bool(library["papers"][k].get("quality", {}).get("high_journal")), v2.rank_key(library["papers"][k])), reverse=True)
    missing = [k for k in ordered if k in library["papers"] and not library["papers"][k].get("abstract", "").strip()]
    for key in missing[:limit] if network else []:
        paper = library["papers"][key]
        audit = {"paper_id": key, "doi": paper.get("doi"), "original_reason": "Existing source metadata supplied no abstract", "sources": [], "status": "missing", "final_source": None}
        print(f"摘要补全：{key}", flush=True)
        for source in ("arxiv", "crossref", "openalex", "publisher"):
            if paper.get("abstract"):
                break
            if source == "arxiv" and not paper.get("arxiv_id") or source != "arxiv" and not paper.get("doi"):
                continue
            if source == "publisher" and (not publishers or paper.get("publication_status") != "published"):
                continue
            item = {"source": source}
            audit["sources"].append(item)
            try:
                if source == "publisher":
                    from clients.publisher_abstract import fetch_publisher_abstract
                    result = fetch_publisher_abstract(paper, root, timeout)
                    if not result["public_allowed"]:
                        paper["abstract_access"] = {"status": "private_only", "source_url": result["url"], "reason": "Publisher abstract found; republication permission not verified"}
                        item.update(status="private_only", chars=len(result["abstract"]))
                        audit.update(status="private_only", final_source=result["url"])
                        continue
                    candidate = {"title": paper["title"], "abstract": result["abstract"], "abstract_source": {"sources": ["publisher"], "url": result["url"], "license_url": result["license_url"], "public_allowed": True}}
                else:
                    candidate = arxiv.fetch_maritime_metadata(paper["arxiv_id"], timeout, retries) if source == "arxiv" else scholarly.fetch_doi(paper["doi"], source, root, timeout, retries)
                if source in ("crossref", "openalex"):
                    if candidate.get("doi") != paper.get("doi") or not v2.same_title_authors(paper, candidate):
                        raise ValueError("Metadata DOI/title/author identity mismatch")
                    v2.merge_records(library, [candidate], rules)
                    paper = library["papers"][library.get("aliases", {}).get(key, key)]
                    if not paper.get("abstract") and paper.get("arxiv_id") and source == "openalex":
                        linked = arxiv.fetch_maritime_metadata(paper["arxiv_id"], timeout, retries)
                        if _accept_abstract(paper, linked, {"sources": ["arxiv"], "url": linked["arxiv_url"]}):
                            item.update(status="filled", chars=len(paper["abstract"]), via="explicit OpenAlex arXiv link")
                            audit.update(status="filled", final_source=paper["abstract_source"])
                            continue
                if paper.get("abstract") or _accept_abstract(paper, candidate, {"sources": [source], "url": candidate.get("arxiv_url") or candidate.get("publication_evidence", {}).get("url", "")}):
                    item.update(status="filled", chars=len(paper["abstract"]))
                    audit.update(status="filled", final_source=paper["abstract_source"])
                else:
                    item["status"] = "no_abstract"
            except Exception as exc:
                item.update(status="paused" if isinstance(exc, scholarly.OpenAlexLimited) else "failed", error=str(exc))
                errors.append({"paper_id": key, "source": source, "error": str(exc)})
        paper["abstract_check"] = {"time": datetime.now(timezone.utc).isoformat(), "status": audit["status"], "sources": audit["sources"]}
        attempts.append(audit)
    from services.maritime import score_paper
    for key in before:
        target = library["papers"][library.get("aliases", {}).get(key, key)]
        if target.get("abstract"):
            target["assessment"] = score_paper(target, rules)
            target["translation_pending"] = target.get("translation", {}).get("status") != "manual"
    v2.normalize_library(library, rules)
    after = sum(not p.get("abstract", "").strip() for p in library["papers"].values())
    result = {"missing_before": len(before), "missing_after": after, "filled": len(before) - after,
              "attempts": attempts, "errors": errors, "time": datetime.now(timezone.utc).isoformat()}
    library.setdefault("metadata_runs", []).append(result)
    return result
