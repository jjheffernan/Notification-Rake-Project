/** Buyer profile sign-in — separate from operator /admin login */

const { profile } = window.Rake;

function showStatus(message, ok = true) {
  const el = document.getElementById("signin-status");
  if (!el) return;
  el.textContent = message;
  el.classList.toggle("hidden", !message);
  el.classList.toggle("signin-status--ok", ok);
  el.classList.toggle("signin-status--error", !ok);
}

async function redirectIfSignedIn() {
  const id = profile.getProfileId();
  if (!id) return;
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next") || "/accounts";
  window.location.href = next;
}

document.getElementById("signin-create-btn")?.addEventListener("click", async () => {
  try {
    const id = await profile.createProfile();
    showStatus(`Profile created. Save this ID: ${id}`);
    setTimeout(() => {
      window.location.href = "/accounts";
    }, 1200);
  } catch (err) {
    showStatus(err.message, false);
  }
});

document.getElementById("signin-restore-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("profile-id-input");
  const raw = input?.value?.trim() || "";
  if (!profile.setProfileId(raw)) {
    showStatus("Enter a valid profile UUID.", false);
    return;
  }
  showStatus("Profile restored.");
  setTimeout(() => {
    const params = new URLSearchParams(window.location.search);
    window.location.href = params.get("next") || "/accounts";
  }, 600);
});

redirectIfSignedIn();
