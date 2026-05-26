from graph.state import AgentState
from tools.media_analyzer import build_strategic_direction
from utils.logger import get_logger


logger = get_logger(__name__)


def run_strategy_agent(state: AgentState) -> AgentState:
    logger.info("Strategy Agent selecting SmileUp direction")
    state["strategic_direction"] = build_strategic_direction(
        state.get("text_insight_report", ""),
        state.get("visual_insight_report", ""),
        state.get("video_insight_report", ""),
        state.get("facebook_trend_analysis", ""),
    )
    state["current_step"] = "strategy"
    state["messages"].append({"role": "strategy", "content": "Selected SmileUp direction for crown and implant content"})
    return state
