"use strict";

// Refresh bot connection status badge
async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const j = await res.json();
    const el = document.getElementById("bot-status");
    if (j.bot_connected) {
      el.innerHTML = "Bot status: <strong class=\"ok\">connected</strong>";
    } else {
      el.innerHTML = "Bot status: <strong class=\"bad\">not connected</strong>";
    }
  } catch (e) {
    document.getElementById("bot-status").textContent = "Bot status: error";
  }
}

// Load redacted config values into form fields
async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const j = await res.json();
    ["DISCORD_TOKEN", "JELLYFIN_URL", "JELLYFIN_API_KEY"].forEach(k => {
      const el = document.getElementById(k);
      if (el) el.value = j[k] || "";
    });
  } catch (e) {
    // Silent: unauthorized or network errors
  }
}

// Handle config form submission
document.getElementById("config-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const res = await fetch("/api/config", { method: "POST", body: fd });
  const j = await res.json();
  document.getElementById("save-result").textContent =
    j.updated?.length ? "Saved." : "No changes.";
  refreshStatus();
});

// Handle test notification form
document.getElementById("notify-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const payload = {
    channel_id: document.getElementById("channel_id").value,
    message: document.getElementById("message").value
  };
  const res = await fetch("/api/notify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const j = await res.json();
  document.getElementById("notify-result").textContent =
    j.ok ? "Sent (stub)." : ("Error: " + (j.error || "unknown"));
});

// Jellyfin auth test
document.getElementById("jellyfin-test-btn").addEventListener("click", async () => {
  const btn = document.getElementById("jellyfin-test-btn");
  const out = document.getElementById("jellyfin-test-result");
  const url = document.getElementById("JELLYFIN_URL").value.trim();
  const apiKey = document.getElementById("JELLYFIN_API_KEY").value.trim();

  out.textContent = "";
  out.className = "";
  btn.disabled = true;

  try {
    const res = await fetch("/api/jellyfin/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, api_key: apiKey })
    });
    const j = await res.json();
    if (j.ok) {
      const name = j.user?.name || "unknown";
      out.textContent = `OK: authenticated as ${name}`;
      out.className = "ok";
    } else {
      out.textContent = `Error: ${j.error || "unknown"}`;
      out.className = "bad";
    }
  } catch (e) {
    out.textContent = "Error: network or server issue";
    out.className = "bad";
  } finally {
    btn.disabled = false;
  }
});

// Initial load
loadConfig();
refreshStatus();
