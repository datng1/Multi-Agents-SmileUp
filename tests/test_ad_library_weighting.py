from tools import ad_library_scraper as scraper


def test_weighted_scan_keeps_15_ads_when_keyword_scan_is_empty() -> None:
    competitor_ads = scraper.fallback_weighted_ad_library_ads(
        "nha khoa răng sứ răng đẹp cấy implant",
        max_ads=12,
        competitor_ratio=1.0,
    )

    original_competitor = scraper._scrape_competitor_page_ads
    original_keyword = scraper._collect_keyword_scan_ads
    try:
        scraper._scrape_competitor_page_ads = lambda *args, **kwargs: competitor_ads
        scraper._collect_keyword_scan_ads = lambda *args, **kwargs: []
        ads = scraper._collect_weighted_ads(
            keywords="nha khoa răng sứ răng đẹp cấy implant",
            country="VN",
            max_ads=15,
            competitor_urls=["https://www.facebook.com/ads/library/?view_all_page_id=1"],
            competitor_ratio=0.8,
        )
    finally:
        scraper._scrape_competitor_page_ads = original_competitor
        scraper._collect_keyword_scan_ads = original_keyword

    assert len(ads) == 15
    assert sum(1 for ad in ads if ad.get("source_type") == "competitor_page") == 12
    assert sum(1 for ad in ads if ad.get("source_type") == "keyword_scan") == 3
