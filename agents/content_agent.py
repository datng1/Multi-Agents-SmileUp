from graph.state import AgentState, DraftContent
from tools.gemini_client import GeminiUnavailable, generate_draft_with_gemini
from utils.logger import get_logger


logger = get_logger(__name__)


def run_content_agent(state: AgentState) -> AgentState:
    logger.info("Content Agent creating draft")
    if state.get("approval_status") == "needs_revision":
        state["revision_count"] = state.get("revision_count", 0) + 1

    try:
        state["draft_content"] = generate_draft_with_gemini(state)
        state["messages"].append({"role": "content", "content": "Draft content created with Gemini"})
    except (GeminiUnavailable, Exception) as exc:
        logger.warning("Gemini draft generation failed, using offline draft: %s", exc)
        state["draft_content"] = _offline_draft(state)
        state["messages"].append({"role": "content", "content": f"Draft content created locally ({exc})"})

    state["approval_status"] = "pending"
    state["current_step"] = "content_creator"
    return state


def _offline_draft(state: AgentState) -> DraftContent:
    topics = _dominant_topics(state)
    revision_note = ""
    if state.get("manager_feedback"):
        revision_note = " Bài viết đã được điều chỉnh theo góp ý: nhấn mạnh tư vấn trước điều trị, tránh cam kết tuyệt đối và làm rõ điều kiện ưu đãi."

    return {
        "marketing_analysis": (
            "Khách hàng mục tiêu là người đang cân nhắc răng sứ hoặc implant nhưng còn lo về chi phí, đau, độ bền và chỉ định có phù hợp không. "
            "Bài viết cần kéo họ vào tư vấn bằng thông điệp cá nhân hóa, minh bạch, bác sĩ thăm khám trước khi quyết định."
        ),
        "trend_angle": "Hook dạng câu hỏi về mất răng/thiếu tự tin, kết hợp lợi ích ăn nhai và thẩm mỹ, CTA inbox để được tư vấn.",
        "post_structure": "Hook -> Nỗi đau -> Giải pháp SmileUp -> Lý do tin tưởng -> Lưu ý chuyên môn -> CTA.",
        "title": "Nụ cười chắc khỏe bắt đầu từ tư vấn răng sứ và implant đúng cách",
        "body": (
            "Bạn đang cân nhắc làm răng sứ để cải thiện nụ cười, hoặc cần cấy ghép implant để khôi phục khả năng ăn nhai sau mất răng? "
            "Tại SmileUp, mỗi kế hoạch đều bắt đầu bằng thăm khám và tư vấn cá nhân hóa để bác sĩ đánh giá nền răng, khớp cắn, xương hàm và mong muốn thẩm mỹ của từng khách hàng. "
            "Điểm quan trọng không chỉ là chọn dịch vụ, mà là chọn đúng chỉ định: răng sứ cần bảo tồn tối đa mô răng thật, implant cần đánh giá kỹ tình trạng xương và sức khỏe tổng quát. "
            "Kết quả có thể khác nhau tùy tình trạng răng miệng và chỉ định chuyên môn, vì vậy SmileUp luôn khuyến khích khách hàng đặt lịch tư vấn trực tiếp trước khi quyết định. "
            f"Thông điệp hôm nay tập trung vào {topics}: chuyên môn rõ ràng, minh bạch và an toàn.{revision_note}"
        ),
        "hashtags": ["#nhakhoa", "#rangsuthammy", "#implant", "#SmileUp"],
        "call_to_action": "Inbox hoặc gọi hotline để đặt lịch tư vấn răng sứ/implant và nhận khung giờ phù hợp hôm nay.",
        "image_prompt": "Ảnh gốc/AI mới cho SmileUp: bác sĩ tư vấn răng sứ và implant trong phòng khám hiện đại, logo SmileUp ở góc trên trái, ánh sáng trắng xanh sạch sẽ.",
    }


def _dominant_topics(state: AgentState) -> str:
    counts: dict[str, int] = {}
    for insight in state.get("competitor_insights", []):
        for topic in insight.get("key_topics", []):
            counts[topic] = counts.get(topic, 0) + 1
    if not counts:
        return "răng sứ thẩm mỹ và implant cá nhân hóa"
    return ", ".join(topic.replace("_", " ") for topic, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:2])
