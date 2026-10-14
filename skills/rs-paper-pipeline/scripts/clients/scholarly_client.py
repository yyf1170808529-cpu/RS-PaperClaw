"""Crossref/OpenAlex metadata only. No venue ranking inferred here."""
from __future__ import annotations
import hashlib
import html
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from datetime import datetime, timezone, timedelta


class OpenAlexLimited(RuntimeError):
    pass


def openalex_key():
    value = os.environ.get("OPENALEX_API_KEY")
    if not value and os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value = winreg.QueryValueEx(key, "OPENALEX_API_KEY")[0]
        except OSError:
            pass
    return value


def doi_id(value):
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value or "", flags=re.I).strip().lower()
    if value and not re.fullmatch(r"10\.\d{4,9}/\S+", value):
        raise ValueError("Invalid DOI")
    return value


def json_request(url, params=None, root=None, timeout=20, retries=3):
    query = dict(params or {})
    is_openalex = urllib.parse.urlsplit(url).hostname == "api.openalex.org"
    api_key = openalex_key() if is_openalex else None
    if api_key:
        # Header avoids persisting credentials in URL/cache/logs.
        headers = {"Authorization": "Bearer " + api_key}
    else:
        headers = {}
    mailto = os.environ.get("CROSSREF_MAILTO") or os.environ.get("OPENALEX_MAILTO")
    if mailto:
        query["mailto"] = mailto
    full = url + (("?" + urllib.parse.urlencode(query)) if query else "")
    cache = Path(root) / "papers/maritime/private/metadata-cache" / (hashlib.sha256(full.encode()).hexdigest() + ".json") if root else None
    if cache and cache.exists() and time.time() - cache.stat().st_mtime < 86400:
        return json.loads(cache.read_text(encoding="utf-8"))
    limit_file = Path(root) / "papers/maritime/private/openalex-cooldown.json" if root else None
    scope = hashlib.sha256(api_key.encode()).hexdigest() if api_key else "anonymous"
    cooldowns = json.loads(limit_file.read_text(encoding="utf-8")) if is_openalex and limit_file and limit_file.exists() else {}
    if is_openalex and cooldowns.get(scope, {}).get("until", 0) > time.time():
        raise OpenAlexLimited(f"api.openalex.org HTTP 429: {cooldowns[scope]['reason']}; paused until {cooldowns[scope]['until']} (cached metadata still usable)")
    headers.update({"User-Agent": "RS-PaperClaw-Maritime/2.0", "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(full, headers=headers), timeout=timeout) as response:
                data = json.load(response)
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data
        except HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", "replace")
            if api_key:
                detail = detail.replace(api_key, "[redacted]")
            if is_openalex and exc.code == 429:
                budget = any(term in detail.lower() for term in ("insufficient budget", "daily budget", "credits", "quota"))
                now = datetime.now(timezone.utc)
                reset = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).timestamp()
                reset_header = (exc.headers or {}).get("X-RateLimit-Reset", "")
                if reset_header.isdigit():
                    value = int(reset_header)
                    reset = value if value > time.time() else time.time() + min(86400, max(1, value))
                delay = (exc.headers or {}).get("Retry-After", "60")
                until = reset if budget else time.time() + min(300, max(1, int(delay) if delay.isdigit() else 60))
                reason = "budget_exhausted" if budget else "rate_limited"
                cooldowns[scope] = {"until": until, "reason": reason}
                if limit_file:
                    limit_file.parent.mkdir(parents=True, exist_ok=True)
                    limit_file.write_text(json.dumps(cooldowns), encoding="utf-8")
                raise OpenAlexLimited(f"api.openalex.org HTTP 429: {reason}; {detail}; requests paused, no batch retry") from None
            if attempt + 1 == retries or exc.code in (400, 401, 403, 404):
                raise RuntimeError(f"{urllib.parse.urlsplit(url).hostname} HTTP {exc.code}: {detail}") from None
            wait = max(3 * (2 ** attempt), int(exc.headers.get("Retry-After", "0")) if exc.headers.get("Retry-After", "0").isdigit() else 0)
            time.sleep(wait)
        except (OSError, ValueError) as exc:
            if attempt + 1 == retries:
                raise RuntimeError(f"{urllib.parse.urlsplit(url).hostname}: {type(exc).__name__}") from None
            time.sleep(3 * (2 ** attempt))


def date_parts(item):
    for field in ("published-online", "published", "published-print", "issued"):
        values = item.get(field, {}).get("date-parts", [])
        if values and values[0]:
            parts = values[0]
            return "-".join(f"{n:04d}" if i == 0 else f"{n:02d}" for i, n in enumerate(parts)), field
    return "", "missing"


def strip_markup(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value or "")).split())


def crossref_paper(item):
    doi = doi_id(item.get("DOI"))
    date, precision_source = date_parts(item)
    authors = item.get("author", [])
    first = authors[0] if authors else {}
    affiliations = [html.unescape(a["name"]) for a in first.get("affiliation", []) if a.get("name")]
    venue = (item.get("container-title") or [""])[0]
    kind = item.get("type")
    journal = kind == "journal-article" and bool(doi and venue and date)
    conference = kind == "proceedings-article" and bool(doi and venue and date)
    return {"paper_id": "doi:" + doi, "doi": doi, "arxiv_id": None,
        "title": strip_markup((item.get("title") or [""])[0]), "abstract": strip_markup(item.get("abstract")),
        "authors": [" ".join([a.get("given", ""), a.get("family", "")]).strip() for a in authors],
        "published": date, "publication_date": date, "publication_date_source": precision_source,
        "source_type": "journal" if journal else "conference" if conference else "metadata",
        "publication_status": "published" if journal or conference else "unknown",
        "venue": venue, "venue_type": "journal" if journal else "conference" if conference else "unknown",
        "issn": item.get("ISSN", []), "original_url": "https://doi.org/" + doi,
        "arxiv_url": "", "pdf_url": "", "open_access_url": "",
        "first_author": " ".join([first.get("given", ""), first.get("family", "")]).strip(),
        "first_author_affiliations": affiliations, "affiliation_source": "Crossref first author" if affiliations else "",
        "affiliation_verified": bool(affiliations), "metadata_source": ["Crossref"],
        "publication_evidence": {"source": "Crossref", "url": "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""), "type": kind},
        "crossref_links": item.get("link", [])}


def inverted_abstract(index):
    if not isinstance(index, dict):
        return ""
    words = {}
    for word, positions in index.items():
        for position in positions:
            words[int(position)] = word
    return " ".join(words[p] for p in sorted(words))


def openalex_paper(item):
    doi = doi_id(item.get("doi"))
    location = item.get("primary_location") or {}
    source = location.get("source") or {}
    authorships = item.get("authorships") or []
    firsts = [a for a in authorships if a.get("author_position") == "first"]
    first = firsts[0] if len(firsts) == 1 else {}
    institutions = [a["display_name"] for a in first.get("institutions", []) if a.get("display_name")]
    affiliations = first.get("raw_affiliation_strings") or institutions
    date = item.get("publication_date", "")
    kind = source.get("type")
    published = bool(doi and date and source.get("id") and kind in ("journal", "conference") and item.get("type") not in ("preprint", "posted-content"))
    arxiv = None
    for loc in item.get("locations") or []:
        match = re.search(r"https?://(?:export\.)?arxiv\.org/(?:abs|pdf)/((?:\d{4}\.\d{4,5}|[a-zA-Z.-]+/\d{7}))(?:v\d+)?", loc.get("landing_page_url") or "")
        if match:
            arxiv = match.group(1)
    oa_locations = [loc for loc in item.get("locations") or [] if loc.get("is_oa") and loc.get("pdf_url")]
    pdf = oa_locations[0]["pdf_url"] if oa_locations else ""
    return {"paper_id": "doi:" + doi if doi else "openalex:" + item["id"].rsplit("/", 1)[-1],
        "doi": doi, "arxiv_id": arxiv, "title": item.get("title") or item.get("display_name") or "",
        "abstract": inverted_abstract(item.get("abstract_inverted_index")),
        "authors": [a.get("author", {}).get("display_name") or "" for a in authorships],
        "published": date, "publication_date": date, "source_type": kind if published else "preprint" if arxiv or item.get("type") == "preprint" else "metadata",
        "publication_status": "published" if published else "unknown", "venue": source.get("display_name", ""),
        "venue_type": kind if published else "unknown", "issn": source.get("issn") or [], "openalex_source_id": source.get("id"),
        "original_url": "https://doi.org/" + doi if doi else location.get("landing_page_url") or item["id"],
        "open_access_url": pdf, "pdf_url": pdf, "arxiv_url": f"https://arxiv.org/abs/{arxiv}" if arxiv else "",
        "oa_evidence": {"source": "OpenAlex is_oa location", "url": item["id"]} if pdf else {},
        "first_author": first.get("author", {}).get("display_name", ""), "first_author_affiliations": affiliations,
        "affiliation_source": "OpenAlex first authorship" if affiliations else "", "affiliation_verified": bool(affiliations),
        "metadata_source": ["OpenAlex"], "publication_evidence": {"source": "OpenAlex", "url": item["id"], "type": item.get("type")},
        "is_retracted": item.get("is_retracted") is True,
        "identity_evidence": {"source": item["id"], "relation": "arxiv landing location"} if arxiv else {}}


def fetch_crossref(journal, start, end, query, root, pages=5, rows=100, timeout=20, retries=3):
    issn = journal["issn"][0]
    endpoint = "https://api.crossref.org/journals/" + issn
    identity = json_request(endpoint, root=root, timeout=timeout, retries=retries)["message"]
    normalize = lambda value: re.sub(r"[^a-z0-9]", "", value.lower())
    if normalize(identity.get("title", "")) != normalize(journal["name"]):
        raise ValueError(f"ISSN/name mismatch for {journal['id']}")
    cursor, result = "*", []
    for page in range(pages):
        time.sleep(1)
        message = json_request(endpoint + "/works", {"filter": f"type:journal-article,from-pub-date:{start},until-pub-date:{end}",
            "query.title": query, "rows": rows, "cursor": cursor}, root, timeout, retries)["message"]
        batch = message.get("items", [])
        result.extend(crossref_paper(item) for item in batch)
        new_cursor = message.get("next-cursor")
        if len(batch) < rows or len(result) >= message.get("total-results", 0) or new_cursor == cursor:
            return result, True
        cursor = new_cursor
    return result, False


def fetch_openalex(start, end, query, root, pages=5, rows=100, timeout=20, retries=3):
    result, cursor = [], "*"
    for page in range(pages):
        if page:
            time.sleep(1)
        data = json_request("https://api.openalex.org/works", {"filter": f"from_publication_date:{start},to_publication_date:{end}",
            "search": query, "per_page": min(rows, 100), "cursor": cursor}, root, timeout, retries)
        batch = data.get("results", [])
        result.extend(openalex_paper(item) for item in batch)
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor or len(batch) < min(rows, 100) or len(result) >= data.get("meta", {}).get("count", 0):
            return result, True
    return result, False


def fetch_doi(doi, source, root, timeout=20, retries=3):
    doi = doi_id(doi)
    if source == "crossref":
        return crossref_paper(json_request("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""), root=root, timeout=timeout, retries=retries)["message"])
    return openalex_paper(json_request("https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi, safe=""), root=root, timeout=timeout, retries=retries))
