from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.media_analyzer import build_text_insight_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_text_insight_agent(state: AgentState) -> AgentState:
    logger.info("Text Insight Agent analyzing competitor captions")
    fallback = build_text_insight_report(state.get("competitor_insights", []))
    report, provider = reason_with_agent_api(
        agent_name="Text Insight Agent",
        role="Đọc caption/bài viết/ads, tách hook, pain point, objection, offer, CTA và ngôn ngữ khách hàng.",
        task="Tạo report cho CMO: đâu là insight chữ viết đáng dùng cho chiến lược tháng, tuyến ads lấy SĐT và tuyến chăm sóc page.",
        context={
            "competitor_insights": state.get("competitor_insights", []),
            "ad_library_report": state.get("ad_library_report", ""),
            "high_match_ads": state.get("high_match_ads", []),
        },
        fallback=fallback,
    )
    state["text_insight_report"] = report
    state["current_step"] = "text_insight"
    state["messages"].append({"role": "text_insight", "content": f"Analyzed competitor captions with {provider}"})
    return state
