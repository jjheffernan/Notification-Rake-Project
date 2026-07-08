/** Market data pages — index browse + per-model classic.com-style view */

const { format, ui } = window.Rake;
const formatPrice = format.price;
const formatNum = format.num;

function normalizeMarketQuery(text) {
  return String(text ?? "").toLowerCase().trim().replace(/\s+/g, " ");
}

function marketTokens(text) {
  return normalizeMarketQuery(text).split(" ").filter(Boolean);
}

/** ponytail: subsequence + prefix + 1-edit; upgrade path: fuse.js */
function subsequenceMatch(needle, haystack) {
  if (!needle) return true;
  let i = 0;
  for (const c of haystack) {
    if (c === needle[i]) i += 1;
    if (i === needle.length) return true;
  }
  return false;
}

function levenshteinWithin(a, b, maxDist = 2) {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;
  if (Math.abs(a.length - b.length) > maxDist) return maxDist + 1;
  const row = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i += 1) {
    let prev = row[0];
    row[0] = i;
    let rowMin = row[0];
    for (let j = 1; j <= b.length; j += 1) {
      const tmp = row[j];
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      row[j] = Math.min(row[j] + 1, row[j - 1] + 1, prev + cost);
      prev = tmp;
      rowMin = Math.min(rowMin, row[j]);
    }
    if (rowMin > maxDist) return maxDist + 1;
  }
  return row[b.length];
}

function tokenMatchScore(token, words, fullHay) {
  let best = 0;
  for (const word of words) {
    if (word === token) best = Math.max(best, 95);
    else if (word.startsWith(token)) best = Math.max(best, 85);
    else if (word.includes(token)) best = Math.max(best, 70);
    else if (subsequenceMatch(token, word)) best = Math.max(best, 55);
    else if (token.length >= 3 && levenshteinWithin(token, word) <= 1) {
      best = Math.max(best, 50);
    }
  }
  if (fullHay.includes(token)) best = Math.max(best, 65);
  else if (subsequenceMatch(token, fullHay)) best = Math.max(best, 45);
  return best;
}

function scoreMarketModel(item, query) {
  const q = normalizeMarketQuery(query);
  if (!q) return 0;
  const hay = normalizeMarketQuery(`${item.make} ${item.model}`);
  const compactHay = hay.replace(/\s+/g, "");
  const compactQ = q.replace(/\s+/g, "");
  if (hay === q) return 200;
  if (hay.startsWith(q)) return 150;
  if (hay.includes(q)) return 120;
  if (compactHay.includes(compactQ)) return 110;

  const tokens = marketTokens(q);
  const words = hay.split(" ").filter(Boolean);
  let total = 0;
  for (const token of tokens) {
    const hit = tokenMatchScore(token, words, hay);
    if (!hit) return 0;
    total += hit;
  }
  return total / tokens.length;
}

function rankMarketModels(items, query) {
  const q = normalizeMarketQuery(query);
  if (!q) {
    return items.map((item) => ({ item, score: 0 }));
  }
  return items
    .map((item) => ({ item, score: scoreMarketModel(item, query) }))
    .filter((row) => row.score > 0)
    .sort((a, b) => b.score - a.score);
}

async function fetchMarketIndex() {
  const resp = await fetch("/api/market/models");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

async function fetchModelMarket(make, model, params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  const resp = await fetch(
    `/api/market/model?make=${encodeURIComponent(make)}&model=${encodeURIComponent(model)}&${qs}`
  );
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

const SALE_STATUS_META = {
  sold: { label: "Sold", color: "#22c55e" },
  high_bid: { label: "High Bid", color: "#ef4444" },
  for_sale: { label: "For Sale", color: "#111827" },
  last_asking: { label: "Last Asking", color: "#9ca3af" },
};

let salesChart = null;
let mileageChart = null;
let yearClassicChart = null;
let marketFilterState = {
  period_months: 12,
  min_price: "",
  max_price: "",
  max_mileage: "",
  country: "",
  status: "",
};

function renderIndexCard(item) {
  const article = document.createElement("article");
  article.className = "ui-card market-card";
  article.dataset.make = item.make;
  article.dataset.model = item.model;
  article.dataset.q = `${item.make} ${item.model}`.toLowerCase();
  const yearRange =
    item.year_min && item.year_max ? `${item.year_min}–${item.year_max}` : "";
  article.innerHTML = `
    <a href="${item.url}" class="market-card-link">
      <h2>${item.make} ${item.model}</h2>
      <div class="market-card-stats">
        <span><strong>${item.listings}</strong> listings</span>
        <span>Median ${formatPrice(item.median_price ?? item.avg_price)}</span>
        ${yearRange ? `<span>${yearRange}</span>` : ""}
      </div>
      <div class="market-card-range">
        ${formatPrice(item.min_price)} – ${formatPrice(item.max_price)}
      </div>
    </a>
  `;
  return article;
}

function initIndexPage() {
  const grid = document.getElementById("market-grid");
  const empty = document.getElementById("market-empty");
  const filter = document.getElementById("market-filter");
  const suggestions = document.getElementById("market-suggestions");
  const countEl = document.getElementById("market-count");
  const cardByKey = new Map();
  let items = [];
  let activeSuggestion = -1;

  function cardKey(item) {
    return `${item.make}\0${item.model}`;
  }

  function hideSuggestions() {
    suggestions?.classList.add("hidden");
    filter?.setAttribute("aria-expanded", "false");
    activeSuggestion = -1;
    suggestions?.querySelectorAll(".market-suggestion").forEach((el) => {
      el.classList.remove("is-active");
    });
  }

  function renderSuggestions(ranked) {
    if (!suggestions || !filter) return;
    suggestions.innerHTML = "";
    const top = ranked.slice(0, 8);
    if (!top.length || !filter.value.trim()) {
      hideSuggestions();
      return;
    }
    top.forEach(({ item }, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "market-suggestion";
      btn.role = "option";
      btn.id = `market-suggestion-${idx}`;
      btn.dataset.url = item.url;
      btn.innerHTML = `<span class="market-suggestion__label">${item.make} ${item.model}</span><span class="market-suggestion__meta">${item.listings} listings</span>`;
      btn.addEventListener("mousedown", (e) => e.preventDefault());
      btn.addEventListener("click", () => {
        window.location.href = item.url;
      });
      suggestions.appendChild(btn);
    });
    suggestions.classList.remove("hidden");
    filter.setAttribute("aria-expanded", "true");
  }

  function applyMarketFilter() {
    const q = filter?.value ?? "";
    const ranked = rankMarketModels(items, q);
    const visibleKeys = new Set(ranked.map(({ item }) => cardKey(item)));

    if (q.trim()) {
      ranked.forEach(({ item }) => {
        const el = cardByKey.get(cardKey(item));
        if (el) grid.appendChild(el);
      });
    }

    cardByKey.forEach((el, key) => {
      const show = !q.trim() || visibleKeys.has(key);
      el.classList.toggle("hidden", !show);
    });

    const visible = q.trim() ? ranked.length : items.length;
    countEl.textContent = q.trim()
      ? `${visible} of ${items.length} models`
      : `${items.length} models indexed`;
    empty.textContent = q.trim()
      ? `No models match “${q.trim()}”.`
      : "No indexed models yet — run ingest to populate market data.";
    empty.classList.toggle("hidden", visible > 0);
    renderSuggestions(ranked);
  }

  fetchMarketIndex()
    .then((data) => {
      items = data.models || [];
      countEl.textContent = `${items.length} models indexed`;
      if (!items.length) {
        empty.classList.remove("hidden");
        return;
      }
      items.forEach((item) => {
        const card = renderIndexCard(item);
        cardByKey.set(cardKey(item), card);
        grid.appendChild(card);
      });
    })
    .catch((err) => {
      empty.textContent = `Failed to load market index: ${err.message}`;
      empty.classList.remove("hidden");
    });

  filter?.addEventListener("input", applyMarketFilter);

  filter?.addEventListener("keydown", (e) => {
    const opts = [...(suggestions?.querySelectorAll(".market-suggestion") || [])];
    if (!opts.length || suggestions?.classList.contains("hidden")) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeSuggestion = Math.min(activeSuggestion + 1, opts.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeSuggestion = Math.max(activeSuggestion - 1, 0);
    } else if (e.key === "Enter" && activeSuggestion >= 0) {
      e.preventDefault();
      const url = opts[activeSuggestion]?.dataset.url;
      if (url) window.location.href = url;
      return;
    } else if (e.key === "Escape") {
      hideSuggestions();
      return;
    } else {
      return;
    }

    opts.forEach((el, idx) => {
      el.classList.toggle("is-active", idx === activeSuggestion);
    });
    if (activeSuggestion >= 0) {
      filter.setAttribute("aria-activedescendant", opts[activeSuggestion].id);
    }
  });

  filter?.addEventListener("blur", () => {
    setTimeout(hideSuggestions, 150);
  });
}

function statCard(label, value, hint = "") {
  return ui.statCard(label, value, hint);
}

function renderTable(headers, rows) {
  return ui.dataTable(headers, rows);
}

function badgeHtml(badges) {
  if (!badges?.length) return "";
  return badges.map((b) => `<span class="badge badge-muted">${b}</span>`).join(" ");
}

function initModelPage() {
  const cfg = window.MARKET_MODEL;
  if (!cfg) return;

  const searchLink = document.getElementById("search-link");
  searchLink.href = `/?make=${encodeURIComponent(cfg.make)}&model=${encodeURIComponent(cfg.model)}`;

  initClassicFilters(cfg);
  loadModelMarket(cfg);
}

function buildMarketParams() {
  const params = {};
  if (marketFilterState.period_months === "all") {
    params.period = "all";
  } else if (marketFilterState.period_months) {
    params.period_months = marketFilterState.period_months;
  }
  if (marketFilterState.min_price) params.min_price = marketFilterState.min_price;
  if (marketFilterState.max_price) params.max_price = marketFilterState.max_price;
  if (marketFilterState.max_mileage) params.max_mileage = marketFilterState.max_mileage;
  if (marketFilterState.country) params.country = marketFilterState.country;
  if (marketFilterState.status) params.status = marketFilterState.status;
  return params;
}

function countActiveFilters() {
  let n = 0;
  if (marketFilterState.period_months && marketFilterState.period_months !== 12) n += 1;
  if (marketFilterState.min_price || marketFilterState.max_price) n += 1;
  if (marketFilterState.max_mileage) n += 1;
  if (marketFilterState.country) n += 1;
  if (marketFilterState.status) n += 1;
  return n;
}

function updateFilterCount() {
  const el = document.getElementById("filter-count");
  if (!el) return;
  const n = countActiveFilters();
  el.textContent = n > 0 ? String(n) : "";
  el.dataset.zero = n === 0 ? "true" : "false";
}

function initClassicFilters(cfg) {
  const pills = document.getElementById("filter-pills");
  const countrySelect = document.getElementById("filter-country");

  pills?.addEventListener("click", (event) => {
    const btn = event.target.closest(".classic-pill");
    if (!btn) return;

    if (btn.dataset.filter === "period") {
      pills.querySelectorAll('[data-filter="period"]').forEach((p) => p.classList.remove("is-active"));
      btn.classList.add("is-active");
      marketFilterState.period_months =
        btn.dataset.value === "all" ? "all" : Number(btn.dataset.value);
      updateFilterCount();
      loadModelMarket(cfg);
      return;
    }

    if (btn.dataset.filter === "panel") {
      const panelId = `filter-panel-${btn.dataset.panel}`;
      document.querySelectorAll(".classic-market__filter-panel").forEach((panel) => {
        const isTarget = panel.id === panelId;
        panel.classList.toggle("hidden", !isTarget);
        panel.toggleAttribute("hidden", !isTarget);
      });
    }
  });

  document.querySelectorAll("[data-apply-filters]").forEach((btn) => {
    btn.addEventListener("click", () => {
      marketFilterState.min_price = document.getElementById("filter-min-price")?.value || "";
      marketFilterState.max_price = document.getElementById("filter-max-price")?.value || "";
      marketFilterState.max_mileage = document.getElementById("filter-max-mileage")?.value || "";
      marketFilterState.country = countrySelect?.value || "";
      marketFilterState.status = document.getElementById("filter-status")?.value || "";
      updateFilterCount();
      loadModelMarket(cfg);
    });
  });

  document.getElementById("market-tabs")?.addEventListener("click", (event) => {
    const tab = event.target.closest(".classic-tab");
    if (!tab) return;
    const name = tab.dataset.tab;
    document.querySelectorAll(".classic-tab").forEach((t) => {
      const active = t === tab;
      t.classList.toggle("is-active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    document.querySelectorAll("[role='tabpanel']").forEach((panel) => {
      const show = panel.id === `tab-${name}`;
      panel.classList.toggle("hidden", !show);
      panel.toggleAttribute("hidden", !show);
    });
  });
}

function loadModelMarket(cfg) {
  fetchModelMarket(cfg.make, cfg.model, buildMarketParams())
    .then((data) => renderModelMarket(cfg, data))
    .catch((err) => {
      document.getElementById("model-subtitle").textContent = `Error: ${err.message}`;
    });
}

function renderModelMarket(cfg, data) {
  if (!data) {
    document.getElementById("model-subtitle").textContent = "No listings found for this model.";
    return;
  }
  const s = data.summary;
  document.getElementById("model-subtitle").textContent =
    `${s.listings} listings · ${s.year_min || "?"}–${s.year_max || "?"} · ` +
    `${data.by_source.length} sources`;

  const analytics = data.sales_analytics || {};
  renderSalesKpis(analytics.kpis || {});
  populateCountryFilter(analytics.filters?.countries || []);
  renderSalesScatterChart(analytics.points || [], analytics.moving_average || []);
  renderMileageChart(analytics.points || []);
  renderYearClassicChart(data.by_year || []);

  document.getElementById("by-source-classic").innerHTML = renderTable(
    ["Source", "Listings", "Avg price"],
    data.by_source.map((r) => [r.source, r.listings, formatPrice(r.avg_price)])
  );
  document.getElementById("by-country-classic").innerHTML = renderTable(
    ["Region", "Listings", "Avg price"],
    data.by_country.map((r) => [r.country || "?", r.listings, formatPrice(r.avg_price)])
  );

  const vol = data.sales_volume || {};
  renderVolumeCharts(vol.internal || {});
  renderExternalVolume(vol.external || {}, cfg);

  document.getElementById("comps-table").innerHTML = renderTable(
    ["Title", "Year", "Price", "Source", "Region", "Δ"],
    data.comps.map((c) => [
      `<span title="${c.title || ""}">${c.title || "Untitled"}</span>`,
      c.year || "—",
      formatPrice(c.price),
      c.source,
      c.country || "—",
      c.price_delta != null && c.price_delta < 0
        ? `<span class="price-drop">↓ ${formatPrice(Math.abs(c.price_delta))}</span>`
        : "—",
    ])
  );
}

function renderSalesKpis(kpis) {
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  set("kpi-avg", formatPrice(kpis.avg_price));
  set("kpi-count", formatNum(kpis.sales_count ?? 0));
  set("kpi-volume", formatPrice(kpis.dollar_volume));
  set("kpi-low", formatPrice(kpis.lowest_sale));
  set("kpi-high", formatPrice(kpis.top_sale));
  set("kpi-recent", formatPrice(kpis.most_recent));
}

function populateCountryFilter(countries) {
  const select = document.getElementById("filter-country");
  if (!select) return;
  const current = marketFilterState.country;
  select.innerHTML =
    `<option value="">All regions</option>` +
    countries.map((c) => `<option value="${c}">${c}</option>`).join("");
  select.value = current;
}

function scatterDatasets(points) {
  return Object.entries(SALE_STATUS_META).map(([status, meta]) => ({
    type: "scatter",
    label: meta.label,
    data: points
      .filter((p) => p.status === status && p.price != null && p.date)
      .map((p) => ({ x: p.date, y: p.price, title: p.title, year: p.year })),
    backgroundColor: meta.color,
    borderColor: meta.color,
    pointRadius: 5,
    pointHoverRadius: 7,
    order: 1,
  }));
}

function renderSalesScatterChart(points, movingAverage) {
  const canvas = document.getElementById("sales-scatter-chart");
  if (!canvas || typeof Chart === "undefined") return;
  if (salesChart) salesChart.destroy();

  const datasets = scatterDatasets(points);
  if (movingAverage.length) {
    datasets.push({
      type: "line",
      label: "Average Sale (Moving Average)",
      data: movingAverage.map((r) => ({ x: r.date, y: r.avg_price })),
      borderColor: "#2563eb",
      backgroundColor: "rgba(37, 99, 235, 0.12)",
      borderWidth: 3,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.35,
      fill: false,
      order: 0,
    });
  }

  salesChart = new Chart(canvas, {
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "nearest", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label(ctx) {
              const raw = ctx.raw || {};
              const price = formatPrice(raw.y);
              const bits = [price];
              if (raw.year) bits.push(`Year ${raw.year}`);
              if (raw.title) bits.push(raw.title);
              return bits;
            },
          },
        },
      },
      scales: {
        x: {
          type: "time",
          time: { unit: "month", displayFormats: { month: "MMM" } },
          grid: { color: "rgba(148, 163, 184, 0.25)" },
          ticks: { color: "#6b7280", maxRotation: 0 },
        },
        y: {
          position: "right",
          grid: { color: "rgba(148, 163, 184, 0.25)" },
          ticks: {
            color: "#6b7280",
            callback: (v) => `$${Math.round(v / 1000)}k`,
          },
        },
      },
    },
  });
}

function renderMileageChart(points) {
  const canvas = document.getElementById("mileage-scatter-chart");
  if (!canvas || typeof Chart === "undefined") return;
  if (mileageChart) mileageChart.destroy();

  const withMileage = points.filter((p) => p.mileage != null && p.price != null);
  mileageChart = new Chart(canvas, {
    type: "scatter",
    data: {
      datasets: Object.entries(SALE_STATUS_META).map(([status, meta]) => ({
        label: meta.label,
        data: withMileage
          .filter((p) => p.status === status)
          .map((p) => ({ x: p.mileage, y: p.price })),
        backgroundColor: meta.color,
        pointRadius: 5,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
      scales: {
        x: {
          title: { display: true, text: "Odometer (mi)" },
          ticks: { callback: (v) => `${Math.round(v / 1000)}k` },
        },
        y: {
          position: "right",
          ticks: { callback: (v) => `$${Math.round(v / 1000)}k` },
        },
      },
    },
  });
}

function renderYearClassicChart(byYear) {
  const canvas = document.getElementById("year-chart-classic");
  if (!canvas || !byYear.length || typeof Chart === "undefined") return;
  if (yearClassicChart) yearClassicChart.destroy();
  const labels = byYear.map((r) => String(r.year)).reverse();
  const values = byYear.map((r) => r.avg_price).reverse();
  yearClassicChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Avg price",
          data: values,
          backgroundColor: "rgba(37, 99, 235, 0.55)",
          borderColor: "#2563eb",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          position: "right",
          ticks: { callback: (v) => `$${Math.round(v / 1000)}k` },
        },
      },
    },
  });
}


function renderVolumeCharts(internal) {
  const byYear = internal.inventory_by_year || [];
  const byMonth = internal.new_listings_by_month || [];

  const yearCanvas = document.getElementById("volume-year-chart");
  if (yearCanvas && byYear.length && typeof Chart !== "undefined") {
    new Chart(yearCanvas, {
      type: "bar",
      data: {
        labels: byYear.map((r) => String(r.year)),
        datasets: [
          {
            label: "Listings",
            data: byYear.map((r) => r.listings),
            backgroundColor: "rgba(255, 159, 64, 0.55)",
            borderColor: "rgba(255, 159, 64, 1)",
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  const monthCanvas = document.getElementById("volume-month-chart");
  if (monthCanvas && byMonth.length && typeof Chart !== "undefined") {
    new Chart(monthCanvas, {
      type: "line",
      data: {
        labels: byMonth.map((r) => r.month?.slice(0, 7) || "?"),
        datasets: [
          {
            label: "New listings",
            data: byMonth.map((r) => r.new_listings),
            borderColor: "rgba(155, 89, 255, 1)",
            backgroundColor: "rgba(155, 89, 255, 0.15)",
            fill: true,
            tension: 0.25,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }
}

function externalCard(title, body, link) {
  return `
    <article class="external-card">
      <h3>${title}</h3>
      ${body}
      ${link ? `<p class="hint"><a href="${link}" target="_blank" rel="noopener">Source ↗</a></p>` : ""}
    </article>`;
}

function renderExternalVolume(external, cfg) {
  const container = document.getElementById("external-volume");
  const sourcesEl = document.getElementById("external-sources");
  if (!container) return;

  const cards = [];

  if (external.production?.units_produced) {
    cards.push(
      externalCard(
        "Historical production",
        `<p class="stat-value">${formatNum(external.production.units_produced)} units</p>
         <p class="hint">${external.production.excerpt || external.production.title || ""}</p>`,
        external.production.url
      )
    );
  }

  if (external.epa?.year_count) {
    cards.push(
      externalCard(
        "US market presence (EPA)",
        `<p class="stat-value">${external.epa.year_count} model years</p>
         <p class="hint">${external.epa.years_on_file?.slice(0, 8).join(", ")}${external.epa.years_on_file?.length > 8 ? "…" : ""}</p>`,
        external.epa.url
      )
    );
  }

  if (external.brand_us_sales?.dealer_sales != null) {
    cards.push(
      externalCard(
        "US dealer sales (brand)",
        `<p class="stat-value">${formatNum(external.brand_us_sales.dealer_sales)} sold</p>
         <p class="hint">${external.brand_us_sales.brand} · ${external.brand_us_sales.region} · ${external.brand_us_sales.month?.slice(0, 7)}</p>`,
        external.brand_us_sales.url
      )
    );
  }

  if (external.model_regional_rank) {
    const rank = external.model_regional_rank;
    cards.push(
      externalCard(
        "Regional model rank",
        `<p class="stat-value">${rank.percent_of_top_sales != null ? `${Math.round(rank.percent_of_top_sales)}% of top seller` : "Ranked"}</p>
         <p class="hint">Last ~45 days · ${rank.region || "US region"}</p>`,
        rank.url
      )
    );
  }

  if (external.nhtsa?.match_count) {
    cards.push(
      externalCard(
        "NHTSA catalog",
        `<p class="stat-value">${external.nhtsa.match_count} variants</p>
         <p class="hint">${external.nhtsa.models_matched?.slice(0, 4).join(", ") || ""}</p>`,
        external.nhtsa.url
      )
    );
  }

  if (external.us_market_trend?.length) {
    const latest = external.us_market_trend[external.us_market_trend.length - 1];
    cards.push(
      externalCard(
        "US total vehicle sales",
        `<p class="stat-value">${latest.sales_saar_millions}M SAAR</p>
         <p class="hint">National market · ${latest.month?.slice(0, 7)} (FRED TOTALSA)</p>`,
        "https://fred.stlouisfed.org/series/TOTALSA"
      )
    );
    renderUsTrendChart(external.us_market_trend);
  }

  container.innerHTML = cards.length
    ? cards.join("")
    : `<p class="hint">No external volume data available for ${cfg.make} ${cfg.model}. Configure FRED_API_KEY or CIS credentials for richer data.</p>`;

  const fetched = (external.sources_fetched || []).join(", ");
  const skipped = (external.sources_skipped || [])
    .map((s) => `${s.source}: ${s.reason}`)
    .join(" · ");
  if (sourcesEl) {
    sourcesEl.textContent = [fetched && `Loaded: ${fetched}`, skipped && `Skipped: ${skipped}`]
      .filter(Boolean)
      .join(" · ");
  }
}

function renderUsTrendChart(trend) {
  let canvas = document.getElementById("us-trend-chart");
  if (!canvas) {
    const panel = document.querySelector(".external-volume-panel");
    if (!panel) return;
    const wrap = document.createElement("div");
    wrap.className = "chart-panel us-trend-wrap";
    wrap.innerHTML = `<h2>US vehicle sales trend</h2><canvas id="us-trend-chart" height="100"></canvas>`;
    panel.appendChild(wrap);
    canvas = document.getElementById("us-trend-chart");
  }
  if (!canvas || typeof Chart === "undefined") return;
  new Chart(canvas, {
    type: "line",
    data: {
      labels: trend.map((r) => r.month?.slice(0, 7)),
      datasets: [
        {
          label: "Sales (M SAAR)",
          data: trend.map((r) => r.sales_saar_millions),
          borderColor: "rgba(255, 99, 132, 1)",
          backgroundColor: "rgba(255, 99, 132, 0.12)",
          fill: true,
          tension: 0.25,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          ticks: {
            callback: (v) => `${v}M`,
          },
        },
      },
    },
  });
}

function renderYearChart(byYear) {
  const canvas = document.getElementById("year-chart");
  if (!canvas || !byYear.length || typeof Chart === "undefined") return;
  const labels = byYear.map((r) => String(r.year)).reverse();
  const values = byYear.map((r) => r.avg_price).reverse();
  new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Avg price",
          data: values,
          backgroundColor: "rgba(91, 156, 255, 0.55)",
          borderColor: "rgba(91, 156, 255, 1)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          ticks: {
            callback: (v) => `$${Math.round(v / 1000)}k`,
          },
        },
      },
    },
  });
}

function renderTrendChart(trend) {
  const canvas = document.getElementById("trend-chart");
  if (!canvas || !trend.length || typeof Chart === "undefined") return;
  new Chart(canvas, {
    type: "line",
    data: {
      labels: trend.map((r) => r.month?.slice(0, 7) || "?"),
      datasets: [
        {
          label: "Avg observed price",
          data: trend.map((r) => r.avg_price),
          borderColor: "rgba(62, 207, 142, 1)",
          backgroundColor: "rgba(62, 207, 142, 0.15)",
          fill: true,
          tension: 0.25,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          ticks: {
            callback: (v) => `$${Math.round(v / 1000)}k`,
          },
        },
      },
    },
  });
}

if (window.MARKET_INDEX) {
  initIndexPage();
} else if (window.MARKET_MODEL) {
  initModelPage();
}
