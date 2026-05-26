const runButton = document.querySelector("#runButton");
const modeValue = document.querySelector("#modeValue");
const dryRunValue = document.querySelector("#dryRunValue");
const statusValue = document.querySelector("#statusValue");
const approvalBadge = document.querySelector("#approvalBadge");
const dailyReport = document.querySelector("#dailyReport");
const dailyStrategy = document.querySelector("#dailyStrategy");
const postTitle = document.querySelector("#postTitle");
const postBody = document.querySelector("#postBody");
const postCta = document.querySelector("#postCta");
const postTags = document.querySelector("#postTags");
const publishStatus = document.querySelector("#publishStatus");
const publishMode = document.querySelector("#publishMode");
const postId = document.querySelector("#postId");
const safePayload = document.querySelector("#safePayload");
const agentCards = [...document.querySelectorAll(".agent-card")];

function setAgentState(activeStep) {
  const order = ["crawler", "content_creator", "manager_review", "publisher"];
  const activeIndex = order.indexOf(activeStep);
  agentCards.forEach((card) => {
    const index = order.indexOf(card.dataset.agent);
    card.classList.toggle("active", index === activeIndex);
    card.classList.toggle("done", activeIndex >= 0 && index < activeIndex);
  });
}

function completeAgents() {
  agentCards.forEach((card) => {
    card.classList.remove("active");
    card.classList.add("done");
  });
}

async function loadStatus() {
  const response = await fetch("/api/status");
  const status = await response.json();
  modeValue.textContent = status.mock_mode ? "Mock" : "Live";
  dryRunValue.textContent = status.dry_run ? "On" : "Off";
}

async function runWorkflow() {
  runButton.disabled = true;
  statusValue.textContent = "Đang chạy";
  setAgentState("crawler");

  try {
    const response = await fetch("/api/run", { method: "POST" });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Workflow failed");
    }

    const result = payload.result;
    renderResult(result);
    completeAgents();
    statusValue.textContent = "Hoàn thành";
  } catch (error) {
    statusValue.textContent = "Lỗi";
    safePayload.textContent = error.message;
  } finally {
    runButton.disabled = false;
  }
}

function renderResult(result) {
  const draft = result.draft_content || {};
  const publish = result.publish_result || {};

  approvalBadge.textContent = result.approval_status || "pending";
  approvalBadge.classList.toggle("approved", result.approval_status === "approved");
  dailyReport.textContent = result.daily_report || "-";
  dailyStrategy.textContent = result.daily_strategy || "-";
  postTitle.textContent = draft.title || "-";
  postBody.textContent = draft.body || "";
  postCta.textContent = draft.call_to_action || "";
  postTags.textContent = (draft.hashtags || []).join(" ");
  publishStatus.textContent = publish.publisher_status || "-";
  publishMode.textContent = publish.publish_mode || "-";
  postId.textContent = publish.published_post_id || "-";
  safePayload.textContent = publish.safe_payload_preview || JSON.stringify(publish, null, 2);
}

runButton.addEventListener("click", runWorkflow);
loadStatus().catch(() => {
  modeValue.textContent = "Unknown";
  dryRunValue.textContent = "-";
});
