/**
 * Notification Rake — shared UI components & utilities (vanilla JS, no build step).
 * Load before page-specific scripts.
 */
(function (global) {
  const PROFILE_KEY = "rake_profile_id";

  function escapeHtml(text) {
    return String(text ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatPrice(value) {
    if (value == null || Number.isNaN(Number(value))) return "—";
    return `$${Math.round(Number(value)).toLocaleString()}`;
  }

  function formatNum(value) {
    if (value == null) return "—";
    return Number(value).toLocaleString();
  }

  function formatKm(meters) {
    if (meters == null) return "";
    return `${(Number(meters) / 1000).toFixed(1)} km`;
  }

  function formatWhen(iso) {
    if (!iso) return "—";
    return String(iso).slice(0, 16).replace("T", " ");
  }

  function badge(text, variant = "") {
    const cls = variant ? ` ui-badge ui-badge--${variant}` : " ui-badge";
    return `<span class="${cls.trim()}">${escapeHtml(text)}</span>`;
  }

  function badges(items, variant = "muted") {
    if (!items?.length) return "";
    return items.map((b) => badge(b, variant)).join(" ");
  }

  function statCard(label, value, hint = "") {
    return `
      <article class="ui-stat">
        <p class="ui-stat__label">${escapeHtml(label)}</p>
        <p class="ui-stat__value">${value}</p>
        ${hint ? `<p class="ui-stat__hint">${escapeHtml(hint)}</p>` : ""}
      </article>`;
  }

  function dataTable(headers, rows) {
    if (!rows?.length) return `<p class="ui-empty">No data</p>`;
    const head = headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("");
    const body = rows
      .map((cells) => `<tr>${cells.map((c) => `<td>${c}</td>`).join("")}</tr>`)
      .join("");
    return `<div class="ui-table-wrap"><table class="ui-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function listRow({ title, badges: badgeItems = [], meta = "", actions = "" }) {
    return `
      <div class="ui-list-row">
        <div class="ui-list-row__head">
          <strong>${escapeHtml(title)}</strong>
          ${badgeItems.map((b) => badge(b)).join(" ")}
        </div>
        ${meta ? `<div class="ui-list-row__meta">${meta}</div>` : ""}
        ${actions ? `<div class="action-row">${actions}</div>` : ""}
      </div>`;
  }

  function emptyState(message) {
    return `<p class="ui-empty">${escapeHtml(message)}</p>`;
  }

  function priceDropBadge(delta) {
    if (delta == null || delta >= 0) return "";
    return `<span class="price-drop">↓ ${formatPrice(Math.abs(delta))}</span>`;
  }

  function listingCardHtml(item, { thumbKey = "thumbnail_proxy" } = {}) {
    const src = item[thumbKey] || item.thumbnail_url;
    const makeModel = [item.make, item.model].filter(Boolean).join(" ");
    const thumb = src
      ? `<img class="ui-card__media" src="${escapeHtml(src)}" alt="" loading="lazy" />`
      : "";
    const layout = src ? "ui-card__row" : "ui-card__body";
    return `
      <article class="ui-card ui-card--interactive card clickable" data-id="${escapeHtml(item.id)}">
        <div class="${layout}">
          ${thumb}
          <div class="ui-card__body">
            <div class="ui-card__head">
              ${badge(item.source || "listing")}
              ${priceDropBadge(item.price_delta)}
              ${badges(item.import_badges)}
            </div>
            <h2 class="ui-card__title">${escapeHtml(item.title || "Untitled")}</h2>
            <div class="ui-card__price">${formatPrice(item.price)}</div>
            <div class="ui-card__meta">
              <span>${escapeHtml(makeModel || "Unknown")}</span>
              ${item.year ? `<span>Year ${item.year}</span>` : ""}
              ${item.meters != null ? `<span>${formatKm(item.meters)}</span>` : ""}
              ${item.country ? `<span>${escapeHtml(item.country)}</span>` : ""}
              ${item.price_events > 1 ? `<span>${item.price_events} price events</span>` : ""}
            </div>
          </div>
        </div>
      </article>`;
  }

  function mountListingCard(item, handlers = {}) {
    const wrap = document.createElement("div");
    wrap.innerHTML = listingCardHtml(item);
    const el = wrap.firstElementChild;
    if (handlers.onClick && el) {
      el.addEventListener("click", () => handlers.onClick(item.id, item));
    }
    if (handlers.onHover && el) {
      el.addEventListener("mouseenter", () => handlers.onHover(item.id, item));
    }
    return el;
  }

  function setStatus(el, message) {
    if (el) el.textContent = message ?? "";
  }

  async function ensureProfileId() {
    let id = localStorage.getItem(PROFILE_KEY);
    if (id) return id;
    const resp = await fetch("/api/profile", { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    id = data.profile_id;
    localStorage.setItem(PROFILE_KEY, id);
    return id;
  }

  function initMobileNav() {
    const toggle = document.querySelector("[data-nav-toggle]");
    const nav = document.querySelector(".topbar nav");
    if (!toggle || !nav) return;
    toggle.addEventListener("click", () => {
      nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", nav.classList.contains("is-open"));
    });
    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => nav.classList.remove("is-open"));
    });
  }

  global.Rake = {
    PROFILE_KEY,
    escapeHtml,
    format: { price: formatPrice, num: formatNum, km: formatKm, when: formatWhen },
    ui: {
      badge,
      badges,
      statCard,
      dataTable,
      listRow,
      emptyState,
      listingCardHtml,
      mountListingCard,
      priceDropBadge,
      setStatus,
    },
    profile: { ensureProfileId },
    initMobileNav,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMobileNav);
  } else {
    initMobileNav();
  }
})(window);
