import pytest

from tools import ad_library_scraper as scraper


def _fake_ads(count: int, source_type: str) -> list[dict]:
    return [
        {
            "library_id": f"{source_type}-{index}",
            "page_name": f"{source_type} page {index}",
            "ad_text": f"nha khoa rang su implant live ad {index}",
            "ad_url": f"https://facebook.com/ads/library/?id={source_type}-{index}",
            "source_type": source_type,
            "source_weight": 0.8 if source_type == "competitor_page" else 0.2,
            "similarity": 0.99,
            "started_timestamp": 1000 + index,
            "sort_score": 1000 + index,
            "score": 10,
        }
        for index in range(count)
    ]


def test_weighted_scan_keeps_12_competitor_and_3_keyword_ads() -> None:
    original_competitor = scraper._scrape_competitor_page_ads
    original_keyword = scraper._collect_keyword_scan_ads
    try:
        scraper._scrape_competitor_page_ads = lambda *args, **kwargs: _fake_ads(12, "competitor_page")
        scraper._collect_keyword_scan_ads = lambda *args, **kwargs: _fake_ads(3, "keyword_scan")
        ads = scraper._collect_weighted_ads(
            keywords="nha khoa rang su rang dep cay implant",
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


def test_weighted_scan_stops_when_live_keyword_quota_is_missing() -> None:
    original_competitor = scraper._scrape_competitor_page_ads
    original_keyword = scraper._collect_keyword_scan_ads
    try:
        scraper._scrape_competitor_page_ads = lambda *args, **kwargs: _fake_ads(12, "competitor_page")
        scraper._collect_keyword_scan_ads = lambda *args, **kwargs: []
        with pytest.raises(RuntimeError, match="Fallback is disabled"):
            scraper._collect_weighted_ads(
                keywords="nha khoa rang su rang dep cay implant",
                country="VN",
                max_ads=15,
                competitor_urls=["https://www.facebook.com/ads/library/?view_all_page_id=1"],
                competitor_ratio=0.8,
            )
    finally:
        scraper._scrape_competitor_page_ads = original_competitor
        scraper._collect_keyword_scan_ads = original_keyword
