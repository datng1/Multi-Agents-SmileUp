const runButton = document.querySelector("#runButton");
const modeValue = document.querySelector("#modeValue");
const dryRunValue = document.querySelector("#dryRunValue");
const approvalValue = document.querySelector("#approvalValue");
const lastRunValue = document.querySelector("#lastRunValue");
const connectionState = document.querySelector("#connectionState");
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
const insightList = document.querySelector("#insightList");
const insightCount = document.querySelector("#insightCount");
const trendAnalysis = document.querySelector("#trendAnalysis");
const visualBrief = document.querySelector("#visualBrief");
const marketingAnalysis = document.querySelector("#marketingAnalysis");
const trendAngle = document.querySelector("#trendAngle");
const postStructure = document.querySelector("#postStructure");
const textAgentReport = document.querySelector("#textAgentReport");
const visualAgentReport = document.querySelector("#visualAgentReport");
const videoAgentReport = document.querySelector("#videoAgentReport");
const strategyAgentReport = document.querySelector("#strategyAgentReport");
const warningList = document.querySelector("#warningList");
const logOutput = document.querySelector("#logOutput");
const manualInput = document.querySelector("#manualInput");
const visualInput = document.querySelector("#visualInput");
const videoInput = document.querySelector("#videoInput");
const manualCount = document.querySelector("#manualCount");
const clearManualButton = document.querySelector("#clearManualButton");
const agentCards = [...document.querySelectorAll(".agent-card")];

const agentOrder = ["crawler", "content_creator", "manager_review", "publisher"];

function setAgentState(activeStep) {
  const activeIndex = agentOrder.indexOf(activeStep);
  agentCards.forEach((card) => {
    const index = agentOrder.indexOf(card.dataset.agent);
    const state = card.querySelector(".agent-state");
    const isActive = index === activeIndex;
    const isDone = activeIndex >= 0 && index < activeIndex;
    card.classList.toggle("active", isActive);
    card.classList.toggle("done", isDone);
    state.textContent = isActive ? "Running" : isDone ? "Done" : "Idle";
  });
}

function completeAgents() {
  agentCards.forEach((card) => {
    card.classList.remove("active");
    card.classList.add("done");
    card.querySelector(".agent-state").textContent = "Done";
  });
}

function resetAgents() {
  agentCards.forEach((card) => {
    card.classList.remove("active", "done");
    card.querySelector(".agent-state").textContent = "Idle";
  });
}

async function loadStatus() {
  const response = await fetch("/api/status");
  const status = await response.json();
  modeValue.textContent = `${status.ai_provider || "Local"} · ${status.ai_model || "template"}`;
  dryRunValue.textContent = status.dry_run ? "Dry-run on" : "Real publish";
  connectionState.textContent = "Ready";
  connectionState.classList.add("ready");
  renderWarnings(status.warnings || []);
}

async function runWorkflow() {
  runButton.disabled = true;
  runButton.querySelector(".button-icon").textContent = "…";
  approvalValue.textContent = "Running";
  resetAgents();
  setAgentState("crawler");

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        manual_competitor_posts: manualInput.value.trim(),
        manual_visual_notes: visualInput.value.trim(),
        manual_video_notes: videoInput.value.trim(),
      }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Workflow failed");
    }

    const result = payload.result;
    renderResult(result, payload.logs || "");
    completeAgents();
    lastRunValue.textContent = new Date().toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch (error) {
    approvalValue.textContent = "Error";
    connectionState.textContent = "Needs attention";
    connectionState.classList.remove("ready");
    safePayload.textContent = error.message;
    logOutput.textContent = error.stack || error.message;
  } finally {
    runButton.disabled = false;
    runButton.querySelector(".button-icon").textContent = "▶";
  }
}

function renderResult(result, logs) {
  const draft = result.draft_content || {};
  const publish = result.publish_result || {};
  const insights = result.competitor_insights || [];
  const approval = result.approval_status || "pending";

  approvalValue.textContent = approval;
  approvalBadge.textContent = approval;
  approvalBadge.className = `badge ${approval}`;
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
  trendAnalysis.textContent = result.facebook_trend_analysis || "Chưa có phân tích trend.";
  visualBrief.textContent = result.visual_creative_brief || draft.image_prompt || "Chưa có brief ảnh.";
  textAgentReport.textContent = result.text_insight_report || "Chưa có phân tích bài viết.";
  visualAgentReport.textContent = result.visual_insight_report || "Chưa có phân tích ảnh.";
  videoAgentReport.textContent = result.video_insight_report || "Chưa có phân tích video.";
  strategyAgentReport.textContent = result.strategic_direction || "Chưa có hướng chiến lược.";
  marketingAnalysis.textContent = draft.marketing_analysis || "Chưa có phân tích marketing.";
  trendAngle.textContent = draft.trend_angle || "Chưa có góc trend.";
  postStructure.textContent = draft.post_structure || "Chưa có cấu trúc bài.";
  logOutput.textContent = logs || formatMessages(result.messages || []);
  renderInsights(insights);
  updateManualCount(result.manual_posts_count || countManualPosts());
}

function renderInsights(insights) {
  insightCount.textContent = `${insights.length} nguồn`;
  if (!insights.length) {
    insightList.className = "insight-list empty-state";
    insightList.textContent = "Chưa có insight.";
    return;
  }

  insightList.className = "insight-list";
  insightList.innerHTML = insights
    .map((item) => {
      const topics = (item.key_topics || [])
        .map((topic) => `<span>${escapeHtml(topic.replaceAll("_", " "))}</span>`)
        .join("");
      return `
        <article class="insight-row">
          <div>
            <strong>${escapeHtml(item.page_name || "Unknown page")}</strong>
            <div class="topic-list">${topics}</div>
          </div>
          <p class="insight-summary">${escapeHtml(item.summary || item.post_content || "")}</p>
          <div class="engagement">
            <span>Engagement</span>
            <strong>${Number(item.engagement || 0).toLocaleString("vi-VN")}</strong>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderWarnings(warnings) {
  if (!warnings.length) {
    warningList.className = "warning-list empty-state";
    warningList.textContent = "Không có warning.";
    return;
  }

  warningList.className = "warning-list";
  warningList.innerHTML = warnings.map((warning) => `<span>${escapeHtml(warning)}</span>`).join("");
}

function countManualPosts() {
  const text = manualInput.value.trim();
  if (!text) {
    return 0;
  }
  return text.split(/\n\s*\n/).filter((block) => block.trim()).length;
}

function updateManualCount(count = countManualPosts()) {
  manualCount.textContent = `${count} bài nhập tay`;
}

function formatMessages(messages) {
  if (!messages.length) {
    return "Workflow completed without captured logs.";
  }
  return messages.map((message) => `[${message.role || "system"}] ${message.content || ""}`).join("\n");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

runButton.addEventListener("click", runWorkflow);
manualInput.addEventListener("input", () => updateManualCount());
clearManualButton.addEventListener("click", () => {
  manualInput.value = "";
  visualInput.value = "";
  videoInput.value = "";
  updateManualCount(0);
  manualInput.focus();
});
loadStatus().catch(() => {
  modeValue.textContent = "Unknown";
  dryRunValue.textContent = "-";
  connectionState.textContent = "Offline";
});
