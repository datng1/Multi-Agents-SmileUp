from graph.state import AgentState
from tools.media_analyzer import build_visual_insight_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_visual_insight_agent(state: AgentState) -> AgentState:
    logger.info("Visual Insight Agent analyzing image notes")
    state["visual_insight_report"] = build_visual_insight_report(
        state.get("competitor_visual_notes", ""),
        state.get("visual_creative_brief", ""),
    )
    state["current_step"] = "visual_insight"
    state["messages"].append({"role": "visual_insight", "content": "Analyzed visual notes and safe SmileUp creative direction"})
    return state
