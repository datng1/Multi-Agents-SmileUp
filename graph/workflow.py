from agents.compliance_agent import run_compliance_agent
from agents.crawler_agent import run_crawler_agent
from agents.hardness_agent import run_hardness_agent
from agents.manager_agent import run_manager_agent
from agents.strategy_agent import run_strategy_agent
from agents.text_insight_agent import run_text_insight_agent
from agents.trend_agent import run_trend_agent
from agents.video_insight_agent import run_video_insight_agent
from agents.visual_insight_agent import run_visual_insight_agent
from graph.state import AgentState
from tools.workflow_progress import emit_workflow_progress

try:
    from langgraph.graph import END, StateGraph
except ImportError:
    END = "__end__"
    StateGraph = None


PRODUCTION_AGENT_ORDER = [
    "crawler",
    "text_insight",
    "trend_analysis",
    "visual_insight",
    "video_insight",
    "strategy",
    "compliance",
    "hardness",
    "manager_review",
]


PRODUCTION_AGENT_FUNCTIONS = {
    "crawler": run_crawler_agent,
    "text_insight": run_text_insight_agent,
    "trend_analysis": run_trend_agent,
    "visual_insight": run_visual_insight_agent,
    "video_insight": run_video_insight_agent,
    "strategy": run_strategy_agent,
    "compliance": run_compliance_agent,
    "hardness": run_hardness_agent,
    "manager_review": run_manager_agent,
}


class SimpleRunner:
    def invoke(self, state: AgentState) -> AgentState:
        for agent_name in PRODUCTION_AGENT_ORDER:
            state = _run_with_progress(agent_name, PRODUCTION_AGENT_FUNCTIONS[agent_name], state)
        state["current_step"] = "end"
        return state


def _run_with_progress(agent_name: str, func, state: AgentState) -> AgentState:
    emit_workflow_progress(agent_name, "running")
    try:
        return func(state)
    finally:
        emit_workflow_progress(agent_name, "done")


def _progress_node(agent_name: str, func):
    def _node(state: AgentState) -> AgentState:
        return _run_with_progress(agent_name, func, state)

    return _node


def build_workflow():
    if StateGraph is None:
        return SimpleRunner()

    workflow = StateGraph(AgentState)
    for agent_name in PRODUCTION_AGENT_ORDER:
        workflow.add_node(agent_name, _progress_node(agent_name, PRODUCTION_AGENT_FUNCTIONS[agent_name]))
    workflow.set_entry_point(PRODUCTION_AGENT_ORDER[0])
    for current, following in zip(PRODUCTION_AGENT_ORDER, PRODUCTION_AGENT_ORDER[1:]):
        workflow.add_edge(current, following)
    workflow.add_edge(PRODUCTION_AGENT_ORDER[-1], END)
    return workflow.compile()
