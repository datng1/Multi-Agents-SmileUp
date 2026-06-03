from typing import Any
import base64
import json
import mimetypes
from pathlib import Path
import unicodedata
from urllib.parse import urlencode

try:
    import requests
except Exception:
    requests = None

from graph.state import DraftContent
from utils import config


GRAPH_URL = "https://graph.facebook.com/v19.0"
ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"


def json_dumps_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def publish_facebook_post(
    draft: DraftContent,
    approved: bool,
    schedule_time: str | None = None,
    page_ids: list[str] | None = None,
    approval_override: bool = False,
    image_path: str = "",
    image_data_url: str = "",
    image_paths: list[str] | None = None,
    image_data_urls: list[str] | None = None,
    video_paths: list[str] | None = None,
    video_data_urls: list[str] | None = None,
) -> dict[str, Any]:
    if not approved and not approval_override:
        return {
            "publisher_status": "skipped",
            "publish_mode": "blocked",
            "publish_attempted": False,
            "published": False,
            "reason": "Content is not approved",
            "safety_checks": ["approved_gate_failed"],
        }

    message = format_facebook_message(draft)
    image_source = _resolve_image_source(image_path=image_path, image_data_url=image_data_url)
    image_sources = _resolve_image_sources(
        image_paths=image_paths,
        image_data_urls=image_data_urls,
        fallback=image_source,
    )
    video_sources = _resolve_video_sources(video_paths=video_paths, video_data_urls=video_data_urls)
    pages = _select_pages(page_ids)
    if not pages:
        raise ValueError("No selected Facebook pages are configured")
    if page_ids is None and not (config.MOCK_MODE or config.DRY_RUN):
        return {
            "publisher_status": "awaiting_user_publish",
            "publish_mode": "final_review_required",
            "publish_attempted": False,
            "published": False,
            "dry_run": False,
            "target_pages": _safe_pages(pages),
            "scheduled_time": schedule_time,
            "safe_payload_preview": message[:240],
            "image_attached": bool(image_sources),
            "image_count": len(image_sources),
            "video_attached": bool(video_sources),
            "video_count": len(video_sources),
            "image_name": image_sources[0].get("name", "") if image_sources else "",
            "safety_checks": _publish_safety_checks(approval_override, "manual_page_selection_required"),
        }
    if config.MOCK_MODE or config.DRY_RUN:
        return {
            "publisher_status": "dry_run",
            "publish_mode": "mock" if config.MOCK_MODE else "dry_run",
            "publish_attempted": True,
            "published": False,
            "dry_run": True,
            "published_post_id": "mock_post_001",
            "target_pages": _safe_pages(pages),
            "page_results": [
                {
                    "page_id": page["page_id"],
                    "page_name": page["name"],
                    "published": False,
                    "dry_run": True,
                    "published_post_id": f"mock_{page['page_id']}",
                    "published_post_url": "",
                }
                for page in pages
            ],
            "scheduled_time": schedule_time,
            "safe_payload_preview": message[:240],
            "image_attached": bool(image_sources),
            "image_count": len(image_sources),
            "video_attached": bool(video_sources),
            "video_count": len(video_sources),
            "image_name": image_sources[0].get("name", "") if image_sources else "",
            "safety_checks": _publish_safety_checks(approval_override, "dry_run_enforced"),
        }

    if requests is None:
        raise RuntimeError("requests is required for real Facebook Graph API calls")
    if not pages:
        raise RuntimeError("No Facebook publish pages configured")

    page_results = []
    for page in pages:
        if video_sources:
            page_results.append(_publish_video_to_page(page, message, video_sources[0], schedule_time))
        elif len(image_sources) > 1:
            page_results.append(_publish_album_to_page(page, message, image_sources, schedule_time))
        elif image_sources:
            page_results.append(_publish_photo_to_page(page, message, image_sources[0], schedule_time))
        else:
            page_results.append(_publish_to_page(page, message, schedule_time))

    published = [item for item in page_results if item.get("published")]
    primary = published[0] if published else page_results[0]
    failed = [item for item in page_results if not item.get("published")]
    return {
        "publisher_status": "published" if published and not failed else "partial_error" if published else "error",
        "publish_mode": "facebook_graph_api",
        "publish_attempted": True,
        "published": bool(published),
        "dry_run": False,
        "published_post_id": primary.get("published_post_id", ""),
        "published_post_url": primary.get("published_post_url", ""),
        "target_pages": _safe_pages(pages),
        "page_results": page_results,
        "scheduled_time": schedule_time,
        "safe_payload_preview": message[:240],
        "image_attached": bool(image_sources),
        "image_count": len(image_sources),
        "video_attached": bool(video_sources),
        "video_count": len(video_sources),
        "image_name": image_sources[0].get("name", "") if image_sources else "",
        "safety_checks": _publish_safety_checks(approval_override),
    }


def _publish_safety_checks(approval_override: bool, *extra: str) -> list[str]:
    checks = ["draft_exists", *extra]
    if approval_override:
        return ["user_override_cmo_gate", *checks]
    return ["approved_gate_passed", *checks]


def get_publish_pages() -> list[dict[str, Any]]:
    return _safe_pages(list(config.FACEBOOK_PUBLISH_PAGES))


def _publish_to_page(page: dict[str, str], message: str, schedule_time: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message": message,
        "access_token": page["access_token"],
    }
    if schedule_time:
        payload["published"] = "false"
        payload["scheduled_publish_time"] = schedule_time

    try:
        response = requests.post(
            f"{GRAPH_URL}/{page['page_id']}/feed",
            data=_encode_graph_form(payload),
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
            timeout=15,
        )
        result = _parse_graph_response(response)
        if not response.ok:
            return {
                "page_id": page["page_id"],
                "page_name": page["name"],
                "published": False,
                "error": _graph_error_message(response, result),
            }
        post_id = result.get("id")
        return {
            "page_id": page["page_id"],
            "page_name": page["name"],
            "published": True,
            "published_post_id": post_id,
            "published_post_url": _facebook_post_url(post_id),
        }
    except Exception as exc:
        return {
            "page_id": page["page_id"],
            "page_name": page["name"],
            "published": False,
            "error": str(exc)[:220],
        }


def _publish_photo_to_page(page: dict[str, str], message: str, image_source: dict[str, Any], schedule_time: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "caption": message,
        "access_token": page["access_token"],
    }
    if schedule_time:
        payload["published"] = "false"
        payload["scheduled_publish_time"] = schedule_time

    files = {
        "source": (
            image_source.get("name") or "smileup-creative.png",
            image_source["bytes"],
            image_source.get("mime") or "image/png",
        )
    }
    try:
        response = requests.post(
            f"{GRAPH_URL}/{page['page_id']}/photos",
            data={key: _normalize_facebook_text(value) for key, value in payload.items()},
            files=files,
            timeout=45,
        )
        result = _parse_graph_response(response)
        if not response.ok:
            return {
                "page_id": page["page_id"],
                "page_name": page["name"],
                "published": False,
                "image_attached": True,
                "error": _graph_error_message(response, result),
            }
        post_id = result.get("post_id") or result.get("id")
        return {
            "page_id": page["page_id"],
            "page_name": page["name"],
            "published": True,
            "image_attached": True,
            "published_photo_id": result.get("id", ""),
            "published_post_id": post_id,
            "published_post_url": _facebook_post_url(post_id),
        }
    except Exception as exc:
        return {
            "page_id": page["page_id"],
            "page_name": page["name"],
            "published": False,
            "image_attached": True,
            "error": str(exc)[:220],
        }


def _publish_album_to_page(page: dict[str, str], message: str, image_sources: list[dict[str, Any]], schedule_time: str | None) -> dict[str, Any]:
    uploaded_ids: list[str] = []
    try:
        for image_source in image_sources[:10]:
            payload = {
                "published": "false",
                "access_token": page["access_token"],
            }
            files = {
                "source": (
                    image_source.get("name") or "smileup-creative.png",
                    image_source["bytes"],
                    image_source.get("mime") or "image/png",
                )
            }
            response = requests.post(
                f"{GRAPH_URL}/{page['page_id']}/photos",
                data={key: _normalize_facebook_text(value) for key, value in payload.items()},
                files=files,
                timeout=45,
            )
            result = _parse_graph_response(response)
            if not response.ok:
                return {
                    "page_id": page["page_id"],
                    "page_name": page["name"],
                    "published": False,
                    "image_attached": True,
                    "image_count": len(image_sources),
                    "error": _graph_error_message(response, result),
                }
            media_id = str(result.get("id") or "").strip()
            if media_id:
                uploaded_ids.append(media_id)

        if not uploaded_ids:
            raise RuntimeError("No uploaded Facebook media IDs returned")

        payload: dict[str, Any] = {
            "message": message,
            "access_token": page["access_token"],
        }
        for index, media_id in enumerate(uploaded_ids):
            payload[f"attached_media[{index}]"] = json_dumps_compact({"media_fbid": media_id})
        if schedule_time:
            payload["published"] = "false"
            payload["scheduled_publish_time"] = schedule_time
        response = requests.post(
            f"{GRAPH_URL}/{page['page_id']}/feed",
            data=_encode_graph_form(payload),
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
            timeout=30,
        )
        result = _parse_graph_response(response)
        if not response.ok:
            return {
                "page_id": page["page_id"],
                "page_name": page["name"],
                "published": False,
                "image_attached": True,
                "image_count": len(uploaded_ids),
                "uploaded_photo_ids": uploaded_ids,
                "error": _graph_error_message(response, result),
            }
        post_id = result.get("id")
        return {
            "page_id": page["page_id"],
            "page_name": page["name"],
            "published": True,
            "image_attached": True,
            "image_count": len(uploaded_ids),
            "uploaded_photo_ids": uploaded_ids,
            "published_post_id": post_id,
            "published_post_url": _facebook_post_url(post_id),
        }
    except Exception as exc:
        return {
            "page_id": page["page_id"],
            "page_name": page["name"],
            "published": False,
            "image_attached": True,
            "image_count": len(image_sources),
            "uploaded_photo_ids": uploaded_ids,
            "error": str(exc)[:220],
        }


def _publish_video_to_page(page: dict[str, str], message: str, video_source: dict[str, Any], schedule_time: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "description": message,
        "access_token": page["access_token"],
    }
    if schedule_time:
        payload["published"] = "false"
        payload["scheduled_publish_time"] = schedule_time

    files = {
        "source": (
            video_source.get("name") or "smileup-video.mp4",
            video_source["bytes"],
            video_source.get("mime") or "video/mp4",
        )
    }
    try:
        response = requests.post(
            f"{GRAPH_URL}/{page['page_id']}/videos",
            data={key: _normalize_facebook_text(value) for key, value in payload.items()},
            files=files,
            timeout=180,
        )
        result = _parse_graph_response(response)
        if not response.ok:
            return {
                "page_id": page["page_id"],
                "page_name": page["name"],
                "published": False,
                "video_attached": True,
                "error": _graph_error_message(response, result),
            }
        video_id = result.get("id")
        return {
            "page_id": page["page_id"],
            "page_name": page["name"],
            "published": True,
            "video_attached": True,
            "published_video_id": video_id,
            "published_post_id": video_id,
            "published_post_url": _facebook_post_url(video_id),
        }
    except Exception as exc:
        return {
            "page_id": page["page_id"],
            "page_name": page["name"],
            "published": False,
            "video_attached": True,
            "error": str(exc)[:220],
        }


def _resolve_image_source(*, image_path: str = "", image_data_url: str = "") -> dict[str, Any] | None:
    if image_data_url:
        return _image_source_from_data_url(image_data_url)
    if image_path:
        return _image_source_from_path(image_path)
    return None


def _resolve_image_sources(
    *,
    image_paths: list[str] | None = None,
    image_data_urls: list[str] | None = None,
    fallback: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for image_path in image_paths or []:
        source = _image_source_from_path(str(image_path or ""))
        if source and source["name"] not in seen:
            sources.append(source)
            seen.add(source["name"])
    for data_url in image_data_urls or []:
        source = _image_source_from_data_url(str(data_url or ""))
        if source:
            key = f"{source['name']}:{len(source['bytes'])}"
            if key not in seen:
                sources.append(source)
                seen.add(key)
    if not sources and fallback:
        sources.append(fallback)
    return sources[:10]


def _resolve_video_sources(
    *,
    video_paths: list[str] | None = None,
    video_data_urls: list[str] | None = None,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for video_path in video_paths or []:
        source = _video_source_from_path(str(video_path or ""))
        if source and source["name"] not in seen:
            sources.append(source)
            seen.add(source["name"])
    for data_url in video_data_urls or []:
        source = _video_source_from_data_url(str(data_url or ""))
        if source:
            key = f"{source['name']}:{len(source['bytes'])}"
            if key not in seen:
                sources.append(source)
                seen.add(key)
    return sources[:1]


def _image_source_from_path(image_path: str) -> dict[str, Any] | None:
    raw = str(image_path or "").strip()
    if not raw or raw.startswith("data:image/") or raw.startswith(("http://", "https://")):
        return None
    relative = raw.lstrip("/").replace("\\", "/")
    path = (WEB_ROOT / relative).resolve()
    try:
        path.relative_to(WEB_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Selected image is outside the publishable web directory") from exc
    if not path.exists() or not path.is_file():
        raise ValueError("Selected image file was not found on the server")
    data = path.read_bytes()
    if not data:
        raise ValueError("Selected image file is empty")
    if len(data) > 80 * 1024 * 1024:
        raise ValueError("Selected image is larger than 80 MB")
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    if not mime.startswith("image/"):
        raise ValueError("Selected file is not an image")
    return {"bytes": data, "mime": mime, "name": path.name}


def _image_source_from_data_url(data_url: str) -> dict[str, Any] | None:
    header, _, encoded = str(data_url or "").partition(",")
    if not header.startswith("data:image/") or not encoded:
        return None
    mime = header[5:].split(";", 1)[0] or "image/png"
    try:
        data = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("Selected image data is invalid") from exc
    if not data:
        raise ValueError("Selected image data is empty")
    if len(data) > 80 * 1024 * 1024:
        raise ValueError("Selected image is larger than 80 MB")
    extension = mimetypes.guess_extension(mime) or ".png"
    return {"bytes": data, "mime": mime, "name": f"smileup-final{extension}"}


def _video_source_from_path(video_path: str) -> dict[str, Any] | None:
    raw = str(video_path or "").strip()
    if not raw or raw.startswith("data:video/") or raw.startswith(("http://", "https://")):
        return None
    relative = raw.lstrip("/").replace("\\", "/")
    path = (WEB_ROOT / relative).resolve()
    try:
        path.relative_to(WEB_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Selected video is outside the publishable web directory") from exc
    if not path.exists() or not path.is_file():
        raise ValueError("Selected video file was not found on the server")
    data = path.read_bytes()
    return _validate_video_source(data, mimetypes.guess_type(path.name)[0] or "video/mp4", path.name)


def _video_source_from_data_url(data_url: str) -> dict[str, Any] | None:
    header, _, encoded = str(data_url or "").partition(",")
    if not header.startswith("data:video/") or not encoded:
        return None
    mime = header[5:].split(";", 1)[0] or "video/mp4"
    try:
        data = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("Selected video data is invalid") from exc
    extension = mimetypes.guess_extension(mime) or ".mp4"
    return _validate_video_source(data, mime, f"smileup-final{extension}")


def _validate_video_source(data: bytes, mime: str, name: str) -> dict[str, Any]:
    if not data:
        raise ValueError("Selected video file is empty")
    if len(data) > 80 * 1024 * 1024:
        raise ValueError("Selected video is larger than 80 MB")
    if not str(mime or "").startswith("video/"):
        raise ValueError("Selected file is not a video")
    return {"bytes": data, "mime": mime or "video/mp4", "name": name}


def _parse_graph_response(response: Any) -> dict[str, Any]:
    try:
        result = response.json()
    except Exception:
        return {}
    return result if isinstance(result, dict) else {}


def _graph_error_message(response: Any, result: dict[str, Any]) -> str:
    error = result.get("error") if isinstance(result.get("error"), dict) else {}
    message = str(error.get("message") or response.text or response.reason or "Facebook Graph API error")
    code = error.get("code")
    subcode = error.get("error_subcode")
    fbtrace_id = error.get("fbtrace_id")
    parts = [f"HTTP {response.status_code}", message]
    if code:
        parts.append(f"code={code}")
    if subcode:
        parts.append(f"subcode={subcode}")
    if fbtrace_id:
        parts.append(f"fbtrace_id={fbtrace_id}")
    return " | ".join(parts)[:500]


def _select_pages(page_ids: list[str] | None) -> list[dict[str, str]]:
    requested = {str(page_id).strip() for page_id in (page_ids or []) if str(page_id).strip()}
    pages = list(config.FACEBOOK_PUBLISH_PAGES)
    if not requested:
        return pages[:1] if pages else []
    configured_ids = {page["page_id"] for page in pages}
    unknown = sorted(requested - configured_ids)
    if unknown:
        raise ValueError(f"Unknown Facebook page id: {', '.join(unknown)}")
    return [page for page in pages if page["page_id"] in requested]


def _safe_pages(pages: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "page_id": page["page_id"],
            "name": page["name"],
            "has_token": bool(page.get("access_token")),
        }
        for page in pages
    ]


def format_facebook_message(draft: DraftContent) -> str:
    hashtags = " ".join(_normalize_facebook_text(tag) for tag in draft.get("hashtags", []))
    return "\n\n".join(
        part
        for part in [
            _normalize_facebook_text(draft.get("title", "")).strip(),
            _normalize_facebook_text(draft.get("body", "")).strip(),
            _normalize_facebook_text(draft.get("call_to_action", "")).strip(),
            hashtags.strip(),
        ]
        if part
    )


def _encode_graph_form(payload: dict[str, Any]) -> bytes:
    normalized = {key: _normalize_facebook_text(value) for key, value in payload.items()}
    return urlencode(normalized, doseq=True, encoding="utf-8", errors="strict").encode("utf-8")


def _normalize_facebook_text(value: Any) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    return _repair_common_mojibake(text)


def _repair_common_mojibake(text: str) -> str:
    if _mojibake_score(text) <= 0:
        return text
    best = text
    best_score = _mojibake_score(text)
    current = text
    for _ in range(2):
        improved = False
        for encoding in ("latin1", "cp1252"):
            try:
                candidate = current.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue
            score = _mojibake_score(candidate)
            if score < best_score:
                best = candidate
                best_score = score
                current = candidate
                improved = True
        if not improved:
            break
    return best


def _mojibake_score(text: str) -> int:
    markers = ("Ã", "Ä", "Æ", "Â", "ƒ", "„", "€", "œ", "áº", "á»", "�")
    return sum(text.count(marker) for marker in markers)


def _facebook_post_url(post_id: str | None) -> str:
    if not post_id:
        return ""
    return f"https://www.facebook.com/{post_id}"
