/** Market data pages — index browse + per-model classic.com-style view */

const { format, ui } = window.Rake;
const formatPrice = format.price;
const formatNum = format.num;

async function fetchMarketIndex() {
  const resp = await fetch("/api/market/models");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

async function fetchModelMarket(make, model, params = {}) {
  const qs = new URLSearchParams(params);
  const resp = await fetch(
    `/api/market/model?make=${encodeURIComponent(make)}&model=${encodeURIComponent(model)}&${qs}`
  );
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

function renderIndexCard(item) {
  const article = document.createElement("article");
  article.className = "ui-card market-card";
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
  const countEl = document.getElementById("market-count");
  let items = [];

  fetchMarketIndex()
    .then((data) => {
      items = data.models || [];
      countEl.textContent = `${items.length} models indexed`;
      if (!items.length) {
        empty.classList.remove("hidden");
        return;
      }
      items.forEach((item) => grid.appendChild(renderIndexCard(item)));
    })
    .catch((err) => {
      empty.textContent = `Failed to load market index: ${err.message}`;
      empty.classList.remove("hidden");
    });

  filter?.addEventListener("input", () => {
    const q = filter.value.trim().toLowerCase();
    grid.querySelectorAll(".market-card").forEach((el) => {
      el.classList.toggle("hidden", q !== "" && !el.dataset.q.includes(q));
    });
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

  fetchModelMarket(cfg.make, cfg.model)
    .then((data) => {
      if (!data) {
        document.getElementById("model-subtitle").textContent = "No listings found for this model.";
        return;
      }
      const s = data.summary;
      document.getElementById("model-subtitle").textContent =
        `${s.listings} listings · ${s.year_min || "?"}–${s.year_max || "?"} · ` +
        `${data.by_source.length} sources`;

      document.getElementById("stat-cards").innerHTML = [
        statCard("Median price", formatPrice(s.median_price), "50th percentile"),
        statCard("Average", formatPrice(s.avg_price)),
        statCard("Range", `${formatPrice(s.min_price)} – ${formatPrice(s.max_price)}`),
        statCard("Inventory", formatNum(s.listings), `${s.priced} with price`),
        statCard("Avg mileage", s.avg_mileage ? `${formatNum(s.avg_mileage)} mi` : "—"),
      ].join("");

      const vol = data.sales_volume || {};
      renderVolumeCharts(vol.internal || {});
      renderExternalVolume(vol.external || {}, cfg);

      document.getElementById("by-source").innerHTML = renderTable(
        ["Source", "Listings", "Avg price"],
        data.by_source.map((r) => [r.source, r.listings, formatPrice(r.avg_price)])
      );

      document.getElementById("by-country").innerHTML = renderTable(
        ["Region", "Listings", "Avg price"],
        data.by_country.map((r) => [r.country || "?", r.listings, formatPrice(r.avg_price)])
      );

      document.getElementById("comps-table").innerHTML = renderTable(
        ["Title", "Year", "Price", "Source", "Region", "Δ"],
        data.comps.map((c) => [
          `<a href="/" onclick="event.preventDefault();">${c.title || "Untitled"}</a>`,
          c.year || "—",
          formatPrice(c.price),
          c.source,
          c.country || "—",
          c.price_delta != null && c.price_delta < 0
            ? `<span class="price-drop">↓ ${formatPrice(Math.abs(c.price_delta))}</span>`
            : "—",
        ])
      );

      renderYearChart(data.by_year);
      renderTrendChart(data.price_trend);
    })
    .catch((err) => {
      document.getElementById("model-subtitle").textContent = `Error: ${err.message}`;
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
