from agents.content_agent import run_content_agent
from agents.crawler_agent import run_crawler_agent
from agents.manager_agent import run_manager_agent
from agents.publisher_agent import run_publisher_agent
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
        state = run_content_agent(state)

        while True:
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
    workflow.add_node("content_creator", run_content_agent)
    workflow.add_node("manager_review", run_manager_agent)
    workflow.add_node("publisher", run_publisher_agent)
    workflow.set_entry_point("crawler")
    workflow.add_edge("crawler", "content_creator")
    workflow.add_edge("content_creator", "manager_review")
    workflow.add_conditional_edges(
        "manager_review",
        route_after_manager,
        {"publish": "publisher", "revise": "content_creator", "end": END},
    )
    workflow.add_edge("publisher", END)
    return workflow.compile()
