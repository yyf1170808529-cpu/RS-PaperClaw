"""Conservative structural checks, preserving source text and human revisions."""
import copy
import hashlib
import re

HEADINGS = r'References|Bibliography|Перелік\s+посилань|Список\s+літератури'

def inspect_abstract(raw):
    raw = raw or ''
    dois = len(re.findall(r'10\.\d{4,9}/', raw))
    urls = len(re.findall(r'https?\s*:', raw))
    # A heading followed by several numbered citations is structural evidence.
    for match in re.finditer(r'(?<!\w)(?:'+HEADINGS+r')\s*:?(?=\s*(?:\[?1[.\]]|\n))', raw, re.I):
        tail = raw[match.end():]
        numbers = [int(n) for n in re.findall(r'(?:^|[\s.])\[?(\d{1,2})[.\]]\s+', tail)]
        if all(n in numbers for n in (1,2,3)) and len(re.findall(r'\b(?:19|20)\d{2}\b', tail)) >= 3:
            prefix = raw[:match.start()].strip()
            if len(prefix) >= 80:
                return {'status':'cleaned','clean':prefix,'reason':'Reference heading followed by numbered bibliography','cut_at':match.start()}
    # Only a line-oriented, consecutive citation tail without a heading can be cut.
    start = re.search(r'\n\s*(?:\[1\]|1\.)\s+', raw)
    if start:
        tail = raw[start.start():]
        numbers = re.findall(r'(?m)^\s*(?:\[(\d+)\]|(\d+)\.)\s+', tail)
        sequence = [int(a or b) for a,b in numbers]
        if sequence[:4] == [1,2,3,4] and len(re.findall(r'10\.\d{4,9}/',tail))>=3 and len(raw[:start.start()].strip())>=80:
            return {'status':'cleaned','clean':raw[:start.start()].strip(),'reason':'Consecutive numbered DOI citation tail','cut_at':start.start()}
    anomalies = []
    if re.search(r'(?<!\w)(?:'+HEADINGS+r')\s*:?(?=\s*(?:\[?1[.\]]|\n))',raw,re.I): anomalies.append('uncertain_reference_heading')
    if len(raw)>6000: anomalies.append('unusually_long')
    if dois>=4 or urls>=6: anomalies.append('many_dois_or_urls')
    if len(re.findall(r'[a-z][A-Z][a-z]{3,}',raw))>=15: anomalies.append('possibly_glued_text')
    return {'status':'review' if anomalies else 'validated' if raw.strip() else 'missing',
            'clean':'' if anomalies else raw,'reason':','.join(anomalies)}

def apply_quality(paper):
    current = paper.get('abstract') or ''
    # A new source version must not inherit the previous raw evidence.
    if 'raw_abstract' not in paper or current != paper.get('clean_abstract',current):
        raw = current
    else:
        raw = paper['raw_abstract']
    result = inspect_abstract(raw)
    changed = current != result['clean']
    if paper.get('raw_abstract') not in (None,raw):
        paper.setdefault('abstract_history',[]).append({'raw':paper['raw_abstract'],'source':copy.deepcopy(paper.get('abstract_source',{}))})
    paper['raw_abstract'] = raw
    paper['clean_abstract'] = paper['abstract'] = result.pop('clean')
    paper['abstract_quality'] = {**result,'raw_hash':hashlib.sha256(raw.encode()).hexdigest()}
    translation = paper.get('translation',{})
    digest = hashlib.sha256(paper['abstract'].encode()).hexdigest()
    if translation.get('status')=='machine' and translation.get('english_hash')!=digest:
        paper.setdefault('translation_history',[]).append(copy.deepcopy(translation))
        paper['translation']={'status':'stale','zh':'','english_hash':digest,'error_type':'abstract_changed'}
        paper['translation_pending']=True
    return changed

def application(paper, policy):
    """Scene evidence from the title or sentences describing the study, never citations."""
    from services.maritime import has
    title = paper.get('title') or ''
    abstract = paper.get('abstract') or ''
    terms = policy['signals']['maritime']
    contexts = [s for s in re.split(r'(?<=[.!?])\s+',abstract) if any(has(s,t) for t in terms) and
                re.search(r'\b(ship|ships|vessel|vessels|AIS|navigation|port|harbou?r|maritime|marine)\b',s,re.I) and
                re.search(r'\b(detect\w*|track\w*|dataset\w*|experiment\w*|perception|fusion|monitor\w*|we|propos\w*|study|paper|method)\b',s,re.I)]
    water = any(has(title,t) for t in terms) or bool(contexts)
    text=title+'\n'+abstract
    land = any(has(text,t) for t in policy['signals']['traffic'])
    return 'water' if water else 'land' if land else 'general' if paper.get('assessment',{}).get('primary_topic') or any(has(text,t) for t in policy['signals']['perception']+policy['signals']['method']) else 'other'
