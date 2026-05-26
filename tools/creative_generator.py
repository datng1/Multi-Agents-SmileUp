from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from textwrap import wrap

from graph.state import ContentVariant

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


def generate_creative_assets(variants: list[ContentVariant]) -> list[dict[str, str]]:
    if not variants or Image is None:
        return []

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, str]] = []
    stamp = datetime.now().strftime("%Y%m%d")
    for index, variant in enumerate(variants, start=1):
        filename = f"{stamp}_{index:02d}_{_slugify(variant.get('service_line') or variant.get('title') or 'creative')}.png"
        output_path = OUTPUT_DIR / filename
        _render_creative(variant, output_path, index)
        url_path = f"/generated/creatives/{filename}"
        variant["image_path"] = url_path
        assets.append(
            {
                "service_line": variant.get("service_line", ""),
                "title": variant.get("title", ""),
                "image_path": url_path,
                "image_prompt": variant.get("image_prompt", ""),
            }
        )
    return assets


def _render_creative(variant: ContentVariant, output_path: Path, index: int) -> None:
    width, height = 1080, 1350
    canvas = _background(width, height)
    draw = ImageDraw.Draw(canvas)

    title_font = _font(54, bold=True)
    body_font = _font(34)
    small_font = _font(26, bold=True)
    micro_font = _font(22)

    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, 0, width, height), fill=(245, 251, 250, 206))
    overlay_draw.rectangle((0, 910, width, height), fill=(12, 98, 91, 228))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)

    _draw_logo(canvas)

    service = (variant.get("service_line") or "SmileUp Dental").upper()
    angle = variant.get("angle") or "Tu van ca nhan hoa"
    title = variant.get("title") or "SmileUp Dental Clinic"
    differentiation = variant.get("differentiation") or "Khac biet bang tu van dung chi dinh, minh bach va an toan."
    cta = variant.get("call_to_action") or "Inbox SmileUp de dat lich tu van."

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

    canvas.convert("RGB").save(output_path, quality=95)


def _background(width: int, height: int):
    if BACKGROUND_PATH.exists():
        image = Image.open(BACKGROUND_PATH).convert("RGB")
        scale = max(width / image.width, height / image.height)
        image = image.resize((int(image.width * scale), int(image.height * scale)))
        left = (image.width - width) // 2
        top = (image.height - height) // 2
        image = image.crop((left, top, left + width, top + height))
        image = image.filter(ImageFilter.GaussianBlur(2.4))
        image = ImageEnhance.Color(image).enhance(0.82)
        image = ImageEnhance.Brightness(image).enhance(1.08)
        return image
    return Image.new("RGB", (width, height), (244, 249, 249))


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


def _font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
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
