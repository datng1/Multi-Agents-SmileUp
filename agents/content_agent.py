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
    state["creative_assets"] = generate_creative_assets(variants)
    if state["creative_assets"]:
        state["messages"].append({"role": "content", "content": f"Generated {len(state['creative_assets'])} branded SmileUp creative images"})

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
        "differentiation": "SmileUp khac biet bang tu van ca nhan hoa, minh bach chi dinh va khong chay dua bang claim qua da.",
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
            "angle": "Mat rang lau nam va an nhai kho khan",
            "differentiation": "Khac voi ads gia soc, SmileUp dan bang tu van dung chi dinh, phim chup va phac do ca nhan hoa.",
            "marketing_analysis": "Nhom khach hang mat rang so dau, so chi phi phat sinh va so cay sai chi dinh. Bai can tao niem tin bang quy trinh tham kham ro rang.",
            "trend_angle": "Cau hoi goi dung noi dau: mat rang lau nam co dang lam ban ngai an nhai?",
            "post_structure": "Hook -> dau hieu -> giai phap implant SmileUp -> luu y tham kham -> CTA",
            "title": "Mat rang lau nam: dung de viec an nhai tro thanh noi lo moi ngay",
            "body": (
                "Mat 1 rang hay nhieu rang khong chi lam ban ngai cuoi, ma con co the anh huong den kha nang an nhai va cac rang ben canh.\n\n"
                "Tai SmileUp, tu van implant bat dau bang kiem tra tinh trang rang, xuong ham va suc khoe tong quat. Bac si se giai thich ro khi nao nen cay implant, khi nao can dieu tri nen truoc, va chi phi du kien theo tung phuong an.\n\n"
                "Diem quan trong khong phai la chon goi dat hay re, ma la chon dung chi dinh cho chinh tinh trang cua ban. Ket qua va thoi gian phuc hoi co the khac nhau tuy tung nguoi, vi vay thien kham truc tiep la buoc can co."
            ),
            "hashtags": ["#SmileUp", "#CayGhepImplant", "#TrongRangImplant", "#NhaKhoaUyTin"],
            "call_to_action": "Inbox SmileUp de dat lich tham kham implant va nhan tu van phac do phu hop.",
            "image_prompt": "Anh goc/AI moi: bac si SmileUp tu van implant ben man hinh phim chup, phong kham sach hien dai, logo SmileUp goc tren trai.",
        },
        {
            "service_line": "rang_su",
            "angle": "Nu cuoi tu nhien va bao ton rang that",
            "differentiation": "SmileUp khong noi qua ve bien doi tuc thi; tap trung tham my tu nhien va tu van phu hop men rang, khop can.",
            "marketing_analysis": "Khach hang rang su muon dep nhung so bi gia, so mai rang nhieu va so nu cuoi kem tu nhien. Bai can nhan vao tham kham va thiet ke ca nhan hoa.",
            "trend_angle": "Checklist: truoc khi lam rang su, ban nen hoi bac si 3 dieu nay.",
            "post_structure": "Hook -> 3 cau hoi truoc khi lam -> SmileUp solution -> trust proof -> CTA",
            "title": "Lam rang su dep khong nen bat dau tu mau rang, ma tu tu van dung",
            "body": (
                "Mot nu cuoi dep khong chi la rang trang. Do la su hai hoa voi khuon mat, khop can va tinh trang rang that hien co.\n\n"
                "Truoc khi quyet dinh lam rang su, hay hoi ro: rang that co can bao ton khong, dang rang nao hop voi khuon mat, va ke hoach cham soc sau phuc hinh nhu the nao.\n\n"
                "SmileUp huong toi thiet ke nu cuoi tu nhien, minh bach vat lieu va giai thich ro tung buoc dieu tri. Ket qua tham my tuy thuoc tinh trang rang va chi dinh cua bac si."
            ),
            "hashtags": ["#SmileUp", "#RangSuThamMy", "#NuCuoiTuNhien", "#NhaKhoaThamMy"],
            "call_to_action": "Nhan tin SmileUp de duoc tu van rang su theo tinh trang rang hien tai.",
            "image_prompt": "Anh goc/AI moi: khach hang soi guong mim cuoi tu nhien trong phong kham SmileUp, logo SmileUp goc tren trai, tone trang xanh.",
        },
        {
            "service_line": "trust",
            "angle": "Minh bach chuyen mon thay vi giam gia soc",
            "differentiation": "Khac voi ads day uu dai, SmileUp xay niem tin bang quy trinh, bac si va tu van minh bach.",
            "marketing_analysis": f"Thi truong dang noi bat cac chu de {topics}; SmileUp nen tach minh bang thong diep CMO: dung chi dinh truoc, uu dai sau.",
            "trend_angle": "Bai giao duc de save: vi sao cung la rang su/implant nhung moi nguoi can phac do khac nhau?",
            "post_structure": "Hook -> insight thi truong -> quan diem SmileUp -> 3 diem minh bach -> CTA",
            "title": "Cung la rang su hay implant, vi sao moi nguoi can mot phac do rieng?",
            "body": (
                "Tren Facebook, ban co the thay rat nhieu quang cao nha khoa voi uu dai hap dan. Nhung voi SmileUp, cau hoi dau tien khong phai la gia bao nhieu, ma la tinh trang cua ban co phu hop voi phuong an nao.\n\n"
                "Bac si can danh gia nen rang, xuong ham, khop can, mong muon tham my va kha nang cham soc sau dieu tri. Khi cac thong tin nay ro rang, khach hang moi co the chon phuong an phu hop va an tam hon.\n\n"
                "SmileUp theo duoi su minh bach: tu van ro, chi phi ro, luu y ro. Ket qua se phu thuoc vao tinh trang rang va chi dinh chuyen mon."
            ),
            "hashtags": ["#SmileUp", "#TuVanNhaKhoa", "#NhaKhoaMinhBach", "#RangSuImplant"],
            "call_to_action": "Gui tinh trang rang cua ban cho SmileUp de duoc hen lich tham kham phu hop.",
            "image_prompt": "Anh goc/AI moi: bac si SmileUp giai thich phac do tren tablet, khong gian phong kham hien dai, logo SmileUp ro net.",
        },
        {
            "service_line": "reels",
            "angle": "Short-form hook de keo binh luan",
            "differentiation": "SmileUp dung cau hoi tu van that thay vi copy offer cua doi thu, phu hop Reels va story.",
            "marketing_analysis": "Short-form can mot cau hoi de khach tu nhan dien van de va de lai comment/inbox.",
            "trend_angle": "Hook dang cau hoi: neu mat 1 rang nhung van an duoc, co can di kham khong?",
            "post_structure": "Question hook -> 3 dau hieu -> CTA comment/inbox",
            "title": "Mat 1 rang nhung van an duoc, co can di kham khong?",
            "body": (
                "Cau tra loi ngan: nen di kiem tra som.\n\n"
                "Vi khoang trong sau mat rang co the lam rang ben canh xoe lech, luc nhai thay doi va xuong ham tieu dan theo thoi gian.\n\n"
                "Neu ban dang mat rang, dau khi nhai, hoac ngai cuoi vi khoang trong tren ham, hay de bac si SmileUp kiem tra truoc khi quyet dinh phuong an. Moi tinh trang se co chi dinh khac nhau."
            ),
            "hashtags": ["#SmileUp", "#HoiDapNhaKhoa", "#MatRang", "#Implant"],
            "call_to_action": "Comment 'IMPLANT' hoac inbox SmileUp de duoc hen lich tu van.",
            "image_prompt": "Anh goc/AI moi: frame reels doc, bac si SmileUp chi vao cau hoi text overlay, logo SmileUp goc tren trai, phong kham sang sach.",
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
        return "rang su tham my va implant ca nhan hoa"
    return ", ".join(topic.replace("_", " ") for topic, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:3])
