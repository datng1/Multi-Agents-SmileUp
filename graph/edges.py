from graph.state import AgentState


MAX_REVISIONS = 3


def route_after_manager(state: AgentState) -> str:
    status = state.get("approval_status", "pending")
    revisions = state.get("revision_count", 0)
    cmo_next_action = state.get("cmo_next_action", "continue")

    if cmo_next_action == "publish" and status == "approved":
        return "publish"
    if cmo_next_action in {"revise", "rescan"} and revisions < MAX_REVISIONS:
        return "revise"
    if status == "approved" and cmo_next_action == "continue":
        return "publish"
    if status == "needs_revision" and revisions < MAX_REVISIONS:
        return "revise"
    state["current_step"] = "end"
    if revisions >= MAX_REVISIONS:
        state["error"] = "Max revisions reached"
    return "end"
