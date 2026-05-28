from graph.state import CompetitorInsight


MOCK_COMPETITOR_POSTS = [
    {
        "page_name": "Nha Khoa Smile Center",
        "message": "Gói tẩy trắng răng cuối tháng, tư vấn miễn phí và kiểm tra màu răng trước khi thực hiện.",
        "reactions": 128,
        "comments": 16,
        "shares": 9,
    },
    {
        "page_name": "Nha Khoa Gia Dinh",
        "message": "Niềng răng trong suốt đang được nhiều khách hàng văn phòng quan tâm vì tính thẩm mỹ.",
        "reactions": 94,
        "comments": 21,
        "shares": 5,
    },
    {
        "page_name": "Dental Care Plus",
        "message": "Khuyến khích khách hàng đặt lịch khám định kỳ 6 tháng để phòng ngừa sâu răng và viêm nướu.",
        "reactions": 76,
        "comments": 8,
        "shares": 12,
    },
]


FALLBACK_AD_LIBRARY_ADS = [
    {
        "library_id": "fallback-implant-001",
        "ad_url": "https://www.facebook.com/ads/library/",
        "page_name": "Fallback Dental Benchmark",
        "started_running": "Fallback benchmark",
        "ad_text": (
            "Mat rang lau ngay, an nhai kem va ngai chi phi? "
            "Dat lich tham kham de bac si danh gia phim chup, tinh trang xuong va tu van ke hoach Implant phu hop. "
            "Ket qua phu thuoc tinh trang rang mieng va can bac si tham kham truc tiep."
        ),
        "media_urls": [],
        "score": 9,
        "similarity": 1.0,
        "recency_score": 0.75,
        "sort_score": 0.93,
        "started_timestamp": 0.0,
    },
    {
        "library_id": "fallback-veneer-002",
        "ad_url": "https://www.facebook.com/ads/library/",
        "page_name": "Fallback Dental Benchmark",
        "started_running": "Fallback benchmark",
        "ad_text": (
            "Dang phan van co nen boc rang su? "
            "SmileUp uu tien tu van ca nhan hoa: khong phai ai cung can boc su, bac si can kiem tra men rang, khop can va muc tieu tham my truoc khi chi dinh. "
            "Inbox de duoc hen lich tu van truong hop cua ban."
        ),
        "media_urls": [],
        "score": 8,
        "similarity": 0.98,
        "recency_score": 0.72,
        "sort_score": 0.91,
        "started_timestamp": 0.0,
    },
    {
        "library_id": "fallback-pagecare-003",
        "ad_url": "https://www.facebook.com/ads/library/",
        "page_name": "Fallback Dental Benchmark",
        "started_running": "Fallback benchmark",
        "ad_text": (
            "Checklist truoc khi lam rang su: hoi ro co can mai rang khong, vat lieu nao phu hop, bao hanh ra sao, va rui ro nao can biet truoc. "
            "Noi dung cham soc page giup khach hang tu tin hon truoc khi inbox."
        ),
        "media_urls": [],
        "score": 7,
        "similarity": 0.96,
        "recency_score": 0.7,
        "sort_score": 0.89,
        "started_timestamp": 0.0,
    },
]


def mock_insights() -> list[CompetitorInsight]:
    return [
        {
            "page_name": post["page_name"],
            "post_content": post["message"],
            "engagement": int(post["reactions"] + post["comments"] + post["shares"]),
            "summary": post["message"],
            "key_topics": _topics_from_text(post["message"]),
        }
        for post in MOCK_COMPETITOR_POSTS
    ]


def fallback_ad_library_ads(keywords: str = "") -> list[dict]:
    ads = [dict(ad) for ad in FALLBACK_AD_LIBRARY_ADS]
    if keywords:
        for ad in ads:
            ad["ad_text"] = f"Keyword scan fallback: {keywords}\n{ad['ad_text']}"
    return ads


def _topics_from_text(text: str) -> list[str]:
    topics = []
    lowered = text.lower()
    if "tẩy trắng" in lowered:
        topics.append("tay_trang_rang")
    if "niềng" in lowered:
        topics.append("nieng_rang")
    if "khám định kỳ" in lowered or "sâu răng" in lowered:
        topics.append("cham_soc_dinh_ky")
    return topics or ["nha_khoa_tong_quat"]
