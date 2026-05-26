from graph.state import AgentState
from tools.media_analyzer import build_text_insight_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_text_insight_agent(state: AgentState) -> AgentState:
    logger.info("Text Insight Agent analyzing competitor captions")
    state["text_insight_report"] = build_text_insight_report(state.get("competitor_insights", []))
    state["current_step"] = "text_insight"
    state["messages"].append({"role": "text_insight", "content": "Analyzed competitor captions, hooks, pain points, offers and CTAs"})
    return state
