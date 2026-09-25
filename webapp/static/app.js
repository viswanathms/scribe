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
      ? `Claude's take: ${paper.importance_reasoning}`
      : "Not yet reviewed by Claude.";

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
  const params = new URLSearchParams({
    sort: sortByEl.value,
    order: orderEl.value,
  });
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

loadStats();
loadPapers();
