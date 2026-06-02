const runButton = document.querySelector("#runButton");
const deepRunButton = document.querySelector("#deepRunButton");
const completionNotice = document.querySelector("#completionNotice");
const completionJumpButton = document.querySelector("#completionJumpButton");
const completionCloseButton = document.querySelector("#completionCloseButton");
const appFavicon = document.querySelector("#appFavicon");
const processingScreen = document.querySelector("#processingScreen");
const processingMode = document.querySelector("#processingMode");
const processingAgent = document.querySelector("#processingAgent");
const processingAgentDetail = document.querySelector("#processingAgentDetail");
const processingElapsed = document.querySelector("#processingElapsed");
const processingSteps = document.querySelector("#processingSteps");
const processingNote = document.querySelector("#processingNote");
const homeButton = document.querySelector("#homeButton");
const historyButton = document.querySelector("#historyButton");
const historyPanel = document.querySelector("#historyPanel");
const historyCloseButton = document.querySelector("#historyCloseButton");
const historyList = document.querySelector("#historyList");
const historyCount = document.querySelector("#historyCount");
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
const finalCreativeUpload = document.querySelector("#finalCreativeUpload");
const finalUseImageButton = document.querySelector("#finalUseImageButton");
const finalNoImageButton = document.querySelector("#finalNoImageButton");
const finalRemoveImageButton = document.querySelector("#finalRemoveImageButton");
const finalAddImageButton = document.querySelector("#finalAddImageButton");
const finalAddImagePreviewButton = document.querySelector("#finalAddImagePreviewButton");
const finalImageStatus = document.querySelector("#finalImageStatus");
const finalCharCount = document.querySelector("#finalCharCount");
const resetFinalButton = document.querySelector("#resetFinalButton");
const copyFinalButton = document.querySelector("#copyFinalButton");
const publishedPostLinkBox = document.querySelector("#publishedPostLinkBox");
const publishedPostLink = document.querySelector("#publishedPostLink");
const publishedPageResults = document.querySelector("#publishedPageResults");
const publishPageList = document.querySelector("#publishPageList");
const publishPageStatus = document.querySelector("#publishPageStatus");
const selectAllPagesButton = document.querySelector("#selectAllPagesButton");
const publishSelectedButton = document.querySelector("#publishSelectedButton");
const publishAllButton = document.querySelector("#publishAllButton");
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
const cmoActionBadge = document.querySelector("#cmoActionBadge");
const cmoObjective = document.querySelector("#cmoObjective");
const cmoDecision = document.querySelector("#cmoDecision");
const cmoSelected = document.querySelector("#cmoSelected");
const cmoFeedback = document.querySelector("#cmoFeedback");
const hardnessReport = document.querySelector("#hardnessReport");
const cmoJurySummary = document.querySelector("#cmoJurySummary");
const cmoBrief = document.querySelector("#cmoBrief");
const cmoScorecard = document.querySelector("#cmoScorecard");
const cmoDecisionGraph = document.querySelector("#cmoDecisionGraph");
const cmoGraphToggle = document.querySelector("#cmoGraphToggle");
const cmoDecisionGraphWrap = document.querySelector("#cmoDecisionGraphWrap");
const visualBrief = document.querySelector("#visualBrief");
const marketingAnalysis = document.querySelector("#marketingAnalysis");
const trendAngle = document.querySelector("#trendAngle");
const postStructure = document.querySelector("#postStructure");
const textAgentReport = document.querySelector("#textAgentReport");
const visualAgentReport = document.querySelector("#visualAgentReport");
const videoAgentReport = document.querySelector("#videoAgentReport");
const strategyAgentReport = document.querySelector("#strategyAgentReport");
const complianceAgentReport = document.querySelector("#complianceAgentReport");
const hardnessAgentReport = document.querySelector("#hardnessAgentReport");
const contentPlanList = document.querySelector("#contentPlanList");
const contentPlanCount = document.querySelector("#contentPlanCount");
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
let currentContentPlan = [];
let currentResult = null;
let publishPages = [];
let finalImageManuallyDisabled = false;
let pendingCompletionNotice = false;

const defaultDocumentTitle = document.title;
const defaultFaviconHref = "/assets/favicon.png";
const completionFaviconHref = "/assets/favicon-alert.png";

const agentOrder = [
  "crawler",
  "text_insight",
  "trend_analysis",
  "visual_insight",
  "video_insight",
  "strategy",
  "content_creator",
  "compliance",
  "hardness",
  "manager_review",
  "publisher",
];

const agentLabels = {
  crawler: "Crawler",
  text_insight: "Text Insight",
  trend_analysis: "Trend",
  visual_insight: "Visual",
  video_insight: "Video",
  strategy: "Strategy",
  content_creator: "Content",
  compliance: "Compliance",
  hardness: "Hardness",
  manager_review: "CMO Lead",
  publisher: "Publisher",
};

const agentDescriptions = {
  crawler: "Quét ads theo chế độ đã chọn, ưu tiên ads đối thủ và nguồn mới nhất.",
  text_insight: "Đọc hook, pain point, offer, CTA và ngôn ngữ khách hàng.",
  trend_analysis: "Tìm góc trend Facebook có thể dùng cho nha khoa mà vẫn phục vụ booking.",
  visual_insight: "Đọc bố cục ảnh, tín hiệu tin cậy và format creative đang hiệu quả.",
  video_insight: "Phân tích hook 3 giây đầu, nhịp kể chuyện và CTA nếu có video.",
  strategy: "Chọn chiến dịch tháng, phân tuyến ads lấy SĐT và chăm sóc page.",
  content_creator: "Viết các biến thể bài đăng theo chiến lược CMO.",
  compliance: "Kiểm tra claim, rủi ro y khoa, pháp lý và an toàn nền tảng.",
  hardness: "Đánh giá độ chắc của dữ liệu trước khi CMO ra quyết định.",
  manager_review: "CMO tổng hợp agent con, chấm điểm và quyết định publish/revise/reject.",
  publisher: "Chuẩn bị payload đăng bài sau khi CMO duyệt.",
};

const sourceLabels = {
  ad_library: "Auto Ad Library",
  ad_library_fallback: "Auto fallback",
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
  if (!creativeImageMode.value || creativeImageMode.value === "text_only") {
    creativeImageMode.value = "top_match_reference";
  }
  const mode = creativeImageMode.value || "top_match_reference";
  const hasUpload = Boolean(uploadedCreativeImage);
  const labels = {
    top_match_reference: "Có ảnh GPT Image",
    auto: "Auto SmileUp",
    owned: hasUpload ? "Using uploaded image" : "Upload needed",
    layout_reference: hasUpload ? "Layout reference" : "Upload needed",
    text_only: "GPT Image bắt buộc",
  };
  const hints = {
    top_match_reference: "GPT Image quét tối đa 12 ads match/mới nhất. Nếu có ảnh ads thì chỉ lấy bố cục làm reference; nếu không có ảnh hoặc ảnh lỗi tải thì tự gen ảnh mới theo bài viết, bối cảnh bác sĩ và bệnh nhân trong phòng khám Việt Nam, photorealistic, không chữ/banner/watermark.",
    auto: "Mặc định tạo ảnh mới từ nền phòng khám và logo SmileUp.",
    owned: "Dùng khi ảnh là của SmileUp hoặc ảnh bạn có quyền sử dụng.",
    layout_reference: "Chỉ lấy bố cục tổng quát; không dùng pixel, logo, mặt người hay tài sản gốc của ads.",
    text_only: "Workflow hiện bắt buộc gen 3 ảnh GPT Image 2; bạn vẫn có thể bỏ ảnh ở bước final review nếu không muốn đăng kèm ảnh.",
  };
  creativeImageStatus.textContent = labels[mode] || "Auto SmileUp";
  creativeImageHint.textContent = hints[mode] || hints.auto;
  const needsUpload = ["owned", "layout_reference"].includes(mode) && !hasUpload;
  creativeImageStatus.classList.toggle("warning", needsUpload);
  if (needsUpload) {
    creativeImageHint.textContent = "Chọn mode này cần upload ảnh trước khi chạy workflow.";
  }
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

function applyAgentProgress(statuses = {}, currentStep = "") {
  agentCards.forEach((card) => {
    const agent = card.dataset.agent;
    const status = statuses[agent] || (agent === currentStep ? "running" : "idle");
    const state = card.querySelector(".agent-state");
    const isActive = status === "running";
    const isDone = status === "done";
    card.classList.toggle("active", isActive);
    card.classList.toggle("done", isDone);
    state.textContent = isActive ? "Running" : isDone ? "Done" : "Idle";
  });
  updateProcessingScreen(statuses, currentStep);
}

function showProcessingScreen(scanMode = "deep") {
  if (!processingScreen) {
    return;
  }
  document.body.classList.add("is-running");
  processingMode.textContent = scanMode === "deep" ? "Deep scan 12 ads" : "Quick scan 5 ads";
  processingNote.textContent =
    scanMode === "deep"
      ? "Đang quét sâu 12 ads để có thêm tín hiệu và ảnh reference rộng hơn."
      : "Đang chạy nhanh 5 ads để ra chiến lược sớm hơn.";
  processingScreen.classList.remove("hidden-panel");
  updateProcessingScreen({}, "crawler", 0);
}

function hideProcessingScreen() {
  if (!processingScreen) {
    return;
  }
  processingScreen.classList.add("hidden-panel");
  document.body.classList.remove("is-running");
}

function notifyWorkflowComplete() {
  pendingCompletionNotice = true;
  document.body.classList.add("has-completion-notice");
  setBrowserTabAttention(true);
  if (!document.hidden) {
    showCompletionNotice();
  }
}

function showCompletionNotice() {
  if (!completionNotice) {
    return;
  }
  pendingCompletionNotice = false;
  setBrowserTabAttention(false);
  completionNotice.classList.remove("hidden-panel");
  window.clearTimeout(showCompletionNotice._timer);
  showCompletionNotice._timer = window.setTimeout(() => {
    hideCompletionNotice();
  }, 9000);
}

function hideCompletionNotice() {
  if (!completionNotice) {
    return;
  }
  completionNotice.classList.add("hidden-panel");
  document.body.classList.remove("has-completion-notice");
}

function clearCompletionNotice() {
  pendingCompletionNotice = false;
  window.clearTimeout(showCompletionNotice._timer);
  setBrowserTabAttention(false);
  hideCompletionNotice();
}

function setBrowserTabAttention(enabled) {
  document.title = enabled ? `● Hoàn tất - ${defaultDocumentTitle}` : defaultDocumentTitle;
  if (appFavicon) {
    appFavicon.href = enabled ? completionFaviconHref : defaultFaviconHref;
  }
}

function updateProcessingScreen(statuses = {}, currentStep = "", elapsedSeconds = null) {
  if (!processingScreen || processingScreen.classList.contains("hidden-panel")) {
    return;
  }
  const activeStep = currentStep || Object.keys(statuses).find((agent) => statuses[agent] === "running") || "crawler";
  processingAgent.textContent = agentLabel(activeStep);
  if (processingAgentDetail) {
    processingAgentDetail.textContent = agentDescriptions[activeStep] || "Đang xử lý bước hiện tại.";
  }
  if (elapsedSeconds !== null) {
    processingElapsed.textContent = `${elapsedSeconds}s`;
  }
  processingSteps.innerHTML = agentOrder
    .map((agent, index) => {
      const status = statuses[agent] || (agent === activeStep ? "running" : "idle");
      const className = status === "done" ? "done" : status === "running" ? "running" : "";
      const statusLabel = status === "done" ? "Xong" : status === "running" ? "Đang làm" : "Chờ";
      return `
        <div class="processing-step ${className}">
          <span>${String(index + 1).padStart(2, "0")}</span>
          <strong>${escapeHtml(agentLabel(agent))}</strong>
          <small>${statusLabel}</small>
        </div>
      `;
    })
    .join("");
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

function resetFinalReview() {
  originalFinalDraft = null;
  currentCreativeAssets = [];
  currentContentPlan = [];
  finalImageManuallyDisabled = false;
  finalTitleInput.value = "";
  finalBodyInput.value = "";
  finalCtaInput.value = "";
  finalTagsInput.value = "";
  renderFinalCreativeOptions(-1);
  updateFacebookPreview();
  publishPageStatus.textContent = "Publisher chỉ chạy khi CMO đã duyệt và bạn bấm đăng.";
  renderPublishedPostLink({});
}

function resetCmoPanel() {
  cmoActionBadge.textContent = "Running";
  cmoObjective.textContent = "CMO đang nhận dữ liệu mới từ workflow.";
  cmoDecision.textContent = "Đang chờ quyết định mới.";
  cmoSelected.textContent = "Đang chờ chọn variant/creative.";
  cmoFeedback.textContent = "Đang tổng hợp feedback mới cho các agent.";
  hardnessReport.textContent = "Hardness Agent đang đánh giá độ chắc dữ liệu mới.";
  cmoJurySummary.textContent = "CMO Jury đang chờ phiếu đánh giá từ các model khả dụng.";
  cmoBrief.textContent = "CMO brief sẽ được tạo lại sau lượt chạy này.";
  cmoScorecard.className = "cmo-scorecard empty-state";
  cmoScorecard.textContent = "Đang tạo scorecard mới.";
  cmoDecisionGraph.className = "got-graph empty-state";
  cmoDecisionGraph.textContent = "Đang dựng decision graph mới.";
  cmoGraphToggle.setAttribute("aria-expanded", "false");
  cmoGraphToggle.textContent = "Mở đồ thị quyết định của CMO";
  cmoDecisionGraphWrap.classList.add("hidden-panel");
}

function resetRunOutputs() {
  approvalValue.textContent = "Running";
  approvalBadge.textContent = "running";
  approvalBadge.className = "badge";
  connectionState.textContent = "Running";
  connectionState.classList.add("ready");
  syncSourceMode();
  adsValue.textContent = "-";
  durationValue.textContent = "-";
  lastRunValue.textContent = "Đang chạy...";

  dailyReport.textContent = "Đang tạo báo cáo mới...";
  dailyStrategy.textContent = "Đang tạo chiến lược mới...";
  publishStatus.textContent = "-";
  publishMode.textContent = "-";
  postId.textContent = "-";

  trendAnalysis.textContent = "Đang phân tích trend mới...";
  adLibraryReport.textContent = "Đang quét Ad Library mới...";
  visualBrief.textContent = "Đang tạo brief ảnh mới...";
  textAgentReport.textContent = "Đang phân tích bài viết mới...";
  visualAgentReport.textContent = "Đang phân tích ảnh mới...";
  videoAgentReport.textContent = "Đang phân tích video mới...";
  strategyAgentReport.textContent = "Đang chọn hướng chiến lược mới...";
  complianceAgentReport.textContent = "Đang kiểm tra compliance mới...";
  hardnessAgentReport.textContent = "Đang đánh giá hardness mới...";
  marketingAnalysis.textContent = "Đang tạo phân tích marketing mới...";
  trendAngle.textContent = "Đang chọn góc trend mới...";
  postStructure.textContent = "Đang dựng cấu trúc bài mới...";
  logOutput.textContent = "Workflow mới đang chạy...";

  renderInsights([]);
  renderReferencedAds([]);
  renderContentPlan([]);
  renderCreatives([]);
  resetCmoPanel();
  resetFinalReview();
  renderPublishedPostLink({});
  safePayload.textContent = "Payload mới sẽ hiển thị khi workflow hoàn tất.";
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
  renderPublishPages(status.publish_pages || []);
}

function setRunButtons(isRunning, scanMode = "deep") {
  runButton.disabled = true;
  deepRunButton.disabled = true;
  runButton.querySelector(".button-icon").textContent = isRunning ? "..." : "▶";
  runButton.lastChild.textContent = isRunning && scanMode === "deep" ? " Đang quét sâu" : " Quét sâu 12 ads";
  deepRunButton.textContent = isRunning && scanMode === "quick" ? "Đang chạy nhanh..." : "Chạy nhanh 5 ads";
}

async function runWorkflow(scanMode = "deep") {
  clearCompletionNotice();
  setRunButtons(true, scanMode);
  showProcessingScreen(scanMode);
  homeButton.classList.add("hidden-panel");
  resetAgents();
  resetRunOutputs();
  setAgentState("crawler");
  safePayload.textContent =
    scanMode === "deep"
      ? "Đã tạo job quét sâu 12 ads. UI sẽ cập nhật từng agent khi backend chạy."
      : "Đã tạo job chạy nhanh 5 ads. UI sẽ cập nhật từng agent khi backend chạy.";

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        manual_competitor_posts: activeSourceMode === "manual" ? manualInput.value.trim() : "",
        manual_visual_notes: activeSourceMode === "manual" ? visualInput.value.trim() : "",
        manual_video_notes: activeSourceMode === "manual" ? videoInput.value.trim() : "",
        ad_library_keywords: keywordValue.value.trim(),
        scan_mode: scanMode,
        creative_image_mode: creativeImageMode.value || "top_match_reference",
        creative_image_name: uploadedCreativeImage?.name || "",
        creative_image_data_url: uploadedCreativeImage?.dataUrl || "",
      }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Workflow failed");
    }
    if (payload.job_id) {
      safePayload.textContent = `Job ${payload.job_id} đã nhận. Bạn có thể theo dõi từng agent ngay trên màn hình này.`;
    }
    const completedPayload = payload.job_id ? await waitForWorkflowJob(payload.job_id) : payload;

    renderResult(completedPayload.result, completedPayload.logs || "", completedPayload.duration_ms, completedPayload.history_hit);
    notifyWorkflowComplete();
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
    hideProcessingScreen();
    runButton.disabled = false;
    deepRunButton.disabled = false;
    runButton.querySelector(".button-icon").textContent = "▶";
    runButton.lastChild.textContent = " Quét sâu 12 ads";
    deepRunButton.textContent = "Chạy nhanh 5 ads";
  }
}

async function waitForWorkflowJob(jobId) {
  safePayload.textContent = `Job ${jobId} đang chạy nền. Các agent con có thể gọi GPT/Gemini; ảnh GPT Image chỉ gen tối đa 3 creative ưu tiên tuyến ads để tránh chờ quá lâu.`;
  let attempt = 0;
  while (true) {
    await sleep(3000);
    attempt += 1;
    const response = await fetch(`/api/job?id=${encodeURIComponent(jobId)}`, { cache: "no-store" });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Workflow job failed");
    }
    const elapsed = payload.started_at ? Math.round(Date.now() / 1000 - payload.started_at) : attempt * 3;
    if (payload.status === "completed") {
      applyAgentProgress(payload.agent_statuses || {}, payload.current_step || "");
      updateProcessingScreen(payload.agent_statuses || {}, payload.current_step || "", elapsed);
      return payload;
    }
    if (payload.status === "error") {
      throw new Error(payload.error || "Workflow job failed");
    }
    durationValue.textContent = `${elapsed}s`;
    applyAgentProgress(payload.agent_statuses || {}, payload.current_step || "");
    const currentLabel = agentLabel(payload.current_step);
    updateProcessingScreen(payload.agent_statuses || {}, payload.current_step || "", elapsed);
    safePayload.textContent = `Job ${jobId} đang chạy (${elapsed}s). Agent hiện tại: ${currentLabel}.`;
    logOutput.textContent = payload.logs || "Workflow đang chạy...";
  }
}

function agentLabel(agentName) {
  return agentLabels[agentName] || "đang khởi tạo";
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function renderResult(result, logs, durationMs, historyHit = false) {
  currentResult = result || null;
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
  durationValue.textContent = historyHit
    ? "Đã mở từ lịch sử"
    : typeof durationMs === "number"
      ? `${durationMs.toLocaleString("vi-VN")} ms`
      : "-";
  dailyReport.textContent = result.daily_report || "-";
  dailyStrategy.textContent = result.daily_strategy || "-";
  publishStatus.textContent = publish.publisher_status || "-";
  publishMode.textContent = publish.publish_mode || "-";
  postId.textContent = publish.published_post_id || "-";
  safePayload.textContent = publish.safe_payload_preview || JSON.stringify(publish, null, 2);
  renderPublishedPostLink(publish);
  trendAnalysis.textContent = result.facebook_trend_analysis || "Chưa có phân tích trend.";
  adLibraryReport.textContent = result.ad_library_report || "Chưa có dữ liệu Ad Library.";
  visualBrief.textContent = result.visual_creative_brief || draft.image_prompt || "Chưa có brief ảnh.";
  textAgentReport.textContent = result.text_insight_report || "Chưa có phân tích bài viết.";
  visualAgentReport.textContent = result.visual_insight_report || "Chưa có phân tích ảnh.";
  videoAgentReport.textContent = result.video_insight_report || "Chưa có phân tích video.";
  strategyAgentReport.textContent = result.strategic_direction || "Chưa có hướng chiến lược.";
  complianceAgentReport.textContent = result.compliance_report || "Chưa có kiểm tra compliance.";
  hardnessAgentReport.textContent = result.hardness_report || "Chưa có đánh giá hardness.";
  marketingAnalysis.textContent = draft.marketing_analysis || "Chưa có phân tích marketing.";
  trendAngle.textContent = draft.trend_angle || "Chưa có góc trend.";
  postStructure.textContent = draft.post_structure || "Chưa có cấu trúc bài.";
  logOutput.textContent = logs || formatMessages(result.messages || []);
  renderInsights(insights);
  renderReferencedAds(result.ad_library_ads || []);
  renderCmoDecision(result);
  renderContentPlan(result.content_plan || []);
  renderCreatives(creativeAssets);
  setFinalDraft(draft, creativeAssets, result.cmo_selected_creative_index);
  updateManualCount(result.manual_posts_count || countManualPosts());
  highlightResultPanels();
}

function highlightResultPanels() {
  [document.querySelector(".cmo-panel"), document.querySelector(".content-plan-panel"), document.querySelector(".post-panel")]
    .filter(Boolean)
    .forEach((panel) => {
      panel.classList.remove("highlight-result");
      requestAnimationFrame(() => panel.classList.add("highlight-result"));
    });
}

function formatCacheAge(seconds) {
  const safeSeconds = Math.max(0, Number(seconds || 0));
  if (safeSeconds < 60) {
    return `${Math.round(safeSeconds)}s`;
  }
  if (safeSeconds < 3600) {
    return `${Math.round(safeSeconds / 60)} phút`;
  }
  if (safeSeconds < 86400) {
    return `${Math.round(safeSeconds / 3600)} giờ`;
  }
  return `${Math.round(safeSeconds / 86400)} ngày`;
}

async function toggleHistoryPanel() {
  const isOpen = historyButton.getAttribute("aria-expanded") === "true";
  if (isOpen) {
    closeHistoryPanel();
    return;
  }
  historyButton.setAttribute("aria-expanded", "true");
  historyPanel.classList.remove("hidden-panel");
  await loadHistory();
  requestAnimationFrame(() => {
    historyPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function closeHistoryPanel() {
  historyButton.setAttribute("aria-expanded", "false");
  historyPanel.classList.add("hidden-panel");
}

async function loadHistory() {
  historyList.className = "history-list empty-state";
  historyList.textContent = "Đang tải lịch sử...";
  const response = await fetch("/api/history", { cache: "no-store" });
  const payload = await response.json();
  if (!payload.ok) {
    throw new Error(payload.error || "Không tải được lịch sử.");
  }
  renderHistoryList(payload.items || []);
}

function renderHistoryList(items) {
  historyCount.textContent = `${items.length} lượt`;
  if (!items.length) {
    historyList.className = "history-list empty-state";
    historyList.textContent = "Chưa có lịch sử trong 7 ngày gần nhất.";
    return;
  }
  historyList.className = "history-list";
  historyList.innerHTML = items
    .map((item) => {
      const created = item.created_at ? new Date(item.created_at).toLocaleString("vi-VN") : "-";
      const owner = item.owner_username ? ` · ${escapeHtml(item.owner_username)}` : "";
      return `
        <article class="history-card">
          <div>
            <span>${escapeHtml(created)}${owner}</span>
            <h3>${escapeHtml(item.title || "Workflow result")}</h3>
            <p>${escapeHtml(item.keyword || "nha khoa răng sứ răng đẹp cấy implant")}</p>
            <small>${Number(item.ads_count || 0)} ads · ${Number(item.competitor_ads || 0)} đối thủ · ${escapeHtml(item.cmo_decision || item.approval_status || "pending")}</small>
          </div>
          <div class="history-card-actions">
            <button class="secondary-button compact use-history-button" type="button" data-history-id="${escapeHtml(item.history_id)}">Mở lại</button>
            <button class="secondary-button compact danger delete-history-button" type="button" data-history-id="${escapeHtml(item.history_id)}">Xóa</button>
          </div>
        </article>
      `;
    })
    .join("");
}

async function openHistoryItem(historyId) {
  const response = await fetch(`/api/history?id=${encodeURIComponent(historyId)}`, { cache: "no-store" });
  const payload = await response.json();
  if (!payload.ok) {
    throw new Error(payload.error || "Không mở được lịch sử.");
  }
  renderResult(payload.result, payload.logs || "", payload.duration_ms, true);
  lastRunValue.textContent = payload.summary?.created_at ? new Date(payload.summary.created_at).toLocaleTimeString("vi-VN") : "History";
  homeButton.classList.remove("hidden-panel");
  closeHistoryPanel();
}

async function deleteHistoryItem(historyId) {
  if (!window.confirm("Xóa bản lịch sử này khỏi 7 ngày gần nhất?")) {
    return;
  }
  const response = await fetch(`/api/history?id=${encodeURIComponent(historyId)}`, { method: "DELETE" });
  const payload = await response.json();
  if (!payload.ok) {
    throw new Error(payload.error || "Không xóa được lịch sử.");
  }
  await loadHistory();
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
  const highMatchCount = ads.filter((ad) => Number(ad.similarity || 0) >= 0.95).length;
  referencedAdsCount.textContent = `${highMatchCount} ads >=95% · ${ads.length} tổng`;
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
      const sourceLabel = ad.source_type === "competitor_page" ? "Đối thủ ưu tiên" : "Keyword scan";
      return `
        <article class="referenced-ad-card">
          <div>
            <div class="ad-card-topline">
              <span>${escapeHtml(ad.page_name || "Meta Ad Library")}</span>
              <strong>${escapeHtml(scoreLabel)}</strong>
            </div>
            <span class="ad-source-chip">${escapeHtml(sourceLabel)}</span>
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

function renderCmoDecision(result) {
  const selectedVariant = Number(result.cmo_selected_variant_index);
  const selectedCreative = Number(result.cmo_selected_creative_index);
  cmoActionBadge.textContent = result.cmo_next_action || "waiting";
  cmoObjective.textContent = result.cmo_objective || "CMO nha khoa SmileUp: tăng lịch tư vấn răng sứ và implant.";
  cmoDecision.textContent = `${result.cmo_decision || "PENDING"} · ${result.approval_status || "pending"}`;
  cmoSelected.textContent = `Variant ${selectedVariant >= 0 ? `#${selectedVariant + 1}` : "chưa chọn"} · Creative ${selectedCreative >= 0 ? `#${selectedCreative + 1}` : "chưa chọn"}`;
  cmoFeedback.textContent = result.cmo_feedback || result.manager_feedback || "Chưa có feedback.";
  hardnessReport.textContent = result.hardness_report || "Hardness Agent chưa có đánh giá.";
  cmoJurySummary.textContent = result.cmo_jury_summary || "CMO Jury chưa có phiếu model.";
  cmoBrief.textContent = result.monthly_strategy || result.strategic_direction || "CMO sẽ tổng kết chiến lược tháng ở đây.";

  const scorecard = Array.isArray(result.cmo_scorecard) ? result.cmo_scorecard : [];
  if (!scorecard.length) {
    cmoScorecard.className = "cmo-scorecard empty-state";
    cmoScorecard.textContent = "Chưa có scorecard.";
    renderDecisionGraph(result.cmo_decision_graph, result.cmo_graph_summary);
    return;
  }
  cmoScorecard.className = "cmo-scorecard";
  cmoScorecard.innerHTML = scorecard
    .map((item) => {
      const isPicked = Number(item.index) === selectedVariant;
      return `
        <article class="cmo-score-card ${isPicked ? "picked" : ""}">
          <div>
            <strong>${String(Number(item.index) + 1).padStart(2, "0")} · ${escapeHtml(item.campaign_track || "post")} · ${escapeHtml(item.service_line || "post")}</strong>
            <span>${escapeHtml(isPicked ? "CMO pick" : `${Number(item.score || 0)} điểm`)}</span>
          </div>
          <h3>${escapeHtml(item.title || "-")}</h3>
          <p>${escapeHtml(item.decision_note || "")}</p>
        </article>
      `;
    })
    .join("");
  renderDecisionGraph(result.cmo_decision_graph, result.cmo_graph_summary);
}

function renderDecisionGraph(graph, summary) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  if (!nodes.length) {
    cmoDecisionGraph.className = "got-graph empty-state";
    cmoDecisionGraph.textContent = summary || "Chưa có decision graph.";
    return;
  }

  const selectedPath = new Set(Array.isArray(graph?.selected_path) ? graph.selected_path : []);
  const positions = buildMindMapPositions(nodes, selectedPath);
  cmoDecisionGraph.className = "got-graph";
  const lineHtml = edges
    .filter((edge) => positions.has(edge.source) && positions.has(edge.target))
    .slice(0, 24)
    .map((edge) => {
      const source = positions.get(edge.source);
      const target = positions.get(edge.target);
      const isPathEdge = selectedPath.has(edge.source) && selectedPath.has(edge.target);
      return `
        <line
          class="${isPathEdge ? "path-link" : ""}"
          data-source="${escapeHtml(edge.source)}"
          data-target="${escapeHtml(edge.target)}"
          x1="${source.x}"
          y1="${source.y}"
          x2="${target.x}"
          y2="${target.y}"
        ></line>
      `;
    })
    .join("");
  const nodeHtml = nodes
    .map((node) => {
      const score = typeof node.score === "number" ? `<span>${Number(node.score)}đ</span>` : "";
      const inPath = selectedPath.has(node.id);
      const position = positions.get(node.id) || { x: 50, y: 50 };
      return `
        <article
          class="got-node got-bubble ${escapeHtml(node.type || "node")} ${escapeHtml(node.status || "neutral")} ${inPath ? "in-path" : ""}"
          data-node="${escapeHtml(node.id || "")}"
          style="--x:${position.x}%; --y:${position.y}%;"
          title="Kéo bubble để chỉnh vị trí"
        >
          <div>
            <strong>${escapeHtml(node.type || "node")}</strong>
            ${score}
          </div>
          <p>${escapeHtml(node.label || node.id || "-")}</p>
        </article>
      `;
    })
    .join("");
  cmoDecisionGraph.innerHTML = `
    <pre>${escapeHtml(summary || "Graph-of-Thought CMO đã dựng xong.")}</pre>
    <div class="got-map-hint">Kéo từng bubble để chỉnh vị trí nếu node bị chồng lên nhau.</div>
    <div class="got-mind-map">
      <svg class="got-link-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${lineHtml}</svg>
      ${nodeHtml}
    </div>
  `;
  enableMindMapDrag(cmoDecisionGraph.querySelector(".got-mind-map"));
}

function buildMindMapPositions(nodes, selectedPath) {
  const positions = new Map();
  const nodeIds = new Set(nodes.map((node) => node.id));
  const centerNode =
    nodes.find((node) => node.id === "cmo_decision") ||
    nodes.find((node) => String(node.id || "").includes("cmo")) ||
    nodes[nodes.length - 1];
  if (!centerNode) {
    return positions;
  }

  positions.set(centerNode.id, { x: 50, y: 50 });
  const pathIds = [...selectedPath].filter((id) => id !== centerNode.id && nodeIds.has(id));
  const otherIds = nodes.map((node) => node.id).filter((id) => id !== centerNode.id && !selectedPath.has(id));
  placeRing(positions, pathIds, Math.min(42, 28 + pathIds.length * 2.2), -170, 25, 50, 50);
  placeRing(positions, otherIds, Math.min(46, 34 + otherIds.length * 1.4), 55, 305, 50, 50);
  relaxMindMapPositions(positions, nodes);
  return positions;
}

function placeRing(positions, ids, radius, startDeg, endDeg, centerX, centerY) {
  if (!ids.length) {
    return;
  }
  const span = ids.length === 1 ? 0 : endDeg - startDeg;
  ids.forEach((id, index) => {
    const angle = (startDeg + (span * index) / Math.max(ids.length - 1, 1)) * (Math.PI / 180);
    const x = centerX + Math.cos(angle) * radius;
    const y = centerY + Math.sin(angle) * radius * 0.78;
    positions.set(id, {
      x: Math.max(8, Math.min(92, Number(x.toFixed(2)))),
      y: Math.max(12, Math.min(88, Number(y.toFixed(2)))),
    });
  });
}

function relaxMindMapPositions(positions, nodes) {
  const ids = nodes.map((node) => node.id).filter((id) => positions.has(id));
  for (let pass = 0; pass < 14; pass += 1) {
    for (let i = 0; i < ids.length; i += 1) {
      for (let j = i + 1; j < ids.length; j += 1) {
        const a = positions.get(ids[i]);
        const b = positions.get(ids[j]);
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const distance = Math.hypot(dx, dy) || 0.1;
        const minDistance = 16;
        if (distance >= minDistance) {
          continue;
        }
        const push = (minDistance - distance) / 2;
        const ux = dx / distance;
        const uy = dy / distance;
        a.x = Math.max(8, Math.min(92, Number((a.x - ux * push).toFixed(2))));
        a.y = Math.max(12, Math.min(88, Number((a.y - uy * push).toFixed(2))));
        b.x = Math.max(8, Math.min(92, Number((b.x + ux * push).toFixed(2))));
        b.y = Math.max(12, Math.min(88, Number((b.y + uy * push).toFixed(2))));
      }
    }
  }
}

function enableMindMapDrag(map) {
  if (!map) {
    return;
  }
  const nodes = [...map.querySelectorAll(".got-bubble")];
  const nodeById = new Map(nodes.map((node) => [node.dataset.node, node]));

  const updateLines = () => {
    const mapRect = map.getBoundingClientRect();
    map.querySelectorAll(".got-link-layer line").forEach((line) => {
      const source = nodeById.get(line.dataset.source);
      const target = nodeById.get(line.dataset.target);
      if (!source || !target || !mapRect.width || !mapRect.height) {
        return;
      }
      const sourceRect = source.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      line.setAttribute("x1", (((sourceRect.left + sourceRect.width / 2 - mapRect.left) / mapRect.width) * 100).toFixed(2));
      line.setAttribute("y1", (((sourceRect.top + sourceRect.height / 2 - mapRect.top) / mapRect.height) * 100).toFixed(2));
      line.setAttribute("x2", (((targetRect.left + targetRect.width / 2 - mapRect.left) / mapRect.width) * 100).toFixed(2));
      line.setAttribute("y2", (((targetRect.top + targetRect.height / 2 - mapRect.top) / mapRect.height) * 100).toFixed(2));
    });
  };

  nodes.forEach((node) => {
    node.addEventListener("pointerdown", (event) => {
      if (window.getComputedStyle(node).position !== "absolute") {
        return;
      }
      event.preventDefault();
      node.setPointerCapture(event.pointerId);
      node.classList.add("dragging");

      const moveNode = (moveEvent) => {
        const mapRect = map.getBoundingClientRect();
        const x = ((moveEvent.clientX - mapRect.left) / mapRect.width) * 100;
        const y = ((moveEvent.clientY - mapRect.top) / mapRect.height) * 100;
        node.style.setProperty("--x", `${Math.max(8, Math.min(92, x)).toFixed(2)}%`);
        node.style.setProperty("--y", `${Math.max(12, Math.min(88, y)).toFixed(2)}%`);
        updateLines();
      };

      const stopDrag = () => {
        node.classList.remove("dragging");
        node.removeEventListener("pointermove", moveNode);
        node.removeEventListener("pointerup", stopDrag);
        node.removeEventListener("pointercancel", stopDrag);
      };

      node.addEventListener("pointermove", moveNode);
      node.addEventListener("pointerup", stopDrag);
      node.addEventListener("pointercancel", stopDrag);
    });
  });

  requestAnimationFrame(updateLines);
}

function renderContentPlan(variants) {
  currentContentPlan = Array.isArray(variants) ? variants : [];
  const adsCount = currentContentPlan.filter((variant) => (variant.campaign_track || "ads_effective") === "ads_effective").length;
  const careCount = currentContentPlan.filter((variant) => variant.campaign_track === "page_care").length;
  contentPlanCount.textContent = `${adsCount} ads · ${careCount} chăm sóc`;
  if (!currentContentPlan.length) {
    contentPlanList.className = "content-plan-list empty-state";
    contentPlanList.textContent = "Chưa có campaign variants.";
    return;
  }

  contentPlanList.className = "content-plan-list";
  const groups = [
    {
      key: "ads_effective",
      title: "Tuyến 1: Bài ads hiệu quả",
      note: "Dựa trên ads match >=95%, mục tiêu lấy SĐT/inbox để đội ngũ SmileUp gọi lại.",
    },
    {
      key: "page_care",
      title: "Tuyến 2: Chăm sóc page",
      note: "Nuôi niềm tin, tăng comment/save/share và tạo nền cho các bài ads chuyển đổi.",
    },
  ];
  contentPlanList.innerHTML = groups
    .map((group) => {
      const items = currentContentPlan
        .map((variant, index) => ({ variant, index }))
        .filter((item) => (item.variant.campaign_track || "ads_effective") === group.key);
      if (!items.length) {
        return "";
      }
      return `
        <section class="content-track-group ${group.key}">
          <div class="track-heading">
            <div>
              <span class="track-pill ${group.key}">${escapeHtml(group.title)}</span>
              <p>${escapeHtml(group.note)}</p>
            </div>
            <strong>${items.length} bài</strong>
          </div>
          <div class="track-card-grid">
            ${items.map(({ variant, index }) => renderContentVariantCard(variant, index)).join("")}
          </div>
        </section>
      `;
    })
    .join("");
}

function renderContentVariantCard(variant, index) {
  const tags = (variant.hashtags || []).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
  const role = variant.monthly_role || (variant.campaign_track === "page_care" ? "Chăm sóc page" : "Ads lấy SĐT");
  return `
    <article class="variant-card">
      <div class="variant-topline">
        <span>${String(index + 1).padStart(2, "0")} · ${escapeHtml(variant.service_line || "post")} · ${escapeHtml(role)}</span>
        <strong>${escapeHtml(variant.angle || "")}</strong>
      </div>
      <h3>${escapeHtml(variant.title || "-")}</h3>
      <p>${escapeHtml(variant.differentiation || "")}</p>
      <details>
        <summary>Xem caption</summary>
        <pre>${escapeHtml(variant.body || "")}</pre>
      </details>
      <div class="variant-actions">
        <button class="secondary-button use-variant-button" type="button" data-variant-index="${index}">Dùng làm bài viết</button>
      </div>
      <div class="topic-list">${tags}</div>
    </article>
  `;
}

function useVariantAsFinal(index) {
  const variant = currentContentPlan[index];
  if (!variant) {
    return;
  }

  originalFinalDraft = {
    title: variant.title || "",
    body: variant.body || "",
    call_to_action: variant.call_to_action || "",
    hashtags: Array.isArray(variant.hashtags) ? variant.hashtags : [],
  };
  finalTitleInput.value = originalFinalDraft.title;
  finalBodyInput.value = originalFinalDraft.body;
  finalCtaInput.value = originalFinalDraft.call_to_action;
  finalTagsInput.value = originalFinalDraft.hashtags.join(" ");

  if (currentCreativeAssets[index]?.image_path) {
    finalImageManuallyDisabled = false;
    finalCreativeSelect.value = String(index);
  } else if (!finalImageManuallyDisabled && currentCreativeAssets[0]?.image_path) {
    finalCreativeSelect.value = "0";
  }

  marketingAnalysis.textContent = variant.marketing_analysis || "Campaign này chưa có phân tích marketing riêng.";
  trendAngle.textContent = variant.trend_angle || "Campaign này chưa có góc trend riêng.";
  postStructure.textContent = variant.post_structure || "Campaign này chưa có cấu trúc bài riêng.";
  updateFacebookPreview();
  markUsedVariant(index);
  document.querySelector(".post-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function markUsedVariant(index) {
  contentPlanList.querySelectorAll(".use-variant-button").forEach((button) => {
    const card = button.closest(".variant-card");
    card?.classList.toggle("used", Number(button.dataset.variantIndex) === index);
  });
}

function renderCreatives(assets) {
  return assets;
}

function renderPublishedPostLink(publish) {
  const postUrl = publish.published_post_url || publish.permalink_url || "";
  const postIdValue = publish.published_post_id || "";
  const fallbackUrl = postIdValue && !publish.dry_run ? `https://www.facebook.com/${encodeURIComponent(postIdValue)}` : "";
  const finalUrl = postUrl || fallbackUrl;
  const pageResults = Array.isArray(publish.page_results) ? publish.page_results : [];
  const resultLinks = pageResults
    .map((item) => {
      const label = `${item.published ? "Đã đăng" : item.dry_run ? "Dry-run" : "Lỗi"} · ${item.page_name || item.page_id}`;
      if (item.published_post_url) {
        return `<a href="${escapeHtml(item.published_post_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
      }
      return `<span>${escapeHtml(label)}${item.error ? `: ${escapeHtml(item.error)}` : ""}</span>`;
    })
    .join("");
  publishedPageResults.innerHTML = resultLinks;

  if (!finalUrl && !resultLinks) {
    publishedPostLinkBox.hidden = true;
    publishedPostLink.removeAttribute("href");
    return;
  }
  if (finalUrl && publish.published) {
    publishedPostLink.href = finalUrl;
    publishedPostLink.textContent = "Mở bài viết vừa đăng trên Facebook";
    publishedPostLink.hidden = false;
  } else {
    publishedPostLink.hidden = true;
    publishedPostLink.removeAttribute("href");
  }
  publishedPostLinkBox.hidden = false;
}

function renderPublishPages(pages) {
  publishPages = Array.isArray(pages) ? pages : [];
  if (!publishPages.length) {
    publishPageList.className = "publish-page-list empty-state";
    publishPageList.textContent = "Chưa cấu hình page publish.";
    publishSelectedButton.disabled = true;
    publishAllButton.disabled = true;
    selectAllPagesButton.disabled = true;
    return;
  }

  publishSelectedButton.disabled = false;
  publishAllButton.disabled = false;
  selectAllPagesButton.disabled = false;
  publishPageList.className = "publish-page-list";
  publishPageList.innerHTML = publishPages
    .map(
      (page, index) => `
        <label class="publish-page-option">
          <input type="checkbox" value="${escapeHtml(page.page_id)}" ${index === 0 ? "checked" : ""} />
          <span>
            <strong>${escapeHtml(displayPublishPageName(page, index))}</strong>
            <small>${page.has_token ? "Sẵn sàng đăng" : "Thiếu token"}</small>
          </span>
        </label>
      `,
    )
    .join("");
}

function displayPublishPageName(page, index) {
  const name = String(page?.name || "").trim();
  if (name && !/^Page\s+\d+$/i.test(name)) {
    return name;
  }
  return `Trang Facebook ${index + 1}${page?.page_id ? ` · ${String(page.page_id).slice(-6)}` : ""}`;
}

function getSelectedPublishPageIds() {
  return [...publishPageList.querySelectorAll('input[type="checkbox"]:checked')].map((input) => input.value);
}

function isCurrentResultApproved() {
  return currentResult?.approval_status === "approved" && currentResult?.cmo_decision === "APPROVE_TO_PUBLISH";
}

function shouldOverrideCmoBeforePublish() {
  if (isCurrentResultApproved()) {
    return false;
  }
  const decision = currentResult?.cmo_decision || "chưa có quyết định CMO";
  const approval = currentResult?.approval_status || "pending";
  const reviseFirst = window.confirm(
    `CMO hiện chưa approve bài này (${decision} · ${approval}).\n\n` +
      "Bạn có muốn sửa lại/chạy lại workflow trước khi đăng không?\n\n" +
      "OK: sửa lại và chạy lại workflow.\n" +
      "Cancel: bỏ qua cảnh báo CMO và tiếp tục đăng."
  );
  if (reviseFirst) {
    publishPageStatus.textContent = "Đã chọn sửa lại. Workflow sẽ chạy lại đến khi CMO approve.";
    runWorkflow("deep").catch((error) => {
      publishPageStatus.textContent = error.message;
    });
    return null;
  }
  return true;
}

async function publishFinalDraft(pageIds) {
  const selectedPageIds = pageIds || getSelectedPublishPageIds();
  if (!selectedPageIds.length) {
    publishPageStatus.textContent = "Hãy chọn ít nhất một page trước khi đăng.";
    return;
  }
  const overridePublish = shouldOverrideCmoBeforePublish();
  if (overridePublish === null) {
    return;
  }
  publishSelectedButton.disabled = true;
  publishAllButton.disabled = true;
  publishPageStatus.textContent = overridePublish
    ? `Đang bỏ qua CMO gate và gửi bài đến ${selectedPageIds.length} page...`
    : `Đang gửi bài đến ${selectedPageIds.length} page...`;
  try {
    const response = await fetch("/api/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...buildFinalDraftPayload(),
        page_ids: selectedPageIds,
        approved: isCurrentResultApproved(),
        approval_context_key: currentResult?.publish_approval_context_key || "",
        approval_token: currentResult?.publish_approval_token || "",
        override_publish: overridePublish,
      }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Không đăng được bài.");
    }
    const publish = payload.publish_result || {};
    publishStatus.textContent = publish.publisher_status || "-";
    publishMode.textContent = publish.publish_mode || "-";
    postId.textContent = publish.published_post_id || "-";
    safePayload.textContent = publish.safe_payload_preview || JSON.stringify(publish, null, 2);
    renderPublishedPostLink(publish);
    if (publish.published) {
      publishPageStatus.textContent = `${overridePublish ? "Đã bỏ qua CMO gate và " : ""}Đã đăng thành công ${Number((publish.page_results || []).filter((item) => item.published).length || 0)} page.`;
    } else if (publish.dry_run) {
      publishPageStatus.textContent = `Dry-run OK cho ${Number((publish.page_results || []).length || 0)} page. Tắt DRY_RUN trên server để đăng thật.`;
    } else {
      publishPageStatus.textContent = publish.reason || "Publisher chưa đăng. Kiểm tra CMO approval hoặc quyền page.";
    }
  } catch (error) {
    publishPageStatus.textContent = error.message;
  } finally {
    publishSelectedButton.disabled = !publishPages.length;
    publishAllButton.disabled = !publishPages.length;
  }
}

function setFinalDraft(draft, assets, preferredCreativeIndex = 0) {
  finalImageManuallyDisabled = false;
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
  renderFinalCreativeOptions(preferredCreativeIndex);
  updateFacebookPreview();
}

function renderFinalCreativeOptions(preferredCreativeIndex = 0) {
  finalCreativeSelect.innerHTML = "";
  const noImageOption = document.createElement("option");
  noImageOption.value = "-1";
  noImageOption.textContent = "Không dùng ảnh cho bài này";
  finalCreativeSelect.appendChild(noImageOption);

  if (!currentCreativeAssets.length) {
    const pendingImageOption = document.createElement("option");
    pendingImageOption.value = "image-pending";
    pendingImageOption.disabled = true;
    pendingImageOption.textContent = "Chưa có ảnh GPT Image trong lượt chạy này";
    finalCreativeSelect.appendChild(pendingImageOption);
    finalCreativeSelect.value = "-1";
    updateFinalImageControls();
    return;
  }

  currentCreativeAssets.forEach((asset, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    const isModelRewrite = asset.image_mode === "top_match_reference" || asset.openai_generated || asset.gemini_generated;
    const label = isModelRewrite ? "Có ảnh GPT Image" : "Ảnh SmileUp";
    option.textContent = `${label} · ${String(index + 1).padStart(2, "0")} · ${asset.service_line || asset.title || "SmileUp creative"}`;
    finalCreativeSelect.appendChild(option);
  });
  const safeIndex = Number(preferredCreativeIndex);
  finalCreativeSelect.value = finalImageManuallyDisabled
    ? "-1"
    : safeIndex >= 0 && safeIndex < currentCreativeAssets.length
      ? String(safeIndex)
      : "0";
  updateFinalImageControls();
}

function updateFacebookPreview() {
  const message = formatFinalFacebookMessage();
  fbPreviewText.textContent = message || "Chạy workflow để xem bản preview cuối.";
  finalCharCount.textContent = `${message.length.toLocaleString("vi-VN")} ký tự`;
  safePayload.textContent = message || "Payload preview sẽ hiện ở đây.";

  let selectedIndex = Number(finalCreativeSelect.value);
  if (!finalImageManuallyDisabled && (!Number.isInteger(selectedIndex) || selectedIndex < 0) && currentCreativeAssets[0]?.image_path) {
    selectedIndex = 0;
    finalCreativeSelect.value = "0";
  }
  const selectedAsset = Number.isInteger(selectedIndex) ? currentCreativeAssets[selectedIndex] : null;
  if (selectedAsset?.image_path) {
    const label = selectedAsset.openai_generated || selectedAsset.gemini_generated || selectedAsset.image_mode === "top_match_reference" ? "Ảnh GPT Image" : "Ảnh đính kèm";
    fbPreviewImage.className = "fb-preview-image has-image";
    fbPreviewImage.innerHTML = `
      <img src="${escapeHtml(selectedAsset.image_path)}" alt="${escapeHtml(selectedAsset.title || "SmileUp creative")}" />
      <span>${escapeHtml(label)}</span>
    `;
  } else {
    fbPreviewImage.className = "fb-preview-image empty";
    fbPreviewImage.textContent = currentCreativeAssets.length
      ? "Đã có ảnh, hãy chọn trong mục Ảnh đi kèm để xem trước."
      : "Chưa có ảnh GPT Image trong lượt chạy này.";
  }
  updateFinalImageControls();
}

function updateFinalImageControls() {
  const selectedIndex = Number(finalCreativeSelect.value);
  const selectedAsset = Number.isInteger(selectedIndex) ? currentCreativeAssets[selectedIndex] : null;
  const hasSelectedImage = Boolean(selectedAsset?.image_path);
  const firstImageAsset = currentCreativeAssets.find((asset) => asset?.image_path);
  const firstImageIsModelGenerated = firstImageAsset?.openai_generated || firstImageAsset?.gemini_generated || firstImageAsset?.image_mode === "top_match_reference";
  finalUseImageButton.disabled = !firstImageAsset;
  finalUseImageButton.textContent = firstImageIsModelGenerated ? "Dùng ảnh GPT Image" : "Dùng ảnh đang có";
  finalRemoveImageButton.disabled = !hasSelectedImage;
  finalNoImageButton.classList.toggle("active", selectedIndex === -1);
  finalUseImageButton.classList.toggle("active", hasSelectedImage);
  finalImageStatus.textContent = hasSelectedImage
    ? `${selectedAsset.openai_generated || selectedAsset.gemini_generated || selectedAsset.image_mode === "top_match_reference" ? "Đang chọn ảnh GPT Image" : "Đang chọn ảnh"}: ${selectedAsset.title || selectedAsset.service_line || "SmileUp creative"}`
    : currentCreativeAssets.length
      ? "Có ảnh trong lượt chạy này. Bấm “Dùng ảnh đang có” hoặc chọn ảnh trong dropdown để xem trước."
      : "Chưa có ảnh trong lượt chạy này. Hãy chạy workflow ở chế độ “Có ảnh GPT Image” hoặc bấm “Thêm / đổi ảnh”.";
}

function useFirstAvailableImage() {
  const index = currentCreativeAssets.findIndex((asset) => asset?.image_path);
  if (index < 0) {
    finalImageStatus.textContent = "Chưa có ảnh để dùng. Hãy chạy workflow ở chế độ có ảnh hoặc thêm ảnh thủ công.";
    return;
  }
  finalImageManuallyDisabled = false;
  finalCreativeSelect.value = String(index);
  updateFacebookPreview();
}

function openFinalImagePicker() {
  finalCreativeUpload.click();
}

function removeSelectedFinalImage() {
  const selectedIndex = Number(finalCreativeSelect.value);
  if (!Number.isInteger(selectedIndex) || selectedIndex < 0 || selectedIndex >= currentCreativeAssets.length) {
    finalCreativeSelect.value = "-1";
    updateFacebookPreview();
    return;
  }
  currentCreativeAssets.splice(selectedIndex, 1);
  renderFinalCreativeOptions(-1);
  updateFacebookPreview();
}

function addFinalCreativeFromFile(file) {
  if (!file) {
    return;
  }
  if (!file.type.startsWith("image/")) {
    finalImageStatus.textContent = "File không phải ảnh. Hãy chọn PNG, JPG hoặc WEBP.";
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    finalImageStatus.textContent = "Ảnh vượt quá 8 MB. Hãy chọn ảnh nhẹ hơn.";
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    const dataUrl = String(reader.result || "");
    currentCreativeAssets.push({
      service_line: "Ảnh thủ công",
      title: file.name,
      image_path: dataUrl,
      image_prompt: "Ảnh được thêm thủ công ở bước final review.",
      image_mode: "manual_final_upload",
      source_policy: "Chỉ dùng nếu ảnh thuộc SmileUp hoặc bạn có quyền sử dụng.",
    });
    renderFinalCreativeOptions(currentCreativeAssets.length - 1);
    updateFacebookPreview();
  };
  reader.readAsDataURL(file);
}

function formatFinalFacebookMessage() {
  const tags = normalizeHashtags(finalTagsInput.value).join(" ");
  return [finalTitleInput.value, finalBodyInput.value, finalCtaInput.value, tags]
    .map((part) => String(part || "").trim())
    .filter(Boolean)
    .join("\n\n");
}

function buildFinalDraftPayload() {
  return {
    title: finalTitleInput.value.trim(),
    body: finalBodyInput.value.trim(),
    call_to_action: finalCtaInput.value.trim(),
    hashtags: normalizeHashtags(finalTagsInput.value),
  };
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

runButton.addEventListener("click", () => runWorkflow("deep"));
deepRunButton.addEventListener("click", () => runWorkflow("quick"));
completionJumpButton?.addEventListener("click", () => {
  document.querySelector(".post-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  hideCompletionNotice();
});
completionCloseButton?.addEventListener("click", hideCompletionNotice);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && pendingCompletionNotice) {
    showCompletionNotice();
  }
});
window.addEventListener("focus", () => {
  if (pendingCompletionNotice) {
    showCompletionNotice();
  }
});
homeButton.addEventListener("click", () => {
  window.location.href = "/";
});
historyButton.addEventListener("click", () => {
  toggleHistoryPanel().catch((error) => {
    historyList.className = "history-list empty-state";
    historyList.textContent = error.message;
  });
});
historyCloseButton.addEventListener("click", closeHistoryPanel);
historyList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest(".delete-history-button");
  if (deleteButton) {
    deleteHistoryItem(deleteButton.dataset.historyId).catch((error) => {
      historyList.className = "history-list empty-state";
      historyList.textContent = error.message;
    });
    return;
  }

  const button = event.target.closest(".use-history-button");
  if (!button) {
    return;
  }
  openHistoryItem(button.dataset.historyId).catch((error) => {
    historyList.className = "history-list empty-state";
    historyList.textContent = error.message;
  });
});
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
    creativeImageInput.value = "";
  };
  reader.onerror = () => {
    uploadedCreativeImage = null;
    creativeImagePreview.className = "creative-image-preview empty";
    creativeImagePreview.textContent = "Không đọc được ảnh upload";
    creativeImageInput.value = "";
    syncCreativeImageMode();
  };
  reader.readAsDataURL(file);
});
creativeImageMode.addEventListener("change", syncCreativeImageMode);
finalTitleInput.addEventListener("input", updateFacebookPreview);
finalBodyInput.addEventListener("input", updateFacebookPreview);
finalCtaInput.addEventListener("input", updateFacebookPreview);
finalTagsInput.addEventListener("input", updateFacebookPreview);
finalCreativeSelect.addEventListener("change", () => {
  finalImageManuallyDisabled = finalCreativeSelect.value === "-1";
  updateFacebookPreview();
});
finalUseImageButton.addEventListener("click", useFirstAvailableImage);
finalNoImageButton.addEventListener("click", () => {
  finalImageManuallyDisabled = true;
  finalCreativeSelect.value = "-1";
  updateFacebookPreview();
});
finalRemoveImageButton.addEventListener("click", removeSelectedFinalImage);
finalAddImageButton.addEventListener("click", openFinalImagePicker);
finalAddImagePreviewButton.addEventListener("click", openFinalImagePicker);
finalCreativeUpload.addEventListener("change", () => {
  addFinalCreativeFromFile(finalCreativeUpload.files?.[0]);
  finalCreativeUpload.value = "";
});
resetFinalButton.addEventListener("click", () => {
  if (!originalFinalDraft) {
    return;
  }
  finalTitleInput.value = originalFinalDraft.title;
  finalBodyInput.value = originalFinalDraft.body;
  finalCtaInput.value = originalFinalDraft.call_to_action;
  finalTagsInput.value = originalFinalDraft.hashtags.join(" ");
  finalImageManuallyDisabled = false;
  renderFinalCreativeOptions(currentCreativeAssets.length ? 0 : -1);
  updateFacebookPreview();
});
copyFinalButton.addEventListener("click", copyFinalCaption);
selectAllPagesButton.addEventListener("click", () => {
  publishPageList.querySelectorAll('input[type="checkbox"]').forEach((input) => {
    input.checked = true;
  });
});
publishSelectedButton.addEventListener("click", () => publishFinalDraft());
publishAllButton.addEventListener("click", () => {
  publishPageList.querySelectorAll('input[type="checkbox"]').forEach((input) => {
    input.checked = true;
  });
  publishFinalDraft(publishPages.map((page) => page.page_id));
});
contentPlanList.addEventListener("click", (event) => {
  const button = event.target.closest(".use-variant-button");
  if (!button) {
    return;
  }
  useVariantAsFinal(Number(button.dataset.variantIndex));
});
cmoGraphToggle.addEventListener("click", () => {
  const isOpen = cmoGraphToggle.getAttribute("aria-expanded") === "true";
  cmoGraphToggle.setAttribute("aria-expanded", String(!isOpen));
  cmoGraphToggle.textContent = isOpen ? "Mở đồ thị quyết định của CMO" : "Ẩn đồ thị quyết định của CMO";
  cmoDecisionGraphWrap.classList.toggle("hidden-panel", isOpen);
});
setSourceMode("auto");
syncCreativeImageMode();
updateFacebookPreview();
loadStatus().catch(() => {
  modeValue.textContent = "Unknown";
  dryRunValue.textContent = "-";
  connectionState.textContent = "Offline";
});
