from collections import Counter


TEXT_SIGNALS = {
    "pain_price": ["giá", "ưu đãi", "trả góp", "chi phí", "khuyến mãi"],
    "pain_fear": ["đau", "sợ", "ê buốt", "lo lắng", "biến chứng"],
    "trust_doctor": ["bác sĩ", "chuyên gia", "thăm khám", "phác đồ", "quy trình"],
    "service_crown": ["răng sứ", "bọc sứ", "thẩm mỹ", "nụ cười"],
    "service_implant": ["implant", "cấy ghép", "mất răng", "trồng răng", "ăn nhai"],
}

VISUAL_SIGNALS = {
    "doctor_consulting": ["bác sĩ", "tư vấn", "ghế nha", "phòng khám", "máy móc"],
    "patient_smile": ["nụ cười", "khách hàng", "before", "after", "chân dung"],
    "promo_overlay": ["ưu đãi", "giá", "trả góp", "hotline", "inbox"],
    "clinical_clean": ["sạch", "trắng", "xanh", "hiện đại", "vô khuẩn"],
}

VIDEO_SIGNALS = {
    "short_hook": ["3 giây", "hook", "mở đầu", "vấn đề", "câu hỏi"],
    "process": ["quy trình", "thăm khám", "chụp phim", "scan", "tư vấn"],
    "testimonial": ["khách hàng", "review", "cảm nhận", "trải nghiệm"],
    "doctor_talk": ["bác sĩ", "giải thích", "chỉ định", "phác đồ"],
}


def build_text_insight_report(insights: list[dict]) -> str:
    counter = Counter()
    hooks: list[str] = []
    for insight in insights:
        text = f"{insight.get('post_content', '')} {insight.get('summary', '')}".lower()
        for label, keywords in TEXT_SIGNALS.items():
            if any(keyword in text for keyword in keywords):
                counter[label] += 1
        summary = str(insight.get("summary", "")).strip()
        if summary:
            hooks.append(summary[:140])

    dominant = _format_counter(counter) or "trust_doctor, service_crown, service_implant"
    hook_examples = "; ".join(hooks[:3]) or "Chưa có caption đủ dài, cần nhập thêm nội dung bài viết để phân tích sâu."
    return (
        "Text Insight Agent:\n"
        f"- Tín hiệu caption nổi bật: {dominant}.\n"
        "- Nên ưu tiên hook đánh vào nỗi lo thật: sợ đau, sợ sai chỉ định, sợ giá cao, mất tự tin khi cười hoặc mất răng khó ăn nhai.\n"
        "- Với SmileUp, chuyển góc cạnh tranh sang tư vấn cá nhân hóa cho răng sứ và implant thay vì chạy ưu đãi chung chung.\n"
        f"- Hook/caption tham chiếu từ dữ liệu đầu vào: {hook_examples}"
    )


def build_visual_insight_report(visual_notes: str, visual_brief: str) -> str:
    text = visual_notes.lower()
    counter = Counter(
        label for label, keywords in VISUAL_SIGNALS.items() if any(keyword in text for keyword in keywords)
    )
    dominant = _format_counter(counter) or "doctor_consulting, clinical_clean, patient_smile"
    evidence = _shorten(visual_notes) or "Chưa có mô tả ảnh đối thủ; đang dùng visual brief an toàn mặc định."
    return (
        "Visual Insight Agent:\n"
        f"- Tín hiệu hình ảnh ghi nhận: {dominant}.\n"
        f"- Ghi chú ảnh/video frame đầu vào: {evidence}\n"
        "- Hướng đúng cho SmileUp: dùng ảnh gốc, ảnh có license hoặc ảnh AI mới; giữ cảm giác phòng khám thật, sạch, hiện đại, có bác sĩ tư vấn.\n"
        "- Nếu chọn rewrite ảnh, chỉ dùng ads đối thủ làm reference bố cục/hierarchy; ảnh SmileUp mới phải khác pixel, mặt, logo, text, nền và chi tiết nhận diện gốc.\n"
        f"- Brief nền hiện có: {_shorten(visual_brief, 260)}"
    )


def build_video_insight_report(video_notes: str) -> str:
    text = video_notes.lower()
    counter = Counter(
        label for label, keywords in VIDEO_SIGNALS.items() if any(keyword in text for keyword in keywords)
    )
    dominant = _format_counter(counter) or "short_hook, process, doctor_talk"
    evidence = _shorten(video_notes) or "Chưa có transcript/shot notes video; nên nhập transcript, cảnh mở đầu, CTA và comment nổi bật."
    return (
        "Video Insight Agent:\n"
        f"- Tín hiệu video/reel: {dominant}.\n"
        f"- Dữ liệu video đầu vào: {evidence}\n"
        "- Hướng reel nên test: mở đầu bằng câu hỏi 2-3 giây, bác sĩ giải thích ngắn, chèn 3 lợi ích dễ scan, cuối video CTA inbox để được tư vấn.\n"
        "- Với răng sứ: nhấn tự tin khi cười và thẩm mỹ tự nhiên. Với implant: nhấn ăn nhai, mất răng lâu năm và cần thăm khám đúng chỉ định."
    )


def build_strategic_direction(
    text_report: str,
    visual_report: str,
    video_report: str,
    trend_analysis: str,
) -> str:
    combined = " ".join([text_report, visual_report, video_report, trend_analysis]).lower()
    focus = "implant" if "implant" in combined or "mất răng" in combined else "răng sứ thẩm mỹ"
    secondary = "răng sứ thẩm mỹ" if focus == "implant" else "implant"
    return (
        "Strategic Direction Agent:\n"
        f"- Trụ cột chính nên triển khai hôm nay: {focus}; trụ cột phụ: {secondary}.\n"
        "- Góc nội dung: không sao chép đối thủ, dùng insight thị trường để viết lại theo lợi thế SmileUp: tư vấn rõ chỉ định, bác sĩ đồng hành, phòng khám hiện đại.\n"
        "- Công thức ưu tiên: Hook vấn đề thật -> checklist dấu hiệu cần đi khám -> giải pháp SmileUp -> lưu ý kết quả tùy tình trạng -> CTA inbox/đặt lịch.\n"
        "- Trend Facebook nên bám: caption ngắn đoạn, câu hỏi ở đầu bài, lợi ích dạng bullet, hình/video có mặt bác sĩ hoặc bối cảnh phòng khám, hashtag hẹp theo dịch vụ.\n"
        "- KPI nội dung: tăng inbox tư vấn, tăng lịch thăm khám, không chạy claim quá đà hoặc cam kết kết quả tuyệt đối."
    )


def _format_counter(counter: Counter) -> str:
    return ", ".join(label.replace("_", " ") for label, _ in counter.most_common(5))


def _shorten(value: str, limit: int = 320) -> str:
    cleaned = " ".join(str(value or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit - 3]}..."
