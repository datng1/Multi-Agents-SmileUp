from __future__ import annotations

import hashlib
import hmac
import json
import os
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
from graph.workflow import PRODUCTION_AGENT_ORDER, build_workflow
from tools.workflow_progress import set_workflow_progress_callback
from utils import config


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
WORKFLOW_CONTEXT_CACHE_PATH = ROOT / "data" / "workflow_context_cache.json"
HOST = "127.0.0.1"
PORT = 8765
MAX_REQUEST_BYTES = 1024 * 1024
JOB_LOCK = threading.Lock()
CACHE_LOCK = threading.Lock()
JOBS: dict[str, dict] = {}
AUTH_COOKIE_NAME = "smileup_session"
CLIENT_SESSION_COOKIE_NAME = "smileup_client_session"
AUTH_SESSION_SECONDS = 12 * 60 * 60
CLIENT_SESSION_SECONDS = 30 * 24 * 60 * 60
WORKFLOW_CONTEXT_CACHE_VERSION = 2
WORKFLOW_CONTEXT_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
WORKFLOW_CONTEXT_CACHE_CLEANUP_INTERVAL_SECONDS = 60 * 60
JOB_TTL_SECONDS = 24 * 60 * 60
WORKFLOW_AGENT_ORDER = list(PRODUCTION_AGENT_ORDER)


def _enable_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


class MarketingUIHandler(BaseHTTPRequestHandler):
    def _current_session_id(self, username: str) -> str:
        cookies = self._cookies()
        session_id = cookies.get(CLIENT_SESSION_COOKIE_NAME, "")
        if _is_safe_session_id(session_id, username):
            return session_id
        session_id = f"{_session_owner_prefix(username)}_{uuid.uuid4().hex}"
        self._pending_session_cookie = session_id
        return session_id

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._send_json({"ok": True, "service": "smileup-cmo"})
            return
        if path == "/login":
            self._send_login_page()
            return
        if not self._is_authenticated():
            if path.startswith("/api/"):
                self._send_json({"ok": False, "error": "Authentication required"}, status=401)
            else:
                self._redirect("/login")
            return
        username = self._current_username()
        session_id = self._current_session_id(username)
        if path == "/":
            self._serve_file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if path == "/api/status":
            self._send_json(
                {
                    "ai_provider": config.AI_PROVIDER,
                    "ai_model": _model_status_label(),
                    "ad_library_enabled": config.AD_LIBRARY_ENABLED,
                    "ad_library_keywords": config.AD_LIBRARY_KEYWORDS,
                    "ad_library_competitor_ratio": config.AD_LIBRARY_COMPETITOR_RATIO,
                    "ad_library_competitor_count": len(config.AD_LIBRARY_COMPETITOR_URLS),
                    "scan_ads": 100,
                    "agent_order": WORKFLOW_AGENT_ORDER,
                    "workflow_context_cache_days": round(WORKFLOW_CONTEXT_CACHE_TTL_SECONDS / 86400),
                    "warnings": config.CONFIG_WARNINGS,
                }
            )
            return
        if path == "/api/history":
            query = parse_qs(parsed.query)
            history_id = (query.get("id") or [""])[0]
            if history_id:
                item = _get_workflow_context_history_item(history_id, session_id, username)
                if not item:
                    self._send_json({"ok": False, "error": "History item not found"}, status=404)
                    return
                self._send_json({"ok": True, **item})
                return
            self._send_json({"ok": True, "items": _list_workflow_context_history(session_id, username)})
            return
        if path == "/api/job":
            query = parse_qs(parsed.query)
            job_id = (query.get("id") or [""])[0]
            with JOB_LOCK:
                _prune_jobs_locked()
                job = dict(JOBS.get(job_id) or {})
            if not job:
                self._send_json({"ok": False, "error": "Job not found"}, status=404)
                return
            if job.get("session_id") != session_id and not _is_admin_user(username):
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
        username = self._current_username()
        session_id = self._current_session_id(username)
        if path != "/api/run":
            self.send_error(404)
            return

        history_id = ""
        try:
            request_payload = self._read_json()
            history_id = _create_workflow_context_history(request_payload, session_id, username)
            if request_payload.get("sync"):
                self._send_json(
                    {
                        "ok": True,
                        **_run_workflow_payload(request_payload, session_id, username, history_id=history_id),
                    }
                )
                return

            job_id = uuid.uuid4().hex
            with JOB_LOCK:
                _prune_jobs_locked()
                JOBS[job_id] = {
                    "status": "running",
                    "started_at": time.time(),
                    "logs": "Workflow queued.",
                    "session_id": session_id,
                    "owner_username": username,
                    "history_id": history_id,
                }
            worker = threading.Thread(
                target=_run_job,
                args=(job_id, request_payload, session_id, username, history_id),
                daemon=True,
            )
            worker.start()
            self._send_json(
                {"ok": True, "job_id": job_id, "history_id": history_id, "status": "running"}
            )
        except Exception as exc:
            error = _sanitize_error(str(exc))
            if history_id:
                _record_workflow_context_history_error(
                    history_id,
                    request_payload,
                    session_id,
                    username,
                    error,
                )
            self._send_json({"ok": False, "error": error, "logs": ""}, status=500)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if not self._is_authenticated():
            self._send_json({"ok": False, "error": "Authentication required"}, status=401)
            return
        username = self._current_username()
        session_id = self._current_session_id(username)
        if path != "/api/history":
            self.send_error(404)
            return

        history_id = (parse_qs(parsed.query).get("id") or [""])[0]
        if not history_id:
            self._send_json({"ok": False, "error": "Missing history id"}, status=400)
            return
        if not _delete_workflow_context_history_item(history_id, session_id, username):
            self._send_json({"ok": False, "error": "History item not found"}, status=404)
            return
        self._send_json({"ok": True, "history_id": history_id})

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
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self._send_pending_session_cookie()
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_pending_session_cookie()
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200, headers: dict[str, str] | None = None) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self._send_pending_session_cookie()
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str, headers: dict[str, str | list[str]] | None = None) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        for name, value in (headers or {}).items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                self.send_header(name, item)
        self._send_pending_session_cookie()
        self.end_headers()

    def _send_pending_session_cookie(self) -> None:
        session_id = getattr(self, "_pending_session_cookie", "")
        if not session_id:
            return
        self.send_header(
            "Set-Cookie",
            f"{CLIENT_SESSION_COOKIE_NAME}={session_id}; Max-Age={CLIENT_SESSION_SECONDS}; Path=/; HttpOnly; SameSite=Lax",
        )
        self._pending_session_cookie = ""

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
        valid = _verify_credentials(username, password)
        if not valid:
            self._send_login_page("Sai tài khoản hoặc mật khẩu.", status=401)
            return
        token = _make_auth_token(username)
        self._redirect(
            "/",
            {
                "Set-Cookie": [
                    (
                        f"{AUTH_COOKIE_NAME}={token}; Max-Age={AUTH_SESSION_SECONDS}; "
                        "Path=/; HttpOnly; SameSite=Lax"
                    ),
                    f"{CLIENT_SESSION_COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax",
                ]
            },
        )

    def _clear_auth_cookie(self) -> None:
        self._redirect(
            "/login",
            {
                "Set-Cookie": [
                    f"{AUTH_COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax",
                    f"{CLIENT_SESSION_COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax",
                ]
            },
        )

    def _is_authenticated(self) -> bool:
        return bool(self._current_username())

    def _current_username(self) -> str:
        if not config.AUTH_ENABLED:
            return config.ADMIN_USERNAME or "local"
        cookies = self._cookies()
        return _auth_username(cookies.get(AUTH_COOKIE_NAME, ""))

    def _cookies(self) -> dict[str, str]:
        cookie_header = self.headers.get("Cookie", "")
        cookies = {}
        for part in cookie_header.split(";"):
            if "=" in part:
                name, value = part.strip().split("=", 1)
                cookies[name] = value
        return cookies

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            return {}
        if content_length > MAX_REQUEST_BYTES:
            raise ValueError("Request body is too large.")
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


def _run_job(
    job_id: str,
    request_payload: dict,
    session_id: str,
    username: str,
    history_id: str,
) -> None:
    def _progress(agent_name: str, status: str) -> None:
        with JOB_LOCK:
            job = JOBS.get(job_id)
            if not job:
                return
            statuses = dict(job.get("agent_statuses") or {})
            if status == "running" and agent_name in WORKFLOW_AGENT_ORDER:
                for downstream_agent in WORKFLOW_AGENT_ORDER[WORKFLOW_AGENT_ORDER.index(agent_name) + 1 :]:
                    statuses.pop(downstream_agent, None)
            statuses[agent_name] = status
            job["agent_statuses"] = statuses
            job["current_step"] = agent_name
            job["logs"] = _progress_log(statuses, agent_name, status)

    try:
        set_workflow_progress_callback(_progress)
        output = _run_workflow_payload(
            request_payload,
            session_id,
            username,
            history_id=history_id,
        )
        with JOB_LOCK:
            statuses = dict(JOBS[job_id].get("agent_statuses") or {})
            result = output.get("result") or {}
            JOBS[job_id].update(
                {
                    "status": "completed",
                    "agent_statuses": statuses,
                    "current_step": _completed_workflow_step(result, statuses),
                    **output,
                    "finished_at": time.time(),
                }
            )
    except Exception as exc:
        error = _sanitize_error(str(exc))
        with JOB_LOCK:
            job = JOBS[job_id]
            statuses = dict(job.get("agent_statuses") or {})
            current_step = str(job.get("current_step") or "")
            logs = str(job.get("logs") or error)
            job.update(
                {
                    "status": "error",
                    "error": error,
                    "finished_at": time.time(),
                }
            )
        _record_workflow_context_history_error(
            history_id,
            request_payload,
            session_id,
            username,
            error,
            job_id=job_id,
            current_step=current_step,
            agent_statuses=statuses,
            logs=logs,
        )
    finally:
        set_workflow_progress_callback(None)


def _prune_jobs_locked() -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    stale_ids = [
        job_id
        for job_id, job in JOBS.items()
        if job.get("status") in {"completed", "error"}
        and float(job.get("finished_at") or 0) < cutoff
    ]
    for job_id in stale_ids:
        JOBS.pop(job_id, None)


def _progress_log(statuses: dict, current_agent: str, current_status: str) -> str:
    labels = {
        "crawler": "Crawler",
        "text_insight": "Text Insight",
        "trend_analysis": "Trend",
        "visual_insight": "Visual",
        "video_insight": "Video",
        "strategy": "Strategy",
        "compliance": "Compliance",
        "hardness": "Hardness",
        "manager_review": "CMO Lead",
    }
    lines = [f"{labels.get(current_agent, current_agent)}: {current_status}"]
    for key, label in labels.items():
        if key in statuses:
            lines.append(f"- {label}: {statuses[key]}")
    return "\n".join(lines)


def _run_workflow_payload(
    request_payload: dict,
    session_id: str,
    username: str,
    *,
    history_id: str = "",
) -> dict:
    context_key = _workflow_context_cache_key(request_payload)
    keyword = _normalize_scan_keyword(request_payload.get("ad_library_keywords"))
    previous_campaign = _latest_previous_campaign_snapshot(keyword, session_id, username)
    initial_state = _build_initial_state(request_payload, previous_campaign)
    started_at = time.perf_counter()
    result = build_workflow().invoke(initial_state)
    duration_ms = round((time.perf_counter() - started_at) * 1000)
    output = {
        "result": result,
        "duration_ms": duration_ms,
        "logs": "Monthly media campaign completed with four-week and SmileUp brand contracts.",
        "history_hit": False,
        "run_status": "completed",
        "context_cache_key": context_key,
    }
    output["history_id"] = _write_workflow_context_cache(
        context_key,
        output,
        request_payload,
        session_id,
        username,
        history_id=history_id,
    )
    return output


def _completed_workflow_step(result: dict, statuses: dict) -> str:
    for agent_name in reversed(WORKFLOW_AGENT_ORDER):
        if statuses.get(agent_name) in {"done", "running"}:
            return agent_name
    return str(result.get("current_step") or "manager_review")


def _workflow_context_cache_key(request_payload: dict) -> str:
    ad_library_keywords = _normalize_scan_keyword(request_payload.get("ad_library_keywords"))
    scan_mode, max_ads, reference_scan_limit = _scan_settings(request_payload)
    payload = {
        "version": WORKFLOW_CONTEXT_CACHE_VERSION,
        "mode": str(request_payload.get("mode", "auto")).strip(),
        "scan_mode": scan_mode,
        "ad_library_run_max_ads": max_ads,
        "ad_library_reference_scan_limit": reference_scan_limit,
        "ad_library_keywords": re.sub(r"\s+", " ", ad_library_keywords).strip().casefold(),
        "data_source": "auto",
        "settings": {
            "ad_library_enabled": config.AD_LIBRARY_ENABLED,
            "ad_library_country": config.AD_LIBRARY_COUNTRY,
            "ad_library_max_ads": config.AD_LIBRARY_MAX_ADS,
            "ad_library_competitor_urls": config.AD_LIBRARY_COMPETITOR_URLS,
            "ad_library_competitor_ratio": config.AD_LIBRARY_COMPETITOR_RATIO,
            "openai_model": config.OPENAI_MODEL,
            "openai_reasoning_effort": config.OPENAI_REASONING_EFFORT,
            "gemini_model": config.GEMINI_MODEL,
            "agent_api_reasoning_enabled": config.AGENT_API_REASONING_ENABLED,
        },
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _get_workflow_context_history_item(history_id: str, session_id: str, username: str) -> dict | None:
    with CACHE_LOCK:
        cache = _load_workflow_context_cache()
        entry = (cache.get("entries") or {}).get(history_id)
        if not isinstance(entry, dict):
            return None
        if not _can_access_history_entry(entry, session_id, username):
            return None
        cached_at = float(entry.get("cached_at", 0) or 0)
        if time.time() - cached_at >= WORKFLOW_CONTEXT_CACHE_TTL_SECONDS:
            cache.get("entries", {}).pop(history_id, None)
            _save_workflow_context_cache(cache)
            return None
        output = entry.get("output")
        if not isinstance(output, dict):
            return None
        output = dict(output)
        if isinstance(output.get("result"), dict):
            output["result"] = dict(output["result"])
        output["run_status"] = str(
            output.get("run_status") or ("completed" if output.get("result") else "running")
        )
        output["context_cache_key"] = str(output.get("context_cache_key") or entry.get("context_key") or "")
        return {
            "history_id": history_id,
            "cached_at": cached_at,
            "summary": entry.get("summary") or {},
            **output,
            "history_hit": True,
        }


def _list_workflow_context_history(session_id: str, username: str) -> list[dict]:
    with CACHE_LOCK:
        cache = _load_workflow_context_cache()
        removed = _prune_workflow_context_cache_entries(cache, time.time())
        if removed:
            _save_workflow_context_cache(cache)
        items = []
        for history_id, entry in (cache.get("entries") or {}).items():
            if not isinstance(entry, dict):
                continue
            if not _can_access_history_entry(entry, session_id, username):
                continue
            summary = dict(entry.get("summary") or {})
            output = entry.get("output") or {}
            cached_at = float(entry.get("cached_at", 0) or 0)
            created_at = float(entry.get("created_at", 0) or cached_at)
            run_status = str(
                summary.get("run_status")
                or output.get("run_status")
                or ("completed" if output.get("result") else "running")
            )
            items.append(
                {
                    "history_id": history_id,
                    "owner_username": entry.get("owner_username") or "",
                    "cached_at": cached_at,
                    "created_at": summary.get("created_at") or datetime.fromtimestamp(created_at).isoformat(timespec="seconds"),
                    "run_status": run_status,
                    "has_result": bool(summary.get("has_result") or output.get("result")),
                    "error": str(summary.get("error") or output.get("error") or ""),
                    **summary,
                }
            )
        return sorted(items, key=lambda item: float(item.get("cached_at", 0) or 0), reverse=True)


def _latest_previous_campaign_snapshot(keyword: str, session_id: str, username: str) -> dict:
    with CACHE_LOCK:
        cache = _load_workflow_context_cache()
        candidates = []
        for entry in (cache.get("entries") or {}).values():
            if not isinstance(entry, dict):
                continue
            output = entry.get("output") or {}
            if str(output.get("run_status") or "completed") != "completed" or not output.get("result"):
                continue
            owner = str(entry.get("owner_username") or "")
            same_owner = secrets.compare_digest(owner, username) if owner else secrets.compare_digest(
                str(entry.get("session_id") or ""), session_id
            )
            summary = entry.get("summary") or {}
            entry_keyword = str(summary.get("keyword") or "").strip()
            if not same_owner or not entry_keyword or _normalize_scan_keyword(entry_keyword) != keyword:
                continue
            candidates.append(entry)
        if not candidates:
            return {}
        latest = max(candidates, key=lambda item: float(item.get("cached_at", 0) or 0))
        result = ((latest.get("output") or {}).get("result") or {})
        workflow = result.get("media_production_workflow") or {}
        campaign = workflow.get("monthly_campaign") or {}
        return {
            "workflow_id": workflow.get("workflow_id") or "",
            "focus_keyword": workflow.get("focus_keyword") or keyword,
            "campaign_thesis": campaign.get("campaign_thesis") or "",
            "monthly_strategy": str(result.get("monthly_strategy") or "")[:18000],
            "weeks": [
                {
                    "week": week.get("week"),
                    "theme": week.get("theme") or "",
                    "objective": week.get("objective") or "",
                    "content_outputs": list(week.get("content_outputs") or []),
                }
                for week in (workflow.get("weeks") or [])[:4]
            ],
            "production_focus_profile": dict(result.get("production_focus_profile") or {}),
        }


def _delete_workflow_context_history_item(history_id: str, session_id: str, username: str) -> bool:
    with CACHE_LOCK:
        cache = _load_workflow_context_cache()
        entries = cache.setdefault("entries", {})
        entry = entries.get(history_id)
        if not isinstance(entry, dict) or not _can_access_history_entry(entry, session_id, username):
            return False
        entries.pop(history_id, None)
        _save_workflow_context_cache(cache)
        return True


def _prune_workflow_context_cache(now: float | None = None) -> int:
    now = time.time() if now is None else now
    cache = _load_workflow_context_cache()
    removed = _prune_workflow_context_cache_entries(cache, now)
    if removed:
        _save_workflow_context_cache(cache)
    return removed


def _prune_workflow_context_cache_entries(cache: dict, now: float) -> int:
    entries = cache.setdefault("entries", {})
    removed = 0
    for key, entry in list(entries.items()):
        cached_at = float((entry or {}).get("cached_at", 0) or 0)
        if cached_at <= 0 or now - cached_at >= WORKFLOW_CONTEXT_CACHE_TTL_SECONDS:
            entries.pop(key, None)
            removed += 1
    return removed


def _recover_interrupted_workflow_context_entries(cache: dict, now: float) -> int:
    recovered = 0
    for entry in (cache.get("entries") or {}).values():
        if not isinstance(entry, dict):
            continue
        output = entry.get("output") or {}
        if output.get("run_status") != "running":
            continue
        error = "Workflow bị gián đoạn khi dịch vụ khởi động lại. Hãy chạy lại để tạo kế hoạch mới."
        output["run_status"] = "error"
        output["error"] = error
        output["logs"] = str(output.get("logs") or error)
        entry["output"] = output
        entry["cached_at"] = now
        summary = dict(entry.get("summary") or {})
        summary["run_status"] = "error"
        summary["has_result"] = False
        summary["error"] = error
        entry["summary"] = summary
        recovered += 1
    return recovered


def _start_workflow_context_cache_cleanup() -> None:
    def cleanup_loop() -> None:
        while True:
            time.sleep(WORKFLOW_CONTEXT_CACHE_CLEANUP_INTERVAL_SECONDS)
            with CACHE_LOCK:
                _prune_workflow_context_cache()
            with JOB_LOCK:
                _prune_jobs_locked()

    with CACHE_LOCK:
        cache = _load_workflow_context_cache()
        now = time.time()
        changed = _recover_interrupted_workflow_context_entries(cache, now)
        changed += _prune_workflow_context_cache_entries(cache, now)
        if changed:
            _save_workflow_context_cache(cache)
    with JOB_LOCK:
        _prune_jobs_locked()
    worker = threading.Thread(target=cleanup_loop, daemon=True)
    worker.start()


def _create_workflow_context_history(request_payload: dict, session_id: str, username: str) -> str:
    context_key = _workflow_context_cache_key(request_payload)
    output = {
        "result": {},
        "duration_ms": 0,
        "logs": "Workflow queued.",
        "error": "",
        "history_hit": False,
        "run_status": "running",
        "context_cache_key": context_key,
    }
    return _write_workflow_context_cache(
        context_key,
        output,
        request_payload,
        session_id,
        username,
    )


def _record_workflow_context_history_error(
    history_id: str,
    request_payload: dict,
    session_id: str,
    username: str,
    error: str,
    *,
    job_id: str = "",
    current_step: str = "",
    agent_statuses: dict | None = None,
    logs: str = "",
) -> None:
    context_key = _workflow_context_cache_key(request_payload)
    output = {
        "result": {},
        "duration_ms": 0,
        "logs": logs or error,
        "error": error,
        "history_hit": False,
        "run_status": "error",
        "job_id": job_id,
        "current_step": current_step,
        "agent_statuses": dict(agent_statuses or {}),
        "context_cache_key": context_key,
    }
    _write_workflow_context_cache(
        context_key,
        output,
        request_payload,
        session_id,
        username,
        history_id=history_id,
    )


def _write_workflow_context_cache(
    context_key: str,
    output: dict,
    request_payload: dict,
    session_id: str,
    username: str,
    *,
    history_id: str = "",
) -> str:
    with CACHE_LOCK:
        cache = _load_workflow_context_cache()
        entries = cache.setdefault("entries", {})
        now = time.time()
        _prune_workflow_context_cache_entries(cache, now)
        history_id = str(history_id or uuid.uuid4().hex)
        existing = entries.get(history_id)
        if isinstance(existing, dict) and not _can_access_history_entry(existing, session_id, username):
            raise PermissionError("History item belongs to another user")
        created_at = float((existing or {}).get("created_at") or (existing or {}).get("cached_at") or now)
        cache_output = dict(output)
        cache_output["history_hit"] = False
        cache_output["logs"] = str(cache_output.get("logs") or "")
        entries[history_id] = {
            "cached_at": now,
            "created_at": created_at,
            "session_id": session_id,
            "owner_username": username,
            "context_key": context_key,
            "summary": _workflow_context_history_summary(cache_output, request_payload, created_at),
            "output": cache_output,
        }
        _save_workflow_context_cache(cache)
        return history_id


def _workflow_context_history_summary(output: dict, request_payload: dict, cached_at: float) -> dict:
    result = output.get("result") or {}
    ads = result.get("ad_library_ads") or []
    workflow = result.get("media_production_workflow") or {}
    campaign = workflow.get("monthly_campaign") or {}
    evidence = campaign.get("meta_evidence") or {}
    keyword = _normalize_scan_keyword(
        request_payload.get("ad_library_keywords") or result.get("ad_library_keywords")
    )
    run_status = str(output.get("run_status") or ("completed" if result else "running"))
    return {
        "created_at": datetime.fromtimestamp(cached_at).isoformat(timespec="seconds"),
        "keyword": keyword,
        "mode": str(request_payload.get("mode", "auto") or "auto"),
        "data_source": result.get("data_source") or "",
        "approval_status": result.get("approval_status") or "",
        "cmo_decision": result.get("cmo_decision") or "",
        "ads_count": len(ads),
        "scan_id": evidence.get("scan_id") or result.get("ad_library_scan_id") or "",
        "scanned_at": evidence.get("analyzed_at") or result.get("ad_library_scanned_at") or "",
        "competitor_ads": sum(1 for ad in ads if ad.get("source_type") == "competitor_page"),
        "keyword_ads": sum(1 for ad in ads if ad.get("source_type") == "keyword_scan"),
        "title": workflow.get("workflow_id") or f"CMO · {keyword}",
        "workflow_status": workflow.get("status") or "pending",
        "run_status": run_status,
        "has_result": bool(result),
        "error": str(output.get("error") or ""),
        "tasks_count": len(workflow.get("tasks") or []),
        "duration_ms": output.get("duration_ms", 0),
    }


def _load_workflow_context_cache() -> dict:
    if not WORKFLOW_CONTEXT_CACHE_PATH.exists():
        return {"version": WORKFLOW_CONTEXT_CACHE_VERSION, "entries": {}}
    try:
        cache = json.loads(WORKFLOW_CONTEXT_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": WORKFLOW_CONTEXT_CACHE_VERSION, "entries": {}}
    if cache.get("version") != WORKFLOW_CONTEXT_CACHE_VERSION:
        return {"version": WORKFLOW_CONTEXT_CACHE_VERSION, "entries": {}}
    if not isinstance(cache.get("entries"), dict):
        cache["entries"] = {}
    return cache


def _save_workflow_context_cache(cache: dict) -> None:
    WORKFLOW_CONTEXT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = WORKFLOW_CONTEXT_CACHE_PATH.with_name(
        f".{WORKFLOW_CONTEXT_CACHE_PATH.name}.{os.getpid()}.tmp"
    )
    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(cache, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, WORKFLOW_CONTEXT_CACHE_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)


def _build_initial_state(request_payload: dict, previous_campaign_snapshot: dict | None = None) -> dict:
    ad_library_keywords = _normalize_scan_keyword(request_payload.get("ad_library_keywords"))
    scan_mode, max_ads, reference_scan_limit = _scan_settings(request_payload)

    initial_state = create_initial_state()
    run_seed = _build_run_seed(ad_library_keywords, scan_mode)
    previous_campaign_snapshot = dict(previous_campaign_snapshot or {})
    initial_state["run_seed"] = run_seed
    initial_state["previous_campaign_snapshot"] = previous_campaign_snapshot
    initial_state["production_focus_profile"] = _production_focus_profile(
        run_seed,
        ad_library_keywords,
        previous_campaign_snapshot.get("production_focus_profile") or {},
    )
    initial_state["ad_library_keywords"] = ad_library_keywords
    initial_state["cmo_objective"] = (
        f"Phân tích tín hiệu Meta mới nhất theo keyword '{ad_library_keywords}', xây chiến dịch media 1 tháng chia 4 tuần, "
        "đề xuất brand lane SmileUp và giao việc cho Biên kịch, Đạo diễn AI, Video Editor."
    )
    initial_state["ad_library_scan_mode"] = scan_mode
    initial_state["ad_library_max_ads"] = max_ads
    initial_state["ad_library_reference_scan_limit"] = reference_scan_limit
    initial_state["ad_library_competitor_urls"] = config.AD_LIBRARY_COMPETITOR_URLS
    initial_state["ad_library_competitor_ratio"] = config.AD_LIBRARY_COMPETITOR_RATIO
    initial_state["business_economics"] = config.SMILEUP_BUSINESS_ECONOMICS
    initial_state["competitor_visual_notes"] = ""
    initial_state["competitor_video_notes"] = ""
    return initial_state


def _build_run_seed(keywords: str, scan_mode: str) -> str:
    raw = f"{keywords}|{scan_mode}|{time.time_ns()}|{uuid.uuid4().hex}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _normalize_scan_keyword(value: object) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    return (normalized or config.AD_LIBRARY_KEYWORDS)[:120].strip()


def _production_focus_profile(
    run_seed: str,
    focus_keyword: str,
    previous_profile: dict[str, str] | None = None,
) -> dict[str, str]:
    seed = str(run_seed or "0").ljust(16, "0")
    previous_profile = previous_profile or {}
    hook_styles = [
        "counter-intuitive: đi ngược quảng cáo giảm giá, nhấn vào tư vấn đúng chỉ định",
        "checklist: các câu hỏi cần hỏi trước khi làm răng sứ/implant",
        "story/problem-first: bắt đầu từ nỗi lo thật của khách Việt",
        "myth-busting: sửa hiểu lầm phổ biến nhưng không hù dọa",
        "consultation-first: mời để lại SĐT để được hỏi đúng tình trạng",
    ]
    copy_rhythms = [
        "mở bài ngắn, đoạn 1 câu mạnh, CTA đặt riêng ở cuối",
        "mở bằng câu hỏi, thân bài dạng 3 gạch đầu dòng dễ scan",
        "mở bằng tình huống đời thường, thân bài kể chuyện ngắn",
        "mở bằng checklist, mỗi ý chỉ 1-2 câu",
        "mở bằng insight khách hàng, sau đó dẫn vào quy trình SmileUp",
    ]
    production_formats = [
        "short video 30-45 giây + static proof",
        "carousel giải thích + short video hỏi đáp",
        "doctor-led video + checklist graphic",
        "patient journey video + process carousel",
        "myth-busting reel + trust-building static",
    ]
    lead_magnets = [
        "kiểm tra bước đầu xem trường hợp có phù hợp răng sứ/implant không",
        "gợi ý danh sách câu hỏi cần hỏi bác sĩ trước khi quyết định",
        "tư vấn cá nhân hóa theo tình trạng răng, thời gian mất răng và ngân sách",
        "phân biệt khi nào nên phục hình sứ, khi nào cần kiểm tra implant",
        "hẹn thăm khám để có phim chụp và kế hoạch điều trị rõ ràng",
    ]
    cta_modes = [
        "xin SĐT để SmileUp gọi lại hỏi nhanh tình trạng",
        "inbox số điện thoại kèm vấn đề răng đang gặp",
        "để lại SĐT để được gợi ý bước thăm khám phù hợp",
        "nhắn 'tư vấn' kèm SĐT để đội ngũ liên hệ",
        "comment/inbox tình trạng, bài ads vẫn ưu tiên lấy SĐT",
    ]

    hypotheses = [
        "decision-clarity: thắng bằng khả năng giúp khách hiểu đúng trước khi chọn",
        "proof-of-process: biến quy trình thăm khám thành bằng chứng tin cậy",
        "objection-to-consultation: chuyển rào cản thật thành động lực đặt lịch đủ điều kiện",
        "doctor-authority-with-restraint: dùng chuyên môn để sàng lọc, không gây áp lực",
        "patient-fit-first: đặt mức độ phù hợp của từng ca trước ưu đãi và số lượng lead",
    ]

    def pick(items: list[str], slot: int, previous_key: str) -> str:
        start = (slot * 2) % max(2, len(seed) - 1)
        index = int(seed[start : start + 2], 16) % len(items)
        if len(items) > 1 and items[index] == previous_profile.get(previous_key):
            index = (index + 1) % len(items)
        return items[index]

    return {
        "run_seed": run_seed,
        "focus_keyword": focus_keyword,
        "campaign_hypothesis": pick(hypotheses, 0, "campaign_hypothesis"),
        "hook_style": pick(hook_styles, 1, "hook_style"),
        "copy_rhythm": pick(copy_rhythms, 2, "copy_rhythm"),
        "production_format": pick(production_formats, 3, "production_format"),
        "lead_magnet": pick(lead_magnets, 4, "lead_magnet"),
        "cta_mode": pick(cta_modes, 5, "cta_mode"),
        "anti_repeat_rule": (
            "Không đổi dữ kiện để tạo cảm giác mới. Phải đổi ít nhất ba yếu tố có căn cứ trong hypothesis, "
            "audience angle, hook, format, lead magnet hoặc CTA so với kế hoạch trước."
        ),
    }


def _scan_settings(request_payload: dict) -> tuple[str, int, int]:
    return "market", 100, 20


def _model_status_label() -> str:
    models = []
    if config.OPENAI_API_KEY:
        models.append(f"CMO/complex:{config.OPENAI_MODEL}")
    if config.GEMINI_API_KEY:
        models.append(f"easy:{config.GEMINI_MODEL}")
    return " + ".join(models) if models else "local-template"


def _auth_secret() -> str:
    if config.AUTH_SECRET:
        return config.AUTH_SECRET
    return hashlib.sha256((config.ADMIN_PASSWORD or "smileup-local-secret").encode("utf-8")).hexdigest()


def _verify_credentials(username: str, password: str) -> bool:
    safe_username = str(username or "").strip()
    expected_password = config.AUTH_USERS.get(safe_username, "")
    return bool(expected_password) and secrets.compare_digest(str(password or ""), expected_password)


def _make_auth_token(username: str) -> str:
    expires_at = str(int(time.time()) + AUTH_SESSION_SECONDS)
    payload = f"{username}|{expires_at}"
    signature = hmac.new(_auth_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def _auth_username(token: str) -> str:
    try:
        username, expires_at, signature = token.split("|", 2)
        if int(expires_at) < int(time.time()):
            return ""
    except Exception:
        return ""
    if username not in config.AUTH_USERS:
        return ""
    payload = f"{username}|{expires_at}"
    expected = hmac.new(_auth_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return username if secrets.compare_digest(signature, expected) else ""


def _is_admin_user(username: str) -> bool:
    return str(username or "") in set(config.AUTH_ADMIN_USERNAMES)


def _can_access_history_entry(entry: dict, session_id: str, username: str) -> bool:
    if _is_admin_user(username):
        return True
    owner = str(entry.get("owner_username") or "")
    if owner:
        return secrets.compare_digest(owner, username)
    return secrets.compare_digest(str(entry.get("session_id") or ""), session_id)


def _session_owner_prefix(username: str) -> str:
    return hashlib.sha1(str(username or "anonymous").encode("utf-8")).hexdigest()[:12]


def _is_safe_session_id(value: str, username: str) -> bool:
    expected_prefix = _session_owner_prefix(username)
    return bool(re.fullmatch(rf"{expected_prefix}_[a-f0-9]{{32}}", str(value or "")))


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
    _start_workflow_context_cache_cleanup()
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
