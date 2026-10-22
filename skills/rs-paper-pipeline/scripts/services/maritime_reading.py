"""Optional CPU translation and private single-paper PDF preparation."""
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import importlib.util

MATH_PATTERN=r'\$\$[\s\S]+?\$\$|(?<!\\)\$(?:\\.|[^$])+\$|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\]'
TECH_PATTERN=r'\b(?:v\d+(?:\.\d+)*|(?=[A-Za-z0-9-]*(?:[A-Z]{2}|\d|[a-z][A-Z]))[A-Z][A-Za-z0-9]*(?:-(?:[A-Z0-9][A-Za-z0-9]*|v\d+))+|[A-Z][a-z]+\d+[A-Za-z0-9]*|[A-Z]{2,}[a-z]+[A-Za-z0-9_]*|\d+[A-Za-z][A-Za-z0-9_]*|[A-Za-z0-9_]*[a-z][A-Z][A-Za-z0-9_]*|[A-Z][A-Z0-9]{1,})\b'


def repeated_text(text):
    return bool(re.search(r"([\u4e00-\u9fff][\u4e00-\u9fff，、, ]{1,18})\1{3,}", text))


def translation_warnings(english,chinese):
    """Review suggestions do not hide a structurally valid cached translation."""
    warnings=[]
    terms=json.loads((Path(__file__).resolve().parents[1]/'config/maritime/translation_terms.json').read_text(encoding='utf8'))
    for term,expected in terms.items():
        if re.search(r'\b'+re.escape(term)+r'\b',english,re.I) and expected not in chinese:
            warnings.append('terminology_review: '+term+' → '+expected)
    if english and not .25<=len(chinese)/len(english)<=1.5:warnings.append('length_ratio_review')
    return warnings


def translation_error(english, chinese):
    """Conservative structural checks; these do not certify translation accuracy."""
    if not isinstance(chinese, str) or not re.search(r"[\u4e00-\u9fff]", chinese):
        return "no_chinese: translation contains no Chinese text"
    if re.search(r"保险丝|硬底片|变压器|硬负面|硬负片", chinese):
        return "terminology: obvious technical mistranslation"
    numbers = lambda text: Counter(re.sub(r"\s+", "", n) for n in re.findall(r"\d+(?:\.\d+)?(?:\s*%)?", text))
    source_numbers, target_numbers = numbers(english), numbers(chinese)
    # Argos may render spelled-out "five benchmarks" as "5个基准". Such a
    # supported conversion is not an added experimental result.
    spelled = {word:str(i) for i,word in enumerate(('zero','one','two','three','four','five','six','seven','eight','nine','ten'))}
    allowed = Counter(spelled[word.lower()] for word in re.findall(r'\b(?:'+'|'.join(spelled)+r')\b', english, re.I))
    if source_numbers - target_numbers or (target_numbers - source_numbers) - allowed:
        return "numeric_mismatch: numbers or percentages changed"
    for url in re.findall(r'https?://[^\s<>]+', english):
        if url not in chinese:
            return 'protected_url_missing: ' + url
    for formula,count in Counter(re.findall(MATH_PATTERN,english)).items():
        if chinese.count(formula)<count:return 'protected_formula_missing: '+formula
    source_text=re.sub(MATH_PATTERN,'',re.sub(r'https?://[^\s<>]+','',english))
    tokens=re.findall(TECH_PATTERN,source_text)
    terms=json.loads((Path(__file__).resolve().parents[1]/'config/maritime/translation_terms.json').read_text(encoding='utf8'))
    metric_names={'AP':('平均精度','平均精确率'),'mAP':('平均精度均值','平均精确率均值')}
    metric_context=bool(re.search(r'\bmAP\b|\bAP@',english) or re.search(r'average\s+precision|\b(?:detection|segmentation|metric|precision)\b',english,re.I))
    for token, count in Counter(tokens).items():
        preserved=len(re.findall(r'(?<![A-Za-z0-9_])'+re.escape(token)+r'(?![A-Za-z0-9_])',chinese))
        alternatives=(metric_names.get(token,()) if metric_context else ()) or ((terms[token.lower()],) if token.lower() in terms else ())
        translated=sum(len(re.findall(re.escape(t)+(r'(?!均值)' if token=='AP' else ''),chinese)) for t in alternatives)
        if preserved+translated<count:
            return "protected_token_missing: " + token
    if len(chinese) < len(english) * .12 or len(chinese) > len(english) * 2:
        return "length_mismatch: possible omission or repeated text"
    sentences = [s.strip() for s in re.split(r"[。！？.!?]", chinese) if len(s.strip()) >= 30]
    if repeated_text(chinese) or len(sentences) != len(set(sentences)):
        return "repeated_sentence: duplicated long sentence"
    return None


def cached_translation(paper):
    value = paper.get("translation", {})
    return (value.get("status") == "machine"
            and value.get("english_hash") == hashlib.sha256(paper.get("abstract", "").encode()).hexdigest()
            and translation_error(paper.get("abstract", ""), value.get("zh")) is None)


def configure_argos():
    private = Path(__file__).resolve().parents[4] / "papers/maritime/private/translation"
    for variable, folder in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache"), ("STANZA_RESOURCES_DIR", "stanza")):
        os.environ.setdefault(variable, str(private / folder))
    os.environ["ARGOS_DEVICE_TYPE"] = "cpu"
    os.environ.setdefault("ARGOS_INTRA_THREADS", "2")
    os.environ.setdefault("OMP_NUM_THREADS", "2")


def argos_translator(resources_path=None):
    """Use installed Argos decoder; avoid incompatible legacy Stanza sentence splitting."""
    configure_argos()
    from argostranslate import translate
    import stanza
    languages=translate.get_installed_languages()
    en=next((x for x in languages if x.code=='en'),None)
    zh=next((x for x in languages if x.code=='zh'),None)
    if not en or not zh:raise RuntimeError('Install the optional en→zh Argos model first')
    pair=en.get_translation(zh)
    packaged=getattr(pair,'underlying',pair)
    sentencizer=getattr(packaged,'sentencizer',None)
    if sentencizer is not None and hasattr(sentencizer,'stanza_pipeline') and sentencizer.stanza_pipeline is None:
        directory=packaged.pkg.package_path/'stanza'
        resource=Path(resources_path) if resources_path else directory/'resources.json'
        content=json.loads(resource.read_text(encoding='utf8'))
        lang=sentencizer.stanza_lang_code
        class OfflineEnglishSentencizer:
            def split_sentences(self,text):
                return [x for x in re.split(r'(?<=[.!?])\s+(?=[A-Z])',text) if x.strip()]
        if 'packages' not in content.get(lang,{}):
            # Legacy Argos tokenizer weights also lack newer Stanza feat_dropout.
            # Keep the installed Argos decoder; English boundary splitting needs no model.
            packaged.sentencizer=OfflineEnglishSentencizer()
        else:
            try:
                sentencizer.stanza_pipeline=stanza.Pipeline(lang=lang,dir=str(directory),resources_filepath=str(resource),
                    processors='tokenize',use_gpu=False,download_method=None,logging_level='WARNING')
            except (KeyError,FileNotFoundError):
                # A cache may contain refreshed JSON but old or incomplete SBD weights.
                # This fallback never replaces or hides a missing translation decoder.
                packaged.sentencizer=OfflineEnglishSentencizer()
    def inference(text):
        values=pair.hypotheses(text,num_hypotheses=4)
        return next((v.value for v in values if v.value.strip() and len(v.value)>=len(text)*.08 and not repeated_text(v.value)),'')
    return inference


def translation_smoke():
    result=translate_one({'abstract':'We propose a robust object tracking method.'})
    if result.get('status')!='machine':raise RuntimeError('Argos smoke failed: '+result.get('error','unknown'))
    return {'status':'success','english':'We propose a robust object tracking method.','chinese':result['zh']}


def translate_one(paper, translator=None):
    from services.abstract_quality import apply_quality
    apply_quality(paper)
    original = paper.get("abstract", "")
    digest = hashlib.sha256(original.encode()).hexdigest()
    previous = paper.get("translation", {})
    if previous.get("status") == "manual" or cached_translation(paper):
        return previous
    if not original:
        return {"status": "missing_english", "error_type": "missing_english", "zh": "", "english_hash": digest}
    try:
        if translator is None:
            translator = argos_translator()
        terms = json.loads((Path(__file__).resolve().parents[1] / "config/maritime/translation_terms.json").read_text(encoding="utf-8"))
        phrases = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
        pattern = r'(https?://[^\s<>]+|'+MATH_PATTERN+r'|(?i:\b(?:'+phrases+r')\b)|'+TECH_PATTERN+r'|\b\d+(?:\.\d+)*(?:\s*%|[MG])?\b)'
        parts = re.split(pattern, original)
        retries=[]
        # Both word and number placeholders altered model output in real tests.
        # Keep terms and boundary punctuation outside the model instead.
        def prose(part):
            if not re.search(r"[A-Za-z]", part):
                return part
            match = re.fullmatch(r"(\W*)(.*?)(\W*)", part, re.S)
            leading, body, trailing = match.groups()
            connectors = {"a":"", "an":"", "the":"", "and":"和", "or":"或", "of":"的", "on":"在", "with":"结合", "to":"以", "by":"通过", "for":"用于", "in":"在", "from":"来自"}
            if body.casefold() in connectors:
                return leading + connectors[body.casefold()] + trailing
            result = translator(body)
            if not result.strip():
                # Stanza can omit an unfinished fragment at a protected term
                # boundary. Terminal punctuation keeps the same source words.
                result = translator(body + '.').rstrip('.。')
            issue=translation_error(body,result) if isinstance(result,str) and result.strip() else 'translation_incomplete'
            if issue and issue.startswith(('numeric_mismatch','protected_','translation_incomplete')):
                retries.append({'segment':body[:120],'reason':issue})
                result=translator(body+'.').rstrip('.。')
                issue=translation_error(body,result)
                if issue and issue.startswith(('numeric_mismatch','protected_','translation_incomplete')):
                    raise ValueError(issue+'; segment: '+body[:120])
            if not isinstance(result, str) or not result.strip() or len(result) < len(body) * .08:
                raise ValueError("translation_incomplete: model omitted segment: " + body[:80])
            return leading + result + trailing
        translated = "".join(terms.get(part.lower(), part) if i % 2 else prose(part)
                             for i, part in enumerate(parts))
        if any(terms.get(part.lower(), part) not in translated for part in parts[1::2]):
            raise ValueError("term_restoration_failed: protected terminology missing")
        if not re.search(r"[\u4e00-\u9fff]", translated):
            raise RuntimeError("Translation contains no Chinese text")
        error = translation_error(original, translated)
        if error:
            raise ValueError(error)
        return {"status": "machine", "engine": "Argos Translate (CPU)", "zh": translated,
            "english_hash": digest, "protection_revision": 8, "segment_retries":retries,"quality_warnings":translation_warnings(original,translated),
            "updated_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        category = "dependency_missing" if isinstance(exc, ModuleNotFoundError) else "model_missing" if "optional en" in str(exc) else "translation_validation_failed" if isinstance(exc, ValueError) else "model_runtime_error"
        return {**previous, "status": "failed", "zh": previous.get("zh", ""), "error": str(exc), "error_type": category,
                "candidate_zh":locals().get('translated',''),"segment_retries":locals().get('retries',[]),
                "english_hash": digest, "updated_at": datetime.now(timezone.utc).isoformat()}


def install_model(path=None):
    configure_argos()
    from argostranslate import package
    if path:
        package.install_from_path(path)
    else:
        if any(p.from_code == "en" and p.to_code == "zh" for p in package.get_installed_packages()):
            print("English-to-Chinese model already installed; no download needed.")
            return
        package.update_package_index()
        model = next(p for p in package.get_available_packages() if p.from_code == "en" and p.to_code == "zh")
        package.install_from_path(model.download())


def translate_available(library, keys):
    """Fetch never installs/downloads translation dependencies or models."""
    counts = {"translated": 0, "cached": 0, "failed": 0, "missing_english": 0, "manual": 0}
    for key in keys:
        paper = library["papers"][key]
        if paper.get("assessment", {}).get("level") != "excluded":
            previous = paper.get("translation", {})
            paper["translation"] = translate_one(paper)
            result = paper["translation"]
            outcome = "manual" if result["status"] == "manual" else "cached" if result is previous else "translated" if result["status"] == "machine" else "missing_english" if result["status"] == "missing_english" else "failed"
            counts[outcome] += 1
            print(f"翻译 {key}: {outcome}" + (f" ({result.get('error_type')})" if outcome == "failed" else ""), flush=True)
    return counts


def prepare_pdf(paper, root, local_file=None, extract=False, timeout=20):
    from services.maritime_validity import eligible_paper
    if not eligible_paper(paper):
        raise ValueError("Only valid research papers use the full-paper reading template")
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


def translation_order(library):
    from services.maritime_v2 import rank_key
    return [p["paper_id"] for p in sorted(library["papers"].values(), key=lambda p: (p.get("assessment", {}).get("level") == "high", bool(p.get("quality", {}).get("high_journal") or p.get("quality", {}).get("ccf_a")), rank_key(p)), reverse=True)]


def translate_history(root, library, rules, max_papers, seconds, batches=1, retry_failed=False):
    from services.maritime import library_path, write_json, build, load_library
    from services.maritime_update import translate_budget
    from update_maritime import update_lock
    results = []
    with update_lock(root / "papers/maritime/private/update.lock"):
        library.clear()
        library.update(load_library(root))
        for index in range(batches):
            started = datetime.now(timezone.utc).isoformat()
            print(f"历史翻译批次 {index+1}/{batches}：每批最多{max_papers}篇，预算{seconds}s", flush=True)
            result = translate_budget(library, translation_order(library), max_papers, seconds, lambda: write_json(library_path(root), library), retry_failed)
            result.update(started_at=started, completed_at=datetime.now(timezone.utc).isoformat())
            library.setdefault("translation_batches", []).append(result)
            write_json(library_path(root), library)
            results.append(result)
            if not result["pending"] or result["failed"]:
                break
        build(root, library, rules)
        write_json(library_path(root), library)
    return results
