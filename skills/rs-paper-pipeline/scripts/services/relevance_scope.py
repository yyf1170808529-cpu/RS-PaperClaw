"""Daily eligibility evidence, independent of cached LLM scores."""
import re

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
    return not infrastructure(p) and bool(re.search(scene,text,re.I) and re.search(task,text,re.I))

def arxiv_preprint(p):
    value=p.get('arxiv_id') or ''
    if re.fullmatch(r'(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+/\d{7})(?:v\d+)?',str(value)):return True
    # A DOI or generic preprint type alone provides no arXiv evidence.
    return bool(re.fullmatch(r'https://(?:www\.)?arxiv\.org/(?:abs|pdf)/(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+/\d{7})(?:v\d+)?(?:\.pdf)?',str(p.get('arxiv_url') or '')) and 'arxiv' in str(p.get('metadata_source','')).lower())

def generic_method(p,value):
    title=p.get('title','');abstract=p.get('abstract','')
    mechanism=r'hard negative|contrastive (?:learning|representation|objective)|(?:cross.modal|transmodal) (?:alignment|representation|calibration)|representation calibration|differentiable (?:matching|assignment)|optimal transport|missing modal|modality.missing|uncertainty.aware|robust representation'
    if infrastructure(p):return False
    # Evidence must describe a reusable learning/matching mechanism, not just an architecture name.
    evidence=' '.join(e.get('quote_en','') for e in value.get('method_evidence',[]))
    mechanism+=r'|conditional random field|CRF|self.supervised learning|representation learning|contrastive learning|mask refinement'
    return bool(re.search(mechanism,title,re.I) and re.search(mechanism+r'|cross.covariance|whitened feature|rotation subspace',abstract+' '+evidence,re.I))
