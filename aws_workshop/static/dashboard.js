/* Return Radar - seller dashboard.
 * Fetches aggregated stats from /stats and renders summary cards, pure-CSS bar
 * charts of top return reasons per category, and a table of recent submissions.
 */
(function () {
  "use strict";

  const statCards = document.getElementById("stat-cards");
  const charts = document.getElementById("charts");
  const tableWrap = document.getElementById("submissions-table");

  // Escape text to avoid injecting markup from stored feedback.
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[c];
    });
  }

  function renderStatCards(data) {
    const categoryCount = Object.keys(data.by_category || {}).length;
    const topCategory = topEntry(data.by_category);
    statCards.innerHTML = `
      <div class="stat">
        <div class="value">${data.total}</div>
        <div class="label">Total returns logged</div>
      </div>
      <div class="stat">
        <div class="value">${categoryCount}</div>
        <div class="label">Categories with returns</div>
      </div>
      <div class="stat">
        <div class="value">${topCategory ? esc(topCategory[0]) : "&mdash;"}</div>
        <div class="label">Most returned category</div>
      </div>
    `;
  }

  function topEntry(obj) {
    const entries = Object.entries(obj || {});
    if (!entries.length) return null;
    entries.sort((a, b) => b[1] - a[1]);
    return entries[0];
  }

  function renderCharts(data) {
    const reasons = data.reasons_by_category || {};
    const categories = Object.keys(reasons);

    if (!categories.length) {
      charts.innerHTML =
        '<p class="empty-state">No feedback yet. Submissions will appear here as customers complete the questionnaire.</p>';
      return;
    }

    let html = "";
    categories.forEach(function (cat) {
      const rows = reasons[cat] || [];
      const total = rows.reduce((sum, r) => sum + r.count, 0);
      const max = rows.reduce((m, r) => Math.max(m, r.count), 0) || 1;

      html += `<div class="category-panel">
        <h3>
          <span>${esc(cat)}</span>
          <span class="count-badge">${total} return${total === 1 ? "" : "s"}</span>
        </h3>`;

      rows.forEach(function (r) {
        const pct = Math.round((r.count / max) * 100);
        // Bar conveys magnitude; the numeric count is shown as text too
        // so meaning does not rely on color/length alone.
        html += `<div class="bar-row">
          <span class="bar-label">${esc(r.reason)}</span>
          <span class="bar-track" role="img"
                aria-label="${esc(r.reason)}: ${r.count} of ${total}">
            <span class="bar-fill" style="width:${pct}%"></span>
          </span>
          <span class="bar-count">${r.count}</span>
        </div>`;
      });

      html += `</div>`;
    });

    charts.innerHTML = html;
  }

  function renderTable(data) {
    const subs = data.submissions || [];
    if (!subs.length) {
      tableWrap.innerHTML =
        '<p class="empty-state">No submissions yet.</p>';
      return;
    }

    let rows = "";
    subs.forEach(function (s) {
      const when = formatDate(s.created_at);
      const detail = (s.answers || [])
        .map((a) => esc(a.answer_value))
        .join(" &middot; ");
      rows += `<tr>
        <td>${s.id}</td>
        <td>${esc(s.category)}</td>
        <td>${esc(s.final_reason || "—")}</td>
        <td>${detail}</td>
        <td>${when}</td>
      </tr>`;
    });

    tableWrap.innerHTML = `
      <table class="submissions">
        <caption class="visually-hidden">Recent return submissions</caption>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Category</th>
            <th scope="col">Primary reason</th>
            <th scope="col">Answer trail</th>
            <th scope="col">Submitted</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return esc(iso);
    return d.toLocaleString();
  }

  async function load() {
    try {
      const res = await fetch("/stats", {
        headers: { Accept: "application/json" },
      });
      if (res.status === 401) {
        window.location.href = "/login?next=/dashboard";
        return;
      }
      const data = await res.json();
      renderStatCards(data);
      renderCharts(data);
      renderTable(data);
    } catch (err) {
      charts.innerHTML =
        '<p class="empty-state">Could not load dashboard data.</p>';
    }
  }

  load();
})();
