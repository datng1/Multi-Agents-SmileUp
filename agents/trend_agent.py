from graph.state import AgentState
from tools.agent_api_reasoning import reason_with_agent_api
from tools.trend_analyzer import analyze_facebook_trends, build_visual_creative_brief
from utils.logger import get_logger


logger = get_logger(__name__)


def run_trend_agent(state: AgentState) -> AgentState:
    logger.info("Trend Agent analyzing Facebook trend signals")
    focus_keyword = state.get("ad_library_keywords", "")
    insights = state.get("competitor_insights", [])
    fallback_trend = analyze_facebook_trends(insights)
    fallback_visual = build_visual_creative_brief(insights)
    report, provider = reason_with_agent_api(
        agent_name="Trend Agent",
        role="Tổng hợp trend Facebook/Reels/short-form có thể ứng dụng an toàn cho marketing nha khoa.",
        task=(
            "Xuất đúng 2 phần: 'Facebook trend analysis:' và 'Production visual direction:'. "
            "Nêu trend phục vụ paid media và organic, cùng các format nên đưa vào workflow sản xuất."
        ),
        context={
            "focus_keyword": focus_keyword,
            "competitor_insights": insights,
            "high_match_ads": state.get("high_match_ads", []),
            "fallback_trend": fallback_trend,
            "fallback_visual_brief": fallback_visual,
        },
        fallback=f"{fallback_trend}\n\n{fallback_visual}",
    )
    state["facebook_trend_analysis"] = (
        f"Focus keyword: {focus_keyword}\n"
        f"{_section_or_fallback(report, 'Facebook trend analysis:', fallback_trend)}"
    ).strip()
    state["visual_direction"] = (
        f"Focus keyword: {focus_keyword}\n"
        f"{_section_or_fallback(report, 'Production visual direction:', fallback_visual)}"
    ).strip()
    state["current_step"] = "trend_analysis"
    state["messages"].append({"role": "trend", "content": f"Analyzed Facebook trend signals with {provider}"})
    return state


def _section_or_fallback(report: str, marker: str, fallback: str) -> str:
    if marker not in report:
        return fallback
    start = report.find(marker)
    other_markers = ["Facebook trend analysis:", "Production visual direction:"]
    end = len(report)
    for other in other_markers:
        if other == marker:
            continue
        index = report.find(other, start + len(marker))
        if index != -1:
            end = min(end, index)
    return report[start:end].strip() or fallback
