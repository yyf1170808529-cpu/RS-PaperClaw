"""Serve the personal reading page until the user presses Ctrl+C."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Timer
import webbrowser
import urllib.request


def existing_service(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/maritime.html", timeout=2) as response:
            text = response.read(20000).decode("utf-8")
        return "maritime.js" in text and "个人科研论文库" in text
    except (OSError, UnicodeError):
        return False


def main():
    parser = argparse.ArgumentParser(description="启动个人论文阅读页")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--check", action="store_true", help="仅检查文件和端口，不持续运行或打开浏览器")
    args = parser.parse_args()
    docs = Path(__file__).resolve().parents[3] / "docs"
    if not (docs / "maritime.html").is_file() or not (docs / "maritime-data/library.json").is_file():
        parser.exit(1, "Missing reading page/data. Run maritime --action site first.\n")
    if existing_service(args.port):
        print("Reusing existing personal reading service.")
        if not args.check:
            webbrowser.open(f"http://127.0.0.1:{args.port}/maritime.html")
        return
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(SimpleHTTPRequestHandler, directory=str(docs)))
    except OSError as exc:
        parser.exit(1, f"Cannot start server on port {args.port}: {exc}\nTry --port 8001.\n")
    url = f"http://127.0.0.1:{args.port}/maritime.html"
    if args.check:
        server.server_close()
        print(f"OK: reading page, data and port. {url}")
        return
    print(f"Reading page: {url}\nKeep this window open. Press Ctrl+C to stop.", flush=True)
    opener = Timer(1, lambda: webbrowser.open(url))
    opener.daemon = True
    opener.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        opener.cancel()
        server.server_close()


if __name__ == "__main__":
    main()
