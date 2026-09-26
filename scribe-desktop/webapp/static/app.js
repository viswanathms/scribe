const wizardEl = document.getElementById("wizard");
const mainViewEl = document.getElementById("mainView");

const PROVIDER_DEFAULT_BASE_URL = {
  anthropic: "https://api.anthropic.com",
  openai: "https://api.openai.com/v1",
  ollama: "http://localhost:11434",
};
const PROVIDER_MODEL_SUGGESTIONS = {
  anthropic: ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"],
  openai: ["gpt-5.1", "gpt-5.1-mini"],
  ollama: [],
};

let currentSettings = null;

// ===================== Wizard =====================

function showWizardStep(step) {
  document.querySelectorAll(".wizard-step").forEach((el) => {
    el.classList.toggle("hidden", el.dataset.step !== String(step));
  });
  document.querySelectorAll(".wizard-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.step === String(step));
  });
}

document.querySelectorAll(".wizard-tab").forEach((tab) => {
  tab.addEventListener("click", () => showWizardStep(tab.dataset.step));
});

function applyProviderDefaults() {
  const provider = document.getElementById("provider").value;
  const baseUrlEl = document.getElementById("baseUrl");
  if (!baseUrlEl.value || Object.values(PROVIDER_DEFAULT_BASE_URL).includes(baseUrlEl.value)) {
    baseUrlEl.value = PROVIDER_DEFAULT_BASE_URL[provider] || "";
  }
  document.getElementById("apiKeyLabel").classList.toggle("hidden", provider === "ollama");

  const modelList = document.getElementById("modelSuggestions");
  modelList.innerHTML = "";
  if (provider === "ollama") {
    fetch(`/api/settings/models?provider=ollama&base_url=${encodeURIComponent(baseUrlEl.value)}`)
      .then((r) => r.json())
      .then((data) => {
        (data.models || []).forEach((m) => {
          const opt = document.createElement("option");
          opt.value = m;
          modelList.appendChild(opt);
        });
      });
  } else {
    (PROVIDER_MODEL_SUGGESTIONS[provider] || []).forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m;
      modelList.appendChild(opt);
    });
  }
}

document.getElementById("provider").addEventListener("change", applyProviderDefaults);

document.getElementById("testConnectionBtn").addEventListener("click", async () => {
  const resultEl = document.getElementById("testConnectionResult");
  resultEl.textContent = "Testing…";
  resultEl.removeAttribute("data-ok");

  const payload = {
    provider: document.getElementById("provider").value,
    base_url: document.getElementById("baseUrl").value,
    model: document.getElementById("model").value,
  };
  const apiKey = document.getElementById("apiKey").value;
  if (apiKey) payload.api_key = apiKey;

  const res = await fetch("/api/settings/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (data.ok) {
    resultEl.textContent = "Connected.";
    resultEl.dataset.ok = "true";
    document.getElementById("step1Next").disabled = false;
  } else {
    resultEl.textContent = data.error || "Failed.";
    resultEl.dataset.ok = "false";
    document.getElementById("step1Next").disabled = true;
  }
});

document.getElementById("step1Next").addEventListener("click", async () => {
  await saveSettingsFromStep1();
  showWizardStep(2);
});

document.getElementById("step2Back").addEventListener("click", () => showWizardStep(1));
document.getElementById("step3Back").addEventListener("click", () => showWizardStep(2));

async function saveSettingsFromStep1() {
  const payload = {
    provider: document.getElementById("provider").value,
    base_url: document.getElementById("baseUrl").value,
    model: document.getElementById("model").value,
  };
  const apiKey = document.getElementById("apiKey").value;
  if (apiKey) payload.api_key = apiKey;
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function pollJob(progressEl, fillEl, detailEl, onDone) {
  const interval = setInterval(async () => {
    const res = await fetch("/api/job");
    const job = await res.json();
    progressEl.classList.remove("hidden");
    const pct = job.total ? Math.min(100, Math.round((job.progress / job.total) * 100)) : 0;
    fillEl.style.width = `${pct}%`;
    detailEl.textContent = job.detail || `${job.progress}/${job.total || "?"}`;
    if (job.state === "done") {
      clearInterval(interval);
      detailEl.textContent = "Done.";
      onDone(true);
    } else if (job.state === "error") {
      clearInterval(interval);
      detailEl.textContent = `Error: ${job.error}`;
      onDone(false);
    }
  }, 1000);
}

document.getElementById("extractBtn").addEventListener("click", async () => {
  const category = document.getElementById("category").value || "cs.AI";
  const days = parseInt(document.getElementById("daysBack").value, 10) || 30;
  document.getElementById("extractBtn").disabled = true;

  await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category, days }),
  });

  pollJob(
    document.getElementById("jobProgress"),
    document.getElementById("jobProgressFill"),
    document.getElementById("jobProgressDetail"),
    (ok) => {
      document.getElementById("extractBtn").disabled = false;
      if (ok) document.getElementById("step2Next").disabled = false;
    }
  );
});

document.getElementById("step2Next").addEventListener("click", async () => {
  const category = document.getElementById("category").value || "cs.AI";
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category }),
  });
  await loadCriteriaSuggestions();
  showWizardStep(3);
});

async function loadCriteriaSuggestions() {
  const res = await fetch("/api/settings/criteria-suggestions");
  const data = await res.json();
  const typeList = document.getElementById("typeSuggestions");
  const funcList = document.getElementById("functionSuggestions");
  typeList.innerHTML = "";
  funcList.innerHTML = "";
  (data.type || []).forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t;
    typeList.appendChild(opt);
  });
  (data.function || []).forEach((f) => {
    const opt = document.createElement("option");
    opt.value = f;
    funcList.appendChild(opt);
  });
}

document.getElementById("saveAndReviewBtn").addEventListener("click", async () => {
  const criteria = {
    type: document.getElementById("critType").value,
    function: document.getElementById("critFunction").value,
    area: document.getElementById("critArea").value,
    other: document.getElementById("critOther").value,
  };
  document.getElementById("saveAndReviewBtn").disabled = true;

  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ criteria, onboarded: true }),
  });

  await fetch("/api/review/run", { method: "POST" });

  pollJob(
    document.getElementById("reviewProgress"),
    document.getElementById("reviewProgressFill"),
    document.getElementById("reviewProgressDetail"),
    (ok) => {
      document.getElementById("saveAndReviewBtn").disabled = false;
      if (ok) document.getElementById("finishBtn").classList.remove("hidden");
    }
  );
});

document.getElementById("finishBtn").addEventListener("click", () => {
  wizardEl.classList.add("hidden");
  mainViewEl.classList.remove("hidden");
  loadStats();
  loadPapers();
});

document.getElementById("settingsBtn").addEventListener("click", async () => {
  await populateWizardFromSettings();
  mainViewEl.classList.add("hidden");
  wizardEl.classList.remove("hidden");
  showWizardStep(1);
  document.getElementById("step1Next").disabled = false;
  document.getElementById("finishBtn").classList.remove("hidden");
});

document.getElementById("extractMoreBtn").addEventListener("click", async () => {
  await populateWizardFromSettings();
  mainViewEl.classList.add("hidden");
  wizardEl.classList.remove("hidden");
  showWizardStep(2);
  document.getElementById("finishBtn").classList.remove("hidden");
});

async function populateWizardFromSettings() {
  const res = await fetch("/api/settings");
  const settings = await res.json();
  currentSettings = settings;
  document.getElementById("provider").value = settings.provider || "anthropic";
  document.getElementById("baseUrl").value = settings.base_url || "";
  document.getElementById("apiKey").value = "";
  document.getElementById("apiKey").placeholder = settings.api_key_set ? "•••••••• (saved, leave blank to keep)" : "sk-...";
  document.getElementById("model").value = settings.model || "";
  document.getElementById("category").value = settings.category || "cs.AI";
  document.getElementById("critType").value = settings.criteria?.type || "";
  document.getElementById("critFunction").value = settings.criteria?.function || "";
  document.getElementById("critArea").value = settings.criteria?.area || "";
  document.getElementById("critOther").value = settings.criteria?.other || "";
  applyProviderDefaults();
  await loadCriteriaSuggestions();
}

// ===================== Main paper list (unchanged behavior from original SCRIBE) =====================

const resultsEl = document.getElementById("results");
const statsEl = document.getElementById("stats");
const sortByEl = document.getElementById("sortBy");
const orderEl = document.getElementById("order");
const dateFilterEl = document.getElementById("dateFilter");
const minScoreEl = document.getElementById("minScore");
const cardTemplate = document.getElementById("paperCardTemplate");

function scoreTier(score) {
  if (score === null || score === undefined) return "low";
  if (score >= 8) return "high";
  if (score >= 5) return "mid";
  return "low";
}

function renderPapers(papers) {
  resultsEl.innerHTML = "";
  if (papers.length === 0) {
    resultsEl.innerHTML = '<p class="empty">No papers match these filters yet.</p>';
    return;
  }
  for (const paper of papers) {
    const node = cardTemplate.content.cloneNode(true);
    const scoreEl = node.querySelector('[data-role="score"]');
    scoreEl.textContent = paper.importance_score ?? "–";
    scoreEl.dataset.tier = scoreTier(paper.importance_score);

    const absLink = node.querySelector('[data-role="abs-link"]');
    absLink.textContent = paper.title;
    absLink.href = paper.abs_url;

    node.querySelector('[data-role="date"]').textContent = paper.published_date;
    node.querySelector('[data-role="authors"]').textContent = paper.authors;
    node.querySelector('[data-role="pdf-link"]').href = paper.pdf_url;

    const tagsEl = node.querySelector('[data-role="tags"]');
    (paper.review_tags || []).forEach((tag) => {
      const span = document.createElement("span");
      span.textContent = tag;
      tagsEl.appendChild(span);
    });

    node.querySelector('[data-role="impact"]').textContent = paper.growth_impact || "";
    node.querySelector('[data-role="abstract"]').textContent = paper.abstract;
    node.querySelector('[data-role="reasoning"]').textContent = paper.importance_reasoning
      ? `Take: ${paper.importance_reasoning}`
      : "Not yet reviewed.";

    resultsEl.appendChild(node);
  }
}

async function loadStats() {
  const res = await fetch("/api/stats");
  const stats = await res.json();
  statsEl.textContent = `${stats.total_papers} papers tracked · ${stats.reviewed} reviewed · ${stats.days_covered} days covered`;
}

async function loadPapers() {
  resultsEl.innerHTML = '<p class="loading">Loading papers…</p>';
  const params = new URLSearchParams({ sort: sortByEl.value, order: orderEl.value });
  if (dateFilterEl.value) params.set("date", dateFilterEl.value);
  if (minScoreEl.value) params.set("min_score", minScoreEl.value);

  const res = await fetch(`/api/papers?${params.toString()}`);
  const papers = await res.json();
  renderPapers(papers);
}

for (const el of [sortByEl, orderEl, dateFilterEl, minScoreEl]) {
  el.addEventListener("change", loadPapers);
}
document.getElementById("clearFilters").addEventListener("click", () => {
  dateFilterEl.value = "";
  minScoreEl.value = "";
  loadPapers();
});

// ===================== Main tabs =====================

document.querySelectorAll(".main-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".main-tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("hidden", p.id !== `tab-${tab.dataset.tab}`));
    if (tab.dataset.tab === "report") loadReport();
    if (tab.dataset.tab === "subject") loadSubjectChart();
    if (tab.dataset.tab === "calendar") loadCalendar();
  });
});

// ===================== Daily Report =====================

const reportItemTemplate = document.getElementById("reportItemTemplate");
const reportDateEl = document.getElementById("reportDate");
const reportThresholdEl = document.getElementById("reportThreshold");

async function loadReport() {
  const resultsEl = document.getElementById("reportResults");
  const summaryEl = document.getElementById("reportSummary");
  resultsEl.innerHTML = '<p class="loading">Loading report…</p>';

  if (!reportDateEl.value || !reportThresholdEl.value) {
    const [datesRes, settingsRes] = await Promise.all([fetch("/api/dates"), fetch("/api/settings")]);
    const dates = await datesRes.json();
    const settings = await settingsRes.json();
    if (!reportDateEl.value) reportDateEl.value = dates.latest || "";
    if (!reportThresholdEl.value) reportThresholdEl.value = settings.report_threshold ?? 7;
  }

  const params = new URLSearchParams({ date: reportDateEl.value, min_score: reportThresholdEl.value });
  const res = await fetch(`/api/report?${params.toString()}`);
  const data = await res.json();

  summaryEl.textContent = `${data.papers.length} paper(s) on ${data.date} scoring >= ${data.min_score}`;

  resultsEl.innerHTML = "";
  if (data.papers.length === 0) {
    resultsEl.innerHTML = '<p class="empty">Nothing at or above this threshold for this day.</p>';
    return;
  }
  const ul = document.createElement("ul");
  for (const paper of data.papers) {
    const node = reportItemTemplate.content.cloneNode(true);
    const scoreEl = node.querySelector('[data-role="score"]');
    scoreEl.textContent = paper.importance_score;
    scoreEl.dataset.tier = scoreTier(paper.importance_score);
    const link = node.querySelector('[data-role="link"]');
    link.textContent = paper.title;
    link.href = paper.abs_url;
    node.querySelector('[data-role="summary"]').textContent = paper.summary || "(no summary yet -- run the summary backfill)";
    ul.appendChild(node);
  }
  resultsEl.appendChild(ul);
}

document.getElementById("reportRefreshBtn").addEventListener("click", async () => {
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_threshold: parseInt(reportThresholdEl.value, 10) || 7 }),
  });
  loadReport();
});

// ===================== By Subject =====================

async function loadSubjectChart() {
  const chartEl = document.getElementById("subjectChart");
  chartEl.innerHTML = '<p class="loading">Loading…</p>';
  const res = await fetch("/api/stats/by-subject?limit=15");
  const rows = await res.json();
  if (rows.length === 0) {
    chartEl.innerHTML = '<p class="empty">No subject data yet.</p>';
    return;
  }
  const max = Math.max(...rows.map((r) => r.count));
  chartEl.innerHTML = "";
  for (const row of rows) {
    const rowEl = document.createElement("div");
    rowEl.className = "subject-bar-row";
    rowEl.title = `${row.subject}: ${row.count} paper(s)`;

    const label = document.createElement("span");
    label.className = "subject-bar-label";
    label.textContent = row.subject;

    const track = document.createElement("span");
    track.className = "subject-bar-track";
    const fill = document.createElement("span");
    fill.className = "subject-bar-fill";
    fill.style.width = `${Math.max(2, (row.count / max) * 100)}%`;
    track.appendChild(fill);

    const count = document.createElement("span");
    count.className = "subject-bar-count";
    count.textContent = row.count;

    rowEl.append(label, track, count);
    chartEl.appendChild(rowEl);
  }
}

// ===================== Calendar =====================

let calYear = null;
let calMonth = null; // 1-12
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function tierFromAvg(avg) {
  if (avg === null || avg === undefined) return null;
  if (avg >= 8) return "high";
  if (avg >= 5) return "mid";
  return "low";
}

async function loadCalendar() {
  const grid = document.getElementById("calGrid");
  if (calYear === null) {
    const res = await fetch("/api/dates");
    const dates = await res.json();
    if (dates.latest) {
      calYear = parseInt(dates.latest.slice(0, 4), 10);
      calMonth = parseInt(dates.latest.slice(5, 7), 10);
    } else {
      const today = new Date();
      calYear = today.getFullYear();
      calMonth = today.getMonth() + 1;
    }
  }

  document.getElementById("calMonthLabel").textContent = `${MONTH_NAMES[calMonth - 1]} ${calYear}`;

  const res = await fetch(`/api/stats/by-day?year=${calYear}&month=${calMonth}`);
  const data = await res.json();
  const byDate = {};
  for (const d of data.days) byDate[d.date] = d;

  grid.innerHTML = "";
  for (const name of DAY_NAMES) {
    const el = document.createElement("div");
    el.className = "cal-day-name";
    el.textContent = name;
    grid.appendChild(el);
  }

  const firstOfMonth = new Date(Date.UTC(calYear, calMonth - 1, 1));
  const daysInMonth = new Date(Date.UTC(calYear, calMonth, 0)).getUTCDate();
  const leadingBlanks = firstOfMonth.getUTCDay();

  for (let i = 0; i < leadingBlanks; i++) {
    const el = document.createElement("div");
    el.className = "cal-cell empty";
    grid.appendChild(el);
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${calYear}-${String(calMonth).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const info = byDate[dateStr];
    const cell = document.createElement("div");
    cell.className = "cal-cell";
    if (info) {
      const tier = tierFromAvg(info.avg_score);
      if (tier) cell.dataset.tier = tier;
      cell.title = `${dateStr}: ${info.total} paper(s), avg score ${info.avg_score ?? "n/a"}`;
    } else {
      cell.title = dateStr;
    }
    const num = document.createElement("span");
    num.className = "cal-daynum";
    num.textContent = day;
    const count = document.createElement("span");
    count.className = "cal-count";
    count.textContent = info ? info.total : "";
    cell.append(num, count);
    grid.appendChild(cell);
  }
}

document.getElementById("calPrevBtn").addEventListener("click", () => {
  calMonth -= 1;
  if (calMonth < 1) { calMonth = 12; calYear -= 1; }
  loadCalendar();
});
document.getElementById("calNextBtn").addEventListener("click", () => {
  calMonth += 1;
  if (calMonth > 12) { calMonth = 1; calYear += 1; }
  loadCalendar();
});

// ===================== Boot =====================

(async function boot() {
  const res = await fetch("/api/settings");
  const settings = await res.json();
  currentSettings = settings;
  if (settings.onboarded) {
    wizardEl.classList.add("hidden");
    mainViewEl.classList.remove("hidden");
    loadStats();
    loadPapers();
  } else {
    mainViewEl.classList.add("hidden");
    wizardEl.classList.remove("hidden");
    document.getElementById("provider").value = "anthropic";
    applyProviderDefaults();
    await loadCriteriaSuggestions();
    showWizardStep(1);
  }
})();
