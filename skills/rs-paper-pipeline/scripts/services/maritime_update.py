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
    batch = arxiv_client.fetch_topic_candidates(job["query"], str(start), str(end), args.page_size,
        args.max_pages, args.retries, args.timeout)
    for p in batch:
        p.update(paper_id=p["arxiv_id"], publication_date=p["published"], metadata_source=["arXiv"])
    return batch, True


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


def _translation_worker(queue, papers):
    for paper in papers:
        queue.put((paper["paper_id"], reading.translate_one(paper)))
    queue.put((None, None))


def translate_budget(library, keys, limit, seconds, save, retry_failed=True):
    import hashlib
    import multiprocessing
    from queue import Empty
    from services.maritime_validity import eligible_paper
    counts = {"translated": 0, "cached": 0, "manual": 0, "failed": 0, "missing_english": 0, "pending": 0, "skipped_failed": 0}
    work = []
    for key in dict.fromkeys(keys):
        p = library["papers"][key]
        if not eligible_paper(p) or p.get("assessment", {}).get("level") == "excluded":
            continue
        t = p.get("translation", {})
        if t.get("status") == "manual":
            counts["manual"] += 1
        elif not p.get("abstract", "").strip():
            counts["missing_english"] += 1
        elif t.get("status") == "machine" and t.get("english_hash") == hashlib.sha256(p["abstract"].encode()).hexdigest() and t.get("protection_revision") in (4, 5):
            counts["cached"] += 1
        elif t.get("status") == "failed" and not retry_failed:
            counts["skipped_failed"] += 1
        else:
            work.append(p)
    counts["pending"] = max(0, len(work) - limit)
    work = work[:limit]
    if not work:
        return counts
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_translation_worker, args=(queue, work))
    process.start()
    done = set()
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            try:
                key, result = queue.get(timeout=min(15, max(.01, deadline-time.monotonic())))
                if key is None:
                    break
                library["papers"][key]["translation"] = result
                if result["status"] == "machine":
                    library["papers"][key].pop("translation_pending", None)
                counts["translated" if result["status"] == "machine" else "failed"] += 1
                done.add(key)
                save()
                print(f"中文翻译 {len(done)}/{len(work)}：{key} {result['status']} {result.get('error_type', '')}", flush=True)
            except Empty:
                print(f"中文翻译仍在运行：已完成 {len(done)}/{len(work)}，阶段上限 {seconds}s", flush=True)
                if not process.is_alive():
                    break
    finally:
        if process.is_alive():
            process.terminate()
        process.join()
        queue.close()
    for p in work:
        if p["paper_id"] not in done:
            p["translation"] = {**p.get("translation", {}), "status": "failed", "error_type": "model_runtime_error",
                                "error": "Translation worker exceeded time budget or exited; English preserved"}
            counts["failed"] += 1
    save()
    return counts


def run_update(args, library, rules):
    from services.maritime import today, write_json, library_path, build
    from services.maritime_metadata import enrich_missing
    from services.maritime_validity import verify_records
    end = datetime.strptime(args.date.replace("-", ""), "%Y%m%d").date() if args.date else today()
    venues, policy = v2.assets()
    jobs = update_jobs(args, venues)
    if not jobs:
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
    focus = v2.recommendation_view(list(library["papers"].values()), policy, end)["paper_ids"]
    # Cached checks are bounded; no full-history availability sweep.
    new_keys = [library.get("aliases", {}).get(k, k) for k in new_keys]
    verify_records(library, focus + [k for k in new_keys if k in library["papers"]], min(args.timeout, 10), limit=5)
    v2.normalize_library(library, rules)
    save()
    print(f"[2/4] 完成：合并 {merged}，补全 {metadata['filled']}，耗时 {time.monotonic()-stage:.1f}s", flush=True)
    stage = time.monotonic()
    print("[3/4] 中文摘要翻译：开始，成功缓存不重翻", flush=True)
    from services.maritime_reading import translation_order
    focused_new = [k for k in focus if k in new_keys]
    keys = focused_new + focus + new_keys + translation_order(library)
    translations = translate_budget(library, keys, args.translation_limit, args.translation_timeout, save, args.retry_failed)
    print(f"[3/4] 完成：{translations}，耗时 {time.monotonic()-stage:.1f}s", flush=True)
    stage = time.monotonic()
    print("[4/4] 生成网页和日报：开始", flush=True)
    build(args.root, library, rules)
    save()
    print(f"[4/4] 完成，耗时 {time.monotonic()-stage:.1f}s", flush=True)
    source_status = "success" if all(r["status"] == "success" for r in results) else "partial" if any(r["status"] != "failed" for r in results) else "failed"
    summary = {"run_id": run_id, "completed_at": datetime.now(timezone.utc).isoformat(),
               "local_update": "partial" if source_status == "success" and translations["failed"] else source_status,
               "jobs": len(results), "successful": sum(r["status"] == "success" for r in results),
               "incomplete": sum(r["status"] == "incomplete" for r in results), "failed": sum(r["status"] == "failed" for r in results),
               "added": added, "filled": metadata["filled"], "merged": merged,
               "before_count": before_count, "after_count": len(library["papers"]), "translation": translations,
               "translation_failed": translations["failed"], "suspected_duplicates": dedup["suspected"],
               "github_sync": "not_attempted", "pages_publish": "not_attempted"}
    write_json(args.root / "papers/maritime/logs/latest-update.json", summary)
    public = args.root / "docs/maritime-data/library.json"
    payload = json.loads(public.read_text(encoding="utf-8"))
    payload["update_summary"] = summary
    write_json(public, payload)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary["local_update"] == "success" else 2 if summary["local_update"] == "partial" else 1
