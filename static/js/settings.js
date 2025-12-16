const jf_helpers = (function () {
  function getToastContainer() {
    return document.getElementById('toast-container');
  }

  function showToast(message, kind = 'success', ttl = 5000) {
    const container = getToastContainer();
    if (!container) return;
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.setAttribute('role', 'status');
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), ttl);
  }

  async function fetchJson(path, opts = {}) {
    try {
      const resp = await fetch(path, opts.method ? opts : { method: 'GET' });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        return { ok: false, status: resp.status, message: data?.message || 'HTTP error', data: null };
      }
      if (data && typeof data === 'object' && ('ok' in data || 'data' in data)) {
        return data;
      }
      return { ok: true, status: resp.status, data };
    } catch (err) {
      return { ok: false, status: 0, message: err?.message || 'Network error', data: null };
    }
  }

  async function postJson(path, body, method = 'POST') {
    try {
      const resp = await fetch(path, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        return { ok: false, status: resp.status, message: data?.message || 'HTTP error', data: null };
      }
      if (data && typeof data === 'object' && ('ok' in data || 'data' in data)) {
        return data;
      }
      return { ok: true, status: resp.status, data };
    } catch (err) {
      return { ok: false, status: 0, message: err?.message || 'Network error', data: null };
    }
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  function humanDuration(ms) {
    if (!ms || ms <= 0) return '0s';
    let s = Math.floor(ms / 1000);
    const h = Math.floor(s / 3600);
    s = s % 3600;
    const m = Math.floor(s / 60);
    const sec = s % 60;
    if (h) return `${h}h ${m}m`;
    if (m) return `${m}m ${sec}s`;
    return `${sec}s`;
  }

  function humanBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
  }

  function humanTime(seconds) {
    if (!seconds || seconds === 0) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return h ? `${h}h ${m}m` : m ? `${m}m ${s}s` : `${s}s`;
  }

  function maskKey(key) {
    if (!key) return '';
    if (key.length <= 8) return '•'.repeat(Math.max(4, key.length));
    return `${key.slice(0, 4)}…${key.slice(-4)}`;
  }

  return {
    showToast,
    fetchJson,
    postJson,
    escapeHtml,
    humanDuration,
    humanBytes,
    humanTime,
    maskKey,
  };
}());

function showToast(message, kind = 'success') { return jf_helpers.showToast(message, kind); }
async function fetchJson(path) { return jf_helpers.fetchJson(path); }
async function postJson(path, body, method = 'POST') { return jf_helpers.postJson(path, body, method); }
function escapeHtml(s) { return jf_helpers.escapeHtml(s); }
function humanDuration(ms) { return jf_helpers.humanDuration(ms); }
function humanBytes(bytes) { return jf_helpers.humanBytes(bytes); }
function humanTime(seconds) { return jf_helpers.humanTime(seconds); }
function maskKey(key) { return jf_helpers.maskKey(key); }

(function () {
  const tabs = Array.from(document.querySelectorAll('.settings-tab'));
  const panels = Array.from(
    document.querySelectorAll('.settings-content[role="tabpanel"]')
  );

  function activate(id) {
    tabs.forEach(t => {
      const isActive = t.getAttribute('href') === `#${id}`;
      t.classList.toggle('active', isActive);
      t.setAttribute('aria-selected', String(isActive));
      t.setAttribute('tabindex', isActive ? '0' : '-1');
    });
    panels.forEach(p => {
      p.hidden = p.id !== id;
    });
  }

  function fromHash() {
    const id = (location.hash || '#general').slice(1);
    const known = panels.some(p => p.id === id);
    activate(known ? id : 'general');
  }

  tabs.forEach(t => {
    t.addEventListener('click', (e) => {
      e.preventDefault();
      const id = t.getAttribute('href').slice(1);
      history.replaceState(null, '', `#${id}`);
      activate(id);
    });
  });

  window.addEventListener('hashchange', fromHash);
  fromHash();
})();

(function () {
  const testConnectionBtn = document.getElementById('jf-test-connection-btn');
  const testSystemInfoBtn = document.getElementById('jf-test-sysinfo-btn');

  if (testConnectionBtn) {
    testConnectionBtn.addEventListener('click', async () => {
      const originalText = testConnectionBtn.textContent;
      testConnectionBtn.disabled = true;
      testConnectionBtn.textContent = 'Testing...';
      try {
        const resp = await fetch('/api/test-connection', { method: 'GET' });
        const data = await resp.json();
        const kind = data.ok ? 'success' : 'error';
        const statusInfo = typeof data.status === 'number' ? ` (status: ${data.status})` : '';
        const msg = (data.message || (data.ok ? 'Connection successful.' : 'Connection failed.')) + statusInfo;
        showToast(msg, kind);
      } catch (err) {
        showToast('Failed to test connection', 'error');
        console.error(err);
      } finally {
        testConnectionBtn.textContent = originalText;
        const COOLDOWN_MS = 3000;
        setTimeout(() => { testConnectionBtn.disabled = false; }, COOLDOWN_MS);
      }
    });
  }

  if (testSystemInfoBtn) {
    testSystemInfoBtn.addEventListener('click', async () => {
      const originalText = testSystemInfoBtn.textContent;
      testSystemInfoBtn.disabled = true;
      testSystemInfoBtn.textContent = 'Fetching...';
      try {
        const resp = await fetch('/api/jellyfin/system-info', { method: 'GET' });
        const result = await resp.json();

        if (result && result.ok) {
          const d = result.data || {};
          const name = d.ServerName || d.ServerId || 'Unknown';
          const ver = d.Version || d.ProductVersion || 'n/a';
          const os = d.OperatingSystem || d.System || 'n/a';
          const msg = `SystemInfo: name=${name}, version=${ver}, os=${os} (status: ${result.status})`;
          showToast(msg, 'success');
        } else {
          const status = result?.status ?? resp.status;
          const message = result?.message || 'Failed to fetch SystemInfo.';
          showToast(`${message} (status: ${status})`, 'error');
        }
      } catch (err) {
        showToast('Failed to fetch SystemInfo', 'error');
        console.error(err);
      } finally {
        testSystemInfoBtn.textContent = originalText;
        const COOLDOWN_MS = 3000;
        setTimeout(() => { testSystemInfoBtn.disabled = false; }, COOLDOWN_MS);
      }
    });
  }
})();

(function () {
  const panel = document.getElementById('libraries');
  const list = document.getElementById('libraries-list');
  const empty = document.getElementById('libraries-empty');
  const librariesTab = document.getElementById('libraries-tab');

  async function loadLibraries() {
    const result = await fetchJson('/api/analytics/stats/libraries');
    if (!result.ok) {
      showToast(result.message || 'Failed to load libraries', 'error');
      if (empty) empty.hidden = false;
      if (list) list.hidden = true;
      return;
    }
    const libs = Array.isArray(result.data) ? result.data : [];
    renderLibraries(libs);
  }

  function renderLibraries(libs) {
    if (!list || !empty) return;
    list.innerHTML = '';
    const hasItems = libs.length > 0;
    empty.hidden = hasItems;

    libs.forEach(lib => {
      const li = document.createElement('li');

      const name = document.createElement('span');
      const itemCount = typeof lib.item_count === 'number' ? lib.item_count : 0;
      name.textContent = `${lib.name} (${itemCount} items)`;

      const tracked = document.createElement('span');
      tracked.textContent = lib.tracked ? 'Tracked' : 'Not tracked';

      const toggleWrap = document.createElement('label');
      toggleWrap.className = 'switch';
      toggleWrap.setAttribute('aria-label', `Toggle tracking for ${lib.name}`);

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = !!lib.tracked;

      const slider = document.createElement('span');
      slider.className = 'slider';

      toggleWrap.appendChild(checkbox);
      toggleWrap.appendChild(slider);

      checkbox.addEventListener('change', async () => {
        checkbox.disabled = true;
        const desired = checkbox.checked;
        const path = `/api/analytics/library/${encodeURIComponent(lib.jellyfin_id)}/tracked`;
        const result = await postJson(path, { tracked: desired });
        if (result.ok && result.data) {
          lib.tracked = !!result.data.tracked;
          tracked.textContent = lib.tracked ? 'Tracked' : 'Not tracked';
          showToast(`${lib.name}: tracking ${lib.tracked ? 'enabled' : 'disabled'}`, 'success');
        } else {
          checkbox.checked = !!lib.tracked;
          const msg = result.message || 'Failed to update tracking';
          showToast(`${lib.name}: ${msg}`, 'error');
        }
        checkbox.disabled = false;
      });

      li.appendChild(name);
      li.appendChild(tracked);
      li.appendChild(toggleWrap);
      list.appendChild(li);
    });
  }

  function loadIfVisible() {
    if (panel && !panel.hidden) {
      loadLibraries();
    }
  }

  if (location.hash === '#libraries') {
    setTimeout(loadIfVisible, 0);
  }

  if (librariesTab) {
    librariesTab.addEventListener('click', () => {
      setTimeout(loadIfVisible, 0);
    });
  }
  window.addEventListener('hashchange', loadIfVisible);
})();

(function () {
  const noServerDiv = document.getElementById('jf-no-server');
  const serverAddedDiv = document.getElementById('jf-server-added');
  const syncProgressDiv = document.getElementById('jf-sync-progress');
  const addServerBtn = document.getElementById('jf-add-server-btn');
  const removeServerBtn = document.getElementById('jf-remove-server-btn');
  const modalBackdrop = document.getElementById('jf-modal-backdrop');
  const modal = document.getElementById('jf-add-server-modal');
  const modalForm = document.getElementById('jf-modal-form');
  const modalCloseBtn = document.getElementById('jf-modal-close');
  const modalTestBtn = document.getElementById('jf-modal-test-btn');
  const modalHostInput = document.getElementById('jf-modal-host');
  const modalPortInput = document.getElementById('jf-modal-port');
  const modalKeyInput = document.getElementById('jf-modal-api-key');
  const serverHostDisplay = document.getElementById('jf-server-host-display');
  const serverKeyDisplay = document.getElementById('jf-server-key-display');
  const syncPercent = document.getElementById('jf-sync-percent');

  function openModal() {
    if (!modal || !modalBackdrop || !modalHostInput) return;
    modal.hidden = false;
    modalBackdrop.hidden = false;
    modalHostInput.focus();
  }

  function closeModal() {
    if (!modal || !modalBackdrop || !modalForm) return;
    modal.hidden = true;
    modalBackdrop.hidden = true;
    modalForm.reset();
  }

  function updateServerState(hasServer) {
    if (noServerDiv) noServerDiv.hidden = hasServer;
    if (serverAddedDiv) serverAddedDiv.hidden = !hasServer;
    if (syncProgressDiv) syncProgressDiv.hidden = true;
  }

  function showSyncProgress(show = true) {
    if (syncProgressDiv) syncProgressDiv.hidden = !show;
  }

  function displayServer(host, port, apiKey) {
    if (serverHostDisplay) {
      serverHostDisplay.textContent = `${host}:${port}`;
    }
    if (serverKeyDisplay) {
      const redacted = apiKey ? `API Key: ${apiKey.substring(0, 3)}**************************` : 'API Key: *****************************';
      serverKeyDisplay.textContent = redacted;
    }
  }

  async function checkServerState() {
    try {
      const resp = await fetch('/api/settings');
      if (!resp.ok) return;
      const data = await resp.json();

      const hasServer = !!(data.jf_host && data.jf_port && data.jf_api_key);

      if (hasServer) {
        updateServerState(true);
        displayServer(data.jf_host, data.jf_port, data.jf_api_key);
      } else {
        updateServerState(false);
      }
    } catch (err) {
      console.error('Failed to check server state:', err);
    }
  }

  if (addServerBtn) addServerBtn.addEventListener('click', openModal);
  if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
  if (modalBackdrop) modalBackdrop.addEventListener('click', closeModal);

  if (modalForm) {
    modalForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const host = (modalHostInput.value || '').trim();
      const port = (modalPortInput.value || '').trim();
      const apiKey = (modalKeyInput.value || '').trim();

      if (!host || !port || !apiKey) {
        showToast('Please fill in all fields', 'error');
        return;
      }

      try {
        const resp = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ jf_host: host, jf_port: port, jf_api_key: apiKey }),
        });

        if (!resp.ok) {
          showToast('Failed to save server settings', 'error');
          return;
        }

        closeModal();
        showToast('Server added successfully', 'success');
        await checkServerState();
      } catch (err) {
        showToast('Error adding server', 'error');
        console.error(err);
      }
    });
  }

  if (modalTestBtn) {
    modalTestBtn.addEventListener('click', async () => {
      const host = (modalHostInput.value || '').trim();
      const port = (modalPortInput.value || '').trim();
      const apiKey = (modalKeyInput.value || '').trim();

      if (!host || !port || !apiKey) {
        showToast('Please fill in all fields', 'error');
        return;
      }

      const originalText = modalTestBtn.textContent;
      modalTestBtn.disabled = true;
      modalTestBtn.textContent = 'Testing...';

      try {
        const resp = await fetch('/api/test-connection-with-credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ jf_host: host, jf_port: port, jf_api_key: apiKey }),
        });
        const result = await resp.json();

        if (result.ok) {
          showToast('Connection successful!', 'success');
        } else {
          const msg = result.message || 'Connection failed';
          showToast(msg, 'error');
        }
      } catch (err) {
        showToast('Failed to test connection', 'error');
        console.error(err);
      } finally {
        modalTestBtn.textContent = originalText;
        modalTestBtn.disabled = false;
      }
    });
  }

  if (removeServerBtn) {
    removeServerBtn.addEventListener('click', async () => {
      if (!confirm('Remove Jellyfin server configuration?')) return;

      try {
        const resp = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ jf_host: '', jf_port: '', jf_api_key: '' }),
        });

        if (!resp.ok) {
          showToast('Failed to remove server', 'error');
          return;
        }

        showToast('Server removed', 'success');
        updateServerState(false);
        showSyncProgress(false);

        const libList = document.getElementById('libraries-list');
        const libEmpty = document.getElementById('libraries-empty');
        if (libList) libList.innerHTML = '';
        if (libEmpty) libEmpty.hidden = false;
      } catch (err) {
        showToast('Error removing server', 'error');
        console.error(err);
      }
    });
  }

  checkServerState();
})();

(function () {
  const panel = document.getElementById('tasklog');
  const list = document.getElementById('tasklog-list');
  const empty = document.getElementById('tasklog-empty');
  const tab = document.getElementById('task-log-tab');

  async function loadTaskLogs() {
    try {
      const result = await fetchJson('/api/analytics/task-logs');
      if (!result.ok) {
        console.error('Failed to load task logs', result.message);
        if (empty) empty.hidden = false;
        if (list) list.hidden = true;
        return;
      }

      const logs = Array.isArray(result.data) ? result.data : [];
      if (!logs.length) {
        if (empty) empty.hidden = false;
        if (list) list.hidden = true;
        return;
      }

      if (empty) empty.hidden = true;
      if (list) list.hidden = false;
      list.innerHTML = '';

      logs.forEach(l => {
        const li = document.createElement('li');
        li.style.padding = '0.6rem';
        li.style.borderBottom = '1px solid var(--border)';
        const started = l.started_at ? new Date(Number(l.started_at) * 1000) : null;

        li.innerHTML = `
          <div style="display:flex;justify-content:space-between;gap:0.75rem;align-items:center;">
            <div>
              <div style="font-weight:600;color:var(--text);">${escapeHtml(l.name || '(unnamed)')}</div>
              <div style="font-size:0.9rem;color:var(--text-muted);">
                ${started ? started.toLocaleString() : ''}
                ${l.type ? ' • ' + escapeHtml(l.type) : ''}
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-weight:600;color:var(--text);">${humanDuration(Number(l.duration_ms || 0))}</div>
              <div style="font-size:0.85rem;color:var(--text-muted);">${escapeHtml(l.result || '')}</div>
            </div>
          </div>
        `;
        list.appendChild(li);
      });
    } catch (err) {
      console.error('Error loading task logs', err);
      if (empty) empty.hidden = false;
      if (list) list.hidden = true;
    }
  }

  function loadIfVisible() {
    if (panel && !panel.hidden) loadTaskLogs();
  }

  if (location.hash === '#tasklog') setTimeout(loadIfVisible, 0);
  if (tab) tab.addEventListener('click', () => setTimeout(loadIfVisible, 0));
})();