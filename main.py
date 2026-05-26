from graph.state import AgentState, create_initial_state
from graph.workflow import build_workflow
from utils import config


def _enable_utf8_console() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = __import__("sys").__dict__[stream_name]
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def run_daily_marketing() -> AgentState:
    _enable_utf8_console()
    print("Khoi dong Dental Marketing Multi-Agent System...")
    if config.CONFIG_WARNINGS:
        print("Mock mode enabled:", "; ".join(config.CONFIG_WARNINGS))

    app = build_workflow()
    result = app.invoke(create_initial_state())
    _show_result(result)
    return result


def _show_result(result: AgentState) -> None:
    print("\n=== BAO CAO NGAY ===")
    print(result["daily_report"])
    print("\n=== CHIEN LUOC ===")
    print(result["daily_strategy"])
    print("\n=== BAI DANG DUYET ===")
    draft = result.get("draft_content") or {}
    print(draft.get("title", ""))
    print(draft.get("body", ""))
    print(draft.get("call_to_action", ""))
    print(" ".join(draft.get("hashtags", [])))
    print("\n=== PUBLISH RESULT ===")
    print(result.get("publish_result"))


if __name__ == "__main__":
    run_daily_marketing()
