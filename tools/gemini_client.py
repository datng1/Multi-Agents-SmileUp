import json
import re

from graph.state import AgentState, ContentVariant, DraftContent
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

    response = _generate_with_gemini_models(genai, _build_prompt(state))
    text = getattr(response, "text", "") or ""
    return _parse_draft(text)


def generate_content_plan_with_gemini(state: AgentState) -> list[ContentVariant]:
    if not config.GEMINI_API_KEY:
        raise GeminiUnavailable("GEMINI_API_KEY missing")

    try:
        from google import genai
    except Exception as exc:
        raise GeminiUnavailable("google-genai package is not installed") from exc

    response = _generate_with_gemini_models(genai, _build_campaign_prompt(state))
    text = getattr(response, "text", "") or ""
    return _parse_content_plan(text)


def generate_text_with_gemini(prompt: str) -> str:
    text, _ = generate_text_with_gemini_and_model(prompt)
    return text


def generate_text_with_gemini_and_model(prompt: str) -> tuple[str, str]:
    if not config.GEMINI_API_KEY:
        raise GeminiUnavailable("GEMINI_API_KEY missing")

    try:
        from google import genai
    except Exception as exc:
        raise GeminiUnavailable("google-genai package is not installed") from exc

    response = _generate_with_gemini_models(genai, prompt)
    return getattr(response, "text", "") or "", str(getattr(response, "_resolved_model", config.GEMINI_MODEL))


def _generate_with_gemini_models(genai_module, prompt: str):
    client = genai_module.Client(api_key=config.GEMINI_API_KEY)
    errors: list[str] = []
    for model in _gemini_model_candidates():
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            try:
                setattr(response, "_resolved_model", model)
            except Exception:
                pass
            return response
        except Exception as exc:
            errors.append(f"{model}: {exc}")
            continue
    raise GeminiUnavailable("Gemini models unavailable: " + " | ".join(errors[-3:]))


def _gemini_model_candidates() -> list[str]:
    candidates: list[str] = []
    for model in [config.GEMINI_MODEL, *config.GEMINI_FALLBACK_MODELS]:
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def _build_prompt(state: AgentState) -> str:
    insights = json.dumps(state.get("competitor_insights", []), ensure_ascii=False, indent=2)
    trend_analysis = state.get("facebook_trend_analysis") or "Chưa có phân tích trend."
    visual_brief = state.get("visual_creative_brief") or "Tạo ảnh gốc có nhận diện SmileUp, không dùng ảnh đối thủ."
    text_report = state.get("text_insight_report") or "Text Insight Agent chưa có đủ caption để phân tích."
    visual_report = state.get("visual_insight_report") or "Visual Insight Agent chưa có mô tả ảnh."
    video_report = state.get("video_insight_report") or "Video Insight Agent chưa có transcript/ghi chú video."
    strategic_direction = state.get("strategic_direction") or "Ưu tiên răng sứ thẩm mỹ và implant với CTA đặt lịch tư vấn."
    ad_library_report = state.get("ad_library_report") or "Chưa có dữ liệu Meta Ad Library."
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

Ad Library Agent report:
{ad_library_report}

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


def _build_campaign_prompt(state: AgentState) -> str:
    base = _build_prompt(state)
    return f"""
{base}

NHIỆM VỤ MỞ RỘNG CHO CMO:
Thay vì chỉ tạo 1 bài, hãy tạo 4 bài đăng Facebook khác nhau cho SmileUp, mỗi bài gắn với một trụ cột chiến dịch riêng:
1. Cấy ghép implant: tập trung ăn nhai, mất răng lâu năm, cần thăm khám đúng chỉ định.
2. Răng sứ thẩm mỹ: tập trung nụ cười tự nhiên, tự tin, bảo tồn răng thật khi có thể.
3. Minh bạch chuyên môn: tập trung bác sĩ tư vấn, phim chụp/kiểm tra, không chạy đua giá rẻ.
4. Reels/short post để bắt trend: hook ngắn, câu hỏi gợi comment, dùng cho Facebook/Reels caption.

Mỗi bài phải khác biệt hơn các ads đầu vào bằng cách:
- Không dựa vào giảm giá sốc làm lợi thế chính.
- Không copy câu chữ, offer, bố cục copy của đối thủ.
- Làm nổi bật SmileUp: tư vấn cá nhân hóa, quy trình minh bạch, phòng khám hiện đại, an toàn y khoa.
- Có visual direction riêng và image_prompt riêng. image_prompt bắt buộc yêu cầu ảnh gốc/AI mới, có logo SmileUp, không rebrand ảnh đối thủ.

Chỉ trả về JSON thuần theo schema:
{{
  "variants": [
    {{
      "service_line": "implant | rang_su | trust | reels",
      "angle": "góc nội dung",
      "differentiation": "SmileUp khác biệt hơn ads đối thủ ở điểm nào",
      "marketing_analysis": "phân tích ngắn cho bài này",
      "trend_angle": "trend angle rieng",
      "post_structure": "Hook -> Pain point -> SmileUp solution -> Trust proof -> CTA",
      "title": "string",
      "body": "caption có thể đăng ngay",
      "hashtags": ["#tag"],
      "call_to_action": "string",
      "image_prompt": "prompt ảnh gốc có logo SmileUp"
    }}
  ]
}}
""".strip()


def _parse_draft(text: str) -> DraftContent:
    cleaned = text.strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    payload = json.loads(cleaned)
    title = str(payload.get("title", "")).strip()
    body = _dedupe_title_from_body(title, str(payload.get("body", "")).strip())
    return {
        "marketing_analysis": str(payload.get("marketing_analysis", "")).strip(),
        "trend_angle": str(payload.get("trend_angle", "")).strip(),
        "post_structure": str(payload.get("post_structure", "")).strip(),
        "title": title,
        "body": body,
        "hashtags": [str(tag).strip() for tag in payload.get("hashtags", []) if str(tag).strip()],
        "call_to_action": str(payload.get("call_to_action", "")).strip(),
        "image_prompt": str(payload.get("image_prompt", "")).strip() or None,
    }


def _parse_content_plan(text: str) -> list[ContentVariant]:
    cleaned = text.strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    payload = json.loads(cleaned)
    raw_variants = payload.get("variants", [])
    variants: list[ContentVariant] = []
    for raw in raw_variants:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title", "")).strip()
        body = _dedupe_title_from_body(title, str(raw.get("body", "")).strip())
        variants.append(
            {
                "service_line": str(raw.get("service_line", "")).strip(),
                "angle": str(raw.get("angle", "")).strip(),
                "differentiation": str(raw.get("differentiation", "")).strip(),
                "marketing_analysis": str(raw.get("marketing_analysis", "")).strip(),
                "trend_angle": str(raw.get("trend_angle", "")).strip(),
                "post_structure": str(raw.get("post_structure", "")).strip(),
                "title": title,
                "body": body,
                "hashtags": [str(tag).strip() for tag in raw.get("hashtags", []) if str(tag).strip()],
                "call_to_action": str(raw.get("call_to_action", "")).strip(),
                "image_prompt": str(raw.get("image_prompt", "")).strip(),
            }
        )
    if not variants:
        raise ValueError("Gemini returned no content variants")
    return variants[:4]


def _dedupe_title_from_body(title: str, body: str) -> str:
    if not title or not body:
        return body

    normalized_title = _normalize_for_compare(title)
    normalized_body = _normalize_for_compare(body)
    if not normalized_body.startswith(normalized_title):
        return body

    remainder = body[len(title):].lstrip(" \n\r\t-:|")
    return remainder or body


def _normalize_for_compare(value: str) -> str:
    return " ".join(value.casefold().split())
