from graph.state import create_initial_state
from graph.workflow import build_workflow
from datetime import datetime


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
    assert result["draft_content"], "content agent should produce draft"
    assert result.get("creative_image_mode") == "upload_only", "workflow should run in upload-only media mode"
    assert result.get("creative_assets"), "workflow should produce copyable creative prompt assets"
    assert all(not asset.get("image_path") for asset in result["creative_assets"]), "creative prompt assets should not include generated images"
    assert any(asset.get("prompt_text") or asset.get("image_prompt") for asset in result["creative_assets"]), "prompt assets should include copyable prompts"
    assert all(asset.get("image_prompt") for asset in result["creative_assets"]), "each prompt asset should include an image prompt"
    assert all(asset.get("video_prompt") for asset in result["creative_assets"]), "each prompt asset should include a 40s video prompt"
    assert result["compliance_report"], "compliance agent should produce a report"
    assert result["hardness_report"], "hardness agent should produce a report"
    assert result["hardness_score"] >= 0, "hardness agent should score the workflow"
    assert result["hardness_publish_readiness"] in {"ready", "revise", "block"}, result["hardness_publish_readiness"]
    assert result["approval_status"] == "approved", result["manager_feedback"]
    assert result["cmo_decision"] == "APPROVE_TO_PUBLISH", result["cmo_feedback"]
    assert result["cmo_next_action"] == "publish", result["cmo_next_action"]
    assert result["cmo_selected_variant_index"] >= 0, "CMO should select a campaign variant"
    assert result["cmo_campaign_brief"], "CMO should produce a campaign brief"
    assert "CMO Jury" in result["cmo_jury_summary"], "CMO should summarize model jury status"
    assert result["publish_result"], "publisher should produce a result"
    print("SMOKE OK")
    print("approval_status=", result["approval_status"])
    print("cmo_decision=", result["cmo_decision"])
    print("publish_result=", result["publish_result"])


if __name__ == "__main__":
    main()
