from __future__ import annotations

from typing import Any

import requests

from utils import config


class OpenAIUnavailable(RuntimeError):
    pass


def generate_text_with_openai(
    prompt: str,
    *,
    system: str,
    temperature: float = 0.25,
    timeout: int = 45,
) -> tuple[str, str]:
    if not config.OPENAI_API_KEY:
        raise OpenAIUnavailable("OPENAI_API_KEY missing")

    if _prefers_responses_api(config.OPENAI_MODEL):
        try:
            return _call_responses_api(prompt, system=system, timeout=timeout), config.OPENAI_MODEL
        except Exception as exc:
            raise OpenAIUnavailable(str(exc)) from exc

    try:
        return _call_chat_completions(prompt, system=system, temperature=temperature, timeout=timeout), config.OPENAI_MODEL
    except Exception as exc:
        raise OpenAIUnavailable(str(exc)) from exc


def _prefers_responses_api(model: str) -> bool:
    return model.startswith(("gpt-5", "o1", "o3", "o4"))


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }


def _call_responses_api(prompt: str, *, system: str, timeout: int) -> str:
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers=_headers(),
        json={
            "model": config.OPENAI_MODEL,
            "instructions": system,
            "input": prompt,
            "reasoning": {"effort": config.OPENAI_REASONING_EFFORT},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return _extract_responses_text(response.json())


def _call_chat_completions(prompt: str, *, system: str, temperature: float, timeout: int) -> str:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=_headers(),
        json={
            "model": config.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def _extract_responses_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    parts: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(str(content["text"]))
    text = "\n".join(part.strip() for part in parts if part.strip()).strip()
    if not text:
        raise OpenAIUnavailable("OpenAI response did not contain text output")
    return text
