from typing import Annotated, Any, Literal, Optional, TypedDict

def add_messages(left: list[Any], right: list[Any]) -> list[Any]:
    existing = left or []
    incoming = right or []
    if len(incoming) >= len(existing) and incoming[: len(existing)] == existing:
        return incoming
    return existing + incoming


ApprovalStatus = Literal["pending", "approved", "rejected", "needs_revision"]
CMONextAction = Literal["continue", "revise", "publish", "stop", "rescan"]
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
    "hardness",
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
    campaign_track: str
    monthly_role: str
    source_ads_count: int
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
    high_match_ads: list[dict[str, Any]]
    high_match_threshold: float
    ad_library_report: str
    ad_library_keywords: str
    ad_library_max_ads: int
    ad_library_reference_scan_limit: int
    ad_library_scan_mode: str
    ad_library_competitor_urls: list[str]
    ad_library_competitor_ratio: float
    market_trend_summary: str
    facebook_trend_analysis: str
    visual_creative_brief: str
    competitor_visual_notes: str
    competitor_video_notes: str
    text_insight_report: str
    visual_insight_report: str
    video_insight_report: str
    strategic_direction: str
    monthly_strategy: str
    compliance_report: str
    hardness_score: int
    hardness_risk_level: str
    hardness_missing_evidence: list[str]
    hardness_recommended_next_agents: list[str]
    hardness_publish_readiness: str
    hardness_report: str
    draft_content: Optional[DraftContent]
    content_plan: list[ContentVariant]
    creative_assets: list[dict[str, Any]]
    creative_image_mode: str
    creative_upload_path: str
    creative_upload_url: str
    creative_reference_note: str
    creative_reference_ad: dict[str, Any]
    creative_reference_blueprint: str
    cmo_objective: str
    cmo_decision: str
    cmo_feedback: str
    cmo_next_action: CMONextAction
    cmo_selected_variant_index: int
    cmo_selected_creative_index: int
    cmo_scorecard: list[dict[str, Any]]
    cmo_campaign_brief: str
    cmo_model_votes: list[dict[str, Any]]
    cmo_jury_summary: str
    cmo_decision_graph: dict[str, Any]
    cmo_graph_summary: str
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
    run_seed: str
    creative_variation_profile: dict[str, str]


def create_initial_state() -> AgentState:
    return {
        "competitor_insights": [],
        "ad_library_ads": [],
        "high_match_ads": [],
        "high_match_threshold": 0.95,
        "ad_library_report": "",
        "ad_library_keywords": "",
        "ad_library_max_ads": 15,
        "ad_library_reference_scan_limit": 15,
        "ad_library_scan_mode": "deep",
        "ad_library_competitor_urls": [],
        "ad_library_competitor_ratio": 0.8,
        "market_trend_summary": "",
        "facebook_trend_analysis": "",
        "visual_creative_brief": "",
        "competitor_visual_notes": "",
        "competitor_video_notes": "",
        "text_insight_report": "",
        "visual_insight_report": "",
        "video_insight_report": "",
        "strategic_direction": "",
        "monthly_strategy": "",
        "compliance_report": "",
        "hardness_score": 0,
        "hardness_risk_level": "unknown",
        "hardness_missing_evidence": [],
        "hardness_recommended_next_agents": [],
        "hardness_publish_readiness": "unknown",
        "hardness_report": "",
        "draft_content": None,
        "content_plan": [],
        "creative_assets": [],
        "creative_image_mode": "upload_only",
        "creative_upload_path": "",
        "creative_upload_url": "",
        "creative_reference_note": "",
        "creative_reference_ad": {},
        "creative_reference_blueprint": "",
        "cmo_objective": "CMO SmileUp: lập chiến lược tháng, tách tuyến ads lấy SĐT và tuyến chăm sóc page, ưu tiên răng sứ, phục hình sứ và implant.",
        "cmo_decision": "",
        "cmo_feedback": "",
        "cmo_next_action": "continue",
        "cmo_selected_variant_index": -1,
        "cmo_selected_creative_index": -1,
        "cmo_scorecard": [],
        "cmo_campaign_brief": "",
        "cmo_model_votes": [],
        "cmo_jury_summary": "",
        "cmo_decision_graph": {"nodes": [], "edges": [], "selected_path": []},
        "cmo_graph_summary": "",
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
        "run_seed": "",
        "creative_variation_profile": {},
    }
