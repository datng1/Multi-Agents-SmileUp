from datetime import datetime

from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.media_analyzer import build_strategic_direction
from utils.logger import get_logger


logger = get_logger(__name__)


def run_strategy_agent(state: AgentState) -> AgentState:
    logger.info("Strategy Agent selecting SmileUp direction")
    focus_keyword = state.get("ad_library_keywords", "")
    fallback_direction = build_strategic_direction(
        state.get("text_insight_report", ""),
        state.get("visual_insight_report", ""),
        state.get("video_insight_report", ""),
        state.get("facebook_trend_analysis", ""),
    )
    fallback_monthly = _build_monthly_strategy(state)
    report, provider = reason_with_agent_api(
        agent_name="Strategy Agent",
        role="Chuyển insight từ agent con thành chiến lược tháng, funnel, phân khúc, KPI và phạm vi sản xuất media.",
        task=(
            "Tạo chiến lược tháng cho CMO. Bắt buộc chia paid media và organic media, xác định audience, "
            "message hierarchy, format cần sản xuất và KPI. Không viết bài đăng hoặc tạo asset."
        ),
        context={
            "focus_keyword": focus_keyword,
            "text_insight_report": state.get("text_insight_report", ""),
            "facebook_trend_analysis": state.get("facebook_trend_analysis", ""),
            "visual_insight_report": state.get("visual_insight_report", ""),
            "video_insight_report": state.get("video_insight_report", ""),
            "ad_library_report": state.get("ad_library_report", ""),
            "high_match_ads": state.get("high_match_ads", []),
            "fallback_monthly_strategy": fallback_monthly,
            "run_seed": state.get("run_seed", ""),
            "production_focus_profile": state.get("production_focus_profile", {}),
        },
        fallback=f"{fallback_monthly}\n\n{fallback_direction}",
    )
    state["monthly_strategy"] = f"Focus keyword: {focus_keyword}\n{report}".strip()
    state["strategic_direction"] = f"Focus keyword: {focus_keyword}\n{report}\n\n{fallback_direction}".strip()
    state["current_step"] = "strategy"
    state["messages"].append({"role": "strategy", "content": f"Built monthly CMO strategy with {provider}"})
    return state


def _build_monthly_strategy(state: AgentState) -> str:
    month_label = datetime.now().strftime("%m/%Y")
    high_match_ads = state.get("high_match_ads", [])
    keywords = state.get("ad_library_keywords") or "nha khoa răng sứ răng đẹp cấy implant"
    source_count = len(high_match_ads)
    service_focus = _service_focus(state)
    sample_pages = _sample_pages(high_match_ads or state.get("ad_library_ads", []))

    return (
        f"Chiến lược tháng {month_label} cho SmileUp:\n"
        f"- Trọng tâm dịch vụ: {service_focus}.\n"
        f"- Nguồn ads ưu tiên: {source_count} ads có keyword match từ 95% trở lên với cụm '{keywords}'. "
        "Nếu chưa đủ nguồn 95%, CMO vẫn dùng toàn bộ ads đã quét để lấy tín hiệu phụ nhưng không coi là chuẩn chiến dịch.\n"
        f"- Page/nguồn nổi bật để tham chiếu thị trường: {sample_pages or 'chưa đủ dữ liệu'}.\n"
        "- Paid media lane: ưu tiên short video, static proof và carousel giải thích; mỗi format phải có hypothesis và mục tiêu lead rõ.\n"
        "- Organic lane: ưu tiên checklist, hỏi đáp và quy trình chuyên môn để tăng trust, save/share và chuẩn bị nhu cầu.\n"
        "- CMO chỉ khóa brief, format và tiêu chí; đội sản xuất chịu trách nhiệm tạo asset qua các approval gate."
    )


def _service_focus(state: AgentState) -> str:
    text = " ".join(str(ad.get("ad_text", "")) for ad in state.get("high_match_ads", []) or state.get("ad_library_ads", []))
    lowered = text.lower()
    if "implant" in lowered or "cấy" in lowered:
        return "cấy ghép Implant và phục hình ăn nhai"
    if "sứ" in lowered or "su" in lowered:
        return "răng sứ thẩm mỹ và phục hình răng sứ"
    return "răng sứ thẩm mỹ, phục hình răng sứ và cấy ghép Implant"


def _sample_pages(ads: list[dict]) -> str:
    pages: list[str] = []
    for ad in ads:
        page = str(ad.get("page_name", "")).strip()
        if page and page not in pages:
            pages.append(page)
    return ", ".join(pages[:6])
