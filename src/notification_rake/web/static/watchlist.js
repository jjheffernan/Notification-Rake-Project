/** Watchlist — scheduled vehicle searches + batch run */

const { ui, profile, escapeHtml, format } = window.Rake;

const statusEl = document.getElementById("watchlist-status");
const itemsEl = document.getElementById("watchlist-items");
const form = document.getElementById("watchlist-form");
const runDueBtn = document.getElementById("run-due-btn");
const runAllBtn = document.getElementById("run-all-btn");
const routeSelect = document.getElementById("watch-route");
const ingestSelect = document.getElementById("watch-ingest-routes");

function searchSummary(q) {
  const parts = [q.make, q.model, q.q].filter(Boolean);
  return parts.join(" · ") || "Any";
}

async function loadRoutes() {
  const resp = await fetch("/api/routes");
  if (!resp.ok) return;
  const data = await resp.json();
  const routes = data.routes || [];
  if (routeSelect) {
    routeSelect.innerHTML = '<option value="">All routes</option>';
    routes.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.slug;
      opt.textContent = `${r.label} (${r.listings})`;
      routeSelect.appendChild(opt);
    });
  }
  if (ingestSelect) {
    ingestSelect.innerHTML = "";
    routes.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.slug;
      opt.textContent = r.label;
      opt.selected = true;
      ingestSelect.appendChild(opt);
    });
  }
}

async function loadWatchlist() {
  const profileId = await profile.ensureProfileId();
  const resp = await fetch(
    `/api/scheduled-searches?profile_id=${encodeURIComponent(profileId)}`
  );
  if (!resp.ok) {
    ui.setStatus(statusEl, "Failed to load watchlist");
    return;
  }
  const data = await resp.json();
  const items = data.searches || [];
  if (!items.length) {
    itemsEl.innerHTML = ui.emptyState("No scheduled searches yet.");
    ui.setStatus(statusEl, "0 scheduled searches");
    return;
  }
  itemsEl.innerHTML = items
    .map(
      (s) => `
    <div class="ui-list-row watchlist-row" data-id="${s.id}">
      <div class="ui-list-row__head watchlist-row-head">
        <strong>${escapeHtml(s.name)}</strong>
        ${ui.badge(s.enabled ? "Active" : "Paused", s.enabled ? "" : "muted")}
      </div>
      <div class="ui-list-row__meta watchlist-row-meta">
        ${escapeHtml(searchSummary(s.query_json))}
        · every ${Math.round(s.interval_minutes / 60)}h
        · ${s.last_match_count ?? "—"} matches
        ${s.last_new_count ? ` · <span class="price-drop">${s.last_new_count} new</span>` : ""}
      </div>
      <div class="ui-list-row__meta watchlist-row-meta">
        Last: ${format.when(s.last_run_at)} · Next: ${format.when(s.next_run_at)}
      </div>
      <div class="action-row watchlist-actions">
        <a class="ui-btn ui-btn--secondary" href="/?make=${encodeURIComponent(s.query_json.make || "")}&model=${encodeURIComponent(s.query_json.model || "")}&route=${encodeURIComponent(s.query_json.route || "")}">Open search</a>
        <button type="button" class="ui-btn ui-btn--secondary run-one" data-id="${s.id}">Run now</button>
        <button type="button" class="ui-btn ui-btn--secondary delete-one" data-id="${s.id}">Delete</button>
      </div>
    </div>`
    )
    .join("");
  ui.setStatus(statusEl, `${items.length} scheduled search${items.length === 1 ? "" : "es"}`);
  itemsEl.querySelectorAll(".run-one").forEach((btn) => {
    btn.addEventListener("click", () => runBatch({ searchId: btn.dataset.id }));
  });
  itemsEl.querySelectorAll(".delete-one").forEach((btn) => {
    btn.addEventListener("click", () => deleteSearch(btn.dataset.id));
  });
}

async function deleteSearch(id) {
  const profileId = await profile.ensureProfileId();
  await fetch(`/api/scheduled-searches/${id}?profile_id=${encodeURIComponent(profileId)}`, {
    method: "DELETE",
  });
  loadWatchlist();
}

async function runBatch({ force = false, searchId = null } = {}) {
  const profileId = await profile.ensureProfileId();
  ui.setStatus(statusEl, force ? "Running all searches…" : "Running due searches…");
  runDueBtn.disabled = true;
  runAllBtn.disabled = true;
  try {
    const resp = await fetch("/api/scheduled-searches/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: profileId, force, search_id: searchId }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.description || data.error || "Run failed");
    ui.setStatus(
      statusEl,
      `Batch complete: ${data.searches_run} searches, ${data.total_new_matches} new matches, ` +
        `${data.ingest_upserted} listings refreshed`
    );
    loadWatchlist();
  } catch (err) {
    ui.setStatus(statusEl, err.message);
  } finally {
    runDueBtn.disabled = false;
    runAllBtn.disabled = false;
  }
}

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const profileId = await profile.ensureProfileId();
  const fd = new FormData(form);
  const ingestRoutes = [...ingestSelect.selectedOptions].map((o) => o.value);
  const query = {
    make: fd.get("make") || null,
    model: fd.get("model") || null,
    q: fd.get("q") || null,
    route: fd.get("route") || null,
  };
  Object.keys(query).forEach((k) => {
    if (!query[k]) delete query[k];
  });
  const hours = parseInt(fd.get("interval_hours") || "6", 10);
  const body = {
    profile_id: profileId,
    name: fd.get("name"),
    query_json: query,
    interval_minutes: Math.max(15, hours * 60),
    ingest_routes: ingestRoutes,
    alert_enabled: fd.get("alert_enabled") === "on",
    enabled: fd.get("enabled") === "on",
  };
  const resp = await fetch("/api/scheduled-searches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (resp.ok) {
    form.reset();
    if (ingestSelect) {
      [...ingestSelect.options].forEach((o) => {
        o.selected = true;
      });
    }
    document.getElementById("watch-interval").value = "6";
    document.getElementById("watch-alert").checked = true;
    document.getElementById("watch-enabled").checked = true;
    loadWatchlist();
    ui.setStatus(statusEl, "Scheduled search saved");
  } else {
    ui.setStatus(statusEl, "Failed to save search");
  }
});

runDueBtn?.addEventListener("click", () => runBatch({ force: false }));
runAllBtn?.addEventListener("click", () => runBatch({ force: true }));

loadRoutes().then(loadWatchlist);
