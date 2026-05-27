from graph.state import AgentState
from tools.facebook_publisher import format_facebook_message, publish_facebook_post
from utils.logger import get_logger


logger = get_logger(__name__)


def run_publisher_agent(state: AgentState) -> AgentState:
    logger.info("Publisher Agent preparing publish step")
    draft = state.get("draft_content")
    if not draft:
        state["publish_result"] = {"published": False, "reason": "Thiếu bản nháp để Publisher xử lý."}
        state["current_step"] = "error"
        state["error"] = "Publisher không nhận được bản nháp."
        return state

    approved = state.get("approval_status") == "approved" and state.get("cmo_decision") == "APPROVE_TO_PUBLISH"
    result = publish_facebook_post(draft, approved=approved)
    if not approved:
        result["reason"] = "Publisher bị chặn: CMO decision phải là APPROVE_TO_PUBLISH và approval_status phải là approved."
    result["cmo_selected_variant_index"] = state.get("cmo_selected_variant_index", -1)
    result["cmo_selected_creative_index"] = state.get("cmo_selected_creative_index", -1)
    result["cmo_decision"] = state.get("cmo_decision", "")
    result["cmo_model_votes"] = state.get("cmo_model_votes", [])
    result["campaign_payloads"] = [
        {
            "is_cmo_pick": index == state.get("cmo_selected_variant_index", -1),
            "service_line": variant.get("service_line", ""),
            "title": variant.get("title", ""),
            "image_path": variant.get("image_path", ""),
            "safe_payload_preview": format_facebook_message(variant)[:260],
        }
        for index, variant in enumerate(state.get("content_plan", []))
    ]
    state["publish_result"] = result
    state["current_step"] = "publisher"
    state["messages"].append({"role": "publisher", "content": str(result)})
    return state
