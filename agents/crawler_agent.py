from graph.state import AgentState
from tools.ad_library_scraper import (
    ads_to_competitor_insights,
    build_ad_library_report,
    build_ad_visual_notes,
    collect_ad_library_ads,
    filter_high_match_ads,
)
from tools.facebook_crawler import crawl_facebook_posts
from tools.offline_fixtures import fallback_ad_library_ads
from utils import config
from utils.logger import get_logger


logger = get_logger(__name__)


def run_crawler_agent(state: AgentState) -> AgentState:
    logger.info("Crawler Agent collecting competitor insights")
    if config.AD_LIBRARY_ENABLED:
        keywords = state.get("ad_library_keywords") or config.AD_LIBRARY_KEYWORDS
        max_ads = int(state.get("ad_library_max_ads") or config.AD_LIBRARY_MAX_ADS)
        try:
            ads = collect_ad_library_ads(
                keywords=keywords,
                country=config.AD_LIBRARY_COUNTRY,
                max_ads=max_ads,
                cache_ttl_hours=config.AD_LIBRARY_CACHE_TTL_HOURS,
                force_refresh=True,
                competitor_urls=config.AD_LIBRARY_COMPETITOR_URLS,
                competitor_ratio=config.AD_LIBRARY_COMPETITOR_RATIO,
            )
        except Exception as exc:
            message = f"Ad Library live scan failed with fallback disabled: {exc}"
            logger.exception(message)
            state["current_step"] = "error"
            state["error"] = message
            state["messages"].append({"role": "crawler", "content": message})
            raise RuntimeError(message) from exc
        high_match_ads = filter_high_match_ads(ads, threshold=0.95)
        strategy_ads = high_match_ads or ads
        insights = ads_to_competitor_insights(strategy_ads)
        state["ad_library_ads"] = ads
        state["high_match_ads"] = high_match_ads
        state["high_match_threshold"] = 0.95
        state["ad_library_keywords"] = keywords
        state["ad_library_competitor_urls"] = config.AD_LIBRARY_COMPETITOR_URLS
        state["ad_library_competitor_ratio"] = config.AD_LIBRARY_COMPETITOR_RATIO
        state["ad_library_report"] = build_ad_library_report(
            ads,
            keywords,
            high_match_ads=high_match_ads,
            threshold=0.95,
            competitor_urls=config.AD_LIBRARY_COMPETITOR_URLS,
            competitor_ratio=config.AD_LIBRARY_COMPETITOR_RATIO,
        )
        state["competitor_visual_notes"] = build_ad_visual_notes(strategy_ads)
        state["data_source"] = "ad_library"
        competitor_count = sum(1 for ad in ads if ad.get("source_type") == "competitor_page")
        keyword_count = sum(1 for ad in ads if ad.get("source_type") == "keyword_scan")
        state["messages"].append(
            {
                "role": "crawler",
                "content": (
                    f"Collected {len(insights)} live Ad Library insights; {len(high_match_ads)} ads match >=95%; "
                    f"scan mode {state.get('ad_library_scan_mode', 'quick')} ({max_ads} ads); "
                    f"source mix {competitor_count} competitor ads / {keyword_count} keyword ads; fallback disabled"
                ),
            }
        )
    else:
        try:
            insights = crawl_facebook_posts(config.COMPETITOR_PAGE_IDS, limit=5)
        except Exception as exc:
            logger.warning("Facebook fallback crawler failed, using controlled fallback ads: %s", exc)
            insights = ads_to_competitor_insights(fallback_ad_library_ads(config.AD_LIBRARY_KEYWORDS))
        state["data_source"] = "mock" if config.MOCK_MODE else "fallback"
        state["messages"].append({"role": "crawler", "content": f"Collected {len(insights)} controlled insights"})

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
