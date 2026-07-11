from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.media_analyzer import build_text_insight_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_text_insight_agent(state: AgentState) -> AgentState:
    logger.info("Text Insight Agent analyzing competitor captions")
    focus_keyword = state.get("ad_library_keywords", "")
    fallback = build_text_insight_report(state.get("competitor_insights", []))
    report, provider = reason_with_agent_api(
        agent_name="Text Insight Agent",
        role="Đọc caption/bài viết/ads, tách hook, pain point, objection, offer, CTA và ngôn ngữ khách hàng.",
        task="Tạo report cho CMO: đâu là insight chữ viết đáng dùng cho chiến dịch media 1 tháng và nhu cầu tư vấn đủ điều kiện.",
        context={
            "focus_keyword": focus_keyword,
            "competitor_insights": state.get("competitor_insights", []),
            "ad_library_report": state.get("ad_library_report", ""),
            "high_match_ads": state.get("high_match_ads", []),
        },
        fallback=fallback,
    )
    state["text_insight_report"] = f"Focus keyword: {focus_keyword}\n{report}".strip()
    state["current_step"] = "text_insight"
    state["messages"].append({"role": "text_insight", "content": f"Analyzed competitor captions with {provider}"})
    return state
