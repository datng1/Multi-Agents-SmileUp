const runButton = document.querySelector("#runButton");
const modeValue = document.querySelector("#modeValue");
const dryRunValue = document.querySelector("#dryRunValue");
const approvalValue = document.querySelector("#approvalValue");
const lastRunValue = document.querySelector("#lastRunValue");
const connectionState = document.querySelector("#connectionState");
const dataSourceValue = document.querySelector("#dataSourceValue");
const keywordValue = document.querySelector("#keywordValue");
const adsValue = document.querySelector("#adsValue");
const durationValue = document.querySelector("#durationValue");
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
const adLibraryReport = document.querySelector("#adLibraryReport");
const visualBrief = document.querySelector("#visualBrief");
const marketingAnalysis = document.querySelector("#marketingAnalysis");
const trendAngle = document.querySelector("#trendAngle");
const postStructure = document.querySelector("#postStructure");
const textAgentReport = document.querySelector("#textAgentReport");
const visualAgentReport = document.querySelector("#visualAgentReport");
const videoAgentReport = document.querySelector("#videoAgentReport");
const strategyAgentReport = document.querySelector("#strategyAgentReport");
const complianceAgentReport = document.querySelector("#complianceAgentReport");
const contentPlanList = document.querySelector("#contentPlanList");
const contentPlanCount = document.querySelector("#contentPlanCount");
const creativeGrid = document.querySelector("#creativeGrid");
const creativeCount = document.querySelector("#creativeCount");
const warningList = document.querySelector("#warningList");
const logOutput = document.querySelector("#logOutput");
const manualInput = document.querySelector("#manualInput");
const visualInput = document.querySelector("#visualInput");
const videoInput = document.querySelector("#videoInput");
const manualCount = document.querySelector("#manualCount");
const clearManualButton = document.querySelector("#clearManualButton");
const agentCards = [...document.querySelectorAll(".agent-card")];

const agentOrder = [
  "crawler",
  "text_insight",
  "trend_analysis",
  "visual_insight",
  "video_insight",
  "strategy",
  "content_creator",
  "compliance",
  "manager_review",
  "publisher",
];

const sourceLabels = {
  ad_library: "Auto Ad Library",
  manual: "Manual override",
  facebook: "Facebook Graph API",
  mock: "Demo data",
};

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
  keywordValue.textContent = status.ad_library_keywords || "-";
  dataSourceValue.textContent = status.ad_library_enabled ? "Auto Ad Library" : "Manual/Facebook";
  connectionState.textContent = "Ready";
  connectionState.classList.add("ready");
  renderWarnings(status.warnings || []);
}

async function runWorkflow() {
  runButton.disabled = true;
  runButton.querySelector(".button-icon").textContent = "...";
  approvalValue.textContent = "Running";
  dataSourceValue.textContent = countManualPosts() ? "Manual override" : "Auto Ad Library";
  adsValue.textContent = "-";
  durationValue.textContent = "-";
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

    renderResult(payload.result, payload.logs || "", payload.duration_ms);
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

function renderResult(result, logs, durationMs) {
  const draft = result.draft_content || {};
  const publish = result.publish_result || {};
  const insights = result.competitor_insights || [];
  const approval = result.approval_status || "pending";
  const source = result.data_source || (result.ad_library_ads?.length ? "ad_library" : "manual");
  const adCount = Array.isArray(result.ad_library_ads) ? result.ad_library_ads.length : 0;

  approvalValue.textContent = approval;
  approvalBadge.textContent = approval;
  approvalBadge.className = `badge ${approval}`;
  dataSourceValue.textContent = sourceLabels[source] || source;
  adsValue.textContent = adCount ? `${adCount} ads` : source === "manual" ? "Manual" : "-";
  durationValue.textContent = typeof durationMs === "number" ? `${durationMs.toLocaleString("vi-VN")} ms` : "-";
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
  adLibraryReport.textContent = result.ad_library_report || "Chưa có dữ liệu Ad Library.";
  visualBrief.textContent = result.visual_creative_brief || draft.image_prompt || "Chưa có brief ảnh.";
  textAgentReport.textContent = result.text_insight_report || "Chưa có phân tích bài viết.";
  visualAgentReport.textContent = result.visual_insight_report || "Chưa có phân tích ảnh.";
  videoAgentReport.textContent = result.video_insight_report || "Chưa có phân tích video.";
  strategyAgentReport.textContent = result.strategic_direction || "Chưa có hướng chiến lược.";
  complianceAgentReport.textContent = result.compliance_report || "Chưa có kiểm tra compliance.";
  marketingAnalysis.textContent = draft.marketing_analysis || "Chưa có phân tích marketing.";
  trendAngle.textContent = draft.trend_angle || "Chưa có góc trend.";
  postStructure.textContent = draft.post_structure || "Chưa có cấu trúc bài.";
  logOutput.textContent = logs || formatMessages(result.messages || []);
  renderInsights(insights);
  renderContentPlan(result.content_plan || []);
  renderCreatives(result.creative_assets || []);
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
        .map((topic) => `<span>${escapeHtml(String(topic).replaceAll("_", " "))}</span>`)
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

function renderContentPlan(variants) {
  contentPlanCount.textContent = `${variants.length} biến thể`;
  if (!variants.length) {
    contentPlanList.className = "content-plan-list empty-state";
    contentPlanList.textContent = "Chưa có campaign variants.";
    return;
  }

  contentPlanList.className = "content-plan-list";
  contentPlanList.innerHTML = variants
    .map((variant, index) => {
      const tags = (variant.hashtags || []).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
      return `
        <article class="variant-card">
          <div class="variant-topline">
            <span>${String(index + 1).padStart(2, "0")} · ${escapeHtml(variant.service_line || "post")}</span>
            <strong>${escapeHtml(variant.angle || "")}</strong>
          </div>
          <h3>${escapeHtml(variant.title || "-")}</h3>
          <p>${escapeHtml(variant.differentiation || "")}</p>
          <details>
            <summary>Xem caption</summary>
            <pre>${escapeHtml(variant.body || "")}</pre>
          </details>
          <div class="topic-list">${tags}</div>
        </article>
      `;
    })
    .join("");
}

function renderCreatives(assets) {
  creativeCount.textContent = `${assets.length} ảnh`;
  if (!assets.length) {
    creativeGrid.className = "creative-grid empty-state";
    creativeGrid.textContent = "Chưa có ảnh creative.";
    return;
  }

  creativeGrid.className = "creative-grid";
  creativeGrid.innerHTML = assets
    .map((asset) => {
      const imagePath = asset.image_path || "";
      return `
        <article class="creative-card">
          ${imagePath ? `<img src="${escapeHtml(imagePath)}" alt="${escapeHtml(asset.title || "SmileUp creative")}" />` : ""}
          <div>
            <span class="label">${escapeHtml(asset.service_line || "creative")}</span>
            <h3>${escapeHtml(asset.title || "-")}</h3>
            <p>${escapeHtml(asset.image_prompt || "")}</p>
          </div>
        </article>
      `;
    })
    .join("");
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
