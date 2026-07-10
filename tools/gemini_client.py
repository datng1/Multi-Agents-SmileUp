from utils import config


class GeminiUnavailable(RuntimeError):
    pass


def generate_text_with_gemini(prompt: str) -> str:
    text, _ = generate_text_with_gemini_and_model(prompt)
    return text


def generate_text_with_gemini_and_model(prompt: str) -> tuple[str, str]:
    if not config.GEMINI_API_KEY:
        raise GeminiUnavailable("GEMINI_API_KEY missing")

    try:
        from google import genai
    except ImportError as exc:
        raise GeminiUnavailable("google-genai package is not installed") from exc

    response = _generate_with_gemini_models(genai, prompt)
    text = getattr(response, "text", "") or ""
    model = str(getattr(response, "_resolved_model", config.GEMINI_MODEL))
    return text, model


def _generate_with_gemini_models(genai_module, prompt: str):
    client = genai_module.Client(api_key=config.GEMINI_API_KEY)
    errors: list[str] = []
    for model in _gemini_model_candidates():
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            try:
                setattr(response, "_resolved_model", model)
            except (AttributeError, TypeError):
                pass
            return response
        except Exception as exc:
            errors.append(f"{model}: {exc}")
    raise GeminiUnavailable("Gemini models unavailable: " + " | ".join(errors[-3:]))


def _gemini_model_candidates() -> list[str]:
    candidates: list[str] = []
    for model in [config.GEMINI_MODEL, *config.GEMINI_FALLBACK_MODELS]:
        if model and model not in candidates:
            candidates.append(model)
    return candidates
