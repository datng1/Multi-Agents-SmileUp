import time
from typing import Any

try:
    import requests
except Exception:
    requests = None

from graph.state import CompetitorInsight
from tools.offline_fixtures import mock_insights
from tools.summarizer import extract_topics, summarize_text
from utils import config


GRAPH_URL = "https://graph.facebook.com/v19.0"


def crawl_facebook_posts(page_ids: list[str] | None = None, limit: int = 5) -> list[CompetitorInsight]:
    page_ids = page_ids or config.COMPETITOR_PAGE_IDS
    if config.MOCK_MODE or not page_ids:
        return mock_insights()

    insights: list[CompetitorInsight] = []
    for page_id in page_ids:
        time.sleep(config.settings.facebook_request_delay_seconds)
        try:
            posts = _request_posts(page_id, limit=limit)
        except Exception:
            continue
        for post in posts:
            insights.append(summarize_post({"page_id": page_id, **post}))
    return insights or mock_insights()


def summarize_post(post: dict[str, Any]) -> CompetitorInsight:
    content = post.get("message") or post.get("post_content") or ""
    engagement = _engagement_count(post)
    return {
        "page_name": str(post.get("page_name") or post.get("page_id") or "Unknown page"),
        "post_content": content,
        "engagement": engagement,
        "summary": summarize_text(content),
        "key_topics": extract_topics(content),
    }


def _request_posts(page_id: str, limit: int) -> list[dict[str, Any]]:
    if requests is None:
        raise RuntimeError("requests is required for real Facebook Graph API calls")
    fields = "id,message,created_time,permalink_url,shares,comments.summary(true),reactions.summary(true)"
    response = requests.get(
        f"{GRAPH_URL}/{page_id}/posts",
        params={"fields": fields, "limit": limit, "access_token": config.FACEBOOK_ACCESS_TOKEN},
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def _engagement_count(post: dict[str, Any]) -> int:
    shares = post.get("shares", {}).get("count", post.get("shares", 0))
    comments = post.get("comments", {}).get("summary", {}).get("total_count", post.get("comments", 0))
    reactions = post.get("reactions", {}).get("summary", {}).get("total_count", post.get("reactions", 0))
    return int(shares or 0) + int(comments or 0) + int(reactions or 0)
