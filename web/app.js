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
const finalTitleInput = document.querySelector("#finalTitleInput");
const finalBodyInput = document.querySelector("#finalBodyInput");
const finalCtaInput = document.querySelector("#finalCtaInput");
const finalTagsInput = document.querySelector("#finalTagsInput");
const finalCreativeSelect = document.querySelector("#finalCreativeSelect");
const finalCharCount = document.querySelector("#finalCharCount");
const resetFinalButton = document.querySelector("#resetFinalButton");
const copyFinalButton = document.querySelector("#copyFinalButton");
const fbPreviewText = document.querySelector("#fbPreviewText");
const fbPreviewImage = document.querySelector("#fbPreviewImage");
const publishStatus = document.querySelector("#publishStatus");
const publishMode = document.querySelector("#publishMode");
const postId = document.querySelector("#postId");
const safePayload = document.querySelector("#safePayload");
const insightList = document.querySelector("#insightList");
const insightCount = document.querySelector("#insightCount");
const trendAnalysis = document.querySelector("#trendAnalysis");
const adLibraryReport = document.querySelector("#adLibraryReport");
const referencedAdsList = document.querySelector("#referencedAdsList");
const referencedAdsCount = document.querySelector("#referencedAdsCount");
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
const autoTabButton = document.querySelector("#autoTabButton");
const manualTabButton = document.querySelector("#manualTabButton");
const autoSourcePanel = document.querySelector("#autoSourcePanel");
const manualSourcePanel = document.querySelector("#manualSourcePanel");
const creativeImageInput = document.querySelector("#creativeImageInput");
const creativeImageMode = document.querySelector("#creativeImageMode");
const creativeImagePreview = document.querySelector("#creativeImagePreview");
const creativeImageStatus = document.querySelector("#creativeImageStatus");
const creativeImageHint = document.querySelector("#creativeImageHint");
const agentCards = [...document.querySelectorAll(".agent-card")];

let activeSourceMode = "auto";
let uploadedCreativeImage = null;
let originalFinalDraft = null;
let currentCreativeAssets = [];

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

function setSourceMode(mode) {
  activeSourceMode = mode;
  const isManual = mode === "manual";
  autoTabButton.classList.toggle("active", !isManual);
  manualTabButton.classList.toggle("active", isManual);
  autoTabButton.setAttribute("aria-selected", String(!isManual));
  manualTabButton.setAttribute("aria-selected", String(isManual));
  autoSourcePanel.classList.toggle("active", !isManual);
  manualSourcePanel.classList.toggle("active", isManual);
  autoSourcePanel.hidden = isManual;
  manualSourcePanel.hidden = !isManual;
  syncSourceMode();
}

function syncSourceMode() {
  dataSourceValue.textContent = activeSourceMode === "manual" ? "Manual override" : "Auto Ad Library";
}

function syncCreativeImageMode() {
  const mode = creativeImageMode.value;
  const hasUpload = Boolean(uploadedCreativeImage);
  const labels = {
    auto: "Auto SmileUp",
    owned: hasUpload ? "Using uploaded image" : "Upload needed",
    layout_reference: hasUpload ? "Layout reference" : "Upload needed",
  };
  const hints = {
    auto: "Mặc định tạo ảnh mới từ nền phòng khám và logo SmileUp.",
    owned: "Dùng khi ảnh là của SmileUp hoặc ảnh bạn có quyền sử dụng.",
    layout_reference: "Chỉ lấy bố cục tổng quát; không dùng pixel, logo, mặt người hay tài sản gốc của ads.",
  };
  creativeImageStatus.textContent = labels[mode] || "Auto SmileUp";
  creativeImageHint.textContent = hints[mode] || hints.auto;
  creativeImageStatus.classList.toggle("warning", mode !== "auto" && !hasUpload);
}

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
  keywordValue.value = status.ad_library_keywords || "nha khoa răng sứ răng đẹp cấy implant";
  connectionState.textContent = "Ready";
  connectionState.classList.add("ready");
  syncSourceMode();
  renderWarnings(status.warnings || []);
}

async function runWorkflow() {
  runButton.disabled = true;
  runButton.querySelector(".button-icon").textContent = "...";
  approvalValue.textContent = "Running";
  syncSourceMode();
  adsValue.textContent = "-";
  durationValue.textContent = "-";
  resetAgents();
  setAgentState("crawler");

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        manual_competitor_posts: activeSourceMode === "manual" ? manualInput.value.trim() : "",
        manual_visual_notes: activeSourceMode === "manual" ? visualInput.value.trim() : "",
        manual_video_notes: activeSourceMode === "manual" ? videoInput.value.trim() : "",
        ad_library_keywords: keywordValue.value.trim(),
        creative_image_mode: creativeImageMode.value,
        creative_image_name: uploadedCreativeImage?.name || "",
        creative_image_data_url: uploadedCreativeImage?.dataUrl || "",
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
  const creativeAssets = result.creative_assets || [];

  approvalValue.textContent = approval;
  approvalBadge.textContent = approval;
  approvalBadge.className = `badge ${approval}`;
  dataSourceValue.textContent = sourceLabels[source] || source;
  if (result.ad_library_keywords) {
    keywordValue.value = result.ad_library_keywords;
  }
  adsValue.textContent = adCount ? `${adCount} ads` : source === "manual" ? "Manual" : "-";
  durationValue.textContent = typeof durationMs === "number" ? `${durationMs.toLocaleString("vi-VN")} ms` : "-";
  dailyReport.textContent = result.daily_report || "-";
  dailyStrategy.textContent = result.daily_strategy || "-";
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
  renderReferencedAds(result.ad_library_ads || []);
  renderContentPlan(result.content_plan || []);
  renderCreatives(creativeAssets);
  setFinalDraft(draft, creativeAssets);
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

function renderReferencedAds(ads) {
  referencedAdsCount.textContent = `${ads.length} ads`;
  if (!ads.length) {
    referencedAdsList.className = "referenced-ads-list empty-state";
    referencedAdsList.textContent = "Chưa có ads tham chiếu.";
    return;
  }

  referencedAdsList.className = "referenced-ads-list";
  referencedAdsList.innerHTML = ads
    .map((ad) => {
      const libraryId = ad.library_id || "";
      const adUrl = ad.ad_url || (libraryId ? `https://www.facebook.com/ads/library/?id=${encodeURIComponent(libraryId)}` : "https://www.facebook.com/ads/library/");
      const firstLine = String(ad.ad_text || "").split(/\r?\n/).find((line) => line.trim()) || "";
      const similarity = Number(ad.similarity || 0);
      const scoreLabel = similarity ? `${Math.round(similarity * 100)}% match` : "Matched";
      return `
        <article class="referenced-ad-card">
          <div>
            <div class="ad-card-topline">
              <span>${escapeHtml(ad.page_name || "Meta Ad Library")}</span>
              <strong>${escapeHtml(scoreLabel)}</strong>
            </div>
            <h3>${escapeHtml(firstLine || "Ad Library creative")}</h3>
            <p>${escapeHtml(ad.started_running || "No start date")}</p>
          </div>
          <a class="ad-link-button" href="${escapeHtml(adUrl)}" target="_blank" rel="noopener noreferrer">Mở ad</a>
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
            ${asset.source_policy ? `<p class="source-policy">${escapeHtml(asset.source_policy)}</p>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
}

function setFinalDraft(draft, assets) {
  originalFinalDraft = {
    title: draft.title || "",
    body: draft.body || "",
    call_to_action: draft.call_to_action || "",
    hashtags: Array.isArray(draft.hashtags) ? draft.hashtags : [],
  };
  currentCreativeAssets = Array.isArray(assets) ? assets : [];
  finalTitleInput.value = originalFinalDraft.title;
  finalBodyInput.value = originalFinalDraft.body;
  finalCtaInput.value = originalFinalDraft.call_to_action;
  finalTagsInput.value = originalFinalDraft.hashtags.join(" ");
  renderFinalCreativeOptions();
  updateFacebookPreview();
}

function renderFinalCreativeOptions() {
  finalCreativeSelect.innerHTML = "";
  if (!currentCreativeAssets.length) {
    const option = document.createElement("option");
    option.value = "-1";
    option.textContent = "Chưa có ảnh creative";
    finalCreativeSelect.appendChild(option);
    return;
  }

  currentCreativeAssets.forEach((asset, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${String(index + 1).padStart(2, "0")} · ${asset.service_line || asset.title || "SmileUp creative"}`;
    finalCreativeSelect.appendChild(option);
  });
  finalCreativeSelect.value = "0";
}

function updateFacebookPreview() {
  const message = formatFinalFacebookMessage();
  fbPreviewText.textContent = message || "Chạy workflow để xem bản preview cuối.";
  finalCharCount.textContent = `${message.length.toLocaleString("vi-VN")} ký tự`;
  safePayload.textContent = message || "Payload preview sẽ hiện ở đây.";

  const selectedIndex = Number(finalCreativeSelect.value);
  const selectedAsset = Number.isInteger(selectedIndex) ? currentCreativeAssets[selectedIndex] : null;
  if (selectedAsset?.image_path) {
    fbPreviewImage.className = "fb-preview-image";
    fbPreviewImage.innerHTML = `<img src="${escapeHtml(selectedAsset.image_path)}" alt="${escapeHtml(selectedAsset.title || "SmileUp creative")}" />`;
  } else {
    fbPreviewImage.className = "fb-preview-image empty";
    fbPreviewImage.textContent = "Ảnh creative sẽ hiện ở đây.";
  }
}

function formatFinalFacebookMessage() {
  const tags = normalizeHashtags(finalTagsInput.value).join(" ");
  return [finalTitleInput.value, finalBodyInput.value, finalCtaInput.value, tags]
    .map((part) => String(part || "").trim())
    .filter(Boolean)
    .join("\n\n");
}

function normalizeHashtags(value) {
  return String(value || "")
    .split(/[\s,]+/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .map((tag) => (tag.startsWith("#") ? tag : `#${tag}`));
}

async function copyFinalCaption() {
  const message = formatFinalFacebookMessage();
  if (!message) {
    return;
  }
  try {
    await navigator.clipboard.writeText(message);
    copyFinalButton.textContent = "Đã copy";
    setTimeout(() => {
      copyFinalButton.textContent = "Copy caption cuối";
    }, 1200);
  } catch {
    safePayload.textContent = message;
    copyFinalButton.textContent = "Đã đưa vào payload";
    setTimeout(() => {
      copyFinalButton.textContent = "Copy caption cuối";
    }, 1200);
  }
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
autoTabButton.addEventListener("click", () => setSourceMode("auto"));
manualTabButton.addEventListener("click", () => setSourceMode("manual"));
keywordValue.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    setSourceMode("auto");
    runWorkflow();
  }
});
manualInput.addEventListener("input", () => updateManualCount());
clearManualButton.addEventListener("click", () => {
  manualInput.value = "";
  visualInput.value = "";
  videoInput.value = "";
  updateManualCount(0);
  manualInput.focus();
});
creativeImageInput.addEventListener("change", () => {
  const file = creativeImageInput.files?.[0];
  if (!file) {
    uploadedCreativeImage = null;
    creativeImagePreview.className = "creative-image-preview empty";
    creativeImagePreview.textContent = "Chưa có ảnh upload";
    syncCreativeImageMode();
    return;
  }
  if (!file.type.startsWith("image/")) {
    uploadedCreativeImage = null;
    creativeImagePreview.className = "creative-image-preview empty";
    creativeImagePreview.textContent = "File không phải ảnh";
    syncCreativeImageMode();
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    uploadedCreativeImage = null;
    creativeImagePreview.className = "creative-image-preview empty";
    creativeImagePreview.textContent = "Ảnh vượt quá 8 MB";
    syncCreativeImageMode();
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    uploadedCreativeImage = {
      name: file.name,
      dataUrl: String(reader.result || ""),
    };
    creativeImagePreview.className = "creative-image-preview";
    creativeImagePreview.innerHTML = `<img src="${escapeHtml(uploadedCreativeImage.dataUrl)}" alt="${escapeHtml(file.name)}" /><span>${escapeHtml(file.name)}</span>`;
    if (creativeImageMode.value === "auto") {
      creativeImageMode.value = "owned";
    }
    syncCreativeImageMode();
  };
  reader.readAsDataURL(file);
});
creativeImageMode.addEventListener("change", syncCreativeImageMode);
finalTitleInput.addEventListener("input", updateFacebookPreview);
finalBodyInput.addEventListener("input", updateFacebookPreview);
finalCtaInput.addEventListener("input", updateFacebookPreview);
finalTagsInput.addEventListener("input", updateFacebookPreview);
finalCreativeSelect.addEventListener("change", updateFacebookPreview);
resetFinalButton.addEventListener("click", () => {
  if (!originalFinalDraft) {
    return;
  }
  finalTitleInput.value = originalFinalDraft.title;
  finalBodyInput.value = originalFinalDraft.body;
  finalCtaInput.value = originalFinalDraft.call_to_action;
  finalTagsInput.value = originalFinalDraft.hashtags.join(" ");
  finalCreativeSelect.value = currentCreativeAssets.length ? "0" : "-1";
  updateFacebookPreview();
});
copyFinalButton.addEventListener("click", copyFinalCaption);
setSourceMode("auto");
syncCreativeImageMode();
updateFacebookPreview();
loadStatus().catch(() => {
  modeValue.textContent = "Unknown";
  dryRunValue.textContent = "-";
  connectionState.textContent = "Offline";
});
