from graph.state import AgentState
from tools.ad_library_scraper import (
    ads_to_competitor_insights,
    build_ad_library_report,
    build_ad_visual_notes,
    collect_ad_library_ads,
)
from tools.facebook_crawler import crawl_facebook_posts
from utils import config
from utils.logger import get_logger


logger = get_logger(__name__)


def run_crawler_agent(state: AgentState) -> AgentState:
    logger.info("Crawler Agent collecting competitor insights")
    if state.get("data_source") == "manual":
        insights = state.get("competitor_insights", [])
        logger.info("Crawler Agent using manual competitor input")
        state["messages"].append({"role": "crawler", "content": f"Used {len(insights)} manual competitor posts plus media notes"})
    elif config.AD_LIBRARY_ENABLED:
        try:
            ads = collect_ad_library_ads(
                keywords=config.AD_LIBRARY_KEYWORDS,
                country=config.AD_LIBRARY_COUNTRY,
                max_ads=config.AD_LIBRARY_MAX_ADS,
                cache_ttl_hours=config.AD_LIBRARY_CACHE_TTL_HOURS,
            )
            insights = ads_to_competitor_insights(ads)
            state["ad_library_ads"] = ads
            state["ad_library_report"] = build_ad_library_report(ads, config.AD_LIBRARY_KEYWORDS)
            state["competitor_visual_notes"] = build_ad_visual_notes(ads)
            state["data_source"] = "ad_library"
            state["messages"].append({"role": "crawler", "content": f"Collected {len(insights)} Ad Library insights"})
        except Exception as exc:
            logger.warning("Ad Library scan failed, falling back to Facebook/mock crawler: %s", exc)
            insights = crawl_facebook_posts(config.COMPETITOR_PAGE_IDS, limit=5)
            state["ad_library_report"] = f"Ad Library Agent lỗi: {exc}"
            state["messages"].append({"role": "crawler", "content": f"Ad Library failed, collected {len(insights)} fallback insights"})
    else:
        insights = crawl_facebook_posts(config.COMPETITOR_PAGE_IDS, limit=5)
        state["messages"].append({"role": "crawler", "content": f"Collected {len(insights)} insights"})

    state["competitor_insights"] = insights
    state["market_trend_summary"] = _market_summary(insights)
    state["current_step"] = "crawler"
    return state


def _market_summary(insights: list[dict]) -> str:
    topics: dict[str, int] = {}
    for insight in insights:
        for topic in insight.get("key_topics", []):
            topics[topic] = topics.get(topic, 0) + 1
    ranked = ", ".join(topic for topic, _ in sorted(topics.items(), key=lambda item: item[1], reverse=True))
    return f"Xu hướng nổi bật: {ranked or 'nha_khoa_tong_quat'}. Khách hàng quan tâm ưu đãi rõ ràng, tư vấn trước điều trị và chăm sóc định kỳ."
