from graph.state import AgentState
from tools.compliance import compliance_flags
from utils.logger import get_logger


logger = get_logger(__name__)


def run_manager_agent(state: AgentState) -> AgentState:
    logger.info("Manager Agent reviewing draft and campaign plan")
    draft = state.get("draft_content")
    if not draft:
        state["approval_status"] = "rejected"
        state["manager_feedback"] = "Chua co ban nhap de duyet."
    else:
        flags = compliance_flags(draft)
        for index, variant in enumerate(state.get("content_plan", []), start=1):
            for flag in compliance_flags(variant):
                flags.append(f"variant {index}: {flag}")

        word_count = len(draft["body"].split())
        if flags:
            state["approval_status"] = "needs_revision" if state.get("revision_count", 0) < 3 else "rejected"
            state["manager_feedback"] = "Can sua claim rui ro: " + ", ".join(flags)
        elif word_count < 110:
            state["approval_status"] = "needs_revision"
            state["manager_feedback"] = "Bai viet con ngan, can bo sung insight, dieu kien tu van va luu y tham kham."
        elif not draft.get("call_to_action"):
            state["approval_status"] = "needs_revision"
            state["manager_feedback"] = "Thieu CTA dat lich/tu van."
        else:
            state["approval_status"] = "approved"
            state["manager_feedback"] = "Duyet: noi dung ro loi ich, CTA an toan, khong cam ket qua muc."

    state["daily_strategy"] = _daily_strategy(state)
    state["daily_report"] = _daily_report(state)
    state["current_step"] = "manager_review"
    state["messages"].append({"role": "manager", "content": state["approval_status"]})
    return state


def _daily_strategy(state: AgentState) -> str:
    return (
        "Thong diep chu dao: SmileUp khac biet bang tu van ca nhan hoa, minh bach chi dinh va an toan y khoa.\n"
        "Dich vu trong tam: rang su tham my, phuc hinh rang su, cay ghep implant.\n"
        f"Insight thi truong: {state.get('market_trend_summary', '')}\n"
        f"{state.get('ad_library_report', '')}\n"
        f"{state.get('facebook_trend_analysis', '')}\n"
        f"{state.get('strategic_direction', '')}\n"
        f"{state.get('compliance_report', '')}\n"
        f"{_content_plan_summary(state)}\n"
        f"{_creative_asset_summary(state)}\n"
        "3-5 hanh dong hom nay:\n"
        "- Dang/len lich cac bien the bai viet theo tung tru cot: implant, rang su, trust, reels.\n"
        "- Ghim CTA inbox/hotline va kich ban hoi nhanh: tinh trang rang, mong muon, thoi gian ranh de tham kham.\n"
        "- Dung creative goc co logo SmileUp; khong dung anh/nhan dien cua doi thu.\n"
        "- Theo doi comment trong 2 gio dau sau dang va chuyen lead nong sang inbox.\n"
        "Rui ro can tranh: claim tuyet doi, before/after thieu consent, rebrand anh doi thu."
    )


def _daily_report(state: AgentState) -> str:
    insights = state.get("competitor_insights", [])
    status = state.get("approval_status", "pending")
    return (
        f"Tong quan insight doi thu: da phan tich {len(insights)} nguon, uu tien rang su, implant, uu dai, tu van va CTA.\n"
        f"Noi dung hien tai: {status}.\n"
        f"Ly do quyet dinh: {state.get('manager_feedback', '')}\n"
        f"Ad Library: {state.get('ad_library_report', '').replace(chr(10), ' ')}\n"
        f"Trend Facebook: {state.get('facebook_trend_analysis', '').replace(chr(10), ' ')}\n"
        f"Visual brief: {state.get('visual_creative_brief', '').replace(chr(10), ' ')}\n"
        f"Agent strategy: {state.get('strategic_direction', '').replace(chr(10), ' ')}\n"
        f"Compliance: {state.get('compliance_report', '').replace(chr(10), ' ')}\n"
        f"Content variants: {_content_plan_summary(state).replace(chr(10), ' ')}\n"
        f"Creative assets: {_creative_asset_summary(state).replace(chr(10), ' ')}\n"
        "Checklist compliance: khong claim tuyet doi, CTA la dat lich tu van, co luu y ket qua tuy tinh trang rang.\n"
        "Khuyen nghi ngay mai: so sanh hieu qua bai rang su voi bai implant, uu tien hook co van de cu the va visual goc cua SmileUp."
    )


def _content_plan_summary(state: AgentState) -> str:
    variants = state.get("content_plan", [])
    if not variants:
        return "Content plan: chua co bien the bai viet."
    lines = ["Content plan CMO:"]
    for index, variant in enumerate(variants, start=1):
        lines.append(
            f"- {index}. {variant.get('service_line', 'post')}: {variant.get('title', '')} | Khac biet: {variant.get('differentiation', '')}"
        )
    return "\n".join(lines)


def _creative_asset_summary(state: AgentState) -> str:
    assets = state.get("creative_assets", [])
    if not assets:
        return "Creative assets: chua sinh anh branded."
    lines = ["Creative assets SmileUp:"]
    for asset in assets:
        lines.append(f"- {asset.get('service_line', 'post')}: {asset.get('image_path', '')}")
    return "\n".join(lines)
