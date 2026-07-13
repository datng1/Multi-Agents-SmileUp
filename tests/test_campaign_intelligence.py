from __future__ import annotations

import unittest

from tools.campaign_intelligence import analyze_market_campaigns, build_revenue_strategy


def _ad(index: int, page: str, text: str, source_page_id: str = "") -> dict:
    return {
        "library_id": f"market-{index}",
        "page_name": page,
        "ad_text": text,
        "source_type": "competitor_page" if source_page_id else "keyword_scan",
        "source_page_id": source_page_id,
        "similarity": 0.96,
        "started_running": "Started running on 1 Jul 2026",
        "started_timestamp": 1782864000 + index,
        "media_urls": [f"https://example.com/{index}.jpg"],
    }


class CampaignIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ads = [
            _ad(1, "Nha khoa A", "Implant toàn hàm ưu đãi 20%, trả góp, đăng ký tư vấn ngay", "page-a"),
            _ad(2, "Nha khoa A", "Trồng răng implant trả góp 0%, đặt lịch hôm nay", "page-a"),
            _ad(3, "Nha khoa B", "Bác sĩ giải thích quy trình implant và điều kiện xương", "page-b"),
            _ad(4, "Nha khoa B", "Công nghệ implant, chụp phim và tư vấn cùng bác sĩ", "page-b"),
            _ad(5, "Nha khoa C", "Niềng răng trong suốt ưu đãi, inbox nhận báo giá", "page-c"),
            _ad(6, "Nha khoa D", "Khách hàng chia sẻ hành trình phục hình ăn nhai", ""),
        ]

    def test_market_analysis_clusters_campaigns_and_reports_honest_coverage(self) -> None:
        result = analyze_market_campaigns(
            self.ads,
            focus_keyword="implant toàn hàm",
            configured_competitor_pages=9,
            scan_target=100,
        )

        coverage = result["coverage"]
        self.assertEqual(coverage["ads_observed"], 6)
        self.assertEqual(coverage["unique_pages"], 4)
        self.assertEqual(coverage["configured_pages_observed"], 3)
        self.assertEqual(coverage["coverage_level"], "low")
        self.assertIn("không bảo đảm toàn bộ", coverage["limitation"].lower())
        self.assertGreaterEqual(len(result["campaigns"]), 4)
        self.assertTrue(all(campaign["representative_messages"] for campaign in result["campaigns"]))
        self.assertTrue(all(campaign["strengths"] and campaign["weaknesses"] for campaign in result["campaigns"]))
        self.assertIsNone(result["selected_opportunity"])

    def test_keyword_only_scan_cannot_claim_medium_or_high_market_coverage(self) -> None:
        ads = [_ad(index, f"Nha khoa {index}", "Bác sĩ giải thích implant và đặt lịch") for index in range(100)]
        result = analyze_market_campaigns(ads, "implant", configured_competitor_pages=0, scan_target=100)

        self.assertEqual(result["coverage"]["coverage_level"], "low")
        self.assertLess(result["coverage"]["coverage_score"], 45)

    def test_configured_competitors_must_be_observed_before_strategy_selection(self) -> None:
        ads = [_ad(index, f"Nha khoa {index}", "Implant đặt lịch tư vấn") for index in range(100)]
        result = analyze_market_campaigns(ads, "implant", configured_competitor_pages=9, scan_target=100)

        self.assertEqual(result["coverage"]["configured_pages_observed"], 0)
        self.assertLess(result["coverage"]["coverage_score"], 45)
        self.assertIsNone(result["selected_opportunity"])

    def test_selected_opportunity_changes_with_observed_funnel_gap(self) -> None:
        educational_ads = [
            _ad(index, f"Nha khoa {index}", "Bác sĩ giải thích chỉ định và rủi ro implant", f"page-{index}")
            for index in range(1, 7)
        ]
        result = analyze_market_campaigns(educational_ads, "implant", 6, 6)

        self.assertEqual(result["selected_opportunity"]["name"], "Objection-to-Consultation")
        self.assertIn("conversion", result["selected_opportunity"]["selection_reason"].lower())

    def test_revenue_strategy_uses_funnel_and_refuses_to_invent_financial_projection(self) -> None:
        intelligence = analyze_market_campaigns(self.ads, "implant toàn hàm", 3, 6)
        strategy = build_revenue_strategy("implant toàn hàm", intelligence, business_economics={})

        self.assertEqual(strategy["primary_conversion"], "Lịch tư vấn đủ điều kiện đã xác nhận")
        self.assertEqual(strategy["economics_status"], "needs_business_inputs")
        self.assertTrue(strategy["required_business_inputs"])
        self.assertTrue(strategy["scale_rules"])
        self.assertIn("không phải cam kết", strategy["revenue_caveat"].lower())

    def test_empty_market_does_not_invent_a_selected_opportunity(self) -> None:
        intelligence = analyze_market_campaigns([], "implant", 9, 100)
        strategy = build_revenue_strategy("implant", intelligence, business_economics={})

        self.assertIsNone(intelligence["selected_opportunity"])
        self.assertEqual(strategy["selected_opportunity"], {})
        self.assertEqual(strategy["market_evidence_status"], "insufficient_market_evidence")

    def test_revenue_strategy_calculates_guardrails_when_economics_are_available(self) -> None:
        intelligence = analyze_market_campaigns(self.ads, "implant toàn hàm", 3, 6)
        strategy = build_revenue_strategy(
            "implant toàn hàm",
            intelligence,
            business_economics={
                "average_case_value": 100_000_000,
                "gross_margin_rate": 0.5,
                "qualified_lead_to_booking_rate": 0.5,
                "booking_show_rate": 0.8,
                "consultation_close_rate": 0.25,
                "max_acquisition_share_of_gross_profit": 0.2,
            },
        )

        self.assertEqual(strategy["economics_status"], "ready")
        self.assertEqual(strategy["unit_economics"]["gross_profit_per_case"], 50_000_000)
        self.assertEqual(strategy["unit_economics"]["max_cost_per_acquired_case"], 10_000_000)
        self.assertEqual(strategy["unit_economics"]["max_cost_per_qualified_lead"], 1_000_000)

    def test_revenue_strategy_rejects_percentage_values_outside_zero_to_one(self) -> None:
        intelligence = analyze_market_campaigns(self.ads, "implant toàn hàm", 3, 6)
        strategy = build_revenue_strategy(
            "implant toàn hàm",
            intelligence,
            business_economics={
                "average_case_value": 100_000_000,
                "gross_margin_rate": 50,
                "qualified_lead_to_booking_rate": 0.5,
                "booking_show_rate": 0.8,
                "consultation_close_rate": 0.25,
                "max_acquisition_share_of_gross_profit": 0.2,
            },
        )

        self.assertEqual(strategy["economics_status"], "needs_business_inputs")
        self.assertIn("gross_margin_rate", strategy["invalid_business_inputs"])
        self.assertEqual(strategy["unit_economics"], {})


if __name__ == "__main__":
    unittest.main()
