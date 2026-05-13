/* DM Post-Processor — frontend logic */
'use strict';

// ── Module state ──────────────────────────────────────────────────────────────
let csvColumns = [];
let csvData    = [];
let activePlot = null;  // track last Plotly render for theme re-render
let currentEventSource = null;
let outputFilePath = '';

// Path browser state
let modalTargetInput = null;
let modalBrowseMode  = 'folder';
let modalSelected    = '';

// Config debounce timer
let configDebounceTimer = null;

// ── Utilities ─────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function plotlyLayout(xTitle, yTitle) {
  return {
    paper_bgcolor: 'transparent',
    plot_bgcolor:  'transparent',
    font: { family: 'IBM Plex Sans', color: cssVar('--text-primary'), size: 12 },
    xaxis: { gridcolor: cssVar('--border'), linecolor: cssVar('--border'),
             title: { text: (xTitle || '').replace(/_/g, ' '), font: { size: 11 } },
             tickfont: { size: 10 } },
    yaxis: { gridcolor: cssVar('--border'), linecolor: cssVar('--border'),
             title: { text: (yTitle || '').replace(/_/g, ' '), font: { size: 11 } },
             tickfont: { size: 10 } },
    legend: { bgcolor: 'transparent', bordercolor: cssVar('--border') },
    margin: { t: 40, r: 24, b: 60, l: 64 },
  };
}

// ── Startup ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([fetchVersion(), fetchSystemInfo(), fetchConfig()]);
  bindUI();
});

async function fetchVersion() {
  try {
    const d = await fetch('/api/version').then(r => r.json());
    $('version-badge').textContent = `v${d.version}`;
  } catch {}
}

async function fetchSystemInfo() {
  try {
    const d = await fetch('/api/system_info').then(r => r.json());
    const slider = $('n-workers');
    slider.max = d.cpu_count;
    updateWorkersLabel(parseInt(slider.value), d.cpu_count);
  } catch {}
}

async function fetchConfig() {
  try {
    const cfg = await fetch('/api/config').then(r => r.json());
    applyConfig(cfg);
  } catch {}
}

function applyConfig(cfg) {
  const setVal = (id, val) => { const el = $(id); if (el && val !== undefined && val !== null) el.value = val; };
  setVal('params-filename', cfg.params_filename);
  setVal('data-filename',   cfg.data_filename);
  setVal('subfolder-name',  cfg.subfolder_name);
  setVal('run-folder-path', cfg.last_run_folder);
  setVal('output-folder-path', cfg.last_output_folder);
  setVal('window-value',    cfg.last_window_type === 'fractional'
    ? Math.round((cfg.last_window_value || 0.2) * 100)
    : (cfg.last_window_value || 0.2));
  setVal('n-workers', cfg.last_n_workers || 1);

  // Window type radio
  const wt = cfg.last_window_type || 'fractional';
  document.querySelectorAll('input[name="window-type"]').forEach(r => {
    r.checked = (r.value === wt);
  });
  updateWindowUnit(wt);

  // Theme
  if (cfg.theme) {
    document.documentElement.setAttribute('data-theme', cfg.theme);
  }

  // Workers label
  const slider = $('n-workers');
  updateWorkersLabel(parseInt(slider.value), parseInt(slider.max));
}

// ── Config auto-save (debounced 800ms) ────────────────────────────────────────
function scheduleConfigSave() {
  clearTimeout(configDebounceTimer);
  configDebounceTimer = setTimeout(pushConfig, 800);
}

function currentConfigPayload() {
  const wt = document.querySelector('input[name="window-type"]:checked')?.value || 'fractional';
  const rawWv = parseFloat($('window-value').value) || 20;
  const windowVal = wt === 'fractional' ? rawWv / 100 : rawWv;
  return {
    params_filename:    $('params-filename').value,
    data_filename:      $('data-filename').value,
    subfolder_name:     $('subfolder-name').value,
    last_run_folder:    $('run-folder-path').value,
    last_output_folder: $('output-folder-path').value,
    last_window_type:   wt,
    last_window_value:  windowVal,
    last_n_workers:     parseInt($('n-workers').value) || 1,
    theme:              document.documentElement.getAttribute('data-theme') || 'dark',
  };
}

async function pushConfig(extra) {
  try {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...currentConfigPayload(), ...extra }),
    });
  } catch {}
}

// ── UI bindings ───────────────────────────────────────────────────────────────
function bindUI() {
  // Mode toggle
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => switchMode(btn.dataset.mode));
  });

  // Theme toggle
  $('theme-toggle').addEventListener('click', toggleTheme);

  // Collapsible sections
  document.querySelectorAll('.collapsible .section-header').forEach(hdr => {
    hdr.setAttribute('aria-expanded', 'true');
    hdr.addEventListener('click', () => {
      const body = hdr.nextElementSibling;
      const open = hdr.getAttribute('aria-expanded') === 'true';
      hdr.setAttribute('aria-expanded', open ? 'false' : 'true');
      body.classList.toggle('collapsed', open);
    });
  });

  // Config-tracked inputs
  ['params-filename','data-filename','subfolder-name','run-folder-path',
   'output-folder-path','window-value','n-workers'].forEach(id => {
    $(id)?.addEventListener('input', scheduleConfigSave);
  });
  document.querySelectorAll('input[name="window-type"]').forEach(r => {
    r.addEventListener('change', () => {
      updateWindowUnit(r.value);
      scheduleConfigSave();
    });
  });

  // Workers slider label
  $('n-workers').addEventListener('input', e => {
    updateWorkersLabel(parseInt(e.target.value), parseInt(e.target.max));
  });

  // Browse buttons
  document.querySelectorAll('[data-target]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = $(btn.dataset.target);
      const mode   = btn.dataset.mode || 'folder';
      openModal(target, mode);
    });
  });

  // Run button
  $('run-btn').addEventListener('click', startProcessing);

  // Download button
  $('download-btn').addEventListener('click', () => {
    if (outputFilePath) {
      const a = document.createElement('a');
      a.href = `/api/download?file_path=${encodeURIComponent(outputFilePath)}`;
      a.click();
    }
  });

  // Mode B: load and plot
  $('load-btn').addEventListener('click', loadCSV);
  $('plot-btn').addEventListener('click', generatePlot);
  $('plot-type').addEventListener('change', updatePlotControls);

  // Modal controls
  $('modal-close').addEventListener('click', closeModal);
  $('modal-backdrop').addEventListener('click', closeModal);
  $('modal-up').addEventListener('click', navigateUp);
  $('modal-select').addEventListener('click', confirmModalSelection);
  $('modal-current-path').addEventListener('keydown', e => {
    if (e.key === 'Enter') browsePath($('modal-current-path').value);
  });

  // Keyboard: Escape closes modal
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
  });
}

// ── Mode toggle ───────────────────────────────────────────────────────────────
function switchMode(mode) {
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
  $('panel-A').classList.toggle('hidden', mode !== 'A');
  $('panel-B').classList.toggle('hidden', mode !== 'B');
  $('view-A').classList.toggle('hidden', mode !== 'A');
  $('view-B').classList.toggle('hidden', mode !== 'B');
}

// ── Theme toggle ──────────────────────────────────────────────────────────────
function toggleTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  pushConfig({ theme: next });
  if (activePlot) rerenderPlot();
}

// ── Window unit helper ────────────────────────────────────────────────────────
function updateWindowUnit(wt) {
  $('window-unit').textContent = wt === 'fractional' ? '%' : 'iterations';
  const input = $('window-value');
  if (wt === 'fractional') {
    input.min = 1; input.max = 100;
    if (parseFloat(input.value) > 100) input.value = 20;
  } else {
    input.min = 1; input.removeAttribute('max');
  }
}

function updateWorkersLabel(val, max) {
  $('workers-label').textContent = `${val} of ${max} core${max !== 1 ? 's' : ''}`;
}

// ── Mode A — Run ──────────────────────────────────────────────────────────────
async function startProcessing() {
  const runFolder = $('run-folder-path').value.trim();
  if (!runFolder) { alert('Please enter a run folder path.'); return; }
  const wv = parseFloat($('window-value').value);
  if (!wv || wv <= 0) { alert('Window value must be > 0.'); return; }

  // Reset UI
  $('case-log').innerHTML = '';
  $('progress-bar').style.width = '0%';
  $('summary-chips').classList.add('hidden');
  $('summary-chips').innerHTML = '';
  $('download-btn').classList.add('hidden');
  $('process-status').textContent = 'Starting…';
  outputFilePath = '';

  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }

  await pushConfig();

  const wt  = document.querySelector('input[name="window-type"]:checked')?.value || 'fractional';
  const rawWv = parseFloat($('window-value').value);
  const windowVal = wt === 'fractional' ? rawWv / 100 : rawWv;
  const nWorkers = parseInt($('n-workers').value) || 1;
  const outFolder = $('output-folder-path').value.trim();

  const params = new URLSearchParams({
    root_path:    runFolder,
    window_type:  wt,
    window_value: windowVal,
    n_workers:    nWorkers,
    output_path:  outFolder,
  });

  let doneCount = 0;
  let totalCount = 0;

  const es = new EventSource(`/api/stream_process?${params}`);
  currentEventSource = es;

  $('run-btn').disabled = true;

  es.onmessage = e => {
    const msg = JSON.parse(e.data);

    if (msg.done) {
      es.close();
      currentEventSource = null;
      $('run-btn').disabled = false;
      $('progress-bar').style.width = '100%';
      $('process-status').textContent = 'Complete';
      outputFilePath = msg.output_path || '';
      showSummaryChips(msg.summary || {});
      if (outputFilePath) $('download-btn').classList.remove('hidden');
      return;
    }

    if (msg.error) {
      es.close();
      currentEventSource = null;
      $('run-btn').disabled = false;
      $('process-status').textContent = `Error: ${msg.error}`;
      return;
    }

    doneCount++;
    if (!totalCount && msg.progress_pct) {
      totalCount = Math.round(doneCount / (msg.progress_pct / 100));
    }

    $('progress-bar').style.width = `${msg.progress_pct}%`;
    $('process-status').textContent = `Processing… (${doneCount}${totalCount ? '/' + totalCount : ''} cases)`;

    appendLogRow(msg.case, msg.status, msg.warnings || []);
  };

  es.onerror = () => {
    es.close();
    currentEventSource = null;
    $('run-btn').disabled = false;
    if ($('process-status').textContent === 'Starting…') {
      $('process-status').textContent = 'Connection error — check server console';
    }
  };
}

function appendLogRow(caseName, status, warnings) {
  const row = document.createElement('div');
  const iconMap = { ok: '✓', warning: '⚠', missing_data: '✗', missing_params: '✗', error: '✗' };
  const classMap = { ok: 'log-ok', warning: 'log-warning',
                     missing_data: 'log-error', missing_params: 'log-error', error: 'log-error' };
  const detailMap = {
    ok: '', warning: `${warnings.length} warning${warnings.length !== 1 ? 's' : ''}`,
    missing_data: 'data CSV not found', missing_params: 'params CSV not found', error: warnings[0] || 'error',
  };

  row.className = `log-row ${classMap[status] || 'log-skip'} ${warnings.length ? 'has-warnings' : ''}`;
  row.innerHTML = `
    <span class="log-icon">${iconMap[status] || '—'}</span>
    <div class="log-content">
      <div class="log-name font-mono">${caseName}</div>
      ${detailMap[status] ? `<div class="log-detail">${detailMap[status]}</div>` : ''}
      ${warnings.length ? `<ul class="log-warnings-list">${warnings.map(w => `<li>${w}</li>`).join('')}</ul>` : ''}
    </div>`;

  if (warnings.length) {
    row.addEventListener('click', () => {
      row.querySelector('.log-warnings-list').classList.toggle('open');
    });
  }

  const log = $('case-log');
  log.appendChild(row);
  row.style.animationDelay = `${Math.min(log.children.length * 20, 200)}ms`;
  log.scrollTop = log.scrollHeight;
}

function showSummaryChips(summary) {
  const chips = $('summary-chips');
  chips.innerHTML = '';
  if (summary.ok !== undefined) {
    const c = document.createElement('span');
    c.className = 'chip chip-ok';
    c.textContent = `${summary.ok} processed`;
    chips.appendChild(c);
  }
  if (summary.warnings) {
    const c = document.createElement('span');
    c.className = 'chip chip-warning';
    c.textContent = `${summary.warnings} warning${summary.warnings !== 1 ? 's' : ''}`;
    chips.appendChild(c);
  }
  const skipped = (summary.missing_data || 0) + (summary.missing_params || 0);
  if (skipped) {
    const c = document.createElement('span');
    c.className = 'chip chip-skip';
    c.textContent = `${skipped} skipped`;
    chips.appendChild(c);
  }
  chips.classList.remove('hidden');
}

// ── Mode B — Load CSV ─────────────────────────────────────────────────────────
async function loadCSV() {
  const filePath = $('csv-path').value.trim();
  if (!filePath) { alert('Please enter a CSV file path.'); return; }

  try {
    const res = await fetch('/api/load_csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath }),
    });
    const d = await res.json();
    if (d.error) { alert(`Error loading CSV: ${d.error}`); return; }
    csvColumns = d.columns;
    csvData    = d.data;
    populatePlotDropdowns(csvColumns);
    $('plot-config-section').classList.remove('hidden');
  } catch (err) {
    alert(`Network error: ${err.message}`);
  }
}

function populatePlotDropdowns(cols) {
  const numericCols = cols.filter(c => {
    if (c === 'case_name') return false;
    const vals = csvData.map(r => r[c]).filter(v => v !== null && v !== undefined);
    return vals.some(v => typeof v === 'number');
  });

  fillSelect('scatter-x', numericCols);
  fillSelect('scatter-y', numericCols, 1);
  fillSelect('scatter-color', ['', ...cols.filter(c => c !== 'case_name')]);
  fillSelect('custom-x', numericCols);
  fillSelect('custom-y', numericCols, null, true);

  // Pair matrix checkboxes
  const list = $('pair-column-list');
  list.innerHTML = '';
  numericCols.forEach((c, i) => {
    const lbl = document.createElement('label');
    lbl.innerHTML = `<input type="checkbox" value="${c}" ${i < 4 ? 'checked' : ''} />${c.replace(/_/g,' ')}`;
    list.appendChild(lbl);
  });

  updatePlotControls();
}

function fillSelect(id, opts, defaultIdx = 0, keepEmpty = false) {
  const sel = $(id);
  sel.innerHTML = '';
  opts.forEach((o, i) => {
    const opt = document.createElement('option');
    opt.value = o; opt.textContent = o === '' ? 'None' : o.replace(/_/g, ' ');
    if (i === defaultIdx && !keepEmpty) opt.selected = true;
    sel.appendChild(opt);
  });
}

function updatePlotControls() {
  const type = $('plot-type').value;
  $('scatter-controls').classList.toggle('hidden', type !== 'scatter');
  $('pair-controls').classList.toggle('hidden',    type !== 'pair');
  $('custom-controls').classList.toggle('hidden',  type !== 'custom');
}

// ── Mode B — Generate Plot ────────────────────────────────────────────────────
function generatePlot() {
  if (!csvData.length) { alert('No data loaded.'); return; }
  const type = $('plot-type').value;

  if (type === 'scatter')   renderScatter();
  else if (type === 'pair') renderPair();
  else if (type === 'custom') renderCustom();
}

function renderScatter() {
  const xCol     = $('scatter-x').value;
  const yCol     = $('scatter-y').value;
  const colorCol = $('scatter-color').value;
  if (!xCol || !yCol) return;

  const colorVals = colorCol ? csvData.map(r => r[colorCol]) : null;
  const stdCol    = `${yCol}_std`;
  const hasStd    = csvColumns.includes(stdCol);

  const paramCols = csvColumns.filter(c => {
    const sfx = ['_mean','_min','_max','_std','_n'];
    return c !== 'case_name' && !sfx.some(s => c.endsWith(s));
  });

  const trace = {
    type: 'scatter', mode: 'markers',
    x: csvData.map(r => r[xCol]),
    y: csvData.map(r => r[yCol]),
    text: csvData.map(r =>
      ['case_name', ...paramCols].map(c => `${c}: ${r[c]}`).join('<br>')
    ),
    hovertemplate: '%{text}<extra></extra>',
    marker: {
      color: colorVals || cssVar('--accent'),
      colorscale: colorVals ? 'Viridis' : undefined,
      showscale: !!colorVals,
      size: 8,
      colorbar: colorVals ? { title: { text: colorCol.replace(/_/g,' '), side: 'right' }, thickness: 14 } : undefined,
    },
    error_y: hasStd ? {
      array: csvData.map(r => r[stdCol]),
      visible: true,
      color: cssVar('--text-secondary'),
    } : undefined,
  };

  const layout = plotlyLayout(xCol, yCol);
  activePlot = { type: 'scatter', xCol, yCol, colorCol };
  Plotly.newPlot('plot-container', [trace], layout, { responsive: true });
  renderStatsTable([xCol, yCol]);
}

function renderPair() {
  const selected = Array.from($('pair-column-list').querySelectorAll('input:checked')).map(i => i.value);
  if (selected.length < 2) { alert('Select at least 2 columns for pair matrix.'); return; }

  const paramCols = csvColumns.filter(c => {
    const sfx = ['_mean','_min','_max','_std','_n'];
    return c !== 'case_name' && !sfx.some(s => c.endsWith(s));
  });
  const firstParam = paramCols[0];

  const trace = {
    type: 'splom',
    dimensions: selected.map(c => ({
      label: c.replace(/_/g, ' '),
      values: csvData.map(r => r[c]),
    })),
    marker: {
      color: firstParam ? csvData.map(r => r[firstParam]) : cssVar('--accent'),
      colorscale: 'Viridis',
      size: 5,
      showscale: !!firstParam,
    },
    text: csvData.map(r =>
      paramCols.slice(0, 4).map(c => `${c}: ${r[c]}`).join('<br>')
    ),
    hovertemplate: '%{text}<extra></extra>',
  };

  const layout = {
    ...plotlyLayout('', ''),
    dragmode: 'select',
    height: Math.max(480, selected.length * 120),
  };

  activePlot = { type: 'pair', selected };
  Plotly.newPlot('plot-container', [trace], layout, { responsive: true });
  renderStatsTable(selected);
}

function renderCustom() {
  const xCol  = $('custom-x').value;
  const yCols = Array.from($('custom-y').selectedOptions).map(o => o.value);
  if (!xCol || !yCols.length) { alert('Select X axis and at least one Y axis.'); return; }

  const colors = ['#4D80FF','#2AAD6A','#E07820','#E5453A','#A855F7','#06B6D4'];

  const traces = yCols.map((yCol, i) => ({
    type: 'scatter', mode: 'lines+markers',
    name: yCol.replace(/_/g, ' '),
    x: csvData.map(r => r[xCol]),
    y: csvData.map(r => r[yCol]),
    line: { color: colors[i % colors.length], width: 2 },
    marker: { size: 5 },
  }));

  const layout = plotlyLayout(xCol, yCols.length === 1 ? yCols[0] : 'Value');
  activePlot = { type: 'custom', xCol, yCols };
  Plotly.newPlot('plot-container', traces, layout, { responsive: true });
  renderStatsTable([xCol, ...yCols]);
}

function rerenderPlot() {
  if (!activePlot || !csvData.length) return;
  const { type } = activePlot;
  if (type === 'scatter')     renderScatter();
  else if (type === 'pair')   renderPair();
  else if (type === 'custom') renderCustom();
}

function renderStatsTable(cols) {
  const container = $('stats-table-container');
  if (!cols.length || !csvData.length) { container.innerHTML = ''; return; }

  const validCols = cols.filter(c => csvColumns.includes(c));
  const numFmt = v => (v === null || v === undefined) ? '—' : (typeof v === 'number' ? v.toPrecision(5) : v);

  let html = '<table class="stats-table"><thead><tr>';
  html += '<th>Case</th>';
  validCols.forEach(c => { html += `<th>${c.replace(/_/g,' ')}</th>`; });
  html += '</tr></thead><tbody>';

  csvData.slice(0, 200).forEach(row => {
    html += '<tr>';
    html += `<td class="font-mono">${row.case_name || ''}</td>`;
    validCols.forEach(c => { html += `<td>${numFmt(row[c])}</td>`; });
    html += '</tr>';
  });
  html += '</tbody></table>';
  container.innerHTML = html;
}

// ── Path browser modal ────────────────────────────────────────────────────────
function openModal(targetInput, mode) {
  modalTargetInput = targetInput;
  modalBrowseMode  = mode;
  modalSelected    = '';

  const startPath = targetInput?.value?.trim() || '';
  browsePath(startPath);
  $('path-modal').classList.remove('hidden');
}

function closeModal() {
  $('path-modal').classList.add('hidden');
  modalTargetInput = null;
  modalSelected    = '';
}

async function browsePath(path) {
  const url = `/api/browse?path=${encodeURIComponent(path)}&mode=${modalBrowseMode}`;
  try {
    const d = await fetch(url).then(r => r.json());
    if (d.error) { renderModalListing([], [], path); return; }
    $('modal-current-path').value = d.current || path;
    renderModalListing(d.dirs || [], d.files || [], d.current || path);
  } catch {
    renderModalListing([], [], path);
  }
}

function renderModalListing(dirs, files, currentPath) {
  const listing = $('modal-listing');
  listing.innerHTML = '';

  if (!dirs.length && !files.length) {
    listing.innerHTML = '<div class="listing-empty">No items to show</div>';
    return;
  }

  dirs.forEach(dir => {
    const row = document.createElement('div');
    row.className = 'listing-row listing-dir';
    row.innerHTML = `<span class="listing-icon">&#128193;</span><span>${dir}</span>`;
    row.addEventListener('click', () => {
      // Deselect any file selection when navigating
      listing.querySelectorAll('.listing-row.selected').forEach(r => r.classList.remove('selected'));
      modalSelected = dir;
      browsePath(dir);
    });
    listing.appendChild(row);
  });

  files.forEach(file => {
    const row = document.createElement('div');
    row.className = 'listing-row listing-file';
    row.innerHTML = `<span class="listing-icon">&#128196;</span><span>${file}</span>`;
    row.addEventListener('click', () => {
      listing.querySelectorAll('.listing-row.selected').forEach(r => r.classList.remove('selected'));
      row.classList.add('selected');
      modalSelected = file;
    });
    listing.appendChild(row);
  });
}

function navigateUp() {
  const current = $('modal-current-path').value.trim();
  fetch(`/api/browse?path=${encodeURIComponent(current)}&mode=${modalBrowseMode}`)
    .then(r => r.json())
    .then(d => {
      if (d.parent) browsePath(d.parent);
    })
    .catch(() => {});
}

function confirmModalSelection() {
  if (!modalTargetInput) { closeModal(); return; }
  const val = modalSelected || $('modal-current-path').value.trim();
  if (val) {
    modalTargetInput.value = val;
    modalTargetInput.dispatchEvent(new Event('input'));
  }
  closeModal();
}
