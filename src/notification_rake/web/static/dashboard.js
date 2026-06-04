/** Unified search dashboard — decoupled map viewport vs search radius, cached lazy load */

const { format, ui } = window.Rake;
const formatPrice = format.price;
const formatKm = format.km;

const feed = document.getElementById("feed");
const sentinel = document.getElementById("sentinel");
const stats = document.getElementById("stats");
const form = document.getElementById("search-form");
const sourceTabs = document.getElementById("source-tabs");
const marketSummary = document.getElementById("market-summary");
const resultsSection = document.getElementById("results-section");
const searchAreaBtn = document.getElementById("search-area-btn");
const saveSearchBtn = document.getElementById("save-search-btn");
const detailDialog = document.getElementById("detail-dialog");
const detailContent = document.getElementById("detail-content");
const viewButtons = document.querySelectorAll(".view-btn");

const DEFAULT = window.RAKE_DEFAULT || { lat: 37.7749, lon: -122.4194 };
const SAVED_KEY = "rake_saved_searches";
const PAGE_CACHE_TTL_MS = 5 * 60 * 1000;
const DETAIL_CACHE_TTL_MS = 10 * 60 * 1000;

let offset = 0;
let hasSearched = false;
const limit = 24;
let loading = false;
let done = false;
let total = 0;
let loadedCount = 0;
let map = null;
let radiusCircle = null;
let activeCardId = null;

/** Fixed anchor for API geo filter — only changes on Search or "Search this area". */
let searchCenter = { lat: DEFAULT.lat, lon: DEFAULT.lon };

/** Current search query key (filters + search center + radius). */
let activeSearchKey = "";

const apiCache = new Map();
const listingsPageCache = new Map();
const listingById = new Map();
const markerById = new Map();
const detailCache = new Map();

function badgeHtml(badges) {
  return ui.badges(badges);
}

function card(item) {
  return ui.mountListingCard(item, {
    onClick: (id) => openDetail(id),
    onHover: (id) => highlightMarker(id),
  });
}

function radiusMeters() {
  const fd = new FormData(form);
  const radiusKm = parseFloat(fd.get("radius_km") || "50");
  return Math.round(radiusKm * 1000);
}

function buildFilterParams(extra = {}) {
  const fd = new FormData(form);
  const params = new URLSearchParams({ limit, ...extra });
  for (const [k, v] of fd.entries()) {
    if (v !== "") params.set(k, v);
  }
  if (!fd.get("import_us")) params.delete("import_us");
  if (!fd.get("import_ca")) params.delete("import_ca");
  params.delete("radius_km");
  params.set("lat", String(searchCenter.lat));
  params.set("lon", String(searchCenter.lon));
  params.set("radius_m", String(radiusMeters()));
  return params;
}

function searchCacheKey(params) {
  const p = new URLSearchParams(params);
  p.delete("limit");
  p.delete("offset");
  return p.toString();
}

function setActiveCard(id) {
  activeCardId = id;
  feed.querySelectorAll(".ui-card, .card").forEach((el) => {
    el.classList.toggle("ui-card--active", el.dataset.id === id);
    el.classList.toggle("card-active", el.dataset.id === id);
  });
}

async function fetchJsonCached(url, { cacheMap, ttlMs, key }) {
  const now = Date.now();
  const hit = cacheMap.get(key);
  if (hit && now - hit.fetchedAt < ttlMs) {
    return hit.data;
  }
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = await resp.json();
  cacheMap.set(key, { fetchedAt: now, data });
  return data;
}

async function fetchListingsPage(params) {
  const key = searchCacheKey(params);
  const pageOffset = parseInt(params.get("offset") || "0", 10);
  const now = Date.now();
  let bucket = listingsPageCache.get(key);
  if (bucket && now - bucket.fetchedAt < PAGE_CACHE_TTL_MS) {
    const cached = bucket.pages.get(pageOffset);
    if (cached) return { data: cached, fromCache: true };
  }
  const resp = await fetch(`/api/listings?${params}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = await resp.json();
  if (!bucket) {
    bucket = { fetchedAt: now, pages: new Map(), total: data.total };
    listingsPageCache.set(key, bucket);
  }
  bucket.pages.set(pageOffset, data);
  bucket.total = data.total;
  bucket.fetchedAt = now;
  return { data, fromCache: false };
}

async function openDetail(id) {
  try {
    const d = await fetchJsonCached(`/api/listings/${id}`, {
      cacheMap: detailCache,
      ttlMs: DETAIL_CACHE_TTL_MS,
      key: id,
    });
    const history = (d.price_history || [])
      .map((h) => `<li>${h.recorded_at?.slice(0, 10) || "?"} — ${formatPrice(h.price)}</li>`)
      .join("");
    const badges = badgeHtml(d.badges);
    const gallery = (d.images || [])
      .map((img) => `<img class="detail-thumb" src="${img.proxy_url || img.url}" alt="" loading="lazy" />`)
      .join("");
    const outbound = d.outbound_url
      ? `<p><a href="${d.outbound_url}" target="_blank" rel="noopener">Open on ${d.source}</a></p>`
      : "";
    const auction = d.auction
      ? `<p class="meta">Auction: ${d.auction.auction_status || "?"} · ${d.auction.primary_damage || ""} · ${d.auction.title_type || ""}</p>`
      : "";
    const proxies = d.proxy_links && Object.keys(d.proxy_links).length
      ? `<p class="meta">${Object.entries(d.proxy_links).map(([k, u]) => `<a href="${u}" target="_blank" rel="noopener">${k}</a>`).join(" · ")}</p>`
      : "";
    detailContent.innerHTML = `
      <h2>${d.title || "Listing"}</h2>
      <div class="detail-badges">${badges}</div>
      ${gallery ? `<div class="detail-gallery">${gallery}</div>` : ""}
      <p class="price">${formatPrice(d.price)} · ${d.make || ""} ${d.model || ""} · ${d.year || ""}</p>
      <p class="meta">Source: ${d.source} · ID: ${d.source_listing_id}${d.country ? ` · ${d.country}` : ""}</p>
      ${auction}
      ${d.description ? `<p>${d.description}</p>` : ""}
      ${outbound}
      ${proxies}
      <h3>Price history</h3>
      <ul>${history || "<li>No history yet</li>"}</ul>
    `;
    detailDialog.showModal();
    if (d.lat != null && d.lon != null && map) {
      highlightMarker(id);
    }
  } catch (err) {
    console.error(err);
  }
}

function resetFeed() {
  feed.innerHTML = "";
  offset = 0;
  done = false;
  loadedCount = 0;
  listingById.clear();
}

function clearMarkers() {
  markerById.forEach((m) => m.remove());
  markerById.clear();
  activeCardId = null;
}

function rememberListings(items) {
  items.forEach((item) => listingById.set(item.id, item));
}

async function loadRoutes() {
  const routeSelect = document.getElementById("route");
  if (!routeSelect) return;
  try {
    const data = await fetchJsonCached("/api/routes", {
      cacheMap: apiCache,
      ttlMs: PAGE_CACHE_TTL_MS,
      key: "routes:catalog",
    });
    const current = routeSelect.value;
    routeSelect.innerHTML = '<option value="">All routes</option>';
    (data.routes || []).forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.slug;
      opt.textContent = `${r.label} (${r.listings})`;
      if (r.country) {
        opt.dataset.country = r.country;
      }
      routeSelect.appendChild(opt);
    });
    routeSelect.value = current;
  } catch (err) {
    console.error(err);
  }
}

async function loadFacets() {
  try {
    const params = buildFilterParams();
    params.delete("limit");
    params.delete("offset");
    const key = `facets:${searchCacheKey(params)}`;
    const data = await fetchJsonCached(`/api/facets?${params}`, {
      cacheMap: apiCache,
      ttlMs: PAGE_CACHE_TTL_MS,
      key,
    });
    const select = document.getElementById("source");
    const current = select.value;
    select.innerHTML = '<option value="">All sources</option>';
    (data.sources || []).forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.name;
      opt.textContent = `${s.name} (${s.count})`;
      select.appendChild(opt);
    });
    select.value = current;

    sourceTabs.innerHTML = "";
    const allBtn = document.createElement("button");
    allBtn.type = "button";
    allBtn.className = "tab active";
    allBtn.textContent = `All (${total || "…"})`;
    allBtn.onclick = () => {
      select.value = "";
      form.requestSubmit();
    };
    sourceTabs.appendChild(allBtn);
    (data.sources || []).forEach((s) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tab";
      btn.textContent = `${s.name} (${s.count})`;
      btn.onclick = () => {
        select.value = s.name;
        form.requestSubmit();
      };
      sourceTabs.appendChild(btn);
    });
  } catch (err) {
    console.error(err);
  }
}

async function loadMarketSummary() {
  try {
    const data = await fetchJsonCached("/api/market/summary", {
      cacheMap: apiCache,
      ttlMs: PAGE_CACHE_TTL_MS,
      key: "market:summary",
    });
    if (!data.by_source?.length) {
      marketSummary.textContent = "";
      return;
    }
    marketSummary.innerHTML = data.by_source
      .map(
        (s) =>
          `<span><strong>${s.source}</strong> ${s.listings} listings · avg ${formatPrice(s.avg_price)}</span>`
      )
      .join("");
  } catch (err) {
    marketSummary.textContent = "";
  }
}

function initMap() {
  if (map) return;
  map = L.map("map", { scrollWheelZoom: true }).setView([DEFAULT.lat, DEFAULT.lon], 10);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
  }).addTo(map);
  updateRadiusCircle();
  map.on("moveend", updateStatsLine);
  map.on("movestart", () => {
    if (hasSearched) searchAreaBtn?.classList.remove("hidden");
  });
}

function updateRadiusCircle() {
  if (!map) return;
  const radius = radiusMeters();
  const latlng = [searchCenter.lat, searchCenter.lon];
  if (radiusCircle) {
    radiusCircle.setLatLng(latlng);
    radiusCircle.setRadius(radius);
    return;
  }
  radiusCircle = L.circle(latlng, {
    radius,
    color: "#5b9cff",
    fillColor: "#5b9cff",
    fillOpacity: 0.08,
    weight: 1,
  }).addTo(map);
}

function searchCenterMarker() {
  if (!map || !window.L) return null;
  return L.circleMarker([searchCenter.lat, searchCenter.lon], {
    radius: 6,
    color: "#5b9cff",
    fillColor: "#5b9cff",
    fillOpacity: 1,
    weight: 2,
  });
}

let centerDot = null;

function updateSearchCenterMarker() {
  if (!map) return;
  if (centerDot) centerDot.remove();
  centerDot = searchCenterMarker();
  if (centerDot) centerDot.addTo(map);
}

function countVisibleOnMap() {
  if (!map) return 0;
  const bounds = map.getBounds();
  let n = 0;
  listingById.forEach((item) => {
    if (item.lat == null || item.lon == null) return;
    if (bounds.contains([item.lat, item.lon])) n += 1;
  });
  return n;
}

function updateStatsLine() {
  const visible = countVisibleOnMap();
  const mapped = [...listingById.values()].filter((i) => i.lat != null && i.lon != null).length;
  stats.textContent =
    `${total} in search · ${loadedCount} loaded · ${mapped} pinned · ${visible} in view`;
}

function highlightMarker(id) {
  setActiveCard(id);
  const marker = markerById.get(id);
  if (!marker) return;
  marker.setZIndexOffset(1000);
  marker.openPopup();
  markerById.forEach((m, mid) => {
    if (mid !== id) m.setZIndexOffset(0);
  });
}

function upsertMarker(item) {
  if (!map || item.lat == null || item.lon == null || markerById.has(item.id)) return;
  const m = L.marker([item.lat, item.lon]).addTo(map);
  m.bindPopup(`<strong>${item.title || "Listing"}</strong><br>${formatPrice(item.price)}`);
  m.on("click", () => {
    highlightMarker(item.id);
    openDetail(item.id);
  });
  markerById.set(item.id, m);
}

function fitMapToResults() {
  if (!map || !markerById.size) return;
  const group = L.featureGroup([...markerById.values()]);
  map.fitBounds(group.getBounds().pad(0.12));
}

function addMapMarkers(items, { fit = false } = {}) {
  items.forEach((item) => upsertMarker(item));
  if (fit && markerById.size) fitMapToResults();
}

async function loadMore() {
  if (loading || done) return;
  loading = true;
  sentinel.textContent = "Loading…";

  try {
    const params = buildFilterParams({ offset });
    const { data, fromCache } = await fetchListingsPage(params);
    total = data.total;
    activeSearchKey = searchCacheKey(params);

    if (!data.items.length) {
      done = true;
      sentinel.textContent = offset === 0 ? "No matches — widen filters or run pipeline." : "End";
      updateStatsLine();
      return;
    }

    const isFirstPage = offset === 0;
    data.items.forEach((item) => feed.appendChild(card(item)));
    rememberListings(data.items);
    addMapMarkers(data.items, { fit: isFirstPage && !fromCache });
    loadedCount += data.items.length;
    offset += data.items.length;
    done = offset >= data.total;
    sentinel.textContent = done
      ? "End of results"
      : fromCache
        ? "Loaded from cache · scroll for more"
        : "Scroll for more";
    if (isFirstPage) loadFacets();
    updateStatsLine();
  } catch (err) {
    sentinel.textContent = "Load failed.";
    console.error(err);
  } finally {
    loading = false;
  }
}

function setSearchCenterFromMap() {
  if (!map) return;
  const c = map.getCenter();
  searchCenter = { lat: c.lat, lon: c.lng };
}

function beginSearch({ recenterFromMap = false } = {}) {
  if (recenterFromMap || !hasSearched) {
    setSearchCenterFromMap();
  }
  hasSearched = true;
  searchAreaBtn?.classList.add("hidden");
  resetFeed();
  clearMarkers();
  updateRadiusCircle();
  updateSearchCenterMarker();
  loadMore();
}

function setViewMode(mode) {
  resultsSection.classList.remove("view-split", "view-list", "view-map");
  resultsSection.classList.add(`view-${mode}`);
  viewButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === mode);
  });
  if (map) setTimeout(() => map.invalidateSize(), 120);
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  beginSearch();
});

form.addEventListener("change", (e) => {
  if (e.target.name === "radius_km") {
    updateRadiusCircle();
  }
  if (e.target.name === "country" && e.target.value && map) {
    const opt = e.target.selectedOptions[0];
    const lat = parseFloat(opt.dataset.lat);
    const lon = parseFloat(opt.dataset.lon);
    if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
      map.setView([lat, lon], 8);
    }
  }
  if (e.target.name === "route") {
    const sourceSelect = document.getElementById("source");
    if (sourceSelect) sourceSelect.value = "";
    const opt = e.target.selectedOptions[0];
    const countrySelect = document.getElementById("country");
    if (countrySelect && opt?.dataset.country) {
      countrySelect.value = opt.dataset.country;
      countrySelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }
});

viewButtons.forEach((btn) => {
  btn.addEventListener("click", () => setViewMode(btn.dataset.view));
});

searchAreaBtn?.addEventListener("click", () => {
  beginSearch({ recenterFromMap: true });
});

saveSearchBtn?.addEventListener("click", () => {
  const params = Object.fromEntries(buildFilterParams().entries());
  const saved = JSON.parse(localStorage.getItem(SAVED_KEY) || "[]");
  const name = params.q || params.make || "Saved search";
  saved.unshift({ name, params, saved_at: new Date().toISOString() });
  localStorage.setItem(SAVED_KEY, JSON.stringify(saved.slice(0, 20)));
  stats.textContent = `Saved "${name}" locally (${saved.length} total)`;
});

const observer = new IntersectionObserver((entries) => {
  if (entries.some((e) => e.isIntersecting)) loadMore();
}, { rootMargin: "200px" });

observer.observe(sentinel);

initMap();
updateSearchCenterMarker();
loadRoutes();
loadMarketSummary();
beginSearch();
