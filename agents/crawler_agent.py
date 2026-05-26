from graph.state import AgentState
from tools.facebook_crawler import crawl_facebook_posts
from tools.trend_analyzer import analyze_facebook_trends, build_visual_creative_brief
from utils import config
from utils.logger import get_logger


logger = get_logger(__name__)


def run_crawler_agent(state: AgentState) -> AgentState:
    logger.info("Crawler Agent collecting competitor insights")
    if state.get("data_source") == "manual" and state.get("competitor_insights"):
        insights = state["competitor_insights"]
        logger.info("Crawler Agent using manual competitor input")
        state["messages"].append({"role": "crawler", "content": f"Used {len(insights)} manual competitor posts"})
    else:
        insights = crawl_facebook_posts(config.COMPETITOR_PAGE_IDS, limit=5)
        state["messages"].append({"role": "crawler", "content": f"Collected {len(insights)} insights"})

    state["competitor_insights"] = insights
    state["market_trend_summary"] = _market_summary(insights)
    state["facebook_trend_analysis"] = analyze_facebook_trends(insights)
    state["visual_creative_brief"] = build_visual_creative_brief(insights)
    state["current_step"] = "crawler"
    return state


def _market_summary(insights: list[dict]) -> str:
    topics: dict[str, int] = {}
    for insight in insights:
        for topic in insight.get("key_topics", []):
            topics[topic] = topics.get(topic, 0) + 1
    ranked = ", ".join(topic for topic, _ in sorted(topics.items(), key=lambda item: item[1], reverse=True))
    return f"Xu hướng nổi bật: {ranked or 'nha_khoa_tong_quat'}. Khách hàng quan tâm ưu đãi rõ ràng, tư vấn trước điều trị và chăm sóc định kỳ."
