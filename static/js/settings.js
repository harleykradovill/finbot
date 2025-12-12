(function () {
  const tabs = Array.from(document.querySelectorAll('.settings-tab'));
  const panels = Array.from(
    document.querySelectorAll('.settings-content[role="tabpanel"]')
  );

  const toastContainer = document.getElementById('toast-container');
  function showToast(message, kind = "success") {
    if (!toastContainer) return;
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.setAttribute('role', 'status');
    el.textContent = message;
    toastContainer.appendChild(el);

    setTimeout(() => { // Auto-remove after 5s
      el.remove();
    }, 5000);
  }

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
  const pullDataBtn = document.getElementById('jf-sync-data-btn');

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
        const COOLDOWN_MS = 5000;
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
        const COOLDOWN_MS = 5000;
        setTimeout(() => { testSystemInfoBtn.disabled = false; }, COOLDOWN_MS);
      }
    });
  }

  if (pullDataBtn) {
  pullDataBtn.textContent = 'Sync Data';
  pullDataBtn.addEventListener('click', async () => {
    const originalText = pullDataBtn.textContent;
    pullDataBtn.disabled = true;
    pullDataBtn.textContent = 'Syncing...';

    try {
      const resp = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'full' })
      });
      const result = await resp.json();

      if (result.ok) {
        const data = result.data;
        const msg = `Synced: ${data.users_synced} users, ${data.libraries_synced} libraries, ${data.items_synced} items (${data.duration_ms}ms)`;
        showToast(msg, 'success');
      } else {
        const errors = result.data?.errors || ['Unknown error'];
        showToast(`Sync failed: ${errors.join(', ')}`, 'error');
      }
    } catch (err) {
      showToast('Failed to sync data', 'error');
      console.error(err);
    } finally {
      pullDataBtn.textContent = originalText;
      setTimeout(() => { pullDataBtn.disabled = false; }, 5000);
    }
  });
}
})();

(function () {
  const panel = document.getElementById('libraries');
  const list = document.getElementById('libraries-list');
  const empty = document.getElementById('libraries-empty');
  const librariesTab = document.getElementById('libraries-tab');

  function showToast(message, kind = "success") {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.setAttribute('role', 'status');
    el.textContent = message;
    toastContainer.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }

  async function fetchJson(path) {
    try {
      const resp = await fetch(path, { method: 'GET' });
      const data = await resp.json();
      if (!resp.ok) {
        return { ok: false, status: resp.status, message: 'HTTP error', data: null };
      }
      return data;
    } catch (err) {
      return { ok: false, status: 0, message: err?.message || 'Network error', data: null };
    }
  }

  async function postJson(path, body) {
    try {
      const resp = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) {
        return { ok: false, status: resp.status, message: 'HTTP error', data: null };
      }
      return data;
    } catch (err) {
      return { ok: false, status: 0, message: err?.message || 'Network error', data: null };
    }
  }

  async function loadLibraries() {
    const result = await fetchJson('/api/analytics/libraries');
    if (!result.ok) {
      showToast(result.message || 'Failed to load libraries', 'error');
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
  // Jellyfin server management: Add/Remove server with state detection
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
  const serverHostDisplay = document.getElementById(
    'jf-server-host-display'
  );
  const serverKeyDisplay = document.getElementById(
    'jf-server-key-display'
  );
  const syncBar = document.getElementById('jf-sync-bar');
  const syncPercent = document.getElementById('jf-sync-percent');

  function showToast(message, kind = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.setAttribute('role', 'status');
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 5000);
  }

  function openModal() {
    modal.hidden = false;
    modalBackdrop.hidden = false;
    modalHostInput.focus();
  }

  function closeModal() {
    modal.hidden = true;
    modalBackdrop.hidden = true;
    modalForm.reset();
  }

  function updateServerState(hasServer) {
    // Toggle visibility between no-server and server-added states
    if (noServerDiv) noServerDiv.hidden = hasServer;
    if (serverAddedDiv) serverAddedDiv.hidden = !hasServer;
    if (syncProgressDiv) syncProgressDiv.hidden = true;
  }

  function showSyncProgress(show = true) {
    if (syncProgressDiv) {
      syncProgressDiv.hidden = !show;
    }
  }

  function updateSyncProgress(current, total) {
    // Calculate and display progress percentage
    const percent = total > 0
      ? Math.round((current / total) * 100)
      : 0;
    if (syncBar) syncBar.style.width = `${percent}%`;
    if (syncPercent) {
      syncPercent.textContent = `${percent}%`;
    }
  }

  function displayServer(host, port, apiKey) {
    // Display server connection info (redacted API key)
    if (serverHostDisplay) {
      serverHostDisplay.textContent = `${host}:${port}`;
    }
    if (serverKeyDisplay) {
      const redacted = apiKey
        ? `API Key: ${apiKey.substring(0, 3)}**************************`
        : 'API Key: *****************************';
      serverKeyDisplay.textContent = redacted;
    }
  }

  async function checkServerState() {
    // Query settings API to determine current server state
    try {
      const resp = await fetch('/api/settings');
      if (!resp.ok) return;
      const data = await resp.json();

      const hasServer = !!(
        data.jf_host && data.jf_port && data.jf_api_key
      );

      if (hasServer) {
        updateServerState(true);
        displayServer(
          data.jf_host,
          data.jf_port,
          data.jf_api_key
        );
        // Check if initial sync is in progress
        checkSyncProgress();
      } else {
        updateServerState(false);
      }
    } catch (err) {
      console.error('Failed to check server state:', err);
    }
  }

  async function checkSyncProgress() {
    // Poll for initial activity log sync progress
    try {
      const resp = await fetch(
        '/api/analytics/server/sync-progress'
      );
      if (!resp.ok) return;
      const data = await resp.json();

      if (data.syncing) {
        showSyncProgress(true);
        updateSyncProgress(
          data.processed_events || 0,
          data.total_events || 1
        );
        // Poll again in 2 seconds
        setTimeout(checkSyncProgress, 2000);
      } else {
        showSyncProgress(false);
      }
    } catch (err) {
      // Endpoint may not exist yet; suppress error
    }
  }

  if (addServerBtn) {
    addServerBtn.addEventListener('click', openModal);
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', closeModal);
  }

  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', closeModal);
  }

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
        // Save server settings
        const resp = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            jf_host: host,
            jf_port: port,
            jf_api_key: apiKey,
          }),
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
        const resp = await fetch(
          '/api/test-connection-with-credentials',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              jf_host: host,
              jf_port: port,
              jf_api_key: apiKey,
            }),
          }
        );
        const result = await resp.json();

        if (result.ok) {
          showToast('Connection successful!', 'success');
        } else {
          const msg = (
            result.message || 'Connection failed'
          );
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
      if (!confirm('Remove Jellyfin server configuration?')) {
        return;
      }

      try {
        const resp = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            jf_host: '',
            jf_port: '',
            jf_api_key: '',
          }),
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