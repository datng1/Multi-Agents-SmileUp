from graph.state import AgentState
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
        flags = _compliance_flags(draft)
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
        "Thông điệp chủ đạo: Tư vấn nha khoa cá nhân hóa, minh bạch và an toàn.\n"
        "Dịch vụ trọng tâm: Khám tổng quát, tẩy trắng răng, niềng răng trong suốt.\n"
        f"Insight thị trường: {state.get('market_trend_summary', '')}\n"
        "3-5 hành động hôm nay:\n"
        "- Đăng bài tư vấn đặt lịch trước.\n"
        "- Ghim CTA inbox/hotline trên Facebook Page.\n"
        "- Chuẩn bị phản hồi mẫu cho câu hỏi về giá và thời gian điều trị.\n"
        "- Theo dõi comment trong 2 giờ đầu sau đăng.\n"
        "Kênh triển khai: Facebook Page, inbox, hotline.\n"
        "Rủi ro cần tránh: Cam kết kết quả tuyệt đối hoặc so sánh công kích đối thủ."
    )


def _daily_report(state: AgentState) -> str:
    insights = state.get("competitor_insights", [])
    status = state.get("approval_status", "pending")
    return (
        f"Tổng quan insight đối thủ: đã phân tích {len(insights)} nguồn, nổi bật là tư vấn miễn phí, tẩy trắng răng và chăm sóc định kỳ.\n"
        f"Nội dung hiện tại: {status}.\n"
        f"Lý do quyết định: {state.get('manager_feedback', '')}\n"
        "Checklist compliance: không claim tuyệt đối, CTA là đặt lịch tư vấn, có lưu ý kết quả tùy tình trạng răng.\n"
        "Khuyến nghị cho ngày mai: so sánh hiệu quả tương tác của bài tư vấn với bài ưu đãi để tối ưu lịch đăng."
    )
