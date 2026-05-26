import contextlib
import io
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from graph.state import create_initial_state
from graph.workflow import build_workflow
from utils import config


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
HOST = "127.0.0.1"
PORT = 8765


def _enable_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


class MarketingUIHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._serve_file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if self.path.startswith("/api/status"):
            self._send_json(
                {
                    "mock_mode": config.MOCK_MODE,
                    "dry_run": config.DRY_RUN,
                    "warnings": config.CONFIG_WARNINGS,
                }
            )
            return

        relative = unquote(self.path.lstrip("/"))
        self._serve_static(WEB_ROOT / relative)

    def do_POST(self) -> None:
        if self.path != "/api/run":
            self.send_error(404)
            return

        log_buffer = io.StringIO()
        try:
            started_at = time.perf_counter()
            with contextlib.redirect_stdout(log_buffer), contextlib.redirect_stderr(log_buffer):
                result = build_workflow().invoke(create_initial_state())
            duration_ms = round((time.perf_counter() - started_at) * 1000)
            self._send_json(
                {
                    "ok": True,
                    "result": result,
                    "duration_ms": duration_ms,
                    "logs": log_buffer.getvalue().strip(),
                }
            )
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc), "logs": log_buffer.getvalue().strip()}, status=500)

    def _serve_static(self, path: Path) -> None:
        resolved = path.resolve()
        if not str(resolved).startswith(str(WEB_ROOT.resolve())) or not resolved.is_file():
            self.send_error(404)
            return

        content_types = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".html": "text/html; charset=utf-8",
        }
        self._serve_file(resolved, content_types.get(resolved.suffix, "application/octet-stream"))

    def _serve_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    _enable_utf8_console()
    server = ThreadingHTTPServer((HOST, PORT), MarketingUIHandler)
    print(f"Dental Marketing UI running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
