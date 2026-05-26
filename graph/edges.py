from graph.state import AgentState


MAX_REVISIONS = 3


def route_after_manager(state: AgentState) -> str:
    status = state.get("approval_status", "pending")
    revisions = state.get("revision_count", 0)

    if status == "approved":
        return "publish"
    if status == "needs_revision" and revisions < MAX_REVISIONS:
        return "revise"
    state["current_step"] = "end"
    if revisions >= MAX_REVISIONS:
        state["error"] = "Max revisions reached"
    return "end"
