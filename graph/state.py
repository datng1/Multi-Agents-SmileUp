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
    "text_insight",
    "trend_analysis",
    "visual_insight",
    "video_insight",
    "strategy",
    "content_creator",
    "compliance",
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
    marketing_analysis: str
    trend_angle: str
    post_structure: str
    title: str
    body: str
    hashtags: list[str]
    call_to_action: str
    image_prompt: Optional[str]


class ContentVariant(TypedDict, total=False):
    service_line: str
    angle: str
    differentiation: str
    marketing_analysis: str
    trend_angle: str
    post_structure: str
    title: str
    body: str
    hashtags: list[str]
    call_to_action: str
    image_prompt: str
    image_path: str


class AgentState(TypedDict):
    competitor_insights: list[CompetitorInsight]
    ad_library_ads: list[dict[str, Any]]
    ad_library_report: str
    ad_library_keywords: str
    market_trend_summary: str
    facebook_trend_analysis: str
    visual_creative_brief: str
    competitor_visual_notes: str
    competitor_video_notes: str
    text_insight_report: str
    visual_insight_report: str
    video_insight_report: str
    strategic_direction: str
    compliance_report: str
    draft_content: Optional[DraftContent]
    content_plan: list[ContentVariant]
    creative_assets: list[dict[str, Any]]
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
        "ad_library_ads": [],
        "ad_library_report": "",
        "ad_library_keywords": "",
        "market_trend_summary": "",
        "facebook_trend_analysis": "",
        "visual_creative_brief": "",
        "competitor_visual_notes": "",
        "competitor_video_notes": "",
        "text_insight_report": "",
        "visual_insight_report": "",
        "video_insight_report": "",
        "strategic_direction": "",
        "compliance_report": "",
        "draft_content": None,
        "content_plan": [],
        "creative_assets": [],
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
