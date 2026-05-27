from graph.state import AgentState, ContentVariant, DraftContent
from tools.creative_generator import generate_creative_assets
from tools.gemini_client import GeminiUnavailable, generate_content_plan_with_gemini, generate_draft_with_gemini
from utils.logger import get_logger


logger = get_logger(__name__)


def run_content_agent(state: AgentState) -> AgentState:
    logger.info("Content Agent creating campaign variants")
    if state.get("approval_status") == "needs_revision":
        state["revision_count"] = state.get("revision_count", 0) + 1

    try:
        variants = generate_content_plan_with_gemini(state)
        state["messages"].append({"role": "content", "content": f"Campaign plan created with Gemini ({len(variants)} variants)"})
    except (GeminiUnavailable, Exception) as exc:
        logger.warning("Gemini campaign generation failed, using fallback draft/plan: %s", exc)
        try:
            draft = generate_draft_with_gemini(state)
            variants = [_variant_from_draft(draft, "implant")]
            state["messages"].append({"role": "content", "content": f"Single draft created with Gemini ({exc})"})
        except Exception:
            variants = _offline_content_plan(state)
            state["messages"].append({"role": "content", "content": f"Campaign plan created locally ({exc})"})

    state["content_plan"] = variants
    state["draft_content"] = _draft_from_variant(variants[0]) if variants else _offline_draft(state)
    creative_context = {
        "creative_image_mode": state.get("creative_image_mode", "auto"),
        "creative_upload_path": state.get("creative_upload_path", ""),
        "creative_upload_url": state.get("creative_upload_url", ""),
        "creative_reference_note": state.get("creative_reference_note", ""),
        "creative_reference_ad": state.get("creative_reference_ad", {}),
        "creative_reference_blueprint": state.get("creative_reference_blueprint", ""),
    }
    state["creative_assets"] = generate_creative_assets(variants, creative_context)
    if creative_context.get("creative_reference_blueprint"):
        state["creative_reference_blueprint"] = str(creative_context.get("creative_reference_blueprint") or "")
    if state["creative_assets"]:
        state["messages"].append({"role": "content", "content": f"Generated {len(state['creative_assets'])} branded SmileUp creative images"})
    elif creative_context["creative_image_mode"] == "text_only":
        state["messages"].append({"role": "content", "content": "Text-only mode selected; skipped creative image generation"})

    state["approval_status"] = "pending"
    state["current_step"] = "content_creator"
    return state


def _draft_from_variant(variant: ContentVariant) -> DraftContent:
    return {
        "marketing_analysis": variant.get("marketing_analysis", ""),
        "trend_angle": variant.get("trend_angle", ""),
        "post_structure": variant.get("post_structure", ""),
        "title": variant.get("title", ""),
        "body": variant.get("body", ""),
        "hashtags": variant.get("hashtags", []),
        "call_to_action": variant.get("call_to_action", ""),
        "image_prompt": variant.get("image_prompt", "") or None,
    }


def _variant_from_draft(draft: DraftContent, service_line: str) -> ContentVariant:
    return {
        "service_line": service_line,
        "angle": draft.get("trend_angle", ""),
        "differentiation": "SmileUp khác biệt bằng tư vấn cá nhân hóa, minh bạch chỉ định và không chạy đua bằng claim quá đà.",
        "marketing_analysis": draft.get("marketing_analysis", ""),
        "trend_angle": draft.get("trend_angle", ""),
        "post_structure": draft.get("post_structure", ""),
        "title": draft.get("title", ""),
        "body": draft.get("body", ""),
        "hashtags": draft.get("hashtags", []),
        "call_to_action": draft.get("call_to_action", ""),
        "image_prompt": draft.get("image_prompt", "") or "",
    }


def _offline_content_plan(state: AgentState) -> list[ContentVariant]:
    topics = _dominant_topics(state)
    return [
        {
            "service_line": "implant",
            "angle": "Mất răng lâu năm và ăn nhai khó khăn",
            "differentiation": "Khác với ads giá sốc, SmileUp dẫn bằng tư vấn đúng chỉ định, phim chụp và phác đồ cá nhân hóa.",
            "marketing_analysis": "Nhóm khách hàng mất răng thường sợ đau, sợ chi phí phát sinh và sợ cấy sai chỉ định. Bài cần tạo niềm tin bằng quy trình thăm khám rõ ràng.",
            "trend_angle": "Câu hỏi gợi đúng nỗi đau: mất răng lâu năm có đang làm bạn ngại ăn nhai?",
            "post_structure": "Hook -> dấu hiệu -> giải pháp implant SmileUp -> lưu ý thăm khám -> CTA",
            "title": "Mất răng lâu năm: đừng để việc ăn nhai trở thành nỗi lo mỗi ngày",
            "body": (
                "Mất 1 răng hay nhiều răng không chỉ làm bạn ngại cười, mà còn có thể ảnh hưởng đến khả năng ăn nhai và các răng bên cạnh.\n\n"
                "Tại SmileUp, tư vấn implant bắt đầu bằng kiểm tra tình trạng răng, xương hàm và sức khỏe tổng quát. Bác sĩ sẽ giải thích rõ khi nào nên cấy implant, khi nào cần điều trị nền trước và chi phí dự kiến theo từng phương án.\n\n"
                "Điểm quan trọng không phải là chọn gói đắt hay rẻ, mà là chọn đúng chỉ định cho chính tình trạng của bạn. Kết quả và thời gian phục hồi có thể khác nhau tùy từng người, vì vậy thăm khám trực tiếp là bước cần có."
            ),
            "hashtags": ["#SmileUp", "#CayGhepImplant", "#TrongRangImplant", "#NhaKhoaUyTin"],
            "call_to_action": "Inbox SmileUp để đặt lịch thăm khám implant và nhận tư vấn phác đồ phù hợp.",
            "image_prompt": "Ảnh gốc/AI mới: bác sĩ SmileUp tư vấn implant bên màn hình phim chụp, phòng khám sạch hiện đại, logo SmileUp góc trên trái.",
        },
        {
            "service_line": "rang_su",
            "angle": "Nụ cười tự nhiên và bảo tồn răng thật",
            "differentiation": "SmileUp không nói quá về biến đổi tức thì; tập trung thẩm mỹ tự nhiên và tư vấn phù hợp men răng, khớp cắn.",
            "marketing_analysis": "Khách hàng răng sứ muốn đẹp nhưng sợ bị giả, sợ mài răng nhiều và sợ nụ cười kém tự nhiên. Bài cần nhấn vào thăm khám và thiết kế cá nhân hóa.",
            "trend_angle": "Checklist: trước khi làm răng sứ, bạn nên hỏi bác sĩ 3 điều này.",
            "post_structure": "Hook -> 3 câu hỏi trước khi làm -> SmileUp solution -> trust proof -> CTA",
            "title": "Làm răng sứ đẹp không nên bắt đầu từ màu răng, mà từ tư vấn đúng",
            "body": (
                "Một nụ cười đẹp không chỉ là răng trắng. Đó là sự hài hòa với khuôn mặt, khớp cắn và tình trạng răng thật hiện có.\n\n"
                "Trước khi quyết định làm răng sứ, hãy hỏi rõ: răng thật có cần bảo tồn không, dáng răng nào hợp với khuôn mặt và kế hoạch chăm sóc sau phục hình như thế nào.\n\n"
                "SmileUp hướng tới thiết kế nụ cười tự nhiên, minh bạch vật liệu và giải thích rõ từng bước điều trị. Kết quả thẩm mỹ tùy thuộc tình trạng răng và chỉ định của bác sĩ."
            ),
            "hashtags": ["#SmileUp", "#RangSuThamMy", "#NuCuoiTuNhien", "#NhaKhoaThamMy"],
            "call_to_action": "Nhắn tin SmileUp để được tư vấn răng sứ theo tình trạng răng hiện tại.",
            "image_prompt": "Ảnh gốc/AI mới: khách hàng soi gương mỉm cười tự nhiên trong phòng khám SmileUp, logo SmileUp góc trên trái, tone trắng xanh.",
        },
        {
            "service_line": "trust",
            "angle": "Minh bạch chuyên môn thay vì giảm giá sốc",
            "differentiation": "Khác với ads đẩy ưu đãi, SmileUp xây niềm tin bằng quy trình, bác sĩ và tư vấn minh bạch.",
            "marketing_analysis": f"Thị trường đang nổi bật các chủ đề {topics}; SmileUp nên tách mình bằng thông điệp CMO: đúng chỉ định trước, ưu đãi sau.",
            "trend_angle": "Bài giáo dục dễ save: vì sao cùng là răng sứ/implant nhưng mỗi người cần phác đồ khác nhau?",
            "post_structure": "Hook -> insight thị trường -> quan điểm SmileUp -> 3 điểm minh bạch -> CTA",
            "title": "Cùng là răng sứ hay implant, vì sao mỗi người cần một phác đồ riêng?",
            "body": (
                "Trên Facebook, bạn có thể thấy rất nhiều quảng cáo nha khoa với ưu đãi hấp dẫn. Nhưng với SmileUp, câu hỏi đầu tiên không phải là giá bao nhiêu, mà là tình trạng của bạn phù hợp với phương án nào.\n\n"
                "Bác sĩ cần đánh giá nền răng, xương hàm, khớp cắn, mong muốn thẩm mỹ và khả năng chăm sóc sau điều trị. Khi các thông tin này rõ ràng, khách hàng mới có thể chọn phương án phù hợp và an tâm hơn.\n\n"
                "SmileUp theo đuổi sự minh bạch: tư vấn rõ, chi phí rõ, lưu ý rõ. Kết quả sẽ phụ thuộc vào tình trạng răng và chỉ định chuyên môn."
            ),
            "hashtags": ["#SmileUp", "#TuVanNhaKhoa", "#NhaKhoaMinhBach", "#RangSuImplant"],
            "call_to_action": "Gửi tình trạng răng của bạn cho SmileUp để được hẹn lịch thăm khám phù hợp.",
            "image_prompt": "Ảnh gốc/AI mới: bác sĩ SmileUp giải thích phác đồ trên tablet, không gian phòng khám hiện đại, logo SmileUp rõ nét.",
        },
        {
            "service_line": "reels",
            "angle": "Short-form hook để kéo bình luận",
            "differentiation": "SmileUp dùng câu hỏi tư vấn thật thay vì copy offer của đối thủ, phù hợp Reels và story.",
            "marketing_analysis": "Short-form cần một câu hỏi để khách tự nhận diện vấn đề và để lại comment/inbox.",
            "trend_angle": "Hook dạng câu hỏi: nếu mất 1 răng nhưng vẫn ăn được, có cần đi khám không?",
            "post_structure": "Question hook -> 3 dấu hiệu -> CTA comment/inbox",
            "title": "Mất 1 răng nhưng vẫn ăn được, có cần đi khám không?",
            "body": (
                "Câu trả lời ngắn: nên đi kiểm tra sớm.\n\n"
                "Vì khoảng trống sau mất răng có thể làm răng bên cạnh xô lệch, lực nhai thay đổi và xương hàm tiêu dần theo thời gian.\n\n"
                "Nếu bạn đang mất răng, đau khi nhai hoặc ngại cười vì khoảng trống trên hàm, hãy để bác sĩ SmileUp kiểm tra trước khi quyết định phương án. Mỗi tình trạng sẽ có chỉ định khác nhau."
            ),
            "hashtags": ["#SmileUp", "#HoiDapNhaKhoa", "#MatRang", "#Implant"],
            "call_to_action": "Comment 'IMPLANT' hoặc inbox SmileUp để được hẹn lịch tư vấn.",
            "image_prompt": "Ảnh gốc/AI mới: frame reels dọc, bác sĩ SmileUp chỉ vào câu hỏi text overlay, logo SmileUp góc trên trái, phòng khám sáng sạch.",
        },
    ]


def _offline_draft(state: AgentState) -> DraftContent:
    return _draft_from_variant(_offline_content_plan(state)[0])


def _dominant_topics(state: AgentState) -> str:
    counts: dict[str, int] = {}
    for insight in state.get("competitor_insights", []):
        for topic in insight.get("key_topics", []):
            counts[topic] = counts.get(topic, 0) + 1
    if not counts:
        return "răng sứ thẩm mỹ và implant cá nhân hóa"
    return ", ".join(topic.replace("_", " ") for topic, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:3])
