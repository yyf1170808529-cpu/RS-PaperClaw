"""Single official page only; no crawling, login, PDF download or protection bypass."""
from html.parser import HTMLParser
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

from clients.scholarly_client import doi_id, strip_markup

ALLOWED = {"sciencedirect.com", "www.sciencedirect.com", "ieeexplore.ieee.org", "link.springer.com",
           "link.springernature.com", "linkinghub.elsevier.com", "www.nature.com", "nature.com", "www.mdpi.com", "mdpi.com"}


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.scripts, self.abstract = {}, [], []
        self.script = None
        self.capture = 0
        self.depth = 0
        self.abstract_complete = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            self.meta[(a.get("name") or a.get("property") or "").lower()] = a.get("content", "")
        if tag == "link" and a.get("rel") == "license":
            self.meta["article_license"] = a.get("href", "")
        if tag == "script":
            self.script = []
        if tag not in {"meta", "link", "br", "img", "input", "hr", "source"}:
            self.depth += 1
        if not self.capture and not self.abstract_complete and ((tag == "section" and a.get("data-title") == "Abstract") or
                (tag == "div" and {"abstract", "author"}.issubset(set(a.get("class", "").split())))):
            self.capture = self.depth

    def handle_endtag(self, tag):
        if tag in {"meta", "link", "br", "img", "input", "hr", "source"}:
            return
        if tag == "script" and self.script is not None:
            self.scripts.append("".join(self.script))
            self.script = None
        if self.capture == self.depth:
            self.capture = 0
            self.abstract_complete = True
        if tag not in {"meta", "link", "br", "img", "input", "hr", "source"}:
            self.depth = max(0, self.depth - 1)

    def handle_data(self, text):
        if self.script is not None:
            self.script.append(text)
        elif self.capture:
            self.abstract.append(text)


def extract_metadata(body, paper):
    from services.maritime_v2 import normalized_identity
    parser = MetadataParser()
    parser.feed(body)
    meta = parser.meta
    candidates = [{"doi": meta.get("citation_doi") or meta.get("dc.identifier"),
                   "title": meta.get("citation_title") or meta.get("dc.title"),
                   "abstract": meta.get("citation_abstract") or " ".join(parser.abstract),
                   "license": meta.get("article_license") or meta.get("dc.rights", "")}]
    for script in parser.scripts:
        try:
            # IEEE's explicit document metadata is a JSON object, not executed JS.
            marker = "global.document.metadata="
            if marker in script:
                data, _ = json.JSONDecoder().raw_decode(script.split(marker, 1)[1].lstrip())
                candidates.append({"doi": data.get("doi"), "title": data.get("documentTitle"), "abstract": data.get("abstract"), "license": data.get("license", "")})
                continue
            data = json.loads(script)
            nodes = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
            for node in nodes:
                if isinstance(node, dict) and node.get("abstract"):
                    identifier = node.get("identifier", node.get("doi", ""))
                    candidates.append({"doi": str(identifier), "title": node.get("headline") or node.get("name"),
                                       "abstract": node["abstract"], "license": str(node.get("license", ""))})
        except (ValueError, TypeError):
            continue
    for candidate in candidates:
        identifiers = re.findall(r"10\.\d{4,9}/[^\s\"'<>}]+", html.unescape(candidate.get("doi") or ""), re.I)
        if not any(doi_id(d.rstrip(".,")) == doi_id(paper.get("doi")) for d in identifiers):
            continue
        if normalized_identity(candidate.get("title") or "") != normalized_identity(paper.get("title", "")):
            continue
        abstract = strip_markup(candidate.get("abstract") or "")
        if len(abstract) < 80:
            continue
        license_url = re.fullmatch(r"https?://creativecommons\.org/(?:licenses/by/[0-9.]+|publicdomain/zero/[0-9.]+)/?", candidate.get("license", "").strip(), re.I)
        return {"abstract": abstract, "license_url": license_url[0] if license_url else "", "public_allowed": bool(license_url)}
    raise ValueError("No explicit abstract with matching DOI and complete title")


def fetch_publisher_abstract(paper, root, timeout=15):
    # DOI registry redirects directly to the official article. No guessed page grid.
    url = "https://doi.org/" + doi_id(paper.get("doi"))
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "RS-PaperClaw/metadata", "Accept": "text/html"}), timeout=timeout) as response:
        final = response.url
        if urllib.parse.urlsplit(final).hostname not in ALLOWED:
            raise ValueError("Publisher not in the existing limited official-page adapter")
        if "text/html" not in response.headers.get("Content-Type", ""):
            raise ValueError("Not an HTML article page; no PDF downloaded")
        body = response.read(2 * 1024 * 1024).decode("utf-8", "replace")
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    if title and strip_markup(title[1]).casefold() in {"client challenge", "access denied", "just a moment..."}:
        raise PermissionError("publisher_access_restricted: browser validation required; no bypass attempted")
    result = extract_metadata(body, paper)
    result.update(url=final, doi=paper["doi"], title=paper["title"])
    if not result["public_allowed"]:
        path = Path(root) / "papers/maritime/private/publisher-abstracts" / (hashlib.sha256(paper["doi"].encode()).hexdigest() + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
