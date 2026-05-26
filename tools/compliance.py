RISKY_CLAIMS = [
    "100%",
    "vĩnh viễn",
    "không đau hoàn toàn",
    "không đau",
    "đẹp ngay lập tức",
    "số 1",
    "duy nhất",
    "rẻ nhất",
    "chắc chắn khỏi",
    "cam kết khỏi",
    "bảo đảm thành công",
]


def compliance_flags(draft: dict) -> list[str]:
    text = " ".join(str(draft.get(key, "")) for key in ("title", "body", "call_to_action")).lower()
    return [claim for claim in RISKY_CLAIMS if claim.lower() in text]


def build_compliance_report(draft: dict | None) -> str:
    if not draft:
        return "Compliance Agent: Chưa có bản nháp để kiểm tra."

    flags = compliance_flags(draft)
    if flags:
        return (
            "Compliance Agent:\n"
            f"- Phát hiện claim rủi ro: {', '.join(flags)}.\n"
            "- Cần sửa trước khi duyệt: tránh cam kết tuyệt đối, tránh khẳng định kết quả chắc chắn, thêm lưu ý cần bác sĩ thăm khám."
        )

    return (
        "Compliance Agent:\n"
        "- Không phát hiện claim tuyệt đối trong tiêu đề, nội dung và CTA.\n"
        "- Bài có thể chuyển sang Manager Agent nếu đã có CTA, lợi ích rõ và lưu ý kết quả tùy tình trạng răng."
    )
