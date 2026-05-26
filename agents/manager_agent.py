from graph.state import AgentState, ContentVariant, DraftContent
from tools.compliance import compliance_flags
from utils.logger import get_logger


logger = get_logger(__name__)


CMO_SYSTEM_PROMPT = """
Bạn là CMO chuyên nghiệp về marketing nha khoa cho SmileUp Dental Clinic.
Bạn có 10+ năm kinh nghiệm tăng trưởng lead nha khoa tại Việt Nam, đặc biệt ở răng sứ thẩm mỹ,
phục hình răng sứ và cấy ghép implant.

Nhiệm vụ của bạn không phải chỉ duyệt cuối. Bạn điều phối toàn bộ multi-agent workflow:
- Đọc dữ liệu crawler, text insight, trend, visual, video, strategy, content và compliance.
- Chọn chiến dịch có khả năng tạo lịch tư vấn tốt nhất cho SmileUp.
- Ưu tiên khác biệt thương hiệu: tư vấn cá nhân hóa, minh bạch chỉ định, an toàn y khoa.
- Chặn claim rủi ro y tế, không cho publish khi nội dung hứa hẹn quá mức.
- Chọn bài viết và creative tốt nhất trước khi Publisher được phép đăng.
- Nếu output chưa đủ sức marketing hoặc chưa an toàn, yêu cầu agent content sửa lại.

Luôn nghĩ như CMO: mục tiêu kinh doanh trước, khách hàng thật trước, compliance trước khi publish.
""".strip()


def run_manager_agent(state: AgentState) -> AgentState:
    logger.info("CMO Agent orchestrating final decision")
    _ensure_cmo_defaults(state)
    variants = state.get("content_plan", [])
    assets = state.get("creative_assets", [])

    if not variants and not state.get("draft_content"):
        _set_cmo_decision(
            state,
            status="rejected",
            next_action="stop",
            decision="STOP",
            feedback="CMO chặn luồng: chưa có bản nháp hoặc campaign variant để đánh giá.",
        )
        _finish_report(state)
        return state

    scorecard = _score_variants(state, variants)
    state["cmo_scorecard"] = scorecard
    selected_variant_index = _best_variant_index(scorecard)
    if selected_variant_index >= 0 and selected_variant_index < len(variants):
        selected_variant = variants[selected_variant_index]
        state["draft_content"] = _draft_from_variant(selected_variant)
    else:
        selected_variant = None

    selected_creative_index = _select_creative_index(assets, selected_variant_index)
    state["cmo_selected_variant_index"] = selected_variant_index
    state["cmo_selected_creative_index"] = selected_creative_index
    state["cmo_campaign_brief"] = _campaign_brief(state, selected_variant, selected_creative_index)

    draft = state.get("draft_content")
    if not draft:
        _set_cmo_decision(
            state,
            status="rejected",
            next_action="stop",
            decision="STOP",
            feedback="CMO chặn publish: không có draft_content sau khi chọn variant.",
        )
    else:
        _decide_from_draft(state, draft, scorecard, selected_variant_index, selected_creative_index)

    _finish_report(state)
    return state


def _ensure_cmo_defaults(state: AgentState) -> None:
    state.setdefault(
        "cmo_objective",
        "CMO nha khoa SmileUp: tăng lịch tư vấn răng sứ và implant bằng nội dung khác biệt, an toàn y khoa.",
    )
    state.setdefault("cmo_decision", "")
    state.setdefault("cmo_feedback", "")
    state.setdefault("cmo_next_action", "continue")
    state.setdefault("cmo_selected_variant_index", -1)
    state.setdefault("cmo_selected_creative_index", -1)
    state.setdefault("cmo_scorecard", [])
    state.setdefault("cmo_campaign_brief", "")


def _score_variants(state: AgentState, variants: list[ContentVariant]) -> list[dict]:
    scorecard: list[dict] = []
    for index, variant in enumerate(variants):
        title = variant.get("title", "")
        body = variant.get("body", "")
        service_line = variant.get("service_line", "")
        flags = compliance_flags(variant)
        word_count = len(body.split())

        score = 45
        if service_line in {"implant", "rang_su"}:
            score += 16
        if "implant" in (title + " " + body).lower() or "răng sứ" in (title + " " + body).lower() or "rang su" in (title + " " + body).lower():
            score += 12
        if variant.get("differentiation"):
            score += 10
        if variant.get("trend_angle"):
            score += 8
        if variant.get("call_to_action"):
            score += 8
        if 110 <= word_count <= 260:
            score += 10
        elif word_count < 90:
            score -= 14
        if flags:
            score -= 35
        if state.get("facebook_trend_analysis"):
            score += 4
        if state.get("visual_creative_brief"):
            score += 3

        scorecard.append(
            {
                "index": index,
                "service_line": service_line or "post",
                "title": title,
                "score": max(0, min(100, score)),
                "word_count": word_count,
                "flags": flags,
                "decision_note": _score_note(score, flags, word_count, variant),
            }
        )
    return scorecard


def _score_note(score: int, flags: list[str], word_count: int, variant: ContentVariant) -> str:
    if flags:
        return "Có claim/compliance rủi ro, cần sửa trước khi publish."
    if word_count < 90:
        return "Caption còn mỏng, cần thêm insight, trust proof và lý do inbox."
    if variant.get("service_line") in {"implant", "rang_su"}:
        return "Phù hợp trọng tâm kinh doanh SmileUp: răng sứ/implant."
    if score >= 75:
        return "Đủ tốt để CMO cân nhắc publish."
    return "Có thể dùng làm biến thể phụ nhưng chưa phải lựa chọn chính."


def _best_variant_index(scorecard: list[dict]) -> int:
    if not scorecard:
        return -1
    return int(max(scorecard, key=lambda item: item.get("score", 0)).get("index", -1))


def _select_creative_index(assets: list[dict], selected_variant_index: int) -> int:
    if not assets:
        return -1
    if 0 <= selected_variant_index < len(assets):
        return selected_variant_index
    return 0


def _decide_from_draft(
    state: AgentState,
    draft: DraftContent,
    scorecard: list[dict],
    selected_variant_index: int,
    selected_creative_index: int,
) -> None:
    flags = compliance_flags(draft)
    selected_score = 0
    if 0 <= selected_variant_index < len(scorecard):
        selected_score = int(scorecard[selected_variant_index].get("score", 0))
        flags.extend(scorecard[selected_variant_index].get("flags", []))

    word_count = len(draft.get("body", "").split())
    if flags:
        _set_cmo_decision(
            state,
            status="needs_revision" if state.get("revision_count", 0) < 3 else "rejected",
            next_action="revise" if state.get("revision_count", 0) < 3 else "stop",
            decision="REVISE",
            feedback="CMO yêu cầu sửa claim rủi ro trước khi publish: " + ", ".join(sorted(set(flags))),
        )
    elif word_count < 110:
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE",
            feedback="CMO yêu cầu viết dày hơn: cần thêm insight khách hàng, trust proof và lưu ý thăm khám.",
        )
    elif not draft.get("call_to_action"):
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE",
            feedback="CMO yêu cầu bổ sung CTA đặt lịch/inbox rõ ràng.",
        )
    elif selected_score < 62:
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE",
            feedback="CMO đánh giá variant tốt nhất vẫn chưa đủ khác biệt hoặc chưa đủ lực chuyển đổi.",
        )
    else:
        creative_text = "có creative đi kèm" if selected_creative_index >= 0 else "chưa có creative, vẫn có thể dùng caption"
        _set_cmo_decision(
            state,
            status="approved",
            next_action="publish",
            decision="APPROVE",
            feedback=f"CMO duyệt publish: chọn variant #{selected_variant_index + 1}, {creative_text}, CTA an toàn và đúng trọng tâm SmileUp.",
        )


def _set_cmo_decision(
    state: AgentState,
    *,
    status: str,
    next_action: str,
    decision: str,
    feedback: str,
) -> None:
    state["approval_status"] = status
    state["cmo_next_action"] = next_action
    state["cmo_decision"] = decision
    state["cmo_feedback"] = feedback
    state["manager_feedback"] = feedback


def _draft_from_variant(variant: ContentVariant) -> DraftContent:
    return {
        "marketing_analysis": variant.get("marketing_analysis", ""),
        "trend_angle": variant.get("trend_angle", ""),
        "post_structure": variant.get("post_structure", ""),
        "title": variant.get("title", ""),
        "body": variant.get("body", ""),
        "hashtags": variant.get("hashtags", []),
        "call_to_action": variant.get("call_to_action", ""),
        "image_prompt": variant.get("image_prompt", "") or None,
    }


def _campaign_brief(state: AgentState, selected_variant: ContentVariant | None, selected_creative_index: int) -> str:
    if not selected_variant:
        return "CMO chưa chọn được campaign variant."
    return (
        f"Mục tiêu: {state.get('cmo_objective', '')}\n"
        f"Trụ cột được chọn: {selected_variant.get('service_line', 'post')}.\n"
        f"Góc triển khai: {selected_variant.get('angle', '')}\n"
        f"Điểm khác biệt SmileUp: {selected_variant.get('differentiation', '')}\n"
        f"Creative được chọn: #{selected_creative_index + 1 if selected_creative_index >= 0 else 'chưa có'}.\n"
        "Guardrail: không claim tuyệt đối, không rebrand tài sản đối thủ, CTA phải hướng về tư vấn/thăm khám."
    )


def _finish_report(state: AgentState) -> None:
    state["daily_strategy"] = _daily_strategy(state)
    state["daily_report"] = _daily_report(state)
    state["current_step"] = "manager_review"
    state["messages"].append(
        {
            "role": "cmo",
            "content": f"{state.get('cmo_decision', '')}: {state.get('cmo_feedback', '')}",
        }
    )


def _daily_strategy(state: AgentState) -> str:
    return (
        f"{CMO_SYSTEM_PROMPT}\n\n"
        f"CMO objective: {state.get('cmo_objective', '')}\n"
        f"CMO decision: {state.get('cmo_decision', '')} -> {state.get('cmo_next_action', '')}\n"
        f"CMO selected variant: #{state.get('cmo_selected_variant_index', -1) + 1 if state.get('cmo_selected_variant_index', -1) >= 0 else 'none'}\n"
        f"CMO selected creative: #{state.get('cmo_selected_creative_index', -1) + 1 if state.get('cmo_selected_creative_index', -1) >= 0 else 'none'}\n"
        f"CMO feedback: {state.get('cmo_feedback', '')}\n\n"
        f"{state.get('cmo_campaign_brief', '')}\n\n"
        "Thông điệp chủ đạo: SmileUp khác biệt bằng tư vấn cá nhân hóa, minh bạch chỉ định và an toàn y khoa.\n"
        "Dịch vụ trọng tâm: răng sứ thẩm mỹ, phục hình răng sứ, cấy ghép implant.\n"
        f"Insight thị trường: {state.get('market_trend_summary', '')}\n"
        f"{state.get('ad_library_report', '')}\n"
        f"{state.get('facebook_trend_analysis', '')}\n"
        f"{state.get('strategic_direction', '')}\n"
        f"{state.get('compliance_report', '')}\n"
        f"{_content_plan_summary(state)}\n"
        f"{_creative_asset_summary(state)}\n"
        "3-5 hành động hôm nay:\n"
        "- Đăng/lên lịch variant được CMO chọn trước, các variant còn lại dùng làm backup A/B test.\n"
        "- Ghim CTA inbox/hotline và kịch bản hỏi nhanh: tình trạng răng, mong muốn, thời gian rảnh để thăm khám.\n"
        "- Dùng creative gốc có logo SmileUp; không dùng ảnh/nhận diện của đối thủ.\n"
        "- Theo dõi comment trong 2 giờ đầu sau đăng và chuyển lead nóng sang inbox.\n"
        "Rủi ro cần tránh: claim tuyệt đối, before/after thiếu consent, rebrand ảnh đối thủ."
    )


def _daily_report(state: AgentState) -> str:
    insights = state.get("competitor_insights", [])
    status = state.get("approval_status", "pending")
    return (
        f"Tổng quan insight đối thủ: đã phân tích {len(insights)} nguồn, ưu tiên răng sứ, implant, ưu đãi, tư vấn và CTA.\n"
        f"CMO status: {status}.\n"
        f"CMO decision: {state.get('cmo_decision', '')} -> {state.get('cmo_next_action', '')}\n"
        f"CMO feedback: {state.get('cmo_feedback', '')}\n"
        f"CMO brief: {state.get('cmo_campaign_brief', '').replace(chr(10), ' ')}\n"
        f"Ad Library: {state.get('ad_library_report', '').replace(chr(10), ' ')}\n"
        f"Trend Facebook: {state.get('facebook_trend_analysis', '').replace(chr(10), ' ')}\n"
        f"Visual brief: {state.get('visual_creative_brief', '').replace(chr(10), ' ')}\n"
        f"Agent strategy: {state.get('strategic_direction', '').replace(chr(10), ' ')}\n"
        f"Compliance: {state.get('compliance_report', '').replace(chr(10), ' ')}\n"
        f"Content variants: {_content_plan_summary(state).replace(chr(10), ' ')}\n"
        f"Creative assets: {_creative_asset_summary(state).replace(chr(10), ' ')}\n"
        "Checklist compliance: không claim tuyệt đối, CTA là đặt lịch tư vấn, có lưu ý kết quả tùy tình trạng răng.\n"
        "Khuyến nghị ngày mai: so sánh hiệu quả bài răng sứ với bài implant, ưu tiên hook có vấn đề cụ thể và visual gốc của SmileUp."
    )


def _content_plan_summary(state: AgentState) -> str:
    variants = state.get("content_plan", [])
    if not variants:
        return "Content plan: chưa có biến thể bài viết."
    lines = ["Content plan CMO:"]
    selected = state.get("cmo_selected_variant_index", -1)
    for index, variant in enumerate(variants, start=1):
        marker = " [CMO PICK]" if index - 1 == selected else ""
        lines.append(
            f"- {index}. {variant.get('service_line', 'post')}{marker}: {variant.get('title', '')} | Khác biệt: {variant.get('differentiation', '')}"
        )
    return "\n".join(lines)


def _creative_asset_summary(state: AgentState) -> str:
    assets = state.get("creative_assets", [])
    if not assets:
        return "Creative assets: chưa sinh ảnh branded."
    selected = state.get("cmo_selected_creative_index", -1)
    lines = ["Creative assets SmileUp:"]
    for index, asset in enumerate(assets, start=1):
        marker = " [CMO PICK]" if index - 1 == selected else ""
        lines.append(f"- {index}. {asset.get('service_line', 'post')}{marker}: {asset.get('image_path', '')}")
    return "\n".join(lines)
