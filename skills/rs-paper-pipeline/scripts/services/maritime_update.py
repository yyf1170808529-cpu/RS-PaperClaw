"""One sequential multi-source update, retaining every successful batch."""
from datetime import datetime, timedelta, timezone
import json
import time
import importlib.util

from clients import arxiv_client, scholarly_client
from services import maritime_v2 as v2, maritime_reading as reading


def update_jobs(args, venues):
    policy = json.loads((v2.CONFIG_DIR / "discovery.json").read_text(encoding="utf-8"))
    jobs = []
    for direction, config in policy.items():
        days = 365 if direction == "water" and args.bootstrap else config["days"]
        for source in ("crossref", "openalex", "arxiv"):
            if args.source and source not in args.source:
                continue
            journals = [j for j in venues["journals"] if j["enabled"] and
                        (j["id"] in args.journal if args.journal else j["id"] in config.get("journal_ids", []))] if source == "crossref" else [None]
            for journal in journals:
                for query in config.get(source, []):
                    if args.query and args.query != query:
                        continue
                    jobs.append({"source": source, "direction": direction, "days": days, "journal": journal, "query": query})
    return jobs


def fetch_job(job, args, start, end):
    if job["source"] == "crossref":
        return scholarly_client.fetch_crossref(job["journal"], str(start), str(end), job["query"], args.root,
            args.max_pages, min(args.page_size, 100), args.timeout, args.retries)
    if job["source"] == "openalex":
        return scholarly_client.fetch_openalex(str(start), str(end), job["query"], args.root,
            args.max_pages, min(args.page_size, 100), args.timeout, args.retries)
    time.sleep(3)
    complete=True
    try:
        batch = arxiv_client.fetch_topic_candidates(job["query"], str(start), str(end), args.page_size,
            args.max_pages, args.retries, args.timeout)
    except arxiv_client.ArxivUnavailableError as exc:
        if not job.get('supplement') or not getattr(exc,'partial_results',None):raise
        batch=exc.partial_results;complete=False
    for p in batch:
        p.update(paper_id=p["arxiv_id"], publication_date=p["published"], metadata_source=["arXiv"])
    return batch, complete


def _fetch_worker(queue, job, args, start, end):
    try:
        queue.put((True, fetch_job(job, args, start, end)))
    except Exception as exc:
        queue.put((False, str(exc)))


def bounded_fetch(job, args, start, end):
    if not args.task_timeout:
        return fetch_job(job, args, start, end)
    import multiprocessing
    from queue import Empty
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_fetch_worker, args=(queue, job, args, start, end))
    process.start()
    deadline = time.monotonic() + args.task_timeout
    try:
        while time.monotonic() < deadline:
            try:
                ok, result = queue.get(timeout=min(15, max(.01, deadline - time.monotonic())))
                if not ok:
                    raise RuntimeError(result)
                return result
            except Empty:
                print(f"仍在检索 {job['source']} / {job['direction']}，任务上限 {args.task_timeout}s", flush=True)
                if not process.is_alive():
                    raise RuntimeError("Source worker exited without a result")
        raise TimeoutError(f"Task exceeded {args.task_timeout}s; successful earlier batches retained")
    finally:
        if process.is_alive():
            process.terminate()
        process.join()
        queue.close()


def translate_budget(library, keys, limit, seconds, save, retry_failed=True, selected=False):
    # Compatibility for historical local data: never infer or pay on the full library.
    counts={k:0 for k in ('translated','cached','manual','failed','missing_english','pending','skipped_failed')}
    for key in dict.fromkeys(keys):
        p=library['papers'][key];value=p.get('translation',{})
        if value.get('status')=='manual':counts['manual']+=1
        elif not p.get('abstract'):counts['missing_english']+=1
        elif reading.cached_translation(p):counts['cached']+=1
        elif value.get('status')=='failed' and not retry_failed:counts['skipped_failed']+=1
        else:counts['pending']+=1
    return counts


def run_update(args, library, rules):
    from services.maritime import today, write_json, library_path, build
    from services.maritime_metadata import enrich_missing
    from services.maritime_validity import verify_records
    end = datetime.strptime(args.date.replace("-", ""), "%Y%m%d").date() if args.date else today()
    venues, policy = v2.assets()
    jobs = [] if __import__("os").environ.get("RS_RESUME_ONLY")=="1" else update_jobs(args, venues)
    if not jobs and __import__("os").environ.get("RS_RESUME_ONLY")!="1":
        raise ValueError("No matching source/query jobs")
    before_count = len(library["papers"])
    run_id = datetime.now(timezone.utc).isoformat()
    results = []
    started = time.monotonic()
    save = lambda: write_json(library_path(args.root), library)
    print(f"[1/4] 检索新论文：开始，共 {len(jobs)} 项来源任务", flush=True)
    merged = 0
    added = 0
    new_keys = []
    for index, job in enumerate(jobs, 1):
        start = end - timedelta(days=job["days"] - 1)
        status = {"run_id": run_id, "time": datetime.now(timezone.utc).isoformat(), "source": job["source"],
                  "direction": job["direction"], "journal": job["journal"]["id"] if job["journal"] else None,
                  "query": job["query"], "start": str(start), "end": str(end)}
        task_started = time.monotonic()
        print(f"[1/4] {index}/{len(jobs)}：{job['source']} / {status['journal'] or job['direction']} 开始", flush=True)
        try:
            batch, complete = bounded_fetch(job, args, start, end)
            size = len(library["papers"])
            previous_keys = set(library["papers"])
            removed = v2.merge_records(library, batch, rules)
            new_keys.extend(k for k in library["papers"] if k not in previous_keys)
            merged += removed
            added += len(library["papers"]) - size + removed
            status.update(status="success" if complete else "incomplete", candidate_count=len(batch))
        except Exception as exc:
            status.update(status="failed", error=str(exc))
        status["elapsed_seconds"] = round(time.monotonic()-task_started, 2)
        library.setdefault("source_runs", []).append(status)
        save()
        results.append(status)
        print(json.dumps(status, ensure_ascii=False), flush=True)
    print(f"[1/4] 检索结束，耗时 {time.monotonic()-started:.1f}s", flush=True)
    stage = time.monotonic()
    print("[2/4] 去重与摘要补全：开始（使用已有来源缓存）", flush=True)
    dedup = v2.deduplicate_library(library, rules)
    merged += dedup["merged"]
    metadata = enrich_missing(library, rules, args.root, network=False)
    # Missing abstracts must not permanently hide newly discovered core maritime
    # journal papers. Reuse the existing bounded enrichment chain, with cooldown.
    priority=[k for k,p in library['papers'].items() if p.get('application_bucket')=='water'
              and p.get('quality',{}).get('high_journal') and not p.get('abstract')
              and p.get('abstract_check',{}).get('time','')[:10]!=str(end)]
    priority.sort(key=lambda k:('A' in library['papers'][k].get('research_directions',[]),library['papers'][k].get('last_seen','')),reverse=True)
    if priority:
        filled=enrich_missing(library,rules,args.root,keys=priority,limit=3,timeout=min(args.timeout,10),retries=1)
        metadata['filled']+=filled['filled']
        metadata['priority_enrichment']=filled
    focus = v2.recommendation_view(list(library["papers"].values()), policy, end)["paper_ids"]
    # Cached checks are bounded; no full-history availability sweep.
    new_keys = [library.get("aliases", {}).get(k, k) for k in new_keys]
    verify_records(library, focus + [k for k in new_keys if k in library["papers"]], min(args.timeout, 10), limit=5)
    v2.normalize_library(library, rules)
    save()
    print(f"[2/4] 完成：合并 {merged}，补全 {metadata['filled']}，耗时 {time.monotonic()-stage:.1f}s", flush=True)
    stage = time.monotonic()
    print('[3/4] DeepSeek分批审核：开始（只有有效评价可进入日报）',flush=True)
    from services.semantic_evaluation import daily_evaluate,settings
    semantic_config=settings()
    library['semantic_enabled']=bool(semantic_config['enabled'] and not getattr(args,'no_ai',False))
    try:
        ai=daily_evaluate(args.root,library,new_keys,end,getattr(args,'ai_limit',None),getattr(args,'ai_budget',None),getattr(args,'no_ai',False))
    except Exception as exc:
        ai={'status':'fallback','processed':0,'cached':0,'cost_upper_cny':0,'priced_cost_cny':0,'reason':type(exc).__name__}
    save()
    write_json(args.root/'papers/maritime/logs/latest-ai.json',ai)
    print('[3/4] '+json.dumps(ai,ensure_ascii=False),flush=True)
    from services.mobile_digest import select_daily
    from services.maritime_metadata import enrich_first_affiliations
    picks,_=select_daily(args.root,library,end,config=semantic_config)
    affiliations=enrich_first_affiliations(args.root,library,[p['paper_id'] for p,_,_ in picks])
    save()
    print('[译] 精选摘要翻译：开始；普通历史库翻译可单独运行',flush=True)
    from services.selected_translation import translate_selected
    try:
        library['reading_enrichment_enabled']=True
        translations=translate_selected(args.root,library,end,semantic_config,args.translation_timeout,enrichment=True)
    except Exception as exc:translations={'selected':0,'translated':0,'cached':0,'manual':0,'failed':1,'cost_upper_cny':0,'priced_cost_cny':0,'reason':str(exc)}
    save()
    print('[译] '+json.dumps(translations,ensure_ascii=False),flush=True)
    from services.adaptive_discovery import recover
    library.pop('supplement_existing_ai',None)
    library.pop('supplement_existing_translation',None)
    args.supplement_seconds=max(0,2400-(time.monotonic()-started))
    supplement=recover(args,library,rules,end,save)
    added+=sum(r.get('added',0) for r in supplement)
    for field in ('processed','tokens','cost_upper_cny','priced_cost_cny'):
        ai[field]=ai.get(field,0)+library.get('supplement_existing_ai',{}).get(field,0)+sum(r.get('ai',{}).get(field,0) for r in supplement)
    for field in ('translated','api_calls','cost_upper_cny','priced_cost_cny'):
        translations[field]=translations.get(field,0)+library.get('supplement_existing_translation',{}).get(field,0)+sum(r.get('translation',{}).get(field,0) for r in supplement)
    stage = time.monotonic()
    print("[4/4] 生成网页和日报：开始", flush=True)
    build(args.root, library, rules, mobile_date=end)
    from services.mobile_digest import refresh_mobile_pages
    refresh_mobile_pages(args.root,library)
    save()
    print(f"[4/4] 完成，耗时 {time.monotonic()-stage:.1f}s", flush=True)
    source_status = "success" if all(r["status"] == "success" for r in results) else "partial" if any(r["status"] != "failed" for r in results) else "failed"
    mobile_directory=args.root/'docs/maritime-data/mobile'
    publication=json.loads((mobile_directory/'publication-status.json').read_text(encoding='utf8'))
    latest_path=mobile_directory/'latest.json'
    summary = {"run_id": run_id, "completed_at": datetime.now(timezone.utc).isoformat(),
               "local_update": "partial" if source_status == "success" and translations["failed"] else source_status,
               "jobs": len(results), "successful": sum(r["status"] == "success" for r in results),
               "incomplete": sum(r["status"] == "incomplete" for r in results), "failed": sum(r["status"] == "failed" for r in results),
               "added": added, "filled": metadata["filled"], "merged": merged,
               "before_count": before_count, "after_count": len(library["papers"]), "translation": translations,
               "translation_failed": translations["failed"], "suspected_duplicates": dedup["suspected"],
               "ai":ai,"affiliations":affiliations, "daily_selected":publication['selection_audit']['selected_count'],
               "daily_publication":publication['status'],"published_daily_date":publication['published_date'],
               "published_daily_count":len(json.loads(latest_path.read_text(encoding='utf8'))['papers']) if latest_path.exists() else 0,
               "github_sync": "not_attempted", "pages_publish": "not_attempted"}
    summary.update(ai_status=ai['status'],translation_status='partial' if translations['failed'] else 'success',selection_status='complete' if publication['status']=='complete' else 'pending',publication_status='published' if publication['status']=='complete' else 'pending',sync_status='not_attempted',pages_status='not_attempted',supplement=supplement)
    summary["retrieval_status"]="not_run_resume" if not jobs else source_status
    all_sources=results+[job for row in supplement for job in row.get('jobs',[])]
    summary['retrieval_status']=('not_run_resume' if not all_sources else 'failed' if all(r['status']=='failed' for r in all_sources) else 'partial' if any(r['status']!='success' for r in all_sources) else 'success')
    summary['translation_status']='success' if publication['status']=='complete' else 'pending'
    summary['ai_status']='success' if ai.get('processed') else ai['status']
    summary["github_run_id"]=__import__("os").environ.get("GITHUB_RUN_ID")
    write_json(args.root / "papers/maritime/logs/latest-update.json", summary)
    write_json(args.root / "docs/maritime-data/update-result.json", summary)
    public = args.root / "docs/maritime-data/library.json"
    payload = json.loads(public.read_text(encoding="utf-8"))
    payload["update_summary"] = summary
    write_json(public, payload)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0  # A saved pending batch is a recoverable outcome, not a program crash.
