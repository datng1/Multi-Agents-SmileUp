import json
import re

from graph.state import AgentState, DraftContent
from utils import config


class GeminiUnavailable(RuntimeError):
    pass


def generate_draft_with_gemini(state: AgentState) -> DraftContent:
    if not config.GEMINI_API_KEY:
        raise GeminiUnavailable("GEMINI_API_KEY missing")

    try:
        from google import genai
    except Exception as exc:
        raise GeminiUnavailable("google-genai package is not installed") from exc

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=_build_prompt(state),
    )
    text = getattr(response, "text", "") or ""
    return _parse_draft(text)


def _build_prompt(state: AgentState) -> str:
    insights = json.dumps(state.get("competitor_insights", []), ensure_ascii=False, indent=2)
    trend_analysis = state.get("facebook_trend_analysis") or "Chưa có phân tích trend."
    visual_brief = state.get("visual_creative_brief") or "Tạo ảnh gốc có nhận diện SmileUp, không dùng ảnh đối thủ."
    strategy = state.get("daily_strategy") or "Tư vấn nha khoa cá nhân hóa, minh bạch, an toàn."
    feedback = state.get("manager_feedback") or "Không có feedback trước đó."
    return f"""
Bạn là senior strategist kiêm copywriter marketing nha khoa tại Việt Nam cho phòng khám SmileUp.

Hãy phân tích thật kỹ trong nội bộ trước khi viết, nhưng KHÔNG xuất chain-of-thought. Chỉ xuất JSON cuối cùng.

Định vị SmileUp cần ưu tiên:
- Dịch vụ trọng tâm: răng sứ thẩm mỹ, phục hình răng sứ, cấy ghép implant.
- Tone: chuyên gia, tin cậy, hiện đại, không hù dọa, không phóng đại.
- Mục tiêu: tạo lịch tư vấn/thăm khám, không hứa hẹn kết quả tuyệt đối.

Dữ liệu insight đối thủ:
{insights}

Phân tích trend Facebook từ dữ liệu đầu vào:
{trend_analysis}

Creative brief hình ảnh an toàn:
{visual_brief}

Chiến lược hiện tại:
{strategy}

Feedback cần xử lý:
{feedback}

Hãy tạo một bài đăng Facebook mới cho SmileUp.
Yêu cầu:
- Bám trọng tâm răng sứ hoặc implant, không lan man sang dịch vụ khác nếu insight không yêu cầu.
- Tiếng Việt tự nhiên, chuyên nghiệp, thân thiện.
- Có yếu tố dễ lên xu hướng: hook mạnh, câu hỏi gợi nhu cầu, lợi ích dễ scan, CTA rõ, hashtag hẹp.
- Không sao chép câu chữ hoặc ảnh của đối thủ.
- Không cam kết tuyệt đối như 100%, vĩnh viễn, không đau hoàn toàn, chắc chắn khỏi.
- Có lưu ý kết quả tùy tình trạng răng và cần bác sĩ thăm khám.
- Có CTA đặt lịch/inbox/gọi hotline.
- Hashtag 3-8 cái.
- image_prompt phải mô tả ảnh gốc/AI mới cho SmileUp, có logo/nhận diện SmileUp, tuyệt đối không yêu cầu chỉnh ảnh đối thủ thành ảnh của SmileUp.

Chỉ trả về JSON thuần, không markdown:
{{
  "title": "string",
  "body": "string",
  "hashtags": ["#tag"],
  "call_to_action": "string",
  "image_prompt": "string"
}}
""".strip()


def _parse_draft(text: str) -> DraftContent:
    cleaned = text.strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    payload = json.loads(cleaned)
    return {
        "title": str(payload.get("title", "")).strip(),
        "body": str(payload.get("body", "")).strip(),
        "hashtags": [str(tag).strip() for tag in payload.get("hashtags", []) if str(tag).strip()],
        "call_to_action": str(payload.get("call_to_action", "")).strip(),
        "image_prompt": str(payload.get("image_prompt", "")).strip() or None,
    }
