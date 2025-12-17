(function () {
  const container = document.getElementById('activitylog-container');
  const empty = document.getElementById('activitylog-empty');
  const tbody = document.getElementById('activitylog-tbody');

  const firstBtn = document.getElementById('activitylog-first');
  const prevBtn = document.getElementById('activitylog-prev');
  const nextBtn = document.getElementById('activitylog-next');
  const lastBtn = document.getElementById('activitylog-last');
  const pagesDiv = document.getElementById('activitylog-pages');
  const pageNumEl = document.getElementById('activitylog-page-num');
  const metaEl = document.getElementById('activitylog-meta');

  const PER_PAGE = 25;
  const MAX_PAGE_BUTTONS = 7;

  function safeShowToast(msg, kind = 'error') {
    if (typeof showToast === 'function') {
      showToast(msg, kind);
    } else {
      console.error(msg);
    }
  }

  function parseHashPage() {
    const m = (location.hash || '').match(/page=(\d+)/);
    return m ? Math.max(1, parseInt(m[1], 10)) : 1;
  }

  function gotoPage(n) {
    if (!n || n < 1) n = 1;
    location.hash = `page=${n}`;
  }

  async function loadPage(page) {
    page = Number(page) || 1;
    // show loading state
    setNavigationDisabled(true);
    try {
      const resp = await fetch(`/api/analytics/activitylog?page=${page}&per_page=${PER_PAGE}`);
      if (!resp.ok) throw new Error('Network error');
      const payload = await resp.json();
      if (!payload || !payload.ok) {
        throw new Error(payload?.message || 'API error');
      }
      render(payload.data || {});
    } catch (err) {
      safeShowToast(`Failed to load activity log: ${err?.message || err}`, 'error');
      renderEmpty();
    } finally {
      setNavigationDisabled(false);
    }
  }

  function renderEmpty() {
    container.hidden = true;
    empty.hidden = false;
    pagesDiv.innerHTML = '';
    pageNumEl.textContent = '1';
    metaEl.textContent = 'Page 1';
  }

  function render(data) {
    const items = Array.isArray(data.items) ? data.items : [];
    const page = Number(data.page || 1);
    const per_page = Number(data.per_page || PER_PAGE);
    const total = Number(data.total || 0);

    if (!items.length) {
      renderEmpty();
      return;
    }

    tbody.innerHTML = '';
    items.forEach(it => {
      const tr = document.createElement('tr');

      const userTd = document.createElement('td');
      userTd.style.padding = '0.5rem';
      userTd.textContent = it.username_denorm || it.user_id || '(unknown)';
      tr.appendChild(userTd);

      const eventTd = document.createElement('td');
      eventTd.style.padding = '0.5rem';
      eventTd.textContent = it.event_name || '';
      tr.appendChild(eventTd);

      const dateTd = document.createElement('td');
      dateTd.style.padding = '0.5rem';
      dateTd.style.textAlign = 'right';
      const ts = it.activity_at ? Number(it.activity_at) : null;
      dateTd.textContent = ts ? new Date(ts * 1000).toLocaleString() : '';
      tr.appendChild(dateTd);

      tbody.appendChild(tr);
    });

    empty.hidden = true;
    container.hidden = false;

    const totalPages = Math.max(1, Math.ceil(total / per_page));
    pageNumEl.textContent = String(page);
    metaEl.textContent = `Page ${page} of ${totalPages}`;

    renderPaginationControls(page, totalPages);
  }

  function renderPaginationControls(current, totalPages) {
    firstBtn.disabled = current <= 1;
    prevBtn.disabled = current <= 1;
    nextBtn.disabled = current >= totalPages;
    lastBtn.disabled = current >= totalPages;

    pagesDiv.innerHTML = '';

    const half = Math.floor(MAX_PAGE_BUTTONS / 2);
    let start = Math.max(1, current - half);
    let end = Math.min(totalPages, start + MAX_PAGE_BUTTONS - 1);
    if (end - start + 1 < MAX_PAGE_BUTTONS) {
      start = Math.max(1, end - MAX_PAGE_BUTTONS + 1);
    }

    for (let p = start; p <= end; p++) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-ghost';
      btn.style.minWidth = '36px';
      btn.dataset.page = String(p);
      btn.textContent = String(p);
      if (p === current) {
        btn.setAttribute('aria-current', 'page');
        btn.classList.add('active');
      }
      btn.addEventListener('click', () => gotoPage(p));
      pagesDiv.appendChild(btn);
    }
  }

  function setNavigationDisabled(state) {
    [firstBtn, prevBtn, nextBtn, lastBtn].forEach(b => {
      if (!b) return;
      b.disabled = state || b.disabled;
    });
    Array.from(pagesDiv.children).forEach(ch => {
      if (ch.tagName === 'BUTTON') ch.disabled = state;
    });
  }

  if (firstBtn) firstBtn.addEventListener('click', () => gotoPage(1));
  if (prevBtn) prevBtn.addEventListener('click', () => {
    const p = parseHashPage();
    gotoPage(Math.max(1, p - 1));
  });
  if (nextBtn) nextBtn.addEventListener('click', () => {
    const p = parseHashPage();
    gotoPage(p + 1);
  });
  if (lastBtn) lastBtn.addEventListener('click', async () => {
    try {
      const resp = await fetch(`/api/analytics/activitylog?page=1&per_page=${PER_PAGE}`);
      if (!resp.ok) throw new Error('Network error');
      const payload = await resp.json();
      if (!payload || !payload.ok) throw new Error(payload?.message || 'API error');
      const total = Number(payload.data?.total || 0);
      const totalPages = Math.max(1, Math.ceil(total / Number(payload.data?.per_page || PER_PAGE)));
      gotoPage(totalPages);
    } catch (err) {
      safeShowToast('Failed to jump to last page', 'error');
    }
  });

  window.addEventListener('hashchange', () => {
    const page = parseHashPage();
    loadPage(page);
  });

  setTimeout(() => {
    const page = parseHashPage();
    loadPage(page);
  }, 0);
})();