from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict


def add_messages(left: list[Any], right: list[Any]) -> list[Any]:
    existing = left or []
    incoming = right or []
    if len(incoming) >= len(existing) and incoming[: len(existing)] == existing:
        return incoming
    return existing + incoming


ApprovalStatus = Literal["pending", "approved", "needs_revision", "blocked"]
CMONextAction = Literal["continue", "dispatch", "rescan", "stop"]
CurrentStep = Literal[
    "start",
    "crawler",
    "text_insight",
    "trend_analysis",
    "visual_insight",
    "video_insight",
    "strategy",
    "compliance",
    "hardness",
    "manager_review",
    "end",
    "error",
]


class CompetitorInsight(TypedDict):
    page_name: str
    post_content: str
    engagement: int
    summary: str
    key_topics: list[str]


class ProductionTask(TypedDict, total=False):
    id: str
    stage: str
    title: str
    owner_role: str
    objective: str
    inputs: list[str]
    deliverables: list[str]
    dependencies: list[str]
    acceptance_criteria: list[str]
    priority: str
    status: str
    estimated_duration: str


class ApprovalGate(TypedDict, total=False):
    id: str
    after_task: str
    approver_role: str
    checks: list[str]
    failure_action: str


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
    ad_library_scanned_at: str
    ad_library_scan_id: str
    market_campaign_intelligence: dict[str, Any]
    business_economics: dict[str, float]
    market_trend_summary: str
    facebook_trend_analysis: str
    visual_direction: str
    competitor_visual_notes: str
    competitor_video_notes: str
    text_insight_report: str
    visual_insight_report: str
    video_insight_report: str
    strategic_direction: str
    weekly_strategy: str
    monthly_strategy: str
    compliance_report: str
    production_guardrails: list[str]
    hardness_score: int
    hardness_risk_level: str
    hardness_missing_evidence: list[str]
    hardness_recommended_next_agents: list[str]
    hardness_production_readiness: str
    hardness_report: str
    cmo_objective: str
    cmo_decision: str
    cmo_feedback: str
    cmo_next_action: CMONextAction
    cmo_campaign_brief: str
    cmo_decision_graph: dict[str, Any]
    cmo_graph_summary: str
    approval_status: ApprovalStatus
    manager_feedback: str
    media_production_brief: str
    media_production_workflow: dict[str, Any]
    production_handoff: str
    daily_strategy: str
    daily_report: str
    messages: Annotated[list[Any], add_messages]
    current_step: CurrentStep
    error: str | None
    data_source: str
    run_seed: str
    production_focus_profile: dict[str, str]


def create_initial_state() -> AgentState:
    return {
        "competitor_insights": [],
        "ad_library_ads": [],
        "high_match_ads": [],
        "high_match_threshold": 0.95,
        "ad_library_report": "",
        "ad_library_keywords": "",
        "ad_library_max_ads": 100,
        "ad_library_reference_scan_limit": 20,
        "ad_library_scan_mode": "auto",
        "ad_library_competitor_urls": [],
        "ad_library_competitor_ratio": 0.8,
        "ad_library_scanned_at": "",
        "ad_library_scan_id": "",
        "market_campaign_intelligence": {},
        "business_economics": {},
        "market_trend_summary": "",
        "facebook_trend_analysis": "",
        "visual_direction": "",
        "competitor_visual_notes": "",
        "competitor_video_notes": "",
        "text_insight_report": "",
        "visual_insight_report": "",
        "video_insight_report": "",
        "strategic_direction": "",
        "weekly_strategy": "",
        "monthly_strategy": "",
        "compliance_report": "",
        "production_guardrails": [],
        "hardness_score": 0,
        "hardness_risk_level": "unknown",
        "hardness_missing_evidence": [],
        "hardness_recommended_next_agents": [],
        "hardness_production_readiness": "unknown",
        "hardness_report": "",
        "cmo_objective": (
            "Phân tích tín hiệu Meta mới nhất, xây chiến dịch media 1 tháng chia 4 tuần, "
            "đề xuất brand lane SmileUp và giao việc cho ba vai trò media."
        ),
        "cmo_decision": "",
        "cmo_feedback": "",
        "cmo_next_action": "continue",
        "cmo_campaign_brief": "",
        "cmo_decision_graph": {"nodes": [], "edges": [], "selected_path": []},
        "cmo_graph_summary": "",
        "approval_status": "pending",
        "manager_feedback": "",
        "media_production_brief": "",
        "media_production_workflow": {
            "workflow_id": "",
            "status": "pending",
            "tasks": [],
            "approval_gates": [],
            "metrics": [],
            "risks": [],
        },
        "production_handoff": "",
        "daily_strategy": "",
        "daily_report": "",
        "messages": [],
        "current_step": "start",
        "error": None,
        "data_source": "auto",
        "run_seed": "",
        "production_focus_profile": {},
    }
