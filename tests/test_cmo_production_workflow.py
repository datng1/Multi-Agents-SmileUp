from __future__ import annotations

import unittest
from unittest.mock import patch

from agents import crawler_agent, strategy_agent
from agents.manager_agent import run_manager_agent
from agents.strategy_agent import _assess_strategy_quality
from graph.state import create_initial_state
from graph.workflow import PRODUCTION_AGENT_ORDER, build_workflow
from tools.ad_evidence import build_full_ad_evidence
from tools.campaign_intelligence import analyze_market_campaigns
from web_app import (
    _build_initial_state,
    _normalize_scan_keyword,
    _production_focus_profile,
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
        state["full_ad_evidence"] = build_full_ad_evidence(
            state["ad_library_ads"], focus_keyword="implant toàn hàm", scan_id="META-TEST"
        )
        state["production_focus_profile"] = _production_focus_profile("0123456789abcdef", "implant toàn hàm")
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
        self.assertEqual(workflow["model_routing"]["easy_analysis"], "gemini-3.1-pro-preview")
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
        sol_coverage = campaign["meta_evidence"]["sol_evidence_coverage"]
        self.assertEqual(sol_coverage["included_ads"], 100)
        self.assertTrue(sol_coverage["all_ads_included"])
        self.assertEqual(len(sol_coverage["priority_reference_ads"]), 12)
        self.assertTrue(all(week["evidence_refs"] for week in workflow["weeks"]))
        self.assertTrue(all(len(task["acceptance_criteria"]) >= 4 for task in tasks))
        self.assertTrue(any(item.startswith("Evidence ads:") for item in tasks[0]["inputs"]))
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

    def test_new_focus_profile_changes_at_least_three_dimensions(self) -> None:
        previous = _production_focus_profile("0123456789abcdef", "implant toàn hàm")
        current = _production_focus_profile("0123456789abcdef", "implant toàn hàm", previous)
        dimensions = ("campaign_hypothesis", "hook_style", "production_format", "lead_magnet", "cta_mode")

        changed = [key for key in dimensions if previous[key] != current[key]]

        self.assertGreaterEqual(len(changed), 3)

    def test_full_ad_evidence_contains_every_scanned_ad(self) -> None:
        ads = [
            {
                "library_id": f"library-{index}",
                "page_name": f"Dental {index % 7}",
                "ad_text": f"Thông điệp riêng của quảng cáo số {index}",
                "source_type": "keyword_scan",
                "similarity": 0.95 + (index % 5) / 100,
            }
            for index in range(1, 101)
        ]

        evidence = build_full_ad_evidence(ads, focus_keyword="implant", scan_id="META-ALL")

        self.assertEqual(evidence["observed_ads_count"], 100)
        self.assertEqual(evidence["included_ads_count"], 100)
        self.assertTrue(evidence["all_ads_included"])
        self.assertEqual(evidence["ads"][0]["evidence_id"], "AD-001")
        self.assertEqual(evidence["ads"][-1]["evidence_id"], "AD-100")
        self.assertEqual({item["library_id"] for item in evidence["ads"]}, {f"library-{index}" for index in range(1, 101)})
        self.assertFalse(any(item["text_truncated"] for item in evidence["ads"]))

    def test_strategy_sends_the_complete_ad_packet_to_sol_route(self) -> None:
        state = self._ready_state()
        state["ad_library_scan_id"] = "META-CONTEXT"
        state["run_seed"] = "0123456789abcdef"

        with patch.object(
            strategy_agent,
            "reason_with_agent_api",
            return_value=("Báo cáo strategy có cấu trúc.", "GPT (gpt-5.6-sol)"),
        ) as reason:
            result = strategy_agent.run_strategy_agent(state)

        context = reason.call_args.kwargs["context"]
        evidence = context["full_ad_evidence"]
        self.assertEqual(evidence["included_ads_count"], 100)
        self.assertEqual(evidence["ads"][0]["evidence_id"], "AD-001")
        self.assertEqual(evidence["ads"][-1]["evidence_id"], "AD-100")
        self.assertEqual(reason.call_args.kwargs["max_context_chars"], strategy_agent.MAX_STRATEGY_CONTEXT_CHARS)
        self.assertEqual(result["current_step"], "strategy")

    def test_strategy_quality_gate_requires_coverage_citations_and_novelty(self) -> None:
        evidence = build_full_ad_evidence(
            [
                {"library_id": f"ad-{index}", "ad_text": f"Ad {index}", "similarity": 0.99}
                for index in range(1, 21)
            ],
            focus_keyword="implant",
            scan_id="META-GATE",
        )
        previous_profile = _production_focus_profile("0123456789abcdef", "implant")
        current_profile = _production_focus_profile("0123456789abcdef", "implant", previous_profile)
        previous = {
            "workflow_id": "MPW-OLD",
            "monthly_strategy": "Chiến lược cũ chỉ nói về ưu đãi và giảm giá trong bốn tuần.",
            "production_focus_profile": previous_profile,
        }
        candidate = (
            "EVIDENCE_COVERAGE: 20/20\nĐiểm mới so với chiến dịch trước: chuyển sang tư vấn đúng chỉ định.\n"
            "Tuần 1 dùng AD-001 và AD-002. Tuần 2 dùng AD-003 và AD-004. "
            "Xây niềm tin chuyên môn, gỡ rào cản và tạo lịch tư vấn đủ điều kiện.\n"
            "WEEKLY_BLUEPRINT_JSON:\n```json\n"
            '{"weeks":['
            '{"week":1,"theme":"Nhận diện","objective":"Hiểu vấn đề","evidence_ids":["AD-001","AD-002"],'
            '"content_outputs":["Video 1","Video 2","Video 3"],"scriptwriter_brief":"Viết ba kịch bản nhận diện có evidence rõ ràng.",'
            '"director_brief":"Tạo storyboard nhận diện với cảnh quay khả thi tại SmileUp.",'
            '"editor_brief":"Dựng ba video nhận diện có hook và phụ đề rõ ràng."},'
            '{"week":2,"theme":"Chuyên môn","objective":"Xây niềm tin","evidence_ids":["AD-003","AD-004"],'
            '"content_outputs":["Video 4","Video 5","Video 6"],"scriptwriter_brief":"Viết ba kịch bản chuyên môn có evidence rõ ràng.",'
            '"director_brief":"Tạo storyboard chuyên môn với cảnh quay khả thi tại SmileUp.",'
            '"editor_brief":"Dựng ba video chuyên môn có hook và phụ đề rõ ràng."},'
            '{"week":3,"theme":"Gỡ rào cản","objective":"Giảm băn khoăn","evidence_ids":["AD-005","AD-006"],'
            '"content_outputs":["Video 7","Video 8","Video 9"],"scriptwriter_brief":"Viết ba kịch bản gỡ rào cản có evidence rõ ràng.",'
            '"director_brief":"Tạo storyboard gỡ rào cản với cảnh quay khả thi tại SmileUp.",'
            '"editor_brief":"Dựng ba video gỡ rào cản có hook và phụ đề rõ ràng."},'
            '{"week":4,"theme":"Chuyển đổi","objective":"Tạo lịch tư vấn","evidence_ids":["AD-007","AD-008"],'
            '"content_outputs":["Video 10","Video 11","Video 12"],"scriptwriter_brief":"Viết ba kịch bản chuyển đổi có evidence rõ ràng.",'
            '"director_brief":"Tạo storyboard chuyển đổi với cảnh quay khả thi tại SmileUp.",'
            '"editor_brief":"Dựng ba video chuyển đổi có hook và phụ đề rõ ràng."}'
            "]}\n```"
        )

        accepted = _assess_strategy_quality(previous, candidate, current_profile, evidence)
        rejected = _assess_strategy_quality(previous, previous["monthly_strategy"], previous_profile, evidence)

        self.assertTrue(accepted["accepted"])
        self.assertFalse(rejected["accepted"])
        self.assertEqual(accepted["evidence_coverage"], "20/20")
        self.assertEqual(len(accepted["cited_ad_evidence_ids"]), 8)
        self.assertEqual(accepted["weekly_blueprint_weeks"], 4)

    def test_manager_assignments_use_sol_weekly_blueprint(self) -> None:
        state = self._ready_state()
        state["sol_weekly_blueprint"] = [
            {
                "week": week,
                "theme": f"Sol theme {week}",
                "objective": f"Sol objective {week}",
                "evidence_ids": [f"AD-{week * 2 - 1:03d}", f"AD-{week * 2:03d}"],
                "content_outputs": [f"Sol video {week}.{index}" for index in range(1, 4)],
                "scriptwriter_brief": f"Sol giao biên kịch tuần {week} viết ba kịch bản theo evidence đã chọn.",
                "director_brief": f"Sol giao đạo diễn AI tuần {week} tạo storyboard chi tiết theo ba kịch bản.",
                "editor_brief": f"Sol giao editor tuần {week} dựng ba video đúng storyboard và brand.",
            }
            for week in range(1, 5)
        ]

        workflow = run_manager_agent(state)["media_production_workflow"]

        self.assertEqual(workflow["weeks"][0]["theme"], "Sol theme 1")
        self.assertEqual(workflow["weeks"][0]["content_outputs"][0], "Sol video 1.1")
        self.assertIn("Sol giao biên kịch tuần 1", workflow["weeks"][0]["assignments"][0]["objective"])
        self.assertEqual(workflow["weeks"][3]["evidence_refs"], ["AD-007", "AD-008"])

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
