from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import requests

from graph.state import ContentVariant
from utils import config


ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = ROOT / "web" / "assets" / "smileup-logo.jfif"


class GeminiImageUnavailable(RuntimeError):
    pass


def generate_smileup_reference_image(
    variant: ContentVariant,
    context: dict[str, Any],
    output_path: Path,
) -> tuple[bool, str, str]:
    """Generate a new SmileUp image from a top-match ad reference blueprint.

    The competitor media is used only to extract high-level composition notes.
    The generated output must not reuse source pixels, faces, logos, text, or
    distinctive assets from the reference.
    """

    if not config.GEMINI_API_KEY:
        return False, "", "Gemini image skipped: GEMINI_API_KEY missing."

    reference_ad = context.get("creative_reference_ad") or {}
    media_url = str(reference_ad.get("media_url") or "").strip()
    if not media_url:
        return False, "", "Gemini image skipped: top-match ad has no media URL."

    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        return False, "", f"Gemini image skipped: google-genai unavailable ({exc})."

    try:
        image_bytes, mime_type = _download_reference_image(media_url)
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        blueprint = _describe_reference_blueprint(client, types, image_bytes, mime_type, reference_ad)
        prompt = _build_generation_prompt(variant, reference_ad, blueprint)
        generated = _generate_image(client, types, prompt, image_bytes, mime_type)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(generated)
        return True, blueprint, "Gemini rewrote top-match ad image into a new SmileUp creative using reference-image mode."
    except Exception as exc:
        return False, "", f"Gemini image fallback: {exc}"


def _download_reference_image(media_url: str) -> tuple[bytes, str]:
    response = requests.get(
        media_url,
        timeout=15,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        mime_type = _guess_mime_type(media_url)
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise GeminiImageUnavailable(f"unsupported reference media type: {mime_type or 'unknown'}")
    image_bytes = response.content
    if not image_bytes or len(image_bytes) > 8 * 1024 * 1024:
        raise GeminiImageUnavailable("reference media is empty or over 8 MB")
    return image_bytes, mime_type


def _describe_reference_blueprint(client, types, image_bytes: bytes, mime_type: str, reference_ad: dict[str, Any]) -> str:
    prompt = (
        "Analyze this Facebook ad image only as a non-copyable creative blueprint. "
        "Return a concise Vietnamese description of the layout: aspect ratio, major zones, "
        "number/type of subjects, camera distance, color mood, text overlay placement, CTA placement, "
        "and visual hierarchy. Do not identify, preserve, or copy any logo, face, exact text, watermark, "
        "brand asset, or distinctive expression. The final image will be a new SmileUp dental clinic ad.\n\n"
        f"Ad copy context:\n{str(reference_ad.get('ad_text', ''))[:1200]}"
    )
    response = client.models.generate_content(
        model=_analysis_model(),
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
    )
    text = str(getattr(response, "text", "") or "").strip()
    if not text:
        raise GeminiImageUnavailable("Gemini returned no reference blueprint")
    return text[:1600]


def _generate_image(client, types, prompt: str, reference_image: bytes, reference_mime_type: str) -> bytes:
    errors: list[str] = []
    contents = _generation_contents(types, prompt, reference_image, reference_mime_type)
    for model in _image_model_candidates():
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="4:5"),
                ),
            )
            image_bytes = _extract_image_bytes(response)
            if image_bytes:
                return image_bytes
            errors.append(f"{model}: no inline image returned")
        except Exception as exc:
            errors.append(f"{model}: {exc}")
    raise GeminiImageUnavailable(" | ".join(errors[-3:]))


def _generation_contents(types, prompt: str, reference_image: bytes, reference_mime_type: str) -> list[Any]:
    contents: list[Any] = [
        types.Part.from_bytes(data=reference_image, mime_type=reference_mime_type),
    ]
    logo = _load_logo_reference()
    if logo:
        logo_bytes, logo_mime_type = logo
        contents.append(types.Part.from_bytes(data=logo_bytes, mime_type=logo_mime_type))
    contents.append(prompt)
    return contents


def _load_logo_reference() -> tuple[bytes, str] | None:
    if not LOGO_PATH.exists():
        return None
    data = LOGO_PATH.read_bytes()
    if not data or len(data) > 2 * 1024 * 1024:
        return None
    return data, _guess_mime_type(str(LOGO_PATH)) or "image/jpeg"


def _extract_image_bytes(response) -> bytes:
    parts = list(getattr(response, "parts", []) or [])
    if not parts:
        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts.extend(getattr(content, "parts", []) or [])

    for part in parts:
        inline_data = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
        data = getattr(inline_data, "data", None) if inline_data else None
        if isinstance(data, bytes):
            return data
        if data:
            import base64

            return base64.b64decode(data)

        as_image = getattr(part, "as_image", None)
        if callable(as_image):
            image = as_image()
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
    return b""


def _build_generation_prompt(variant: ContentVariant, reference_ad: dict[str, Any], blueprint: str) -> str:
    return f"""
Rewrite the first reference image into a completely new original 4:5 Facebook ad image for SmileUp Dental Clinic in Vietnam.
If a second reference image is attached, use it only for SmileUp logo/brand color guidance.

Use the first reference only as creative structure:
{blueprint}

Strict originality rules:
- Do not reproduce source pixels, exact text, logo, watermark, face, identity, clothing, background, or distinctive props from the competitor ad.
- Preserve only broad composition logic: subject count, relative placement, shot distance, visual hierarchy, and CTA/text zone placement.
- Replace all people with new Vietnamese dentist/patient subjects with different faces, different styling, different clothes, and different background details.
- Remove all competitor brand marks and rewrite any visible text into new SmileUp-safe Vietnamese wording.
- Use SmileUp-owned brand direction: clean modern dental clinic, white/teal palette, trustworthy, premium but warm.
- Add a clean SmileUp logo area at the top-left; local post-processing will overlay the actual logo.
- Avoid exaggerated medical claims, before/after claims, or guaranteed results.
- Make the image suitable for a Facebook dental marketing post about porcelain crowns, porcelain restoration, or implants.
- No watermark. No fake medical before/after. No body-shaming.

SmileUp post variant:
Service: {variant.get("service_line", "")}
Title overlay idea: {variant.get("title", "")}
Angle: {variant.get("angle", "")}
Differentiation: {variant.get("differentiation", "")}
CTA: {variant.get("call_to_action", "")}

Top-match ad context for strategy only, do not copy wording:
Page: {reference_ad.get("page_name", "")}
Ad text summary: {str(reference_ad.get("ad_text", ""))[:900]}
""".strip()


def _analysis_model() -> str:
    return config.GEMINI_FALLBACK_MODELS[-1] if config.GEMINI_FALLBACK_MODELS else "gemini-2.5-flash"


def _image_model_candidates() -> list[str]:
    candidates: list[str] = []
    for model in [config.GEMINI_IMAGE_MODEL, *config.GEMINI_IMAGE_FALLBACK_MODELS]:
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def _guess_mime_type(media_url: str) -> str:
    lower = media_url.lower().split("?", 1)[0]
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    return ""
