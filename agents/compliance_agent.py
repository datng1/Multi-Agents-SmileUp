from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from utils.logger import get_logger


logger = get_logger(__name__)


PRODUCTION_GUARDRAILS = [
    "Không dùng claim tuyệt đối về kết quả, đau, độ bền hoặc tỷ lệ thành công.",
    "Không đưa chỉ định điều trị khi chưa có bác sĩ thăm khám và chẩn đoán.",
    "Ảnh/video có bệnh nhân phải có consent và phạm vi sử dụng được lưu lại.",
    "Không sao chép caption, hình ảnh, gương mặt, logo hoặc nhận diện của đối thủ.",
    "Before/after chỉ được dùng khi có consent, bối cảnh và disclaimer phù hợp.",
    "Mọi asset phải qua Medical Compliance trước khi bàn giao cho đội kênh.",
]


def run_compliance_agent(state: AgentState) -> AgentState:
    logger.info("Compliance Agent defining production guardrails")
    focus_keyword = state.get("ad_library_keywords", "")
    fallback = _fallback_report()
    report, provider = reason_with_agent_api(
        agent_name="Compliance Agent",
        role="Thiết lập guardrail y khoa, pháp lý, quyền hình ảnh và brand safety cho quy trình sản xuất media nha khoa.",
        task=(
            "Đánh giá chiến dịch 1 tháng, brand lane và insight trước khi sản xuất. Chỉ ra các rủi ro cần kiểm tra theo tuần "
            "về chuyên môn, thương hiệu và quyền media. Không viết caption và không tạo nội dung đăng bài."
        ),
        context={
            "focus_keyword": focus_keyword,
            "strategic_direction": state.get("strategic_direction", ""),
            "text_insight_report": state.get("text_insight_report", ""),
            "visual_insight_report": state.get("visual_insight_report", ""),
            "video_insight_report": state.get("video_insight_report", ""),
            "production_guardrails": PRODUCTION_GUARDRAILS,
        },
        fallback=fallback,
        complexity="complex",
    )
    state["production_guardrails"] = list(PRODUCTION_GUARDRAILS)
    state["compliance_report"] = f"Focus keyword: {focus_keyword}\n{report}".strip()
    state["current_step"] = "compliance"
    state["messages"].append({"role": "compliance", "content": f"Defined production guardrails with {provider}"})
    return state


def _fallback_report() -> str:
    return "\n".join(
        [
            "Production compliance guardrails:",
            *[f"- {item}" for item in PRODUCTION_GUARDRAILS],
            "Required checkpoints: medical, brand and asset-rights review at the end of every week before the next brief opens.",
        ]
    )
