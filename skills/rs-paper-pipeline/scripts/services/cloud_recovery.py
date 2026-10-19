"""Recover unsynced public results from the previous workflow's saved artifact."""
import json
from pathlib import Path


def restore(root, archive):
    from services.maritime import read_json,write_json,library_path
    from services.maritime_v2 import merge_records,retain_protected
    from services.filter_assets import load_maritime_assets
    from services.maritime_reading import cached_translation
    from services.semantic_evaluation import current_evaluation
    source=archive/'papers/maritime/library.json'
    if not source.exists():return {'status':'no_archive','added':0}
    incoming=read_json(source,{})
    current=read_json(library_path(root),{'papers':{},'days':{}})
    if any(p.get('reading') for p in incoming['papers'].values()):
        raise RuntimeError('Recovery artifact contains private reading data; preserved privately, not published')
    before=len(current['papers'])
    fresh=[p for k,p in incoming['papers'].items() if k not in current['papers']]
    merge_records(current,fresh,load_maritime_assets(),touch=False)
    for key,p in incoming['papers'].items():
        target=current['papers'].get(current.get('aliases',{}).get(key,key))
        if not target:continue
        retain_protected(target,p,key)
        if target.get('abstract')==p.get('abstract'):
            if cached_translation(p) and target.get('translation',{}).get('status')!='manual':target['translation']=p['translation']
            old=target.get('semantic')
            if current_evaluation(target) is None:
                target['semantic']=p.get('semantic')
                if current_evaluation(target) is None:target['semantic']=old
        for record in p.get('metadata_records',[]):
            if record not in target.setdefault('metadata_records',[]):target['metadata_records'].append(record)
        target['metadata_source']=sorted(set(target.get('metadata_source',[]))|set(p.get('metadata_source',[])))
        for field in ('last_seen','updated'):
            if p.get(field):target[field]=max(target.get(field,'') or '',p[field])
    for old,canonical in incoming.get('aliases',{}).items():
        canonical=current.get('aliases',{}).get(canonical,canonical)
        if canonical in current['papers']:current.setdefault('aliases',{}).setdefault(old,canonical)
    for day,record in incoming.get('days',{}).items():
        target=current.setdefault('days',{}).setdefault(day,{})
        for field in ('candidate_ids','searched_topics'):target[field]=sorted(set(target.get(field,[]))|set(record.get(field,[])))
    for record in incoming.get('source_runs',[]):
        if record not in current.setdefault('source_runs',[]):current['source_runs'].append(record)
    write_json(library_path(root),current)
    for name in ('semantic-cache.json','semantic-attempts.json'):
        path=root/'docs/maritime-data'/name
        saved=read_json(archive/'docs/maritime-data'/name,{'records':{}})
        existing=read_json(path,{'schema_version':1,'records':{}})
        for fingerprint,record in saved.get('records',{}).items():
            old=existing['records'].get(fingerprint)
            if old is None or (name=='semantic-attempts.json' and record.get('date','')>old.get('date','')):existing['records'][fingerprint]=record
        write_json(path,existing)
    for source in (archive/'docs/maritime-data/mobile/pending').glob('*.json'):
        path=root/'docs/maritime-data/mobile/pending'/source.name
        saved=read_json(source,{})
        existing=read_json(path,saved)
        rows={p['paper_id']:p for p in saved.get('reserve_papers',saved.get('papers',[]))}
        rows.update({p['paper_id']:p for p in existing.get('reserve_papers',existing.get('papers',[]))})
        existing['reserve_papers']=list(rows.values());write_json(path,existing)
    return {'status':'restored','added':len(current['papers'])-before}
