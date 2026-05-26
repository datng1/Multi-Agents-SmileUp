from graph.state import AgentState
from tools.compliance import compliance_flags
from utils.logger import get_logger


logger = get_logger(__name__)

RISKY_CLAIMS = [
    "100%",
    "vĩnh viễn",
    "không đau hoàn toàn",
    "đẹp ngay lập tức",
    "số 1",
    "duy nhất",
    "rẻ nhất",
    "chắc chắn khỏi",
]


def run_manager_agent(state: AgentState) -> AgentState:
    logger.info("Manager Agent reviewing draft")
    draft = state.get("draft_content")
    if not draft:
        state["approval_status"] = "rejected"
        state["manager_feedback"] = "Chưa có bản nháp để duyệt."
    else:
        flags = compliance_flags(draft)
        word_count = len(draft["body"].split())
        if flags:
            state["approval_status"] = "needs_revision" if state.get("revision_count", 0) < 3 else "rejected"
            state["manager_feedback"] = "Cần sửa claim rủi ro: " + ", ".join(flags)
        elif word_count < 110:
            state["approval_status"] = "needs_revision"
            state["manager_feedback"] = "Bài viết còn ngắn, cần bổ sung insight, điều kiện ưu đãi và lưu ý thăm khám."
        elif not draft.get("call_to_action"):
            state["approval_status"] = "needs_revision"
            state["manager_feedback"] = "Thiếu CTA đặt lịch/tư vấn."
        else:
            state["approval_status"] = "approved"
            state["manager_feedback"] = "Duyệt: nội dung rõ lợi ích, CTA an toàn, không cam kết quá mức."

    state["daily_strategy"] = _daily_strategy(state)
    state["daily_report"] = _daily_report(state)
    state["current_step"] = "manager_review"
    state["messages"].append({"role": "manager", "content": state["approval_status"]})
    return state


def _compliance_flags(draft: dict) -> list[str]:
    text = " ".join(str(draft.get(key, "")) for key in ("title", "body", "call_to_action")).lower()
    return [claim for claim in RISKY_CLAIMS if claim.lower() in text]


def _daily_strategy(state: AgentState) -> str:
    return (
        "Thông điệp chủ đạo: Răng sứ và implant cá nhân hóa, minh bạch và an toàn.\n"
        "Dịch vụ trọng tâm: Răng sứ thẩm mỹ, phục hình răng sứ, cấy ghép implant.\n"
        f"Insight thị trường: {state.get('market_trend_summary', '')}\n"
        f"{state.get('ad_library_report', '')}\n"
        f"{state.get('facebook_trend_analysis', '')}\n"
        f"{state.get('strategic_direction', '')}\n"
        f"{state.get('compliance_report', '')}\n"
        "3-5 hành động hôm nay:\n"
        "- Đăng bài tư vấn răng sứ/implant với hook gợi nhu cầu thật: mất răng, ăn nhai, nụ cười thiếu tự tin.\n"
        "- Ghim CTA inbox/hotline và kịch bản hỏi nhanh: tình trạng răng, mong muốn, thời gian rảnh để thăm khám.\n"
        "- Chuẩn bị phản hồi mẫu cho câu hỏi về giá, thời gian điều trị, bảo hành và điều kiện trả góp.\n"
        "- Theo dõi comment trong 2 giờ đầu sau đăng và chuyển lead nóng sang inbox.\n"
        "Kênh triển khai: Facebook Page, reels/story ngắn, inbox, hotline.\n"
        "Rủi ro cần tránh: Cam kết kết quả tuyệt đối, before/after thiếu consent, dùng ảnh/nhận diện của đối thủ."
    )


def _daily_report(state: AgentState) -> str:
    insights = state.get("competitor_insights", [])
    status = state.get("approval_status", "pending")
    return (
        f"Tổng quan insight đối thủ: đã phân tích {len(insights)} nguồn, ưu tiên đọc tín hiệu liên quan răng sứ, implant, ưu đãi, tư vấn và CTA.\n"
        f"Nội dung hiện tại: {status}.\n"
        f"Lý do quyết định: {state.get('manager_feedback', '')}\n"
        f"Ad Library: {state.get('ad_library_report', '').replace(chr(10), ' ')}\n"
        f"Trend Facebook: {state.get('facebook_trend_analysis', '').replace(chr(10), ' ')}\n"
        f"Visual brief: {state.get('visual_creative_brief', '').replace(chr(10), ' ')}\n"
        f"Agent strategy: {state.get('strategic_direction', '').replace(chr(10), ' ')}\n"
        f"Compliance: {state.get('compliance_report', '').replace(chr(10), ' ')}\n"
        "Checklist compliance: không claim tuyệt đối, CTA là đặt lịch tư vấn, có lưu ý kết quả tùy tình trạng răng.\n"
        "Khuyến nghị cho ngày mai: so sánh hiệu quả bài răng sứ với bài implant, ưu tiên hook có vấn đề cụ thể và visual gốc của SmileUp."
    )
