from graph.state import AgentState, ContentVariant, DraftContent
from tools.creative_generator import generate_creative_assets
from tools.gemini_client import GeminiUnavailable, generate_content_plan_with_gemini, generate_draft_with_gemini
from tools.openai_client import generate_text_with_openai
from utils import config
from utils.logger import get_logger


logger = get_logger(__name__)


def run_content_agent(state: AgentState) -> AgentState:
    logger.info("Content Agent creating campaign variants")
    if state.get("approval_status") == "needs_revision":
        state["revision_count"] = state.get("revision_count", 0) + 1

    try:
        variants, provider = _generate_content_plan_with_preferred_model(state)
        state["messages"].append({"role": "content", "content": f"Campaign plan created with {provider} ({len(variants)} variants)"})
    except (GeminiUnavailable, Exception) as exc:
        logger.warning("Gemini campaign generation failed, using fallback draft/plan: %s", exc)
        try:
            draft = generate_draft_with_gemini(state)
            variants = [_variant_from_draft(draft, "implant")]
            state["messages"].append({"role": "content", "content": f"Single draft created with Gemini ({exc})"})
        except Exception:
            variants = _offline_content_plan(state)
            state["messages"].append({"role": "content", "content": f"Campaign plan created locally ({exc})"})

    variants = _enforce_people_first_image_prompts(variants)
    state["content_plan"] = variants
    state["draft_content"] = _draft_from_variant(variants[0]) if variants else _offline_draft(state)
    creative_context = {
        "creative_image_mode": state.get("creative_image_mode", "auto"),
        "creative_upload_path": state.get("creative_upload_path", ""),
        "creative_upload_url": state.get("creative_upload_url", ""),
        "creative_reference_note": state.get("creative_reference_note", ""),
        "creative_reference_ad": state.get("creative_reference_ad", {}),
        "creative_reference_blueprint": state.get("creative_reference_blueprint", ""),
        "run_seed": state.get("run_seed", ""),
        "creative_variation_profile": state.get("creative_variation_profile", {}),
    }
    state["creative_assets"] = generate_creative_assets(variants, creative_context)
    if creative_context.get("creative_reference_blueprint"):
        state["creative_reference_blueprint"] = str(creative_context.get("creative_reference_blueprint") or "")
    if state["creative_assets"]:
        state["messages"].append({"role": "content", "content": f"Generated {len(state['creative_assets'])} branded SmileUp creative images"})
    elif creative_context["creative_image_mode"] == "text_only":
        state["messages"].append({"role": "content", "content": "Text-only mode selected; skipped creative image generation"})
    else:
        note = str(creative_context.get("creative_generation_note") or "Creative image generation did not return a usable image.")
        state["messages"].append({"role": "content", "content": note})

    state["approval_status"] = "pending"
    state["current_step"] = "content_creator"
    return state


def _enforce_people_first_image_prompts(variants: list[ContentVariant]) -> list[ContentVariant]:
    """Keep every image brief anchored in real doctor + patient scenes."""
    required = (
        " Bắt buộc ảnh photorealistic có người thật trong phòng khám nha khoa SmileUp: "
        "một bác sĩ Việt Nam mặc đồ lâm sàng đang tư vấn hoặc thăm khám cùng một bệnh nhân/khách hàng; "
        "không tạo ảnh chỉ có logo, icon răng, biểu tượng, poster chữ, banner, infographic, phòng khám trống hoặc layout trang trí."
    )
    for variant in variants:
        prompt = str(variant.get("image_prompt") or "").strip()
        if "photorealistic có người thật" not in prompt:
            variant["image_prompt"] = f"{prompt.rstrip('.')}.{required}" if prompt else required.strip()
    return variants


def _generate_content_plan_with_preferred_model(state: AgentState) -> tuple[list[ContentVariant], str]:
    if config.OPENAI_API_KEY:
        try:
            from tools.gemini_client import _build_campaign_prompt, _parse_content_plan

            text, model = generate_text_with_openai(
                _build_campaign_prompt(state),
                system="You are a senior Vietnamese dental marketing CMO copywriting agent. Return only valid JSON matching the requested schema.",
                temperature=0.72,
                timeout=120,
            )
            return _parse_content_plan(text), f"GPT ({model})"
        except Exception as exc:
            logger.warning("GPT campaign generation failed, trying Gemini: %s", exc)

    variants = generate_content_plan_with_gemini(state)
    return variants, "Gemini"


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
        "campaign_track": "ads_effective",
        "monthly_role": "Bài ads hiệu quả lấy SĐT",
        "source_ads_count": 0,
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
    source_ads_count = len(state.get("high_match_ads", []))
    plan: list[ContentVariant] = [
        {
            "campaign_track": "ads_effective",
            "monthly_role": "Tuyến ads hiệu quả: lấy SĐT và lịch tư vấn",
            "source_ads_count": source_ads_count,
            "service_line": "implant",
            "angle": "Ads chuyển đổi cho khách mất răng, sợ đau và sợ phát sinh chi phí",
            "differentiation": "Thay vì chạy theo ưu đãi sốc, SmileUp xin SĐT để tư vấn cá nhân hóa sau khi hỏi đúng tình trạng mất răng.",
            "marketing_analysis": "Nhóm khách mất răng thường để lại thông tin khi họ thấy được rủi ro trì hoãn, hiểu quy trình thăm khám và biết mình sẽ được gọi tư vấn riêng chứ không bị ép chốt.",
            "trend_angle": "Hook trực diện: mất răng càng lâu càng nên kiểm tra sớm trước khi chọn phương án.",
            "post_structure": "Hook -> dấu hiệu -> giải pháp implant SmileUp -> lưu ý thăm khám -> CTA",
            "title": "Mất răng lâu năm? Để lại SĐT để SmileUp tư vấn hướng xử lý phù hợp",
            "body": (
                "Mất 1 răng hay nhiều răng đều có thể làm lực nhai thay đổi, răng bên cạnh xô lệch và khiến bạn ngại ăn những món mình thích.\n\n"
                "Tại SmileUp, bác sĩ không tư vấn implant theo một công thức chung. Bạn sẽ được hỏi tình trạng mất răng, thời gian mất răng, cảm giác khi ăn nhai và các bệnh lý nền nếu có trước khi hẹn thăm khám.\n\n"
                "Nếu bạn đang phân vân có nên cấy implant không, hãy để lại SĐT. SmileUp sẽ gọi lại, hỏi nhanh tình trạng của bạn và gợi ý bước kiểm tra phù hợp. Kết quả và chỉ định điều trị phụ thuộc tình trạng răng miệng, cần bác sĩ thăm khám trực tiếp."
            ),
            "hashtags": ["#SmileUp", "#CayGhepImplant", "#TrongRangImplant", "#NhaKhoaUyTin"],
            "call_to_action": "Để lại SĐT hoặc inbox SmileUp, đội ngũ tư vấn sẽ gọi lại để hỏi tình trạng và hẹn lịch thăm khám phù hợp.",
            "image_prompt": "Ảnh gốc/AI mới: bác sĩ SmileUp tư vấn implant bên màn hình phim chụp, phòng khám sạch hiện đại, logo SmileUp góc trên trái.",
        },
        {
            "campaign_track": "ads_effective",
            "monthly_role": "Tuyến ads hiệu quả: lấy SĐT và lịch tư vấn",
            "source_ads_count": source_ads_count,
            "service_line": "rang_su",
            "angle": "Ads chuyển đổi cho khách muốn làm răng sứ nhưng sợ bị mài nhiều",
            "differentiation": "SmileUp không bán nụ cười cấp tốc; nhấn vào kiểm tra nền răng, dáng răng tự nhiên và bảo tồn mô răng thật khi phù hợp.",
            "marketing_analysis": "Khách hàng răng sứ để lại SĐT khi họ cảm thấy được bảo vệ khỏi quyết định sai: không bị làm quá tay, biết cần hỏi gì và được tư vấn theo khuôn mặt/tình trạng răng.",
            "trend_angle": "Checklist ngắn: trước khi làm răng sứ, hỏi bác sĩ 3 điều để tránh hối tiếc.",
            "post_structure": "Hook -> 3 câu hỏi trước khi làm -> SmileUp solution -> trust proof -> CTA",
            "title": "Muốn làm răng sứ tự nhiên? Đừng chọn màu răng trước khi được tư vấn",
            "body": (
                "Răng sứ đẹp không chỉ là trắng hơn. Điều quan trọng là dáng răng có hợp khuôn mặt không, nền răng thật có cần bảo tồn không và khớp cắn có được kiểm tra kỹ không.\n\n"
                "Tại SmileUp, tư vấn răng sứ bắt đầu từ tình trạng răng hiện tại, mong muốn thẩm mỹ và kế hoạch chăm sóc sau phục hình. Không phải ai cũng cần bọc sứ, và không phải trường hợp nào cũng nên làm ngay.\n\n"
                "Bạn muốn biết trường hợp của mình nên bắt đầu từ đâu? Để lại SĐT, SmileUp sẽ gọi lại để hỏi tình trạng và hướng dẫn bước thăm khám phù hợp. Kết quả thẩm mỹ phụ thuộc tình trạng răng miệng và chỉ định của bác sĩ."
            ),
            "hashtags": ["#SmileUp", "#RangSuThamMy", "#NuCuoiTuNhien", "#NhaKhoaThamMy"],
            "call_to_action": "Để lại SĐT để SmileUp gọi lại tư vấn răng sứ theo tình trạng răng hiện tại.",
            "image_prompt": "Ảnh gốc/AI mới: khách hàng soi gương mỉm cười tự nhiên trong phòng khám SmileUp, logo SmileUp góc trên trái, tone trắng xanh.",
        },
        {
            "campaign_track": "ads_effective",
            "monthly_role": "Tuyến ads hiệu quả: lấy SĐT và lịch tư vấn",
            "source_ads_count": source_ads_count,
            "service_line": "phuc_hinh_su",
            "angle": "Ads chuyển đổi cho khách răng yếu, răng vỡ hoặc phục hình lại",
            "differentiation": "SmileUp nhấn vào kiểm tra nền răng và kế hoạch phục hình rõ ràng, không hứa làm nhanh cho mọi trường hợp.",
            "marketing_analysis": "Nhóm khách đã vỡ răng, răng yếu hoặc từng làm răng trước đó thường cần một lý do đủ chắc để gửi số điện thoại: họ muốn biết còn giữ được răng thật không và chi phí có phát sinh không.",
            "trend_angle": "Góc cảnh báo mềm: răng vỡ/mẻ không nên tự chọn phương án khi chưa kiểm tra nền răng.",
            "post_structure": "Hook -> tình huống răng yếu/vỡ -> thăm khám SmileUp -> phương án cá nhân hóa -> CTA SĐT",
            "title": "Răng yếu, răng vỡ: để lại SĐT để SmileUp tư vấn bước kiểm tra đầu tiên",
            "body": (
                "Răng vỡ, mẻ lớn hoặc đã từng phục hình nhưng ăn nhai không thoải mái là những trường hợp không nên tự chọn phương án chỉ qua quảng cáo.\n\n"
                "Tại SmileUp, bác sĩ cần kiểm tra nền răng, khớp cắn và mức độ còn lại của mô răng thật trước khi tư vấn phục hình sứ, răng sứ hay phương án khác phù hợp hơn.\n\n"
                "Bạn có thể để lại SĐT, SmileUp sẽ gọi lại để hỏi tình trạng hiện tại và hẹn lịch thăm khám nếu cần. Kết quả và phương án điều trị phụ thuộc tình trạng răng miệng thực tế sau khi bác sĩ kiểm tra."
            ),
            "hashtags": ["#SmileUp", "#PhucHinhRangSu", "#RangSu", "#TuVanNhaKhoa"],
            "call_to_action": "Để lại SĐT để SmileUp gọi lại tư vấn bước kiểm tra phù hợp cho tình trạng răng yếu/vỡ.",
            "image_prompt": "Ảnh gốc/AI mới: bác sĩ SmileUp trao đổi với khách hàng về phục hình răng sứ trên màn hình tư vấn, logo SmileUp góc trái, phòng khám hiện đại.",
        },
        {
            "campaign_track": "page_care",
            "monthly_role": "Tuyến chăm sóc page: nuôi niềm tin và tăng tương tác",
            "service_line": "trust",
            "angle": "Minh bạch chuyên môn thay vì giảm giá sốc",
            "differentiation": "Tuyến chăm sóc page giúp SmileUp được nhớ như phòng khám tư vấn kỹ, không chỉ là nơi đăng ưu đãi.",
            "marketing_analysis": f"Thị trường đang nổi bật các chủ đề {topics}; bài nuôi page nên giúp khách lưu lại và bình luận tình trạng của họ.",
            "trend_angle": "Bài giáo dục dễ save: vì sao cùng là răng sứ/implant nhưng mỗi người cần phác đồ khác nhau?",
            "post_structure": "Hook -> insight thị trường -> quan điểm SmileUp -> 3 điểm minh bạch -> CTA",
            "title": "Cùng là răng sứ hay implant, vì sao mỗi người cần một phác đồ riêng?",
            "body": (
                "Trên Facebook, bạn có thể thấy rất nhiều quảng cáo nha khoa với ưu đãi hấp dẫn. Nhưng với SmileUp, câu hỏi đầu tiên không phải là giá bao nhiêu, mà là tình trạng của bạn phù hợp với phương án nào.\n\n"
                "Bác sĩ cần đánh giá nền răng, xương hàm, khớp cắn, mong muốn thẩm mỹ và khả năng chăm sóc sau điều trị. Khi các thông tin này rõ ràng, khách hàng mới có thể chọn phương án phù hợp và an tâm hơn.\n\n"
                "SmileUp theo đuổi sự minh bạch: tư vấn rõ, chi phí rõ, lưu ý rõ. Kết quả sẽ phụ thuộc vào tình trạng răng và chỉ định chuyên môn."
            ),
            "hashtags": ["#SmileUp", "#TuVanNhaKhoa", "#NhaKhoaMinhBach", "#RangSuImplant"],
            "call_to_action": "Bạn đang phân vân răng sứ hay implant? Bình luận câu hỏi của bạn để SmileUp gợi ý điều nên kiểm tra trước.",
            "image_prompt": "Ảnh gốc/AI mới: bác sĩ SmileUp giải thích phác đồ trên tablet, không gian phòng khám hiện đại, logo SmileUp rõ nét.",
        },
        {
            "campaign_track": "page_care",
            "monthly_role": "Tuyến chăm sóc page: nuôi niềm tin và tăng tương tác",
            "service_line": "reels",
            "angle": "Short-form hook để kéo bình luận",
            "differentiation": "Bài chăm sóc page dùng câu hỏi đời thường để kéo bình luận chất lượng, không ép khách để SĐT.",
            "marketing_analysis": "Short-form cần một câu hỏi để khách tự nhận diện vấn đề, bình luận và lưu lại trước khi chuyển đổi ở bài ads.",
            "trend_angle": "Hook dạng câu hỏi: nếu mất 1 răng nhưng vẫn ăn được, có cần đi khám không?",
            "post_structure": "Question hook -> 3 dấu hiệu -> CTA comment/inbox",
            "title": "Mất 1 răng nhưng vẫn ăn được, có cần đi khám không?",
            "body": (
                "Câu trả lời ngắn: nên đi kiểm tra sớm.\n\n"
                "Vì khoảng trống sau mất răng có thể làm răng bên cạnh xô lệch, lực nhai thay đổi và xương hàm tiêu dần theo thời gian.\n\n"
                "Nếu bạn đang mất răng, đau khi nhai hoặc ngại cười vì khoảng trống trên hàm, hãy để bác sĩ SmileUp kiểm tra trước khi quyết định phương án. Mỗi tình trạng sẽ có chỉ định khác nhau."
            ),
            "hashtags": ["#SmileUp", "#HoiDapNhaKhoa", "#MatRang", "#Implant"],
            "call_to_action": "Comment tình trạng răng của bạn hoặc lưu bài này để nhớ kiểm tra khi có thời gian.",
            "image_prompt": "Ảnh gốc/AI mới: frame reels dọc, bác sĩ SmileUp chỉ vào câu hỏi text overlay, logo SmileUp góc trên trái, phòng khám sáng sạch.",
        },
    ]
    return _vary_offline_plan(plan, state.get("run_seed", ""))


def _vary_offline_plan(plan: list[ContentVariant], run_seed: str) -> list[ContentVariant]:
    seed_value = sum(ord(char) for char in str(run_seed)) if run_seed else 0
    variation_index = seed_value % 3
    hooks = [
        {
            "implant": "Mất răng lâu năm? Để lại SĐT để SmileUp tư vấn hướng xử lý phù hợp",
            "rang_su": "Muốn làm răng sứ tự nhiên? Đừng chọn màu răng trước khi được tư vấn",
            "phuc_hinh_su": "Răng yếu, răng vỡ: để lại SĐT để SmileUp tư vấn bước kiểm tra đầu tiên",
            "trust": "Cùng là răng sứ hay implant, vì sao mỗi người cần một phác đồ riêng?",
            "reels": "Mất 1 răng nhưng vẫn ăn được, có cần đi khám không?",
        },
        {
            "implant": "Trước khi cấy implant, hãy để SmileUp gọi lại hỏi đúng tình trạng của bạn",
            "rang_su": "Sợ làm răng sứ bị giả? Để lại SĐT để được tư vấn dáng răng phù hợp",
            "phuc_hinh_su": "Răng từng làm rồi vẫn khó chịu? Nhắn SĐT để SmileUp hỏi đúng vấn đề",
            "trust": "Đừng chọn nha khoa chỉ vì ưu đãi: hãy hỏi rõ phác đồ trước",
            "reels": "Một khoảng trống mất răng có thể kéo theo điều gì?",
        },
        {
            "implant": "Mất răng không chỉ là chuyện thẩm mỹ: inbox SĐT để được tư vấn bước kiểm tra",
            "rang_su": "Muốn làm răng sứ, điều đầu tiên là biết răng thật còn bảo tồn được bao nhiêu",
            "phuc_hinh_su": "Răng vỡ/mẻ lớn nên phục hình thế nào? Để lại SĐT để được tư vấn bước đầu",
            "trust": "Một kế hoạch nha khoa tốt phải nói rõ cả giới hạn và rủi ro",
            "reels": "Nếu đang phân vân răng sứ hay implant, bắt đầu từ đâu?",
        },
    ]
    ads_ctas = [
        "Để lại SĐT hoặc inbox SmileUp, đội ngũ tư vấn sẽ gọi lại để hỏi tình trạng và hẹn lịch thăm khám phù hợp.",
        "Nhắn SĐT cho SmileUp để được gọi lại tư vấn bước kiểm tra phù hợp trước khi quyết định.",
        "Gửi số điện thoại và tình trạng răng hiện tại, SmileUp sẽ liên hệ tư vấn cá nhân hóa cho bạn.",
    ]
    care_ctas = [
        "Bình luận câu hỏi của bạn để SmileUp gợi ý điều nên kiểm tra trước.",
        "Lưu bài này lại nếu bạn đang cân nhắc răng sứ hoặc implant trong thời gian tới.",
        "Bạn từng lo điều gì nhất khi đi nha khoa? Comment để SmileUp giải đáp ở bài sau.",
    ]
    trend_notes = [
        "Checklist dễ lưu: các câu hỏi cần hỏi bác sĩ trước khi quyết định.",
        "Góc ngược số đông: không phải ai cũng cần làm ngay, cần đúng chỉ định trước.",
        "Tình huống đời thường: khách sợ đau, sợ chi phí phát sinh và sợ bị tư vấn quá tay.",
    ]

    varied: list[ContentVariant] = []
    for index, variant in enumerate(plan):
        service = variant.get("service_line", "post")
        updated = dict(variant)
        updated["title"] = hooks[variation_index].get(service, variant.get("title", ""))
        updated["trend_angle"] = trend_notes[(variation_index + index) % len(trend_notes)]
        ctas = ads_ctas if updated.get("campaign_track") == "ads_effective" else care_ctas
        updated["call_to_action"] = ctas[(variation_index + index) % len(ctas)]
        updated["angle"] = f"{variant.get('angle', '')} · variation {variation_index + 1}".strip(" ·")
        varied.append(updated)
    return varied


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
