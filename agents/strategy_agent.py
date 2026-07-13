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
        role="Chuyển insight Meta mới quét thành chiến dịch media 1 tháng khách quan, có brand riêng và khả thi cho đội ba người.",
        task=(
            "Chọn một campaign thesis cho 1 tháng và chia thành 4 tuần: nhận diện, chuyên môn, gỡ rào cản, chuyển đổi tư vấn. "
            "Mỗi tuần nêu objective, evidence, ba video và đầu việc cho Biên kịch, Đạo diễn AI, Video Editor. "
            "Đề xuất brand lane riêng cho SmileUp dựa trên logo xanh-trắng, tư vấn minh bạch và chuyên môn dễ hiểu. "
            "Phân biệt rõ bằng chứng, suy luận và khuyến nghị; không coi tần suất ads là bằng chứng chuyển đổi. "
            "Không viết bài đăng, tạo asset hoặc thực hiện đăng bài."
        ),
        context={
            "focus_keyword": focus_keyword,
            "text_insight_report": state.get("text_insight_report", ""),
            "facebook_trend_analysis": state.get("facebook_trend_analysis", ""),
            "visual_insight_report": state.get("visual_insight_report", ""),
            "video_insight_report": state.get("video_insight_report", ""),
            "ad_library_report": state.get("ad_library_report", ""),
            "high_match_ads": state.get("high_match_ads", []),
            "market_campaign_intelligence": state.get("market_campaign_intelligence", {}),
            "fallback_monthly_strategy": fallback_monthly,
            "run_seed": state.get("run_seed", ""),
            "production_focus_profile": state.get("production_focus_profile", {}),
        },
        fallback=f"{fallback_monthly}\n\n{fallback_direction}",
        complexity="complex",
    )
    state["monthly_strategy"] = f"Focus keyword: {focus_keyword}\n{report}".strip()
    state["weekly_strategy"] = state["monthly_strategy"]
    state["strategic_direction"] = f"Focus keyword: {focus_keyword}\n{report}\n\n{fallback_direction}".strip()
    state["current_step"] = "strategy"
    state["messages"].append({"role": "strategy", "content": f"Built 1-month CMO campaign with {provider}"})
    return state


def _build_monthly_strategy(state: AgentState) -> str:
    high_match_ads = state.get("high_match_ads", [])
    keywords = state.get("ad_library_keywords") or "nha khoa răng sứ răng đẹp cấy implant"
    source_count = len(high_match_ads)
    service_focus = _service_focus(state)
    sample_pages = _sample_pages(high_match_ads or state.get("ad_library_ads", []))

    return (
        "Chiến dịch media 1 tháng cho SmileUp:\n"
        f"- Trọng tâm dịch vụ: {service_focus}.\n"
        f"- Nguồn ads ưu tiên: {source_count} ads có keyword match từ 95% trở lên với cụm '{keywords}'. "
        "Nếu chưa đủ nguồn 95%, CMO vẫn dùng toàn bộ ads đã quét để lấy tín hiệu phụ nhưng không coi là chuẩn chiến dịch.\n"
        f"- Page/nguồn nổi bật để tham chiếu thị trường: {sample_pages or 'chưa đủ dữ liệu'}.\n"
        "- Tuần 1: nhận diện đúng vấn đề; tuần 2: hiểu đúng chỉ định; tuần 3: gỡ rào cản; tuần 4: tư vấn minh bạch tại SmileUp.\n"
        "- Sản lượng: 3 short video mỗi tuần, tổng 12 video theo cùng một campaign thesis.\n"
        "- Brand lane: xanh cyan/xanh lam/trắng từ logo, motif cánh hoa, bác sĩ giải thích bình tĩnh và không gây áp lực.\n"
        "- Mục tiêu: tạo nhu cầu tư vấn đủ điều kiện và tăng niềm tin, không tối ưu lượt xem đơn thuần.\n"
        "- Giới hạn: dữ liệu ads là tín hiệu thị trường, không chứng minh doanh thu hay chuyển đổi.\n"
        "- Phạm vi: CMO định hướng và giao việc; đội media hoàn thiện video, không đăng bài trong ứng dụng."
    )


def _service_focus(state: AgentState) -> str:
    keyword = str(state.get("ad_library_keywords", ""))
    text = " ".join(
        [keyword, *[str(ad.get("ad_text", "")) for ad in state.get("high_match_ads", []) or state.get("ad_library_ads", [])]]
    )
    lowered = text.lower()
    if "niềng" in lowered or "nieng" in lowered or "chỉnh nha" in lowered:
        return "niềng răng và chỉnh nha theo nhu cầu đã nhập"
    if "implant" in lowered or "cấy" in lowered:
        return "cấy ghép Implant và phục hình ăn nhai"
    if "sứ" in lowered or "su" in lowered:
        return "răng sứ thẩm mỹ và phục hình răng sứ"
    return keyword or "dịch vụ nha khoa theo keyword đã nhập"


def _sample_pages(ads: list[dict]) -> str:
    pages: list[str] = []
    for ad in ads:
        page = str(ad.get("page_name", "")).strip()
        if page and page not in pages:
            pages.append(page)
    return ", ".join(pages[:6])
