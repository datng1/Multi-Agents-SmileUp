from graph.state import AgentState
from tools.facebook_crawler import crawl_facebook_posts
from tools.media_analyzer import (
    build_strategic_direction,
    build_text_insight_report,
    build_video_insight_report,
    build_visual_insight_report,
)
from tools.trend_analyzer import analyze_facebook_trends, build_visual_creative_brief
from utils import config
from utils.logger import get_logger


logger = get_logger(__name__)


def run_crawler_agent(state: AgentState) -> AgentState:
    logger.info("Crawler Agent collecting competitor insights")
    if state.get("data_source") == "manual":
        insights = state.get("competitor_insights", [])
        logger.info("Crawler Agent using manual competitor input")
        state["messages"].append({"role": "crawler", "content": f"Used {len(insights)} manual competitor posts plus media notes"})
    else:
        insights = crawl_facebook_posts(config.COMPETITOR_PAGE_IDS, limit=5)
        state["messages"].append({"role": "crawler", "content": f"Collected {len(insights)} insights"})

    state["competitor_insights"] = insights
    state["market_trend_summary"] = _market_summary(insights)
    state["facebook_trend_analysis"] = analyze_facebook_trends(insights)
    state["visual_creative_brief"] = build_visual_creative_brief(insights)
    state["text_insight_report"] = build_text_insight_report(insights)
    state["visual_insight_report"] = build_visual_insight_report(
        state.get("competitor_visual_notes", ""),
        state["visual_creative_brief"],
    )
    state["video_insight_report"] = build_video_insight_report(state.get("competitor_video_notes", ""))
    state["strategic_direction"] = build_strategic_direction(
        state["text_insight_report"],
        state["visual_insight_report"],
        state["video_insight_report"],
        state["facebook_trend_analysis"],
    )
    state["current_step"] = "crawler"
    return state


def _market_summary(insights: list[dict]) -> str:
    topics: dict[str, int] = {}
    for insight in insights:
        for topic in insight.get("key_topics", []):
            topics[topic] = topics.get(topic, 0) + 1
    ranked = ", ".join(topic for topic, _ in sorted(topics.items(), key=lambda item: item[1], reverse=True))
    return f"Xu hướng nổi bật: {ranked or 'nha_khoa_tong_quat'}. Khách hàng quan tâm ưu đãi rõ ràng, tư vấn trước điều trị và chăm sóc định kỳ."
