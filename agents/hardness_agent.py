from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from utils.logger import get_logger


logger = get_logger(__name__)


def run_hardness_agent(state: AgentState) -> AgentState:
    logger.info("Hardness Agent evaluating evidence readiness for media production")
    focus_keyword = state.get("ad_library_keywords", "")
    missing: list[str] = []
    recommendations: list[str] = []
    penalties = 0

    ad_count = len(state.get("ad_library_ads", []))
    high_match_count = len(state.get("high_match_ads", []))
    if ad_count < 20:
        missing.append(f"Thiếu ads tham chiếu: cần 20, hiện có {ad_count}.")
        recommendations.append("crawler")
        penalties += 30
    if high_match_count < 5:
        missing.append(f"Tín hiệu high-match còn mỏng: hiện có {high_match_count} ads.")
        recommendations.append("crawler")
        penalties += 10

    report_checks = [
        ("text_insight_report", "Thiếu text insight.", "text_insight"),
        ("facebook_trend_analysis", "Thiếu trend analysis.", "trend_analysis"),
        ("visual_insight_report", "Thiếu visual analysis.", "visual_insight"),
        ("video_insight_report", "Thiếu video analysis.", "video_insight"),
        ("strategic_direction", "Thiếu strategic direction.", "strategy"),
        ("compliance_report", "Thiếu production compliance guardrails.", "compliance"),
    ]
    for field, message, agent in report_checks:
        if not str(state.get(field, "")).strip():
            missing.append(message)
            recommendations.append(agent)
            penalties += 10

    score = max(0, min(100, 100 - penalties))
    risk_level = "low" if score >= 80 else "medium" if score >= 60 else "high"
    readiness = "ready" if score >= 80 else "review" if score >= 60 else "blocked"
    recommendations = _unique(recommendations)

    state["hardness_score"] = score
    state["hardness_risk_level"] = risk_level
    state["hardness_missing_evidence"] = missing
    state["hardness_recommended_next_agents"] = recommendations
    state["hardness_production_readiness"] = readiness
    fallback_report = _report(score, risk_level, readiness, missing, recommendations)
    report, provider = reason_with_agent_api(
        agent_name="Hardness Agent",
        role="Đánh giá độ chắc dữ liệu trước khi CMO giao workflow sản xuất media.",
        task=(
            "Kiểm tra evidence coverage, source quality và specialist reports. Chỉ kết luận production readiness; "
            "không đánh giá caption, creative cuối hoặc publish readiness."
        ),
        context={
            "focus_keyword": focus_keyword,
            "score": score,
            "risk_level": risk_level,
            "production_readiness": readiness,
            "missing_evidence": missing,
            "recommended_next_agents": recommendations,
            "ad_library_report": state.get("ad_library_report", ""),
            "strategic_direction": state.get("strategic_direction", ""),
        },
        fallback=fallback_report,
    )
    state["hardness_report"] = f"Focus keyword: {focus_keyword}\n{report}".strip()
    state["current_step"] = "hardness"
    state["messages"].append({"role": "hardness", "content": f"{provider}: production readiness {readiness} ({score}/100)"})
    return state


def _report(score: int, risk_level: str, readiness: str, missing: list[str], recommendations: list[str]) -> str:
    missing_text = "\n".join(f"- {item}" for item in missing) if missing else "- Không thiếu bằng chứng lớn."
    next_agents = ", ".join(recommendations) if recommendations else "Không cần chạy lại agent."
    return (
        f"Evidence readiness: {score}/100\n"
        f"Risk level: {risk_level}\n"
        f"Production readiness: {readiness}\n"
        f"Missing evidence:\n{missing_text}\n"
        f"Recommended next agents: {next_agents}"
    )


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
