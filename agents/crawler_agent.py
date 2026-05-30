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
    if state.get("data_source") == "manual":
        insights = state.get("competitor_insights", [])
        logger.info("Crawler Agent using manual competitor input")
        state["messages"].append({"role": "crawler", "content": f"Used {len(insights)} manual competitor posts plus media notes"})
    elif config.AD_LIBRARY_ENABLED and not config.MOCK_MODE:
        try:
            keywords = state.get("ad_library_keywords") or config.AD_LIBRARY_KEYWORDS
            ads = collect_ad_library_ads(
                keywords=keywords,
                country=config.AD_LIBRARY_COUNTRY,
                max_ads=config.AD_LIBRARY_MAX_ADS,
                cache_ttl_hours=config.AD_LIBRARY_CACHE_TTL_HOURS,
                force_refresh=True,
                competitor_urls=config.AD_LIBRARY_COMPETITOR_URLS,
                competitor_ratio=config.AD_LIBRARY_COMPETITOR_RATIO,
            )
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
            reference_ad = _top_match_reference_ad(strategy_ads)
            if reference_ad:
                state["creative_reference_ad"] = reference_ad
                if state.get("creative_image_mode") == "top_match_reference":
                    state["creative_reference_note"] = (
                        "Using the highest-match Ad Library creative as layout/content reference only. "
                        "Output must be a new SmileUp image with no reused pixels, faces, logos, or original text."
                    )
            state["data_source"] = "ad_library"
            competitor_count = sum(1 for ad in ads if ad.get("source_type") == "competitor_page")
            keyword_count = sum(1 for ad in ads if ad.get("source_type") == "keyword_scan")
            state["messages"].append(
                {
                    "role": "crawler",
                    "content": (
                        f"Collected {len(insights)} Ad Library insights; {len(high_match_ads)} ads match >=95%; "
                        f"source mix {competitor_count} competitor ads / {keyword_count} keyword ads"
                    ),
                }
            )
        except Exception as exc:
            logger.warning("Ad Library scan failed, using controlled fallback ads: %s", exc)
            keywords = state.get("ad_library_keywords") or config.AD_LIBRARY_KEYWORDS
            ads = fallback_ad_library_ads(keywords)
            high_match_ads = filter_high_match_ads(ads, threshold=0.95)
            strategy_ads = high_match_ads or ads
            insights = ads_to_competitor_insights(strategy_ads)
            state["ad_library_ads"] = ads
            state["high_match_ads"] = high_match_ads
            state["high_match_threshold"] = 0.95
            state["ad_library_keywords"] = keywords
            state["ad_library_competitor_urls"] = config.AD_LIBRARY_COMPETITOR_URLS
            state["ad_library_competitor_ratio"] = config.AD_LIBRARY_COMPETITOR_RATIO
            state["ad_library_report"] = (
                "Ad Library Agent: live scan tam thoi khong kha dung tren server, "
                "he thong dung fallback benchmark noi bo de workflow khong bi dung. "
                "Can chay lai scan khi Chrome/Ad Library san sang.\n\n"
                + build_ad_library_report(
                    ads,
                    keywords,
                    high_match_ads=high_match_ads,
                    threshold=0.95,
                    competitor_urls=config.AD_LIBRARY_COMPETITOR_URLS,
                    competitor_ratio=config.AD_LIBRARY_COMPETITOR_RATIO,
                )
            )
            state["competitor_visual_notes"] = build_ad_visual_notes(strategy_ads)
            state["data_source"] = "ad_library_fallback"
            state["messages"].append({"role": "crawler", "content": f"Ad Library failed safely, used {len(insights)} fallback benchmark insights"})
    else:
        try:
            insights = crawl_facebook_posts(config.COMPETITOR_PAGE_IDS, limit=5)
        except Exception as exc:
            logger.warning("Facebook fallback crawler failed, using controlled fallback ads: %s", exc)
            insights = ads_to_competitor_insights(fallback_ad_library_ads(config.AD_LIBRARY_KEYWORDS))
        state["messages"].append({"role": "crawler", "content": f"Collected {len(insights)} insights"})

    state["competitor_insights"] = insights
    state["market_trend_summary"] = _market_summary(insights)
    state["current_step"] = "crawler"
    return state


def _top_match_reference_ad(ads: list[dict]) -> dict:
    if not ads:
        return {}
    top_ad = sorted(
        ads,
        key=lambda ad: (
            float(ad.get("sort_score", 0) or 0),
            float(ad.get("similarity", 0) or 0),
            float(ad.get("started_timestamp", 0) or 0),
        ),
        reverse=True,
    )[0]
    media_urls = [str(url) for url in top_ad.get("media_urls", []) if str(url).strip()]
    return {
        "library_id": str(top_ad.get("library_id", "")),
        "ad_url": str(top_ad.get("ad_url", "")),
        "page_name": str(top_ad.get("page_name", "")),
        "started_running": str(top_ad.get("started_running", "")),
        "ad_text": str(top_ad.get("ad_text", "")),
        "media_url": media_urls[0] if media_urls else "",
        "similarity": float(top_ad.get("similarity", 0) or 0),
        "sort_score": float(top_ad.get("sort_score", 0) or 0),
    }


def _market_summary(insights: list[dict]) -> str:
    topics: dict[str, int] = {}
    for insight in insights:
        for topic in insight.get("key_topics", []):
            topics[topic] = topics.get(topic, 0) + 1
    ranked = ", ".join(topic for topic, _ in sorted(topics.items(), key=lambda item: item[1], reverse=True))
    return f"Xu hướng nổi bật: {ranked or 'nha_khoa_tong_quat'}. Khách hàng quan tâm ưu đãi rõ ràng, tư vấn trước điều trị và chăm sóc định kỳ."
