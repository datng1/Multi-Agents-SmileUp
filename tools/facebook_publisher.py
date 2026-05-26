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
    if config.MOCK_MODE or config.DRY_RUN:
        return {
            "publisher_status": "dry_run",
            "publish_mode": "mock" if config.MOCK_MODE else "dry_run",
            "publish_attempted": True,
            "published": False,
            "dry_run": True,
            "published_post_id": "mock_post_001",
            "scheduled_time": schedule_time,
            "safe_payload_preview": message[:240],
            "safety_checks": ["approved_gate_passed", "draft_exists", "dry_run_enforced"],
        }

    if requests is None:
        raise RuntimeError("requests is required for real Facebook Graph API calls")

    payload: dict[str, Any] = {
        "message": message,
        "access_token": config.FACEBOOK_ACCESS_TOKEN,
    }
    if schedule_time:
        payload["published"] = "false"
        payload["scheduled_publish_time"] = schedule_time

    response = requests.post(
        f"{GRAPH_URL}/{config.FACEBOOK_PAGE_ID}/feed",
        data=payload,
        timeout=15,
    )
    response.raise_for_status()
    result = response.json()
    post_id = result.get("id")
    return {
        "publisher_status": "published",
        "publish_mode": "facebook_graph_api",
        "publish_attempted": True,
        "published": True,
        "dry_run": False,
        "published_post_id": post_id,
        "published_post_url": _facebook_post_url(post_id),
        "scheduled_time": schedule_time,
        "safety_checks": ["approved_gate_passed", "draft_exists"],
    }


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
