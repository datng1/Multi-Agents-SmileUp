from graph.state import AgentState
from tools.compliance import build_compliance_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_compliance_agent(state: AgentState) -> AgentState:
    logger.info("Compliance Agent checking dental marketing claims")
    state["compliance_report"] = build_compliance_report(state.get("draft_content"))
    state["current_step"] = "compliance"
    state["messages"].append({"role": "compliance", "content": "Checked dental claims and safety requirements"})
    return state
