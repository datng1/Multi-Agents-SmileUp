from datetime import datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph.state import create_initial_state
from graph.workflow import build_workflow


FORBIDDEN_OUTPUT_FIELDS = {
    "content_plan",
    "creative_assets",
    "draft_content",
    "publish_result",
}


def _enable_utf8_console() -> None:
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main() -> None:
    _enable_utf8_console()
    initial_state = create_initial_state()
    initial_state["run_seed"] = datetime.now().isoformat(timespec="microseconds")
    result = build_workflow().invoke(initial_state)
    assert result["competitor_insights"], "crawler should produce insights"
    assert result["text_insight_report"], "text insight agent should produce a report"
    assert result["facebook_trend_analysis"], "trend agent should produce a report"
    assert result["visual_insight_report"], "visual insight agent should produce a report"
    assert result["video_insight_report"], "video insight agent should produce a report"
    assert result["strategic_direction"], "strategy agent should produce a direction"
    assert result["compliance_report"], "compliance agent should produce a report"
    assert result["hardness_report"], "hardness agent should produce a report"
    assert result["hardness_score"] >= 0, "hardness agent should score the workflow"
    assert result["hardness_production_readiness"] in {"ready", "review", "blocked"}
    assert result["cmo_campaign_brief"], "CMO should produce a campaign brief"
    workflow = result["media_production_workflow"]
    assert len(workflow["tasks"]) == 3, workflow["tasks"]
    assert len(workflow["approval_gates"]) == 1, workflow["approval_gates"]
    assert [task["owner_role"] for task in workflow["tasks"]] == ["Biên kịch", "Đạo diễn AI", "Video Editor"]
    assert all(task.get("owner_role") and task.get("deliverables") for task in workflow["tasks"])
    assert result["production_handoff"], "CMO should produce a handoff"
    assert not FORBIDDEN_OUTPUT_FIELDS.intersection(result), FORBIDDEN_OUTPUT_FIELDS.intersection(result)
    print("SMOKE OK")
    print("approval_status=", result["approval_status"])
    print("cmo_decision=", result["cmo_decision"])
    print("production_tasks=", len(workflow["tasks"]))


if __name__ == "__main__":
    main()
