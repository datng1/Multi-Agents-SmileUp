from __future__ import annotations

import hashlib
import json

from graph.state import AgentState, ApprovalGate, ProductionTask
from utils.logger import get_logger


logger = get_logger(__name__)


REQUIRED_REPORT_FIELDS = (
    "text_insight_report",
    "facebook_trend_analysis",
    "visual_insight_report",
    "video_insight_report",
    "strategic_direction",
)


def run_manager_agent(state: AgentState) -> AgentState:
    logger.info("CMO Agent building the media production operating plan")
    missing = _missing_evidence(state)
    ready = not missing
    tasks = _production_tasks(state, ready)
    gates = _approval_gates()
    workflow_id = _workflow_id(state)

    workflow = {
        "workflow_id": workflow_id,
        "status": "ready_for_dispatch" if ready else "needs_research",
        "focus_keyword": state.get("ad_library_keywords", ""),
        "objective": state.get("cmo_objective", ""),
        "source_ads_count": len(state.get("ad_library_ads", [])),
        "high_match_ads_count": len(state.get("high_match_ads", [])),
        "tasks": tasks,
        "approval_gates": gates,
        "metrics": _success_metrics(),
        "risks": _production_risks(state, missing),
        "operating_rules": [
            "CMO giao việc và duyệt gate; không tự viết bài, tạo media hoặc đăng bài.",
            "Mỗi owner chỉ bắt đầu khi dependency đã hoàn tất và gate liên quan đã được duyệt.",
            "Tài sản đối thủ chỉ dùng làm dữ liệu tham chiếu, không sao chép caption, hình ảnh hoặc nhận diện.",
            "Mọi asset có người thật phải có quyền sử dụng, consent và lưu vết nguồn.",
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
            f"Workflow {workflow_id} đủ dữ liệu để giao việc. Bắt đầu từ T01 và chỉ chuyển stage sau khi gate được duyệt."
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


def _missing_evidence(state: AgentState) -> list[str]:
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
    }
    for field in REQUIRED_REPORT_FIELDS:
        if not str(state.get(field, "")).strip():
            missing.append(labels[field])
    if int(state.get("hardness_score", 0) or 0) < 70:
        missing.append("evidence readiness dưới 70/100")
    return missing


def _production_tasks(state: AgentState, ready: bool) -> list[ProductionTask]:
    common_status = "queued" if ready else "blocked"
    ads_count = len(state.get("ad_library_ads", []))
    focus_keyword = state.get("ad_library_keywords", "")
    tasks = [
        _task(
            "T01",
            "01_strategy",
            "Khóa production brief",
            "Strategy Lead",
            f"Chuyển phân tích {ads_count} ads theo keyword '{focus_keyword}' thành một brief sản xuất duy nhất cho tháng.",
            ["Ad Library report", "Text/Trend/Visual/Video insight", "Strategic direction"],
            ["Production brief 1 trang", "Audience và message hierarchy", "Danh sách format cần sản xuất"],
            [],
            ["Mục tiêu kinh doanh và audience rõ", "Mỗi insight có nguồn", "Không chứa final caption hoặc asset"],
            common_status,
            "0.5 ngày",
        ),
        _task(
            "T02",
            "02_messaging",
            "Lập message matrix",
            "Copy Lead",
            "Biến chiến lược thành khung thông điệp để đội script và design cùng dùng.",
            ["T01 production brief", "Compliance guardrails"],
            ["Hook bank", "Pain point/objection matrix", "CTA và disclaimer library"],
            ["T01"],
            ["Có paid/organic lane", "Không claim tuyệt đối", "Mỗi CTA gắn đúng intent"],
            common_status,
            "0.5 ngày",
        ),
        _task(
            "T03",
            "03_concept",
            "Phát triển concept media",
            "Creative Director",
            "Đề xuất hệ concept đủ rõ để sản xuất ảnh, carousel và short video.",
            ["T01 production brief", "T02 message matrix", "Visual/Video insight"],
            ["3 concept routes", "Format map", "Visual language và reference board có nguồn"],
            ["T01", "T02"],
            ["Mỗi concept bám một business objective", "Không sao chép asset đối thủ", "Khả thi với nguồn lực công ty"],
            common_status,
            "1 ngày",
        ),
        _task(
            "T04",
            "04_script",
            "Viết script và storyboard",
            "Scriptwriter",
            "Tạo blueprint nội dung cho từng format mà chưa xuất bản thành bài hoàn chỉnh.",
            ["T02 message matrix", "T03 concept routes"],
            ["Video scripts", "Storyboard/shot-by-shot", "Carousel frame outline"],
            ["T02", "T03"],
            ["Hook xuất hiện trong 3 giây đầu", "CTA đúng lane", "Script có disclaimer và shot khả thi"],
            common_status,
            "1 ngày",
        ),
        _task(
            "T05",
            "05_preproduction",
            "Lập kế hoạch tiền kỳ",
            "Media Producer",
            "Khóa lịch, nhân sự, bối cảnh và quyền sử dụng trước khi quay/chụp.",
            ["T03 concept routes", "T04 scripts/storyboards"],
            ["Shot list", "Call sheet", "Lịch sản xuất", "Consent và asset rights checklist"],
            ["T03", "T04"],
            ["Có owner cho từng shot", "Có phương án dự phòng", "Consent được chuẩn bị trước ngày quay"],
            common_status,
            "0.5 ngày",
        ),
        _task(
            "T06",
            "06_production",
            "Quay và chụp media gốc",
            "Photo/Video Team",
            "Sản xuất raw media thuộc quyền sử dụng của công ty theo shot list đã duyệt.",
            ["T05 call sheet và shot list"],
            ["Raw video", "Raw photo", "Audio", "Asset log và consent record"],
            ["T05"],
            ["Đủ shot bắt buộc", "Âm thanh/hình ảnh đạt chuẩn kỹ thuật", "Asset log khớp file"],
            common_status,
            "1 ngày",
        ),
        _task(
            "T07",
            "07_postproduction",
            "Dựng và thiết kế asset",
            "Designer + Video Editor",
            "Biến raw media thành bộ asset theo format map và brand system.",
            ["T06 raw media", "T03 visual language", "T04 storyboard"],
            ["Master assets", "Platform variants", "Subtitle/caption file", "Version manifest"],
            ["T06"],
            ["Đúng kích thước từng format", "Brand nhất quán", "Không chèn claim ngoài brief", "File có version rõ"],
            common_status,
            "1-2 ngày",
        ),
        _task(
            "T08",
            "08_compliance_qa",
            "Kiểm tra y khoa, pháp lý và quyền media",
            "Medical Compliance + Brand QA",
            "Chặn asset có claim, consent hoặc nhận diện không đạt trước bàn giao.",
            ["T07 master assets", "Compliance guardrails", "Consent record"],
            ["QA checklist", "Issue list", "Approved asset manifest"],
            ["T07"],
            ["Không claim tuyệt đối", "Có disclaimer phù hợp", "Consent và nguồn asset hợp lệ", "Issue nghiêm trọng bằng 0"],
            common_status,
            "0.5 ngày",
        ),
        _task(
            "T09",
            "09_handoff",
            "Nghiệm thu và bàn giao media pack",
            "CMO + Performance Lead",
            "Nghiệm thu bộ media và bàn giao cho kênh triển khai bên ngoài CMO app.",
            ["T08 approved asset manifest", "Production metrics"],
            ["Approved media pack", "Experiment matrix", "Naming/UTM convention", "Measurement checklist"],
            ["T08"],
            ["Mỗi asset có objective và audience", "Có test hypothesis", "Có owner đo lường", "Không có hành động đăng bài trong workflow này"],
            common_status,
            "0.5 ngày",
        ),
    ]
    if ready:
        for task in tasks:
            task["status"] = "queued" if task["id"] == "T01" else "waiting_dependency"
    return tasks


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
        "priority": "P0" if task_id in {"T01", "T05", "T08", "T09"} else "P1",
        "status": status,
        "estimated_duration": estimated_duration,
    }


def _approval_gates() -> list[ApprovalGate]:
    return [
        {
            "id": "G01",
            "after_task": "T01",
            "approver_role": "CMO",
            "checks": ["Business objective", "Audience", "Evidence traceability", "Format scope"],
            "failure_action": "Trả T01 cho Strategy Lead, không mở T02/T03.",
        },
        {
            "id": "G02",
            "after_task": "T05",
            "approver_role": "CMO + Media Producer",
            "checks": ["Shot list", "Budget/resource fit", "Consent plan", "Production schedule"],
            "failure_action": "Dừng ngày quay và sửa pre-production pack.",
        },
        {
            "id": "G03",
            "after_task": "T08",
            "approver_role": "Medical Compliance",
            "checks": ["Medical claims", "Disclaimer", "Asset rights", "Brand safety"],
            "failure_action": "Trả đúng asset lỗi về T07; không bàn giao media pack.",
        },
        {
            "id": "G04",
            "after_task": "T09",
            "approver_role": "CMO",
            "checks": ["Objective mapping", "Experiment plan", "Measurement owner", "Version manifest"],
            "failure_action": "Giữ workflow ở trạng thái review, không chuyển cho kênh triển khai.",
        },
    ]


def _success_metrics() -> list[str]:
    return [
        "100% task có owner, dependency và deliverable",
        "100% asset có objective, audience và nguồn/consent",
        "0 issue compliance nghiêm trọng ở final gate",
        "Tỷ lệ asset vượt QA ngay vòng đầu",
        "Thời gian từ brief approved đến media pack approved",
        "Kết quả thử nghiệm theo hook, format và audience sau khi đội kênh triển khai",
    ]


def _production_risks(state: AgentState, missing: list[str]) -> list[str]:
    risks = list(missing)
    risks.extend(state.get("hardness_missing_evidence", []) or [])
    return _unique(risks)


def _production_brief(state: AgentState, workflow: dict, missing: list[str]) -> str:
    readiness = "Sẵn sàng giao việc" if not missing else "Chưa giao việc"
    return (
        f"{readiness} - Workflow {workflow['workflow_id']}\n"
        f"Keyword: {workflow.get('focus_keyword', '')}\n"
        f"Mục tiêu: {workflow['objective']}\n"
        f"Nguồn: {workflow['source_ads_count']} ads, {workflow['high_match_ads_count']} ads high-match.\n"
        f"Chiến lược: {state.get('strategic_direction', '')}\n"
        f"Guardrail: {state.get('compliance_report', '')}\n"
        f"Phạm vi: {len(workflow['tasks'])} task, {len(workflow['approval_gates'])} approval gate; kết thúc ở media pack đã nghiệm thu, không đăng bài."
    )


def _handoff(workflow: dict, missing: list[str]) -> str:
    if missing:
        return "CMO giữ workflow ở Research. Bổ sung dữ liệu còn thiếu rồi chạy lại trước khi giao T01."
    first = workflow["tasks"][0]
    return (
        f"Giao {first['id']} cho {first['owner_role']}. "
        "CMO duyệt G01 trước khi mở các task concept; mọi task cập nhật status và đính kèm deliverable theo đúng ID."
    )


def _decision_graph(tasks: list[ProductionTask], gates: list[ApprovalGate], ready: bool) -> dict:
    nodes: list[dict] = [
        {"id": "evidence", "label": "20 ads + specialist reports", "type": "evidence", "status": "support" if ready else "risk"}
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
    gate_blocks = {
        "G01": ["T02", "T03"],
        "G02": ["T06"],
        "G03": ["T09"],
    }
    for gate_id, next_tasks in gate_blocks.items():
        for task_id in next_tasks:
            edges.append({"source": gate_id, "target": task_id, "relation": "unlocks", "weight": 1.0})
    selected_path = (
        ["evidence", "T01", "G01", "T02", "T03", "T04", "T05", "G02", "T06", "T07", "T08", "G03", "T09", "G04"]
        if ready
        else ["evidence"]
    )
    return {"nodes": nodes, "edges": edges, "selected_path": selected_path}


def _graph_summary(graph: dict) -> str:
    task_count = sum(1 for node in graph.get("nodes", []) if node.get("type") == "task")
    gate_count = sum(1 for node in graph.get("nodes", []) if node.get("type") == "gate")
    return f"Production graph: {task_count} tasks, {gate_count} approval gates, {len(graph.get('edges', []))} dependencies."


def _daily_strategy(state: AgentState) -> str:
    workflow = state.get("media_production_workflow", {})
    task_lines = [
        f"- {task['id']} | {task['owner_role']} | {task['title']} | deps: {', '.join(task['dependencies']) or 'none'}"
        for task in workflow.get("tasks", [])
    ]
    return "\n".join(
        [
            state.get("media_production_brief", ""),
            "",
            "Danh sách giao việc:",
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
        f"Tasks: {len(workflow.get('tasks', []))}\n"
        f"Approval gates: {len(workflow.get('approval_gates', []))}\n"
        f"Next action: {state.get('cmo_next_action', '')}\n"
        f"Feedback: {state.get('cmo_feedback', '')}"
    )


def _workflow_id(state: AgentState) -> str:
    seed = str(state.get("run_seed") or state.get("ad_library_keywords") or "smileup-production")
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8].upper()
    return f"MPW-{digest}"


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
