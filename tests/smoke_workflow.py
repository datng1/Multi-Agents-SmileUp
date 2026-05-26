from graph.state import create_initial_state
from graph.workflow import build_workflow


def _enable_utf8_console() -> None:
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main() -> None:
    _enable_utf8_console()
    result = build_workflow().invoke(create_initial_state())
    assert result["competitor_insights"], "crawler should produce insights"
    assert result["text_insight_report"], "text insight agent should produce a report"
    assert result["facebook_trend_analysis"], "trend agent should produce a report"
    assert result["visual_insight_report"], "visual insight agent should produce a report"
    assert result["video_insight_report"], "video insight agent should produce a report"
    assert result["strategic_direction"], "strategy agent should produce a direction"
    assert result["draft_content"], "content agent should produce draft"
    assert result["compliance_report"], "compliance agent should produce a report"
    assert result["approval_status"] == "approved", result["manager_feedback"]
    assert result["cmo_decision"] == "APPROVE", result["cmo_feedback"]
    assert result["cmo_next_action"] == "publish", result["cmo_next_action"]
    assert result["cmo_selected_variant_index"] >= 0, "CMO should select a campaign variant"
    assert result["cmo_campaign_brief"], "CMO should produce a campaign brief"
    assert result["publish_result"], "publisher should produce a result"
    print("SMOKE OK")
    print("approval_status=", result["approval_status"])
    print("cmo_decision=", result["cmo_decision"])
    print("publish_result=", result["publish_result"])


if __name__ == "__main__":
    main()
