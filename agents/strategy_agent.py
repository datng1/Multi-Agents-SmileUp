import json
import re
from difflib import SequenceMatcher

from graph.state import AgentState
from tools.ad_evidence import build_full_ad_evidence
from tools.agent_api_reasoning import RequiredModelUnavailable, reason_with_agent_api
from tools.media_analyzer import build_strategic_direction
from utils import config
from utils.logger import get_logger


logger = get_logger(__name__)

MAX_STRATEGY_CONTEXT_CHARS = 400000
NOVELTY_SIMILARITY_LIMIT = 0.78


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
    evidence = state.get("full_ad_evidence") or build_full_ad_evidence(
        state.get("ad_library_ads", []),
        focus_keyword=focus_keyword,
        scan_id=state.get("ad_library_scan_id", ""),
    )
    if evidence.get("included_ads_count") != evidence.get("observed_ads_count") or not evidence.get(
        "all_ads_included"
    ):
        raise RuntimeError("Sol evidence packet is incomplete; strategy generation stopped")
    previous = state.get("previous_campaign_snapshot") or {}
    base_context = {
        "focus_keyword": focus_keyword,
        "run_seed": state.get("run_seed", ""),
        "production_focus_profile": state.get("production_focus_profile", {}),
        "previous_campaign_snapshot": previous,
        "full_ad_evidence": evidence,
        "market_campaign_intelligence": state.get("market_campaign_intelligence", {}),
        "text_insight_report": state.get("text_insight_report", ""),
        "facebook_trend_analysis": state.get("facebook_trend_analysis", ""),
        "visual_insight_report": state.get("visual_insight_report", ""),
        "video_insight_report": state.get("video_insight_report", ""),
        "ad_library_report": state.get("ad_library_report", ""),
        "fallback_monthly_strategy": fallback_monthly,
    }
    context_chars = len(json.dumps(base_context, ensure_ascii=False, indent=2, default=str))
    if context_chars > MAX_STRATEGY_CONTEXT_CHARS:
        raise RuntimeError(
            f"Sol strategy context exceeds the safe full-evidence budget: {context_chars}/{MAX_STRATEGY_CONTEXT_CHARS} chars"
        )
    task = _strategy_task(evidence, has_previous=bool(previous))
    report, provider = reason_with_agent_api(
        agent_name="Strategy Agent",
        role="Chuyển insight Meta mới quét thành chiến dịch media 1 tháng khách quan, có brand riêng và khả thi cho đội ba người.",
        task=task,
        context=base_context,
        fallback=f"{fallback_monthly}\n\n{fallback_direction}",
        max_context_chars=MAX_STRATEGY_CONTEXT_CHARS,
        complexity="complex",
    )
    quality = _assess_strategy_quality(previous, report, state.get("production_focus_profile", {}), evidence)
    enforce_quality = config.AGENT_API_REASONING_ENABLED and not config.MOCK_MODE
    if enforce_quality and not quality["accepted"]:
        retry_context = dict(base_context)
        retry_context["rejected_candidate"] = report[:18000]
        retry_context["quality_gate_failures"] = quality["failures"]
        retry_chars = len(json.dumps(retry_context, ensure_ascii=False, indent=2, default=str))
        if retry_chars > MAX_STRATEGY_CONTEXT_CHARS:
            retry_context["rejected_candidate"] = str(report)[:2000]
            retry_chars = len(json.dumps(retry_context, ensure_ascii=False, indent=2, default=str))
        if retry_chars > MAX_STRATEGY_CONTEXT_CHARS:
            raise RequiredModelUnavailable(
                f"Sol strategy retry context exceeds full-evidence budget: {retry_chars}/{MAX_STRATEGY_CONTEXT_CHARS} chars"
            )
        report, provider = reason_with_agent_api(
            agent_name="Strategy Agent",
            role="Sửa chiến lược tháng chưa đạt evidence/novelty gate; không thay đổi dữ kiện nguồn.",
            task=task + "\nĐây là lần sửa cuối. Khắc phục toàn bộ quality_gate_failures và không lặp candidate bị từ chối.",
            context=retry_context,
            fallback=f"{fallback_monthly}\n\n{fallback_direction}",
            max_context_chars=MAX_STRATEGY_CONTEXT_CHARS,
            complexity="complex",
        )
        quality = _assess_strategy_quality(previous, report, state.get("production_focus_profile", {}), evidence)
        if not quality["accepted"]:
            raise RequiredModelUnavailable(
                "Sol strategy quality gate failed after one rewrite: " + "; ".join(quality["failures"])
            )
    quality["enforced"] = enforce_quality
    state["strategy_novelty"] = quality
    state["sol_weekly_blueprint"] = _extract_weekly_blueprint(report)
    state["monthly_strategy"] = f"Focus keyword: {focus_keyword}\n{report}".strip()
    state["weekly_strategy"] = state["monthly_strategy"]
    state["strategic_direction"] = f"Focus keyword: {focus_keyword}\n{report}\n\n{fallback_direction}".strip()
    state["current_step"] = "strategy"
    state["messages"].append({"role": "strategy", "content": f"Built 1-month CMO campaign with {provider}"})
    return state


def _strategy_task(evidence: dict, *, has_previous: bool) -> str:
    included = int(evidence.get("included_ads_count", 0) or 0)
    observed = int(evidence.get("observed_ads_count", 0) or 0)
    previous_rule = (
        "So sánh với previous_campaign_snapshot và thay đổi ít nhất ba yếu tố chiến lược có căn cứ."
        if has_previous
        else "Đây là chiến dịch đầu tiên; ghi rõ baseline thay vì bịa khác biệt lịch sử."
    )
    return (
        f"Đọc đủ full_ad_evidence gồm {included}/{observed} ads trước khi kết luận. "
        "Nhóm priority_reference_ads chỉ là mẫu tham chiếu proxy, không phải quảng cáo đã chứng minh doanh thu. "
        "Chọn một campaign thesis cho 1 tháng và chia thành 4 tuần: nhận diện, chuyên môn, gỡ rào cản, chuyển đổi tư vấn. "
        "Mỗi tuần phải nêu objective, insight học từ toàn bộ tập ads, tối thiểu hai evidence_id liên quan, ba video cụ thể, "
        "và chỉ dẫn riêng cho Biên kịch, Đạo diễn AI, Video Editor. "
        "Đề xuất brand lane SmileUp dựa trên logo xanh-trắng, tư vấn minh bạch và chuyên môn dễ hiểu. "
        f"{previous_rule} "
        "Không coi tần suất ads là bằng chứng chuyển đổi; không viết bài đăng, tạo asset hoặc thực hiện đăng bài. "
        f"Dòng đầu bắt buộc viết chính xác: EVIDENCE_COVERAGE: {included}/{observed}. "
        "Ngay sau đó có mục 'Điểm mới so với chiến dịch trước' và nêu các thay đổi cụ thể."
        " Cuối báo cáo bắt buộc có WEEKLY_BLUEPRINT_JSON trong fenced JSON hợp lệ với schema: "
        '{"weeks":[{"week":1,"theme":"...","objective":"...","evidence_ids":["AD-001","AD-002"],'
        '"content_outputs":["video 1","video 2","video 3"],"scriptwriter_brief":"...",'
        '"director_brief":"...","editor_brief":"..."}, ... đến week 4]}. '
        "Mỗi brief phải đủ cụ thể để đúng người nhận việc có thể bắt đầu mà không tự đoán chiến lược."
    )


def _assess_strategy_quality(
    previous: dict,
    candidate: str,
    profile: dict,
    evidence: dict,
) -> dict:
    failures: list[str] = []
    included = int(evidence.get("included_ads_count", 0) or 0)
    observed = int(evidence.get("observed_ads_count", 0) or 0)
    expected_marker = f"evidence_coverage: {included}/{observed}"
    lowered = str(candidate or "").lower()
    if expected_marker not in lowered:
        failures.append("missing exact evidence coverage marker")

    valid_ids = {str(item.get("evidence_id") or "") for item in evidence.get("ads", [])}
    cited_ids = set(re.findall(r"\bAD-\d{3}\b", str(candidate or ""), flags=re.IGNORECASE))
    cited_ids = {item.upper() for item in cited_ids if item.upper() in valid_ids}
    minimum_citations = min(4, len(valid_ids))
    if len(cited_ids) < minimum_citations:
        failures.append(f"only {len(cited_ids)}/{minimum_citations} unique ad evidence IDs cited")

    blueprint = _extract_weekly_blueprint(candidate)
    if len(blueprint) != 4:
        failures.append(f"weekly blueprint has {len(blueprint)}/4 valid weeks")
    else:
        for index, week in enumerate(blueprint, 1):
            if int(week.get("week", 0) or 0) != index:
                failures.append(f"weekly blueprint week {index} has invalid sequence")
            if len(week.get("content_outputs") or []) != 3:
                failures.append(f"weekly blueprint week {index} does not contain exactly 3 outputs")
            week_ids = {str(item).upper() for item in week.get("evidence_ids") or []}
            if len(week_ids & valid_ids) < min(2, len(valid_ids)):
                failures.append(f"weekly blueprint week {index} lacks two valid evidence IDs")
            for role_key in ("scriptwriter_brief", "director_brief", "editor_brief"):
                if len(str(week.get(role_key) or "").strip()) < 20:
                    failures.append(f"weekly blueprint week {index} has an incomplete {role_key}")

    previous_text = str(previous.get("monthly_strategy") or "")
    similarity = _strategy_similarity(previous_text, candidate) if previous_text else 0.0
    previous_profile = previous.get("production_focus_profile") or {}
    dimensions = ("campaign_hypothesis", "hook_style", "production_format", "lead_magnet", "cta_mode")
    changed_dimensions = [key for key in dimensions if profile.get(key) and profile.get(key) != previous_profile.get(key)]
    if previous_text:
        if "điểm mới" not in lowered:
            failures.append("missing declared delta from previous campaign")
        if similarity >= NOVELTY_SIMILARITY_LIMIT:
            failures.append(f"strategy similarity {similarity:.0%} exceeds {NOVELTY_SIMILARITY_LIMIT:.0%}")
        if len(changed_dimensions) < 3:
            failures.append(f"only {len(changed_dimensions)}/3 strategic dimensions changed")

    return {
        "accepted": not failures,
        "failures": failures,
        "previous_workflow_id": previous.get("workflow_id") or "",
        "similarity_to_previous": round(similarity, 3),
        "similarity_limit": NOVELTY_SIMILARITY_LIMIT,
        "changed_dimensions": changed_dimensions,
        "cited_ad_evidence_ids": sorted(cited_ids),
        "evidence_coverage": f"{included}/{observed}",
        "weekly_blueprint_weeks": len(blueprint),
    }


def _strategy_similarity(previous: str, candidate: str) -> float:
    def normalize(value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value.lower())).strip()

    return SequenceMatcher(None, normalize(previous), normalize(candidate)).ratio()


def _extract_weekly_blueprint(report: str) -> list[dict]:
    marker = re.search(r"weekly_blueprint_json\s*:?\s*", str(report or ""), flags=re.IGNORECASE)
    if not marker:
        return []
    payload = str(report or "")[marker.end() :].lstrip()
    if payload.startswith("```json"):
        payload = payload[7:].lstrip()
    elif payload.startswith("```"):
        payload = payload[3:].lstrip()
    try:
        parsed, _ = json.JSONDecoder().raw_decode(payload)
    except (json.JSONDecodeError, TypeError):
        return []
    weeks = parsed.get("weeks") if isinstance(parsed, dict) else None
    if not isinstance(weeks, list):
        return []
    return [dict(week) for week in weeks if isinstance(week, dict)]


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
