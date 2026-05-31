from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from textwrap import wrap

from graph.state import ContentVariant
from tools.gemini_image_reference import generate_smileup_reference_image

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
except Exception:  # pragma: no cover - optional runtime dependency
    Image = None
    ImageDraw = None
    ImageEnhance = None
    ImageFilter = None
    ImageFont = None


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
ASSET_DIR = WEB_ROOT / "assets"
OUTPUT_DIR = WEB_ROOT / "generated" / "creatives"
BACKGROUND_PATH = ASSET_DIR / "clinic-overview.png"
LOGO_PATH = ASSET_DIR / "smileup-logo.jfif"


def generate_creative_assets(variants: list[ContentVariant], context: dict | None = None) -> list[dict[str, str]]:
    if not variants or Image is None:
        return []

    context = context or {}
    if str(context.get("creative_image_mode") or "auto") == "text_only":
        return []

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, str]] = []
    stamp = datetime.now().strftime("%Y%m%d")
    for index, variant in enumerate(variants, start=1):
        filename = f"{stamp}_{index:02d}_{_slugify(variant.get('service_line') or variant.get('title') or 'creative')}.png"
        output_path = OUTPUT_DIR / filename
        image_mode = str(context.get("creative_image_mode") or "auto")
        gemini_note = ""
        if image_mode == "top_match_reference":
            generated, blueprint, gemini_note = generate_smileup_reference_image(variant, context, output_path)
            if blueprint:
                context["creative_reference_blueprint"] = blueprint
            context["creative_generation_note"] = gemini_note
            if generated:
                _normalize_generated_image(output_path, variant)
            else:
                continue
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
                "gemini_image_note": gemini_note,
                "gemini_generated": bool(image_mode == "top_match_reference" and gemini_note),
                "source_policy": source_policy,
            }
        )
    return assets


def _render_creative(variant: ContentVariant, output_path: Path, index: int, context: dict) -> None:
    width, height = 1080, 1350
    canvas = _background(width, height, context)
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

    _draw_logo(canvas)
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


def _background(width: int, height: int, context: dict):
    image_mode = str(context.get("creative_image_mode") or "auto")
    upload_path = Path(str(context.get("creative_upload_path") or ""))
    if image_mode == "owned" and upload_path.exists():
        image = _crop_to_canvas(upload_path, width, height)
        if image is not None:
            image = image.filter(ImageFilter.GaussianBlur(1.2))
            image = ImageEnhance.Color(image).enhance(0.9)
            image = ImageEnhance.Brightness(image).enhance(1.04)
            return image

    if BACKGROUND_PATH.exists():
        image = _crop_to_canvas(BACKGROUND_PATH, width, height)
        if image is None:
            return Image.new("RGB", (width, height), (244, 249, 249))
        image = image.filter(ImageFilter.GaussianBlur(2.4))
        image = ImageEnhance.Color(image).enhance(0.82)
        image = ImageEnhance.Brightness(image).enhance(1.08)
        return image
    return Image.new("RGB", (width, height), (244, 249, 249))


def _crop_to_canvas(path: Path, width: int, height: int):
    try:
        image = Image.open(path).convert("RGB")
    except Exception:
        return None
    scale = max(width / image.width, height / image.height)
    image = image.resize((int(image.width * scale), int(image.height * scale)))
    left = (image.width - width) // 2
    top = (image.height - height) // 2
    return image.crop((left, top, left + width, top + height))


def _source_policy(image_mode: str) -> str:
    if image_mode == "owned":
        return "Uploaded SmileUp-owned/licensed photo used as the visual source; no text banner is added."
    if image_mode == "layout_reference":
        return "Layout reference only: original ad pixels, faces, logo, text, and assets are not reused."
    if image_mode == "top_match_reference":
        return "Top-match ad reference only: Gemini creates a new SmileUp image without reusing source pixels, faces, logo, or original text; no text banner is added."
    return "Auto-generated from SmileUp brand assets; no text banner is added."


def _draw_logo(canvas) -> None:
    if not LOGO_PATH.exists():
        return
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo.thumbnail((112, 112))
    box = Image.new("RGBA", (142, 142), (255, 255, 255, 245))
    mask = Image.new("L", (142, 142), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, 142, 142), radius=18, fill=255)
    box.putalpha(mask)
    canvas.alpha_composite(box, (62, 56))
    canvas.alpha_composite(logo, (62 + (142 - logo.width) // 2, 56 + (142 - logo.height) // 2))


def _normalize_generated_image(output_path: Path, variant: ContentVariant) -> None:
    try:
        image = Image.open(output_path).convert("RGBA")
    except Exception:
        return
    image = _fit_to_canvas(image, 1080, 1350).convert("RGBA")
    _draw_logo(image)
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
