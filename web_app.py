import contextlib
import base64
import hashlib
import hmac
import io
import json
import re
import secrets
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from graph.state import create_initial_state
from graph.workflow import build_workflow
from tools.manual_input import parse_manual_competitor_posts
from utils import config


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
UPLOAD_ROOT = WEB_ROOT / "generated" / "uploads"
HOST = "127.0.0.1"
PORT = 8765
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
JOB_LOCK = threading.Lock()
JOBS: dict[str, dict] = {}
AUTH_COOKIE_NAME = "smileup_session"
AUTH_SESSION_SECONDS = 12 * 60 * 60


def _enable_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


class MarketingUIHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/login":
            self._send_login_page()
            return
        if not self._is_authenticated():
            if path.startswith("/api/"):
                self._send_json({"ok": False, "error": "Authentication required"}, status=401)
            else:
                self._redirect("/login")
            return
        if path == "/":
            self._serve_file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if path == "/api/status":
            self._send_json(
                {
                    "mock_mode": config.MOCK_MODE,
                    "dry_run": config.DRY_RUN,
                    "ai_provider": config.AI_PROVIDER,
                    "ai_model": _model_status_label(),
                    "gemini_image_model": config.GEMINI_IMAGE_MODEL,
                    "cmo_jury_enabled": config.CMO_JURY_ENABLED,
                    "ad_library_enabled": config.AD_LIBRARY_ENABLED,
                    "ad_library_keywords": config.AD_LIBRARY_KEYWORDS,
                    "warnings": config.CONFIG_WARNINGS,
                }
            )
            return
        if path == "/api/job":
            query = parse_qs(parsed.query)
            job_id = (query.get("id") or [""])[0]
            with JOB_LOCK:
                job = dict(JOBS.get(job_id) or {})
            if not job:
                self._send_json({"ok": False, "error": "Job not found"}, status=404)
                return
            self._send_json({"ok": True, "job_id": job_id, **job})
            return

        relative = unquote(path.lstrip("/"))
        self._serve_static(WEB_ROOT / relative)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/login":
            self._handle_login()
            return
        if path == "/api/logout":
            self._clear_auth_cookie()
            return
        if not self._is_authenticated():
            self._send_json({"ok": False, "error": "Authentication required"}, status=401)
            return
        if path != "/api/run":
            self.send_error(404)
            return

        try:
            request_payload = self._read_json()
            if request_payload.get("sync"):
                self._send_json({"ok": True, **_run_workflow_payload(request_payload)})
                return

            job_id = uuid.uuid4().hex
            with JOB_LOCK:
                JOBS[job_id] = {"status": "running", "started_at": time.time(), "logs": "Workflow queued."}
            worker = threading.Thread(target=_run_job, args=(job_id, request_payload), daemon=True)
            worker.start()
            self._send_json({"ok": True, "job_id": job_id, "status": "running"})
        except Exception as exc:
            self._send_json({"ok": False, "error": _sanitize_error(str(exc)), "logs": ""}, status=500)

    def _serve_static(self, path: Path) -> None:
        resolved = path.resolve()
        if not str(resolved).startswith(str(WEB_ROOT.resolve())) or not resolved.is_file():
            self.send_error(404)
            return

        content_types = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".jfif": "image/jpeg",
            ".webp": "image/webp",
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

    def _send_html(self, html: str, status: int = 200, headers: dict[str, str] | None = None) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str, headers: dict[str, str] | None = None) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()

    def _send_login_page(self, error: str = "", status: int = 200) -> None:
        error_html = f'<div class="error">{_escape_html(error)}</div>' if error else ""
        self._send_html(
            f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SmileUp CMO Login</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17202a;
      --muted: #637083;
      --line: #d6e4ea;
      --brand: #087f73;
      --brand-strong: #05665d;
      --bg: #eef7f6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
      background:
        radial-gradient(circle at 30% 12%, rgba(14, 164, 145, .16), transparent 34%),
        linear-gradient(135deg, #f8fbfb 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(420px, 100%);
      padding: 34px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(255, 255, 255, .9);
      box-shadow: 0 24px 70px rgba(11, 38, 48, .12);
    }}
    .eyebrow {{
      margin: 0 0 8px;
      color: var(--brand);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.15; }}
    p {{ margin: 0 0 24px; color: var(--muted); line-height: 1.55; }}
    label {{ display: block; margin: 16px 0 8px; color: #354255; font-weight: 700; }}
    input {{
      width: 100%;
      min-height: 48px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 10px;
      font: inherit;
      outline: none;
    }}
    input:focus {{ border-color: var(--brand); box-shadow: 0 0 0 3px rgba(8,127,115,.14); }}
    button {{
      width: 100%;
      min-height: 50px;
      margin-top: 22px;
      border: 0;
      border-radius: 10px;
      background: var(--brand);
      color: white;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }}
    button:hover {{ background: var(--brand-strong); }}
    .error {{
      margin: 0 0 16px;
      padding: 12px 14px;
      border: 1px solid #f4b7b7;
      border-radius: 10px;
      background: #fff1f1;
      color: #9b1c1c;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <main>
    <p class="eyebrow">SmileUp CMO</p>
    <h1>Đăng nhập</h1>
    <p>Truy cập dashboard multi-agent marketing của SmileUp.</p>
    {error_html}
    <form method="post" action="/api/login">
      <label for="username">Tài khoản</label>
      <input id="username" name="username" autocomplete="username" required autofocus />
      <label for="password">Mật khẩu</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required />
      <button type="submit">Vào dashboard</button>
    </form>
  </main>
</body>
</html>""",
            status=status,
        )

    def _handle_login(self) -> None:
        payload = self._read_form_or_json()
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))
        valid = (
            bool(config.ADMIN_USERNAME)
            and bool(config.ADMIN_PASSWORD)
            and secrets.compare_digest(username, config.ADMIN_USERNAME)
            and secrets.compare_digest(password, config.ADMIN_PASSWORD)
        )
        if not valid:
            self._send_login_page("Sai tài khoản hoặc mật khẩu.", status=401)
            return
        token = _make_auth_token(username)
        self._redirect(
            "/",
            {
                "Set-Cookie": (
                    f"{AUTH_COOKIE_NAME}={token}; Max-Age={AUTH_SESSION_SECONDS}; "
                    "Path=/; HttpOnly; SameSite=Lax"
                )
            },
        )

    def _clear_auth_cookie(self) -> None:
        self._redirect("/login", {"Set-Cookie": f"{AUTH_COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"})

    def _is_authenticated(self) -> bool:
        if not config.AUTH_ENABLED:
            return True
        cookie_header = self.headers.get("Cookie", "")
        cookies = {}
        for part in cookie_header.split(";"):
            if "=" in part:
                name, value = part.strip().split("=", 1)
                cookies[name] = value
        return _verify_auth_token(cookies.get(AUTH_COOKIE_NAME, ""))

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            return {}
        raw_body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw_body or "{}")

    def _read_form_or_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            return {}
        raw_body = self.rfile.read(content_length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return json.loads(raw_body or "{}")
        parsed = parse_qs(raw_body, keep_blank_values=True)
        return {key: values[-1] if values else "" for key, values in parsed.items()}

    def log_message(self, format: str, *args) -> None:
        return


def _run_job(job_id: str, request_payload: dict) -> None:
    try:
        output = _run_workflow_payload(request_payload)
        with JOB_LOCK:
            JOBS[job_id].update({"status": "completed", **output, "finished_at": time.time()})
    except Exception as exc:
        with JOB_LOCK:
            JOBS[job_id].update(
                {
                    "status": "error",
                    "error": _sanitize_error(str(exc)),
                    "finished_at": time.time(),
                }
            )


def _run_workflow_payload(request_payload: dict) -> dict:
    log_buffer = io.StringIO()
    initial_state = _build_initial_state(request_payload)
    started_at = time.perf_counter()
    with contextlib.redirect_stdout(log_buffer), contextlib.redirect_stderr(log_buffer):
        result = build_workflow().invoke(initial_state)
    duration_ms = round((time.perf_counter() - started_at) * 1000)
    return {
        "result": result,
        "duration_ms": duration_ms,
        "logs": log_buffer.getvalue().strip(),
    }


def _build_initial_state(request_payload: dict) -> dict:
    manual_text = str(request_payload.get("manual_competitor_posts", "")).strip()
    visual_notes = str(request_payload.get("manual_visual_notes", "")).strip()
    video_notes = str(request_payload.get("manual_video_notes", "")).strip()
    ad_library_keywords = str(request_payload.get("ad_library_keywords", "")).strip()
    creative_image_mode = "text_only"
    creative_image_name = str(request_payload.get("creative_image_name", "")).strip()
    creative_image_data_url = str(request_payload.get("creative_image_data_url", "")).strip()

    initial_state = create_initial_state()
    initial_state["run_seed"] = str(time.time_ns())
    initial_state["ad_library_keywords"] = ad_library_keywords or config.AD_LIBRARY_KEYWORDS
    initial_state["competitor_visual_notes"] = visual_notes
    initial_state["competitor_video_notes"] = video_notes
    initial_state["creative_image_mode"] = creative_image_mode
    if creative_image_data_url and creative_image_mode in {"owned", "layout_reference"}:
        upload_path, upload_url = _save_uploaded_creative(creative_image_data_url, creative_image_name)
        initial_state["creative_upload_path"] = upload_path
        initial_state["creative_upload_url"] = upload_url
        if creative_image_mode == "owned":
            initial_state["creative_reference_note"] = "Using uploaded SmileUp-owned/licensed image as creative source."
        else:
            initial_state["creative_reference_note"] = "Using uploaded image as layout reference only; original pixels are not reused."
    if manual_text:
        manual_insights = parse_manual_competitor_posts(manual_text)
        if manual_insights:
            initial_state["competitor_insights"] = manual_insights
            initial_state["data_source"] = "manual"
            initial_state["manual_posts_count"] = len(manual_insights)
    if visual_notes or video_notes:
        initial_state["data_source"] = "manual"
    return initial_state


def _save_uploaded_creative(data_url: str, original_name: str) -> tuple[str, str]:
    match = re.match(r"^data:image/(png|jpe?g|webp);base64,(.+)$", data_url, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Unsupported image upload. Please upload PNG, JPG, JPEG, or WEBP.")

    extension = match.group(1).lower()
    extension = "jpg" if extension in {"jpg", "jpeg"} else extension
    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except Exception as exc:
        raise ValueError("Image upload is not valid base64.") from exc
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Image upload is too large. Maximum size is 8 MB.")

    safe_name = re.sub(r"[^a-zA-Z0-9]+", "-", Path(original_name).stem).strip("-").lower()[:36]
    digest = hashlib.sha1(raw).hexdigest()[:10]
    filename = f"{datetime.now():%Y%m%d_%H%M%S}_{safe_name or 'creative'}_{digest}.{extension}"
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    output_path = UPLOAD_ROOT / filename
    output_path.write_bytes(raw)
    return str(output_path), f"/generated/uploads/{filename}"


def _model_status_label() -> str:
    models = []
    if config.GEMINI_API_KEY:
        models.append(f"Gemini:{config.GEMINI_MODEL}")
    if config.OPENAI_API_KEY:
        models.append(f"GPT:{config.OPENAI_MODEL}")
    if config.ANTHROPIC_API_KEY:
        models.append(f"Claude:{config.ANTHROPIC_MODEL}")
    return " + ".join(models) if models else "local-template"


def _auth_secret() -> str:
    if config.AUTH_SECRET:
        return config.AUTH_SECRET
    return hashlib.sha256((config.ADMIN_PASSWORD or "smileup-local-secret").encode("utf-8")).hexdigest()


def _make_auth_token(username: str) -> str:
    expires_at = str(int(time.time()) + AUTH_SESSION_SECONDS)
    payload = f"{username}|{expires_at}"
    signature = hmac.new(_auth_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def _verify_auth_token(token: str) -> bool:
    try:
        username, expires_at, signature = token.split("|", 2)
        if int(expires_at) < int(time.time()):
            return False
    except Exception:
        return False
    if not config.ADMIN_USERNAME or not secrets.compare_digest(username, config.ADMIN_USERNAME):
        return False
    payload = f"{username}|{expires_at}"
    expected = hmac.new(_auth_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return secrets.compare_digest(signature, expected)


def _escape_html(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def main() -> None:
    _enable_utf8_console()
    server = ThreadingHTTPServer((HOST, PORT), MarketingUIHandler)
    _safe_print(f"Dental Marketing UI running at http://{HOST}:{PORT}")
    _safe_print("Press Ctrl+C to stop.")
    server.serve_forever()


def _safe_print(message: str) -> None:
    try:
        if sys.stdout:
            print(message)
    except Exception:
        return


def _sanitize_error(message: str) -> str:
    sanitized = re.sub(r"(access_token=)[^&\s]+", r"\1[redacted]", message)
    sanitized = re.sub(r"(Authorization:\s*Bearer\s+)[^\s]+", r"\1[redacted]", sanitized, flags=re.IGNORECASE)
    return sanitized


if __name__ == "__main__":
    main()
