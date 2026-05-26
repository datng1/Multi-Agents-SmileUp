from graph.state import AgentState
from tools.trend_analyzer import analyze_facebook_trends, build_visual_creative_brief
from utils.logger import get_logger


logger = get_logger(__name__)


def run_trend_agent(state: AgentState) -> AgentState:
    logger.info("Trend Agent analyzing Facebook trend signals")
    insights = state.get("competitor_insights", [])
    state["facebook_trend_analysis"] = analyze_facebook_trends(insights)
    state["visual_creative_brief"] = build_visual_creative_brief(insights)
    state["current_step"] = "trend_analysis"
    state["messages"].append({"role": "trend", "content": "Analyzed Facebook trend signals and safe visual brief"})
    return state
