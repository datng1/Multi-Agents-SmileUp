from __future__ import annotations

import unittest
from unittest.mock import patch

from agents import crawler_agent
from agents.manager_agent import run_manager_agent
from graph.state import create_initial_state
from graph.workflow import PRODUCTION_AGENT_ORDER, build_workflow
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
    def _ready_state(self) -> dict:
        state = create_initial_state()
        state["ad_library_keywords"] = "implant toàn hàm"
        state["ad_library_ads"] = [
            {
                "library_id": f"ad-{index}",
                "page_name": f"Competitor {index % 5}",
                "ad_text": "Nha khoa rang su implant tu van ca nhan hoa",
                "source_type": "competitor_page" if index < 16 else "keyword_scan",
                "similarity": 0.98,
            }
            for index in range(20)
        ]
        state["high_match_ads"] = state["ad_library_ads"][:12]
        state["text_insight_report"] = "Hook, pain point, objection, offer va CTA da duoc phan tich."
        state["facebook_trend_analysis"] = "Trend short-form va carousel co bang chung tu ads."
        state["visual_insight_report"] = "Visual can co bac si, benh nhan va quy trinh tham kham."
        state["video_insight_report"] = "Video 30-45 giay, hook 3 giay dau, CTA tu van."
        state["strategic_direction"] = "Tap trung rang su va implant, tach paid media va organic."
        state["weekly_strategy"] = "- Tín hiệu ưu tiên: khách hàng cần hiểu chỉ định và kỳ vọng thực tế trước khi đặt lịch."
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
        self.assertEqual(workflow["planning_horizon"], "7 ngày")
        self.assertEqual(len(tasks), 3)
        self.assertEqual(len(workflow["approval_gates"]), 1)
        self.assertEqual(
            [task["owner_role"] for task in tasks],
            ["Biên kịch", "Đạo diễn AI", "Video Editor"],
        )
        self.assertEqual(tasks[0]["status"], "queued")
        self.assertTrue(all(task["status"] == "waiting_dependency" for task in tasks[1:]))

        task_ids = [task["id"] for task in tasks]
        self.assertEqual(len(task_ids), len(set(task_ids)))
        for task in tasks:
            self.assertTrue(task["owner_role"])
            self.assertTrue(task["deliverables"])
            self.assertTrue(task["acceptance_criteria"])
            self.assertTrue(set(task["dependencies"]).issubset(set(task_ids)))

        self.assertTrue(result["media_production_brief"])
        self.assertEqual(workflow["focus_keyword"], "implant toàn hàm")
        direction = workflow["weekly_direction"]
        self.assertEqual(direction["focus_topic"], "implant toàn hàm")
        self.assertTrue(direction["primary_push"])
        self.assertEqual(len(direction["recommended_outputs"]), 3)
        self.assertIn("20 ads", direction["objective_basis"])
        self.assertIn("không phải bằng chứng", direction["evidence_caveat"].lower())
        self.assertTrue(direction["not_recommended"])
        self.assertIn("7 NGÀY", result["media_production_brief"])
        self.assertIn("implant toàn hàm", result["media_production_brief"])
        self.assertTrue(result["production_handoff"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(result))

    def test_weekly_direction_changes_with_strategy_evidence(self) -> None:
        first_state = self._ready_state()
        first_state["weekly_strategy"] = "- Tín hiệu ưu tiên: khách hàng lo ngại thời gian hồi phục sau điều trị."
        second_state = self._ready_state()
        second_state["weekly_strategy"] = "- Tín hiệu ưu tiên: khách hàng cần hiểu điều kiện xương trước khi điều trị."

        first = run_manager_agent(first_state)["media_production_workflow"]["weekly_direction"]
        second = run_manager_agent(second_state)["media_production_workflow"]["weekly_direction"]

        self.assertNotEqual(first["evidence_signal"], second["evidence_signal"])
        self.assertIn("hồi phục", first["primary_push"])
        self.assertIn("điều kiện xương", second["objective_basis"])

    def test_cmo_requests_more_research_when_evidence_is_thin(self) -> None:
        result = run_manager_agent(create_initial_state())

        self.assertEqual(result["cmo_decision"], "NEEDS_MORE_RESEARCH")
        self.assertEqual(result["cmo_next_action"], "rescan")
        self.assertEqual(result["media_production_workflow"]["status"], "needs_research")

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

    def test_web_scan_is_always_twenty_ads(self) -> None:
        self.assertEqual(_scan_settings({}), ("auto", 20, 20))
        self.assertEqual(_scan_settings({"ad_library_max_ads": 5}), ("auto", 20, 20))

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


if __name__ == "__main__":
    unittest.main()
