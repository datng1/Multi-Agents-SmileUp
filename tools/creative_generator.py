from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
import math
import re
from datetime import datetime
from pathlib import Path
from textwrap import wrap

from graph.state import ContentVariant
from tools.openai_image_reference import generate_smileup_reference_image
from utils import config

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat
except Exception:  # pragma: no cover - optional runtime dependency
    Image = None
    ImageDraw = None
    ImageEnhance = None
    ImageFilter = None
    ImageFont = None
    ImageStat = None


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
ASSET_DIR = WEB_ROOT / "assets"
OUTPUT_DIR = WEB_ROOT / "generated" / "creatives"
BACKGROUND_PATH = ASSET_DIR / "clinic-overview.png"
LOGO_PATH = ASSET_DIR / "smileup-logo.jfif"


def generate_creative_assets(variants: list[ContentVariant], context: dict | None = None) -> list[dict[str, str]]:
    context = context or {}
    image_mode = str(context.get("creative_image_mode") or "auto")

    if not variants:
        return []

    if image_mode == "top_match_reference" and Image is None:
        raise RuntimeError("GPT Image output requires Pillow to normalize Facebook images and overlay the SmileUp logo.")

    if Image is None:
        return []

    if image_mode == "text_only":
        return []

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, str]] = []
    seed_suffix = _slugify(str(context.get("run_seed") or datetime.now().strftime("%H%M%S%f")))[:10]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    selected_variants = _build_creative_image_requests(variants)
    if image_mode == "top_match_reference" and not config.MOCK_MODE:
        return _generate_top_match_assets(selected_variants, context, stamp, seed_suffix, image_mode)

    for index, variant in selected_variants:
        filename = _creative_filename(stamp, seed_suffix, index, variant)
        output_path = OUTPUT_DIR / filename
        image_model_note = ""
        if _is_page_care_asset(variant):
            _render_page_care_infographic(variant, output_path, index, context)
            image_model_note = "Rendered locally as a SmileUp page-care infographic for speed and Vietnamese text accuracy."
        elif image_mode == "top_match_reference":
            if config.MOCK_MODE:
                _render_creative(variant, output_path, index, context)
                image_model_note = "MOCK_MODE: GPT Image 2 generation simulated for workflow tests."
            else:
                generated, blueprint, image_model_note = generate_smileup_reference_image(variant, context, output_path)
                if blueprint:
                    context["creative_reference_blueprint"] = blueprint
                context["creative_generation_note"] = image_model_note
                if generated:
                    _normalize_generated_image(output_path, variant)
                else:
                    raise RuntimeError(image_model_note or "GPT Image 2 did not return a usable image.")
        else:
            _render_creative(variant, output_path, index, context)
        url_path = f"/generated/creatives/{filename}"
        variant["image_path"] = url_path
        source_policy = _source_policy(image_mode)
        reference_ad = context.get("creative_reference_ad") or {}
        assets.append(
            {
                "campaign_track": variant.get("campaign_track", ""),
                "service_line": variant.get("service_line", ""),
                "title": variant.get("title", ""),
                "image_path": url_path,
                "image_prompt": variant.get("image_prompt", ""),
                "image_mode": image_mode,
                "source_image_url": str(context.get("creative_upload_url") or reference_ad.get("media_url") or ""),
                "reference_ad_url": str(reference_ad.get("ad_url") or ""),
                "reference_page_name": str(reference_ad.get("page_name") or ""),
                "image_model_note": image_model_note,
                "openai_image_note": image_model_note,
                "openai_generated": bool(image_mode == "top_match_reference" and image_model_note),
                "source_policy": source_policy,
                "creative_group": str(variant.get("creative_group") or ""),
                "audience_segment": str(variant.get("audience_segment") or ""),
                "album_default": bool(variant.get("album_default")),
            }
        )
    return assets


def _generate_top_match_assets(
    selected_variants: list[tuple[int, ContentVariant]],
    context: dict,
    stamp: str,
    seed_suffix: str,
    image_mode: str,
) -> list[dict[str, str]]:
    if not selected_variants:
        return []

    max_workers = min(3, len(selected_variants), max(1, config.OPENAI_IMAGE_PHOTO_CREATIVES))
    assets_by_index: dict[int, dict[str, str]] = {}
    errors: list[str] = []
    photo_requests = [(index, variant) for index, variant in selected_variants if not _is_page_care_asset(variant)]
    page_care_requests = [(index, variant) for index, variant in selected_variants if _is_page_care_asset(variant)]

    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = {
        executor.submit(_generate_one_top_match_asset, index, variant, context, stamp, seed_suffix, image_mode): index
        for index, variant in photo_requests
    }
    pending = set(futures)
    deadline = datetime.now().timestamp() + max(90, config.OPENAI_IMAGE_REQUEST_TIMEOUT_SECONDS + 35)
    try:
        while pending and datetime.now().timestamp() < deadline:
            done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
            for future in done:
                index = futures[future]
                try:
                    asset = future.result()
                    assets_by_index[index] = asset
                except Exception as exc:
                    errors.append(f"creative #{index}: {exc}")
    finally:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

    for index, variant in photo_requests:
        if index in assets_by_index:
            continue
        errors.append(f"creative #{index}: GPT Image timed out; local fallback used")
        assets_by_index[index] = _generate_local_fallback_asset(index, variant, context, stamp, seed_suffix, image_mode)

    for index, variant in page_care_requests:
        assets_by_index[index] = _generate_page_care_asset(index, variant, context, stamp, seed_suffix, image_mode)

    assets = [assets_by_index[index] for index, _ in selected_variants if index in assets_by_index]
    if errors:
        context["creative_generation_note"] = " | ".join(errors[:4])
    return assets


def _generate_one_top_match_asset(
    index: int,
    variant: ContentVariant,
    context: dict,
    stamp: str,
    seed_suffix: str,
    image_mode: str,
) -> dict[str, str]:
    filename = _creative_filename(stamp, seed_suffix, index, variant)
    output_path = OUTPUT_DIR / filename
    local_context = deepcopy(context)
    generated, blueprint, image_model_note = generate_smileup_reference_image(variant, local_context, output_path)
    if not generated:
        raise RuntimeError(image_model_note or "GPT Image 2 did not return a usable image.")
    _normalize_generated_image(output_path, variant)
    url_path = f"/generated/creatives/{filename}"
    variant["image_path"] = url_path
    reference_ad = local_context.get("creative_reference_ad") or {}
    return _asset_payload(
        variant=variant,
        image_mode=image_mode,
        url_path=url_path,
        source_policy=_source_policy(image_mode),
        reference_ad=reference_ad,
        image_model_note=image_model_note,
    )


def _asset_payload(
    variant: ContentVariant,
    image_mode: str,
    url_path: str,
    source_policy: str,
    reference_ad: dict,
    image_model_note: str,
) -> dict[str, str]:
    return {
        "campaign_track": variant.get("campaign_track", ""),
        "service_line": variant.get("service_line", ""),
        "title": variant.get("title", ""),
        "image_path": url_path,
        "image_prompt": variant.get("image_prompt", ""),
        "image_mode": image_mode,
        "source_image_url": str(reference_ad.get("media_url") or ""),
        "reference_ad_url": str(reference_ad.get("ad_url") or ""),
        "reference_page_name": str(reference_ad.get("page_name") or ""),
        "image_model_note": image_model_note,
        "openai_image_note": image_model_note,
        "openai_generated": bool(image_mode == "top_match_reference" and image_model_note),
        "source_policy": source_policy,
        "creative_group": str(variant.get("creative_group") or ""),
        "audience_segment": str(variant.get("audience_segment") or ""),
        "album_default": bool(variant.get("album_default")),
    }


def _build_creative_image_requests(variants: list[ContentVariant]) -> list[tuple[int, ContentVariant]]:
    if config.OPENAI_IMAGE_MAX_CREATIVES <= 0:
        return []
    ranked = [
        item[1]
        for item in sorted(
        enumerate(variants, start=1),
        key=lambda item: (
            0 if item[1].get("campaign_track") == "ads_effective" else 1,
            _service_priority(str(item[1].get("service_line") or "")),
            item[0],
        ),
        )
    ]
    if not ranked:
        return []
    requests: list[tuple[int, ContentVariant]] = []
    index = 1
    photo_slots = min(6, config.OPENAI_IMAGE_PHOTO_CREATIVES, config.OPENAI_IMAGE_MAX_CREATIVES)
    group_specs = [
        ("ads_young", "Khách hàng trẻ 24-35 tuổi, phong cách hiện đại, quan tâm thẩm mỹ nụ cười và quyết định nhanh sau tư vấn rõ ràng.", 3),
        ("ads_middle", "Khách hàng trung tuổi 42-60 tuổi, ưu tiên ăn nhai, phục hình, implant, an toàn và kế hoạch điều trị minh bạch.", 3),
    ]
    for group, audience, count in group_specs:
        if photo_slots <= 0:
            break
        for offset in range(min(count, photo_slots)):
            base = deepcopy(ranked[offset % len(ranked)])
            base["creative_group"] = group
            base["audience_segment"] = audience
            base["album_default"] = group == "ads_young"
            base["image_prompt"] = _append_prompt_context(base.get("image_prompt", ""), audience)
            requests.append((index, base))
            index += 1
            photo_slots -= 1

    page_count = min(config.OPENAI_IMAGE_PAGE_CARE_CREATIVES, config.OPENAI_IMAGE_MAX_CREATIVES - len(requests))
    page_variants = [variant for variant in ranked if variant.get("campaign_track") == "page_care"] or ranked
    for offset in range(page_count):
        base = deepcopy(page_variants[offset % len(page_variants)])
        base["creative_group"] = "page_care"
        base["audience_segment"] = "Ảnh chăm sóc page: infographic/educational visual, đúng tiếng Việt, dễ lưu lại và tăng tương tác."
        base["album_default"] = False
        requests.append((index, base))
        index += 1
    return requests


def _append_prompt_context(prompt: str, addition: str) -> str:
    prompt = str(prompt or "").strip()
    return f"{prompt.rstrip('.')}. {addition}" if prompt else addition


def _service_priority(service_line: str) -> int:
    priorities = {
        "implant": 0,
        "rang_su": 1,
        "phuc_hinh_su": 2,
        "trust": 3,
        "reels": 4,
    }
    return priorities.get(service_line, 9)


def _creative_filename(stamp: str, seed_suffix: str, index: int, variant: ContentVariant) -> str:
    group = _slugify(str(variant.get("creative_group") or "creative"))[:18]
    subject = _slugify(str(variant.get("service_line") or variant.get("title") or "creative"))
    return f"{stamp}_{seed_suffix}_{index:02d}_{group}_{subject}.png"


def _is_page_care_asset(variant: ContentVariant) -> bool:
    return str(variant.get("creative_group") or "") == "page_care"


def _generate_local_fallback_asset(
    index: int,
    variant: ContentVariant,
    context: dict,
    stamp: str,
    seed_suffix: str,
    image_mode: str,
) -> dict[str, str]:
    filename = _creative_filename(stamp, seed_suffix, index, variant)
    output_path = OUTPUT_DIR / filename
    _render_creative(variant, output_path, index, context)
    url_path = f"/generated/creatives/{filename}"
    variant["image_path"] = url_path
    reference_ad = context.get("creative_reference_ad") or {}
    return _asset_payload(
        variant=variant,
        image_mode=image_mode,
        url_path=url_path,
        source_policy="GPT Image timeout fallback: SmileUp-owned local creative generated to keep the workflow moving.",
        reference_ad=reference_ad,
        image_model_note="GPT Image timed out; local fallback rendered.",
    )


def _generate_page_care_asset(
    index: int,
    variant: ContentVariant,
    context: dict,
    stamp: str,
    seed_suffix: str,
    image_mode: str,
) -> dict[str, str]:
    filename = _creative_filename(stamp, seed_suffix, index, variant)
    output_path = OUTPUT_DIR / filename
    _render_page_care_infographic(variant, output_path, index, context)
    url_path = f"/generated/creatives/{filename}"
    variant["image_path"] = url_path
    reference_ad = context.get("creative_reference_ad") or {}
    return _asset_payload(
        variant=variant,
        image_mode=image_mode,
        url_path=url_path,
        source_policy="SmileUp page-care infographic rendered locally for Vietnamese text accuracy and fast workflow completion.",
        reference_ad=reference_ad,
        image_model_note="Local page-care infographic rendered.",
    )


def _render_creative(variant: ContentVariant, output_path: Path, index: int, context: dict) -> None:
    width, height = 1080, 1350
    canvas = _background(width, height, {**context, "variant_index": index})
    draw = ImageDraw.Draw(canvas)

    title_font = _font(54, bold=True)
    body_font = _font(34)
    small_font = _font(26, bold=True)
    micro_font = _font(22)

    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    image_mode = str(context.get("creative_image_mode") or "auto")
    top_alpha = 46
    overlay_draw.rectangle((0, 0, width, height), fill=(245, 251, 250, top_alpha))
    if image_mode in {"layout_reference", "top_match_reference"}:
        overlay_draw.rounded_rectangle((640, 220, 1020, 850), radius=44, fill=(255, 255, 255, 82), outline=(15, 118, 110, 72), width=4)
        overlay_draw.ellipse((700, 280, 960, 540), fill=(232, 245, 242, 120), outline=(15, 118, 110, 60), width=3)
        overlay_draw.rounded_rectangle((690, 600, 970, 790), radius=34, fill=(230, 239, 238, 115))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)

    _draw_brand_overlay(canvas, variant)
    canvas.convert("RGB").save(output_path, quality=95)
    return

    service = (variant.get("service_line") or "SmileUp Dental").upper()
    angle = variant.get("angle") or "Tư vấn cá nhân hóa"
    title = variant.get("title") or "SmileUp Dental Clinic"
    differentiation = variant.get("differentiation") or "Khác biệt bằng tư vấn đúng chỉ định, minh bạch và an toàn."
    cta = variant.get("call_to_action") or "Inbox SmileUp để đặt lịch tư vấn."

    draw.rounded_rectangle((62, 168, 420, 218), radius=25, fill=(224, 248, 244, 255), outline=(15, 118, 110, 80), width=2)
    draw.text((84, 178), service[:30], fill=(15, 94, 88), font=small_font)

    y = 276
    for line in _wrap_text(title, 24, 4):
        draw.text((72, y), line, fill=(21, 31, 42), font=title_font)
        y += 64

    y += 26
    for line in _wrap_text(angle, 36, 3):
        draw.text((76, y), line, fill=(70, 84, 98), font=body_font)
        y += 44

    y = 956
    draw.text((72, y), "DIEM KHAC BIET CUA SMILEUP", fill=(184, 235, 226), font=micro_font)
    y += 42
    for line in _wrap_text(differentiation, 42, 4):
        draw.text((72, y), line, fill=(255, 255, 255), font=body_font)
        y += 45

    draw.rounded_rectangle((72, 1226, 1008, 1290), radius=32, fill=(255, 255, 255, 245))
    draw.text((106, 1243), _shorten(cta, 68), fill=(15, 94, 88), font=small_font)
    draw.text((920, 80), f"{index:02d}", fill=(15, 118, 110), font=title_font)
    if image_mode == "layout_reference":
        draw.text((706, 818), "NEW ORIGINAL VISUAL", fill=(15, 94, 88), font=micro_font)
    elif image_mode == "top_match_reference":
        draw.text((650, 818), "TOP MATCH INSPIRED - ORIGINAL", fill=(15, 94, 88), font=micro_font)
    elif image_mode == "owned":
        draw.text((706, 818), "SMILEUP PHOTO SOURCE", fill=(15, 94, 88), font=micro_font)

    canvas.convert("RGB").save(output_path, quality=95)


def _render_page_care_infographic(variant: ContentVariant, output_path: Path, index: int, context: dict) -> None:
    width, height = 1080, 1350
    seed_value = _seed_value({**context, "variant_index": index, "group": "page_care"})
    canvas = Image.new("RGBA", (width, height), (248, 253, 252, 255))
    draw = ImageDraw.Draw(canvas)
    title_font = _font(58, bold=True)
    subtitle_font = _font(30, bold=True)
    body_font = _font(26)
    small_font = _font(22, bold=True)
    blue = (0, 106, 157, 255)
    teal = (7, 118, 110, 255)
    navy = (20, 42, 67, 255)
    pale = (226, 246, 243, 255)

    if seed_value % 2:
        draw.pieslice((-240, -220, 520, 540), 0, 360, fill=(218, 245, 249, 255))
        draw.rounded_rectangle((76, 330, 1004, 1100), radius=38, fill=(255, 255, 255, 246), outline=(178, 219, 225, 255), width=2)
    else:
        draw.rounded_rectangle((0, 0, width, 335), radius=0, fill=(232, 247, 250, 255))
        draw.pieslice((660, -180, 1280, 440), 0, 360, fill=(205, 236, 242, 255))

    _draw_brand_overlay(canvas, {"title": variant.get("title", ""), "service_line": "page_care"})

    title = _clean_infographic_title(variant)
    y = 150 if seed_value % 2 else 154
    draw.text((72, y), "SMILEUP DENTAL CLINIC", fill=teal, font=small_font)
    y += 54
    for line in _wrap_text(title, 24, 3):
        draw.text((72, y), line, fill=navy, font=title_font)
        y += 70

    bullets = _infographic_bullets(variant)
    card_top = 470
    if len(bullets) <= 3:
        for item_index, bullet in enumerate(bullets, start=1):
            top = card_top + (item_index - 1) * 190
            draw.rounded_rectangle((84, top, 996, top + 142), radius=28, fill=(255, 255, 255, 255), outline=(198, 225, 229, 255), width=2)
            draw.ellipse((114, top + 32, 192, top + 110), fill=blue)
            draw.text((153, top + 71), str(item_index), fill=(255, 255, 255, 255), font=subtitle_font, anchor="mm")
            for line_no, line in enumerate(_wrap_text(bullet, 38, 2)):
                draw.text((222, top + 36 + line_no * 38), line, fill=navy if line_no == 0 else (70, 84, 98), font=subtitle_font if line_no == 0 else body_font)
    else:
        grid_top = 455
        for item_index, bullet in enumerate(bullets[:4], start=1):
            col = (item_index - 1) % 2
            row = (item_index - 1) // 2
            left = 72 + col * 520
            top = grid_top + row * 300
            draw.rounded_rectangle((left, top, left + 456, top + 250), radius=28, fill=(255, 255, 255, 255), outline=(198, 225, 229, 255), width=2)
            draw.ellipse((left + 24, top + 24, left + 90, top + 90), fill=teal)
            draw.text((left + 57, top + 57), str(item_index), fill=(255, 255, 255, 255), font=small_font, anchor="mm")
            for line_no, line in enumerate(_wrap_text(bullet, 22, 4)):
                draw.text((left + 108, top + 32 + line_no * 33), line, fill=navy if line_no == 0 else (70, 84, 98), font=body_font)

    footer_y = 1192
    draw.rounded_rectangle((90, footer_y, 990, footer_y + 86), radius=36, fill=teal)
    cta = _shorten(variant.get("call_to_action") or "Lưu lại và inbox SmileUp để được tư vấn cá nhân hóa.", 58)
    draw.text((540, footer_y + 43), cta, fill=(255, 255, 255, 255), font=subtitle_font, anchor="mm")
    canvas.convert("RGB").save(output_path, quality=95)


def _clean_infographic_title(variant: ContentVariant) -> str:
    title = str(variant.get("title") or variant.get("angle") or "Checklist chăm sóc răng miệng").strip()
    return _shorten(title, 72)


def _infographic_bullets(variant: ContentVariant) -> list[str]:
    text = " ".join(
        str(part or "")
        for part in [
            variant.get("body", ""),
            variant.get("differentiation", ""),
            variant.get("marketing_analysis", ""),
        ]
    )
    pieces = [item.strip(" -•\t\r\n.") for item in re.split(r"[.\n;]+", text) if len(item.strip()) > 18]
    defaults = [
        "Hỏi bác sĩ điều gì trước khi quyết định",
        "Kiểm tra tình trạng răng miệng thực tế",
        "Hiểu rõ thời gian, chi phí và giới hạn",
        "Lưu ý kết quả phụ thuộc từng người",
    ]
    bullets: list[str] = []
    for piece in pieces:
        if piece not in bullets:
            bullets.append(_shorten(piece, 86))
        if len(bullets) >= 4:
            break
    return bullets or defaults


def _background(width: int, height: int, context: dict):
    image_mode = str(context.get("creative_image_mode") or "auto")
    upload_path = Path(str(context.get("creative_upload_path") or ""))
    seed_value = _seed_value(context)
    if image_mode == "owned" and upload_path.exists():
        image = _crop_to_canvas(upload_path, width, height, seed_value)
        if image is not None:
            image = _vary_image_treatment(image, seed_value, blur=1.0)
            return image

    if BACKGROUND_PATH.exists():
        image = _crop_to_canvas(BACKGROUND_PATH, width, height, seed_value)
        if image is None:
            return Image.new("RGB", (width, height), (244, 249, 249))
        image = _vary_image_treatment(image, seed_value, blur=2.0)
        return image
    return Image.new("RGB", (width, height), (244, 249, 249))


def _crop_to_canvas(path: Path, width: int, height: int, seed_value: int = 0):
    try:
        image = Image.open(path).convert("RGB")
    except Exception:
        return None
    scale = max(width / image.width, height / image.height) * (1 + ((seed_value % 4) * 0.015))
    image = image.resize((int(image.width * scale), int(image.height * scale)))
    max_left = max(0, image.width - width)
    max_top = max(0, image.height - height)
    left = min(max_left, max(0, max_left // 2 + ((seed_value % 7) - 3) * max(8, max_left // 18)))
    top = min(max_top, max(0, max_top // 2 + (((seed_value // 7) % 7) - 3) * max(8, max_top // 18)))
    return image.crop((left, top, left + width, top + height))


def _vary_image_treatment(image, seed_value: int, blur: float):
    image = image.filter(ImageFilter.GaussianBlur(blur + (seed_value % 3) * 0.18))
    image = ImageEnhance.Color(image).enhance(0.78 + (seed_value % 5) * 0.035)
    image = ImageEnhance.Brightness(image).enhance(1.02 + ((seed_value // 5) % 5) * 0.018)
    image = ImageEnhance.Contrast(image).enhance(0.94 + ((seed_value // 11) % 5) * 0.025)
    if seed_value % 2:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return image


def _seed_value(context: dict) -> int:
    raw = f"{context.get('run_seed', '')}:{context.get('variant_index', '')}"
    return sum((index + 1) * ord(char) for index, char in enumerate(raw))


def _source_policy(image_mode: str) -> str:
    if image_mode == "owned":
        return "Uploaded SmileUp-owned/licensed photo used as the visual source; no text banner is added."
    if image_mode == "layout_reference":
        return "Layout reference only: original ad pixels, faces, logo, text, and assets are not reused."
    if image_mode == "top_match_reference":
        return "Top-match ad reference only: GPT Image creates a new SmileUp image without reusing source pixels, faces, logo, or original text; no text, banner, watermark, or typography is allowed."
    return "Auto-generated from SmileUp brand assets; no text banner is added."


def _draw_brand_overlay(canvas, variant: ContentVariant | None = None) -> None:
    if not LOGO_PATH.exists():
        return
    width, height = canvas.size
    seed = sum(ord(char) for char in str((variant or {}).get("title") or "smileup"))
    logo = _build_horizontal_logo(max_width=340)
    if logo is not None:
        left, margin_y = _choose_logo_position(canvas, logo, seed)
        _draw_soft_logo_plate(canvas, logo, left, margin_y)

    service_line = str((variant or {}).get("service_line") or "").lower()
    if _should_draw_watermark(service_line, seed):
        _draw_stamp_watermark(canvas, seed)


def _build_horizontal_logo(max_width: int = 340):
    if not LOGO_PATH.exists():
        return None
    mark = _extract_logo_mark()
    if mark is None:
        return None

    mark_size = 58
    gap = 13
    mark.thumbnail((mark_size, mark_size), Image.Resampling.LANCZOS)
    word_font = _brand_font(42)
    clinic_font = _font(11, bold=True)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1), (255, 255, 255, 0)))
    word_bbox = probe.textbbox((0, 0), "SMILEUP", font=word_font)
    clinic_bbox = probe.textbbox((0, 0), "DENTAL CLINIC", font=clinic_font)
    word_width = word_bbox[2] - word_bbox[0]
    clinic_width = clinic_bbox[2] - clinic_bbox[0]
    text_width = max(word_width, clinic_width + 84)
    text_left = mark_size + gap
    logo_width = text_left + text_width + 4
    logo_height = 72
    logo = Image.new("RGBA", (logo_width, logo_height), (255, 255, 255, 0))
    logo.alpha_composite(mark, (0, (logo_height - mark.height) // 2))

    draw = ImageDraw.Draw(logo)
    blue = (0, 106, 157, 245)
    dark = (15, 32, 44, 150)
    clinic_left = text_left + max(0, (word_width - clinic_width) // 2)
    line_y = 22
    draw.text((clinic_left, 7), "DENTAL CLINIC", fill=dark, font=clinic_font)
    draw.line((text_left, line_y, max(text_left, clinic_left - 10), line_y), fill=(15, 32, 44, 120), width=1)
    draw.line((clinic_left + clinic_width + 10, line_y, text_left + word_width, line_y), fill=(15, 32, 44, 120), width=1)
    draw.text((text_left, 25), "SMILEUP", fill=blue, font=word_font)
    bbox = logo.getbbox()
    logo = logo.crop(bbox) if bbox else logo
    if logo.width > max_width:
        ratio = max_width / logo.width
        logo = logo.resize((max_width, max(1, int(logo.height * ratio))), Image.Resampling.LANCZOS)
    return logo


def _extract_logo_mark():
    try:
        raw = Image.open(LOGO_PATH).convert("RGBA")
    except Exception:
        return None
    width, height = raw.size
    crop = raw.crop((0, 0, width, int(height * 0.52)))
    crop = _make_light_background_transparent(crop)
    bbox = crop.getbbox()
    if not bbox:
        return None
    return crop.crop(bbox)


def _make_light_background_transparent(image):
    image = image.convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if r > 235 and g > 235 and b > 235:
                pixels[x, y] = (r, g, b, 0)
            elif r > 220 and g > 220 and b > 220:
                pixels[x, y] = (r, g, b, int(a * 0.22))
    return image


def _choose_logo_position(canvas, logo, seed: int) -> tuple[int, int]:
    width, height = canvas.size
    pad_x, pad_y = 18, 12
    region_w = logo.width + pad_x * 2
    region_h = logo.height + pad_y * 2
    margin = 46
    candidates = [
        (margin, 38, 0),
        (width - region_w - margin, 38, 0),
        (margin, height - region_h - 122, 6),
        (width - region_w - margin, height - region_h - 122, 6),
    ]
    scored: list[tuple[float, int, int]] = []
    for left, top, lower_penalty in candidates:
        scan_left = max(0, left - 24)
        scan_top = max(0, top - 12)
        scan_right = min(width, left + region_w + 24)
        scan_bottom = min(height, top + region_h + 170)
        region = canvas.convert("RGB").crop((scan_left, scan_top, scan_right, scan_bottom))
        score = _logo_region_score(region) - lower_penalty
        if seed % 2:
            score += 0.6 if left > width // 2 else 0
        else:
            score += 0.6 if left < width // 2 else 0
        scored.append((score, left + pad_x, top + pad_y))
    _, best_left, best_top = max(scored, key=lambda item: item[0])
    return best_left, best_top


def _logo_region_score(region) -> float:
    luminance = _average_luminance(region)
    # Score a larger neighborhood, not only the exact logo plate. This helps avoid
    # placing the logo on top of existing wall signs, busy faces, or text-like detail.
    edges = region.filter(ImageFilter.FIND_EDGES).convert("L")
    edge_mean = ImageStat.Stat(edges).mean[0] if ImageStat is not None else 0
    contrast = max(ImageStat.Stat(region.convert("L")).stddev[0], 1) if ImageStat is not None else 1
    light_bonus = max(0, 60 - abs(luminance - 218)) / 6
    return light_bonus - edge_mean / 18 - contrast / 22


def _draw_soft_logo_plate(canvas, logo, left: int, top: int) -> None:
    crop = canvas.convert("RGB").crop((left, top, left + logo.width, top + logo.height))
    luminance = _average_luminance(crop)
    pad_x, pad_y = 16, 10
    plate_alpha = 192 if luminance < 170 else 76
    plate = Image.new("RGBA", (logo.width + pad_x * 2, logo.height + pad_y * 2), (255, 255, 255, 0))
    mask = Image.new("L", plate.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, plate.width, plate.height), radius=18, fill=plate_alpha)
    plate.putalpha(mask)
    canvas.alpha_composite(plate, (left - pad_x, top - pad_y))
    canvas.alpha_composite(logo, (left, top))


def _average_luminance(image) -> float:
    pixel = image.resize((1, 1), Image.Resampling.BILINEAR).getpixel((0, 0))
    return 0.2126 * pixel[0] + 0.7152 * pixel[1] + 0.0722 * pixel[2]


def _should_draw_watermark(service_line: str, seed: int) -> bool:
    if service_line in {"rang_su", "trust", "page_care"}:
        return True
    if service_line in {"implant", "phuc_hinh_su"}:
        return seed % 3 == 0
    return seed % 2 == 0


def _draw_stamp_watermark(canvas, seed: int) -> None:
    width, height = canvas.size
    size = 178
    x_choices = [int(width * 0.50), int(width * 0.58), int(width * 0.42)]
    y_choices = [int(height * 0.58), int(height * 0.64), int(height * 0.52)]
    center_x = x_choices[seed % len(x_choices)]
    center_y = y_choices[(seed // 3) % len(y_choices)]
    left = max(36, min(width - size - 36, center_x - size // 2))
    top = max(270, min(height - size - 230, center_y - size // 2))

    stamp = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(stamp)
    white = (255, 255, 255, 118)
    draw.ellipse((16, 16, size - 16, size - 16), outline=white, width=3)
    draw.ellipse((46, 46, size - 46, size - 46), outline=(255, 255, 255, 70), width=2)
    for tick in range(24):
        angle = math.radians(tick * 15)
        inner = 68 if tick % 2 else 64
        outer = 73
        x1 = size // 2 + math.cos(angle) * inner
        y1 = size // 2 + math.sin(angle) * inner
        x2 = size // 2 + math.cos(angle) * outer
        y2 = size // 2 + math.sin(angle) * outer
        draw.line((x1, y1, x2, y2), fill=(255, 255, 255, 86), width=2)

    mark = _extract_logo_mark()
    if mark is not None:
        mark = _tint_alpha(mark, (255, 255, 255), 132)
        mark.thumbnail((44, 44), Image.Resampling.LANCZOS)
        stamp.alpha_composite(mark, ((size - mark.width) // 2, 54))

    small_font = _font(12, bold=True)
    draw.text((size // 2, size // 2 + 26), "SMILEUP", fill=(255, 255, 255, 128), font=small_font, anchor="mm")
    canvas.alpha_composite(stamp, (left, top))


def _tint_alpha(image, color: tuple[int, int, int], alpha: int):
    mask = image.getchannel("A")
    tinted = Image.new("RGBA", image.size, (*color, 0))
    tinted.putalpha(mask.point(lambda value: min(alpha, value)))
    return tinted


def _brand_font(size: int):
    candidates = [
        "C:/Windows/Fonts/timesbd.ttf",
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return _font(size, bold=True)


def _normalize_generated_image(output_path: Path, variant: ContentVariant) -> None:
    try:
        image = Image.open(output_path).convert("RGBA")
    except Exception:
        return
    image = _fit_to_canvas(image, 1080, 1350).convert("RGBA")
    _draw_brand_overlay(image, variant)
    image.convert("RGB").save(output_path, quality=95)


def _draw_generated_text_overlay(canvas, variant: ContentVariant) -> None:
    draw = ImageDraw.Draw(canvas)
    title_font = _font(50, bold=True)
    cta_font = _font(30, bold=True)
    micro_font = _font(22, bold=True)

    top = Image.new("RGBA", (1080, 230), (7, 92, 86, 232))
    canvas.alpha_composite(top, (0, 0))
    draw.text((224, 46), "SMILEUP DENTAL CLINIC", fill=(196, 241, 235), font=micro_font)
    y = 78
    for line in _wrap_text(variant.get("title") or "SmileUp tư vấn nha khoa cá nhân hóa", 32, 2):
        draw.text((224, y), line, fill=(255, 255, 255), font=title_font)
        y += 58

    bottom = Image.new("RGBA", (1080, 122), (7, 92, 86, 238))
    canvas.alpha_composite(bottom, (0, 1228))
    cta = variant.get("call_to_action") or "Inbox SmileUp để được tư vấn trường hợp của bạn."
    draw.rounded_rectangle((52, 1250, 1028, 1320), radius=34, fill=(255, 255, 255, 245))
    draw.text((92, 1268), _shorten(cta, 62), fill=(7, 92, 86), font=cta_font)


def _fit_to_canvas(image, width: int, height: int):
    scale = max(width / image.width, height / image.height)
    resized = image.resize((int(image.width * scale), int(image.height * scale)))
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _wrap_text(text: str, width: int, max_lines: int) -> list[str]:
    lines = wrap(" ".join(str(text).split()), width=width)
    if len(lines) <= max_lines:
        return lines
    return lines[: max_lines - 1] + [_shorten(lines[max_lines - 1], width)]


def _shorten(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return normalized[:36] or "creative"
