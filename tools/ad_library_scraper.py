import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from tools.summarizer import extract_topics, summarize_text


ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "ad_library_cache.json"
CACHE_VERSION = 2


@dataclass
class AdLibraryAd:
    library_id: str
    page_name: str
    started_running: str
    ad_text: str
    media_urls: list[str]
    score: int
    similarity: float
    recency_score: float
    sort_score: float
    started_timestamp: float


def collect_ad_library_ads(
    keywords: str,
    country: str = "VN",
    max_ads: int = 12,
    cache_ttl_hours: float = 24,
    force_refresh: bool = False,
) -> list[dict]:
    cached = _read_cache(keywords, country, cache_ttl_hours)
    if cached is not None and not force_refresh:
        return cached[:max_ads]

    ads = _scrape_ad_library(keywords=keywords, country=country, max_ads=max_ads)
    _write_cache(keywords, country, ads)
    return ads[:max_ads]


def ads_to_competitor_insights(ads: list[dict]) -> list[dict]:
    insights = []
    for ad in ads:
        content = str(ad.get("ad_text", "")).strip()
        if not content:
            continue
        insights.append(
            {
                "page_name": str(ad.get("page_name") or "Meta Ad Library"),
                "post_content": content,
                "engagement": int(ad.get("score", 0) or 0),
                "summary": summarize_text(content, max_words=46),
                "key_topics": extract_topics(content),
            }
        )
    return insights


def build_ad_library_report(ads: list[dict], keywords: str) -> str:
    if not ads:
        return f"Ad Library Agent: Không tìm được quảng cáo phù hợp cho keyword '{keywords}'."

    pages = []
    for ad in ads:
        page = str(ad.get("page_name") or "").strip()
        if page and page not in pages:
            pages.append(page)
    sample = "; ".join(
        f"{ad.get('page_name', 'Unknown')} - {str(ad.get('ad_text', '')).splitlines()[0][:90]}"
        for ad in ads[:4]
        if str(ad.get("ad_text", "")).strip()
    )
    return (
        "Ad Library Agent:\n"
        f"- Keyword quét: {keywords}.\n"
        f"- Số quảng cáo lấy vào workflow: {len(ads)}.\n"
        "- Thuật toán chọn: ưu tiên ads có độ giống keyword cao và ngày chạy mới nhất.\n"
        f"- Page nổi bật: {', '.join(pages[:8])}.\n"
        f"- Mẫu hook/copy: {sample or 'Chưa có copy đủ rõ.'}\n"
        "- Nguồn này phản ánh quảng cáo trong Meta Ad Library, không phải toàn bộ bài organic của Page."
    )


def build_ad_visual_notes(ads: list[dict]) -> str:
    media_lines = []
    for ad in ads:
        urls = ad.get("media_urls") or []
        if urls:
            media_lines.append(f"{ad.get('page_name', 'Unknown')}: {len(urls)} media preview URL, ví dụ {urls[0]}")
    if not media_lines:
        return "Ad Library không trả media preview đủ rõ trong lần quét này."
    return "Media preview từ Ad Library:\n" + "\n".join(media_lines[:10])


def _scrape_ad_library(keywords: str, country: str, max_ads: int) -> list[dict]:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
    except Exception as exc:
        raise RuntimeError("selenium is required for Ad Library scraping") from exc

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1800")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125 Safari/537.36"
    )

    url = (
        "https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country={quote(country)}&media_type=all"
        f"&q={quote(keywords)}&search_type=keyword_unordered"
    )
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        time.sleep(12)
        body = driver.find_element(By.TAG_NAME, "body").text
        media_urls = _extract_media_urls(driver)
        ads = _parse_ad_cards(body, media_urls, keywords)
        return [asdict(ad) for ad in ads[:max_ads]]
    finally:
        driver.quit()


def _parse_ad_cards(body: str, media_urls: list[str], keywords: str) -> list[AdLibraryAd]:
    parts = re.split(r"(?=(?:Library ID|ID thư viện)[: ]+\d+)", body)
    ads: list[AdLibraryAd] = []
    media_index = 0
    seen: set[str] = set()
    for part in parts:
        if not re.match(r"(?:Library ID|ID thư viện)[: ]+\d+", part):
            continue
        lines = [line.strip() for line in part.splitlines() if line.strip()]
        if not lines:
            continue
        lib_match = re.search(r"(?:Library ID|ID thư viện)[: ]+(\d+)", lines[0])
        library_id = lib_match.group(1) if lib_match else ""
        page_name = _page_name_from_lines(lines)
        started = _started_from_lines(lines)
        ad_text = _ad_text_from_lines(lines)
        dedupe_key = f"{page_name}:{ad_text[:220]}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        full_text = "\n".join(lines)
        score = _dental_score(full_text)
        similarity = _keyword_similarity(keywords, f"{page_name}\n{ad_text}")
        started_timestamp = _started_timestamp(started)
        recency_score = _recency_score(started_timestamp)
        sort_score = round(similarity * 0.72 + recency_score * 0.28, 4)
        if score <= 0 or not ad_text or similarity <= 0:
            continue
        card_media = media_urls[media_index : media_index + 2]
        media_index += 2
        ads.append(
            AdLibraryAd(
                library_id=library_id,
                page_name=page_name,
                started_running=started,
                ad_text=ad_text,
                media_urls=card_media,
                score=score,
                similarity=similarity,
                recency_score=recency_score,
                sort_score=sort_score,
                started_timestamp=started_timestamp,
            )
        )
    return sorted(ads, key=lambda ad: (ad.sort_score, ad.started_timestamp, ad.score), reverse=True)


def _page_name_from_lines(lines: list[str]) -> str:
    for sponsor_word in ("Sponsored", "Được tài trợ"):
        if sponsor_word in lines:
            index = lines.index(sponsor_word)
            if index > 0:
                return lines[index - 1]
    return "Meta Ad Library"


def _started_from_lines(lines: list[str]) -> str:
    for line in lines[:8]:
        if "Started running" in line or "Bắt đầu chạy" in line:
            return line
    return ""


def _ad_text_from_lines(lines: list[str]) -> str:
    for sponsor_word in ("Sponsored", "Được tài trợ"):
        if sponsor_word in lines:
            start = lines.index(sponsor_word) + 1
            break
    else:
        start = 0

    stop_markers = {"Active", "Send message", "Visit profile", "Open Drop-down", "See ad details"}
    text_lines = []
    for line in lines[start:]:
        if line in stop_markers:
            break
        if re.match(r"^\d+:\d+\s*/\s*\d+:\d+$", line):
            continue
        text_lines.append(line)
    return "\n".join(text_lines).strip()


def _dental_score(text: str) -> int:
    return len(
        re.findall(
            r"nha\s*khoa|răng|rang|sứ|implant|niềng|bọc|trồng răng|cấy ghép|mất răng|nụ cười|phục hình",
            text,
            re.IGNORECASE,
        )
    )


def _keyword_similarity(keywords: str, text: str) -> float:
    query_terms = _keyword_terms(keywords)
    if not query_terms:
        return 0.0
    normalized_text = _normalize_vietnamese(text)
    matched = sum(1 for term in query_terms if term in normalized_text)
    phrase_bonus = 0.2 if _normalize_vietnamese(keywords) in normalized_text else 0.0
    density_bonus = min(0.25, sum(normalized_text.count(term) for term in query_terms) / max(len(query_terms) * 10, 1))
    return round(min(1.0, matched / len(query_terms) + phrase_bonus + density_bonus), 4)


def _keyword_terms(keywords: str) -> list[str]:
    normalized = _normalize_vietnamese(keywords)
    raw_terms = re.split(r"[\s,.;|/]+", normalized)
    stopwords = {"va", "voi", "cho", "cua", "the", "la", "de", "tu", "nhung"}
    terms = [term for term in raw_terms if len(term) >= 2 and term not in stopwords]
    phrases = [phrase.strip() for phrase in re.split(r"[,;|/]+", normalized) if len(phrase.strip()) >= 5]
    ordered = []
    for term in phrases + terms:
        if term and term not in ordered:
            ordered.append(term)
    return ordered


def _normalize_vietnamese(value: str) -> str:
    replacements = str.maketrans(
        {
            "à": "a", "á": "a", "ạ": "a", "ả": "a", "ã": "a", "â": "a", "ầ": "a", "ấ": "a", "ậ": "a", "ẩ": "a", "ẫ": "a", "ă": "a", "ằ": "a", "ắ": "a", "ặ": "a", "ẳ": "a", "ẵ": "a",
            "è": "e", "é": "e", "ẹ": "e", "ẻ": "e", "ẽ": "e", "ê": "e", "ề": "e", "ế": "e", "ệ": "e", "ể": "e", "ễ": "e",
            "ì": "i", "í": "i", "ị": "i", "ỉ": "i", "ĩ": "i",
            "ò": "o", "ó": "o", "ọ": "o", "ỏ": "o", "õ": "o", "ô": "o", "ồ": "o", "ố": "o", "ộ": "o", "ổ": "o", "ỗ": "o", "ơ": "o", "ờ": "o", "ớ": "o", "ợ": "o", "ở": "o", "ỡ": "o",
            "ù": "u", "ú": "u", "ụ": "u", "ủ": "u", "ũ": "u", "ư": "u", "ừ": "u", "ứ": "u", "ự": "u", "ử": "u", "ữ": "u",
            "ỳ": "y", "ý": "y", "ỵ": "y", "ỷ": "y", "ỹ": "y", "đ": "d",
        }
    )
    normalized = value.casefold().translate(replacements)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s,.;|/]+", " ", normalized)).strip()


def _started_timestamp(started: str) -> float:
    text = started.strip()
    if not text:
        return 0.0
    date_text = text
    for pattern in (r"Started running on\s+(.+)", r"Bắt đầu chạy vào\s+(.+)", r"Báº¯t Ä‘áº§u cháº¡y vào\s+(.+)"):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_text = match.group(1).strip()
            break
    for fmt in ("%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_text, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _recency_score(started_timestamp: float) -> float:
    if started_timestamp <= 0:
        return 0.0
    age_days = max(0.0, (time.time() - started_timestamp) / 86400)
    return round(1 / (1 + age_days / 45), 4)


def _extract_media_urls(driver) -> list[str]:
    urls = []
    for image in driver.find_elements("tag name", "img")[:240]:
        src = image.get_attribute("src") or ""
        if src and ("scontent" in src or "fbcdn" in src) and src not in urls:
            urls.append(src)
    return urls


def _read_cache(keywords: str, country: str, ttl_hours: float) -> list[dict] | None:
    if not CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("keywords") != keywords or payload.get("country") != country:
        return None
    if payload.get("version") != CACHE_VERSION:
        return None
    created_at = float(payload.get("created_at", 0) or 0)
    if time.time() - created_at > ttl_hours * 3600:
        return None
    ads = payload.get("ads")
    return ads if isinstance(ads, list) else None


def _write_cache(keywords: str, country: str, ads: list[dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": CACHE_VERSION, "created_at": time.time(), "keywords": keywords, "country": country, "ads": ads}
    CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
