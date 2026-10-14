"""Conservative resource typing and cached official availability checks."""
from datetime import datetime, timezone, timedelta
import json
import re
import urllib.request
from urllib.error import HTTPError

INVALID = {"deleted", "withdrawn", "invalid"}
PAPER_TYPES = {"journal_article", "conference_paper", "preprint"}
LABELS = {"journal_article": "正式期刊论文", "conference_paper": "正式会议论文", "preprint": "研究预印本",
          "dataset": "数据集", "software": "软件或代码资源", "other": "其他科研资源", "unknown": "类型未知"}


def formal_evidence(paper, kind):
    evidence = paper.get("publication_evidence") or {}
    expected = {"journal": {"journal-article", "article"}, "conference": {"proceedings-article", "conference-paper", "article"}}
    official = any(r.get("verified") and r.get("evidence", {}).get("url") for r in paper.get("conference_evidence", []))
    return (paper.get("publication_status") == "published" and paper.get("venue_type") == kind
            and not re.search(r"zenodo|figshare|dryad|dataverse", paper.get("venue", ""), re.I)
            and bool(paper.get("venue")) and
            ((evidence.get("source") in {"Crossref", "OpenAlex"} and evidence.get("type") in expected[kind]
              and bool(evidence.get("url"))) or (kind == "conference" and official)))


def resource_type(paper):
    # A repository copy can coexist with independently evidenced publication.
    if formal_evidence(paper, "journal"):
        return "journal_article"
    if formal_evidence(paper, "conference"):
        return "conference_paper"
    kind = str(paper.get("resource_metadata_type") or paper.get("publication_evidence", {}).get("type", "")).lower()
    if kind in {"dataset", "data-set"}:
        return "dataset"
    if kind in {"software", "code"}:
        return "software"
    if paper.get("arxiv_id"):
        return "preprint"
    repository = bool(re.search(r"zenodo|figshare|dryad|dataverse", " ".join(str(paper.get(k, "")) for k in ("doi", "venue", "original_url")), re.I))
    if repository:
        # Only classify explicit resource descriptions; do not infer from DOI alone.
        text = paper.get("title", "") + " " + paper.get("abstract", "")[:250]
        if re.search(r"\b(this dataset|a dataset|dataset of|data set)\b", text, re.I):
            return "dataset"
        if re.search(r"\b(software|source code)\b", text, re.I):
            return "software"
        if kind in {"publication", "preprint", "posted-content"}:
            return "preprint"
        return "other" if kind else "unknown"
    if paper.get("arxiv_id") or kind in {"preprint", "posted-content"}:
        return "preprint"
    return "other" if kind in {"other", "report", "book", "dissertation"} else "unknown"


def eligible_paper(paper):
    return paper.get("validity", {}).get("status") not in INVALID and resource_type(paper) in PAPER_TYPES


def request(url, timeout):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "RS-PaperClaw/validity", "Accept": "application/json"}), timeout=timeout) as response:
            body = response.read(300000).decode("utf-8", "replace")
            return response.status, response.url, body
    except HTTPError as exc:
        return exc.code, exc.url, exc.read(300000).decode("utf-8", "replace")


def check_record(paper, timeout=15):
    doi = paper.get("doi", "")
    zenodo = re.fullmatch(r"10\.5281/zenodo\.(\d+)", doi, re.I)
    figshare = doi.lower().startswith("10.6084/m9.figshare.")
    url = "https://zenodo.org/api/records/" + zenodo[1] if zenodo else "https://api.datacite.org/dois/" + doi if figshare else "https://doi.org/" + doi if doi else paper.get("arxiv_url") or paper.get("original_url")
    result = {"status": "unverified", "checked_at": datetime.now(timezone.utc).isoformat(), "url": url or "", "reason": "无可核验来源链接"}
    if not url:
        return result
    try:
        code, final, body = request(url, timeout)
        result.update(http_status=code, resolved_url=final)
        try:
            data = json.loads(body)
        except ValueError:
            data = {}
        if zenodo and code == 410 and "deleted" in str(data.get("message", "")).lower():
            result.update(status="deleted", reason="Zenodo 官方 API 明确返回记录已删除（410）")
        elif code in {401, 403, 429}:
            result.update(status="restricted", reason=f"访问或额度受限（HTTP {code}），不判为删除")
        elif code >= 400:
            result.update(status="temporary", reason=f"HTTP {code}，尚无明确删除/撤回证据")
        elif 200 <= code < 300:
            result.update(status="accessible", reason="来源响应正常；可访问不代表全文开放或学术质量")
            if zenodo:
                paper["resource_metadata_type"] = data.get("metadata", {}).get("resource_type", {}).get("type", "")
                paper["resource_access"] = data.get("metadata", {}).get("access_right", "unknown")
            elif figshare:
                paper["resource_metadata_type"] = data.get("data", {}).get("attributes", {}).get("types", {}).get("resourceTypeGeneral", "")
    except (OSError, ValueError) as exc:
        result.update(status="temporary", reason=f"{type(exc).__name__}：暂时无法核验，不判为删除")
    # Explicit metadata retraction survives a working DOI or a transient error.
    if paper.get("is_retracted") is True:
        result.update(status="withdrawn", reason="来源元数据明确标记 is_retracted=true")
    return result


def verify_records(library, keys, timeout=15, force=False, limit=20):
    checked = []
    for key in dict.fromkeys(keys):
        p = library["papers"][key]
        old = p.get("validity", {})
        if not force and old.get("checked_at"):
            try:
                if datetime.fromisoformat(old["checked_at"]) > datetime.now(timezone.utc) - timedelta(days=7):
                    continue
            except ValueError:
                pass
        if len(checked) >= limit:
            break
        result = check_record(p, timeout)
        # Never erase a confirmed invalid state just because a later check times out.
        if old.get("status") in INVALID and result["status"] not in INVALID:
            old["last_attempt"] = result
        else:
            p["validity"] = result
        checked.append(key)
    return checked
