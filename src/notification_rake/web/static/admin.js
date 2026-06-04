/** Admin console — live status refresh and async actions. */

const refreshBtn = document.getElementById("refresh-btn");
const actionResult = document.getElementById("action-result");

function statusClass(status) {
  return `status-${status}`;
}

function renderServices(services) {
  const grid = document.getElementById("service-grid");
  if (!grid) return;
  grid.innerHTML = services
    .map(
      (svc) => `
    <article class="service-card ${statusClass(svc.status)}" data-service="${svc.key}">
      <div class="service-head">
        <span class="status-dot"></span>
        <h2>${svc.label}</h2>
      </div>
      <p class="service-detail">${svc.detail}</p>
      <p class="service-url"><code>${svc.url}</code></p>
      ${
        svc.console_url
          ? `<a class="btn-secondary" href="${svc.console_url}" target="_blank" rel="noopener">Open console</a>`
          : ""
      }
    </article>`
    )
    .join("");
}

function renderLayers(layers) {
  const dl = document.getElementById("layer-stats");
  if (!dl) return;
  const entries = [
    ["Search listings", layers.search_listings],
    ["Raw listings", layers.raw_listings],
    ["Catalog models", layers.catalog_models],
    ["Job runs", layers.job_runs],
    ["Sources", layers.sources],
  ];
  dl.innerHTML = entries
    .map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`)
    .join("");
}

async function refreshOverview() {
  refreshBtn.disabled = true;
  refreshBtn.textContent = "Refreshing…";
  try {
    const resp = await fetch("/admin/api/overview");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    renderServices(data.services);
    renderLayers(data.layers);
  } catch (err) {
    console.error(err);
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.textContent = "Refresh status";
  }
}

document.querySelectorAll(".action-form").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    if (!actionResult) return;
    event.preventDefault();
    const action = form.querySelector("[data-action]")?.dataset.action;
    actionResult.hidden = false;
    actionResult.textContent = `Running ${action}…`;
    actionResult.className = "action-result";
    try {
      const resp = await fetch(`/admin/api/actions/${action}`, { method: "POST" });
      const data = await resp.json();
      actionResult.textContent = data.message;
      actionResult.classList.add(data.ok ? "flash-ok" : "flash-err");
      await refreshOverview();
    } catch (err) {
      actionResult.textContent = String(err);
      actionResult.classList.add("flash-err");
    }
  });
});

refreshBtn?.addEventListener("click", refreshOverview);
setInterval(refreshOverview, 60000);
