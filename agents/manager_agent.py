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
    weekly_direction = _weekly_direction(state)
    tasks = _production_tasks(state, ready, weekly_direction)
    gates = _approval_gates()
    workflow_id = _workflow_id(state)

    workflow = {
        "workflow_id": workflow_id,
        "status": "ready_for_dispatch" if ready else "needs_research",
        "focus_keyword": state.get("ad_library_keywords", ""),
        "planning_horizon": "7 ngày",
        "objective": state.get("cmo_objective", ""),
        "source_ads_count": len(state.get("ad_library_ads", [])),
        "high_match_ads_count": len(state.get("high_match_ads", [])),
        "weekly_direction": weekly_direction,
        "tasks": tasks,
        "approval_gates": gates,
        "metrics": _success_metrics(),
        "risks": _production_risks(state, missing),
        "operating_rules": [
            "CMO chọn một trọng tâm cho 7 ngày và giao việc; ứng dụng không đăng bài.",
            "Ba vai trò bàn giao tuần tự: Biên kịch -> Đạo diễn AI -> Video Editor.",
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
            f"Đã chốt hướng media 7 ngày cho '{workflow['focus_keyword']}' và giao việc cho 3 vai trò trong đội."
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


def _weekly_direction(state: AgentState) -> dict:
    keyword = str(state.get("ad_library_keywords", "")).strip() or "dịch vụ nha khoa trọng tâm"
    ads_count = len(state.get("ad_library_ads", []))
    high_match_count = len(state.get("high_match_ads", []))
    evidence_signal = _evidence_signal(state)
    return {
        "focus_topic": keyword,
        "primary_push": (
            f"Đẩy mạnh chuỗi video tư vấn về '{keyword}': giúp khách hàng nhận diện nhu cầu, "
            f"hiểu quy trình thăm khám và giải tỏa băn khoăn trước khi đặt lịch. Góc ưu tiên từ phân tích: {evidence_signal}"
        ),
        "business_goal": "Tăng nhu cầu tư vấn đủ điều kiện và củng cố niềm tin chuyên môn, không chạy theo lượt xem đơn thuần.",
        "target_audience": f"Người đang cân nhắc '{keyword}', còn băn khoăn về độ phù hợp, quy trình, rủi ro và chi phí.",
        "objective_basis": (
            f"Phân tích {ads_count} ads công khai theo keyword, trong đó {high_match_count} ads có mức độ liên quan cao, "
            f"kết hợp insight chữ, hình, video và kiểm tra tuân thủ. Tín hiệu được chọn: {evidence_signal}"
        ),
        "evidence_signal": evidence_signal,
        "evidence_caveat": (
            "Ads công khai chỉ phản ánh tín hiệu thông điệp và mức độ cạnh tranh; đây không phải bằng chứng về doanh thu, "
            "tỷ lệ chuyển đổi hoặc hiệu quả thực tế của đối thủ."
        ),
        "recommended_outputs": [
            f"Video 1 - Nhận diện vấn đề: khi nào nên tìm hiểu '{keyword}'.",
            "Video 2 - Giải thích chuyên môn: quy trình thăm khám và tiêu chí đánh giá phù hợp.",
            "Video 3 - Gỡ băn khoăn: rủi ro, kỳ vọng thực tế và câu hỏi thường gặp.",
        ],
        "weekly_cadence": [
            "Ngày 1: chốt 3 kịch bản và thông điệp chính.",
            "Ngày 2: khóa storyboard, nhịp dựng và hướng hình ảnh bằng AI.",
            "Ngày 3-6: dựng 3 video dọc, phụ đề và kiểm tra chất lượng.",
            "Ngày 7: duyệt chuyên môn, thương hiệu và bàn giao cho đội kênh.",
        ],
        "not_recommended": [
            "Không dàn trải nhiều dịch vụ trong cùng tuần.",
            "Không sao chép quảng cáo đối thủ hoặc dùng claim tuyệt đối.",
            "Không kết luận một thông điệp hiệu quả chỉ vì xuất hiện nhiều trong Ad Library.",
        ],
    }


def _evidence_signal(state: AgentState) -> str:
    reports = (
        state.get("weekly_strategy", ""),
        state.get("strategic_direction", ""),
        state.get("text_insight_report", ""),
        state.get("video_insight_report", ""),
    )
    skipped_prefixes = ("focus keyword:", "định hướng media 7 ngày", "strategic direction agent:")
    for report in reports:
        for raw_line in str(report or "").splitlines():
            line = raw_line.strip().lstrip("-• ").strip()
            if len(line) < 20 or line.lower().startswith(skipped_prefixes):
                continue
            return line[:280].rstrip()
    return "Chưa có tín hiệu nội dung đủ rõ; giữ hướng tư vấn nền và không suy diễn hiệu quả."


def _production_tasks(state: AgentState, ready: bool, direction: dict) -> list[ProductionTask]:
    common_status = "queued" if ready else "blocked"
    focus_keyword = state.get("ad_library_keywords", "")
    tasks = [
        _task(
            "W01",
            "01_script",
            "Viết 3 kịch bản video trong tuần",
            "Biên kịch",
            f"Chuyển hướng tuần về '{focus_keyword}' thành 3 kịch bản ngắn, rõ một mục tiêu và một CTA cho mỗi video.",
            ["Định hướng 7 ngày", "Text insight", "Compliance guardrails"],
            ["3 kịch bản video 30-45 giây", "Hook 3 giây đầu", "Lời thoại, CTA và lưu ý chuyên môn"],
            [],
            ["Đúng 3 góc nội dung đã chốt", "Ngôn ngữ dễ hiểu, khách quan", "Không claim tuyệt đối hoặc hứa kết quả"],
            common_status,
            "Ngày 1",
        ),
        _task(
            "W02",
            "02_ai_direction",
            "Đạo diễn hình ảnh và nhịp kể bằng AI",
            "Đạo diễn AI",
            "Biến 3 kịch bản thành hướng quay/dựng nhất quán, khả thi với nguồn lực hiện có.",
            ["3 kịch bản W01", "Visual/Video insight", "Brand guardrails"],
            ["3 storyboard/shot plan", "Prompt và reference có nguồn cho từng cảnh", "Chỉ dẫn nhịp, text on screen và âm thanh"],
            ["W01"],
            ["Mỗi cảnh phục vụ thông điệp", "Hình ảnh nha khoa chính xác và chuyên nghiệp", "Không dùng tài sản thiếu quyền"],
            common_status,
            "Ngày 2",
        ),
        _task(
            "W03",
            "03_edit",
            "Dựng và hoàn thiện 3 video",
            "Video Editor",
            "Dựng ba video dọc theo storyboard, ưu tiên khả năng hiểu nhanh, độ tin cậy và nhịp xem tự nhiên.",
            ["Storyboard W02", "Voice/footage/AI assets đã được duyệt", "Brand kit"],
            ["3 video dọc 9:16 hoàn chỉnh", "Phụ đề và audio mix", "Master file và bản bàn giao có version"],
            ["W02"],
            ["30-45 giây/video", "Hook rõ trong 3 giây đầu", "Phụ đề dễ đọc", "Không thêm claim ngoài kịch bản"],
            common_status,
            "Ngày 3-6",
        ),
    ]
    if ready:
        for task in tasks:
            task["status"] = "queued" if task["id"] == "W01" else "waiting_dependency"
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
        "priority": "P0" if task_id in {"W01", "W03"} else "P1",
        "status": status,
        "estimated_duration": estimated_duration,
    }


def _approval_gates() -> list[ApprovalGate]:
    return [
        {
            "id": "Q01",
            "after_task": "W03",
            "approver_role": "CMO + phụ trách chuyên môn",
            "checks": ["Medical claims", "Kỳ vọng thực tế", "Brand consistency", "Asset rights"],
            "failure_action": "Trả đúng video có lỗi về Video Editor trước khi bàn giao cho đội kênh.",
        },
    ]


def _success_metrics() -> list[str]:
    return [
        "3 kịch bản được khóa trong ngày 1",
        "3 video 9:16 hoàn tất chậm nhất ngày 6",
        "Mỗi video chỉ có một mục tiêu và một CTA chính",
        "0 claim y khoa thiếu căn cứ hoặc tài sản thiếu quyền ở checkpoint cuối",
        "Sau khi đội kênh triển khai: theo dõi giữ chân 3 giây, tỷ lệ xem hết và số tư vấn đủ điều kiện",
    ]


def _production_risks(state: AgentState, missing: list[str]) -> list[str]:
    risks = list(missing)
    risks.extend(state.get("hardness_missing_evidence", []) or [])
    if not missing:
        risks.extend(
            [
                "Dữ liệu Ad Library không cho biết chi tiêu, doanh thu hoặc tỷ lệ chuyển đổi của đối thủ.",
                "Nội dung y khoa cần người phụ trách chuyên môn xác nhận trước khi bàn giao.",
                "Không mở rộng sang dịch vụ khác trong tuần nếu chưa có dữ liệu mới.",
            ]
        )
    return _unique(risks)


def _production_brief(state: AgentState, workflow: dict, missing: list[str]) -> str:
    readiness = "Sẵn sàng giao việc" if not missing else "Chưa giao việc"
    direction = workflow.get("weekly_direction", {})
    outputs = "\n".join(f"  {index}. {item}" for index, item in enumerate(direction.get("recommended_outputs", []), 1))
    cadence = "\n".join(f"  - {item}" for item in direction.get("weekly_cadence", []))
    avoid = "\n".join(f"  - {item}" for item in direction.get("not_recommended", []))
    return (
        f"ĐỊNH HƯỚNG MEDIA 7 NGÀY - {readiness}\n\n"
        f"Chủ đề trọng tâm: {direction.get('focus_topic', '')}\n"
        f"Cần đẩy mạnh: {direction.get('primary_push', '')}\n"
        f"Mục tiêu kinh doanh: {direction.get('business_goal', '')}\n"
        f"Khán giả chính: {direction.get('target_audience', '')}\n\n"
        f"Cơ sở khách quan: {direction.get('objective_basis', '')}\n"
        f"Giới hạn dữ liệu: {direction.get('evidence_caveat', '')}\n\n"
        f"Sản lượng đề xuất:\n{outputs}\n\n"
        f"Nhịp triển khai:\n{cadence}\n\n"
        f"Không nên làm:\n{avoid}"
    )


def _handoff(workflow: dict, missing: list[str]) -> str:
    if missing:
        return "CMO giữ kế hoạch ở bước nghiên cứu. Bổ sung dữ liệu còn thiếu rồi chạy lại trước khi giao việc."
    return (
        "Bàn giao tuần: Biên kịch chốt W01 ngày 1; Đạo diễn AI nhận W02 ngày 2; "
        "Video Editor hoàn thiện W03 trong ngày 3-6. Ngày 7 duyệt Q01 rồi chuyển video cho đội kênh; ứng dụng không đăng bài."
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
    selected_path = ["evidence", "W01", "W02", "W03", "Q01"] if ready else ["evidence"]
    return {"nodes": nodes, "edges": edges, "selected_path": selected_path}


def _graph_summary(graph: dict) -> str:
    task_count = sum(1 for node in graph.get("nodes", []) if node.get("type") == "task")
    gate_count = sum(1 for node in graph.get("nodes", []) if node.get("type") == "gate")
    return f"Weekly media plan: {task_count} roles, {gate_count} final checkpoint."


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
            "Phân việc đội media:",
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
        f"Planning horizon: {workflow.get('planning_horizon', '7 ngày')}\n"
        f"Media roles: {len(workflow.get('tasks', []))}\n"
        f"Final checkpoints: {len(workflow.get('approval_gates', []))}\n"
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
