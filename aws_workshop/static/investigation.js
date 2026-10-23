/* Return Radar - Issue Investigation (seller-only).
 *
 * Loads the aggregated investigation report, lets the seller pick a product,
 * and shows: total customers reporting each specific problem, the defect rate
 * (% of units sold affected), the share of that model's returns, and a
 * comparison of the model's overall defect rate vs. its category average and
 * sibling models.
 */
(function () {
  "use strict";

  const productSelect = document.getElementById("product-select");
  const summaryEl = document.getElementById("product-summary");
  const issuesEl = document.getElementById("issues");
  const comparisonEl = document.getElementById("comparison");

  let report = null; // cached investigation data

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function pct(n) {
    return (Math.round(n * 100) / 100).toLocaleString() + "%";
  }

  async function load() {
    try {
      const res = await fetch("/investigation-data", {
        headers: { Accept: "application/json" },
      });
      if (res.status === 401) {
        window.location.href = "/login?next=/investigation";
        return;
      }
      report = await res.json();
      populateSelect();
    } catch (err) {
      issuesEl.innerHTML =
        '<p class="empty-state">Could not load investigation data.</p>';
    }
  }

  function populateSelect() {
    const products = (report && report.products) || [];
    if (!products.length) {
      productSelect.innerHTML = '<option value="">No products with returns yet</option>';
      issuesEl.innerHTML =
        '<p class="empty-state">No returns have been logged against any product yet.</p>';
      return;
    }

    let opts = '<option value="">Choose a product&hellip;</option>';
    products.forEach(function (p) {
      opts +=
        '<option value="' +
        esc(p.product_id) +
        '">' +
        esc(p.model) +
        " — " +
        p.total_returns +
        " return" +
        (p.total_returns === 1 ? "" : "s") +
        "</option>";
    });
    productSelect.innerHTML = opts;

    // Auto-select the product with the highest defect rate to tell a story.
    productSelect.value = products[0].product_id;
    renderProduct(products[0].product_id);
  }

  function findProduct(id) {
    return (report.products || []).find(function (p) {
      return p.product_id === id;
    });
  }

  function renderProduct(id) {
    const p = findProduct(id);
    if (!p) {
      summaryEl.innerHTML = "";
      issuesEl.innerHTML = '<p class="empty-state">Select a product to begin.</p>';
      comparisonEl.innerHTML =
        '<p class="empty-state">Select a product to see the comparison.</p>';
      return;
    }
    renderSummary(p);
    renderIssues(p);
    renderComparison(p);
  }

  function renderSummary(p) {
    summaryEl.innerHTML = `
      <div class="stat">
        <div class="value">${p.total_returns}</div>
        <div class="label">Total customers reporting a return</div>
      </div>
      <div class="stat">
        <div class="value">${p.units_sold.toLocaleString()}</div>
        <div class="label">Units sold</div>
      </div>
      <div class="stat">
        <div class="value">${pct(p.return_rate_pct)}</div>
        <div class="label">Overall return rate (of units sold)</div>
      </div>
    `;
  }

  function renderIssues(p) {
    const issues = p.issues || [];
    if (!issues.length) {
      issuesEl.innerHTML =
        '<p class="empty-state">No specific problems recorded for this model.</p>';
      return;
    }
    const maxShare = issues.reduce((m, i) => Math.max(m, i.share_of_returns_pct), 0) || 1;

    let html =
      '<p class="muted-line">Each row shows how many customers reported the ' +
      "problem, what share of this model's returns it represents, and the " +
      "defect rate across all units sold.</p>";

    issues.forEach(function (i) {
      const barPct = Math.round((i.share_of_returns_pct / maxShare) * 100);
      html += `
        <div class="issue-row">
          <div class="issue-head">
            <span class="issue-name">${esc(i.problem)}</span>
            <span class="issue-count">${i.count} customer${i.count === 1 ? "" : "s"}</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">Share of returns</span>
            <span class="bar-track" role="img"
                  aria-label="${esc(i.problem)}: ${pct(i.share_of_returns_pct)} of this model's returns">
              <span class="bar-fill" style="width:${barPct}%"></span>
            </span>
            <span class="bar-count">${pct(i.share_of_returns_pct)}</span>
          </div>
          <p class="issue-defect">
            Defect rate: <strong>${pct(i.defect_rate_pct)}</strong>
            of the ${p.units_sold.toLocaleString()} units sold
          </p>
        </div>`;
    });
    issuesEl.innerHTML = html;
  }

  function renderComparison(p) {
    const catAvg = (report.category_avg_defect_rate || {})[p.category];
    const siblings = (report.products || []).filter(function (o) {
      return o.category === p.category;
    });

    // Build a small set of bars: this model, category average, and siblings.
    const bars = [];
    bars.push({ label: p.model + " (this model)", value: p.return_rate_pct, highlight: true });
    if (typeof catAvg === "number") {
      bars.push({ label: "Category average", value: catAvg, isAvg: true });
    }
    siblings
      .filter((o) => o.product_id !== p.product_id)
      .forEach((o) => bars.push({ label: o.model, value: o.return_rate_pct }));

    const max = bars.reduce((m, b) => Math.max(m, b.value), 0) || 1;

    const catName = p.category_name || p.category;

    // Verdict line: is this model worse or better than its category average?
    let verdict = "";
    if (typeof catAvg === "number") {
      if (p.return_rate_pct > catAvg) {
        const diff = (p.return_rate_pct - catAvg).toFixed(2);
        verdict = `<p class="verdict worse" role="status">This model's return rate is
          <strong>${diff} points higher</strong> than the ${esc(catName)}
          category average — worth investigating.</p>`;
      } else if (p.return_rate_pct < catAvg) {
        const diff = (catAvg - p.return_rate_pct).toFixed(2);
        verdict = `<p class="verdict better" role="status">This model's return rate is
          <strong>${diff} points lower</strong> than the ${esc(catName)}
          category average — performing well.</p>`;
      } else {
        verdict = `<p class="verdict" role="status">This model is right at the
          ${esc(catName)} category average.</p>`;
      }
    }

    let html = verdict;
    bars.forEach(function (b) {
      const barPct = Math.round((b.value / max) * 100);
      const cls =
        "bar-fill" + (b.highlight ? " bar-fill-strong" : b.isAvg ? " bar-fill-avg" : "");
      html += `
        <div class="bar-row">
          <span class="bar-label">${esc(b.label)}</span>
          <span class="bar-track" role="img"
                aria-label="${esc(b.label)}: ${pct(b.value)} return rate">
            <span class="${cls}" style="width:${barPct}%"></span>
          </span>
          <span class="bar-count">${pct(b.value)}</span>
        </div>`;
    });
    comparisonEl.innerHTML = html;
  }

  productSelect.addEventListener("change", function () {
    renderProduct(productSelect.value);
  });

  load();
})();
