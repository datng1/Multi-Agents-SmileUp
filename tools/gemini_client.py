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
    text_report = state.get("text_insight_report") or "Text Insight Agent chưa có đủ caption để phân tích."
    visual_report = state.get("visual_insight_report") or "Visual Insight Agent chưa có mô tả ảnh."
    video_report = state.get("video_insight_report") or "Video Insight Agent chưa có transcript/ghi chú video."
    strategic_direction = state.get("strategic_direction") or "Ưu tiên răng sứ thẩm mỹ và implant với CTA đặt lịch tư vấn."
    strategy = state.get("daily_strategy") or "Tư vấn nha khoa cá nhân hóa, minh bạch, an toàn."
    feedback = state.get("manager_feedback") or "Không có feedback trước đó."
    return f"""
Bạn là hội đồng multi-agent marketing nha khoa cho phòng khám SmileUp tại Việt Nam.

Hãy phân tích thật kỹ trong nội bộ trước khi viết, nhưng KHÔNG xuất chain-of-thought. Chỉ xuất JSON cuối cùng.

Vai trò từng agent:
- Text Insight Agent: đọc toàn bộ caption/bài viết đối thủ, tách hook, pain point, offer, CTA, chủ đề lặp lại.
- Visual Insight Agent: đọc ghi chú ảnh/frame/video still, rút ra bố cục, màu, text overlay, tín hiệu niềm tin; tuyệt đối không sao chép hoặc rebrand ảnh đối thủ.
- Video Insight Agent: đọc transcript/shot notes video, tách hook 3 giây đầu, nhịp kể, proof, CTA, khả năng lên xu hướng.
- Trend Agent: phân tích trend Facebook, định dạng caption, câu hỏi kéo comment, chủ đề dễ share/save.
- Strategy Agent: chọn hướng đúng nhất cho SmileUp dựa trên răng sứ và cấy implant.
- Copywriting Agent: viết bài Facebook đăng được ngay bằng giọng marketing nha khoa chuyên nghiệp.

Định vị SmileUp cần ưu tiên:
- Dịch vụ trọng tâm: răng sứ thẩm mỹ, phục hình răng sứ, cấy ghép implant.
- Tone: chuyên gia, tin cậy, hiện đại, không hù dọa, không phóng đại.
- Mục tiêu: tạo lịch tư vấn/thăm khám, không hứa hẹn kết quả tuyệt đối.

Dữ liệu insight đối thủ:
{insights}

Text Insight Agent report:
{text_report}

Visual Insight Agent report:
{visual_report}

Video Insight Agent report:
{video_report}

Phân tích trend Facebook từ dữ liệu đầu vào:
{trend_analysis}

Creative brief hình ảnh an toàn:
{visual_brief}

Strategic Direction Agent report:
{strategic_direction}

Chiến lược hiện tại:
{strategy}

Feedback cần xử lý:
{feedback}

Hãy tạo một bài đăng Facebook mới cho SmileUp.
Yêu cầu:
- Bám trọng tâm răng sứ hoặc implant, không lan man sang dịch vụ khác nếu insight không yêu cầu.
- Mặc định bạn là chuyên gia marketing nha khoa 10+ năm kinh nghiệm, hiểu hành vi khách hàng Việt Nam, tâm lý sợ đau/sợ giá cao/sợ làm sai chỉ định.
- Bài viết phải có giọng marketing thật: hook sắc, nỗi đau rõ, lợi ích cụ thể, lý do tin tưởng, CTA có lực kéo inbox.
- Chia output thành các phần chính xác: phân tích marketing, góc trend, cấu trúc bài, bài đăng Facebook.
- Bài đăng Facebook phải đọc như caption có thể đăng ngay: tự nhiên, nổi bật, có nhịp cảm xúc, không khô như báo cáo.
- Có yếu tố dễ lên xu hướng: hook mạnh, câu hỏi gợi nhu cầu, lợi ích dễ scan, CTA rõ, hashtag hẹp.
- Không sao chép câu chữ hoặc ảnh của đối thủ.
- Không cam kết tuyệt đối như 100%, vĩnh viễn, không đau hoàn toàn, chắc chắn khỏi.
- Có lưu ý kết quả tùy tình trạng răng và cần bác sĩ thăm khám.
- Có CTA đặt lịch/inbox/gọi hotline.
- Hashtag 3-8 cái.
- image_prompt phải mô tả ảnh gốc/AI mới cho SmileUp, có logo/nhận diện SmileUp, tuyệt đối không yêu cầu chỉnh ảnh đối thủ thành ảnh của SmileUp.

Chỉ trả về JSON thuần, không markdown:
{{
  "marketing_analysis": "Phân tích khách hàng mục tiêu, nỗi đau, insight, lý do bài viết nên thu hút khách hàng.",
  "trend_angle": "Góc bắt trend Facebook nên dùng cho bài này.",
  "post_structure": "Hook -> Pain point -> SmileUp solution -> Trust proof -> CTA.",
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
        "marketing_analysis": str(payload.get("marketing_analysis", "")).strip(),
        "trend_angle": str(payload.get("trend_angle", "")).strip(),
        "post_structure": str(payload.get("post_structure", "")).strip(),
        "title": str(payload.get("title", "")).strip(),
        "body": str(payload.get("body", "")).strip(),
        "hashtags": [str(tag).strip() for tag in payload.get("hashtags", []) if str(tag).strip()],
        "call_to_action": str(payload.get("call_to_action", "")).strip(),
        "image_prompt": str(payload.get("image_prompt", "")).strip() or None,
    }
