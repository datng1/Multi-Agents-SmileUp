from graph.state import AgentState, create_initial_state
from graph.workflow import build_workflow
from utils import config
from datetime import datetime


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
    initial_state = create_initial_state()
    initial_state["run_seed"] = datetime.now().isoformat(timespec="microseconds")
    result = app.invoke(initial_state)
    _show_result(result)
    return result


def _show_result(result: AgentState) -> None:
    print("\n=== BAO CAO NGAY ===")
    print(result["daily_report"])
    print("\n=== PRODUCTION BRIEF ===")
    print(result.get("media_production_brief", ""))
    print("\n=== TASK ASSIGNMENTS ===")
    workflow = result.get("media_production_workflow", {})
    for task in workflow.get("tasks", []):
        dependencies = ", ".join(task.get("dependencies", [])) or "none"
        print(f"{task.get('id')} | {task.get('owner_role')} | {task.get('title')} | deps: {dependencies}")
    print("\n=== APPROVAL GATES ===")
    for gate in workflow.get("approval_gates", []):
        print(f"{gate.get('id')} | after {gate.get('after_task')} | {gate.get('approver_role')}")
    print("\n=== PRODUCTION HANDOFF ===")
    print(result.get("production_handoff", ""))


if __name__ == "__main__":
    run_daily_marketing()
