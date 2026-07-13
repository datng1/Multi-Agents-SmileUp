import hashlib
import json
from datetime import datetime

from graph.state import AgentState
from tools.ad_library_scraper import (
    ads_to_competitor_insights,
    build_ad_library_report,
    build_ad_visual_notes,
    collect_ad_library_ads,
    filter_high_match_ads,
)
from tools.campaign_intelligence import analyze_market_campaigns
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
        min_ads = int(state.get("ad_library_reference_scan_limit") or 20)
        try:
            ads = collect_ad_library_ads(
                keywords=keywords,
                country=config.AD_LIBRARY_COUNTRY,
                max_ads=max_ads,
                cache_ttl_hours=config.AD_LIBRARY_CACHE_TTL_HOURS,
                force_refresh=True,
                competitor_urls=config.AD_LIBRARY_COMPETITOR_URLS,
                competitor_ratio=config.AD_LIBRARY_COMPETITOR_RATIO,
                min_ads=min_ads,
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
        state["ad_library_scanned_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        state["ad_library_scan_id"] = _ad_library_scan_id(keywords, ads)
        state["market_campaign_intelligence"] = analyze_market_campaigns(
            ads,
            focus_keyword=keywords,
            configured_competitor_pages=len(config.AD_LIBRARY_COMPETITOR_URLS),
            scan_target=max_ads,
        )
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
            scan_target=max_ads,
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
        benchmark_ads = fallback_ad_library_ads(config.AD_LIBRARY_KEYWORDS)
        try:
            insights = crawl_facebook_posts(config.COMPETITOR_PAGE_IDS, limit=5)
        except Exception as exc:
            logger.warning("Facebook fallback crawler failed, using controlled fallback ads: %s", exc)
            insights = ads_to_competitor_insights(benchmark_ads)
        state["ad_library_ads"] = benchmark_ads
        state["market_campaign_intelligence"] = analyze_market_campaigns(
            benchmark_ads,
            focus_keyword=config.AD_LIBRARY_KEYWORDS,
            configured_competitor_pages=0,
            scan_target=int(state.get("ad_library_max_ads") or config.AD_LIBRARY_MAX_ADS),
        )
        state["ad_library_scanned_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        state["ad_library_scan_id"] = _ad_library_scan_id(config.AD_LIBRARY_KEYWORDS, benchmark_ads)
        state["data_source"] = "mock" if config.MOCK_MODE else "fallback"
        state["messages"].append({"role": "crawler", "content": f"Collected {len(insights)} controlled insights"})

    state["competitor_insights"] = insights
    state["market_trend_summary"] = _market_summary(insights)
    state["current_step"] = "crawler"
    return state


def _ad_library_scan_id(keywords: str, ads: list[dict]) -> str:
    snapshot = {
        "keywords": keywords,
        "ads": [
            {
                "library_id": ad.get("library_id", ""),
                "page_name": ad.get("page_name", ""),
                "ad_text": ad.get("ad_text", ""),
                "source_type": ad.get("source_type", ""),
            }
            for ad in ads
        ],
    }
    digest = hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16].upper()
    return f"META-{digest}"


def _market_summary(insights: list[dict]) -> str:
    topics: dict[str, int] = {}
    for insight in insights:
        for topic in insight.get("key_topics", []):
            topics[topic] = topics.get(topic, 0) + 1
    ranked = ", ".join(topic for topic, _ in sorted(topics.items(), key=lambda item: item[1], reverse=True))
    return f"Xu hướng nổi bật: {ranked or 'nha_khoa_tong_quat'}. Khách hàng quan tâm ưu đãi rõ ràng, tư vấn trước điều trị và chăm sóc định kỳ."
