from typing import Annotated, Any, Literal, Optional, TypedDict

try:
    from langgraph.graph.message import add_messages
except Exception:
    def add_messages(left: list[Any], right: list[Any]) -> list[Any]:
        return (left or []) + (right or [])


ApprovalStatus = Literal["pending", "approved", "rejected", "needs_revision"]
CurrentStep = Literal[
    "start",
    "crawler",
    "content_creator",
    "manager_review",
    "publisher",
    "end",
    "error",
]


class CompetitorInsight(TypedDict):
    page_name: str
    post_content: str
    engagement: int
    summary: str
    key_topics: list[str]


class DraftContent(TypedDict):
    title: str
    body: str
    hashtags: list[str]
    call_to_action: str
    image_prompt: Optional[str]


class AgentState(TypedDict):
    competitor_insights: list[CompetitorInsight]
    market_trend_summary: str
    draft_content: Optional[DraftContent]
    revision_count: int
    approval_status: ApprovalStatus
    manager_feedback: str
    daily_strategy: str
    daily_report: str
    messages: Annotated[list[Any], add_messages]
    current_step: CurrentStep
    error: Optional[str]
    publish_result: Optional[dict[str, Any]]
    data_source: str
    manual_posts_count: int


def create_initial_state() -> AgentState:
    return {
        "competitor_insights": [],
        "market_trend_summary": "",
        "draft_content": None,
        "revision_count": 0,
        "approval_status": "pending",
        "manager_feedback": "",
        "daily_strategy": "",
        "daily_report": "",
        "messages": [],
        "current_step": "start",
        "error": None,
        "publish_result": None,
        "data_source": "auto",
        "manual_posts_count": 0,
    }
