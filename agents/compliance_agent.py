from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.compliance import build_compliance_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_compliance_agent(state: AgentState) -> AgentState:
    logger.info("Compliance Agent checking dental marketing claims")
    fallback = build_compliance_report(state.get("draft_content"))
    report, provider = reason_with_agent_api(
        agent_name="Compliance Agent",
        role="Kiểm tra rủi ro claim nha khoa, pháp lý quảng cáo, medical safety và nền tảng trước khi CMO duyệt.",
        task="Đánh giá draft và content_plan. Chỉ ra claim phải sửa, disclaimer thiếu, CTA quá vội hoặc rủi ro y khoa.",
        context={
            "draft_content": state.get("draft_content"),
            "content_plan": state.get("content_plan", []),
            "creative_assets": state.get("creative_assets", []),
            "fallback_compliance_report": fallback,
        },
        fallback=fallback,
    )
    state["compliance_report"] = report
    state["current_step"] = "compliance"
    state["messages"].append({"role": "compliance", "content": f"Checked dental claims with {provider}"})
    return state
