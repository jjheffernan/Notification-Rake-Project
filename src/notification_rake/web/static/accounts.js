/** Connected accounts page — profile-scoped marketplace connectors */

const { ui, profile, escapeHtml, format } = window.Rake;

const statusEl = document.getElementById("accounts-status");
const accountForm = document.getElementById("account-form");
const accountsList = document.getElementById("accounts-list");
const syncAccountsBtn = document.getElementById("sync-accounts-btn");

async function loadAccounts() {
  if (!accountsList) return;
  try {
    const profileId = await profile.ensureProfileId();
    const resp = await fetch(`/api/accounts?profile_id=${encodeURIComponent(profileId)}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const rows = data.accounts || [];
    accountsList.innerHTML = rows.length
      ? rows
          .map((a) =>
            ui.listRow({
              title: a.label,
              badges: [a.provider],
              meta: `${a.listings_synced ?? 0} synced · ${escapeHtml(a.last_status || "never synced")}${
                a.last_sync_at ? ` · ${format.when(a.last_sync_at)}` : ""
              }`,
            })
          )
          .join("")
      : ui.emptyState("No accounts connected yet. Add one using the form.");
    ui.setStatus(statusEl, `${rows.length} connected account${rows.length === 1 ? "" : "s"}`);
  } catch (err) {
    ui.setStatus(statusEl, `Failed to load accounts: ${err.message}`);
  }
}

accountForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const profileId = await profile.ensureProfileId();
    const provider = document.getElementById("account-provider").value;
    const label = document.getElementById("account-label").value || provider;
    let config = {};
    const raw = document.getElementById("account-config").value.trim();
    if (raw) {
      try {
        config = JSON.parse(raw);
      } catch {
        ui.setStatus(statusEl, "Invalid JSON in account config");
        return;
      }
    }
    ui.setStatus(statusEl, "Connecting…");
    const resp = await fetch("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: profileId, provider, label, config }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.description || err.error || `HTTP ${resp.status}`);
    }
    accountForm.reset();
    ui.setStatus(statusEl, `Connected ${provider}`);
    loadAccounts();
  } catch (err) {
    ui.setStatus(statusEl, err.message);
  }
});

syncAccountsBtn?.addEventListener("click", async () => {
  try {
    const profileId = await profile.ensureProfileId();
    ui.setStatus(statusEl, "Syncing connected accounts…");
    syncAccountsBtn.disabled = true;
    const resp = await fetch("/api/accounts/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: profileId }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    ui.setStatus(
      statusEl,
      `Synced ${data.upserted || 0} listings from ${data.connected || 0} account(s)`
    );
    loadAccounts();
  } catch (err) {
    ui.setStatus(statusEl, `Sync failed: ${err.message}`);
  } finally {
    syncAccountsBtn.disabled = false;
  }
});

loadAccounts();
