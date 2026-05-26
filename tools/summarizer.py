import re


def summarize_text(text: str, max_words: int = 34) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    words = cleaned.split()
    if len(words) <= max_words:
        return cleaned
    return " ".join(words[:max_words]).rstrip(".,") + "..."


def extract_topics(text: str) -> list[str]:
    mapping = {
        "tay_trang_rang": ["tẩy trắng", "trắng răng"],
        "nieng_rang": ["niềng", "invisalign", "trong suốt"],
        "implant": ["implant", "trồng răng"],
        "cham_soc_dinh_ky": ["khám định kỳ", "sâu răng", "viêm nướu"],
        "uu_dai": ["ưu đãi", "khuyến mãi", "miễn phí"],
    }
    lowered = text.lower()
    topics = [topic for topic, needles in mapping.items() if any(needle in lowered for needle in needles)]
    return topics or ["nha_khoa_tong_quat"]
