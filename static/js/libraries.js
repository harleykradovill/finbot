(function () {
  const container = document.getElementById('libraries-container');
  const empty = document.getElementById('libraries-empty');
  const tbody = document.getElementById('libraries-tbody');

  function humanBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B','KB','MB','GB','TB'];
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

  async function loadLibraries() {
    try {
      const resp = await fetch('/api/analytics/stats/libraries');
      if (!resp.ok) throw new Error('Network error');
      const data = await resp.json();
      if (!data || !data.ok) throw new Error(data?.message || 'API error');

      const libs = Array.isArray(data.data) ? data.data : [];
      renderLibraries(libs);
    } catch (err) {
      console.error('Failed to load libraries', err);
      if (empty) empty.hidden = false;
      if (container) container.hidden = true;
    }
  }

  function renderLibraries(libs) {
    if (!libs || libs.length === 0) {
      if (empty) empty.hidden = false;
      if (container) container.hidden = true;
      return;
    }
    empty.hidden = true;
    container.hidden = false;
    tbody.innerHTML = '';

    libs.forEach(lib => {
      const tr = document.createElement('tr');

      const nameTd = document.createElement('td');
      nameTd.style.padding = '0.5rem';
      nameTd.textContent = lib.name || '(unnamed)';
      tr.appendChild(nameTd);

      const typeTd = document.createElement('td');
      typeTd.style.padding = '0.5rem';
      typeTd.textContent = lib.type || '';
      tr.appendChild(typeTd);

      const totalTimeTd = document.createElement('td');
      totalTimeTd.style.padding = '0.5rem';
      totalTimeTd.style.textAlign = 'right';
      totalTimeTd.textContent = humanTime(lib.total_time_seconds || 0);
      tr.appendChild(totalTimeTd);

      const filesTd = document.createElement('td');
      filesTd.style.padding = '0.5rem';
      filesTd.style.textAlign = 'right';
      filesTd.textContent = String(lib.total_files || 0);
      tr.appendChild(filesTd);

      const sizeTd = document.createElement('td');
      sizeTd.style.padding = '0.5rem';
      sizeTd.style.textAlign = 'right';
      sizeTd.textContent = humanBytes(lib.size_bytes || 0);
      tr.appendChild(sizeTd);

      const playsTd = document.createElement('td');
      playsTd.style.padding = '0.5rem';
      playsTd.style.textAlign = 'right';
      playsTd.textContent = String(lib.total_plays || 0);
      tr.appendChild(playsTd);

      const playbackTd = document.createElement('td');
      playbackTd.style.padding = '0.5rem';
      playbackTd.style.textAlign = 'right';
      playbackTd.textContent = humanTime(lib.total_playback_seconds || 0);
      tr.appendChild(playbackTd);

      const lastTd = document.createElement('td');
      lastTd.style.padding = '0.5rem';
      lastTd.textContent = lib.last_played_item_name || '';
      tr.appendChild(lastTd);

      tbody.appendChild(tr);
    });
  }

  loadLibraries();

  setInterval(loadLibraries, 60 * 1000);
})();