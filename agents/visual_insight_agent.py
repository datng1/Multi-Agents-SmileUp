from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.media_analyzer import build_visual_insight_report
from utils.logger import get_logger


logger = get_logger(__name__)


def run_visual_insight_agent(state: AgentState) -> AgentState:
    logger.info("Visual Insight Agent analyzing image notes")
    fallback = build_visual_insight_report(
        state.get("competitor_visual_notes", ""),
        state.get("visual_creative_brief", ""),
    )
    report, provider = reason_with_agent_api(
        agent_name="Visual Insight Agent",
        role="Đọc ghi chú ảnh/media preview, rút bố cục, text overlay, tín hiệu niềm tin và creative direction an toàn.",
        task=(
            "Tạo report cho CMO về visual nên dùng cho tuyến ads hiệu quả và tuyến chăm sóc page. "
            "Nếu workflow chọn rewrite ảnh, chỉ cho phép dùng ảnh ads làm reference bố cục/visual hierarchy; "
            "ảnh đầu ra phải là creative SmileUp mới, khác mặt người, khác nền, khác text, không dùng lại pixel/logo/tài sản đối thủ."
        ),
        context={
            "competitor_visual_notes": state.get("competitor_visual_notes", ""),
            "visual_creative_brief": state.get("visual_creative_brief", ""),
            "creative_image_mode": state.get("creative_image_mode", ""),
            "creative_reference_ad": state.get("creative_reference_ad", {}),
        },
        fallback=fallback,
    )
    state["visual_insight_report"] = report
    state["current_step"] = "visual_insight"
    state["messages"].append({"role": "visual_insight", "content": f"Analyzed visual notes with {provider}"})
    return state
