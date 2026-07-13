from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.media_analyzer import build_video_insight_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_video_insight_agent(state: AgentState) -> AgentState:
    logger.info("Video Insight Agent analyzing video notes")
    focus_keyword = state.get("ad_library_keywords", "")
    fallback = build_video_insight_report(state.get("competitor_video_notes", ""))
    report, provider = reason_with_agent_api(
        agent_name="Video Insight Agent",
        role="Đọc transcript/shot notes/video notes, tách hook 3 giây đầu, nhịp kể, proof và CTA.",
        task="Tạo report cho CMO về hướng Reels/short video phục vụ ads lấy SĐT và chăm sóc page.",
        context={
            "focus_keyword": focus_keyword,
            "competitor_video_notes": state.get("competitor_video_notes", ""),
            "competitor_insights": state.get("competitor_insights", []),
            "facebook_trend_analysis": state.get("facebook_trend_analysis", ""),
        },
        fallback=fallback,
        complexity="easy",
    )
    state["video_insight_report"] = f"Focus keyword: {focus_keyword}\n{report}".strip()
    state["current_step"] = "video_insight"
    state["messages"].append({"role": "video_insight", "content": f"Analyzed video hooks with {provider}"})
    return state
