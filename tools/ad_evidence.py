from __future__ import annotations

from typing import Any


PRIORITY_REFERENCE_LIMIT = 12


def build_full_ad_evidence(
    ads: list[dict[str, Any]],
    *,
    focus_keyword: str,
    scan_id: str,
) -> dict[str, Any]:
    """Build a bounded packet that still contains one record for every scanned ad."""
    records = [_ad_record(ad, index) for index, ad in enumerate(ads, 1)]
    ranked = sorted(records, key=_reference_sort_key, reverse=True)
    priority = [
        {
            "evidence_id": item["evidence_id"],
            "library_id": item["library_id"],
            "page_name": item["page_name"],
            "similarity": item["similarity"],
            "selection_basis": _selection_basis(item),
        }
        for item in ranked[:PRIORITY_REFERENCE_LIMIT]
    ]
    return {
        "focus_keyword": focus_keyword,
        "scan_id": scan_id,
        "observed_ads_count": len(ads),
        "included_ads_count": len(records),
        "all_ads_included": len(records) == len(ads),
        "priority_reference_ads": priority,
        "priority_method": (
            "Xếp hạng proxy theo độ liên quan keyword, độ đầy đủ thông điệp và sự hiện diện media. "
            "Chỉ dùng để chọn mẫu học hỏi, không phải bằng chứng hiệu quả kinh doanh."
        ),
        "performance_caveat": (
            "Meta Ad Library không cung cấp lead, chi tiêu, doanh thu hay tỷ lệ chuyển đổi. Không được gọi các mẫu "
            "ưu tiên là quảng cáo thắng; chỉ được rút kinh nghiệm từ pattern quan sát được."
        ),
        "ads": records,
    }


def _ad_record(ad: dict[str, Any], index: int) -> dict[str, Any]:
    raw_text = str(ad.get("ad_text") or "").strip()
    media_urls = ad.get("media_urls") or []
    return {
        "evidence_id": f"AD-{index:03d}",
        "library_id": str(ad.get("library_id") or ""),
        "page_name": str(ad.get("page_name") or "Không xác định").strip(),
        "source_type": str(ad.get("source_type") or "unknown"),
        "similarity": round(float(ad.get("similarity", 0) or 0), 3),
        "started_running": str(ad.get("started_running") or ""),
        "has_media": bool(media_urls),
        "ad_text": raw_text,
        "text_truncated": False,
    }


def _reference_sort_key(item: dict[str, Any]) -> tuple[float, int, int, str]:
    return (
        float(item.get("similarity", 0) or 0),
        int(bool(item.get("has_media"))),
        min(len(str(item.get("ad_text") or "")), 600),
        str(item.get("evidence_id") or ""),
    )


def _selection_basis(item: dict[str, Any]) -> str:
    signals = [f"keyword match {float(item.get('similarity', 0) or 0):.0%}"]
    signals.append("có media" if item.get("has_media") else "text-only")
    signals.append(f"{len(str(item.get('ad_text') or ''))} ký tự thông điệp")
    return ", ".join(signals)
