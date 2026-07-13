from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.media_analyzer import build_visual_insight_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_visual_insight_agent(state: AgentState) -> AgentState:
    logger.info("Visual Insight Agent analyzing image notes")
    focus_keyword = state.get("ad_library_keywords", "")
    fallback = build_visual_insight_report(
        state.get("competitor_visual_notes", ""),
        state.get("visual_direction", ""),
    )
    report, provider = reason_with_agent_api(
        agent_name="Visual Insight Agent",
        role="Đọc ghi chú ảnh/media preview, rút bố cục, text overlay, tín hiệu niềm tin và creative direction an toàn.",
        task=(
            "Tạo report cho CMO về format, bố cục, tín hiệu tin cậy và yêu cầu sản xuất cho paid/organic media. "
            "Không tạo ảnh, không rewrite ảnh đối thủ và không viết prompt sinh ảnh. Tài sản đối thủ chỉ là evidence."
        ),
        context={
            "focus_keyword": focus_keyword,
            "competitor_visual_notes": state.get("competitor_visual_notes", ""),
            "production_visual_direction": state.get("visual_direction", ""),
        },
        fallback=fallback,
        complexity="easy",
    )
    state["visual_insight_report"] = f"Focus keyword: {focus_keyword}\n{report}".strip()
    state["current_step"] = "visual_insight"
    state["messages"].append({"role": "visual_insight", "content": f"Analyzed visual notes with {provider}"})
    return state
