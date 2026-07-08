/**
 * Notification Rake — shared UI components & utilities (vanilla JS, no build step).
 * Load before page-specific scripts.
 */
(function (global) {
  const PROFILE_KEY = "rake_profile_id";
  const DISTANCE_UNIT_KEY = "rake_distance_unit";
  const METERS_PER_KM = 1000;
  const METERS_PER_MI = 1609.344;

  function getDistanceUnit() {
    const stored = localStorage.getItem(DISTANCE_UNIT_KEY);
    return stored === "mi" ? "mi" : "km";
  }

  function setDistanceUnit(unit) {
    const prev = getDistanceUnit();
    const next = unit === "mi" ? "mi" : "km";
    if (prev === next) return next;
    localStorage.setItem(DISTANCE_UNIT_KEY, next);
    syncDistanceUnitToggle(next);
    refreshDistanceLabels();
    document.dispatchEvent(
      new CustomEvent("rake:distance-unit", { detail: { unit: next, prev } }),
    );
    return next;
  }

  function displayToMeters(value, unit = getDistanceUnit()) {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return null;
    return Math.round(n * (unit === "mi" ? METERS_PER_MI : METERS_PER_KM));
  }

  function formatDistance(meters) {
    if (meters == null) return "";
    const n = Number(meters);
    if (getDistanceUnit() === "mi") {
      return `${(n / METERS_PER_MI).toFixed(1)} mi`;
    }
    return `${(n / METERS_PER_KM).toFixed(1)} km`;
  }

  function formatKm(meters) {
    return formatDistance(meters);
  }

  function refreshDistanceLabels(root = document) {
    root.querySelectorAll("[data-distance-m]").forEach((el) => {
      const m = Number(el.dataset.distanceM);
      if (Number.isFinite(m)) el.textContent = formatDistance(m);
    });
  }

  function syncDistanceUnitToggle(unit = getDistanceUnit()) {
    document.querySelectorAll("[data-distance-unit]").forEach((btn) => {
      const active = btn.dataset.distanceUnit === unit;
      btn.classList.toggle("active", active);
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function initDistanceUnitToggle() {
    const unit = getDistanceUnit();
    syncDistanceUnitToggle(unit);
    document.querySelectorAll("[data-distance-unit]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.distanceUnit === getDistanceUnit()) return;
        setDistanceUnit(btn.dataset.distanceUnit);
      });
    });
  }

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
              ${item.meters != null ? `<span data-distance-m="${item.meters}">${formatDistance(item.meters)}</span>` : ""}
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
    const id = getProfileId();
    if (id) return id;
    return createProfile();
  }

  function getProfileId() {
    return localStorage.getItem(PROFILE_KEY);
  }

  function isValidProfileId(value) {
    if (!value) return false;
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      String(value).trim()
    );
  }

  function setProfileId(id) {
    const trimmed = String(id || "").trim();
    if (!isValidProfileId(trimmed)) return false;
    localStorage.setItem(PROFILE_KEY, trimmed);
    updateSignedInNav();
    return true;
  }

  async function createProfile() {
    const resp = await fetch("/api/profile", { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const id = data.profile_id;
    localStorage.setItem(PROFILE_KEY, id);
    updateSignedInNav();
    return id;
  }

  function clearProfile() {
    localStorage.removeItem(PROFILE_KEY);
    updateSignedInNav();
  }

  function requireProfileId() {
    const id = getProfileId();
    if (id) return id;
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/signin?next=${next}`;
    return null;
  }

  function updateSignedInNav() {
    const signedIn = Boolean(getProfileId());
    document.querySelectorAll("[data-nav-signin]").forEach((el) => {
      el.classList.toggle("hidden", signedIn);
    });
    document.querySelectorAll("[data-nav-signed-in]").forEach((el) => {
      el.classList.toggle("hidden", !signedIn);
    });
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
    format: { price: formatPrice, num: formatNum, km: formatKm, distance: formatDistance, when: formatWhen },
    units: {
      getDistanceUnit,
      setDistanceUnit,
      displayToMeters,
      refreshDistanceLabels,
      METERS_PER_KM,
      METERS_PER_MI,
    },
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
    profile: {
      ensureProfileId,
      getProfileId,
      setProfileId,
      createProfile,
      clearProfile,
      requireProfileId,
      isValidProfileId,
    },
    initMobileNav,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      initMobileNav();
      initDistanceUnitToggle();
      updateSignedInNav();
    });
  } else {
    initMobileNav();
    initDistanceUnitToggle();
    updateSignedInNav();
  }
})(window);
