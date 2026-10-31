"""Deterministic daily-only domain gate; never changes AI fingerprints."""
import re

def exclusion(paper):
    title=paper.get('title','');abstract=paper.get('abstract','')
    disease=r"\b(?:cancer|alzheimer\w*|dementia|tumou?r|carcinoma|clinical|patient\w*|fetal|foetal|genom\w*|transcriptom\w*|gene expression|electrophysiolog\w*|electroencephalogra\w*|photoplethysmogra\w*|chest x-ray|chest radiograph\w*|brain MRI|medical imag\w*|biomedical|radiology|radiological)\b"
    signal=r"\b(?:EEG|PPG|ECG|MRI)\b"
    task=r"\b(?:brain|diagnos\w*|disease|physiological|health|medical|patient\w*|electro\w*|ultrasound|retrieval|staging)\b"
    hits=re.findall(disease,title,re.I)
    if not hits and re.search(signal,title) and re.search(task,title+' '+abstract,re.I):hits=re.findall(signal,title)
    if not hits:
        matches=re.findall(disease,abstract,re.I)
        if len(matches)>=2 and re.search(r'\b(?:dataset|patients|diagnosis|clinical|predict|staging|medical imaging)\w*\b',abstract,re.I):hits=matches
    if hits:return {'domain':'biomedical','reason':'医学研究对象/实验任务：'+', '.join(dict.fromkeys(hits))}
    return None
