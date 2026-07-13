import unittest

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


class AdLibraryWeightingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_competitor = scraper._scrape_competitor_page_ads
        self.original_keyword = scraper._collect_keyword_scan_ads
        self.original_scrape = scraper._scrape_ad_library
        self.original_read_cache = scraper._read_cache
        self.original_write_cache = scraper._write_cache

    def tearDown(self) -> None:
        scraper._scrape_competitor_page_ads = self.original_competitor
        scraper._collect_keyword_scan_ads = self.original_keyword
        scraper._scrape_ad_library = self.original_scrape
        scraper._read_cache = self.original_read_cache
        scraper._write_cache = self.original_write_cache

    def test_weighted_scan_keeps_16_competitor_and_4_keyword_ads(self) -> None:
        scraper._scrape_competitor_page_ads = lambda *args, **kwargs: _fake_ads(16, "competitor_page")
        scraper._collect_keyword_scan_ads = lambda *args, **kwargs: _fake_ads(4, "keyword_scan")
        ads = scraper._collect_weighted_ads(
            keywords="nha khoa rang su rang dep cay implant",
            country="VN",
            max_ads=20,
            competitor_urls=["https://www.facebook.com/ads/library/?view_all_page_id=1"],
            competitor_ratio=0.8,
        )
        self.assertEqual(len(ads), 20)
        self.assertEqual(sum(ad.get("source_type") == "competitor_page" for ad in ads), 16)
        self.assertEqual(sum(ad.get("source_type") == "keyword_scan" for ad in ads), 4)

    def test_weighted_scan_stops_when_live_keyword_quota_is_missing(self) -> None:
        scraper._scrape_competitor_page_ads = lambda *args, **kwargs: _fake_ads(16, "competitor_page")
        scraper._collect_keyword_scan_ads = lambda *args, **kwargs: []
        with self.assertRaisesRegex(RuntimeError, "Fallback is disabled"):
            scraper._collect_weighted_ads(
                keywords="nha khoa rang su rang dep cay implant",
                country="VN",
                max_ads=20,
                competitor_urls=["https://www.facebook.com/ads/library/?view_all_page_id=1"],
                competitor_ratio=0.8,
            )

    def test_broad_scan_accepts_partial_source_when_minimum_evidence_is_met(self) -> None:
        scraper._scrape_competitor_page_ads = lambda *args, **kwargs: _fake_ads(25, "competitor_page")
        scraper._collect_keyword_scan_ads = lambda *args, **kwargs: []

        ads = scraper._collect_weighted_ads(
            keywords="implant toàn hàm",
            country="VN",
            max_ads=100,
            min_ads=20,
            competitor_urls=["https://www.facebook.com/ads/library/?view_all_page_id=1"],
            competitor_ratio=0.8,
        )

        self.assertEqual(len(ads), 25)

    def test_broad_scan_rejects_total_below_minimum_evidence(self) -> None:
        scraper._scrape_competitor_page_ads = lambda *args, **kwargs: _fake_ads(15, "competitor_page")
        scraper._collect_keyword_scan_ads = lambda *args, **kwargs: _fake_ads(4, "keyword_scan")

        with self.assertRaisesRegex(RuntimeError, "minimum accepted 20"):
            scraper._collect_weighted_ads(
                keywords="implant toàn hàm",
                country="VN",
                max_ads=100,
                min_ads=20,
                competitor_urls=["https://www.facebook.com/ads/library/?view_all_page_id=1"],
                competitor_ratio=0.8,
            )

    def test_keyword_scan_uses_only_the_requested_keyword(self) -> None:
        self.assertEqual(scraper._keyword_scan_queries("  implant toàn hàm  "), ["implant toàn hàm"])

    def test_weighted_scan_backfills_keyword_quota_after_cross_source_duplicate(self) -> None:
        competitor_ads = _fake_ads(16, "competitor_page")
        duplicate = dict(competitor_ads[0], source_type="keyword_scan", source_weight=0.2, started_timestamp=9999)
        keyword_ads = [duplicate, *_fake_ads(4, "keyword_scan")]
        scraper._scrape_competitor_page_ads = lambda *args, **kwargs: competitor_ads
        scraper._collect_keyword_scan_ads = lambda *args, **kwargs: keyword_ads

        ads = scraper._collect_weighted_ads(
            keywords="implant toàn hàm",
            country="VN",
            max_ads=20,
            competitor_urls=["https://www.facebook.com/ads/library/?view_all_page_id=1"],
            competitor_ratio=0.8,
        )

        self.assertEqual(len(ads), 20)
        self.assertEqual(sum(ad.get("source_type") == "keyword_scan" for ad in ads), 4)

    def test_keyword_only_scan_rejects_less_than_requested_count(self) -> None:
        scraper._scrape_ad_library = lambda *args, **kwargs: _fake_ads(3, "keyword_scan")
        scraper._write_cache = lambda *args, **kwargs: None

        with self.assertRaisesRegex(RuntimeError, "need 20 keyword ads"):
            scraper.collect_ad_library_ads(
                keywords="implant toàn hàm",
                country="VN",
                max_ads=20,
                force_refresh=True,
                competitor_urls=[],
            )

    def test_short_cache_is_ignored_and_refreshed_to_requested_count(self) -> None:
        scraper._read_cache = lambda *args, **kwargs: _fake_ads(3, "keyword_scan")
        scraper._scrape_ad_library = lambda *args, **kwargs: _fake_ads(20, "keyword_scan")
        scraper._write_cache = lambda *args, **kwargs: None

        ads = scraper.collect_ad_library_ads(
            keywords="implant toàn hàm",
            country="VN",
            max_ads=20,
            force_refresh=False,
            competitor_urls=[],
        )

        self.assertEqual(len(ads), 20)


if __name__ == "__main__":
    unittest.main()
