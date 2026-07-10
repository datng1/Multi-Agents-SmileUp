from collections import Counter


TREND_KEYWORDS = {
    "uu_dai": ["ưu đãi", "khuyến mãi", "miễn phí", "trả góp"],
    "tu_van": ["tư vấn", "thăm khám", "kiểm tra", "bác sĩ"],
    "tham_my": ["thẩm mỹ", "nụ cười", "tự tin", "trắng răng", "răng sứ"],
    "implant": ["implant", "cấy ghép", "mất răng", "trồng răng"],
    "video_reel": ["reel", "video", "livestream", "story"],
}


def analyze_facebook_trends(insights: list[dict]) -> str:
    topics = Counter()
    keyword_hits = Counter()
    hooks: list[str] = []

    for insight in insights:
        text = f"{insight.get('post_content', '')} {insight.get('summary', '')}".lower()
        for topic in insight.get("key_topics", []):
            topics[topic] += 1
        for label, keywords in TREND_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                keyword_hits[label] += 1
        summary = str(insight.get("summary", "")).strip()
        if summary:
            hooks.append(summary[:120])

    topic_line = _format_counter(topics) or "chăm sóc nha khoa cá nhân hóa"
    hit_line = _format_counter(keyword_hits) or "tư vấn, ưu đãi rõ điều kiện, hình ảnh phòng khám thật"
    hook_line = "; ".join(hooks[:3]) or "Dùng hook dạng câu hỏi, nêu vấn đề thật và CTA đặt lịch tư vấn."

    return (
        "Facebook trend analysis:\n"
        f"- Chủ đề đang lặp lại: {topic_line}.\n"
        f"- Tín hiệu dễ kéo tương tác: {hit_line}.\n"
        "- Góc triển khai nên ưu tiên: răng sứ thẩm mỹ và cấy ghép implant, dẫn bằng câu chuyện tự tin, ăn nhai, mất răng hoặc mong muốn cải thiện nụ cười.\n"
        "- Cấu trúc media: hook mạnh, 3 lợi ích dễ scan, bằng chứng/quy trình thăm khám, disclaimer và CTA intent.\n"
        "- Format: short video, carousel và ảnh gốc SmileUp; mỗi format phải có objective, audience và owner sản xuất.\n"
        f"- Hook tham khảo từ dữ liệu đầu vào: {hook_line}"
    )


def build_visual_creative_brief(insights: list[dict]) -> str:
    topic_text = " ".join(" ".join(insight.get("key_topics", [])) for insight in insights)
    service_focus = "cấy ghép implant" if "implant" in topic_text else "răng sứ thẩm mỹ và implant"
    return (
        "Visual creative brief an toàn:\n"
        f"- Chủ đề hình ảnh: {service_focus} tại SmileUp, cảm giác hiện đại, sạch, tin cậy.\n"
        "- Dùng ảnh gốc của SmileUp, ảnh tự chụp, ảnh có license, hoặc ảnh AI tạo mới. Không tái sử dụng/rebrand ảnh của đối thủ.\n"
        "- Bố cục bắt buộc: ảnh photorealistic có bác sĩ Việt Nam tư vấn bên ghế nha hoặc màn hình phim chụp, có bệnh nhân/khách hàng trong khung hình, ánh sáng trắng xanh nhẹ, logo SmileUp được gắn bằng post-process.\n"
        "- Hạn chế text overlay dài, poster chữ và layout trang trí; mọi chữ trên media phải nằm trong message matrix đã duyệt.\n"
        "- Tránh: before/after không có consent, claim 100%, phóng đại kết quả, dùng ảnh nhận diện phòng khám/khách hàng đối thủ."
    )


def _format_counter(counter: Counter) -> str:
    return ", ".join(label.replace("_", " ") for label, _ in counter.most_common(4))
