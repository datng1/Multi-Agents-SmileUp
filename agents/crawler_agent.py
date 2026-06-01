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
            max_ads = int(state.get("ad_library_max_ads") or config.AD_LIBRARY_MAX_ADS)
            reference_scan_limit = int(state.get("ad_library_reference_scan_limit") or max_ads)
            ads = collect_ad_library_ads(
                keywords=keywords,
                country=config.AD_LIBRARY_COUNTRY,
                max_ads=max_ads,
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
            reference_ad = _top_match_reference_ad(strategy_ads, fallback_ads=ads, scan_limit=reference_scan_limit)
            if reference_ad:
                state["creative_reference_ad"] = reference_ad
                if state.get("creative_image_mode") == "top_match_reference":
                    selection_note = reference_ad.get("selection_note") or "Selected the best-ranked Ad Library creative with usable media."
                    state["creative_reference_note"] = (
                        f"{selection_note} "
                        "Output must be a new SmileUp image with no reused pixels, faces, logos, or original text."
                    )
                    state["messages"].append(
                        {
                            "role": "crawler",
                            "content": (
                                "Creative reference selected: "
                                f"{reference_ad.get('page_name', 'Ad Library')} "
                                f"rank #{reference_ad.get('selected_rank', '-')}, "
                                f"{len(reference_ad.get('media_candidates', []))} media candidate(s)."
                            ),
                        }
                    )
            state["data_source"] = "ad_library"
            competitor_count = sum(1 for ad in ads if ad.get("source_type") == "competitor_page")
            keyword_count = sum(1 for ad in ads if ad.get("source_type") == "keyword_scan")
            state["messages"].append(
                {
                    "role": "crawler",
                    "content": (
                        f"Collected {len(insights)} Ad Library insights; {len(high_match_ads)} ads match >=95%; "
                        f"scan mode {state.get('ad_library_scan_mode', 'quick')} ({max_ads} ads); "
                        f"source mix {competitor_count} competitor ads / {keyword_count} keyword ads"
                    ),
                }
            )
        except Exception as exc:
            logger.warning("Ad Library scan failed, using controlled fallback ads: %s", exc)
            keywords = state.get("ad_library_keywords") or config.AD_LIBRARY_KEYWORDS
            max_ads = int(state.get("ad_library_max_ads") or config.AD_LIBRARY_MAX_ADS)
            reference_scan_limit = int(state.get("ad_library_reference_scan_limit") or max_ads)
            ads = fallback_ad_library_ads(keywords)[:max_ads]
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
            reference_ad = _top_match_reference_ad(strategy_ads, fallback_ads=ads, scan_limit=reference_scan_limit)
            if reference_ad:
                state["creative_reference_ad"] = reference_ad
                if state.get("creative_image_mode") == "top_match_reference":
                    state["creative_reference_note"] = (
                        f"{reference_ad.get('selection_note') or 'Fallback benchmark selected for image reference.'} "
                        "Output must be a new SmileUp image with no reused pixels, faces, logos, or original text."
                    )
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


def _top_match_reference_ad(ads: list[dict], fallback_ads: list[dict] | None = None, scan_limit: int = 12) -> dict:
    """Pick the best ranked ad with usable media for GPT Image rewrite.

    Conversion strategy still prioritizes high-match ads. Visual generation should
    not fail just because the first one or two ads have no image, so we scan the
    top ranked candidates and then fall back to the full Ad Library result set.
    """

    ranked_primary = _rank_reference_ads(ads)
    ranked_fallback = _rank_reference_ads(fallback_ads or [])
    candidates = _dedupe_reference_ads(ranked_primary + ranked_fallback)
    if not candidates:
        return {}

    best_without_media = candidates[0]
    selected_ad = None
    selected_rank = 0
    media_urls: list[str] = []
    for index, ad in enumerate(candidates[:scan_limit], start=1):
        urls = _usable_media_urls(ad)
        if urls:
            selected_ad = ad
            selected_rank = index
            media_urls = urls
            break

    if selected_ad is None:
        selected_ad = best_without_media
        selected_rank = 1
        media_urls = []

    skipped_without_media = sum(1 for ad in candidates[: min(scan_limit, len(candidates))] if not _usable_media_urls(ad))
    selection_note = (
        f"Using ranked ad #{selected_rank} as GPT Image reference after scanning up to {min(scan_limit, len(candidates))} ads; "
        f"{skipped_without_media} candidate(s) had no usable image."
        if media_urls
        else f"No usable image found after scanning top {min(scan_limit, len(candidates))} ranked ads; GPT Image rewrite may be skipped."
    )
    return {
        "library_id": str(selected_ad.get("library_id", "")),
        "ad_url": str(selected_ad.get("ad_url", "")),
        "page_name": str(selected_ad.get("page_name", "")),
        "started_running": str(selected_ad.get("started_running", "")),
        "ad_text": str(selected_ad.get("ad_text", "")),
        "media_url": media_urls[0] if media_urls else "",
        "media_candidates": media_urls[:4],
        "similarity": float(selected_ad.get("similarity", 0) or 0),
        "sort_score": float(selected_ad.get("sort_score", 0) or 0),
        "selected_rank": selected_rank,
        "scanned_ads": min(scan_limit, len(candidates)),
        "selection_note": selection_note,
    }


def _rank_reference_ads(ads: list[dict]) -> list[dict]:
    return sorted(
        ads or [],
        key=lambda ad: (
            float(ad.get("source_weight", 0) or 0),
            float(ad.get("similarity", 0) or 0),
            float(ad.get("started_timestamp", 0) or 0),
            float(ad.get("sort_score", 0) or 0),
            int(ad.get("score", 0) or 0),
        ),
        reverse=True,
    )


def _dedupe_reference_ads(ads: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for ad in ads:
        key = str(ad.get("library_id") or "").strip()
        if not key:
            key = f"{ad.get('page_name', '')}:{str(ad.get('ad_text', ''))[:180]}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ad)
    return deduped


def _usable_media_urls(ad: dict) -> list[str]:
    urls: list[str] = []
    for raw_url in ad.get("media_urls", []) or []:
        url = str(raw_url or "").strip()
        if not url or url in urls:
            continue
        lower = url.lower()
        if not any(marker in lower for marker in ("scontent", "fbcdn", ".jpg", ".jpeg", ".png", ".webp")):
            continue
        urls.append(url)
    return urls


def _market_summary(insights: list[dict]) -> str:
    topics: dict[str, int] = {}
    for insight in insights:
        for topic in insight.get("key_topics", []):
            topics[topic] = topics.get(topic, 0) + 1
    ranked = ", ".join(topic for topic, _ in sorted(topics.items(), key=lambda item: item[1], reverse=True))
    return f"Xu hướng nổi bật: {ranked or 'nha_khoa_tong_quat'}. Khách hàng quan tâm ưu đãi rõ ràng, tư vấn trước điều trị và chăm sóc định kỳ."
