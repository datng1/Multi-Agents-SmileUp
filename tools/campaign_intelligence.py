from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any


SERVICE_RULES = (
    ("implant", ("implant", "cay ghep", "trong rang", "mat rang", "phuc hinh an nhai")),
    ("orthodontics", ("nieng", "chinh nha", "invisalign", "khay trong")),
    ("crowns", ("rang su", "boc su", "dan su", "veneer")),
    ("whitening", ("tay trang", "trang rang")),
    ("general", ("nha khoa", "kham rang", "cham soc rang", "dieu tri")),
)

ANGLE_RULES = (
    ("price_offer", ("uu dai", "giam", "%", "mien phi", "bao gia", "combo", "tra gop", "0%")),
    ("doctor_authority", ("bac si", "chuyen gia", "chuyen mon", "hoi dong")),
    ("technology_process", ("cong nghe", "quy trinh", "chup phim", "scan", "may moc", "vo trung")),
    ("patient_proof", ("khach hang", "hanh trinh", "chia se", "truoc sau", "before", "after")),
    ("pain_problem", ("dau", "so", "mat rang", "an nhai", "tu ti", "hoi mieng")),
    ("education_transparency", ("giai thich", "chi dinh", "dieu kien", "rui ro", "gioi han", "phu hop")),
)

CTA_WORDS = ("dang ky", "dat lich", "inbox", "nhan tin", "goi ngay", "de lai so", "tu van")


def analyze_market_campaigns(
    ads: list[dict],
    focus_keyword: str,
    configured_competitor_pages: int,
    scan_target: int,
) -> dict[str, Any]:
    normalized_ads = [ad for ad in ads if str(ad.get("ad_text", "")).strip()]
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for ad in normalized_ads:
        text = f"{ad.get('page_name', '')} {ad.get('ad_text', '')}"
        service = _classify(text, SERVICE_RULES, "general")
        angle = _classify(text, ANGLE_RULES, "general_promotion")
        funnel = _funnel_stage(text, angle)
        page = str(ad.get("page_name") or "Không xác định").strip()
        grouped[(page, service, angle, funnel)].append(ad)

    campaigns = [
        _campaign_summary(key, campaign_ads)
        for key, campaign_ads in grouped.items()
    ]
    campaigns.sort(key=lambda item: (item["market_pressure_score"], item["ad_count"]), reverse=True)

    pages = _unique(str(ad.get("page_name") or "").strip() for ad in normalized_ads)
    configured_observed = _unique(
        str(ad.get("source_page_id") or "").strip()
        for ad in normalized_ads
        if str(ad.get("source_page_id") or "").strip()
    )
    discovered_pages = _unique(
        str(ad.get("page_name") or "").strip()
        for ad in normalized_ads
        if ad.get("source_type") == "keyword_scan" and str(ad.get("page_name") or "").strip()
    )
    coverage_score = _coverage_score(
        len(normalized_ads), scan_target, len(configured_observed), configured_competitor_pages
    )
    coverage = {
        "scan_target": scan_target,
        "ads_observed": len(normalized_ads),
        "unique_pages": len(pages),
        "configured_competitor_pages": configured_competitor_pages,
        "configured_pages_observed": len(configured_observed),
        "discovered_pages": len(discovered_pages),
        "campaigns_detected": len(campaigns),
        "coverage_score": coverage_score,
        "coverage_level": "high" if coverage_score >= 75 else "medium" if coverage_score >= 45 else "low",
        "limitation": (
            "Độ phủ là mẫu quảng cáo công khai quan sát được tại thời điểm quét; không bảo đảm toàn bộ quảng cáo "
            "của mọi nha khoa và không có dữ liệu chi tiêu, lead hay doanh thu đối thủ."
        ),
    }
    patterns = _market_patterns(campaigns)
    opportunities, selected_opportunity = _market_opportunities(focus_keyword, campaigns, patterns)
    if coverage_score < 45 or not campaigns:
        selected_opportunity = None
    return {
        "coverage": coverage,
        "campaigns": campaigns,
        "market_patterns": patterns,
        "opportunities": opportunities,
        "selected_opportunity": selected_opportunity,
    }


def build_revenue_strategy(
    focus_keyword: str,
    market_intelligence: dict,
    business_economics: dict | None = None,
) -> dict[str, Any]:
    economics = business_economics or {}
    required = (
        "average_case_value",
        "gross_margin_rate",
        "qualified_lead_to_booking_rate",
        "booking_show_rate",
        "consultation_close_rate",
        "max_acquisition_share_of_gross_profit",
    )
    ratio_fields = set(required) - {"average_case_value"}
    missing = [field for field in required if not _is_positive_number(economics.get(field))]
    invalid = [
        field
        for field in ratio_fields
        if field not in missing and float(economics[field]) > 1
    ]
    unit_economics: dict[str, int | float] = {}
    if not missing and not invalid:
        gross_profit = float(economics["average_case_value"]) * float(economics["gross_margin_rate"])
        max_case_cac = gross_profit * float(economics["max_acquisition_share_of_gross_profit"])
        lead_to_case = (
            float(economics["qualified_lead_to_booking_rate"])
            * float(economics["booking_show_rate"])
            * float(economics["consultation_close_rate"])
        )
        unit_economics = {
            "gross_profit_per_case": round(gross_profit),
            "max_cost_per_acquired_case": round(max_case_cac),
            "qualified_lead_to_case_rate": round(lead_to_case, 4),
            "max_cost_per_qualified_lead": round(max_case_cac * lead_to_case),
        }

    opportunity = market_intelligence.get("selected_opportunity") or {}
    market_evidence_status = "sufficient" if opportunity else "insufficient_market_evidence"
    return {
        "objective": f"Tạo thêm ca điều trị có biên lợi nhuận phù hợp cho '{focus_keyword}', không tối ưu lead rác.",
        "primary_conversion": "Lịch tư vấn đủ điều kiện đã xác nhận",
        "selected_opportunity": opportunity,
        "market_evidence_status": market_evidence_status,
        "offer_architecture": [
            "Bước 1: sàng lọc nhu cầu và tình trạng qua hội thoại ngắn, không báo giá gây hiểu lầm.",
            "Bước 2: lịch tư vấn có phim chụp/đánh giá phù hợp và giải thích lựa chọn.",
            "Bước 3: kế hoạch điều trị, chi phí và phương án thanh toán minh bạch sau thăm khám.",
        ],
        "funnel": [
            {"stage": "Demand", "goal": "Thu hút đúng người đang có nhu cầu", "metric": "Qualified conversation rate"},
            {"stage": "Qualification", "goal": "Loại lead không phù hợp", "metric": "Qualified lead rate"},
            {"stage": "Booking", "goal": "Xác nhận lịch tư vấn", "metric": "Cost per confirmed consultation"},
            {"stage": "Show", "goal": "Khách đến đúng lịch", "metric": "Show rate"},
            {"stage": "Treatment", "goal": "Chốt ca phù hợp", "metric": "Case acceptance rate và gross profit"},
        ],
        "economics_status": "ready" if not missing and not invalid else "needs_business_inputs",
        "required_business_inputs": list(dict.fromkeys([*missing, *invalid])),
        "invalid_business_inputs": invalid,
        "unit_economics": unit_economics,
        "scale_rules": [
            "Chỉ tăng ngân sách cho tuyến tạo lịch tư vấn đủ điều kiện và có tỷ lệ đến khám ổn định.",
            "So sánh cost per acquired case với lợi nhuận gộp mỗi ca; không scale theo lượt xem hoặc inbox thô.",
            "Giữ một nhóm đối chứng để phân biệt tăng trưởng thật với nhu cầu tự nhiên.",
        ],
        "stop_rules": [
            "Dừng creative nếu tạo nhiều lead nhưng không tạo lịch xác nhận sau một chu kỳ đánh giá.",
            "Dừng audience/offer nếu tỷ lệ đến khám hoặc tỷ lệ chốt thấp hơn ngưỡng kinh tế đã phê duyệt.",
            "Không tiếp tục ưu đãi khi chi phí thu hút vượt phần lợi nhuận gộp được phép dùng để mua khách.",
        ],
        "revenue_caveat": (
            "Đây là chiến lược hướng tới doanh thu, không phải cam kết doanh thu. Dự phóng tiền chỉ hợp lệ khi SmileUp "
            "cung cấp giá trị ca, biên lợi nhuận, tỷ lệ đặt lịch, đến khám và chốt điều trị thực tế."
        ),
    }


def _campaign_summary(key: tuple[str, str, str, str], ads: list[dict]) -> dict[str, Any]:
    page, service, angle, funnel = key
    messages = _unique(str(ad.get("ad_text") or "").strip() for ad in ads)[:3]
    source_ad_ids = _unique(str(ad.get("library_id") or "").strip() for ad in ads)
    avg_similarity = sum(float(ad.get("similarity", 0) or 0) for ad in ads) / max(1, len(ads))
    media_count = sum(1 for ad in ads if ad.get("media_urls"))
    pressure = min(100, round(20 + len(ads) * 14 + avg_similarity * 25 + min(media_count, 3) * 4))
    combined = _fold(" ".join(messages))
    strengths = [
        "Thông điệp lặp lại đủ để nhận diện một campaign." if len(ads) > 1 else "Thông điệp tập trung vào một nhu cầu rõ.",
        f"Có CTA trực tiếp ở tầng {funnel}." if any(word in combined for word in CTA_WORDS) else "Góc tiếp cận dễ nhận biết.",
    ]
    weaknesses = [
        "Dễ phụ thuộc ưu đãi và làm giảm khác biệt thương hiệu." if angle == "price_offer" else "Chưa chứng minh hiệu quả kinh doanh từ dữ liệu công khai.",
        "Mẫu quan sát còn mỏng, cần theo dõi thêm." if len(ads) == 1 else "Tần suất xuất hiện không đồng nghĩa với tỷ lệ chuyển đổi.",
    ]
    identity = hashlib.sha1("|".join(key).encode("utf-8")).hexdigest()[:10].upper()
    return {
        "campaign_id": f"CMP-{identity}",
        "page_name": page,
        "service_line": service,
        "angle": angle,
        "funnel_stage": funnel,
        "ad_count": len(ads),
        "media_count": media_count,
        "average_similarity": round(avg_similarity, 3),
        "started_running": _unique(str(ad.get("started_running") or "").strip() for ad in ads)[:3],
        "source_ad_ids": source_ad_ids,
        "representative_messages": messages,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "market_pressure_score": pressure,
    }


def _market_patterns(campaigns: list[dict]) -> dict[str, Any]:
    service_counts = Counter(campaign["service_line"] for campaign in campaigns)
    angle_counts = Counter(campaign["angle"] for campaign in campaigns)
    funnel_counts = Counter(campaign["funnel_stage"] for campaign in campaigns)
    return {
        "dominant_services": _ranked_counts(service_counts),
        "dominant_angles": _ranked_counts(angle_counts),
        "funnel_distribution": _ranked_counts(funnel_counts),
        "price_led_share": round(angle_counts.get("price_offer", 0) / max(1, len(campaigns)), 3),
    }


def _market_opportunities(
    focus_keyword: str, campaigns: list[dict], patterns: dict
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    focus_service = _classify(focus_keyword, SERVICE_RULES, "general")
    service_campaigns = [item for item in campaigns if item["service_line"] == focus_service]
    angle_counts = Counter(item["angle"] for item in service_campaigns)
    dominant_angle = angle_counts.most_common(1)[0][0] if angle_counts else "chưa đủ dữ liệu"
    observed_pages = _unique(item["page_name"] for item in service_campaigns)
    evidence = (
        f"Quan sát {len(service_campaigns)} campaign {focus_service} từ {len(observed_pages)} page; "
        f"góc xuất hiện nhiều nhất: {dominant_angle}."
    )
    opportunities: list[dict[str, Any]] = [
        {
            "name": "SmileUp Decision Clinic - Hiểu đúng rồi hãy chọn",
            "service_line": focus_service,
            "strategic_gap": "Chiếm khoảng trống tư vấn ra quyết định minh bạch thay vì cạnh tranh bằng giảm giá hoặc lời hứa kết quả.",
            "evidence": evidence,
            "differentiation": "Bác sĩ giải thích chỉ định, giới hạn, lựa chọn và chi phí sau thăm khám bằng một hệ nội dung nhất quán.",
            "revenue_role": "Tăng tỷ lệ lead đủ điều kiện, lịch tư vấn xác nhận và khả năng chấp nhận kế hoạch điều trị.",
        },
        {
            "name": "Proof of Process",
            "service_line": focus_service,
            "strategic_gap": "Biến quy trình thăm khám thật thành bằng chứng tin cậy thay cho social proof khó kiểm chứng.",
            "evidence": f"Phân bố funnel quan sát được: {patterns.get('funnel_distribution', [])}.",
            "differentiation": "Cho khách thấy cách SmileUp đánh giá và loại trừ trường hợp không phù hợp.",
            "revenue_role": "Giảm lead tò mò và tăng tỷ lệ đến khám của khách có nhu cầu thật.",
        },
        {
            "name": "Objection-to-Consultation",
            "service_line": focus_service,
            "strategic_gap": "Dùng các rào cản đau, thời gian, chi phí và rủi ro để dẫn đến tư vấn đủ điều kiện.",
            "evidence": f"Tỷ trọng campaign dẫn bằng giá quan sát được: {patterns.get('price_led_share', 0):.0%}.",
            "differentiation": "Trả lời thẳng điều khách lo nhưng không dùng nỗi sợ hoặc báo giá thiếu bối cảnh.",
            "revenue_role": "Tăng booking từ nhóm đang cân nhắc và giảm thất thoát ở giữa funnel.",
        },
    ]
    price_share = float(patterns.get("price_led_share", 0) or 0)
    funnel_counts = {item["name"]: int(item["count"]) for item in patterns.get("funnel_distribution", [])}
    conversion_share = funnel_counts.get("conversion", 0) / max(1, sum(funnel_counts.values()))
    if price_share >= 0.25:
        selected_index = 0
        reason = f"{price_share:.0%} campaign quan sát được dẫn bằng giá; SmileUp cần khác biệt bằng tư vấn minh bạch."
    elif conversion_share < 0.34:
        selected_index = 2
        reason = f"Chỉ {conversion_share:.0%} campaign quan sát được ở tầng conversion; cần nối phản đối của khách tới lịch tư vấn."
    else:
        selected_index = 1
        reason = "Thị trường đã có CTA nhưng thiếu bằng chứng quy trình đủ khác biệt cho SmileUp."
    opportunities[selected_index]["selection_reason"] = reason
    opportunities[selected_index]["opportunity_score"] = 100
    return opportunities, opportunities[selected_index]


def _funnel_stage(text: str, angle: str) -> str:
    folded = _fold(text)
    if any(word in folded for word in CTA_WORDS) or angle == "price_offer":
        return "conversion"
    if angle in {"doctor_authority", "technology_process", "education_transparency", "patient_proof"}:
        return "consideration"
    return "awareness"


def _classify(text: str, rules: tuple, fallback: str) -> str:
    folded = _fold(text)
    for label, keywords in rules:
        if any(keyword in folded for keyword in keywords):
            return label
    return fallback


def _coverage_score(ads: int, target: int, observed_pages: int, configured_pages: int) -> int:
    ad_score = min(1.0, ads / max(1, target)) * 60
    if configured_pages <= 0 or observed_pages <= 0:
        return min(44, round(ad_score))
    page_score = min(1.0, observed_pages / max(1, configured_pages)) * 40
    return round(ad_score + page_score)


def _is_positive_number(value: Any) -> bool:
    try:
        return float(value or 0) > 0
    except (TypeError, ValueError):
        return False


def _ranked_counts(counter: Counter) -> list[dict[str, int | str]]:
    return [{"name": name, "count": count} for name, count in counter.most_common()]


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", str(value or "").lower())
    ascii_text = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", ascii_text).strip()


def _unique(items) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
