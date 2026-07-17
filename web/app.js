let currentJobId = null;
let pollTimer = null;
let latestPayload = null;
let latestP0 = null;
let latestFigureImages = null;
let selectedPaper = "";

const statusEl = document.getElementById("jobStatus");
const messageEl = document.getElementById("jobMessage");
const downloadBtn = document.getElementById("downloadBtn");
const exportCsvBtn = document.getElementById("exportCsvBtn");
const exportPdfBtn = document.getElementById("exportPdfBtn");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");
const paperSearch = document.getElementById("paperSearch");

fileInput.addEventListener("change", renderSelectedFiles);
paperSearch.addEventListener("input", () => renderPaperSelector(getSourceFiles()));

document.getElementById("uploadBtn").addEventListener("click", async () => {
  if (!fileInput.files.length) return setStatus("failed", "请选择 1-5 个 PDF/TXT 文件。");
  if (fileInput.files.length > 5) return setStatus("failed", "最多上传 5 个文件。");
  startRun();
  const form = new FormData();
  [...fileInput.files].forEach((file) => form.append("files", file));
  const response = await fetch("/api/upload-run", { method: "POST", body: form });
  const data = await response.json();
  if (!response.ok) return setStatus("failed", data.detail || "上传失败。");
  watchJob(data.job_id);
});

downloadBtn.addEventListener("click", () => { if (currentJobId) window.location.href = `/api/jobs/${currentJobId}/download`; });
exportCsvBtn.addEventListener("click", () => { if (currentJobId) window.location.href = `/api/jobs/${currentJobId}/export/evidence-summary.csv`; });
exportPdfBtn.addEventListener("click", () => { if (currentJobId) window.location.href = `/api/jobs/${currentJobId}/export/figure-summary.pdf`; });
document.getElementById("modalClose").addEventListener("click", closeImageModal);
document.getElementById("imageModal").addEventListener("click", (event) => { if (event.target.id === "imageModal") closeImageModal(); });

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".tabPanel").forEach((panel) => panel.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
  });
});

function renderSelectedFiles() {
  fileList.innerHTML = "";
  [...fileInput.files].forEach((file, index) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = `fileItem ${index === 0 ? "selected" : ""}`;
    row.dataset.sourceName = file.name;
    row.innerHTML = `<span>${escapeHtml(file.name)}</span><strong>${formatBytes(file.size)}</strong>`;
    row.addEventListener("click", () => selectPaperByName(file.name));
    fileList.appendChild(row);
  });
}

function startRun() {
  latestPayload = null;
  latestP0 = null;
  latestFigureImages = null;
  selectedPaper = "";
  downloadBtn.disabled = true;
  exportCsvBtn.disabled = true;
  exportPdfBtn.disabled = true;
  renderEmpty();
  setStatus("queued", "任务已提交，等待后端执行。");
}

function watchJob(jobId) {
  currentJobId = jobId;
  if (pollTimer) clearInterval(pollTimer);
  pollJob();
  pollTimer = setInterval(pollJob, 1200);
}

async function pollJob() {
  const response = await fetch(`/api/jobs/${currentJobId}`);
  const job = await response.json();
  setStatus(job.status, job.message || "");
  if (job.result) {
    await renderPayload(job);
    downloadBtn.disabled = false;
    exportCsvBtn.disabled = false;
    exportPdfBtn.disabled = false;
  }
  if (job.status === "completed" || job.status === "failed") clearInterval(pollTimer);
}

async function renderPayload(job) {
  latestPayload = job.result;
  const arm = latestPayload.full_arm;
  const trace = latestPayload.trace_record;
  latestP0 = p0PanelsFromArm(arm);
  if (!selectedPaper) selectedPaper = (job.summary?.source_file_names || [])[0] || "";
  renderPaperSelector(job.summary?.source_file_names || []);
  renderSummary(job.summary || {});
  renderGate(job.summary?.review_gate || {}, job.summary?.module_status || {});
  renderClaims(arm.claims || []);
  renderDryRun(latestP0);
  renderReferences(arm.provenance?.reference_validation || {});
  renderTrace(trace, arm.provenance?.fine_trace || {});
  document.getElementById("rawJson").textContent = JSON.stringify(latestPayload, null, 2);
  updateBadges(job.summary || {}, arm, trace);
  updateReviewBanner(job.summary || {}, arm, trace);
  await loadFigureImages();
}

function p0PanelsFromArm(arm) {
  const provenance = arm.provenance || {};
  const figures = [];
  (provenance.figure_extraction || []).forEach((entry) => figures.push(...(entry.figures || [])));
  return {
    figure_evidence: figures,
    conflicts: provenance.conflict_detection?.conflict_pairs || [],
    dry_run: provenance.dry_run_result || {},
    evaluation: provenance.evaluation_result || {},
    p0_trace_summary: provenance.p0_trace_summary || {},
  };
}

async function loadFigureImages() {
  if (!currentJobId) return renderFigures(latestP0 || {}, null);
  try {
    const response = await fetch(`/api/jobs/${currentJobId}/figure-images`);
    latestFigureImages = await response.json();
  } catch (error) {
    latestFigureImages = { status: "figure_images_failed", risks: [{ message: String(error) }], figures_with_images: [] };
  }
  renderFigures(latestP0 || {}, latestFigureImages);
}

function renderSummary(summary) {
  const grid = document.getElementById("summaryGrid");
  grid.innerHTML = "";
  [
    ["处理状态", summary.processing_status], ["ARM ID", summary.arm_id], ["论文标题", summary.title], ["ECS 相关", yesNo(summary.ecs_related)],
    ["Claims", summary.claims], ["Evidence", summary.evidence], ["图表 caption", summary.figure_caption_count], ["冲突告警", summary.conflict_count],
    ["Dry-run", summary.dry_run_status], ["评估分", summary.evaluation_score],
  ].forEach(([label, value]) => grid.appendChild(metric(label, value ?? "-")));
  const risks = document.getElementById("risks");
  risks.innerHTML = "";
  const riskItems = summary.failure_risks || [];
  if (!riskItems.length) risks.appendChild(item("无阻断风险", "当前流程未记录 failure_risks。"));
  riskItems.forEach((risk) => risks.appendChild(item(risk.code, risk.message, JSON.stringify(risk.detail || {}))));
}

function renderPaperSelector(sourceFiles) {
  const sources = document.getElementById("sources");
  if (!sources) return;
  const filter = paperSearch.value.trim().toLowerCase();
  const filtered = (sourceFiles || []).filter((source) => !filter || basename(source).toLowerCase().includes(filter));
  sources.innerHTML = "";
  filtered.forEach((source, index) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = `fileItem sourceSelect ${source === selectedPaper || (!selectedPaper && index === 0) ? "selected" : ""}`;
    row.innerHTML = `<span>${escapeHtml(basename(source))}</span><strong>${escapeHtml(source.endsWith(".pdf") ? "PDF" : "TXT")}</strong>`;
    row.addEventListener("click", () => selectPaper(source));
    sources.appendChild(row);
  });
}

function selectPaperByName(name) {
  const match = getSourceFiles().find((source) => basename(source) === name) || name;
  selectPaper(match);
}

function selectPaper(source) {
  selectedPaper = source;
  renderPaperSelector(getSourceFiles());
  if (latestP0) renderFigures(latestP0, latestFigureImages);
}

function getSourceFiles() {
  return latestPayload?.full_arm?.provenance?.source_files || latestPayload?.summary?.source_file_names || [];
}

function renderGate(gate, moduleStatus) {
  const list = document.getElementById("gateList");
  list.innerHTML = "";
  const checks = [
    ["ARM 九模块完整", gate.arm_modules_9, "metadata / claims / evidence / protocol / runbook / eval_plan / provenance / limitations / artifacts"],
    ["至少 5 条 claim", gate.claims_at_least_5, "成功分支应抽取不少于 5 条可追溯结论"],
    ["原文摘抄 claim", gate.quote_only_claims, "raw_text 必须与 support_evidence_snippet 对齐"],
    ["证据已绑定", gate.evidence_linked, "每条 claim 必须有 evidence_ids"],
    ["ECS 专项标记", gate.ecs_tagging, "metadata / claims 中体现 ECS 相关字段"],
    ["Runbook 可试运行", gate.dry_run_runbook, "至少一个步骤 can_dry_run=True"],
    ["Dry-run 已评估", gate.dry_run_evaluated, "dry_run_result 与 evaluation_result 写入 provenance"],
    ["图表 caption 追踪", gate.figure_caption_trace, "图表/表格/补充材料 caption 抽取记录写入 provenance"],
    ["冲突扫描记录", gate.conflict_scan_logged, "跨论文 claim 冲突检测写入 provenance"],
    ["Trace 可回放", gate.trace_replay, "工具调用、输入输出和校验结果可回放"],
    ["引用校验入 provenance", gate.reference_validation_logged, "reference_validator 输出写入 provenance 和 trace"],
    ["医学边界限制", gate.medical_boundary, "limitations 中包含 medical_boundary"],
    ["失败阻断可展示", gate.failure_blocking, "失败输入不生成成功 ARM，而输出 blocked report"],
  ];
  checks.forEach(([title, passed, detail]) => list.appendChild(gateCard(title, passed, detail)));
  const moduleLine = Object.entries(moduleStatus).map(([key, value]) => `${key}:${value ? "OK" : "MISS"}`).join(" | ");
  list.appendChild(gateCard("模块明细", Object.values(moduleStatus).every(Boolean), moduleLine || "未生成"));
}

function renderClaims(claims) {
  const list = document.getElementById("claimsList");
  list.innerHTML = "";
  if (!claims.length) return list.appendChild(item("无 claims", "失败阻断分支不会生成科学 claims。"));
  claims.forEach((claim) => {
    const div = document.createElement("div");
    div.className = "item claimItem";
    div.innerHTML = `<div class="itemTitle">${escapeHtml(claim.claim_id)} · ${escapeHtml(claim.claim_category || claim.claim_type)}</div>
      <div class="meta">${escapeHtml(claim.source_location || claim.locator)} · ECS: ${yesNo(claim.ecs_related)} · ${escapeHtml(claim.source_attribution || "")}</div>
      <div class="quote">${escapeHtml(claim.raw_text || claim.text)}</div>`;
    list.appendChild(div);
  });
}

function renderFigures(p0, imagePayload) {
  const figures = filterBySelectedPaper(p0.figure_evidence || []);
  const conflicts = p0.conflicts || [];
  const summary = document.getElementById("figureSummary");
  summary.innerHTML = "";
  [
    ["caption 数", figures.length, ""], ["冲突对", conflicts.length, conflicts.length >= 3 ? "danger" : ""],
    ["caption 来源", p0.p0_trace_summary?.figure_caption_sources ?? "-", ""],
    ["冲突状态", conflicts.length ? "review_required" : "no_conflict_detected", conflicts.length ? "warn" : ""],
  ].forEach(([label, value, state]) => summary.appendChild(metric(label, value, state)));

  const list = document.getElementById("figureList");
  list.innerHTML = "";
  if (!figures.length) list.appendChild(item("未抽取到图表 caption", "仅解析 PDF/TXT 可抽取文本中的 caption；原图提取失败时不影响图注展示。"));
  const imageRows = imagePayload?.figures_with_images || [];
  figures.forEach((figure, index) => {
    const matched = imageRows.find((row) => sameSource(row.source_file, figure.source_file) && row.figure_id === figure.figure_id) || imageRows[index] || {};
    list.appendChild(figureCard(figure, matched.image, imagePayload));
  });

  const conflictsEl = document.getElementById("conflictList");
  conflictsEl.innerHTML = "";
  if (!conflicts.length) conflictsEl.appendChild(item("未发现冲突候选", "冲突检测为保守词汇级扫描；科学矛盾必须人工复核。"));
  conflicts.forEach((conflict) => conflictsEl.appendChild(item(`${conflict.conflict_id} · ${conflict.risk_level}`, conflict.reason, `shared_terms=${(conflict.shared_terms || []).join(", ")}`)));
}

function figureCard(figure, image, imagePayload) {
  const div = document.createElement("div");
  div.className = "item figureCard";
  const imageHtml = image?.data_url
    ? `<button class="figureImageButton" type="button"><img class="figureImage" src="${image.data_url}" alt="${escapeHtml(figure.figure_id)}"></button>`
    : `<div class="imageFallback">${escapeHtml(imagePayload?.risks?.[0]?.message || "未提取到论文原图，继续展示图注文本。")}</div>`;
  div.innerHTML = `${imageHtml}
    <div class="itemTitle">${escapeHtml(figure.figure_id)} · ${escapeHtml(figure.evidence_type || "figure_caption")}</div>
    <div class="meta">${escapeHtml(figure.locator || "")} · review_required=${figure.review_required}</div>
    <div class="captionText collapsed">${formatCaption(figure.caption || "")}</div>
    <button class="linkButton" type="button">展开/收起</button>`;
  const imageButton = div.querySelector(".figureImageButton");
  if (imageButton) imageButton.addEventListener("click", () => openImageModal(image.data_url));
  div.querySelector(".linkButton").addEventListener("click", () => div.querySelector(".captionText").classList.toggle("collapsed"));
  return div;
}

function renderDryRun(p0) {
  const dry = p0.dry_run || {};
  const evaluation = p0.evaluation || {};
  const summary = document.getElementById("dryRunSummary");
  summary.innerHTML = "";
  [["Dry-run 状态", dry.status], ["步骤数", dry.summary?.total_steps], ["失败步骤", dry.summary?.failed_steps], ["Review required", yesNo(dry.summary?.review_required)], ["评估状态", evaluation.status], ["评估分", evaluation.summary?.score]].forEach(([label, value]) => summary.appendChild(metric(label, value ?? "-")));
  const dryList = document.getElementById("dryRunList");
  dryList.innerHTML = "";
  (dry.steps || []).forEach((step) => dryList.appendChild(item(`${step.step_id} · ${step.status}`, step.observed_output || step.action, (step.errors || []).join(", "))));
  if (!(dry.steps || []).length) dryList.appendChild(item("无 dry-run 结果", "失败阻断或尚未生成 ARM 时可能为空。"));
  const evalList = document.getElementById("evalList");
  evalList.innerHTML = "";
  (evaluation.metrics || []).forEach((metricRow) => evalList.appendChild(item(`${metricRow.metric_id} · ${metricRow.passed ? "PASS" : "CHECK"}`, metricRow.name, `${metricRow.expected} | observed: ${metricRow.observed}`)));
}

function renderReferences(referenceValidation) {
  const summary = referenceValidation.summary || {};
  const grid = document.getElementById("referenceSummary");
  grid.innerHTML = "";
  [["状态", referenceValidation.status], ["检查总数", referenceValidation.checked_count], ["有效", referenceValidation.reference_valid_count], ["需复核/无效", referenceValidation.reference_invalid_count], ["缺 DOI/PMID", summary.identifier_invalid], ["信息不完整", summary.information_incomplete], ["领域不明", summary.domain_mismatch_or_unclear], ["重复/冲突", summary.duplicate_or_conflict]].forEach(([label, value]) => grid.appendChild(metric(label, value ?? "-")));
  const list = document.getElementById("referenceList");
  list.innerHTML = "";
  (referenceValidation.validated_references || []).slice(0, 50).forEach((ref, index) => list.appendChild(item(`[#${index + 1}] ${ref.reference_valid ? "reference_valid" : "reference_invalid"}`, ref.title || ref.reference_text || "Untitled reference", (ref.reference_invalid || []).join(", "))));
}

function renderTrace(trace, fineTrace) {
  const list = document.getElementById("traceList");
  list.innerHTML = "";
  (trace.tool_calls || []).forEach((call) => list.appendChild(item(`${call.sequence}. ${call.tool_name}`, `input: ${JSON.stringify(call.input)}`, `output keys: ${Object.keys(call.output || {}).join(", ")}`)));
  (trace.events || []).forEach((event) => list.appendChild(item(`${event.sequence}. ${event.stage} · ${event.status}`, JSON.stringify(event.detail || {}))));
  if (fineTrace?.claims?.length) list.appendChild(item("fine_trace.claims", `${fineTrace.claims.length} claim-level records embedded in provenance.`));
}

function updateBadges(summary, arm, trace) {
  const refIssues = arm.provenance?.reference_validation?.reference_invalid_count || 0;
  const evidenceReview = (latestP0?.figure_evidence || []).filter((fig) => fig.review_required).length;
  const traceErrors = (trace.events || []).filter((event) => ["blocked", "warning"].includes(event.status)).length;
  setBadge("references", refIssues);
  setBadge("figures", evidenceReview);
  setBadge("trace", traceErrors);
}

function updateReviewBanner(summary, arm, trace) {
  const evidenceReview = (latestP0?.figure_evidence || []).filter((fig) => fig.review_required).length;
  const refIssues = arm.provenance?.reference_validation?.reference_invalid_count || 0;
  const traceErrors = (trace.events || []).filter((event) => ["blocked", "warning"].includes(event.status)).length;
  document.getElementById("reviewBanner").textContent = `待复核：证据 ${evidenceReview} · 引用 ${refIssues} · Trace ${traceErrors}`;
}

function setBadge(tabName, count) {
  const tab = document.querySelector(`.tab[data-tab="${tabName}"]`);
  if (!tab) return;
  tab.dataset.badge = count > 0 ? String(count) : "";
  tab.classList.toggle("hasBadge", count > 0);
}

function renderEmpty() {
  ["summaryGrid", "sources", "risks", "gateList", "claimsList", "figureSummary", "figureList", "conflictList", "dryRunSummary", "dryRunList", "evalList", "referenceSummary", "referenceList", "traceList"].forEach((id) => { document.getElementById(id).innerHTML = ""; });
  document.getElementById("rawJson").textContent = "";
}

function setStatus(status, message) { statusEl.className = `status ${status}`; statusEl.textContent = ({ idle: "待上传", queued: "排队中", running: "生成中", completed: "已完成", failed: "失败" }[status] || status); messageEl.textContent = message || ""; }
function metric(label, value, state = "") { const div = document.createElement("div"); div.className = `metric ${state}`; div.innerHTML = `<div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(String(value))}</div>`; return div; }
function gateCard(title, passed, detail) { const div = document.createElement("div"); div.className = `gateCard ${passed ? "pass" : "fail"}`; div.innerHTML = `<div class="gateState">${passed ? "PASS" : "CHECK"}</div><div class="itemTitle">${escapeHtml(title)}</div><div class="meta">${escapeHtml(detail)}</div>`; return div; }
function item(title, body, meta = "") { const div = document.createElement("div"); div.className = "item"; div.innerHTML = `<div class="itemTitle">${escapeHtml(title)}</div>${meta ? `<div class="meta">${escapeHtml(meta)}</div>` : ""}<div>${escapeHtml(body || "")}</div>`; return div; }
function filterBySelectedPaper(items) { return selectedPaper ? items.filter((item) => sameSource(item.source_file, selectedPaper)) : items; }
function sameSource(a, b) { return basename(a || "") === basename(b || "") || String(a || "") === String(b || ""); }
function basename(path) { return String(path || "").split(/[\\/]/).pop(); }
function yesNo(value) { return value ? "是" : "否"; }
function formatBytes(bytes) { if (!bytes) return "0 B"; const units = ["B", "KB", "MB", "GB"]; const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1); return `${(bytes / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`; }
function escapeHtml(value) { return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
function formatCaption(text) { return escapeHtml(text).replace(/\[(\d+)\]/g, '<span class="refMark" title="引用校验结果请查看引用校验Tab">[$1]</span>').replace(/(conflict|contradict|does not|failed|不一致|冲突)/gi, '<span class="conflictMark">$1</span>'); }
function openImageModal(src) { document.getElementById("modalImage").src = src; document.getElementById("imageModal").classList.remove("hidden"); }
function closeImageModal() { document.getElementById("imageModal").classList.add("hidden"); document.getElementById("modalImage").src = ""; }
