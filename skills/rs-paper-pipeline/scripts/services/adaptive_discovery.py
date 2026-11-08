"""Bounded shortage recovery. Reuses the ordinary source, AI and translation code."""
import json,time,copy
from datetime import timedelta
from pathlib import Path

def settings():
 return json.loads((Path(__file__).resolve().parents[1]/'config/maritime/supplement.json').read_text(encoding='utf8'))

def complete_count(root,library,day):
 from services.mobile_digest import select_daily
 from services.reading_translation import cached
 rows,_=select_daily(root,library,day)
 return sum(bool(cached(p)) for p,_,_ in rows)

def jobs_for(root,library,venues,round_index,config):
 # Persist a cursor across recovery runs; neither repeat all daily jobs nor get
 # stuck forever at the same historical query/window.
 history=library.setdefault('supplement_history',[])
 tasks=[]
 for direction,queries in config['queries'].items():
  for query in queries:
   tasks.append({'source':'openalex','direction':direction,'journal':None,'query':query,'days':config['lookback_days']})
   if direction!='water':tasks.append({'source':'arxiv','direction':direction,'journal':None,'query':query,'days':config['lookback_days']})
   else:
    for journal in venues['journals']:
     if journal['enabled'] and journal['id'] in config['journal_ids']:
      tasks.append({'source':'crossref','direction':direction,'journal':journal,'query':query,'days':config['lookback_days']})
 from itertools import zip_longest
 groups=[[t for t in tasks if t['direction']==d] for d in config['queries']]
 tasks=[t for row in zip_longest(*groups) for t in row if t is not None]
 offset=library.get('supplement_cursor',0)%len(tasks)
 chosen=[tasks[(offset+i)%len(tasks)] for i in range(min(config['jobs_per_round'],len(tasks)))];library['supplement_cursor']=offset+len(chosen)
 return chosen

def recover(args,library,rules,day,save):
 from services.maritime import write_json
 from services.maritime_update import bounded_fetch
 from services.maritime_v2 import merge_records,assets
 from services.mobile_digest import hard_eligible,candidate_pool
 from services.semantic_evaluation import daily_evaluate,ranking_info
 from services.selected_translation import translate_selected
 config=settings();started=time.monotonic();rounds=[]
 if complete_count(args.root,library,day)==5:
  write_json(args.root/'docs/maritime-data/mobile/supplement-status.json',{'attempt_date':str(day),'complete':5,'rounds':rounds,'status':'complete'});return rounds
 # Reuse pending identities/cache and exhaust the existing queue before network.
 ai=daily_evaluate(args.root,library,[],day,limit=config['ai_limit'],disabled=getattr(args,'no_ai',False))
 library['supplement_existing_ai']=ai
 translate_selected(args.root,library,day,seconds=min(120,args.translation_timeout),enrichment=True);save()
 if complete_count(args.root,library,day)==5:
  write_json(args.root/'docs/maritime-data/mobile/supplement-status.json',{'attempt_date':str(day),'complete':5,'rounds':rounds,'status':'complete'});return rounds
 for index in range(config['max_rounds']):
  if time.monotonic()-started>=config['seconds']:break
  before=complete_count(args.root,library,day);record={'round':index+1,'date':str(day),'jobs':[]};new=[];t=time.monotonic()
  bounded=copy.copy(args);bounded.max_pages=1;bounded.retries=1;bounded.timeout=min(args.timeout,15);bounded.task_timeout=config['task_seconds']
  for job in jobs_for(args.root,library,assets()[0],index,{**config,'jobs_per_round':min(config['jobs_per_round'],max(3,(5-before)*2))}):
   if time.monotonic()-started+config['task_seconds']>=config['seconds']:break
   row={'source':job['source'],'query':job['query'],'direction':job['direction'],'journal':(job['journal'] or {}).get('id'),'start':str(day-timedelta(days=job['days']-1)),'end':str(day)}
   try:
    batch,done=bounded_fetch(job,bounded,day-timedelta(days=job['days']-1),day);prior=set(library['papers']);merge_records(library,batch,rules);ids=set(library['papers'])-prior;new.extend(ids)
    row.update(status='success' if done else 'incomplete',retrieved=len(batch),added=len(ids),source_eligible=sum(hard_eligible(library['papers'][k]) for k in ids))
   except Exception as exc:row.update(status='failed',error=str(exc))
   record['jobs'].append(row);save()
  record['added']=len(new)
  record['research_eligible']=sum(hard_eligible(library['papers'][k]) for k in new)
  record['ai']=daily_evaluate(args.root,library,new,day,limit=config['ai_limit'],disabled=getattr(args,'no_ai',False))
  record['ai_qualified']=sum(ranking_info(library['papers'][k])['eligible'] and hard_eligible(library['papers'][k]) for k in new)
  record['translation']=translate_selected(args.root,library,day,seconds=min(args.translation_timeout,120),enrichment=True)
  record.update(complete=complete_count(args.root,library,day),elapsed_seconds=round(time.monotonic()-t,2));record['gained']=record['complete']-before
  rounds.append(record);library.setdefault('supplement_history',[]).append(record);save()
  write_json(args.root/'docs/maritime-data/mobile/supplement-status.json',{'attempt_date':str(day),'complete':record['complete'],'rounds':rounds,'status':'complete' if record['complete']==5 else 'pending'})
  if record['complete']==5:break
 return rounds
