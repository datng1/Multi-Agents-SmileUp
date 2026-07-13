from __future__ import annotations

import hashlib
import json
from datetime import datetime

from graph.state import AgentState, ApprovalGate, ProductionTask
from tools.campaign_intelligence import analyze_market_campaigns, build_revenue_strategy
from utils.logger import get_logger


logger = get_logger(__name__)


REQUIRED_REPORT_FIELDS = (
    "text_insight_report",
    "facebook_trend_analysis",
    "visual_insight_report",
    "video_insight_report",
    "strategic_direction",
    "compliance_report",
)


def run_manager_agent(state: AgentState) -> AgentState:
    logger.info("CMO Agent building the monthly media campaign")
    market_intelligence = state.get("market_campaign_intelligence") or analyze_market_campaigns(
        state.get("ad_library_ads", []),
        focus_keyword=state.get("ad_library_keywords", ""),
        configured_competitor_pages=len(state.get("ad_library_competitor_urls", [])),
        scan_target=int(state.get("ad_library_max_ads", 100) or 100),
    )
    missing = _missing_evidence(state, market_intelligence)
    ready = not missing
    revenue_strategy = build_revenue_strategy(
        state.get("ad_library_keywords", ""), market_intelligence, state.get("business_economics", {})
    )
    monthly_campaign = _monthly_campaign(state, market_intelligence, revenue_strategy)
    brand_platform = _brand_platform(state)
    weeks = _campaign_weeks(state, monthly_campaign, brand_platform, ready)
    tasks = [assignment for week in weeks for assignment in week["assignments"]]
    gates = _approval_gates()
    workflow_id = _workflow_id(state)

    workflow = {
        "workflow_id": workflow_id,
        "status": "ready_for_dispatch" if ready else "needs_research",
        "focus_keyword": state.get("ad_library_keywords", ""),
        "planning_horizon": "1 tháng / 4 tuần",
        "objective": state.get("cmo_objective", ""),
        "source_ads_count": len(state.get("ad_library_ads", [])),
        "high_match_ads_count": len(state.get("high_match_ads", [])),
        "team_roles": ["Biên kịch", "Đạo diễn AI", "Video Editor"],
        "market_intelligence": market_intelligence,
        "revenue_strategy": revenue_strategy,
        "monthly_campaign": monthly_campaign,
        "brand_platform": brand_platform,
        "weeks": weeks,
        "tasks": tasks,
        "approval_gates": gates,
        "metrics": _success_metrics(),
        "risks": _production_risks(state, missing),
        "operating_rules": [
            "CMO chọn một campaign thesis cho tháng và chia thành bốn giai đoạn tuần rõ ràng; ứng dụng không đăng bài.",
            "Mỗi tuần ba vai trò bàn giao tuần tự: Biên kịch -> Đạo diễn AI -> Video Editor.",
            "Tài sản đối thủ chỉ dùng làm dữ liệu tham chiếu, không sao chép caption, hình ảnh hoặc nhận diện.",
            "Mọi nội dung nha khoa phải qua kiểm tra chuyên môn và quyền sử dụng trước khi bàn giao.",
        ],
    }
    state["media_production_workflow"] = workflow
    state["media_production_brief"] = _production_brief(state, workflow, missing)
    state["production_handoff"] = _handoff(workflow, missing)
    state["cmo_campaign_brief"] = state["media_production_brief"]
    state["cmo_decision_graph"] = _decision_graph(tasks, gates, ready)
    state["cmo_graph_summary"] = _graph_summary(state["cmo_decision_graph"])

    if ready:
        state["approval_status"] = "approved"
        state["cmo_decision"] = "READY_FOR_PRODUCTION"
        state["cmo_next_action"] = "dispatch"
        state["cmo_feedback"] = (
            f"Đã chốt chiến dịch 1 tháng cho '{workflow['focus_keyword']}', chia 4 tuần và giao việc cho 3 vai trò."
        )
    else:
        state["approval_status"] = "needs_revision"
        state["cmo_decision"] = "NEEDS_MORE_RESEARCH"
        state["cmo_next_action"] = "rescan"
        state["cmo_feedback"] = "Chưa giao sản xuất: " + "; ".join(missing)

    state["manager_feedback"] = state["cmo_feedback"]
    state["daily_strategy"] = _daily_strategy(state)
    state["daily_report"] = _daily_report(state)
    state["current_step"] = "manager_review"
    state["messages"].append(
        {
            "role": "cmo",
            "content": f"{state['cmo_decision']}: {state['cmo_feedback']}",
        }
    )
    return state


def _missing_evidence(state: AgentState, market_intelligence: dict | None = None) -> list[str]:
    missing: list[str] = []
    ad_count = len(state.get("ad_library_ads", []))
    if ad_count < 20:
        missing.append(f"cần đủ 20 ads tham chiếu, hiện có {ad_count}")
    labels = {
        "text_insight_report": "thiếu text insight",
        "facebook_trend_analysis": "thiếu trend analysis",
        "visual_insight_report": "thiếu visual analysis",
        "video_insight_report": "thiếu video analysis",
        "strategic_direction": "thiếu strategic direction",
        "compliance_report": "thiếu compliance guardrails",
    }
    for field in REQUIRED_REPORT_FIELDS:
        if not str(state.get(field, "")).strip():
            missing.append(labels[field])
    if int(state.get("hardness_score", 0) or 0) < 70:
        missing.append("evidence readiness dưới 70/100")
    coverage = (market_intelligence or state.get("market_campaign_intelligence") or {}).get("coverage", {})
    if int(coverage.get("coverage_score", 0) or 0) < 45:
        missing.append(f"độ phủ thị trường dưới 45/100, hiện có {coverage.get('coverage_score', 0)}/100")
    return missing


def _monthly_campaign(state: AgentState, market_intelligence: dict, revenue_strategy: dict) -> dict:
    keyword = str(state.get("ad_library_keywords", "")).strip() or "dịch vụ nha khoa trọng tâm"
    ads = state.get("ad_library_ads", [])
    ads_count = len(ads)
    high_match_count = len(state.get("high_match_ads", []))
    evidence_signals = _evidence_signals(state)
    selected_signal = evidence_signals[0]
    analyzed_at = str(state.get("ad_library_scanned_at", "")).strip() or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    scan_id = str(state.get("ad_library_scan_id", "")).strip() or _evidence_scan_id(keyword, ads)
    reference_pages = _unique([str(ad.get("page_name", "")) for ad in ads])[:6]
    message_samples = _unique([str(ad.get("ad_text", ""))[:180] for ad in ads])[:3]
    opportunity = market_intelligence.get("selected_opportunity") or {}
    coverage = market_intelligence.get("coverage") or {}
    return {
        "focus_topic": keyword,
        "campaign_name": f"SmileUp | Hiểu đúng về {keyword}",
        "campaign_thesis": (
            f"Trong một tháng, đưa khách hàng từ nhận diện nhu cầu đến sẵn sàng tư vấn về '{keyword}' bằng nội dung "
            f"minh bạch, có chuyên môn và không gây áp lực. Khoảng trống được chọn: "
            f"{opportunity.get('strategic_gap', selected_signal)} Tín hiệu nội dung ưu tiên: {selected_signal}"
        ),
        "business_goal": revenue_strategy.get("objective", "Tăng lịch tư vấn đủ điều kiện và lợi nhuận theo ca."),
        "target_audience": f"Người đang cân nhắc '{keyword}', còn băn khoăn về độ phù hợp, quy trình, rủi ro và chi phí.",
        "meta_evidence": {
            "source": "Meta Ad Library active ads - lượt quét hiện tại",
            "scan_id": scan_id,
            "analyzed_at": analyzed_at,
            "scan_mode": state.get("ad_library_scan_mode", "auto"),
            "basis": (
                f"Mục tiêu quét tối đa 100 ads, ngưỡng evidence tối thiểu 20; nhận được {ads_count} ads công khai, "
                f"trong đó {high_match_count} ads có mức độ liên quan cao. Tín hiệu được chọn: {selected_signal}"
            ),
            "signals": evidence_signals,
            "selected_signal": selected_signal,
            "reference_pages": reference_pages,
            "message_samples": message_samples,
            "coverage": coverage,
            "caveat": (
                "Ads công khai phản ánh tín hiệu thông điệp và mức độ cạnh tranh; đây không phải bằng chứng về doanh thu, "
                "tỷ lệ chuyển đổi hoặc hiệu quả thực tế của đối thủ."
            ),
        },
        "not_recommended": [
            "Không đổi trọng tâm dịch vụ giữa tháng nếu chưa có evidence mới.",
            "Không sao chép quảng cáo đối thủ hoặc dùng claim tuyệt đối.",
            "Không kết luận một thông điệp hiệu quả chỉ vì xuất hiện nhiều trong Ad Library.",
        ],
    }


def _evidence_signals(state: AgentState, limit: int = 4) -> list[str]:
    reports = (
        state.get("monthly_strategy", ""),
        state.get("strategic_direction", ""),
        state.get("text_insight_report", ""),
        state.get("facebook_trend_analysis", ""),
        state.get("video_insight_report", ""),
        state.get("visual_insight_report", ""),
    )
    skipped_prefixes = (
        "focus keyword:",
        "chiến dịch media 1 tháng",
        "định hướng media 7 ngày",
        "strategic direction agent:",
    )
    signals: list[str] = []
    for report in reports:
        for raw_line in str(report or "").splitlines():
            line = raw_line.strip().lstrip("-• ").strip()
            if len(line) < 20 or line.lower().startswith(skipped_prefixes):
                continue
            signal = line[:280].rstrip()
            if signal not in signals:
                signals.append(signal)
            if len(signals) == limit:
                return signals
    fallback = "Chưa có tín hiệu nội dung đủ rõ; giữ hướng tư vấn nền và không suy diễn hiệu quả."
    return signals or [fallback]


def _brand_platform(state: AgentState) -> dict:
    keyword = str(state.get("ad_library_keywords", "")).strip()
    return {
        "brand_idea": "SmileUp - Hiểu đúng rồi hãy chọn",
        "positioning": f"Thương hiệu nha khoa đồng hành giúp khách hiểu đúng tình trạng và lựa chọn phù hợp trước khi quyết định {keyword}.",
        "promise": "Tư vấn rõ chỉ định, nói thật về giới hạn và đặt sự phù hợp của khách hàng trước áp lực bán hàng.",
        "voice": ["Bình tĩnh và dễ hiểu", "Có chuyên môn nhưng không giáo điều", "Minh bạch, không hù dọa", "Tôn trọng quyền lựa chọn"],
        "visual_system": [
            "Giữ xanh cyan, xanh lam và nền trắng từ logo SmileUp làm mã màu nhận diện.",
            "Dùng motif cánh hoa từ logo làm dấu chuyển cảnh hoặc khung thông tin, không trang trí dày.",
            "Ưu tiên bác sĩ tư vấn, phim chụp và không gian phòng khám thật; ánh sáng sạch, da người tự nhiên.",
            "Text on screen ngắn, tương phản cao, cùng một vị trí và nhịp xuất hiện giữa các video.",
        ],
        "signature_series": [
            "Hiểu đúng rồi hãy chọn - bác sĩ giải thích một quyết định nha khoa trong 45 giây.",
            "SmileUp nói thật - giải đáp rủi ro, giới hạn và kỳ vọng thực tế.",
            "Một phút trước khi điều trị - checklist khách hàng nên hỏi khi tư vấn.",
        ],
        "guardrails": [
            "Không dùng ưu đãi làm bản sắc chính.",
            "Không dùng nỗi sợ, before/after thiếu consent hoặc cam kết kết quả.",
            "Không sao chép màu, bố cục, câu chữ hay gương mặt từ quảng cáo đối thủ.",
        ],
    }


def _campaign_weeks(state: AgentState, campaign: dict, brand: dict, ready: bool) -> list[dict]:
    keyword = campaign["focus_topic"]
    signals = campaign["meta_evidence"]["signals"]
    definitions = [
        ("Tuần 1", "Nhận diện đúng vấn đề", "Tạo nhận biết có chất lượng", [
            f"Dấu hiệu cho thấy nên tìm hiểu {keyword}",
            "Hiểu lầm phổ biến khiến khách trì hoãn thăm khám",
            "Checklist khi nào nên đặt lịch tư vấn",
        ]),
        ("Tuần 2", "Hiểu đúng chỉ định", "Xây niềm tin chuyên môn", [
            "Bác sĩ đánh giá sự phù hợp dựa trên những yếu tố nào",
            "Quy trình thăm khám từ tình trạng đến kế hoạch điều trị",
            "Vì sao không phải ai cũng có cùng một phương án",
        ]),
        ("Tuần 3", "Gỡ rào cản quyết định", "Giảm băn khoăn và điều chỉnh kỳ vọng", [
            "Đau, hồi phục và trải nghiệm thực tế cần hiểu thế nào",
            "Những yếu tố cấu thành chi phí, không báo giá gây hiểu lầm",
            "Rủi ro, giới hạn và câu hỏi cần hỏi bác sĩ",
        ]),
        ("Tuần 4", "Chọn SmileUp bằng sự minh bạch", "Chuyển nhu cầu thành tư vấn đủ điều kiện", [
            "Một buổi tư vấn tại SmileUp diễn ra như thế nào",
            "Tổng hợp 5 câu hỏi khách hàng hỏi nhiều nhất trong tháng",
            "CTA đặt tư vấn để nhận đánh giá phù hợp theo tình trạng",
        ]),
    ]
    weeks: list[dict] = []
    for index, (label, theme, objective, outputs) in enumerate(definitions, 1):
        signal = signals[min(index - 1, len(signals) - 1)]
        script_id, director_id, editor_id = f"M{index}-S", f"M{index}-D", f"M{index}-E"
        status = "queued" if ready and index == 1 else ("waiting_dependency" if ready else "blocked")
        script_dependencies = [f"QW{index - 1}"] if index > 1 else []
        assignments = [
            _task(
                script_id, f"week_{index}_script", f"Viết 3 kịch bản - {theme}", "Biên kịch",
                f"Viết ba kịch bản bám output tuần {index}, evidence Meta và giọng nói SmileUp.",
                [campaign["campaign_thesis"], signal, brand["brand_idea"]],
                ["3 kịch bản 30-45 giây", "Hook và CTA cho từng video", "Lưu ý chuyên môn trong lời thoại"],
                script_dependencies,
                ["Mỗi kịch bản một mục tiêu", "Có liên kết evidence", "Đúng brand voice", "Không claim tuyệt đối"],
                status, f"{label} - Ngày 1",
            ),
            _task(
                director_id, f"week_{index}_direction", f"Đạo diễn AI - {theme}", "Đạo diễn AI",
                "Chuyển kịch bản thành storyboard, prompt và ngôn ngữ hình ảnh nhất quán với brand SmileUp.",
                [f"Kịch bản {script_id}", *brand["visual_system"]],
                ["3 storyboard/shot plan", "Prompt AI và reference có nguồn", "Chỉ dẫn nhịp, text on screen và âm thanh"],
                [script_id],
                ["Motif và màu SmileUp nhất quán", "Cảnh khả thi", "Không dùng tài sản thiếu quyền"],
                "waiting_dependency" if ready else "blocked", f"{label} - Ngày 2",
            ),
            _task(
                editor_id, f"week_{index}_edit", f"Dựng 3 video - {theme}", "Video Editor",
                "Dựng ba video dọc theo storyboard và hệ nhận diện tháng, ưu tiên hiểu nhanh và độ tin cậy.",
                [f"Storyboard {director_id}", "Voice/footage/AI assets đã duyệt", "SmileUp brand lane"],
                ["3 video dọc 9:16", "Phụ đề và audio mix", "Master file có version"],
                [director_id],
                ["30-45 giây/video", "Hook rõ trong 3 giây đầu", "Brand continuity", "Không thêm claim ngoài kịch bản"],
                "waiting_dependency" if ready else "blocked", f"{label} - Ngày 3-6",
            ),
        ]
        weeks.append({
            "week": index,
            "label": label,
            "theme": theme,
            "objective": objective,
            "evidence_link": signal,
            "content_outputs": outputs,
            "assignments": assignments,
            "review_focus": "Ngày 7: duyệt chuyên môn, brand consistency và ghi nhận insight để điều chỉnh tuần kế tiếp.",
        })
    return weeks


def _task(
    task_id: str,
    stage: str,
    title: str,
    owner_role: str,
    objective: str,
    inputs: list[str],
    deliverables: list[str],
    dependencies: list[str],
    acceptance_criteria: list[str],
    status: str,
    estimated_duration: str,
) -> ProductionTask:
    return {
        "id": task_id,
        "stage": stage,
        "title": title,
        "owner_role": owner_role,
        "objective": objective,
        "inputs": inputs,
        "deliverables": deliverables,
        "dependencies": dependencies,
        "acceptance_criteria": acceptance_criteria,
        "priority": "P0" if task_id.endswith(("-S", "-E")) else "P1",
        "status": status,
        "estimated_duration": estimated_duration,
    }


def _approval_gates() -> list[ApprovalGate]:
    return [
        {
            "id": f"QW{week}",
            "after_task": f"M{week}-E",
            "approver_role": "CMO + phụ trách chuyên môn",
            "checks": ["Medical claims", "Kỳ vọng thực tế", "Brand consistency", "Asset rights"],
            "failure_action": "Trả đúng đầu việc có lỗi về owner; chưa mở brief tuần kế tiếp.",
        }
        for week in range(1, 5)
    ]


def _success_metrics() -> list[str]:
    return [
        "Mỗi tuần khóa 3 kịch bản trong ngày 1 và hoàn tất 3 video chậm nhất ngày 6",
        "12 video 9:16 hoàn tất trong tháng theo cùng một brand lane",
        "Mỗi video chỉ có một mục tiêu và một CTA chính",
        "0 claim y khoa thiếu căn cứ hoặc tài sản thiếu quyền",
        "Theo dõi theo tuần: giữ chân 3 giây, tỷ lệ xem hết, lưu/chia sẻ và số tư vấn đủ điều kiện",
    ]


def _production_risks(state: AgentState, missing: list[str]) -> list[str]:
    risks = list(missing)
    risks.extend(state.get("hardness_missing_evidence", []) or [])
    if not missing:
        risks.extend(
            [
                "Dữ liệu Ad Library không cho biết chi tiêu, doanh thu hoặc tỷ lệ chuyển đổi của đối thủ.",
                "Nội dung y khoa cần người phụ trách chuyên môn xác nhận trước khi bàn giao.",
                "Không mở rộng sang dịch vụ khác trong tháng nếu chưa có dữ liệu mới.",
            ]
        )
    return _unique(risks)


def _production_brief(state: AgentState, workflow: dict, missing: list[str]) -> str:
    readiness = "Sẵn sàng giao việc" if not missing else "Chưa giao việc"
    campaign = workflow.get("monthly_campaign", {})
    evidence = campaign.get("meta_evidence", {})
    brand = workflow.get("brand_platform", {})
    market = workflow.get("market_intelligence", {})
    coverage = market.get("coverage", {})
    revenue = workflow.get("revenue_strategy", {})
    week_lines = []
    for week in workflow.get("weeks", []):
        outputs = "; ".join(week.get("content_outputs", []))
        week_lines.append(
            f"TUẦN {week['week']} - {week['theme']}\n"
            f"  Mục tiêu: {week['objective']}\n"
            f"  Evidence: {week['evidence_link']}\n"
            f"  Nội dung: {outputs}"
        )
    weeks_text = "\n\n".join(week_lines)
    voice = "; ".join(brand.get("voice", []))
    visual = "\n".join(f"  - {item}" for item in brand.get("visual_system", []))
    avoid = "\n".join(f"  - {item}" for item in campaign.get("not_recommended", []))
    competitor_lines = []
    for item in market.get("campaigns", [])[:8]:
        competitor_lines.append(
            f"  - {item.get('page_name', '')} | {item.get('service_line', '')} | {item.get('angle', '')} | "
            f"{item.get('funnel_stage', '')} | {item.get('ad_count', 0)} ads | "
            f"Mạnh: {'; '.join(item.get('strengths', []))} | Yếu: {'; '.join(item.get('weaknesses', []))}"
        )
    competitors_text = "\n".join(competitor_lines) or "  - Chưa đủ campaign để nhận xét."
    funnel_text = "\n".join(
        f"  - {stage.get('stage', '')}: {stage.get('goal', '')} | KPI: {stage.get('metric', '')}"
        for stage in revenue.get("funnel", [])
    )
    unit_economics = revenue.get("unit_economics", {})
    economics_text = (
        f"  Lợi nhuận gộp/ca: {unit_economics.get('gross_profit_per_case', 0):,.0f} VND | "
        f"Trần CAC/ca: {unit_economics.get('max_cost_per_acquired_case', 0):,.0f} VND | "
        f"Trần CPL đủ điều kiện: {unit_economics.get('max_cost_per_qualified_lead', 0):,.0f} VND\n"
        if unit_economics
        else f"  Cần dữ liệu kinh doanh: {', '.join(revenue.get('required_business_inputs', []))}\n"
    )
    return (
        f"CHIẾN DỊCH MEDIA 1 THÁNG - {readiness}\n\n"
        f"Tên chiến dịch: {campaign.get('campaign_name', '')}\n"
        f"Campaign thesis: {campaign.get('campaign_thesis', '')}\n"
        f"Mục tiêu kinh doanh: {campaign.get('business_goal', '')}\n"
        f"Khán giả chính: {campaign.get('target_audience', '')}\n\n"
        f"META SNAPSHOT: {evidence.get('source', '')} | {evidence.get('analyzed_at', '')}\n"
        f"Scan ID: {evidence.get('scan_id', '')} | Chế độ: {evidence.get('scan_mode', 'auto')}\n"
        f"Cơ sở: {evidence.get('basis', '')}\n"
        f"Nguồn nổi bật: {', '.join(evidence.get('reference_pages', [])) or 'chưa đủ dữ liệu'}\n"
        f"Mẫu thông điệp nguồn: {' | '.join(evidence.get('message_samples', [])) or 'chưa đủ dữ liệu'}\n"
        f"Giới hạn: {evidence.get('caveat', '')}\n\n"
        f"MARKET COVERAGE\n"
        f"  Đã quan sát: {coverage.get('ads_observed', 0)}/{coverage.get('scan_target', 0)} ads | "
        f"{coverage.get('unique_pages', 0)} page | {coverage.get('campaigns_detected', 0)} campaign\n"
        f"  Mức phủ: {coverage.get('coverage_level', 'low')} ({coverage.get('coverage_score', 0)}/100)\n"
        f"  Giới hạn: {coverage.get('limitation', '')}\n\n"
        f"CAMPAIGN ĐỐI THỦ NỔI BẬT\n{competitors_text}\n\n"
        f"REVENUE STRATEGY\n"
        f"  Chuyển đổi chính: {revenue.get('primary_conversion', '')}\n"
        f"  Economics: {revenue.get('economics_status', '')}\n"
        f"{economics_text}"
        f"{funnel_text}\n"
        f"  Lưu ý: {revenue.get('revenue_caveat', '')}\n\n"
        f"SMILEUP BRAND\n"
        f"  Ý tưởng: {brand.get('brand_idea', '')}\n"
        f"  Định vị: {brand.get('positioning', '')}\n"
        f"  Lời hứa: {brand.get('promise', '')}\n"
        f"  Giọng nói: {voice}\n"
        f"  Hệ hình ảnh:\n{visual}\n\n"
        f"KẾ HOẠCH 4 TUẦN\n{weeks_text}\n\n"
        f"Không nên làm:\n{avoid}"
    )


def _handoff(workflow: dict, missing: list[str]) -> str:
    if missing:
        return "CMO giữ kế hoạch ở bước nghiên cứu. Bổ sung dữ liệu còn thiếu rồi chạy lại trước khi giao việc."
    return (
        "Bàn giao tháng: mỗi tuần Biên kịch chốt 3 script ngày 1, Đạo diễn AI khóa storyboard ngày 2, "
        "Video Editor hoàn thiện 3 video ngày 3-6. Ngày 7 duyệt checkpoint QW1-QW4 trước khi mở tuần kế; "
        "QW4 là checkpoint bàn giao cuối tháng."
    )


def _decision_graph(tasks: list[ProductionTask], gates: list[ApprovalGate], ready: bool) -> dict:
    nodes: list[dict] = [
        {
            "id": "evidence",
            "label": "Market ads (tối đa 100) + specialist reports",
            "type": "evidence",
            "status": "support" if ready else "risk",
        }
    ]
    edges: list[dict] = []
    for task in tasks:
        nodes.append(
            {
                "id": task["id"],
                "label": f"{task['id']} {task['title']}",
                "type": "task",
                "status": "support" if ready else "risk",
            }
        )
        if task["dependencies"]:
            for dependency in task["dependencies"]:
                edges.append({"source": dependency, "target": task["id"], "relation": "blocks", "weight": 1.0})
        else:
            edges.append({"source": "evidence", "target": task["id"], "relation": "feeds", "weight": 1.0})
    for gate in gates:
        nodes.append({"id": gate["id"], "label": f"{gate['id']} {gate['approver_role']}", "type": "gate", "status": "neutral"})
        edges.append({"source": gate["after_task"], "target": gate["id"], "relation": "requires_approval", "weight": 1.0})
    selected_path = ["evidence"]
    if ready:
        for week in range(1, 5):
            selected_path.extend([f"M{week}-S", f"M{week}-D", f"M{week}-E", f"QW{week}"])
    return {"nodes": nodes, "edges": edges, "selected_path": selected_path}


def _graph_summary(graph: dict) -> str:
    task_count = sum(1 for node in graph.get("nodes", []) if node.get("type") == "task")
    gate_count = sum(1 for node in graph.get("nodes", []) if node.get("type") == "gate")
    return f"Monthly media campaign: {task_count} assignments across 4 weeks, {gate_count} weekly checkpoints."


def _daily_strategy(state: AgentState) -> str:
    workflow = state.get("media_production_workflow", {})
    task_lines = [
        f"- {task['id']} | {task['owner_role']} | {task['title']} | {task['estimated_duration']}"
        for task in workflow.get("tasks", [])
    ]
    return "\n".join(
        [
            state.get("media_production_brief", ""),
            "",
            "Phân việc chiến dịch 1 tháng:",
            *task_lines,
            "",
            "Handoff:",
            state.get("production_handoff", ""),
        ]
    )


def _daily_report(state: AgentState) -> str:
    workflow = state.get("media_production_workflow", {})
    return (
        f"CMO decision: {state.get('cmo_decision', '')}\n"
        f"Focus keyword: {workflow.get('focus_keyword', '')}\n"
        f"Workflow status: {workflow.get('status', 'pending')}\n"
        f"Evidence readiness: {state.get('hardness_score', 0)}/100\n"
        f"Planning horizon: {workflow.get('planning_horizon', '1 tháng / 4 tuần')}\n"
        f"Campaign weeks: {len(workflow.get('weeks', []))}\n"
        f"Media assignments: {len(workflow.get('tasks', []))}\n"
        f"Final checkpoints: {len(workflow.get('approval_gates', []))}\n"
        f"Next action: {state.get('cmo_next_action', '')}\n"
        f"Feedback: {state.get('cmo_feedback', '')}"
    )


def _workflow_id(state: AgentState) -> str:
    seed = str(state.get("run_seed") or state.get("ad_library_keywords") or "smileup-production")
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8].upper()
    return f"MPW-{digest}"


def _evidence_scan_id(keyword: str, ads: list[dict]) -> str:
    snapshot = {
        "keywords": keyword,
        "ads": [
            {
                "library_id": ad.get("library_id", ""),
                "page_name": ad.get("page_name", ""),
                "ad_text": ad.get("ad_text", ""),
                "source_type": ad.get("source_type", ""),
            }
            for ad in ads
        ],
    }
    digest = hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16].upper()
    return f"META-{digest}"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = str(item or "").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def workflow_as_json(state: AgentState) -> str:
    return json.dumps(state.get("media_production_workflow", {}), ensure_ascii=False, indent=2)
