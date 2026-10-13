"""Optional CPU translation and private single-paper PDF preparation."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import importlib.util


def translate_one(paper, translator=None):
    original = paper.get("abstract", "")
    digest = hashlib.sha256(original.encode()).hexdigest()
    previous = paper.get("translation", {})
    if previous.get("status") == "manual" or (previous.get("english_hash") == digest and previous.get("status") == "machine"):
        return previous
    if not original:
        return {"status": "missing_english", "zh": "", "english_hash": digest}
    try:
        if translator is None:
            os.environ["ARGOS_DEVICE_TYPE"] = "cpu"
            from argostranslate import translate
            languages = translate.get_installed_languages()
            en = next((lang for lang in languages if lang.code == "en"), None)
            zh = next((lang for lang in languages if lang.code == "zh"), None)
            if not en or not zh:
                raise RuntimeError("Install the optional en→zh Argos model first")
            translator = en.get_translation(zh).translate
        protected = {}
        def protect(match):
            token = f"ZXQTERM{len(protected)}QXZ"
            protected[token] = match.group(0)
            return token
        text = re.sub(r"\$[^$]+\$|\b(?:AIS|Radar|LiDAR|DETR|[A-Z][A-Z0-9_-]{2,})\b", protect, original)
        translated = translator(text)
        if any(token not in translated for token in protected):
            raise RuntimeError("Model changed protected technical terms; manual revision required")
        for token, term in protected.items():
            translated = translated.replace(token, term)
        if not re.search(r"[\u4e00-\u9fff]", translated):
            raise RuntimeError("Translation contains no Chinese text")
        return {"status": "machine", "engine": "Argos Translate (CPU)", "zh": translated,
            "english_hash": digest, "updated_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        return {**previous, "status": "failed", "zh": previous.get("zh", ""), "error": str(exc), "english_hash": digest}


def install_model(path=None):
    from argostranslate import package
    if path:
        package.install_from_path(path)
    else:
        package.update_package_index()
        model = next(p for p in package.get_available_packages() if p.from_code == "en" and p.to_code == "zh")
        package.install_from_path(model.download())


def translate_available(library, keys):
    """Fetch never installs/downloads translation dependencies or models."""
    if importlib.util.find_spec("argostranslate") is None:
        return
    for key in keys:
        paper = library["papers"][key]
        if paper.get("abstract") and paper.get("assessment", {}).get("level") != "excluded":
            paper["translation"] = translate_one(paper)


def prepare_pdf(paper, root, local_file=None, extract=False, timeout=20):
    private = root / "papers/maritime/private/reading" / hashlib.sha256(paper["paper_id"].encode()).hexdigest()[:16]
    private.mkdir(parents=True, exist_ok=True)
    target = private / "paper.pdf"
    if local_file:
        data, origin = local_file.read_bytes(), "user-selected local PDF"
    else:
        url = paper.get("open_access_url") or (paper.get("pdf_url") if paper.get("arxiv_id") else "")
        if not url or not (paper.get("arxiv_id") or paper.get("oa_evidence")):
            raise RuntimeError("no_authorized_pdf_found: provide --file with a legally obtained PDF")
        if not url.startswith("https://"):
            raise ValueError("Only HTTPS OA PDF URLs are accepted")
        if target.exists() and target.read_bytes()[:5] == b"%PDF-":
            data = target.read_bytes()
        else:
            request = urllib.request.Request(url, headers={"User-Agent": "RS-PaperClaw-Maritime/2.0", "Accept": "application/pdf"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read(50 * 1024 * 1024 + 1)
        origin = url
    if len(data) > 50 * 1024 * 1024 or not data.startswith(b"%PDF-"):
        raise ValueError("pdf_fetch_failed: not a PDF signature or exceeds 50 MB")
    target.write_bytes(data)
    prompt = (Path(__file__).resolve().parents[1] / "prompts/maritime_analysis.md").read_text(encoding="utf-8")
    values = {**paper, "authors": ", ".join(paper.get("authors", [])),
        "pdf_url": paper.get("open_access_url") or paper.get("pdf_url", "")}
    prompt = re.sub(r"\{\{(\w+)\}\}", lambda match: str(values.get(match.group(1), "")), prompt)
    (private / "prompt.md").write_text(prompt + "\n请手动上传本目录 paper.pdf，以实际上传的 PDF 为全文证据。\n", encoding="utf-8")
    manifest = {"paper_id": paper["paper_id"], "doi": paper.get("doi"), "title": paper["title"], "origin": origin,
        "status": "local_pdf_prepared" if local_file else "open_access_downloaded", "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "extraction": "not_requested"}
    if extract:
        binary = shutil.which("pdftotext")
        if not binary:
            manifest["extraction"] = "pdftotext_unavailable"
        else:
            result = subprocess.run([binary, "-layout", str(target), str(private / "paper.txt")], capture_output=True, timeout=60)
            manifest["extraction"] = "success" if result.returncode == 0 else "failed"
            if result.returncode == 0:
                text = (private / "paper.txt").read_text(encoding="utf-8", errors="replace")
                manifest["title_text_check"] = " ".join(paper["title"].lower().split())[:45] in " ".join(text.lower().split())
                manifest["text_characters"] = len(text)
    (private / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PDF + Prompt prepared privately: {private}")
    return manifest
