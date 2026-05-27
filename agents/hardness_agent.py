from graph.state import AgentState
from tools.compliance import compliance_flags
from utils.logger import get_logger


logger = get_logger(__name__)


def run_hardness_agent(state: AgentState) -> AgentState:
    logger.info("Hardness Agent evaluating publish readiness and evidence depth")
    missing: list[str] = []
    recommendations: list[str] = []
    penalties = 0

    insights = state.get("competitor_insights", [])
    ad_count = len(state.get("ad_library_ads", []))
    variants = state.get("content_plan", [])
    assets = state.get("creative_assets", [])
    draft = state.get("draft_content")
    text_only_mode = state.get("creative_image_mode") == "text_only"

    if len(insights) < 3 and ad_count < 3:
        missing.append("Thiếu dữ liệu đối thủ đủ rộng để kết luận trend.")
        recommendations.append("crawler")
        penalties += 22
    if not state.get("facebook_trend_analysis"):
        missing.append("Thiếu phân tích trend Facebook.")
        recommendations.append("trend_analysis")
        penalties += 12
    if not text_only_mode and not state.get("visual_creative_brief") and not state.get("competitor_visual_notes"):
        missing.append("Thiếu tín hiệu visual/creative để định hướng ảnh.")
        recommendations.append("visual_insight")
        penalties += 10
    if not variants:
        missing.append("Chưa có campaign variants để CMO chọn.")
        recommendations.append("content_creator")
        penalties += 26
    if not assets and not text_only_mode:
        missing.append("Chưa có creative assets đi kèm bài đăng.")
        recommendations.append("content_creator")
        penalties += 8
    if not draft:
        missing.append("Chưa có draft cuối để đánh giá.")
        recommendations.append("content_creator")
        penalties += 24
    else:
        word_count = len(draft.get("body", "").split())
        if word_count < 110:
            missing.append("Caption còn mỏng, chưa đủ insight/trust proof.")
            recommendations.append("content_creator")
            penalties += 16
        if not draft.get("call_to_action"):
            missing.append("Thiếu CTA đặt lịch/inbox rõ ràng.")
            recommendations.append("content_creator")
            penalties += 14
        flags = compliance_flags(draft)
        if flags:
            missing.extend(f"Compliance risk: {flag}" for flag in flags)
            recommendations.append("compliance")
            penalties += 32

    if state.get("creative_image_mode") == "layout_reference" and state.get("creative_upload_url"):
        penalties += 4
        missing.append("Ảnh upload đang ở chế độ layout reference; chỉ dùng form, không dùng pixel gốc.")

    score = max(0, min(100, 100 - penalties))
    risk_level = _risk_level(score)
    readiness = _publish_readiness(score, missing)
    recommendations = _unique(recommendations)

    state["hardness_score"] = score
    state["hardness_risk_level"] = risk_level
    state["hardness_missing_evidence"] = missing
    state["hardness_recommended_next_agents"] = recommendations
    state["hardness_publish_readiness"] = readiness
    state["hardness_report"] = _report(score, risk_level, readiness, missing, recommendations)
    state["current_step"] = "hardness"
    state["messages"].append({"role": "hardness", "content": state["hardness_report"]})
    return state


def _risk_level(score: int) -> str:
    if score >= 82:
        return "low"
    if score >= 62:
        return "medium"
    return "high"


def _publish_readiness(score: int, missing: list[str]) -> str:
    if any(item.startswith("Compliance risk") for item in missing):
        return "block"
    if score >= 82:
        return "ready"
    if score >= 62:
        return "revise"
    return "block"


def _report(score: int, risk_level: str, readiness: str, missing: list[str], recommendations: list[str]) -> str:
    missing_text = "\n".join(f"- {item}" for item in missing) if missing else "- Không thiếu bằng chứng lớn."
    next_agents = ", ".join(recommendations) if recommendations else "Không cần chạy lại agent."
    return (
        f"Hardness score: {score}/100\n"
        f"Risk level: {risk_level}\n"
        f"Publish readiness: {readiness}\n"
        "Missing evidence / risks:\n"
        f"{missing_text}\n"
        f"Recommended next agents: {next_agents}"
    )


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
