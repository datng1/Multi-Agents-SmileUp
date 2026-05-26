from graph.state import AgentState
from tools.media_analyzer import build_video_insight_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_video_insight_agent(state: AgentState) -> AgentState:
    logger.info("Video Insight Agent analyzing video notes")
    state["video_insight_report"] = build_video_insight_report(state.get("competitor_video_notes", ""))
    state["current_step"] = "video_insight"
    state["messages"].append({"role": "video_insight", "content": "Analyzed video hooks, shot notes, proof and CTA"})
    return state
