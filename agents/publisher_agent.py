from graph.state import AgentState
from tools.facebook_publisher import format_facebook_message, publish_facebook_post
from utils.logger import get_logger


logger = get_logger(__name__)


def run_publisher_agent(state: AgentState) -> AgentState:
    logger.info("Publisher Agent preparing publish step")
    draft = state.get("draft_content")
    if not draft:
        state["publish_result"] = {"published": False, "reason": "Missing draft"}
        state["current_step"] = "error"
        state["error"] = "Publisher received no draft"
        return state

    approved = state.get("approval_status") == "approved"
    result = publish_facebook_post(draft, approved=approved)
    result["campaign_payloads"] = [
        {
            "service_line": variant.get("service_line", ""),
            "title": variant.get("title", ""),
            "image_path": variant.get("image_path", ""),
            "safe_payload_preview": format_facebook_message(variant)[:260],
        }
        for variant in state.get("content_plan", [])
    ]
    state["publish_result"] = result
    state["current_step"] = "publisher"
    state["messages"].append({"role": "publisher", "content": str(result)})
    return state
