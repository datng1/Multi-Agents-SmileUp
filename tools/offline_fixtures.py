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
