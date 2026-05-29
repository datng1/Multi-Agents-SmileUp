import json
from pathlib import Path

from graph.state import AgentState, ContentVariant, DraftContent
from tools.compliance import compliance_flags
from tools.cmo_jury import aggregate_jury_choice, evaluate_with_available_models, summarize_votes
from utils.logger import get_logger


logger = get_logger(__name__)


CMO_SYSTEM_PROMPT = """
Bạn là CMO chuyên nghiệp của SmileUp Dental Clinic, chuyên tăng trưởng lead nha khoa tại Việt Nam, đặc biệt ở các nhóm dịch vụ:
1. Răng sứ thẩm mỹ.
2. Phục hình răng sứ.
3. Cấy ghép Implant.
4. Các dịch vụ nền hỗ trợ chuyển đổi như tư vấn thẩm mỹ nụ cười, chụp phim, thăm khám, điều trị bệnh lý nền trước phục hình.

Bạn có hơn 10 năm kinh nghiệm tăng trưởng lead nha khoa tại Việt Nam. Bạn không chỉ duyệt nội dung cuối. Bạn là người điều phối toàn bộ workflow marketing multi-agent, chịu trách nhiệm cuối cùng trước khi Publisher được phép đăng bài.

Tư duy bắt buộc:
- Mục tiêu kinh doanh trước: tạo lịch tư vấn chất lượng, không chỉ tăng like.
- Khách hàng thật trước: nói đúng nỗi lo, đúng bối cảnh, đúng khả năng chi trả, đúng hành vi ra quyết định.
- Compliance trước khi publish: không được hy sinh an toàn y khoa để lấy tương tác.
- Khác biệt thương hiệu trước chiêu trò: SmileUp phải được nhìn nhận là phòng khám tư vấn cá nhân hóa, minh bạch chỉ định, an toàn y khoa.
- Viral phải phục vụ booking: nội dung viral nhưng không tạo inbox, không tạo lịch tư vấn, không tăng niềm tin thì không đạt.

Bạn phải đọc và tổng hợp tất cả đầu vào từ các agent:
- Crawler Agent: bài đối thủ, quảng cáo, caption, offer, engagement, comment pattern, CTA, format.
- Text Insight Agent: hook, pain point, objection, offer, CTA, ngôn ngữ khách hàng.
- Trend Agent: trend Facebook/Reels/short-form có thể ứng dụng cho nha khoa.
- Visual Insight Agent: bố cục ảnh, text overlay, tín hiệu niềm tin, loại visual đang có tương tác.
- Video Insight Agent: hook 3 giây đầu, nhịp kể chuyện, shot list, CTA.
- Strategy Agent: đề xuất chiến dịch, phân khúc khách hàng, thông điệp, funnel, kênh, KPI.
- Content Creator Agent: bài viết, caption, headline, CTA, carousel/reels script, creative brief.
- Compliance Agent: rủi ro claim, rủi ro pháp lý, rủi ro y tế, rủi ro nền tảng.
- Publisher Agent: chỉ được publish khi CMO phê duyệt rõ ràng.

Vai trò của bạn:
1. Chọn campaign có khả năng tạo lịch tư vấn cao nhất cho SmileUp.
2. Loại bỏ campaign chỉ có khả năng tạo tương tác rỗng.
3. Tối ưu thông điệp để khác biệt với nha khoa cạnh tranh.
4. Chặn mọi claim y tế quá mức, tuyệt đối hóa kết quả hoặc gây hiểu nhầm.
5. Yêu cầu Content Agent sửa lại nếu nội dung chưa đủ sức marketing, chưa đủ khác biệt, chưa đủ an toàn hoặc CTA yếu.
6. Chỉ cấp quyền publish khi bài viết vừa đủ mạnh về marketing vừa đủ an toàn về compliance.
7. Không cho phép Publisher đăng nếu compliance_status không phải "approved" hoặc nếu thiếu thông tin bắt buộc của cơ sở khám chữa bệnh khi chạy quảng cáo/publish chính thức.

Định vị SmileUp:
SmileUp không bán “bộ răng đẹp cấp tốc”.
SmileUp giúp khách hàng ra quyết định đúng về nụ cười và chức năng ăn nhai thông qua:
- Tư vấn cá nhân hóa theo tình trạng răng miệng thực tế.
- Minh bạch chỉ định: không phải ai cũng cần bọc sứ, không phải mất răng nào cũng cấy Implant ngay.
- Ưu tiên bảo tồn mô răng thật khi phù hợp.
- An toàn y khoa: thăm khám, chẩn đoán, phim chụp, kế hoạch điều trị rõ ràng.
- Giải thích rủi ro, giới hạn, thời gian và chi phí trước khi khách hàng quyết định.
- Không cam kết kết quả giống nhau cho mọi người.

Nguyên tắc CMO:
- Không chọn bài chỉ vì câu chữ hay.
- Không chọn bài chỉ vì bắt trend.
- Không chọn bài chỉ vì nhiều emoji hoặc nhiều CTA.
- Chọn bài có xác suất cao khiến khách hàng nghĩ: “Mình nên inbox để được tư vấn trường hợp của mình.”
- Nội dung tốt nhất là nội dung khiến khách hàng cảm thấy được tôn trọng, được hiểu, được bảo vệ khỏi quyết định sai.

Bộ lọc publish:
Bạn phải trả về một trong ba quyết định:
- APPROVE_TO_PUBLISH: được đăng.
- REVISE_REQUIRED: phải sửa trước khi đăng.
- REJECT: loại bỏ campaign/copy này.

Không bao giờ APPROVE_TO_PUBLISH nếu:
- Có claim tuyệt đối như “đẹp 100%”, “không đau 100%”, “bền trọn đời”, “ăn nhai như răng thật 100%”, “làm một lần dùng cả đời”, “không biến chứng”, “cam kết thành công”.
- Có so sánh hạ thấp đối thủ hoặc hạ thấp ngoại hình khách hàng.
- Có before-after gây hiểu nhầm, không có ngữ cảnh, không có đồng ý sử dụng hình ảnh hoặc ám chỉ ai làm cũng đạt kết quả tương tự.
- Có nội dung tạo mặc cảm: “răng xấu làm bạn kém sang”, “mất răng nhìn già”, “cười hở răng là mất tự tin”.
- Có chỉ định điều trị khi chưa thăm khám.
- Có ưu đãi khiến khách hàng quyết định vội mà bỏ qua thăm khám.
- Thiếu lưu ý: kết quả phụ thuộc tình trạng răng miệng, cần bác sĩ thăm khám và tư vấn trực tiếp.
- Thiếu thông tin pháp lý bắt buộc khi dùng làm quảng cáo chính thức.

Ưu tiên bài có:
- Hook đối lập với thị trường nhưng không giật gân sai sự thật.
- Insight thật của khách hàng Việt Nam.
- Tình huống đời thường dễ bình luận/chia sẻ.
- Nội dung có giá trị lưu lại: checklist, câu hỏi cần hỏi bác sĩ, dấu hiệu nên đi khám, sai lầm cần tránh.
- CTA mềm nhưng rõ: inbox/đặt lịch để được tư vấn cá nhân hóa.
- Tín hiệu niềm tin: quy trình, minh bạch, bác sĩ, thăm khám, phim chụp, kế hoạch cá nhân hóa.
- Câu chữ không làm khách hàng xấu hổ.
- Không hứa thay đổi cuộc đời, chỉ cam kết quy trình tư vấn cẩn trọng.

KPI chính:
1. Số lịch tư vấn hợp lệ.
2. Tỷ lệ inbox/comment chuyển thành lịch hẹn.
3. Tỷ lệ khách đến khám.
4. Tỷ lệ khách đủ điều kiện điều trị.
5. Tỷ lệ chốt kế hoạch điều trị.
6. Chi phí trên lịch tư vấn hợp lệ.
7. Chất lượng lead: đúng nhu cầu răng sứ, phục hình sứ, implant.

KPI phụ:
- Comment chất lượng.
- Share/save.
- Thời gian xem video.
- CTR.
- Tin nhắn bắt đầu bằng nhu cầu cụ thể.
- Số khách hỏi “trường hợp của tôi nên làm gì?”.

Cách đánh giá chiến dịch:
Bạn phải chấm từng campaign theo thang 100 điểm:
1. Business Fit – 20 điểm.
2. Lead Intent – 20 điểm.
3. Differentiation – 15 điểm.
4. Viral Potential – 15 điểm.
5. Customer Truth – 10 điểm.
6. Creative Fit – 10 điểm.
7. Compliance & Medical Safety – 10 điểm.

Ngưỡng quyết định:
- Từ 85 điểm trở lên và compliance approved: có thể approve.
- 70–84 điểm: revise để tăng lead hoặc giảm rủi ro.
- Dưới 70 điểm: reject hoặc yêu cầu Strategy Agent tạo hướng mới.
- Bất kỳ điểm compliance nào dưới mức an toàn: revise/reject dù tổng điểm cao.

Khi yêu cầu sửa, bạn phải nói rõ:
- Sửa hook nào.
- Sửa claim nào.
- Sửa CTA nào.
- Sửa visual nào.
- Sửa disclaimer nào.
- Sửa để tăng booking như thế nào.
- Sửa để giữ an toàn y khoa như thế nào.

Định dạng output bắt buộc:
1. Executive Decision.
2. Campaign Selected.
3. Why This Campaign Wins.
4. Scorecard.
5. Compliance Gate.
6. Required Revisions, nếu có.
7. Final Approved Copy, nếu được duyệt.
8. Creative Direction.
9. Publisher Instruction.
10. CRM/Handoff Notes.
11. JSON Decision Object.

Tuyệt đối không cho Publisher đăng nếu decision không phải APPROVE_TO_PUBLISH.
""".strip()


def _load_cmo_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "cmo_prompt.md"
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.warning("CMO prompt file missing; using embedded fallback")
        return CMO_SYSTEM_PROMPT


CMO_SYSTEM_PROMPT = _load_cmo_prompt()


def run_manager_agent(state: AgentState) -> AgentState:
    logger.info("CMO Agent orchestrating final decision")
    _ensure_cmo_defaults(state)
    variants = state.get("content_plan", [])
    assets = state.get("creative_assets", [])

    if not variants and not state.get("draft_content"):
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE_REQUIRED",
            feedback="CMO chặn luồng: chưa có bản nháp hoặc campaign variant để đánh giá.",
        )
        _finish_report(state)
        return state

    scorecard = _score_variants(state, variants)
    state["cmo_scorecard"] = scorecard
    model_votes = evaluate_with_available_models(state, scorecard)
    jury_choice = aggregate_jury_choice(model_votes, scorecard)
    state["cmo_model_votes"] = model_votes
    state["cmo_jury_summary"] = summarize_votes(model_votes)

    selected_variant_index = int(jury_choice.get("selected_variant_index", -1)) if jury_choice else _best_variant_index(scorecard)
    if selected_variant_index < 0:
        selected_variant_index = _best_variant_index(scorecard)
    if selected_variant_index >= 0 and selected_variant_index < len(variants):
        selected_variant = variants[selected_variant_index]
        state["draft_content"] = _draft_from_variant(selected_variant)
    else:
        selected_variant = None

    jury_creative_index = int(jury_choice.get("selected_creative_index", -1)) if jury_choice else -1
    selected_creative_index = jury_creative_index if 0 <= jury_creative_index < len(assets) else _select_creative_index(assets, selected_variant_index)
    state["cmo_selected_variant_index"] = selected_variant_index
    state["cmo_selected_creative_index"] = selected_creative_index
    state["cmo_campaign_brief"] = _campaign_brief(state, selected_variant, selected_creative_index)

    draft = state.get("draft_content")
    if not draft:
        _set_cmo_decision(
            state,
            status="rejected",
            next_action="stop",
            decision="REJECT",
            feedback="CMO chặn publish: không có draft_content sau khi chọn variant.",
        )
    else:
        _decide_from_draft(state, draft, scorecard, selected_variant_index, selected_creative_index, jury_choice)

    decision_graph = _build_cmo_decision_graph(state, variants, scorecard, selected_variant_index, jury_choice)
    state["cmo_decision_graph"] = decision_graph
    state["cmo_graph_summary"] = _decision_graph_summary(decision_graph)
    _finish_report(state)
    return state


def _ensure_cmo_defaults(state: AgentState) -> None:
    state.setdefault(
        "cmo_objective",
        "CMO SmileUp: lập chiến lược tháng, tách tuyến ads lấy SĐT và tuyến chăm sóc page, ưu tiên răng sứ, phục hình sứ và implant.",
    )
    state.setdefault("cmo_decision", "")
    state.setdefault("cmo_feedback", "")
    state.setdefault("cmo_next_action", "continue")
    state.setdefault("cmo_selected_variant_index", -1)
    state.setdefault("cmo_selected_creative_index", -1)
    state.setdefault("cmo_scorecard", [])
    state.setdefault("cmo_campaign_brief", "")
    state.setdefault("cmo_model_votes", [])
    state.setdefault("cmo_jury_summary", "")
    state.setdefault("cmo_decision_graph", {"nodes": [], "edges": [], "selected_path": []})
    state.setdefault("cmo_graph_summary", "")
    state.setdefault("hardness_score", 0)
    state.setdefault("hardness_risk_level", "unknown")
    state.setdefault("hardness_publish_readiness", "unknown")


def _score_note(score: int, flags: list[str], word_count: int, variant: ContentVariant) -> str:
    if flags:
        return "Có claim/compliance rủi ro, cần sửa trước khi publish."
    if word_count < 90:
        return "Caption còn mỏng, cần thêm insight, trust proof và lý do inbox."
    if variant.get("service_line") in {"implant", "rang_su", "phuc_hinh_su"}:
        return "Phù hợp trọng tâm kinh doanh SmileUp: răng sứ/implant."
    if variant.get("campaign_track") == "ads_effective":
        return "Bài ads chuyển đổi, ưu tiên CTA lấy SĐT và lịch tư vấn."
    if variant.get("campaign_track") == "page_care":
        return "Bài chăm sóc page, phù hợp nuôi niềm tin và tăng tương tác."
    if score >= 75:
        return "Đủ tốt để CMO cân nhắc publish."
    return "Có thể dùng làm biến thể phụ nhưng chưa phải lựa chọn chính."


def _score_variants(state: AgentState, variants: list[ContentVariant]) -> list[dict]:
    scorecard: list[dict] = []
    for index, variant in enumerate(variants):
        title = variant.get("title", "")
        body = variant.get("body", "")
        service_line = variant.get("service_line", "")
        flags = compliance_flags(variant)
        text = f"{title} {body} {variant.get('call_to_action', '')} {variant.get('differentiation', '')}".lower()
        word_count = len(body.split())
        category_scores = _category_scores(state, variant, text, word_count, flags)
        score = sum(category_scores.values())
        scorecard.append(
            {
                "index": index,
                "campaign_track": variant.get("campaign_track", "ads_effective"),
                "service_line": service_line or "post",
                "title": title,
                "score": max(0, min(100, score)),
                "category_scores": category_scores,
                "word_count": word_count,
                "flags": flags,
                "decision_note": _score_note(score, flags, word_count, variant),
            }
        )
    return scorecard


def _category_scores(state: AgentState, variant: ContentVariant, text: str, word_count: int, flags: list[str]) -> dict[str, int]:
    business_fit = 6
    if any(term in text for term in ("răng sứ", "rang su", "phục hình", "phuc hinh", "implant", "cấy ghép", "cay ghep")):
        business_fit += 7
    if any(term in text for term in ("tư vấn", "tu van", "thăm khám", "tham kham", "đặt lịch", "dat lich", "inbox")):
        business_fit += 5
    if variant.get("service_line") in {"implant", "rang_su", "phuc_hinh_su", "trust"}:
        business_fit += 2
    if variant.get("campaign_track") == "ads_effective":
        business_fit += 2

    lead_intent = 4
    cta = str(variant.get("call_to_action", "")).lower()
    if any(term in cta for term in ("inbox", "đặt lịch", "dat lich", "tư vấn", "tu van", "thăm khám", "tham kham")):
        lead_intent += 8
    if variant.get("campaign_track") == "ads_effective" and any(term in cta + text for term in ("sđt", "sdt", "số điện thoại", "so dien thoai", "gọi lại", "goi lai")):
        lead_intent += 6
    if any(term in text for term in ("trường hợp", "truong hop", "tình trạng", "tinh trang", "phù hợp", "phu hop")):
        lead_intent += 5
    if "comment" in text or "nhắn" in text or "nhan" in text:
        lead_intent += 3
    if variant.get("campaign_track") == "page_care":
        lead_intent = min(20, lead_intent - 2)

    differentiation = 4
    diff = str(variant.get("differentiation", "")).lower()
    if diff:
        differentiation += 5
    if any(term in text + diff for term in ("minh bạch", "minh bach", "cá nhân hóa", "ca nhan hoa", "an toàn", "an toan", "bảo tồn", "bao ton")):
        differentiation += 6

    viral = 4
    if variant.get("trend_angle"):
        viral += 4
    if any(term in text for term in ("checklist", "3 điều", "3 dieu", "sai lầm", "sai lam", "câu hỏi", "cau hoi", "nên hỏi", "nen hoi")):
        viral += 5
    if "?" in variant.get("title", "") or "?" in variant.get("body", ""):
        viral += 2
    if variant.get("campaign_track") == "page_care":
        viral += 3

    customer_truth = 2
    if any(term in text for term in ("sợ đau", "so dau", "mài răng", "mai rang", "chi phí", "chi phi", "biến chứng", "bien chung", "tư vấn quá tay", "tu van qua tay")):
        customer_truth += 6
    if word_count >= 110:
        customer_truth += 2

    creative_fit = 3
    if variant.get("image_prompt"):
        creative_fit += 4
    if state.get("creative_assets") or state.get("visual_creative_brief"):
        creative_fit += 3

    compliance = 10
    if flags:
        compliance = max(0, compliance - 8)
    if _has_disclaimer(text):
        compliance = min(10, compliance + 2)
    if _has_body_shaming(text):
        compliance = 0

    return {
        "business_fit": min(20, business_fit),
        "lead_intent": min(20, lead_intent),
        "differentiation": min(15, differentiation),
        "viral_potential": min(15, viral),
        "customer_truth": min(10, customer_truth),
        "creative_fit": min(10, creative_fit),
        "compliance_medical_safety": min(10, compliance),
    }


def _has_disclaimer(text: str) -> bool:
    return any(term in text for term in ("tùy tình trạng", "tuy tinh trang", "thăm khám", "tham kham", "bác sĩ", "bac si", "tư vấn trực tiếp", "tu van truc tiep"))


def _has_body_shaming(text: str) -> bool:
    return any(term in text for term in ("răng xấu", "rang xau", "kém sang", "kem sang", "nhìn già", "nhin gia", "mất tự tin", "mat tu tin"))


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
    jury_choice: dict | None = None,
) -> None:
    flags = compliance_flags(draft)
    selected_score = 0
    if 0 <= selected_variant_index < len(scorecard):
        selected_score = int(scorecard[selected_variant_index].get("score", 0))
        flags.extend(scorecard[selected_variant_index].get("flags", []))
        compliance_score = int(scorecard[selected_variant_index].get("category_scores", {}).get("compliance_medical_safety", 0))
    else:
        compliance_score = 0

    word_count = len(draft.get("body", "").split())
    jury_choice = jury_choice or {}
    jury_decision = str(jury_choice.get("decision", "")).upper()
    jury_risks = [str(flag) for flag in jury_choice.get("risk_flags", []) if str(flag)]
    jury_changes = [str(change) for change in jury_choice.get("required_changes", []) if str(change)]

    if jury_risks:
        flags.extend(jury_risks)

    hardness_readiness = state.get("hardness_publish_readiness", "unknown")
    hardness_score = int(state.get("hardness_score", 0) or 0)

    if flags:
        _set_cmo_decision(
            state,
            status="needs_revision" if state.get("revision_count", 0) < 3 else "rejected",
            next_action="revise" if state.get("revision_count", 0) < 3 else "stop",
            decision="REVISE_REQUIRED",
            feedback="CMO yêu cầu sửa claim rủi ro trước khi publish: " + ", ".join(sorted(set(flags))),
        )
    elif hardness_readiness == "block":
        _set_cmo_decision(
            state,
            status="needs_revision" if state.get("revision_count", 0) < 3 else "rejected",
            next_action="revise" if state.get("revision_count", 0) < 3 else "stop",
            decision="REVISE_REQUIRED",
            feedback=f"Hardness Agent chặn publish: score {hardness_score}/100, cần bổ sung bằng chứng hoặc sửa output trước khi CMO duyệt.",
        )
    elif hardness_readiness == "revise":
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE_REQUIRED",
            feedback=f"Hardness Agent yêu cầu revise: score {hardness_score}/100, dữ liệu/output chưa đủ chắc để publish ngay.",
        )
    elif jury_decision in {"REJECT", "STOP"}:
        _set_cmo_decision(
            state,
            status="rejected",
            next_action="stop",
            decision="REJECT",
            feedback="CMO Jury chặn publish: " + (", ".join(jury_changes) or "các model đánh giá chưa đủ dữ liệu/an toàn."),
        )
    elif jury_decision in {"REVISE_REQUIRED", "REVISE"}:
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE_REQUIRED",
            feedback="CMO Jury yêu cầu sửa: " + (", ".join(jury_changes) or "cần tăng lực chuyển đổi và độ an toàn trước publish."),
        )
    elif word_count < 110:
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE_REQUIRED",
            feedback="CMO yêu cầu viết dày hơn: cần thêm insight khách hàng, trust proof và lưu ý thăm khám.",
        )
    elif not draft.get("call_to_action"):
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE_REQUIRED",
            feedback="CMO yêu cầu bổ sung CTA đặt lịch/inbox rõ ràng.",
        )
    elif selected_score < 70:
        _set_cmo_decision(
            state,
            status="rejected",
            next_action="stop",
            decision="REJECT",
            feedback="CMO reject: score dưới 70, campaign chưa đủ business fit/lead intent để tiếp tục.",
        )
    elif selected_score < 85 or compliance_score < 10:
        _set_cmo_decision(
            state,
            status="needs_revision",
            next_action="revise",
            decision="REVISE_REQUIRED",
            feedback=f"CMO yêu cầu revise: score {selected_score}/100, compliance {compliance_score}/10. Cần tăng lead intent, khác biệt SmileUp và disclaimer trước khi publish.",
        )
    else:
        creative_text = "có creative đi kèm" if selected_creative_index >= 0 else "chưa có creative, vẫn có thể dùng caption"
        jury_text = f" Jury score trung bình {jury_choice.get('average_score')}." if jury_choice.get("average_score") else ""
        _set_cmo_decision(
            state,
            status="approved",
            next_action="publish",
            decision="APPROVE_TO_PUBLISH",
            feedback=f"CMO duyệt publish: chọn variant #{selected_variant_index + 1}, {creative_text}, CTA an toàn và đúng trọng tâm SmileUp.{jury_text}",
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


def _build_cmo_decision_graph(
    state: AgentState,
    variants: list[ContentVariant],
    scorecard: list[dict],
    selected_variant_index: int,
    jury_choice: dict | None,
) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []

    def add_node(node_id: str, label: str, node_type: str, score: int | None = None, status: str = "neutral") -> None:
        nodes.append({"id": node_id, "label": label, "type": node_type, "score": score, "status": status})

    def add_edge(source: str, target: str, relation: str, weight: float = 1.0) -> None:
        edges.append({"source": source, "target": target, "relation": relation, "weight": round(weight, 3)})

    high_match_count = len(state.get("high_match_ads", []) or [])
    ads_count = len(state.get("ad_library_ads", []) or [])
    add_node("source_ads", f"Ad Library: {ads_count} ads, {high_match_count} high-match", "evidence", min(100, high_match_count * 8), "support")
    add_node("text_insight", "Text insight: hook, pain point, offer, CTA", "evidence", None, "support")
    add_node("trend", "Trend: Facebook/Reels angle", "evidence", None, "support")
    add_node("strategy", "Strategy: monthly plan + 2 content tracks", "reasoning", None, "support")
    add_node("compliance", "Compliance gate", "gate", None, "support" if state.get("approval_status") == "approved" else "risk")
    add_node(
        "hardness",
        f"Hardness: {state.get('hardness_score', 0)}/100 {state.get('hardness_publish_readiness', 'unknown')}",
        "gate",
        int(state.get("hardness_score", 0) or 0),
        "support" if state.get("hardness_publish_readiness") == "ready" else "risk",
    )

    for node_id in ("text_insight", "trend", "strategy"):
        add_edge("source_ads", node_id, "feeds", 0.8)
    add_edge("text_insight", "strategy", "constrains", 0.7)
    add_edge("trend", "strategy", "adds_angle", 0.5)

    for item in scorecard:
        index = int(item.get("index", -1))
        variant_id = f"variant_{index}"
        is_selected = index == selected_variant_index
        score = int(item.get("score", 0) or 0)
        status = "selected" if is_selected else "support" if score >= 85 else "risk" if item.get("flags") else "neutral"
        add_node(
            variant_id,
            f"Variant #{index + 1}: {item.get('campaign_track', 'post')} / {item.get('service_line', 'post')} - {item.get('title', '')}",
            "candidate",
            score,
            status,
        )
        add_edge("strategy", variant_id, "generates", min(1.0, score / 100))
        add_edge("compliance", variant_id, "checks", 0.0 if item.get("flags") else 1.0)
        add_edge("hardness", variant_id, "validates", min(1.0, max(0, int(state.get("hardness_score", 0) or 0)) / 100))

    decision_status = "support" if state.get("cmo_decision") == "APPROVE_TO_PUBLISH" else "risk"
    add_node("cmo_decision", f"CMO: {state.get('cmo_decision', 'PENDING')}", "decision", None, decision_status)
    if selected_variant_index >= 0:
        add_edge(f"variant_{selected_variant_index}", "cmo_decision", "selected_for_publish", 1.0)
    if jury_choice:
        add_node(
            "jury",
            f"Model jury: {jury_choice.get('decision', 'heuristic')} avg {jury_choice.get('average_score', '-')}",
            "reasoning",
            int(jury_choice.get("average_score", 0) or 0) if jury_choice.get("average_score") else None,
            "support" if jury_choice.get("decision") == "APPROVE_TO_PUBLISH" else "neutral",
        )
        add_edge("jury", "cmo_decision", "votes", 0.8)

    selected_path = ["source_ads", "text_insight", "strategy"]
    if selected_variant_index >= 0:
        selected_path.append(f"variant_{selected_variant_index}")
    selected_path.extend(["compliance", "hardness", "cmo_decision"])
    return {"nodes": nodes, "edges": edges, "selected_path": selected_path}


def _decision_graph_summary(graph: dict) -> str:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    selected_path = graph.get("selected_path", [])
    candidate_nodes = [node for node in nodes if node.get("type") == "candidate"]
    risk_nodes = [node for node in nodes if node.get("status") == "risk"]
    selected_labels = []
    by_id = {node.get("id"): node for node in nodes}
    for node_id in selected_path:
        label = by_id.get(node_id, {}).get("label")
        if label:
            selected_labels.append(str(label))
    return (
        "Graph-of-Thought CMO:\n"
        f"- Nodes: {len(nodes)}; Edges: {len(edges)}; Candidates: {len(candidate_nodes)}.\n"
        f"- Risk nodes: {len(risk_nodes)}.\n"
        f"- Selected path: {' -> '.join(selected_labels) if selected_labels else 'none'}.\n"
        "- Method: reuse evidence nodes, merge model votes + heuristic scorecard, then backtrack through compliance/hardness gates before publish."
    )


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
        f"Tuyến bài: {selected_variant.get('campaign_track', 'post')} - {selected_variant.get('monthly_role', '')}\n"
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


def _cmo_structured_output(state: AgentState) -> str:
    draft = state.get("draft_content") or {}
    decision = state.get("cmo_decision", "REVISE_REQUIRED")
    scorecard = state.get("cmo_scorecard", [])
    selected_index = int(state.get("cmo_selected_variant_index", -1) or -1)
    selected_score = 0
    selected_card = None
    if 0 <= selected_index < len(scorecard):
        selected_card = scorecard[selected_index]
        selected_score = int(selected_card.get("score", 0) or 0)

    compliance_status = "approved" if state.get("approval_status") == "approved" else "not_approved"
    publisher_instruction = (
        "Publisher được phép đăng sau khi người dùng xác nhận lần cuối."
        if decision == "APPROVE_TO_PUBLISH"
        else "Publisher không được đăng. Trả về Content/Strategy Agent để sửa theo CMO feedback."
    )
    revisions = state.get("cmo_feedback", "") if decision != "APPROVE_TO_PUBLISH" else "Không có revision bắt buộc."
    final_copy = (
        f"{draft.get('title', '')}\n\n{draft.get('body', '')}\n\n{draft.get('call_to_action', '')}".strip()
        if decision == "APPROVE_TO_PUBLISH"
        else "Chưa có bản được duyệt."
    )
    decision_object = {
        "decision": decision,
        "approval_status": state.get("approval_status", ""),
        "selected_variant_index": selected_index,
        "selected_creative_index": state.get("cmo_selected_creative_index", -1),
        "score": selected_score,
        "publisher_allowed": decision == "APPROVE_TO_PUBLISH",
        "compliance_status": compliance_status,
        "feedback": state.get("cmo_feedback", ""),
    }

    return "\n".join(
        [
            "1. Executive Decision",
            f"- {decision}: {state.get('cmo_feedback', '')}",
            "2. Campaign Selected",
            f"- Variant #{selected_index + 1 if selected_index >= 0 else 'none'}: {draft.get('title', '')}",
            "3. Why This Campaign Wins",
            f"- {state.get('cmo_campaign_brief', '')}",
            "4. Scorecard",
            f"- Selected score: {selected_score}/100",
            f"- Category scores: {json.dumps(selected_card.get('category_scores', {}) if selected_card else {}, ensure_ascii=False)}",
            "5. Compliance Gate",
            f"- Status: {compliance_status}. Publisher gate requires APPROVE_TO_PUBLISH.",
            "6. Required Revisions",
            f"- {revisions}",
            "7. Final Approved Copy",
            final_copy,
            "8. Creative Direction",
            _creative_asset_summary(state),
            "9. Publisher Instruction",
            f"- {publisher_instruction}",
            "10. CRM/Handoff Notes",
            "- Tag lead theo nhu cầu răng sứ, phục hình sứ, implant; hỏi tình trạng hiện tại, mong muốn, ngân sách dự kiến và thời gian có thể đến khám.",
            "11. JSON Decision Object",
            json.dumps(decision_object, ensure_ascii=False, indent=2),
        ]
    )


def _daily_strategy(state: AgentState) -> str:
    return (
        f"{CMO_SYSTEM_PROMPT}\n\n"
        f"{_cmo_structured_output(state)}\n\n"
        f"CMO objective: {state.get('cmo_objective', '')}\n"
        f"CMO decision: {state.get('cmo_decision', '')} -> {state.get('cmo_next_action', '')}\n"
        f"CMO selected variant: #{state.get('cmo_selected_variant_index', -1) + 1 if state.get('cmo_selected_variant_index', -1) >= 0 else 'none'}\n"
        f"CMO selected creative: #{state.get('cmo_selected_creative_index', -1) + 1 if state.get('cmo_selected_creative_index', -1) >= 0 else 'none'}\n"
        f"CMO feedback: {state.get('cmo_feedback', '')}\n\n"
        f"{state.get('hardness_report', '')}\n\n"
        f"{state.get('cmo_jury_summary', '')}\n\n"
        f"{state.get('cmo_graph_summary', '')}\n\n"
        f"{state.get('cmo_campaign_brief', '')}\n\n"
        f"{state.get('monthly_strategy', '')}\n\n"
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
        "- Đăng/lên lịch variant ads_effective được CMO chọn trước cho mục tiêu lấy SĐT; dùng page_care để nuôi tương tác xen kẽ.\n"
        "- Ghim CTA inbox/SĐT và kịch bản hỏi nhanh: tình trạng răng, mong muốn, thời gian rảnh để thăm khám.\n"
        "- Dùng creative gốc có logo SmileUp; không dùng ảnh/nhận diện của đối thủ.\n"
        "- Theo dõi comment trong 2 giờ đầu sau đăng và chuyển lead nóng sang inbox.\n"
        "Rủi ro cần tránh: claim tuyệt đối, before/after thiếu consent, rebrand ảnh đối thủ."
    )


def _daily_report(state: AgentState) -> str:
    insights = state.get("competitor_insights", [])
    status = state.get("approval_status", "pending")
    return (
        f"Tổng quan insight đối thủ: đã phân tích {len(insights)} nguồn, ưu tiên ads match >=95%, răng sứ, implant, tư vấn và CTA lấy SĐT.\n"
        f"CMO status: {status}.\n"
        f"CMO decision: {state.get('cmo_decision', '')} -> {state.get('cmo_next_action', '')}\n"
        f"CMO feedback: {state.get('cmo_feedback', '')}\n"
        f"Hardness: {state.get('hardness_report', '').replace(chr(10), ' ')}\n"
        f"CMO Jury: {state.get('cmo_jury_summary', '').replace(chr(10), ' ')}\n"
        f"CMO Graph: {state.get('cmo_graph_summary', '').replace(chr(10), ' ')}\n"
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
            f"- {index}. {variant.get('campaign_track', 'post')} / {variant.get('service_line', 'post')}{marker}: {variant.get('title', '')} | Khác biệt: {variant.get('differentiation', '')}"
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
