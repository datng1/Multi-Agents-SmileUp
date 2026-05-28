from datetime import datetime

from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.media_analyzer import build_strategic_direction
from utils.logger import get_logger


logger = get_logger(__name__)


def run_strategy_agent(state: AgentState) -> AgentState:
    logger.info("Strategy Agent selecting SmileUp direction")
    fallback_direction = build_strategic_direction(
        state.get("text_insight_report", ""),
        state.get("visual_insight_report", ""),
        state.get("video_insight_report", ""),
        state.get("facebook_trend_analysis", ""),
    )
    fallback_monthly = _build_monthly_strategy(state)
    report, provider = reason_with_agent_api(
        agent_name="Strategy Agent",
        role="Chuyển insight từ agent con thành chiến lược tháng, funnel, phân khúc, KPI và tuyến bài.",
        task=(
            "Tạo chiến lược tháng cho CMO. Bắt buộc chia 2 tuyến: ads_effective lấy SĐT từ ads match >=95%, "
            "và page_care để nuôi page/tăng tương tác."
        ),
        context={
            "text_insight_report": state.get("text_insight_report", ""),
            "facebook_trend_analysis": state.get("facebook_trend_analysis", ""),
            "visual_insight_report": state.get("visual_insight_report", ""),
            "video_insight_report": state.get("video_insight_report", ""),
            "ad_library_report": state.get("ad_library_report", ""),
            "high_match_ads": state.get("high_match_ads", []),
            "fallback_monthly_strategy": fallback_monthly,
        },
        fallback=f"{fallback_monthly}\n\n{fallback_direction}",
    )
    state["monthly_strategy"] = report
    state["strategic_direction"] = f"{report}\n\n{fallback_direction}".strip()
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
        "- Tuyến 1 - Bài ads hiệu quả: viết theo mục tiêu lấy SĐT/inbox nhanh, dùng hook đúng nỗi đau, lead magnet rõ, CTA yêu cầu khách để lại số điện thoại để được gọi tư vấn; vẫn bắt buộc có thăm khám và không claim quá mức.\n"
        "- Tuyến 2 - Chăm sóc page: bài nuôi niềm tin, checklist, hỏi đáp, tình huống đời thường, tăng bình luận/lưu/chia sẻ; không ép SĐT, không bán gắt.\n"
        "- CMO phải thay đổi hook, góc kể, offer mềm và CTA sau mỗi lượt chạy bằng run_seed để tránh lặp nội dung."
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
