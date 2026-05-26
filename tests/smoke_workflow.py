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
    assert result["draft_content"], "content agent should produce draft"
    assert result["approval_status"] == "approved", result["manager_feedback"]
    assert result["publish_result"], "publisher should produce a result"
    print("SMOKE OK")
    print("approval_status=", result["approval_status"])
    print("publish_result=", result["publish_result"])


if __name__ == "__main__":
    main()
