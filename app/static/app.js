"use strict";

const form = document.getElementById("scan-form");
const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const dzTitle = document.getElementById("dz-title");
const scanBtn = document.getElementById("scan-btn");
const errorEl = document.getElementById("error");
const loading = document.getElementById("loading");
const results = document.getElementById("results");
const uploadSection = document.getElementById("upload-section");
const rescanBtn = document.getElementById("rescan-btn");

const SEVERITY_LABEL = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

function statusClass(status) {
  return status === "good" ? "good" : status === "warning" ? "warning" : "poor";
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
}

function clearError() {
  errorEl.hidden = true;
  errorEl.textContent = "";
}

function setFile(file) {
  if (!file) return;
  clearError();
  dzTitle.textContent = file.name;
  dropzone.classList.add("has-file");
  scanBtn.disabled = false;
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) {
    fileInput.files = e.dataTransfer.files;
    setFile(file);
  }
});
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();
  if (!fileInput.files[0]) {
    showError("Please choose a CV file first.");
    return;
  }

  const data = new FormData();
  data.append("file", fileInput.files[0]);
  data.append(
    "job_description",
    document.getElementById("job-description").value || ""
  );

  uploadSection.hidden = true;
  results.hidden = true;
  loading.hidden = false;

  try {
    const res = await fetch("/api/scan", { method: "POST", body: data });
    const payload = await res.json();
    if (!res.ok) {
      throw new Error(payload.detail || "Something went wrong. Please try again.");
    }
    renderResults(payload);
  } catch (err) {
    uploadSection.hidden = false;
    showError(err.message);
  } finally {
    loading.hidden = true;
  }
});

rescanBtn.addEventListener("click", () => {
  results.hidden = true;
  uploadSection.hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
});

function ratingColor(score) {
  if (score >= 80) return "var(--good)";
  if (score >= 55) return "var(--warn)";
  return "var(--poor)";
}

function animateScore(target) {
  const ring = document.getElementById("score-ring");
  const valueEl = document.getElementById("score-value");
  const col = ratingColor(target);
  ring.style.setProperty("--col", col);
  let current = 0;
  const step = Math.max(1, Math.round(target / 30));
  const timer = setInterval(() => {
    current = Math.min(target, current + step);
    valueEl.textContent = current;
    ring.style.setProperty("--val", current);
    if (current >= target) clearInterval(timer);
  }, 18);
}

function renderResults(p) {
  animateScore(p.overall_score);

  const pill = document.getElementById("rating-pill");
  pill.textContent = p.rating;
  pill.style.background = ratingColor(p.overall_score);
  document.getElementById("score-summary").textContent = p.summary;

  const statRow = document.getElementById("stat-row");
  const s = p.stats;
  statRow.innerHTML = "";
  const stats = [
    ["Words", s.word_count],
    ["Bullet points", s.bullet_points],
    ["Action verbs", s.action_verbs],
    ["Quantified bullets", s.quantified_bullets],
  ];
  for (const [label, val] of stats) {
    const el = document.createElement("div");
    el.className = "stat";
    el.innerHTML = `<b>${val}</b><span>${label}</span>`;
    statRow.appendChild(el);
  }

  // Top fixes
  const topFixes = document.getElementById("top-fixes");
  topFixes.innerHTML = "";
  if (p.top_fixes.length === 0) {
    topFixes.innerHTML = "<li>Nice work — no critical issues found.</li>";
  }
  for (const fix of p.top_fixes) {
    const li = document.createElement("li");
    li.textContent = fix.message;
    topFixes.appendChild(li);
  }

  // Categories
  const cats = document.getElementById("categories");
  cats.innerHTML = "";
  for (const c of p.categories) {
    const cls = statusClass(c.status);
    const wrap = document.createElement("div");
    wrap.className = "cat";
    const details = (c.details || [])
      .map((d) => `<li>${escapeHtml(d)}</li>`)
      .join("");
    wrap.innerHTML = `
      <div class="cat-head">
        <b>${escapeHtml(c.label)}</b>
        <span class="cat-score ${cls}">${c.score}/100</span>
      </div>
      <div class="bar"><span class="bg-${c.status}" style="width:${c.score}%"></span></div>
      <p class="cat-summary">${escapeHtml(c.summary)}</p>
      <ul class="cat-details">${details}</ul>
    `;
    cats.appendChild(wrap);
  }

  // Keywords
  const kwCard = document.getElementById("keywords-card");
  if (p.meta && p.meta.job_description_provided) {
    kwCard.hidden = false;
    renderTags("kw-matched", p.matched_keywords, "tag");
    renderTags("kw-missing", p.missing_keywords, "tag miss");
  } else {
    kwCard.hidden = true;
  }

  // Recommendations
  const recs = document.getElementById("recommendations");
  recs.innerHTML = "";
  if (p.recommendations.length === 0) {
    recs.innerHTML = "<li>No recommendations — your resume looks great!</li>";
  }
  for (const r of p.recommendations) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="sev sev-${r.severity}">${
      SEVERITY_LABEL[r.severity] || r.severity
    }</span><span>${escapeHtml(r.message)}</span>`;
    recs.appendChild(li);
  }

  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth" });
}

function renderTags(id, items, cls) {
  const el = document.getElementById(id);
  el.innerHTML = "";
  if (!items || items.length === 0) {
    el.innerHTML = '<span class="cat-summary">None</span>';
    return;
  }
  for (const item of items) {
    const span = document.createElement("span");
    span.className = cls;
    span.textContent = item;
    el.appendChild(span);
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
