"""Desktop dispatches the single cloud writer; local maintenance is opt-in."""
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import webbrowser
import json
import os
import socket
import time
import threading
from queue import Queue, Empty
from contextlib import contextmanager

import preview_maritime


class UpdateAlreadyRunning(RuntimeError):
    pass


@contextmanager
def update_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise UpdateAlreadyRunning() from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise UpdateAlreadyRunning() from exc
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def execute_update(root, path, arguments):
    started = time.time()
    print(f"正在更新论文。日志：{path}", flush=True)
    code = 1
    try:
        with path.open("w", encoding="utf-8") as log:
            child = subprocess.Popen([sys.executable, "-u", str(root / "skills/rs-paper-pipeline/scripts/cli.py"), "maritime",
                "--action", "update", "--timeout", "30", "--retries", "2", "--max-pages", "5", *arguments],
                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
            output = Queue()
            def reader():
                for line in child.stdout:
                    output.put(line)
                output.put(None)
            thread = threading.Thread(target=reader, daemon=True)
            thread.start()
            while True:
                try:
                    line = output.get(timeout=15)
                except Empty:
                    line = "当前阶段仍在运行，请等待；已完成的来源结果已保留。\n"
                if line is None:
                    break
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            thread.join()
            code = child.wait()
    except OSError as exc:
        print(f"更新失败：{exc}", flush=True)
    summary_path = root / "papers/maritime/logs/latest-update.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() and summary_path.stat().st_mtime >= started else {}
    label = "更新完成" if code == 0 else "部分完成" if code == 2 else "更新失败"
    print(f"{label}：新增 {summary.get('added', 0)} 篇，补全 {summary.get('filled', 0)} 篇，合并重复 {summary.get('merged', 0)} 篇，中文翻译成功 {summary.get('translation', {}).get('translated', 0)} 篇，失败 {summary.get('failed', 0) + summary.get('translation_failed', 0)} 项。", flush=True)
    ai=summary.get('ai',{})
    translation=summary.get('translation',{})
    print(f"AI新评价 {ai.get('processed',0)} 篇，复用 {ai.get('cached',0)} 篇；精选新译 {translation.get('translated',0)} 篇；本次API计价约 ¥{ai.get('priced_cost_cny',0)+translation.get('priced_cost_cny',0):.6f}（评价 ¥{ai.get('priced_cost_cny',0):.6f}，翻译 ¥{translation.get('priced_cost_cny',0):.6f}），预算记账上界 ¥{ai.get('cost_upper_cny',0)+translation.get('cost_upper_cny',0):.6f}；每日精选 {summary.get('daily_selected',0)} 篇。",flush=True)
    if ai.get('unsettled_upper_cny'):
        print(f"API可能存在未决计费，保留预算上界 ¥{ai['unsettled_upper_cny']:.6f}；不是已核实扣款。",flush=True)
    print(f"本地阶段已结束；AI状态：{ai.get('status','未执行')}；日志：{path}", flush=True)
    print('本地维护结果已保存；未执行付费AI、GitHub同步或Pages发布。正式更新请双击默认论文更新。',flush=True)
    print(f"全部结束时间：{datetime.now().astimezone().isoformat()}；退出码 {code}。",flush=True)
    return code


def main():
    root = Path(__file__).resolve().parents[3]
    logs = root / "papers/maritime/logs"
    logs.mkdir(parents=True, exist_ok=True)
    path = logs / ("update-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
    arguments = sys.argv[1:]
    sync_only = '--sync-only' in arguments
    if sync_only and os.environ.get("GITHUB_ACTIONS")!="true":
        print("正式数据由云端统一写入；本地不自动推送。请双击默认论文更新。",flush=True)
        return 2
    arguments = [a for a in arguments if a != '--sync-only']
    no_open = "--no-open" in arguments
    arguments = [a for a in arguments if a != "--no-open"]
    proxy_config = root / "papers/maritime/private/network.json"
    if proxy_config.is_file():
        proxy = json.loads(proxy_config.read_text(encoding="utf-8"))["proxy_url"]
        os.environ.setdefault("RS_PROXY_URL", proxy)
        os.environ.setdefault("HTTPS_PROXY", proxy)
        os.environ.setdefault("HTTP_PROXY", proxy)
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if sys.platform == "win32" and not os.environ.get("OPENALEX_API_KEY"):
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                os.environ["OPENALEX_API_KEY"] = winreg.QueryValueEx(key, "OPENALEX_API_KEY")[0]
        except OSError:
            pass
    local_mode='--local' in arguments
    arguments=[a for a in arguments if a!='--local']
    if not local_mode and not sync_only:
        try:
            from services.cloud_update import cloud_update
            only_open='--only-open' in arguments
            if only_open:code=0
            else:
                with update_lock(root/'papers/maritime/private/cloud-update.lock'):
                    code=cloud_update(root,arguments,wait='--cloud-no-wait' not in arguments)
            if not no_open:webbrowser.open('https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html')
            return code
        except UpdateAlreadyRunning:
            print('已有桌面窗口正在触发或查询云端，本窗口不重复触发。',flush=True)
            return 3
        except Exception as exc:
            print('本地触发或查询未完成：'+str(exc)+'；不代表云端任务失败。下次双击将优先恢复已保存任务。',flush=True)
            return 2
    only_open = "--only-open" in arguments
    arguments = [a for a in arguments if a != "--only-open"]
    code = 0
    if not only_open:
        try:
            with update_lock(root / "papers/maritime/private/update.lock"):
                if sync_only:
                    from services.maritime_sync import sync
                    result=sync(root)
                    code=0 if result['github_sync']=='success' and result['pages_publish'] in ('success','workflow_run_pending') else 2
                else:
                    if "--no-ai" not in arguments:arguments.append("--no-ai")
                    code = execute_update(root, path, arguments)
        except UpdateAlreadyRunning:
            print("已有论文更新正在运行，本次未重复启动。等待原窗口显示结束结果即可。", flush=True)
            return 3
        except OSError as exc:
            print(f"更新失败：无法获取本地更新锁或写入日志：{exc}；结束时间 {datetime.now().astimezone().isoformat()}；退出码1。", flush=True)
            return 1
    if not no_open:
        port = 8000
        for candidate in range(8000, 8005):
            if preview_maritime.existing_service(candidate):
                port = candidate
                break
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", candidate)) != 0:
                    port = candidate
                    break
        url = f"http://127.0.0.1:{port}/maritime.html"
        if preview_maritime.existing_service(port):
            webbrowser.open(url)
        else:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.Popen([sys.executable, str(root / "skills/rs-paper-pipeline/scripts/preview_maritime.py"), "--port", str(port)],
                cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
