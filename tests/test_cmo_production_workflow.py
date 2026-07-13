from __future__ import annotations

import unittest
from unittest.mock import patch

from agents import crawler_agent
from agents.manager_agent import run_manager_agent
from graph.state import create_initial_state
from graph.workflow import PRODUCTION_AGENT_ORDER, build_workflow
from tools.campaign_intelligence import analyze_market_campaigns
from web_app import (
    _build_initial_state,
    _normalize_scan_keyword,
    _scan_settings,
    _workflow_context_cache_key,
)


FORBIDDEN_OUTPUT_FIELDS = {
    "content_plan",
    "creative_assets",
    "creative_image_mode",
    "draft_content",
    "publish_result",
}


class CMOProductionWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api_reasoning_patch = patch.object(crawler_agent.config, "AGENT_API_REASONING_ENABLED", False)
        self.api_reasoning_patch.start()

    def tearDown(self) -> None:
        self.api_reasoning_patch.stop()

    def _ready_state(self) -> dict:
        state = create_initial_state()
        state["ad_library_keywords"] = "implant toàn hàm"
        state["ad_library_ads"] = [
            {
                "library_id": f"ad-{index}",
                "page_name": f"Competitor {index % 5}",
                "ad_text": "Nha khoa rang su implant tu van ca nhan hoa",
                "source_type": "competitor_page" if index < 80 else "keyword_scan",
                "similarity": 0.98,
                "source_page_id": f"page-{index % 5}" if index < 80 else "",
            }
            for index in range(100)
        ]
        state["ad_library_competitor_urls"] = [f"https://example.com/page-{index}" for index in range(5)]
        state["high_match_ads"] = state["ad_library_ads"][:50]
        state["text_insight_report"] = "Hook, pain point, objection, offer va CTA da duoc phan tich."
        state["facebook_trend_analysis"] = "Trend short-form va carousel co bang chung tu ads."
        state["visual_insight_report"] = "Visual can co bac si, benh nhan va quy trinh tham kham."
        state["video_insight_report"] = "Video 30-45 giay, hook 3 giay dau, CTA tu van."
        state["strategic_direction"] = "Tap trung rang su va implant, tach paid media va organic."
        state["monthly_strategy"] = "- Tín hiệu ưu tiên: khách hàng cần hiểu chỉ định và kỳ vọng thực tế trước khi đặt lịch."
        state["compliance_report"] = "Khong claim tuyet doi; bat buoc disclaimer tham kham."
        state["hardness_score"] = 90
        state["hardness_production_readiness"] = "ready"
        return state

    def test_cmo_builds_assignable_media_production_workflow(self) -> None:
        result = run_manager_agent(self._ready_state())

        workflow = result["media_production_workflow"]
        tasks = workflow["tasks"]
        self.assertEqual(result["cmo_decision"], "READY_FOR_PRODUCTION")
        self.assertEqual(result["cmo_next_action"], "dispatch")
        self.assertEqual(workflow["planning_horizon"], "1 tháng / 4 tuần")
        self.assertTrue(workflow["market_intelligence"]["campaigns"])
        self.assertTrue(workflow["market_intelligence"]["selected_opportunity"])
        self.assertEqual(workflow["revenue_strategy"]["primary_conversion"], "Lịch tư vấn đủ điều kiện đã xác nhận")
        self.assertTrue(workflow["revenue_strategy"]["funnel"])
        self.assertEqual(workflow["model_routing"]["cmo_and_complex"], "gpt-5.6-sol")
        self.assertEqual(workflow["model_routing"]["easy_analysis"], "gemini-2.5-flash")
        self.assertTrue(workflow["model_routing"]["cmo_review_provider"])
        self.assertEqual(len(tasks), 12)
        self.assertEqual(len(workflow["approval_gates"]), 4)
        self.assertEqual([gate["id"] for gate in workflow["approval_gates"]], ["QW1", "QW2", "QW3", "QW4"])
        self.assertEqual(workflow["team_roles"], ["Biên kịch", "Đạo diễn AI", "Video Editor"])
        self.assertEqual(len(workflow["weeks"]), 4)
        for week in workflow["weeks"]:
            self.assertEqual(
                [assignment["owner_role"] for assignment in week["assignments"]],
                ["Biên kịch", "Đạo diễn AI", "Video Editor"],
            )
            self.assertEqual(len(week["content_outputs"]), 3)
        self.assertEqual(tasks[0]["status"], "queued")
        self.assertTrue(all(task["status"] == "waiting_dependency" for task in tasks[1:]))

        task_ids = [task["id"] for task in tasks]
        dependency_ids = set(task_ids) | {gate["id"] for gate in workflow["approval_gates"]}
        self.assertEqual(len(task_ids), len(set(task_ids)))
        for task in tasks:
            self.assertTrue(task["owner_role"])
            self.assertTrue(task["deliverables"])
            self.assertTrue(task["acceptance_criteria"])
            self.assertTrue(set(task["dependencies"]).issubset(dependency_ids))
        self.assertEqual(tasks[3]["dependencies"], ["QW1"])

        self.assertTrue(result["media_production_brief"])
        self.assertEqual(workflow["focus_keyword"], "implant toàn hàm")
        campaign = workflow["monthly_campaign"]
        self.assertEqual(campaign["focus_topic"], "implant toàn hàm")
        self.assertTrue(campaign["campaign_thesis"])
        self.assertIn("tối đa 100 ads", campaign["meta_evidence"]["basis"])
        self.assertIn("không phải bằng chứng", campaign["meta_evidence"]["caveat"].lower())
        self.assertIn("lượt quét hiện tại", campaign["meta_evidence"]["source"])
        self.assertTrue(campaign["meta_evidence"]["scan_id"].startswith("META-"))
        self.assertTrue(campaign["meta_evidence"]["analyzed_at"])
        self.assertTrue(campaign["meta_evidence"]["reference_pages"])
        self.assertTrue(campaign["meta_evidence"]["message_samples"])
        brand = workflow["brand_platform"]
        for field in ("brand_idea", "positioning", "promise", "voice", "visual_system", "signature_series", "guardrails"):
            self.assertTrue(brand[field], field)
        self.assertIn("SmileUp", brand["brand_idea"])
        self.assertIn("1 THÁNG", result["media_production_brief"])
        self.assertIn("TUẦN 1", result["media_production_brief"])
        self.assertIn("SMILEUP BRAND", result["media_production_brief"])
        self.assertIn("implant toàn hàm", result["media_production_brief"])
        self.assertTrue(result["production_handoff"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(result))

    def test_monthly_campaign_changes_with_strategy_evidence(self) -> None:
        first_state = self._ready_state()
        first_state["monthly_strategy"] = "- Tín hiệu ưu tiên: khách hàng lo ngại thời gian hồi phục sau điều trị."
        second_state = self._ready_state()
        second_state["monthly_strategy"] = "- Tín hiệu ưu tiên: khách hàng cần hiểu điều kiện xương trước khi điều trị."

        first = run_manager_agent(first_state)["media_production_workflow"]["monthly_campaign"]
        second = run_manager_agent(second_state)["media_production_workflow"]["monthly_campaign"]

        self.assertNotEqual(first["meta_evidence"]["selected_signal"], second["meta_evidence"]["selected_signal"])
        self.assertIn("hồi phục", first["campaign_thesis"])
        self.assertIn("điều kiện xương", second["meta_evidence"]["basis"])

    def test_monthly_campaign_keeps_current_scan_sources_and_messages(self) -> None:
        state = self._ready_state()
        state["ad_library_ads"][0]["page_name"] = "Current Scan Dental"
        state["ad_library_ads"][0]["ad_text"] = "Thông điệp chỉ có trong lượt quét hiện tại"

        campaign = run_manager_agent(state)["media_production_workflow"]["monthly_campaign"]

        self.assertIn("Current Scan Dental", campaign["meta_evidence"]["reference_pages"])
        self.assertIn("Thông điệp chỉ có trong lượt quét hiện tại", campaign["meta_evidence"]["message_samples"])
        self.assertIn(campaign["meta_evidence"]["scan_id"], run_manager_agent(state)["media_production_brief"])

    def test_cmo_requests_more_research_when_evidence_is_thin(self) -> None:
        result = run_manager_agent(create_initial_state())

        self.assertEqual(result["cmo_decision"], "NEEDS_MORE_RESEARCH")
        self.assertEqual(result["cmo_next_action"], "rescan")
        self.assertEqual(result["media_production_workflow"]["status"], "needs_research")
        self.assertIsNone(result["media_production_workflow"]["market_intelligence"]["selected_opportunity"])

    def test_cmo_does_not_dispatch_when_market_coverage_is_low(self) -> None:
        state = self._ready_state()
        state["market_campaign_intelligence"] = analyze_market_campaigns(
            state["ad_library_ads"][:20], "implant toàn hàm", 9, 100
        )

        result = run_manager_agent(state)

        self.assertEqual(result["cmo_decision"], "NEEDS_MORE_RESEARCH")
        self.assertIn("độ phủ thị trường", result["cmo_feedback"])

    def test_cmo_does_not_dispatch_without_compliance_report(self) -> None:
        state = self._ready_state()
        state["compliance_report"] = ""

        result = run_manager_agent(state)

        self.assertEqual(result["cmo_decision"], "NEEDS_MORE_RESEARCH")
        self.assertIn("compliance", result["cmo_feedback"])

    def test_graph_contains_analysis_and_dispatch_roles_only(self) -> None:
        self.assertEqual(
            PRODUCTION_AGENT_ORDER,
            [
                "crawler",
                "text_insight",
                "trend_analysis",
                "visual_insight",
                "video_insight",
                "strategy",
                "compliance",
                "hardness",
                "manager_review",
            ],
        )
        self.assertNotIn("content_creator", PRODUCTION_AGENT_ORDER)
        self.assertNotIn("publisher", PRODUCTION_AGENT_ORDER)

    def test_web_scan_targets_one_hundred_ads_with_twenty_ad_minimum(self) -> None:
        self.assertEqual(_scan_settings({}), ("market", 100, 20))
        self.assertEqual(_scan_settings({"ad_library_max_ads": 5}), ("market", 100, 20))

    def test_keyword_is_normalized_and_propagated_into_initial_state(self) -> None:
        keyword = _normalize_scan_keyword("  implant\n\ttoàn   hàm  ")
        self.assertEqual(keyword, "implant toàn hàm")

        state = _build_initial_state({"ad_library_keywords": "  implant\n\ttoàn   hàm  "})
        self.assertEqual(state["ad_library_keywords"], "implant toàn hàm")
        self.assertEqual(state["production_focus_profile"]["focus_keyword"], "implant toàn hàm")
        self.assertIn("implant toàn hàm", state["cmo_objective"])

    def test_keyword_is_limited_and_part_of_cache_identity(self) -> None:
        self.assertEqual(len(_normalize_scan_keyword("a" * 200)), 120)
        self.assertNotEqual(
            _workflow_context_cache_key({"ad_library_keywords": "implant toàn hàm"}),
            _workflow_context_cache_key({"ad_library_keywords": "niềng răng trong suốt"}),
        )

    def test_keyword_propagates_through_specialist_reports_and_workflow(self) -> None:
        keyword = "niềng răng trong suốt"
        ads = [
            {
                "library_id": f"keyword-ad-{index}",
                "page_name": "Controlled Dental",
                "ad_text": f"{keyword} tư vấn minh bạch {index}",
                "source_type": "keyword_scan",
                "similarity": 0.99,
            }
            for index in range(20)
        ]
        with patch.object(crawler_agent.config, "AD_LIBRARY_ENABLED", True), patch.object(
            crawler_agent, "collect_ad_library_ads", return_value=ads
        ):
            result = build_workflow().invoke(_build_initial_state({"ad_library_keywords": keyword}))

        for field in (
            "text_insight_report",
            "facebook_trend_analysis",
            "visual_insight_report",
            "video_insight_report",
            "strategic_direction",
            "compliance_report",
            "hardness_report",
        ):
            self.assertIn(keyword, result[field], field)
        self.assertEqual(result["media_production_workflow"]["focus_keyword"], keyword)
        self.assertIn(keyword, result["media_production_brief"])

    def test_ad_library_scan_does_not_depend_on_llm_mock_mode(self) -> None:
        keyword = "implant toàn hàm"
        state = _build_initial_state({"ad_library_keywords": keyword})
        ads = [
            {
                "library_id": f"ad-{index}",
                "page_name": "Dental page",
                "ad_text": f"{keyword} ad {index}",
                "source_type": "competitor_page" if index < 16 else "keyword_scan",
                "similarity": 0.99,
            }
            for index in range(20)
        ]

        with patch.object(crawler_agent.config, "AD_LIBRARY_ENABLED", True), patch.object(
            crawler_agent.config, "MOCK_MODE", True
        ), patch.object(crawler_agent, "collect_ad_library_ads", return_value=ads) as collect:
            result = crawler_agent.run_crawler_agent(state)

        self.assertEqual(collect.call_args.kwargs["keywords"], keyword)
        self.assertEqual(len(result["ad_library_ads"]), 20)
        self.assertEqual(result["data_source"], "ad_library")
        self.assertTrue(result["ad_library_scan_id"].startswith("META-"))
        self.assertTrue(result["ad_library_scanned_at"])


if __name__ == "__main__":
    unittest.main()
