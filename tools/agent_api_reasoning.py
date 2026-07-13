from __future__ import annotations

import json
from typing import Any

from tools.gemini_client import generate_text_with_gemini
from tools.openai_client import generate_text_with_openai
from utils import config
from utils.logger import get_logger


logger = get_logger(__name__)


class RequiredModelUnavailable(RuntimeError):
    pass


def reason_with_agent_api(
    *,
    agent_name: str,
    role: str,
    task: str,
    context: dict[str, Any],
    fallback: str,
    max_context_chars: int = 9000,
    complexity: str = "complex",
) -> tuple[str, str]:
    """Route bounded reasoning to the model required by the task tier."""
    if complexity not in {"easy", "complex"}:
        raise ValueError("complexity must be 'easy' or 'complex'")
    prompt = _build_prompt(agent_name, role, task, context, max_context_chars)
    if not config.AGENT_API_REASONING_ENABLED:
        return fallback, "local-bounded"

    if config.MOCK_MODE:
        return fallback, "mock-local"

    if complexity == "easy":
        if not config.GEMINI_API_KEY:
            raise RequiredModelUnavailable("Gemini API key is required for easy tasks")
        try:
            return _clean_report(generate_text_with_gemini(prompt), fallback), f"Gemini ({config.GEMINI_MODEL})"
        except Exception as exc:
            logger.warning("%s Gemini reasoning failed: %s", agent_name, exc)
            raise RequiredModelUnavailable(f"Gemini easy-task route failed: {exc}") from exc

    if not config.OPENAI_API_KEY:
        raise RequiredModelUnavailable("OpenAI API key is required for complex tasks")
    try:
        return _clean_report(_call_openai(prompt), fallback), f"GPT ({config.OPENAI_MODEL})"
    except Exception as exc:
        logger.warning("%s OpenAI reasoning failed: %s", agent_name, exc)
        raise RequiredModelUnavailable(f"OpenAI complex-task route failed: {exc}") from exc


def _build_prompt(
    agent_name: str,
    role: str,
    task: str,
    context: dict[str, Any],
    max_context_chars: int,
) -> str:
    context_text = json.dumps(context, ensure_ascii=False, indent=2, default=str)
    if len(context_text) > max_context_chars:
        context_text = context_text[: max_context_chars - 80] + "\n... [context truncated]"

    return f"""
Bạn là {agent_name} trong workflow multi-agent marketing của SmileUp Dental Clinic.

Vai trò cố định:
{role}

Nhiệm vụ cần làm:
{task}

Ràng buộc bắt buộc:
- Chỉ dùng dữ liệu trong CONTEXT bên dưới; không tự bịa nguồn, không tự crawl, không tự publish.
- Không xuất chain-of-thought. Chỉ xuất báo cáo cuối cùng ngắn gọn, có cấu trúc bullet.
- Không xử lý token, cookie, mật khẩu hoặc credential.
- Không làm thay vai của agent khác. Nếu phát hiện vấn đề ngoài vai của mình, ghi vào mục "Cần agent khác xử lý" thay vì tự xử lý.
- Phải bám dịch vụ trọng tâm: răng sứ thẩm mỹ, phục hình răng sứ, cấy ghép Implant.
- Phải phục vụ CMO: report cần giúp CMO lập chiến lược tháng, chia tuyến ads hiệu quả và chăm sóc page.
- Bài ads hiệu quả hướng tới lead/SĐT nhưng vẫn an toàn y khoa; không claim tuyệt đối.
- Nếu thiếu dữ liệu, nói rõ thiếu gì và agent nào cần bổ sung.

Chuẩn chất lượng bắt buộc:
- Phân biệt rõ "Dữ kiện quan sát được", "Suy luận marketing", và "Khuyến nghị cho CMO".
- Luôn nói rõ insight nào dùng cho tuyến ads_effective, insight nào dùng cho tuyến page_care.
- Ưu tiên hiệu quả kinh doanh: lịch tư vấn hợp lệ, SĐT/inbox chất lượng, khách đủ nhu cầu răng sứ/phục hình/implant.
- Không đánh đồng tương tác với hiệu quả. Like/share chỉ có giá trị nếu hỗ trợ lead hoặc trust.
- Không dùng ngôn ngữ tuyệt đối như "chắc chắn", "đảm bảo", "100%" trong khuyến nghị marketing/y khoa.
- Nếu dữ liệu yếu, phải hạ mức tự tin và đề xuất chạy lại agent/crawler thay vì kết luận mạnh.

Định dạng output bắt buộc:
1. Tóm tắt cho CMO.
2. Dữ kiện quan sát được.
3. Suy luận marketing.
4. Khuyến nghị cho tuyến ads_effective.
5. Khuyến nghị cho tuyến page_care.
6. Rủi ro hoặc dữ liệu còn thiếu.
7. Cần agent khác xử lý, nếu có.

CONTEXT:
{context_text}
""".strip()


def _clean_report(text: str, fallback: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return fallback
    return cleaned


def _call_openai(prompt: str) -> str:
    text, _ = generate_text_with_openai(
        prompt,
        system="You are a bounded Vietnamese dental marketing analysis agent. Stay in role, do not reveal reasoning, return only the final report.",
        temperature=0.25,
        timeout=45,
    )
    return text
