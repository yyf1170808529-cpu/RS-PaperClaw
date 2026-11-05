"""Daily eligibility evidence, independent of cached LLM scores."""
import re

def primary_scope_exclusion(p):
    """Study objective evidence, not keywords found only in evaluation scenes."""
    title=p.get('title','')
    abstract=p.get('abstract','')
    rules=[('communication_engineering',r'semantic communication|(?:adaptive )?pilot (?:selection|allocation|configuration)|channel estimation|communication resource allocation|waveform optimi[sz]ation|wireless communication protocols?',
            '通信系统/波形/导频优化'),
           ('security_centric',r'cybersecurity|(?:security|stereo vision|camera) vulnerabilit\w*|physical adversarial attacks?|network intrusion|attack exploitation|security threat assessment',
            '安全攻击或漏洞分析'),
           ('specialized_industrial_inspection',r'(?:industrial|manufacturing|steel|weld|fabric|wafer) (?:surface )?(?:defect|flaw|inspection)\w*',
            '无关专用工业巡检')]
    # A reusable perception defense can use attacks as evaluation. Neither ISAC
    # nor adversarial/robust alone is a negative research objective.
    for domain,pattern,reason in rules:
        match=re.search(pattern,title,re.I)
        if domain=='security_centric' and match and re.search(r'(?:representation learning|feature learning|multimodal fusion|cross.modal alignment).*(?:under|against|evaluated)',title,re.I):
            # The learning mechanism is the object; attacks are its stress test.
            match=None
        if match:return {'domain':domain,'reason':reason+'：'+match[0],'evidence':title}
        for sentence in re.split(r'(?<=[.!?])\s+',abstract):
            if re.search(r'\b(?:we|our|this (?:paper|work|study))\b',sentence,re.I) and re.search(r'propos|optimi[sz]|reveal|exploit|investigat|develop|introduc',sentence,re.I):
                match=re.search(pattern,sentence,re.I)
                if match:return {'domain':domain,'reason':reason+'：'+match[0],'evidence':sentence}
    return None

def research_directions(p):
    """Independent content directions A-D; does not determine venue quality."""
    if primary_scope_exclusion(p) or infrastructure(p):return []
    text=p.get('title','')+' '+p.get('abstract','')
    directions=[]
    if re.search(r'\bAIS\b|automatic identification system',text,re.I) and re.search(r'vision|visual|radar|associat|match|fusion',text,re.I):directions.append('A')
    if re.search(r'\b(?:vessel|ship|maritime)\b',text,re.I) and re.search(r'detect|segment|track|depth|enhance|perception|restorat',text,re.I):directions.append('B')
    if traffic_task(p):directions.append('C')
    if generic_method(p,{}):directions.append('D')
    return directions

def infrastructure(p):
    title=p.get('title','');abstract=p.get('abstract','')
    pattern=r'\b(?:(?:pavement|asphalt|road surface|bridge|concrete|structural)\s+(?:crack\w*|defect\w*|damage|distress|maintenance|inspection)|road (?:infrastructure )?(?:inspection|maintenance)|infrastructure inspection)\b'
    hits=re.findall(pattern,title,re.I)
    if not hits:
        hits=[s for s in re.split(r'(?<=[.!?])\s+',abstract) if re.search(pattern,s,re.I) and re.search(r'we |our |propos|develop|dataset|experiment',s,re.I)]
    return {'domain':'infrastructure_inspection','reason':'基础设施病害/巡检研究：'+hits[0][:180]} if hits else None

def traffic_task(p):
    text=p.get('title','')+' '+p.get('abstract','')
    scene=r'autonomous driving|self.driving|traffic (?:scene|surveillance|monitoring|participant)|road (?:user|scene)|vehicle|pedestrian|vehicle.infrastructure|roadside cooperative'
    task=r'detect\w*|track\w*|perception|segment\w*|sensor fusion|multimodal fusion|multi.modal fusion'
    return not (infrastructure(p) or primary_scope_exclusion(p)) and bool(re.search(scene,text,re.I) and re.search(task,text,re.I))

def arxiv_preprint(p):
    value=p.get('arxiv_id') or ''
    if re.fullmatch(r'(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+/\d{7})(?:v\d+)?',str(value)):return True
    # A DOI or generic preprint type alone provides no arXiv evidence.
    return bool(re.fullmatch(r'https://(?:www\.)?arxiv\.org/(?:abs|pdf)/(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+/\d{7})(?:v\d+)?(?:\.pdf)?',str(p.get('arxiv_url') or '')) and 'arxiv' in str(p.get('metadata_source','')).lower())

def generic_method(p,value):
    title=p.get('title','');abstract=p.get('abstract','')
    mechanism=r'hard negative|contrastive (?:learning|representation|objective)|(?:cross.modal|transmodal) (?:alignment|representation|calibration)|representation calibration|differentiable (?:matching|assignment)|optimal transport|missing modal|modality.missing|uncertainty.aware|robust representation'
    if infrastructure(p) or primary_scope_exclusion(p):return False
    # Evidence must describe a reusable learning/matching mechanism, not just an architecture name.
    evidence=' '.join(e.get('quote_en','') for e in value.get('method_evidence',[]))
    mechanism+=r'|conditional random field|CRF|self.supervised learning|representation learning|contrastive learning|mask refinement'
    return bool(re.search(mechanism,title,re.I) and re.search(mechanism+r'|cross.covariance|whitened feature|rotation subspace',abstract+' '+evidence,re.I))
