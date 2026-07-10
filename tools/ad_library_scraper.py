from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

from tools.summarizer import extract_topics, summarize_text


ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "ad_library_cache.json"
CACHE_VERSION = 7
HIGH_MATCH_THRESHOLD = 0.95
PAGE_WAIT_SECONDS = float(os.getenv("AD_LIBRARY_PAGE_WAIT_SECONDS", "8"))
PAGE_LOAD_TIMEOUT_SECONDS = float(os.getenv("AD_LIBRARY_PAGE_LOAD_TIMEOUT_SECONDS", "25"))
KEYWORD_QUERY_LIMIT = int(os.getenv("AD_LIBRARY_KEYWORD_QUERY_LIMIT", "3"))
SCROLL_ATTEMPTS = int(os.getenv("AD_LIBRARY_SCROLL_ATTEMPTS", "8"))
SCROLL_WAIT_SECONDS = float(os.getenv("AD_LIBRARY_SCROLL_WAIT_SECONDS", "2.2"))


@dataclass
class AdLibraryAd:
    library_id: str
    ad_url: str
    page_name: str
    started_running: str
    ad_text: str
    media_urls: list[str]
    score: int
    similarity: float
    recency_score: float
    sort_score: float
    started_timestamp: float
    source_type: str = "keyword_scan"
    source_page_id: str = ""
    source_weight: float = 0.2


def collect_ad_library_ads(
    keywords: str,
    country: str = "VN",
    max_ads: int = 12,
    cache_ttl_hours: float = 24,
    force_refresh: bool = False,
    competitor_urls: list[str] | None = None,
    competitor_ratio: float = 0.8,
) -> list[dict]:
    competitor_urls = [url.strip() for url in competitor_urls or [] if url.strip()]
    competitor_ratio = min(1.0, max(0.0, competitor_ratio))
    cache_key = _cache_key(keywords, country, max_ads, competitor_urls, competitor_ratio)
    cached = _read_cache(cache_key, cache_ttl_hours)
    if cached is not None and not force_refresh and len(cached) >= max_ads:
        return cached[:max_ads]

    if competitor_urls:
        ads = _collect_weighted_ads(keywords, country, max_ads, competitor_urls, competitor_ratio)
    else:
        ads = _dedupe_ads(_scrape_ad_library(keywords=keywords, country=country, max_ads=max_ads))
        if len(ads) < max_ads:
            raise RuntimeError(
                f"Ad Library live scan did not return enough ads (need {max_ads} keyword ads; got {len(ads)}). "
                "Fallback is disabled by configuration, so the workflow is stopped instead of using synthetic benchmark ads."
            )

    _write_cache(cache_key, keywords, country, ads, competitor_urls, competitor_ratio)
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


def filter_high_match_ads(ads: list[dict], threshold: float = HIGH_MATCH_THRESHOLD) -> list[dict]:
    high_match = [ad for ad in ads if float(ad.get("similarity", 0) or 0) >= threshold]
    return sorted(
        high_match,
        key=lambda ad: (
            float(ad.get("similarity", 0) or 0),
            float(ad.get("started_timestamp", 0) or 0),
            float(ad.get("sort_score", 0) or 0),
        ),
        reverse=True,
    )


def build_ad_library_report(
    ads: list[dict],
    keywords: str,
    high_match_ads: list[dict] | None = None,
    threshold: float = HIGH_MATCH_THRESHOLD,
    competitor_urls: list[str] | None = None,
    competitor_ratio: float = 0.8,
) -> str:
    if not ads:
        return f"Ad Library Agent: Không tìm được quảng cáo phù hợp cho keyword '{keywords}'."

    high_match_ads = high_match_ads if high_match_ads is not None else filter_high_match_ads(ads, threshold)
    competitor_count = sum(1 for ad in ads if ad.get("source_type") == "competitor_page")
    keyword_count = sum(1 for ad in ads if ad.get("source_type") == "keyword_scan")
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
    source_line = (
        f"- Tỷ trọng nguồn: {competitor_count}/{len(ads)} ads từ page đối thủ ưu tiên "
        f"(mục tiêu {round(competitor_ratio * 100)}%), {keyword_count}/{len(ads)} ads từ keyword scan mở rộng.\n"
        if competitor_urls
        else "- Tỷ trọng nguồn: chỉ dùng keyword scan mở rộng vì chưa cấu hình page đối thủ ưu tiên.\n"
    )
    return (
        "Ad Library Agent:\n"
        f"- Keyword quét mở rộng: {keywords}.\n"
        f"- Page đối thủ ưu tiên: {len(competitor_urls or [])} page.\n"
        f"- Số quảng cáo lấy vào workflow: {len(ads)}.\n"
        + source_line
        + f"- Ads đủ điều kiện cho tuyến bài ads hiệu quả: {len(high_match_ads)} ads có keyword match từ {round(threshold * 100)}% trở lên.\n"
        "- Thuật toán chọn: ưu tiên đúng page đối thủ trước, sau đó lọc theo độ giống keyword, ngày chạy mới nhất và tín hiệu nha khoa.\n"
        f"- Page nổi bật: {', '.join(pages[:8])}.\n"
        f"- Mẫu hook/copy: {sample or 'Chưa có copy đủ rõ.'}\n"
        "- Nguồn này phản ánh quảng cáo công khai trong Meta Ad Library, không phải toàn bộ bài organic của Page."
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


def extract_page_ids(urls: list[str]) -> list[str]:
    page_ids: list[str] = []
    for url in urls:
        query = parse_qs(urlparse(url).query)
        page_id = (query.get("view_all_page_id") or [""])[0].strip()
        if page_id and page_id not in page_ids:
            page_ids.append(page_id)
    return page_ids


def _collect_weighted_ads(
    keywords: str,
    country: str,
    max_ads: int,
    competitor_urls: list[str],
    competitor_ratio: float,
) -> list[dict]:
    competitor_target = min(max_ads, max(1, math.ceil(max_ads * competitor_ratio)))
    keyword_target = max(0, max_ads - competitor_target)

    competitor_ads = (
        _scrape_competitor_page_ads(
            urls=competitor_urls,
            keywords=keywords,
            max_ads=max(competitor_target * 3, competitor_target + len(competitor_urls)),
        )
        if competitor_target
        else []
    )
    keyword_ads = _collect_keyword_scan_ads(
        keywords=keywords,
        country=country,
        max_ads=max(keyword_target * 4, keyword_target, 4),
    ) if keyword_target else []

    competitor_ranked = _rank_ads(competitor_ads)
    keyword_ranked = _rank_ads(keyword_ads)
    selected: list[dict] = []
    seen: set[str] = set()
    _append_unique_ads(selected, seen, competitor_ranked, competitor_target)
    _append_unique_ads(selected, seen, keyword_ranked, keyword_target)

    competitor_count = sum(1 for ad in selected if ad.get("source_type") == "competitor_page")
    keyword_count = sum(1 for ad in selected if ad.get("source_type") == "keyword_scan")
    if competitor_count < competitor_target or keyword_count < keyword_target or len(selected) < max_ads:
        raise RuntimeError(
            "Ad Library live scan did not return enough ads "
            f"(need {competitor_target} competitor + {keyword_target} keyword = {max_ads}; "
            f"got {competitor_count} competitor + {keyword_count} keyword = {len(selected)}). "
            "Fallback is disabled by configuration, so the workflow is stopped instead of using synthetic benchmark ads."
        )

    return selected[:max_ads]


def _collect_keyword_scan_ads(keywords: str, country: str, max_ads: int) -> list[dict]:
    queries = _keyword_scan_queries(keywords)[: max(1, KEYWORD_QUERY_LIMIT)]
    collected: list[dict] = []
    for query in queries:
        if len(collected) >= max_ads:
            break
        try:
            collected.extend(
                _scrape_ad_library(
                    keywords=query,
                    country=country,
                    max_ads=max(max_ads - len(collected), 4),
                )
            )
            collected = _dedupe_ads(collected)
        except Exception:
            if query == queries[0]:
                raise
    return _dedupe_ads(collected)[:max_ads]


def _keyword_scan_queries(keywords: str) -> list[str]:
    base = str(keywords or "").strip()
    return [base] if base else []


def _scrape_ad_library(keywords: str, country: str, max_ads: int) -> list[dict]:
    url = (
        "https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country={quote(country)}&media_type=all"
        f"&q={quote(keywords)}&search_type=keyword_unordered"
    )
    return _scrape_ad_library_url(url, keywords, max_ads, source_type="keyword_scan", source_weight=0.2)


def _scrape_competitor_page_ads(urls: list[str], keywords: str, max_ads: int) -> list[dict]:
    page_ids = extract_page_ids(urls)
    if not page_ids:
        return []

    per_page_limit = max(2, math.ceil(max_ads / len(page_ids)) + 1)
    specs = [
        {
            "url": _page_ad_library_url(page_id),
            "max_ads": per_page_limit,
            "source_type": "competitor_page",
            "source_page_id": page_id,
            "source_weight": 0.8,
        }
        for page_id in page_ids
    ]
    return _dedupe_ads(_scrape_ad_library_urls(specs, keywords, stop_after=max_ads))


def _scrape_ad_library_url(
    url: str,
    keywords: str,
    max_ads: int,
    source_type: str,
    source_page_id: str = "",
    source_weight: float = 0.2,
) -> list[dict]:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
    except Exception as exc:
        raise RuntimeError("selenium is required for Ad Library scraping") from exc

    driver = webdriver.Chrome(options=_chrome_options())
    try:
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT_SECONDS)
        driver.implicitly_wait(3)
        driver.get(url)
        return _collect_ads_from_current_page(driver, keywords, max_ads, source_type, source_page_id, source_weight, By)
    finally:
        driver.quit()


def _scrape_ad_library_urls(specs: list[dict], keywords: str, stop_after: int) -> list[dict]:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
    except Exception as exc:
        raise RuntimeError("selenium is required for Ad Library scraping") from exc

    ads: list[dict] = []
    driver = webdriver.Chrome(options=_chrome_options())
    try:
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT_SECONDS)
        driver.implicitly_wait(3)
        for spec in specs:
            driver.get(str(spec["url"]))
            page_ads = _collect_ads_from_current_page(
                driver,
                keywords,
                int(spec.get("max_ads") or stop_after),
                str(spec.get("source_type") or "keyword_scan"),
                str(spec.get("source_page_id") or ""),
                float(spec.get("source_weight") or 0.2),
                By,
            )
            ads.extend(page_ads)
            ads = _dedupe_ads(ads)
            if len(ads) >= stop_after:
                break
        return ads[:stop_after]
    finally:
        driver.quit()


def _collect_ads_from_current_page(
    driver,
    keywords: str,
    max_ads: int,
    source_type: str,
    source_page_id: str,
    source_weight: float,
    by,
) -> list[dict]:
    ads: list[dict] = []
    last_height = 0
    stagnant_rounds = 0
    time.sleep(PAGE_WAIT_SECONDS)
    for _attempt in range(max(1, SCROLL_ATTEMPTS)):
        body = driver.find_element(by.TAG_NAME, "body").text
        media_urls = _extract_media_urls(driver)
        ads = _dedupe_ads(
            ads
            + _parse_ad_cards(
                body,
                media_urls,
                keywords,
                source_type,
                source_page_id,
                source_weight,
            )
        )
        if len(ads) >= max_ads:
            return ads[:max_ads]

        height = int(driver.execute_script("return document.body.scrollHeight || 0") or 0)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_WAIT_SECONDS)
        if height <= last_height:
            stagnant_rounds += 1
        else:
            stagnant_rounds = 0
        last_height = max(last_height, height)
        if stagnant_rounds >= 2:
            break
    return ads[:max_ads]


def _chrome_options():
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.page_load_strategy = "eager"
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--window-size=1440,1800")
    options.add_argument("--lang=vi-VN")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125 Safari/537.36"
    )
    return options


def _parse_ad_cards(
    body: str,
    media_urls: list[str],
    keywords: str,
    source_type: str = "keyword_scan",
    source_page_id: str = "",
    source_weight: float = 0.2,
) -> list[dict]:
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
        dedupe_key = library_id or f"{page_name}:{ad_text[:220]}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        full_text = "\n".join(lines)
        score = _dental_score(full_text)
        similarity = _keyword_similarity(keywords, f"{page_name}\n{ad_text}")
        started_timestamp = _started_timestamp(started)
        recency_score = _recency_score(started_timestamp)
        sort_score = round(similarity * 0.62 + recency_score * 0.23 + min(score / 20, 1) * 0.15, 4)
        if score <= 0 or not ad_text or similarity <= 0:
            continue
        card_media = media_urls[media_index : media_index + 2]
        media_index += 2
        ads.append(
            AdLibraryAd(
                library_id=library_id,
                ad_url=_ad_library_url(library_id),
                page_name=page_name,
                started_running=started,
                ad_text=ad_text,
                media_urls=card_media,
                score=score,
                similarity=similarity,
                recency_score=recency_score,
                sort_score=sort_score,
                started_timestamp=started_timestamp,
                source_type=source_type,
                source_page_id=source_page_id,
                source_weight=source_weight,
            )
        )
    return _rank_ads([asdict(ad) for ad in ads])


def _page_name_from_lines(lines: list[str]) -> str:
    for sponsor_word in ("Sponsored", "Được tài trợ"):
        if sponsor_word in lines:
            index = lines.index(sponsor_word)
            if index > 0:
                return lines[index - 1]
    return "Meta Ad Library"


def _ad_library_url(library_id: str) -> str:
    if not library_id:
        return "https://www.facebook.com/ads/library/"
    return f"https://www.facebook.com/ads/library/?id={library_id}"


def _page_ad_library_url(page_id: str) -> str:
    params = {
        "active_status": "active",
        "ad_type": "all",
        "country": "ALL",
        "is_targeted_country": "false",
        "media_type": "all",
        "search_type": "page",
        "sort_data[mode]": "total_impressions",
        "sort_data[direction]": "desc",
        "source": "page-transparency-widget",
        "view_all_page_id": page_id,
    }
    return "https://www.facebook.com/ads/library/?" + urlencode(params)


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
    normalized = _normalize_vietnamese(text)
    terms = (
        "nha khoa",
        "rang",
        "rang su",
        "implant",
        "nieng",
        "boc",
        "trong rang",
        "cay ghep",
        "mat rang",
        "nu cuoi",
        "phuc hinh",
        "tham my",
    )
    return sum(normalized.count(term) for term in terms)


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
    normalized = value.casefold().replace("đ", "d").replace("Đ", "d")
    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s,.;|/]+", " ", normalized)).strip()


def _started_timestamp(started: str) -> float:
    text = started.strip()
    if not text:
        return 0.0
    date_text = text
    for pattern in (r"Started running on\s+(.+)", r"Bắt đầu chạy vào\s+(.+)"):
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


def _rank_ads(ads: list[dict]) -> list[dict]:
    return sorted(
        ads,
        key=lambda ad: (
            float(ad.get("source_weight", 0) or 0),
            float(ad.get("similarity", 0) or 0),
            float(ad.get("started_timestamp", 0) or 0),
            float(ad.get("sort_score", 0) or 0),
            int(ad.get("score", 0) or 0),
        ),
        reverse=True,
    )


def _dedupe_ads(ads: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for ad in ads:
        key = _ad_identity(ad)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ad)
    return deduped


def _append_unique_ads(
    selected: list[dict],
    seen: set[str],
    candidates: list[dict],
    target_count: int,
) -> None:
    added = 0
    for ad in candidates:
        key = _ad_identity(ad)
        if key in seen:
            continue
        seen.add(key)
        selected.append(ad)
        added += 1
        if added >= target_count:
            return


def _ad_identity(ad: dict) -> str:
    library_id = str(ad.get("library_id") or "").strip()
    return library_id or f"{ad.get('page_name', '')}:{str(ad.get('ad_text', ''))[:220]}"


def _cache_key(
    keywords: str,
    country: str,
    max_ads: int,
    competitor_urls: list[str],
    competitor_ratio: float,
) -> str:
    payload = {
        "version": CACHE_VERSION,
        "keywords": keywords,
        "country": country,
        "max_ads": max_ads,
        "competitor_urls": competitor_urls,
        "competitor_ratio": competitor_ratio,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _read_cache(cache_key: str, ttl_hours: float) -> list[dict] | None:
    if not CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("version") != CACHE_VERSION or payload.get("cache_key") != cache_key:
        return None
    created_at = float(payload.get("created_at", 0) or 0)
    if time.time() - created_at > ttl_hours * 3600:
        return None
    ads = payload.get("ads")
    return ads if isinstance(ads, list) else None


def _write_cache(
    cache_key: str,
    keywords: str,
    country: str,
    ads: list[dict],
    competitor_urls: list[str],
    competitor_ratio: float,
) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_VERSION,
        "cache_key": cache_key,
        "created_at": time.time(),
        "keywords": keywords,
        "country": country,
        "competitor_urls": competitor_urls,
        "competitor_ratio": competitor_ratio,
        "ads": ads,
    }
    CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
