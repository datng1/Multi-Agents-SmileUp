from typing import Any

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
) -> dict[str, Any]:
    if not approved:
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
            "safety_checks": ["approved_gate_passed", "draft_exists", "manual_page_selection_required"],
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
            "safety_checks": ["approved_gate_passed", "draft_exists", "dry_run_enforced"],
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
        "safety_checks": ["approved_gate_passed", "draft_exists"],
    }


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
            data=payload,
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()
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


def _select_pages(page_ids: list[str] | None) -> list[dict[str, str]]:
    requested = {str(page_id).strip() for page_id in (page_ids or []) if str(page_id).strip()}
    pages = list(config.FACEBOOK_PUBLISH_PAGES)
    if not requested:
        return pages[:1] if pages else []
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
    hashtags = " ".join(draft.get("hashtags", []))
    return "\n\n".join(
        part
        for part in [
            draft.get("title", "").strip(),
            draft.get("body", "").strip(),
            draft.get("call_to_action", "").strip(),
            hashtags.strip(),
        ]
        if part
    )


def _facebook_post_url(post_id: str | None) -> str:
    if not post_id:
        return ""
    return f"https://www.facebook.com/{post_id}"
