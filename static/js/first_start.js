(function () {
  function showToast(message, kind = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.setAttribute("role", "status");
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 5000);
  }

  async function postJson(path, body, method = "POST") {
    try {
      const resp = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return await resp.json();
    } catch (err) {
      return { ok: false, status: 0, message: err?.message || "Network error" };
    }
  }

  function maskKey(key) {
    if (!key) return "";
    if (key.length <= 8) return "•".repeat(Math.max(4, key.length));
    return `${key.slice(0, 4)}…${key.slice(-4)}`;
  }

  // Elements
  const hostInput = document.getElementById("jf-first-host");
  const portInput = document.getElementById("jf-first-port");
  const keyInput = document.getElementById("jf-first-api-key");
  const testBtn = document.getElementById("jf-first-test-btn");
  const addBtn = document.getElementById("jf-first-add-btn");
  const form = document.getElementById("first-start-form");
  const noServerDiv = document.getElementById("jf-first-no-server");
  const serverAddedDiv = document.getElementById("jf-first-server-added");
  const serverDisplay = document.getElementById("jf-first-server-display");

  function displayServer(host, port, apiKey) {
    if (!serverDisplay) return;
    serverDisplay.innerHTML = `
      <div class="jf-server-host">${host}:${port}</div>
      <div class="jf-server-key">API Key: ${maskKey(apiKey)}</div>
    `;
  }

  if (testBtn) {
    testBtn.addEventListener("click", async () => {
      const host = (hostInput?.value || "").trim();
      const port = (portInput?.value || "").trim();
      const apiKey = (keyInput?.value || "").trim();

      if (!host || !port || !apiKey) {
        showToast("Please fill in host, port and API key", "error");
        return;
      }

      testBtn.disabled = true;
      const original = testBtn.textContent;
      testBtn.textContent = "Testing...";

      const result = await postJson(
        "/api/test-connection-with-credentials",
        { jf_host: host, jf_port: port, jf_api_key: apiKey },
        "POST"
      );

      if (result && result.ok) {
        showToast("Connection successful", "success");
      } else {
        const msg = result?.message || `Failed (status: ${result?.status ?? "n/a"})`;
        showToast(msg, "error");
      }

      testBtn.textContent = original;
      setTimeout(() => (testBtn.disabled = false), 5000);
    });
  }

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const host = (hostInput?.value || "").trim();
      const port = (portInput?.value || "").trim();
      const apiKey = (keyInput?.value || "").trim();
      const hourFormat = (document.getElementById("hour-format")?.value || "24")
      const language = (document.getElementById("language")?.value || "en");

      if (!host || !port || !apiKey) {
        showToast("Please fill in host, port and API key", "error");
        return;
      }

      addBtn.disabled = true;
      const original = addBtn.textContent;
      addBtn.textContent = "Saving...";

      const resp = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jf_host: host,
          jf_port: port,
          jf_api_key: apiKey,
          hour_format: hourFormat,
          language: language
        }),
      });

      if (!resp.ok) {
        showToast("Failed to save settings", "error");
        addBtn.textContent = original;
        addBtn.disabled = false;
        return;
      }

      try {
        const data = await resp.json();
        showToast("Server added successfully", "success");
        if (noServerDiv) noServerDiv.hidden = true;
        if (serverAddedDiv) serverAddedDiv.hidden = false;
        displayServer(host, port, apiKey);
        window.location.href = "/";
      } catch (err) {
        showToast("Saved but failed to parse response", "error");
      }

      addBtn.textContent = original;
      addBtn.disabled = false;
    });
  }
})();