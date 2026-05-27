from agents.compliance_agent import run_compliance_agent
from agents.content_agent import run_content_agent
from agents.crawler_agent import run_crawler_agent
from agents.hardness_agent import run_hardness_agent
from agents.manager_agent import run_manager_agent
from agents.publisher_agent import run_publisher_agent
from agents.strategy_agent import run_strategy_agent
from agents.text_insight_agent import run_text_insight_agent
from agents.trend_agent import run_trend_agent
from agents.video_insight_agent import run_video_insight_agent
from agents.visual_insight_agent import run_visual_insight_agent
from graph.edges import route_after_manager
from graph.state import AgentState

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = "__end__"
    StateGraph = None


class SimpleRunner:
    def invoke(self, state: AgentState) -> AgentState:
        state = run_crawler_agent(state)
        state = run_text_insight_agent(state)
        state = run_trend_agent(state)
        state = run_visual_insight_agent(state)
        state = run_video_insight_agent(state)
        state = run_strategy_agent(state)
        state = run_content_agent(state)

        while True:
            state = run_compliance_agent(state)
            state = run_hardness_agent(state)
            state = run_manager_agent(state)
            route = route_after_manager(state)
            if route == "publish":
                return run_publisher_agent(state)
            if route == "revise":
                state = run_content_agent(state)
                continue
            return state


def build_workflow():
    if StateGraph is None:
        return SimpleRunner()

    workflow = StateGraph(AgentState)
    workflow.add_node("crawler", run_crawler_agent)
    workflow.add_node("text_insight", run_text_insight_agent)
    workflow.add_node("trend_analysis", run_trend_agent)
    workflow.add_node("visual_insight", run_visual_insight_agent)
    workflow.add_node("video_insight", run_video_insight_agent)
    workflow.add_node("strategy", run_strategy_agent)
    workflow.add_node("content_creator", run_content_agent)
    workflow.add_node("compliance", run_compliance_agent)
    workflow.add_node("hardness", run_hardness_agent)
    workflow.add_node("manager_review", run_manager_agent)
    workflow.add_node("publisher", run_publisher_agent)
    workflow.set_entry_point("crawler")
    workflow.add_edge("crawler", "text_insight")
    workflow.add_edge("text_insight", "trend_analysis")
    workflow.add_edge("trend_analysis", "visual_insight")
    workflow.add_edge("visual_insight", "video_insight")
    workflow.add_edge("video_insight", "strategy")
    workflow.add_edge("strategy", "content_creator")
    workflow.add_edge("content_creator", "compliance")
    workflow.add_edge("compliance", "hardness")
    workflow.add_edge("hardness", "manager_review")
    workflow.add_conditional_edges(
        "manager_review",
        route_after_manager,
        {"publish": "publisher", "revise": "content_creator", "end": END},
    )
    workflow.add_edge("publisher", END)
    return workflow.compile()
