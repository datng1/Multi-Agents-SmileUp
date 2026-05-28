from __future__ import annotations

import json
import re
from typing import Any

import requests

from graph.state import AgentState
from tools.gemini_client import GeminiUnavailable, generate_text_with_gemini_and_model
from tools.openai_client import generate_text_with_openai
from utils import config


class CMOJuryUnavailable(RuntimeError):
    pass


def evaluate_with_available_models(state: AgentState, scorecard: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not config.CMO_JURY_ENABLED:
        return []

    prompt = _build_jury_prompt(state, scorecard)
    evaluators = []
    if config.GEMINI_API_KEY:
        evaluators.append(("Gemini", config.GEMINI_MODEL, _call_gemini))
    if config.OPENAI_API_KEY:
        evaluators.append(("GPT", config.OPENAI_MODEL, _call_openai))
    if config.ANTHROPIC_API_KEY:
        evaluators.append(("Claude", config.ANTHROPIC_MODEL, _call_claude))

    votes: list[dict[str, Any]] = []
    for provider, model, caller in evaluators:
        try:
            text, resolved_model = caller(prompt)
            vote = _parse_vote(text)
            vote["provider"] = provider
            vote["model"] = resolved_model or model
            votes.append(vote)
        except Exception as exc:
            votes.append(
                {
                    "provider": provider,
                    "model": model,
                    "decision": "ERROR",
                    "selected_variant_index": -1,
                    "selected_creative_index": -1,
                    "score": 0,
                    "rationale": str(exc)[:500],
                    "required_changes": [],
                    "risk_flags": ["model_unavailable"],
                }
            )
    return votes


def summarize_votes(votes: list[dict[str, Any]]) -> str:
    usable = [vote for vote in votes if vote.get("decision") != "ERROR"]
    if not votes:
        return "CMO Jury: không có API key GPT/Gemini/Claude, dùng heuristic nội bộ."
    if not usable:
        return "CMO Jury: tất cả model lỗi, dùng heuristic nội bộ."
    lines = [f"CMO Jury: {len(usable)}/{len(votes)} model đánh giá thành công."]
    for vote in votes:
        lines.append(
            f"- {vote.get('provider')} ({vote.get('model')}): {vote.get('decision')} | "
            f"variant #{_human_index(vote.get('selected_variant_index'))} | "
            f"score {vote.get('score', 0)} | {vote.get('rationale', '')}"
        )
    return "\n".join(lines)


def aggregate_jury_choice(votes: list[dict[str, Any]], scorecard: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [vote for vote in votes if vote.get("decision") in {"APPROVE_TO_PUBLISH", "REVISE_REQUIRED", "REJECT"}]
    if not usable:
        return {}

    decisions = _count_by(usable, "decision")
    variant_scores: dict[int, float] = {}
    creative_scores: dict[int, float] = {}
    for vote in usable:
        weight = max(1, int(vote.get("score", 0) or 0))
        variant = int(vote.get("selected_variant_index", -1))
        creative = int(vote.get("selected_creative_index", -1))
        if variant >= 0:
            variant_scores[variant] = variant_scores.get(variant, 0) + weight
        if creative >= 0:
            creative_scores[creative] = creative_scores.get(creative, 0) + weight

    majority_decision = max(decisions.items(), key=lambda item: item[1])[0]
    if decisions.get("REJECT", 0) >= max(1, len(usable) // 2 + 1):
        majority_decision = "REJECT"
    elif decisions.get("REVISE_REQUIRED", 0) >= max(1, len(usable) // 2 + 1):
        majority_decision = "REVISE_REQUIRED"

    selected_variant = _best_weighted_index(variant_scores)
    if selected_variant < 0 and scorecard:
        selected_variant = int(max(scorecard, key=lambda item: item.get("score", 0)).get("index", -1))

    return {
        "decision": majority_decision,
        "selected_variant_index": selected_variant,
        "selected_creative_index": _best_weighted_index(creative_scores),
        "risk_flags": sorted({flag for vote in usable for flag in vote.get("risk_flags", [])}),
        "required_changes": sorted({change for vote in usable for change in vote.get("required_changes", [])}),
        "average_score": round(sum(int(vote.get("score", 0) or 0) for vote in usable) / len(usable)),
    }


def _call_gemini(prompt: str) -> tuple[str, str]:
    try:
        return generate_text_with_gemini_and_model(prompt)
    except GeminiUnavailable as exc:
        raise CMOJuryUnavailable(str(exc)) from exc


def _call_openai(prompt: str) -> tuple[str, str]:
    return generate_text_with_openai(
        prompt,
        system="Bạn là CMO marketing nha khoa cấp cao. Chỉ trả JSON.",
        temperature=0.2,
        timeout=40,
    )


def _call_claude(prompt: str) -> tuple[str, str]:
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": config.ANTHROPIC_MODEL,
            "max_tokens": 1400,
            "temperature": 0.2,
            "system": "Bạn là CMO marketing nha khoa cấp cao. Chỉ trả JSON.",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=40,
    )
    response.raise_for_status()
    payload = response.json()
    return "\n".join(block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"), config.ANTHROPIC_MODEL


def _build_jury_prompt(state: AgentState, scorecard: list[dict[str, Any]]) -> str:
    compact_variants = [
        {
            "index": index,
            "campaign_track": variant.get("campaign_track", ""),
            "monthly_role": variant.get("monthly_role", ""),
            "service_line": variant.get("service_line", ""),
            "title": variant.get("title", ""),
            "body": variant.get("body", "")[:1200],
            "cta": variant.get("call_to_action", ""),
            "differentiation": variant.get("differentiation", ""),
            "trend_angle": variant.get("trend_angle", ""),
        }
        for index, variant in enumerate(state.get("content_plan", []))
    ]
    compact_assets = [
        {
            "index": index,
            "service_line": asset.get("service_line", ""),
            "image_prompt": asset.get("image_prompt", ""),
            "source_policy": asset.get("source_policy", ""),
        }
        for index, asset in enumerate(state.get("creative_assets", []))
    ]
    return f"""
Bạn là CMO chuyên nghiệp về marketing nha khoa cho SmileUp Dental Clinic.
Hãy đánh giá như người chịu KPI lead tư vấn cho răng sứ thẩm mỹ, phục hình răng sứ và cấy ghép implant.
Không xuất chain-of-thought. Chỉ trả JSON.

Mục tiêu CMO:
{state.get('cmo_objective', '')}

Insight và agent reports:
- Ad Library: {state.get('ad_library_report', '')[:1500]}
- Text: {state.get('text_insight_report', '')[:1000]}
- Trend: {state.get('facebook_trend_analysis', '')[:1000]}
- Visual: {state.get('visual_insight_report', '')[:1000]}
- Video: {state.get('video_insight_report', '')[:1000]}
- Strategy: {state.get('strategic_direction', '')[:1000]}
- Compliance: {state.get('compliance_report', '')[:1000]}

Heuristic scorecard:
{json.dumps(scorecard, ensure_ascii=False, indent=2)}

Campaign variants:
{json.dumps(compact_variants, ensure_ascii=False, indent=2)}

Creative assets:
{json.dumps(compact_assets, ensure_ascii=False, indent=2)}

Yêu cầu đánh giá:
- Chọn variant có khả năng tạo lịch tư vấn tốt nhất.
- Chọn creative phù hợp nhất.
- APPROVE_TO_PUBLISH nếu có thể publish, score tối thiểu 85 và compliance an toàn.
- REVISE_REQUIRED nếu cần sửa copy/CTA/claim/visual/disclaimer trước khi publish.
- REJECT nếu rủi ro nghiêm trọng, dưới 70 điểm hoặc thiếu dữ liệu không thể publish.
- Không cho phép claim tuyệt đối, không copy/rebrand tài sản đối thủ.

JSON schema:
Decision phải dùng đúng contract mới của CMO:
- APPROVE_TO_PUBLISH: chỉ dùng khi score tối thiểu 85 và compliance an toàn.
- REVISE_REQUIRED: copy, CTA, hook, visual, claim hoặc disclaimer cần sửa trước khi publish.
- REJECT: score dưới 70, rủi ro nghiêm trọng hoặc không đủ dữ liệu để publish.
{{
  "decision": "APPROVE_TO_PUBLISH | REVISE_REQUIRED | REJECT",
  "selected_variant_index": 0,
  "selected_creative_index": 0,
  "score": 0,
  "rationale": "lý do ngắn, không chain-of-thought",
  "required_changes": ["việc cần sửa nếu có"],
  "risk_flags": ["rủi ro nếu có"]
}}
""".strip()


def _parse_vote(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    payload = json.loads(cleaned)
    decision = _normalize_decision(payload.get("decision", "REVISE_REQUIRED"))
    return {
        "decision": decision,
        "selected_variant_index": int(payload.get("selected_variant_index", -1)),
        "selected_creative_index": int(payload.get("selected_creative_index", -1)),
        "score": max(0, min(100, int(payload.get("score", 0) or 0))),
        "rationale": str(payload.get("rationale", "")).strip(),
        "required_changes": [str(item).strip() for item in payload.get("required_changes", []) if str(item).strip()],
        "risk_flags": [str(item).strip() for item in payload.get("risk_flags", []) if str(item).strip()],
    }


def _normalize_decision(value: Any) -> str:
    decision = str(value).strip().upper()
    aliases = {
        "APPROVE": "APPROVE_TO_PUBLISH",
        "APPROVED": "APPROVE_TO_PUBLISH",
        "PUBLISH": "APPROVE_TO_PUBLISH",
        "REVISE": "REVISE_REQUIRED",
        "REVISION_REQUIRED": "REVISE_REQUIRED",
        "NEEDS_REVISION": "REVISE_REQUIRED",
        "STOP": "REJECT",
        "BLOCK": "REJECT",
    }
    decision = aliases.get(decision, decision)
    if decision not in {"APPROVE_TO_PUBLISH", "REVISE_REQUIRED", "REJECT"}:
        return "REVISE_REQUIRED"
    return decision


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _best_weighted_index(scores: dict[int, float]) -> int:
    if not scores:
        return -1
    return max(scores.items(), key=lambda item: item[1])[0]


def _human_index(value: Any) -> str:
    try:
        index = int(value)
    except Exception:
        return "none"
    return str(index + 1) if index >= 0 else "none"
