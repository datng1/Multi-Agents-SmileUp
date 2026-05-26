from graph.state import AgentState, DraftContent
from utils.logger import get_logger


logger = get_logger(__name__)


def run_content_agent(state: AgentState) -> AgentState:
    logger.info("Content Agent creating draft")
    if state.get("approval_status") == "needs_revision":
        state["revision_count"] = state.get("revision_count", 0) + 1
    state["draft_content"] = _offline_draft(state)
    state["approval_status"] = "pending"
    state["current_step"] = "content_creator"
    state["messages"].append({"role": "content", "content": "Draft content created"})
    return state


def _offline_draft(state: AgentState) -> DraftContent:
    topics = _dominant_topics(state)
    revision_note = ""
    if state.get("manager_feedback"):
        revision_note = " Bài viết đã được điều chỉnh theo góp ý: nhấn mạnh tư vấn trước điều trị, tránh cam kết tuyệt đối và làm rõ điều kiện ưu đãi."

    return {
        "title": "Nụ cười tự tin bắt đầu từ buổi tư vấn đúng cách",
        "body": (
            "Bạn đang phân vân giữa tẩy trắng răng, niềng răng trong suốt hoặc chỉ đơn giản là muốn kiểm tra sức khỏe răng miệng định kỳ? "
            "Đội ngũ bác sĩ tại phòng khám sẽ thăm khám, lắng nghe nhu cầu và gợi ý lộ trình phù hợp với tình trạng răng của từng khách hàng. "
            "Trong tuần này, khách hàng đặt lịch trước sẽ được tư vấn ban đầu và kiểm tra tổng quát miễn phí theo khung giờ còn trống. "
            "Kết quả thẩm mỹ có thể khác nhau tùy cơ địa, nền răng và chỉ định chuyên môn, vì vậy mọi kế hoạch đều cần được bác sĩ đánh giá trực tiếp. "
            f"Thông điệp hôm nay tập trung vào {topics}: chăm sóc chủ động, minh bạch và an toàn.{revision_note}"
        ),
        "hashtags": ["#nhakhoa", "#rangdep", "#tuvannhakhoa", "#chamsocrangmieng"],
        "call_to_action": "Inbox hoặc gọi hotline để đặt lịch tư vấn và nhận khung giờ phù hợp hôm nay.",
        "image_prompt": "Ảnh phòng khám nha khoa hiện đại, bác sĩ tư vấn thân thiện cho khách hàng Việt Nam.",
    }


def _dominant_topics(state: AgentState) -> str:
    counts: dict[str, int] = {}
    for insight in state.get("competitor_insights", []):
        for topic in insight.get("key_topics", []):
            counts[topic] = counts.get(topic, 0) + 1
    if not counts:
        return "khám định kỳ và tư vấn cá nhân hóa"
    return ", ".join(topic.replace("_", " ") for topic, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:2])
