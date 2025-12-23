(function () {
  let idCounter = 0;
  const toasts = new Map();

  function getOrCreateContainer() {
    let c = document.getElementById("toast-container");
    if (!c) {
      c = document.createElement("div");
      c.id = "toast-container";
      c.className = "toast-container";
      c.setAttribute("role", "status");
      document.body.appendChild(c);
    }
    return c;
  }

  function makeId() {
    idCounter += 1;
    return `toast-${Date.now()}-${idCounter}`;
  }

  function showToast(message, kind = "success", ttl = 5000) {
    const container = getOrCreateContainer();
    if (!container) return null;

    const id = makeId();
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.setAttribute("role", "status");
    el.dataset.toastId = id;
    el.textContent = message;

    container.appendChild(el);

    let timeoutId = null;
    if (typeof ttl === "number" && ttl > 0) {
      timeoutId = setTimeout(() => removeToast(id), ttl);
    }

    toasts.set(id, { el, timeoutId });
    return id;
  }

  function updateToast(id, message, kind) {
    const entry = toasts.get(id);
    if (!entry) return false;
    if (typeof message === "string") entry.el.textContent = message;
    if (typeof kind === "string") {
      entry.el.className = `toast ${kind}`;
    }
    return true;
  }

  function removeToast(id) {
    const entry = toasts.get(id);
    if (!entry) return false;
    if (entry.timeoutId) {
      clearTimeout(entry.timeoutId);
    }
    try {
      entry.el.remove();
    } catch (e) {}
    toasts.delete(id);
    return true;
  }

  window.Toast = {
    showToast,
    updateToast,
    removeToast,
  };
})();
