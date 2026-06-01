from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from graph.state import ContentVariant
from utils import config


class OpenAIImageUnavailable(RuntimeError):
    pass


def generate_smileup_reference_image(
    variant: ContentVariant,
    context: dict[str, Any],
    output_path: Path,
) -> tuple[bool, str, str]:
    """Generate a new SmileUp image with OpenAI GPT Image.

    Competitor media is only a loose reference for composition. The generated
    output must not reuse source pixels, faces, logos, text, or distinctive
    assets from the reference.
    """

    if not config.OPENAI_API_KEY:
        return False, "", "GPT Image skipped: OPENAI_API_KEY missing."

    reference_ad = context.get("creative_reference_ad") or {}
    media_urls = _reference_media_urls(reference_ad)
    try:
        image_bytes = b""
        mime_type = ""
        reference_note = "no reference image"
        if media_urls:
            try:
                image_bytes, mime_type, used_media_url = _download_first_reference_image(media_urls)
                reference_ad["media_url"] = used_media_url
                reference_note = "reference image used"
            except Exception as exc:
                reference_ad["media_url"] = ""
                reference_ad["media_download_error"] = str(exc)[:320]
                reference_note = "reference image unavailable; generated from campaign text"

        blueprint = _reference_blueprint(reference_ad, bool(image_bytes))
        prompt = _build_generation_prompt(variant, reference_ad, blueprint, context)
        generated, used_model = _edit_or_generate_image(prompt, image_bytes, mime_type)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(generated)
        return (
            True,
            blueprint,
            f"{used_model} generated a photorealistic text-free SmileUp dental image ({reference_note}); SmileUp logo is overlaid locally.",
        )
    except Exception as exc:
        return False, "", f"GPT Image fallback: {exc}"


def _reference_media_urls(reference_ad: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for raw_url in [reference_ad.get("media_url"), *(reference_ad.get("media_candidates") or [])]:
        url = str(raw_url or "").strip()
        if url and url not in urls:
            urls.append(url)
    return urls


def _download_first_reference_image(media_urls: list[str]) -> tuple[bytes, str, str]:
    errors: list[str] = []
    for media_url in media_urls:
        try:
            image_bytes, mime_type = _download_reference_image(media_url)
            return image_bytes, mime_type, media_url
        except Exception as exc:
            errors.append(f"{media_url[:80]}: {exc}")
    raise OpenAIImageUnavailable("no usable reference media after trying candidates: " + " | ".join(errors[-3:]))


def _download_reference_image(media_url: str) -> tuple[bytes, str]:
    response = requests.get(
        media_url,
        timeout=20,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        mime_type = _guess_mime_type(media_url)
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise OpenAIImageUnavailable(f"unsupported reference media type: {mime_type or 'unknown'}")
    image_bytes = response.content
    if not image_bytes or len(image_bytes) > 12 * 1024 * 1024:
        raise OpenAIImageUnavailable("reference media is empty or over 12 MB")
    return image_bytes, mime_type


def _edit_or_generate_image(prompt: str, reference_image: bytes, reference_mime_type: str) -> tuple[bytes, str]:
    errors: list[str] = []
    for model in _image_model_candidates():
        if reference_image:
            try:
                return _call_image_edit(prompt, reference_image, reference_mime_type, model), model
            except Exception as exc:
                errors.append(f"edit {model}: {_compact_error(exc)}")
        try:
            return _call_image_generation(prompt, model), model
        except Exception as exc:
            errors.append(f"generation {model}: {_compact_error(exc)}")
    raise OpenAIImageUnavailable(" | ".join(errors[-6:]))


def _call_image_edit(prompt: str, reference_image: bytes, reference_mime_type: str, model: str) -> bytes:
    response = requests.post(
        "https://api.openai.com/v1/images/edits",
        headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
        data={
            "model": model,
            "prompt": prompt,
            "size": "1024x1536",
            "quality": "high",
        },
        files={
            "image": (f"reference.{_extension_for_mime(reference_mime_type)}", reference_image, reference_mime_type),
        },
        timeout=180,
    )
    _raise_for_image_error(response)
    return _extract_image_bytes(response.json())


def _call_image_generation(prompt: str, model: str) -> bytes:
    response = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "prompt": prompt,
            "size": "1024x1536",
            "quality": "high",
        },
        timeout=180,
    )
    _raise_for_image_error(response)
    return _extract_image_bytes(response.json())


def _extract_image_bytes(payload: dict[str, Any]) -> bytes:
    data = payload.get("data") or []
    if not data:
        raise OpenAIImageUnavailable("OpenAI image response did not contain data")
    first = data[0] or {}
    b64_json = first.get("b64_json")
    if b64_json:
        return base64.b64decode(b64_json)
    url = first.get("url")
    if url:
        response = requests.get(str(url), timeout=60)
        response.raise_for_status()
        return response.content
    raise OpenAIImageUnavailable("OpenAI image response did not contain b64_json or url")


def _reference_blueprint(reference_ad: dict[str, Any], has_image_reference: bool) -> str:
    if has_image_reference:
        return (
            "Use the attached ad image only as a loose composition reference: broad subject count, "
            "camera distance, visual rhythm, and overall mood. Do not copy text zones, banners, logos, "
            "faces, clothes, background, props, or any source pixels."
        )
    return (
        "No usable image reference was available. Create a fresh premium SmileUp consultation photo "
        "based on the campaign angle and service line; use a realistic Vietnamese dental clinic setting "
        "with real-looking people, natural light, authentic posture, and no graphic/banner treatment."
    )


def _build_generation_prompt(variant: ContentVariant, reference_ad: dict[str, Any], blueprint: str, context: dict[str, Any]) -> str:
    variation = context.get("creative_variation_profile") or {}
    return f"""
Create a completely new, original, photorealistic vertical Facebook image for SmileUp Dental Clinic in Vietnam.

Reference handling:
{blueprint}

Absolute visual rules:
- IMAGE ONLY. No readable text anywhere.
- No typography, no captions, no labels, no numbers, no price, no discount, no CTA, no banner, no poster layout, no headline block, no speech bubble, no watermark, no UI frame, no menu board, no certificate text, no clinic sign text.
- If a monitor, tablet, X-ray screen, chart, or document appears, it must show only blurred/non-readable medical imagery or abstract shapes. No readable interface text, no measurement labels, no form fields, no brand names.
- Do not draw fake logos or brand words inside the image. Leave a clean blank area in the top-left so the real SmileUp logo can be overlaid locally after generation.
- Do not reproduce source pixels, exact composition, exact colors, exact background, face, identity, clothing, logo, watermark, props, or distinctive assets from the competitor ad.
- Replace all people with new Vietnamese subjects: different faces, different styling, different clothes, different background details.
- The image must contain real people in a dental clinic scene in Vietnam: at least one Vietnamese dentist in clinical attire and at least one Vietnamese patient/customer in consultation or examination.
- Do not generate standalone logos, tooth icons, abstract shapes, decorative graphics, empty clinic rooms, product-only shots, infographics, before/after comparisons, or medical shock imagery.
- No medical guarantee, no exaggerated transformation, no body-shaming implication.

SmileUp brand direction:
- Premium but warm Vietnamese dental clinic, realistic Ho Chi Minh/Hanoi clinic interior cues, clean reception/consultation room, dentist chair or X-ray consultation screen if useful.
- Clean white and teal color mood, modern lighting, trustworthy, human, realistic.
- Natural expressions, respectful consultation, imperfectly real photography, believable skin texture, realistic hands and teeth, no plastic AI look, no hyper-smooth faces, no mannequin poses, no beauty-ad retouching.
- Shot like a real clinic campaign photo: 35mm or 50mm lens feel, natural depth of field, credible Vietnamese people, realistic dental uniforms, tidy equipment, soft daylight or clinic lighting.
- Suitable for porcelain crowns, porcelain restoration, or dental implants.

Freshness requirement:
- Creative variation for this run: {variation}
- Even if the keyword and reference ad are the same, change camera angle, lighting, distance, dentist/patient styling, room detail, and pose from previous runs.

Campaign context for visual planning only. Do NOT write any of these words in the image:
Service: {variant.get("service_line", "")}
Angle: {variant.get("angle", "")}
Differentiation: {variant.get("differentiation", "")}
Image brief: {variant.get("image_prompt", "")}
Ad text context: {str(reference_ad.get("ad_text", ""))[:900]}
""".strip()


def _image_model_candidates() -> list[str]:
    candidates: list[str] = []
    for model in [config.OPENAI_IMAGE_MODEL, *config.OPENAI_IMAGE_FALLBACK_MODELS]:
        safe_model = str(model or "").strip()
        if safe_model and safe_model not in candidates:
            candidates.append(safe_model)
    return candidates


def _raise_for_image_error(response: requests.Response) -> None:
    if response.ok:
        return
    detail = response.text[:500]
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        detail = str(error.get("message") or detail)
    except Exception:
        pass
    raise OpenAIImageUnavailable(f"HTTP {response.status_code}: {detail}")


def _compact_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:260]


def _guess_mime_type(media_url: str) -> str:
    lower = media_url.lower().split("?", 1)[0]
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    return ""


def _extension_for_mime(mime_type: str) -> str:
    if mime_type == "image/png":
        return "png"
    if mime_type == "image/webp":
        return "webp"
    return "jpg"
