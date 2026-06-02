from typing import Any
import unicodedata
from urllib.parse import urlencode

try:
    import requests
except Exception:
    requests = None

from graph.state import DraftContent
from utils import config


GRAPH_URL = "https://graph.facebook.com/v19.0"


def publish_facebook_post(
    draft: DraftContent,
    approved: bool,
    schedule_time: str | None = None,
    page_ids: list[str] | None = None,
    approval_override: bool = False,
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
            "safety_checks": _publish_safety_checks(approval_override, "dry_run_enforced"),
        }

    if requests is None:
        raise RuntimeError("requests is required for real Facebook Graph API calls")
    if not pages:
        raise RuntimeError("No Facebook publish pages configured")

    page_results = []
    for page in pages:
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
