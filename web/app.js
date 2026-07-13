const AGENT_ORDER = [
  "crawler",
  "text_insight",
  "trend_analysis",
  "visual_insight",
  "video_insight",
  "strategy",
  "compliance",
  "hardness",
  "manager_review",
];

const AGENT_LABELS = {
  crawler: "Crawler",
  text_insight: "Text Insight",
  trend_analysis: "Trend",
  visual_insight: "Visual",
  video_insight: "Video",
  strategy: "Strategy",
  compliance: "Compliance",
  hardness: "Hardness",
  manager_review: "CMO Dispatch",
};

const elements = Object.fromEntries(
  [
    "serviceStatus",
    "modelStatus",
    "logoutButton",
    "keywordInput",
    "runButton",
    "runMessage",
    "historyList",
    "processingScreen",
    "processingTitle",
    "elapsedTime",
    "agentProgress",
    "operationsCanvas",
    "officePhaseLabel",
    "officeCompletedCount",
    "cmoFeedback",
    "cmoDecision",
    "hardnessScore",
    "teamCount",
    "planWindow",
    "marketCoverage",
    "competitorCampaigns",
    "revenueStrategy",
    "workflowStatus",
    "productionBrief",
    "productionHandoff",
    "taskStatusText",
    "brandPlatform",
    "campaignWeeks",
    "successMetrics",
    "riskList",
    "adsSummary",
    "strategyReport",
    "textReport",
    "trendReport",
    "visualReport",
    "videoReport",
    "complianceReport",
    "hardnessReport",
    "adsTableBody",
    "warningList",
    "logOutput",
  ].map((id) => [id, document.getElementById(id)]),
);

let currentJobId = "";
let jobStartedAt = 0;
let officeAnimationFrame = 0;
let officeAnimationRunning = false;
let officeStatuses = {};
let officeCurrentStep = "";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatList(items, emptyText = "Chưa có dữ liệu.") {
  const values = Array.isArray(items) ? items.filter(Boolean) : [];
  return values.length ? values.map((item) => `<li>${escapeHtml(item)}</li>`).join("") : `<li>${escapeHtml(emptyText)}</li>`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Phiên đăng nhập đã hết hạn.");
  }
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

async function loadStatus() {
  const status = await fetchJson("/api/status");
  elements.serviceStatus.textContent = "Hệ thống sẵn sàng";
  elements.serviceStatus.className = "status-pill ready";
  elements.modelStatus.textContent = `${status.ai_provider || "Local"} · ${status.ai_model || "template"} · tối đa ${status.scan_ads || 100} ads`;
  if (!elements.keywordInput.value.trim()) {
    elements.keywordInput.value = status.ad_library_keywords || "";
  }
  renderWarnings(status.warnings || []);
}

function renderWarnings(warnings) {
  if (!warnings.length) {
    elements.warningList.className = "warning-list empty-state";
    elements.warningList.textContent = "Không có warning cấu hình.";
    return;
  }
  elements.warningList.className = "warning-list";
  elements.warningList.innerHTML = warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("");
}

function setRunning(running) {
  elements.runButton.disabled = running;
  elements.keywordInput.disabled = running;
  elements.runButton.textContent = running ? "CMO đang xử lý..." : "Chạy CMO và giao việc";
  elements.processingScreen.classList.toggle("hidden", !running);
  if (running) {
    startOperationsFloor();
  } else {
    stopOperationsFloor();
  }
}

function renderAgentProgress(statuses = {}, currentStep = "") {
  officeStatuses = { ...statuses };
  officeCurrentStep = currentStep;
  elements.agentProgress.innerHTML = AGENT_ORDER.map((agent, index) => {
    const status = statuses[agent] || (agent === currentStep ? "running" : "idle");
    const label = status === "done" ? "Xong" : status === "running" ? "Đang làm" : "Chờ";
    return `
      <div class="agent-step ${escapeHtml(status)}">
        <span class="step-index">${String(index + 1).padStart(2, "0")}</span>
        <div><strong>${escapeHtml(AGENT_LABELS[agent])}</strong><small>${label}</small></div>
      </div>`;
  }).join("");
  const activeLabel = AGENT_LABELS[currentStep] || "CMO";
  elements.processingTitle.textContent = `${activeLabel} đang xử lý`;
  elements.officePhaseLabel.textContent = `${activeLabel} đang làm việc`;
  elements.officeCompletedCount.textContent = `${AGENT_ORDER.filter((agent) => statuses[agent] === "done").length}/9 hoàn tất`;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) drawOperationsFloor(window.performance.now());
}

function startOperationsFloor() {
  if (officeAnimationRunning) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    drawOperationsFloor(window.performance.now());
    return;
  }
  officeAnimationRunning = true;
  const draw = (timestamp) => {
    drawOperationsFloor(timestamp);
    if (officeAnimationRunning) officeAnimationFrame = window.requestAnimationFrame(draw);
  };
  officeAnimationFrame = window.requestAnimationFrame(draw);
}

function stopOperationsFloor() {
  officeAnimationRunning = false;
  window.cancelAnimationFrame(officeAnimationFrame);
}

function drawOperationsFloor(timestamp = 0) {
  const canvas = elements.operationsCanvas;
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  if (rect.width < 20 || rect.height < 20) return;
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  const targetWidth = Math.round(rect.width * pixelRatio);
  const targetHeight = Math.round(rect.height * pixelRatio);
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
  }
  const context = canvas.getContext("2d");
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  renderOfficeScene(context, rect.width, rect.height, timestamp);
}

function renderOfficeScene(context, width, height, timestamp) {
  const compact = width < 620;
  const positions = compact
    ? [
        [0.25, 0.18], [0.75, 0.18], [0.75, 0.36], [0.25, 0.36], [0.25, 0.54],
        [0.75, 0.54], [0.75, 0.72], [0.25, 0.72], [0.5, 0.9],
      ]
    : [
        [0.12, 0.27], [0.31, 0.27], [0.5, 0.27], [0.69, 0.27], [0.88, 0.27],
        [0.88, 0.72], [0.69, 0.72], [0.5, 0.72], [0.25, 0.72],
      ];
  const points = positions.map(([x, y]) => ({ x: width * x, y: height * y }));
  const activeIndex = Math.max(0, AGENT_ORDER.indexOf(officeCurrentStep));
  const unit = Math.min(width / (compact ? 4.2 : 8.2), height / (compact ? 8 : 4.4));

  context.clearRect(0, 0, width, height);
  context.fillStyle = "#e9efec";
  context.fillRect(0, 0, width, height);
  drawFloorGrid(context, width, height, compact ? 28 : 34);
  drawOfficeFixtures(context, width, height, compact);
  drawWorkflowPath(context, points, activeIndex, timestamp);

  AGENT_ORDER.forEach((agent, index) => {
    const status = officeStatuses[agent] || (agent === officeCurrentStep ? "running" : "idle");
    drawWorkstation(context, points[index], unit, AGENT_LABELS[agent], index, status, timestamp);
  });
}

function drawFloorGrid(context, width, height, gridSize) {
  context.save();
  context.strokeStyle = "rgba(88, 111, 104, 0.08)";
  context.lineWidth = 1;
  for (let x = 0; x <= width; x += gridSize) {
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, height);
    context.stroke();
  }
  for (let y = 0; y <= height; y += gridSize) {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  }
  context.restore();
}

function drawOfficeFixtures(context, width, height, compact) {
  context.save();
  context.fillStyle = "#d7e0dc";
  context.fillRect(0, 0, width, 8);
  context.fillRect(0, height - 8, width, 8);
  context.fillStyle = "#c7d5d0";
  const fixtureWidth = compact ? 34 : 48;
  context.fillRect(10, height * 0.44, fixtureWidth, height * 0.12);
  context.fillRect(width - fixtureWidth - 10, height * 0.44, fixtureWidth, height * 0.12);
  context.fillStyle = "#6f8f84";
  context.fillRect(18, height * 0.46, fixtureWidth - 16, 6);
  context.fillRect(width - fixtureWidth - 2, height * 0.46, fixtureWidth - 16, 6);
  context.restore();
}

function drawWorkflowPath(context, points, activeIndex, timestamp) {
  context.save();
  context.lineCap = "round";
  context.lineJoin = "round";
  context.lineWidth = 4;
  context.strokeStyle = "rgba(91, 116, 108, 0.2)";
  context.beginPath();
  points.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y));
  context.stroke();

  if (activeIndex > 0) {
    context.strokeStyle = "#4e9b8f";
    context.beginPath();
    points.slice(0, activeIndex + 1).forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y));
    context.stroke();
  }
  const point = points[activeIndex] || points[0];
  const pulse = 5 + Math.sin(timestamp / 240) * 2;
  context.fillStyle = "rgba(15, 118, 110, 0.2)";
  context.beginPath();
  context.arc(point.x, point.y, 14 + pulse, 0, Math.PI * 2);
  context.fill();
  context.restore();
}

function drawWorkstation(context, point, unit, label, index, status, timestamp) {
  const deskWidth = unit * 1.5;
  const deskHeight = unit * 0.52;
  const running = status === "running";
  const done = status === "done";
  const bob = running ? Math.sin(timestamp / 160 + index) * 2 : 0;
  const screenColor = done ? "#4f8f69" : running ? "#0f766e" : "#263431";

  context.save();
  context.translate(point.x, point.y);
  context.fillStyle = "rgba(38, 52, 49, 0.13)";
  roundedRect(context, -deskWidth / 2 + 4, -deskHeight / 2 + 7, deskWidth, deskHeight, 5);
  context.fill();
  context.fillStyle = "#c4b9a5";
  roundedRect(context, -deskWidth / 2, -deskHeight / 2, deskWidth, deskHeight, 5);
  context.fill();
  context.fillStyle = "#8b7f6e";
  context.fillRect(-deskWidth / 2 + 6, deskHeight / 2 - 3, deskWidth - 12, 4);

  context.fillStyle = "#17201e";
  roundedRect(context, -unit * 0.3, -unit * 0.38, unit * 0.6, unit * 0.34, 3);
  context.fill();
  context.fillStyle = screenColor;
  roundedRect(context, -unit * 0.25, -unit * 0.33, unit * 0.5, unit * 0.23, 2);
  context.fill();
  if (running) {
    context.fillStyle = "rgba(255,255,255,0.72)";
    context.fillRect(-unit * 0.19, -unit * 0.27, unit * (0.14 + ((timestamp / 700) % 0.22)), 2);
  }

  context.fillStyle = done ? "#cfe7d8" : running ? "#bde4de" : "#cfd8d5";
  context.beginPath();
  context.arc(0, unit * 0.28 + bob, unit * 0.13, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = done ? "#397052" : running ? "#0f766e" : "#66746f";
  roundedRect(context, -unit * 0.2, unit * 0.38 + bob, unit * 0.4, unit * 0.28, 5);
  context.fill();
  context.strokeStyle = running ? "#0f766e" : "#66746f";
  context.lineWidth = 3;
  context.beginPath();
  context.moveTo(-unit * 0.12, unit * 0.45 + bob);
  context.lineTo(-unit * 0.3, unit * 0.08 + bob);
  context.moveTo(unit * 0.12, unit * 0.45 + bob);
  context.lineTo(unit * 0.3, unit * 0.08 + bob);
  context.stroke();

  context.fillStyle = "#ffffff";
  context.strokeStyle = done ? "#9fc7ad" : running ? "#73b9af" : "#c7d1ce";
  context.lineWidth = 1;
  roundedRect(context, -deskWidth * 0.48, -deskHeight * 0.93, deskWidth * 0.96, unit * 0.24, 4);
  context.fill();
  context.stroke();
  context.fillStyle = running ? "#0f5f58" : "#33413e";
  context.font = `700 ${Math.max(8, unit * 0.13)}px Inter, sans-serif`;
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(`${String(index + 1).padStart(2, "0")}  ${label}`, 0, -deskHeight * 0.93 + unit * 0.12, deskWidth * 0.88);
  context.restore();
}

function roundedRect(context, x, y, width, height, radius) {
  const safeRadius = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(x + safeRadius, y);
  context.lineTo(x + width - safeRadius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + safeRadius);
  context.lineTo(x + width, y + height - safeRadius);
  context.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height);
  context.lineTo(x + safeRadius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
  context.lineTo(x, y + safeRadius);
  context.quadraticCurveTo(x, y, x + safeRadius, y);
  context.closePath();
}

async function runWorkflow() {
  const keyword = elements.keywordInput.value.replace(/\s+/g, " ").trim();
  if (!keyword) {
    elements.runMessage.textContent = "Vui lòng nhập keyword cần quét.";
    elements.keywordInput.focus();
    return;
  }
  elements.keywordInput.value = keyword;
  setRunning(true);
  jobStartedAt = Date.now();
  elements.runMessage.textContent = `Đang bao phủ thị trường theo "${keyword}" với tối đa 100 ads.`;
  elements.logOutput.textContent = "Workflow queued.";
  renderAgentProgress({}, "crawler");
  if (window.matchMedia("(max-width: 860px)").matches) {
    window.setTimeout(() => elements.processingScreen.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
  }
  try {
    const payload = await fetchJson("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "market", ad_library_max_ads: 100, ad_library_keywords: keyword }),
    });
    currentJobId = payload.job_id;
    await pollJob(currentJobId);
  } catch (error) {
    setRunning(false);
    elements.runMessage.textContent = error.message;
    elements.logOutput.textContent = error.message;
  }
}

async function pollJob(jobId) {
  while (currentJobId === jobId) {
    const payload = await fetchJson(`/api/job?id=${encodeURIComponent(jobId)}`);
    const elapsed = Math.max(0, Math.round((Date.now() - jobStartedAt) / 1000));
    elements.elapsedTime.textContent = `${elapsed}s`;
    elements.logOutput.textContent = payload.logs || `Job ${payload.status}`;
    renderAgentProgress(payload.agent_statuses || {}, payload.current_step || "");

    if (payload.status === "completed") {
      renderResult(payload.result || {}, payload.logs || "");
      setRunning(false);
      elements.runMessage.textContent = "CMO đã hoàn thành chiến dịch 1 tháng.";
      currentJobId = "";
      await loadHistory();
      return;
    }
    if (payload.status === "error") {
      throw new Error(payload.error || "Workflow thất bại.");
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1800));
  }
}

function renderResult(result, logs = "") {
  const workflow = result.media_production_workflow || {};
  const keyword = String(result.ad_library_keywords || workflow.focus_keyword || elements.keywordInput.value).trim();
  const teamRoles = Array.isArray(workflow.team_roles) ? workflow.team_roles : [];
  const weeks = Array.isArray(workflow.weeks) ? workflow.weeks : [];
  const plannedVideos = weeks.reduce(
    (total, week) => total + (Array.isArray(week.content_outputs) ? week.content_outputs.length : 0),
    0,
  );

  elements.cmoDecision.textContent = formatDecision(result.cmo_decision);
  elements.cmoFeedback.textContent = result.cmo_feedback || "CMO chưa có kết luận.";
  elements.hardnessScore.textContent = `${Number(result.hardness_score || 0)}/100`;
  elements.teamCount.textContent = teamRoles.length ? `${teamRoles.length} vai trò` : "Chưa có";
  elements.planWindow.textContent = workflow.planning_horizon || "1 tháng";
  elements.workflowStatus.textContent = workflow.status || "pending";
  elements.workflowStatus.className = `status-pill ${workflow.status === "ready_for_dispatch" ? "ready" : "warning"}`;
  elements.productionBrief.textContent = result.media_production_brief || "Chưa có production brief.";
  elements.productionHandoff.textContent = result.production_handoff || "Chưa có handoff.";
  elements.taskStatusText.textContent = `${weeks.length} tuần · ${plannedVideos} video`;

  renderMarketIntelligence(workflow.market_intelligence || {});
  renderRevenueStrategy(workflow.revenue_strategy || {});
  renderBrandPlatform(workflow.brand_platform || {});
  renderCampaignWeeks(weeks);
  elements.successMetrics.innerHTML = formatList(workflow.metrics);
  elements.riskList.innerHTML = formatList(workflow.risks, "Không có rủi ro lớn được ghi nhận.");
  renderReports(result);
  if (keyword) elements.keywordInput.value = keyword;
  renderAds(result.ad_library_ads || [], keyword);
  elements.logOutput.textContent = logs || result.daily_report || "Workflow completed.";
}

function renderMarketIntelligence(market) {
  const coverage = market.coverage || {};
  const campaigns = Array.isArray(market.campaigns) ? market.campaigns : [];
  if (!campaigns.length) {
    elements.marketCoverage.className = "market-coverage empty-state";
    elements.marketCoverage.textContent = "Chưa đủ campaign để đo độ phủ.";
    elements.competitorCampaigns.className = "competitor-campaigns empty-state";
    elements.competitorCampaigns.textContent = "Campaign đối thủ sẽ hiện ở đây.";
    return;
  }
  elements.marketCoverage.className = "market-coverage";
  elements.marketCoverage.innerHTML = `
    <div><span>Ads quan sát</span><strong>${Number(coverage.ads_observed || 0)}/${Number(coverage.scan_target || 0)}</strong></div>
    <div><span>Nha khoa</span><strong>${Number(coverage.unique_pages || 0)}</strong></div>
    <div><span>Campaign</span><strong>${Number(coverage.campaigns_detected || 0)}</strong></div>
    <div><span>Độ phủ</span><strong>${escapeHtml(coverage.coverage_level || "low")} · ${Number(coverage.coverage_score || 0)}/100</strong></div>
    <p>Đối thủ cấu hình đã xác minh: ${Number(coverage.configured_pages_observed || 0)}/${Number(coverage.configured_competitor_pages || 0)} page. ${escapeHtml(coverage.limitation || "")}</p>`;
  elements.competitorCampaigns.className = "competitor-campaigns";
  elements.competitorCampaigns.innerHTML = campaigns.slice(0, 12).map((campaign) => `
    <article class="competitor-campaign">
      <div><strong>${escapeHtml(campaign.page_name)}</strong><span>${Number(campaign.ad_count || 0)} ads</span></div>
      <h3>${escapeHtml(campaign.service_line)} · ${escapeHtml(campaign.angle)}</h3>
      <p>${escapeHtml(campaign.funnel_stage)} · áp lực ${Number(campaign.market_pressure_score || 0)}/100</p>
      <dl>
        <div><dt>Mạnh</dt><dd>${escapeHtml((campaign.strengths || []).join("; "))}</dd></div>
        <div><dt>Yếu</dt><dd>${escapeHtml((campaign.weaknesses || []).join("; "))}</dd></div>
      </dl>
    </article>`).join("");
}

function renderRevenueStrategy(strategy) {
  const funnel = Array.isArray(strategy.funnel) ? strategy.funnel : [];
  if (!strategy.primary_conversion) {
    elements.revenueStrategy.className = "revenue-strategy empty-state";
    elements.revenueStrategy.textContent = "Revenue strategy sẽ hiện ở đây.";
    return;
  }
  const opportunity = strategy.selected_opportunity || {};
  const unitEconomics = strategy.unit_economics || {};
  const economicsReady = strategy.economics_status === "ready";
  elements.revenueStrategy.className = "revenue-strategy";
  elements.revenueStrategy.innerHTML = `
    <div class="revenue-headline">
      <div><span>Khoảng trống được chọn</span><h3>${escapeHtml(opportunity.name || "Chưa chọn - cần quét thêm")}</h3></div>
      <strong class="economics-status ${economicsReady ? "ready" : "warning"}">${economicsReady ? "Economics ready" : "Thiếu unit economics"}</strong>
    </div>
    <p>${escapeHtml(opportunity.strategic_gap || strategy.objective || "")}</p>
    <p class="opportunity-reason">${escapeHtml(opportunity.selection_reason || "")}</p>
    ${economicsReady ? `<div class="unit-economics">
      <div><span>Lợi nhuận gộp/ca</span><strong>${Number(unitEconomics.gross_profit_per_case || 0).toLocaleString("vi-VN")} đ</strong></div>
      <div><span>Trần CAC/ca</span><strong>${Number(unitEconomics.max_cost_per_acquired_case || 0).toLocaleString("vi-VN")} đ</strong></div>
      <div><span>Trần CPL đủ điều kiện</span><strong>${Number(unitEconomics.max_cost_per_qualified_lead || 0).toLocaleString("vi-VN")} đ</strong></div>
    </div>` : `<p class="economics-missing">Cần dữ liệu thật: ${escapeHtml((strategy.required_business_inputs || []).join(", "))}</p>`}
    <div class="revenue-funnel">${funnel.map((stage, index) => `
      <div><span>${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(stage.stage)}</strong><small>${escapeHtml(stage.metric)}</small></div>`).join("")}</div>
    <div class="revenue-rules">
      <div><span>Chuyển đổi chính</span><strong>${escapeHtml(strategy.primary_conversion)}</strong></div>
      <div><span>Quy tắc scale</span><ul>${formatList(strategy.scale_rules)}</ul></div>
      <div><span>Quy tắc dừng</span><ul>${formatList(strategy.stop_rules)}</ul></div>
    </div>
    <p class="revenue-caveat">${escapeHtml(strategy.revenue_caveat || "")}</p>`;
}

function formatDecision(decision) {
  if (decision === "READY_FOR_PRODUCTION") return "READY";
  if (decision === "NEEDS_MORE_RESEARCH") return "RESEARCH";
  return decision || "PENDING";
}

function renderBrandPlatform(brand) {
  if (!brand.brand_idea) {
    elements.brandPlatform.className = "brand-platform empty-state";
    elements.brandPlatform.textContent = "Brand lane sẽ hiện ở đây.";
    return;
  }
  elements.brandPlatform.className = "brand-platform";
  elements.brandPlatform.innerHTML = `
    <div class="brand-core">
      <div class="brand-mark-row">
        <img src="/assets/smileup-logo.jfif" alt="SmileUp" />
        <div><span>Brand idea</span><h3>${escapeHtml(brand.brand_idea)}</h3></div>
      </div>
      <p><strong>Định vị:</strong> ${escapeHtml(brand.positioning)}</p>
      <p><strong>Lời hứa:</strong> ${escapeHtml(brand.promise)}</p>
      <div class="brand-swatches" aria-label="Màu nhận diện SmileUp">
        <i class="swatch-cyan" title="SmileUp cyan"></i><i class="swatch-blue" title="SmileUp blue"></i><i class="swatch-white" title="Clinical white"></i>
      </div>
    </div>
    <div class="brand-rules">
      <div><span>Giọng nói</span><ul>${formatList(brand.voice)}</ul></div>
      <div><span>Hệ hình ảnh</span><ul>${formatList(brand.visual_system)}</ul></div>
      <div><span>Series nhận diện</span><ul>${formatList(brand.signature_series)}</ul></div>
      <div><span>Không sử dụng</span><ul>${formatList(brand.guardrails)}</ul></div>
    </div>`;
}

function renderCampaignWeeks(weeks) {
  if (!weeks.length) {
    elements.campaignWeeks.className = "campaign-weeks empty-state";
    elements.campaignWeeks.textContent = "Chưa có kế hoạch tháng.";
    return;
  }
  elements.campaignWeeks.className = "campaign-weeks";
  elements.campaignWeeks.innerHTML = weeks.map((week) => `
    <section class="campaign-week">
      <div class="week-heading">
        <div class="week-number">${escapeHtml(week.label)}</div>
        <div><h3>${escapeHtml(week.theme)}</h3><p>${escapeHtml(week.objective)}</p></div>
      </div>
      <p class="week-evidence"><strong>Tín hiệu Meta:</strong> ${escapeHtml(week.evidence_link)}</p>
      <p class="week-evidence"><strong>Evidence ads:</strong> ${escapeHtml((week.evidence_refs || []).join(", ") || "Chưa đủ")}</p>
      <p class="week-evidence"><strong>Góc chiến lược:</strong> ${escapeHtml(week.strategic_angle || "")}</p>
      <div class="week-outputs"><span>3 nội dung</span><ol>${formatList(week.content_outputs)}</ol></div>
      <div class="assignment-grid">
        ${(week.assignments || []).map((task) => `
          <article class="assignment-item">
            <div><span>${escapeHtml(task.owner_role)}</span><small>${escapeHtml(task.estimated_duration || "")}</small></div>
            <h4>${escapeHtml(task.title)}</h4>
            <p>${escapeHtml(task.objective)}</p>
            <ul>${formatList(task.deliverables)}</ul>
            <details><summary>Tiêu chí nghiệm thu</summary><ul>${formatList(task.acceptance_criteria)}</ul></details>
          </article>`).join("")}
      </div>
      <p class="week-review">${escapeHtml(week.review_focus)}</p>
    </section>`).join("");
}

function renderReports(result) {
  elements.strategyReport.textContent = result.monthly_strategy || result.strategic_direction || result.weekly_strategy || "Chưa có dữ liệu.";
  elements.textReport.textContent = result.text_insight_report || "Chưa có dữ liệu.";
  elements.trendReport.textContent = result.facebook_trend_analysis || "Chưa có dữ liệu.";
  elements.visualReport.textContent = result.visual_insight_report || result.visual_direction || "Chưa có dữ liệu.";
  elements.videoReport.textContent = result.video_insight_report || "Chưa có dữ liệu.";
  elements.complianceReport.textContent = result.compliance_report || "Chưa có dữ liệu.";
  elements.hardnessReport.textContent = result.hardness_report || "Chưa có dữ liệu.";
}

function renderAds(ads, keyword = "") {
  elements.adsSummary.textContent = keyword ? `${ads.length} ads · ${keyword}` : `${ads.length} ads`;
  if (!ads.length) {
    elements.adsTableBody.innerHTML = '<tr><td colspan="5" class="empty-cell">Chưa có ads.</td></tr>';
    return;
  }
  elements.adsTableBody.innerHTML = ads.slice(0, 100).map((ad, index) => `
    <tr>
      <td>${index + 1}</td>
      <td>${escapeHtml(ad.page_name || "-")}</td>
      <td>${escapeHtml(ad.source_type === "competitor_page" ? "Đối thủ" : "Keyword")}</td>
      <td>${Math.round(Number(ad.similarity || 0) * 100)}%</td>
      <td>${escapeHtml(String(ad.ad_text || "").slice(0, 180))}</td>
    </tr>`).join("");
}

async function loadHistory() {
  try {
    const payload = await fetchJson("/api/history");
    renderHistory(payload.items || []);
  } catch (error) {
    elements.historyList.className = "history-list empty-state";
    elements.historyList.textContent = error.message;
  }
}

function renderHistory(items) {
  if (!items.length) {
    elements.historyList.className = "history-list empty-state";
    elements.historyList.textContent = "Chưa có workflow.";
    return;
  }
  elements.historyList.className = "history-list";
  elements.historyList.innerHTML = items.map((item) => `
    <article class="history-item">
      <button class="history-open" type="button" data-history-id="${escapeHtml(item.history_id)}">
        <strong>${escapeHtml(item.title || "Media workflow")}</strong>
        <span>${escapeHtml(item.created_at || "")} · ${Number(item.ads_count || 0)} ads</span>
        <span>${escapeHtml(item.scan_id || "Chưa có Scan ID")}</span>
        <small>${escapeHtml(item.keyword || "")} · ${escapeHtml(item.workflow_status || item.cmo_decision || "pending")} · ${Number(item.tasks_count || 0)} đầu việc</small>
      </button>
      <button class="history-delete" type="button" data-delete-history-id="${escapeHtml(item.history_id)}" aria-label="Xóa workflow">Xóa</button>
    </article>`).join("");
}

async function openHistory(historyId) {
  const payload = await fetchJson(`/api/history?id=${encodeURIComponent(historyId)}`);
  renderResult(payload.result || {}, payload.logs || "Loaded from history.");
  elements.runMessage.textContent = "Đã mở workflow từ lịch sử.";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function deleteHistory(historyId) {
  await fetchJson(`/api/history?id=${encodeURIComponent(historyId)}`, { method: "DELETE" });
  await loadHistory();
}

elements.runButton.addEventListener("click", runWorkflow);
elements.keywordInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    runWorkflow();
  }
});
elements.logoutButton.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/login";
});
elements.historyList.addEventListener("click", (event) => {
  const openButton = event.target.closest("[data-history-id]");
  const deleteButton = event.target.closest("[data-delete-history-id]");
  if (openButton) {
    openHistory(openButton.dataset.historyId).catch((error) => {
      elements.runMessage.textContent = error.message;
    });
  }
  if (deleteButton) {
    deleteHistory(deleteButton.dataset.deleteHistoryId).catch((error) => {
      elements.runMessage.textContent = error.message;
    });
  }
});

renderAgentProgress();
Promise.all([loadStatus(), loadHistory()]).catch((error) => {
  elements.serviceStatus.textContent = "Mất kết nối";
  elements.serviceStatus.className = "status-pill warning";
  elements.runMessage.textContent = error.message;
});
