import contextlib
import base64
import hashlib
import io
import json
import re
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

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
                    "ai_provider": config.AI_PROVIDER,
                    "ai_model": _model_status_label(),
                    "cmo_jury_enabled": config.CMO_JURY_ENABLED,
                    "ad_library_enabled": config.AD_LIBRARY_ENABLED,
                    "ad_library_keywords": config.AD_LIBRARY_KEYWORDS,
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
            request_payload = self._read_json()
            manual_text = str(request_payload.get("manual_competitor_posts", "")).strip()
            visual_notes = str(request_payload.get("manual_visual_notes", "")).strip()
            video_notes = str(request_payload.get("manual_video_notes", "")).strip()
            ad_library_keywords = str(request_payload.get("ad_library_keywords", "")).strip()
            creative_image_mode = str(request_payload.get("creative_image_mode", "auto")).strip() or "auto"
            creative_image_name = str(request_payload.get("creative_image_name", "")).strip()
            creative_image_data_url = str(request_payload.get("creative_image_data_url", "")).strip()
            initial_state = create_initial_state()
            initial_state["ad_library_keywords"] = ad_library_keywords or config.AD_LIBRARY_KEYWORDS
            initial_state["competitor_visual_notes"] = visual_notes
            initial_state["competitor_video_notes"] = video_notes
            if creative_image_mode not in {"auto", "owned", "layout_reference"}:
                creative_image_mode = "auto"
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

            started_at = time.perf_counter()
            with contextlib.redirect_stdout(log_buffer), contextlib.redirect_stderr(log_buffer):
                result = build_workflow().invoke(initial_state)
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

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            return {}
        raw_body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw_body or "{}")

    def log_message(self, format: str, *args) -> None:
        return


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


if __name__ == "__main__":
    main()
