/**
 * compare.js — Compare Module for Project Delivery Accelerator Engine
 *
 * Provides Version A vs Version B and Review X vs Review Y comparison.
 * No backend changes required — uses existing API endpoints:
 *   POST /api/projects/{pid}/compare-versions  { version_a, version_b }
 *   POST /api/projects/{pid}/compare-reviews   { review_a, review_b }
 *   GET  /api/projects/{pid}/hierarchy/versions
 *   GET  /api/projects/{pid}/hierarchy/reviews
 *
 * Public API (attached to window.Compare):
 *   Compare.open(projectId)         — open the compare modal
 *   Compare.close()                 — close modal
 *   Compare.setMode(mode)           — 'versions' | 'reviews'
 *   Compare.run()                   — execute comparison
 */

(function (global) {
  'use strict';

  // ── Constants ────────────────────────────────────────────────────────────

  const MODES = { VERSIONS: 'versions', REVIEWS: 'reviews' };

  const CAT_ICONS = {
    risks: '🔴', assumptions: '💭', dependencies: '🔗',
    constraints: '⛔', action_items: '✅',
    gaps: '🔍', findings: '📋', recommendations: '💡',
    design_gaps: '⚠️', questions: '❓',
  };

  const TREND_MAP = {
    improving: { cls: 'cmp-trend-down', label: '↓ Improving' },
    risks_increasing: { cls: 'cmp-trend-up', label: '↑ Risks Rising' },
    complexity_increasing: { cls: 'cmp-trend-up', label: '↑ Complexity Rising' },
    stable: { cls: 'cmp-trend-same', label: '→ Stable' },
    degrading: { cls: 'cmp-trend-up', label: '↑ Degrading' },
  };


  // ── Module state ─────────────────────────────────────────────────────────

  const _state = {
    projectId: null,
    mode: MODES.VERSIONS,          // 'versions' | 'reviews'
    versions: [],                  // [{version_id, label, created_at, review_count, persona}]
    reviews: [],                   // [{review_id, version_id, persona, created_at, iteration_number}]
    loading: false,
    result: null,                  // last API response
    error: null,
  };

  // ── Utilities ─────────────────────────────────────────────────────────────

  function _esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _fmtDate(iso) {
    if (!iso) return '–';
    return iso.slice(0, 16).replace('T', ' ');
  }

  function _fmtDateShort(iso) {
    return iso ? iso.slice(0, 10) : '–';
  }

  async function _api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    try {
      const r = await fetch(path, opts);
      return r.json();
    } catch (e) {
      return { error: e.message };
    }
  }

  function _el(id) { return document.getElementById(id); }

  function _setHtml(id, html) {
    const el = _el(id);
    if (el) el.innerHTML = html;
  }


  // ── Data loading ──────────────────────────────────────────────────────────

  async function _loadVersions(pid) {
    const r = await _api('GET', `/api/projects/${pid}/hierarchy/versions`);
    _state.versions = (r.versions || []).slice().sort(
      (a, b) => (b.created_at || '').localeCompare(a.created_at || '')
    );
  }

  async function _loadReviews(pid) {
    const r = await _api('GET', `/api/projects/${pid}/hierarchy/reviews`);
    _state.reviews = (r.reviews || []).slice().sort(
      (a, b) => (b.created_at || '').localeCompare(a.created_at || '')
    );
  }

  // ── Client-side diff logic ────────────────────────────────────────────────
  // Used to compute field-level changes between two version/review objects
  // so we can display "Modified" items in addition to Added/Removed from the API.

  /**
   * Diff two flat string arrays — returns {added, removed, unchanged}.
   * Normalises strings to lowercase for comparison.
   */
  function _diffArrays(before, after) {
    const setA = new Set((before || []).map(s => String(s).trim().toLowerCase()));
    const setB = new Set((after  || []).map(s => String(s).trim().toLowerCase()));
    // Preserve original casing from the "after" set for display
    const afterMap = {};
    (after || []).forEach(s => { afterMap[String(s).trim().toLowerCase()] = s; });
    const beforeMap = {};
    (before || []).forEach(s => { beforeMap[String(s).trim().toLowerCase()] = s; });
    return {
      added:     [...setB].filter(k => !setA.has(k)).map(k => afterMap[k]),
      removed:   [...setA].filter(k => !setB.has(k)).map(k => beforeMap[k]),
      unchanged: [...setA].filter(k => setB.has(k)).length,
    };
  }

  /**
   * Diff two version/review scalar fields.
   * Returns {field, before, after, changed: bool}.
   */
  function _diffFields(objA, objB, fields) {
    return fields
      .map(f => ({
        field:   f,
        before:  objA[f] ?? '–',
        after:   objB[f] ?? '–',
        changed: String(objA[f] ?? '') !== String(objB[f] ?? ''),
      }))
      .filter(d => d.changed);
  }


  // ── Run comparison ────────────────────────────────────────────────────────

  async function _runVersionCompare() {
    const selA = _el('cmp-sel-a');
    const selB = _el('cmp-sel-b');
    if (!selA || !selB) return;
    const va = selA.value;
    const vb = selB.value;

    if (!va || !vb) {
      _showError('Select both versions before comparing.');
      return;
    }
    if (va === vb) {
      _showError('Select two different versions.');
      return;
    }

    _setLoading(true);
    const data = await _api(
      'POST',
      `/api/projects/${_state.projectId}/compare-versions`,
      { version_a: va, version_b: vb }
    );
    _setLoading(false);

    if (data.error) { _showError(data.error); return; }

    // Attach client-side metadata diff (persona, ai_backend, scope)
    const objA = _state.versions.find(v => v.version_id === va) || {};
    const objB = _state.versions.find(v => v.version_id === vb) || {};
    data._meta_diff = _diffFields(objA, objB, ['persona', 'ai_backend', 'label']);
    data._stats_diff = _diffFields(
      objA.stats || {}, objB.stats || {},
      ['risks', 'dependencies', 'constraints', 'assumptions', 'action_items']
    );

    _state.result = data;
    _state.error  = null;
    _renderVersionResult(data, objA, objB);
  }

  async function _runReviewCompare() {
    const selA = _el('cmp-sel-a');
    const selB = _el('cmp-sel-b');
    if (!selA || !selB) return;
    const ra = selA.value;
    const rb = selB.value;

    if (!ra || !rb) {
      _showError('Select both reviews before comparing.');
      return;
    }
    if (ra === rb) {
      _showError('Select two different reviews.');
      return;
    }

    _setLoading(true);
    const data = await _api(
      'POST',
      `/api/projects/${_state.projectId}/compare-reviews`,
      { review_a: ra, review_b: rb }
    );
    _setLoading(false);

    if (data.error) { _showError(data.error); return; }

    const objA = _state.reviews.find(r => r.review_id === ra) || {};
    const objB = _state.reviews.find(r => r.review_id === rb) || {};
    data._meta_diff = _diffFields(objA, objB, ['persona', 'ai_backend', 'version_id']);

    _state.result = data;
    _state.error  = null;
    _renderReviewResult(data, objA, objB);
  }


  // ── Renderers — Version result ────────────────────────────────────────────

  function _renderVersionResult(data, objA, objB) {
    const s      = data.summary || {};
    const cats   = data.categories || {};
    const trend  = TREND_MAP[s.trend] || { cls: 'cmp-trend-same', label: '→ ' + (s.trend || 'unknown') };

    // Summary bar
    let html = `
      <div class="cmp-summary-bar">
        <div class="cmp-summary-pair">
          <span class="cmp-ver-badge cmp-badge-a">${_esc(data.version_a)}</span>
          <span class="cmp-arrow">→</span>
          <span class="cmp-ver-badge cmp-badge-b">${_esc(data.version_b)}</span>
        </div>
        <div class="cmp-summary-stats">
          <span class="cmp-stat-added">+${s.total_added || 0} added</span>
          <span class="cmp-stat-removed">−${s.total_removed || 0} removed</span>
          <span class="cmp-trend-pill ${trend.cls}">${trend.label}</span>
        </div>
        <div class="cmp-ts-row">
          <span>${_fmtDate(data.timestamp_a)}</span>
          <span class="cmp-ts-sep">→</span>
          <span>${_fmtDate(data.timestamp_b)}</span>
        </div>
      </div>`;

    // Metadata diff (persona, backend, label)
    if (data._meta_diff && data._meta_diff.length) {
      html += `<div class="cmp-section-title">⚙ Metadata Changes</div>
        <div class="cmp-meta-grid">`;
      data._meta_diff.forEach(d => {
        html += `<div class="cmp-meta-row">
          <span class="cmp-meta-field">${_esc(d.field)}</span>
          <span class="cmp-meta-before">${_esc(d.before)}</span>
          <span class="cmp-arrow">→</span>
          <span class="cmp-meta-after">${_esc(d.after)}</span>
        </div>`;
      });
      html += `</div>`;
    }

    // Stats diff (count changes)
    if (data._stats_diff && data._stats_diff.length) {
      html += `<div class="cmp-section-title">📊 Stat Changes</div>
        <div class="cmp-meta-grid">`;
      data._stats_diff.forEach(d => {
        const delta  = Number(d.after) - Number(d.before);
        const dCls   = delta > 0 ? 'cmp-delta-up' : delta < 0 ? 'cmp-delta-down' : '';
        const dLabel = delta > 0 ? `+${delta}` : String(delta);
        html += `<div class="cmp-meta-row">
          <span class="cmp-meta-field">${_esc(d.field)}</span>
          <span class="cmp-meta-before">${_esc(d.before)}</span>
          <span class="cmp-arrow">→</span>
          <span class="cmp-meta-after">${_esc(d.after)}</span>
          <span class="cmp-delta ${dCls}">${dLabel}</span>
        </div>`;
      });
      html += `</div>`;
    }


    // Per-category diff blocks
    html += `<div class="cmp-section-title">📋 Category Breakdown</div>`;
    const catEntries = Object.entries(cats);
    if (!catEntries.length) {
      html += `<p class="cmp-empty">No category data returned.</p>`;
    } else {
      catEntries.forEach(([cat, d]) => {
        const added   = d.added   || [];
        const removed = d.removed || [];
        const net     = d.net_change || 0;
        const hasChanges = added.length > 0 || removed.length > 0;
        const netCls  = net > 0 ? 'cmp-delta-up' : net < 0 ? 'cmp-delta-down' : 'cmp-delta-neutral';
        const netLbl  = net > 0 ? `+${net}` : String(net);
        const icon    = CAT_ICONS[cat] || '📌';
        const openAttr = hasChanges ? 'open' : '';

        html += `<details class="cmp-cat-block" ${openAttr}>
          <summary class="cmp-cat-header">
            <span class="cmp-cat-chevron">▶</span>
            <span class="cmp-cat-icon">${icon}</span>
            <span class="cmp-cat-name">${_esc(cat.replace(/_/g, ' '))}</span>
            <span class="cmp-count-pill">${d.count_before} → ${d.count_after}</span>
            <span class="cmp-delta ${netCls}">${netLbl}</span>
            ${!hasChanges ? '<span class="cmp-no-change">no changes</span>' : ''}
          </summary>
          <div class="cmp-cat-body">`;

        if (added.length) {
          html += `<div class="cmp-group-label cmp-label-added">ADDED (${added.length})</div>`;
          added.slice(0, 8).forEach(item => {
            html += `<div class="cmp-item cmp-item-added">
              <span class="cmp-item-marker">+</span>
              <span>${_esc(String(item).slice(0, 140))}</span>
            </div>`;
          });
          if (added.length > 8) {
            html += `<p class="cmp-overflow">… and ${added.length - 8} more</p>`;
          }
        }

        if (removed.length) {
          html += `<div class="cmp-group-label cmp-label-removed">REMOVED (${removed.length})</div>`;
          removed.slice(0, 8).forEach(item => {
            html += `<div class="cmp-item cmp-item-removed">
              <span class="cmp-item-marker">−</span>
              <span>${_esc(String(item).slice(0, 140))}</span>
            </div>`;
          });
          if (removed.length > 8) {
            html += `<p class="cmp-overflow">… and ${removed.length - 8} more</p>`;
          }
        }

        if (!hasChanges) {
          html += `<p class="cmp-unchanged-note">
            ${d.unchanged_count || d.count_before} item${d.count_before !== 1 ? 's' : ''} — no changes
          </p>`;
        }

        html += `</div></details>`;
      });
    }

    _setHtml('cmp-result', html);
  }


  // ── Renderers — Review result ─────────────────────────────────────────────

  function _renderReviewResult(data, objA, objB) {
    const s        = data.summary || {};
    const sections = data.sections || {};
    const dirMap   = {
      improving:  { cls: 'cmp-trend-down', label: '↓ Improving' },
      stable:     { cls: 'cmp-trend-same', label: '→ Stable' },
      degrading:  { cls: 'cmp-trend-up',  label: '↑ Degrading' },
    };
    const dir = dirMap[s.direction] || { cls: 'cmp-trend-same', label: '→ ' + (s.direction || 'unknown') };

    const ridA = objA.review_id || data.review_a || 'A';
    const ridB = objB.review_id || data.review_b || 'B';
    const iterA = objA.iteration_number ? `R${objA.iteration_number}` : ridA;
    const iterB = objB.iteration_number ? `R${objB.iteration_number}` : ridB;

    // Summary bar
    let html = `
      <div class="cmp-summary-bar">
        <div class="cmp-summary-pair">
          <span class="cmp-ver-badge cmp-badge-a">${_esc(iterA)}</span>
          <span class="cmp-arrow">→</span>
          <span class="cmp-ver-badge cmp-badge-b">${_esc(iterB)}</span>
        </div>
        <div class="cmp-summary-stats">
          <span class="cmp-stat-added">+${s.new_findings || 0} new</span>
          <span class="cmp-stat-removed">−${s.resolved_findings || 0} resolved</span>
          <span class="cmp-trend-pill ${dir.cls}">${dir.label}</span>
        </div>
      </div>`;

    // Metadata diff
    if (data._meta_diff && data._meta_diff.length) {
      html += `<div class="cmp-section-title">⚙ Metadata Changes</div>
        <div class="cmp-meta-grid">`;
      data._meta_diff.forEach(d => {
        html += `<div class="cmp-meta-row">
          <span class="cmp-meta-field">${_esc(d.field)}</span>
          <span class="cmp-meta-before">${_esc(d.before)}</span>
          <span class="cmp-arrow">→</span>
          <span class="cmp-meta-after">${_esc(d.after)}</span>
        </div>`;
      });
      html += `</div>`;
    }

    // 4-tile progression bar
    html += `
      <div class="cmp-section-title">📈 Review Progression</div>
      <div class="cmp-prog-tiles">
        <div class="cmp-prog-tile cmp-tile-resolved">
          <div class="cmp-prog-num">${s.resolved_findings || 0}</div>
          <div class="cmp-prog-lbl">Resolved</div>
        </div>
        <div class="cmp-prog-tile cmp-tile-new">
          <div class="cmp-prog-num">${s.new_findings || 0}</div>
          <div class="cmp-prog-lbl">New Findings</div>
        </div>
        <div class="cmp-prog-tile cmp-tile-persistent">
          <div class="cmp-prog-num">${_totalPersistent(sections)}</div>
          <div class="cmp-prog-lbl">Persistent</div>
        </div>
        <div class="cmp-prog-tile cmp-tile-net">
          <div class="cmp-prog-num cmp-delta ${s.net_change > 0 ? 'cmp-delta-up' : s.net_change < 0 ? 'cmp-delta-down' : ''}">
            ${s.net_change > 0 ? '+' : ''}${s.net_change || 0}
          </div>
          <div class="cmp-prog-lbl">Net Change</div>
        </div>
      </div>`;


    // Per-section finding blocks
    html += `<div class="cmp-section-title">📋 Finding Sections</div>`;
    const secEntries = Object.entries(sections);
    if (!secEntries.length) {
      html += `<p class="cmp-empty">No section data returned.</p>`;
    } else {
      secEntries.forEach(([sec, d]) => {
        const newF     = d.new_findings  || [];
        const resolved = d.resolved      || [];
        const hasChanges = newF.length > 0 || resolved.length > 0;
        const net      = d.count_after - d.count_before;
        const netCls   = net > 0 ? 'cmp-delta-up' : net < 0 ? 'cmp-delta-down' : 'cmp-delta-neutral';
        const netLbl   = net > 0 ? `+${net}` : String(net);
        const icon     = CAT_ICONS[sec] || '📌';
        const openAttr = hasChanges ? 'open' : '';

        html += `<details class="cmp-cat-block" ${openAttr}>
          <summary class="cmp-cat-header">
            <span class="cmp-cat-chevron">▶</span>
            <span class="cmp-cat-icon">${icon}</span>
            <span class="cmp-cat-name">${_esc(sec.replace(/_/g, ' '))}</span>
            <span class="cmp-count-pill">${d.count_before} → ${d.count_after}</span>
            <span class="cmp-delta ${netCls}">${netLbl}</span>
            ${!hasChanges ? '<span class="cmp-no-change">no changes</span>' : ''}
          </summary>
          <div class="cmp-cat-body">`;

        if (newF.length) {
          html += `<div class="cmp-group-label cmp-label-added">NEW (${newF.length})</div>`;
          newF.slice(0, 8).forEach(item => {
            html += `<div class="cmp-item cmp-item-added">
              <span class="cmp-item-marker">+</span>
              <span>${_esc(String(item).slice(0, 140))}</span>
            </div>`;
          });
          if (newF.length > 8) html += `<p class="cmp-overflow">… and ${newF.length - 8} more</p>`;
        }

        if (resolved.length) {
          html += `<div class="cmp-group-label cmp-label-removed">RESOLVED (${resolved.length})</div>`;
          resolved.slice(0, 8).forEach(item => {
            html += `<div class="cmp-item cmp-item-removed">
              <span class="cmp-item-marker">−</span>
              <span>${_esc(String(item).slice(0, 140))}</span>
            </div>`;
          });
          if (resolved.length > 8) html += `<p class="cmp-overflow">… and ${resolved.length - 8} more</p>`;
        }

        if (d.persistent > 0) {
          html += `<p class="cmp-unchanged-note">
            ${d.persistent} finding${d.persistent !== 1 ? 's' : ''} present in both reviews
          </p>`;
        }

        html += `</div></details>`;
      });
    }

    _setHtml('cmp-result', html);
  }

  function _totalPersistent(sections) {
    return Object.values(sections).reduce((sum, s) => sum + (s.persistent || 0), 0);
  }


  // ── Selector rendering ────────────────────────────────────────────────────

  function _renderVersionSelectors() {
    const versions = _state.versions;
    if (!versions.length) {
      _setHtml('cmp-selectors', `<p class="cmp-empty">No versions found for this project.</p>`);
      return;
    }

    const opts = versions.map(v => {
      const rc  = v.review_count || 0;
      const lbl = v.label ? ` – ${v.label}` : '';
      return `<option value="${_esc(v.version_id)}">`
        + `${_esc(v.version_id)}${_esc(lbl)} `
        + `(${_fmtDateShort(v.created_at)} · ${rc} review${rc !== 1 ? 's' : ''})`
        + `</option>`;
    });

    // Default: pre-select oldest on left, newest on right
    const optA = opts.map((o, i) => i === versions.length - 1
      ? o.replace('<option', '<option selected') : o).join('');
    const optB = opts.map((o, i) => i === 0
      ? o.replace('<option', '<option selected') : o).join('');

    _setHtml('cmp-selectors', `
      <div class="cmp-selector-row">
        <div class="cmp-selector-col">
          <label class="cmp-sel-label cmp-label-a">Version A (before)</label>
          <select id="cmp-sel-a" class="cmp-select cmp-select-a">${optA}</select>
          <div class="cmp-sel-meta" id="cmp-meta-a"></div>
        </div>
        <div class="cmp-selector-divider">⇄</div>
        <div class="cmp-selector-col">
          <label class="cmp-sel-label cmp-label-b">Version B (after)</label>
          <select id="cmp-sel-b" class="cmp-select cmp-select-b">${optB}</select>
          <div class="cmp-sel-meta" id="cmp-meta-b"></div>
        </div>
      </div>
    `);

    // Attach change listeners to refresh meta previews
    const sa = _el('cmp-sel-a');
    const sb = _el('cmp-sel-b');
    if (sa) sa.addEventListener('change', () => _updateVersionMeta('a', sa.value));
    if (sb) sb.addEventListener('change', () => _updateVersionMeta('b', sb.value));
    _updateVersionMeta('a', sa ? sa.value : '');
    _updateVersionMeta('b', sb ? sb.value : '');
  }

  function _updateVersionMeta(side, vid) {
    const v = _state.versions.find(x => x.version_id === vid);
    const el = _el(`cmp-meta-${side}`);
    if (!el) return;
    if (!v) { el.innerHTML = ''; return; }
    const stats = v.stats || {};
    el.innerHTML = `
      <span class="cmp-meta-chip">${_esc(v.persona || 'no persona')}</span>
      <span class="cmp-meta-chip">${_esc(v.ai_backend || 'files_only')}</span>
      ${stats.risks != null ? `<span class="cmp-meta-chip cmp-chip-red">${stats.risks} risks</span>` : ''}
      ${stats.dependencies != null ? `<span class="cmp-meta-chip">${stats.dependencies} deps</span>` : ''}
    `;
  }


  function _renderReviewSelectors() {
    const reviews = _state.reviews;
    if (!reviews.length) {
      _setHtml('cmp-selectors', `<p class="cmp-empty">No reviews found for this project.</p>`);
      return;
    }

    const opts = reviews.map(r => {
      const iter = r.iteration_number ? `R${r.iteration_number}` : r.review_id;
      return `<option value="${_esc(r.review_id)}">`
        + `${_esc(r.review_id)} – ${_esc(iter)} ${_esc(r.persona || '')} `
        + `(${_esc(r.version_id || '')} · ${_fmtDateShort(r.created_at)})`
        + `</option>`;
    });

    const optA = opts.map((o, i) => i === reviews.length - 1
      ? o.replace('<option', '<option selected') : o).join('');
    const optB = opts.map((o, i) => i === 0
      ? o.replace('<option', '<option selected') : o).join('');

    _setHtml('cmp-selectors', `
      <div class="cmp-selector-row">
        <div class="cmp-selector-col">
          <label class="cmp-sel-label cmp-label-a">Review X (before)</label>
          <select id="cmp-sel-a" class="cmp-select cmp-select-a">${optA}</select>
          <div class="cmp-sel-meta" id="cmp-meta-a"></div>
        </div>
        <div class="cmp-selector-divider">⇄</div>
        <div class="cmp-selector-col">
          <label class="cmp-sel-label cmp-label-b">Review Y (after)</label>
          <select id="cmp-sel-b" class="cmp-select cmp-select-b">${optB}</select>
          <div class="cmp-sel-meta" id="cmp-meta-b"></div>
        </div>
      </div>
    `);

    const sa = _el('cmp-sel-a');
    const sb = _el('cmp-sel-b');
    if (sa) sa.addEventListener('change', () => _updateReviewMeta('a', sa.value));
    if (sb) sb.addEventListener('change', () => _updateReviewMeta('b', sb.value));
    _updateReviewMeta('a', sa ? sa.value : '');
    _updateReviewMeta('b', sb ? sb.value : '');
  }

  function _updateReviewMeta(side, rid) {
    const r = _state.reviews.find(x => x.review_id === rid);
    const el = _el(`cmp-meta-${side}`);
    if (!el) return;
    if (!r) { el.innerHTML = ''; return; }
    const tf = r.total_findings || 0;
    el.innerHTML = `
      <span class="cmp-meta-chip cmp-chip-purple">${_esc(r.persona || 'no persona')}</span>
      <span class="cmp-meta-chip">${_esc(r.ai_backend || 'files_only')}</span>
      <span class="cmp-meta-chip">${_esc(r.version_id || '')}</span>
      ${tf ? `<span class="cmp-meta-chip cmp-chip-yellow">${tf} findings</span>` : ''}
      <span class="cmp-meta-chip ${r.quality_status === 'complete' ? 'cmp-chip-green' : ''}">${_esc(r.quality_status || 'pending')}</span>
    `;
  }


  // ── Loading / error helpers ───────────────────────────────────────────────

  function _setLoading(on) {
    _state.loading = on;
    const btn = _el('cmp-run-btn');
    const res = _el('cmp-result');
    if (btn) {
      btn.disabled = on;
      btn.textContent = on ? '⏳ Comparing…' : '⇄  Compare';
    }
    if (on && res) {
      res.innerHTML = `<div class="cmp-loading">
        <span class="cmp-spin">⟳</span> Running comparison…
      </div>`;
    }
  }

  function _showError(msg) {
    _setHtml('cmp-result', `<div class="cmp-error">⚠ ${_esc(msg)}</div>`);
  }

  // ── Mode toggle ───────────────────────────────────────────────────────────

  function _applyMode(mode) {
    _state.mode   = mode;
    _state.result = null;
    _state.error  = null;

    // Update toggle button active state
    ['versions', 'reviews'].forEach(m => {
      const btn = _el(`cmp-mode-${m}`);
      if (btn) btn.classList.toggle('cmp-mode-active', m === mode);
    });

    // Update heading
    const heading = _el('cmp-mode-heading');
    if (heading) {
      heading.textContent = mode === MODES.VERSIONS
        ? 'Compare Versions'
        : 'Compare Reviews';
    }

    // Clear result
    _setHtml('cmp-result', '');

    // Render appropriate selectors (data already loaded in open())
    if (mode === MODES.VERSIONS) {
      _renderVersionSelectors();
    } else {
      _renderReviewSelectors();
    }
  }


  // ── Modal build ───────────────────────────────────────────────────────────

  function _buildModal() {
    // Remove any pre-existing instance
    const existing = _el('cmp-modal-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'cmp-modal-overlay';
    overlay.className = 'cmp-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'cmp-mode-heading');

    overlay.innerHTML = `
      <div class="cmp-modal" id="cmp-modal">
        <div class="cmp-modal-header">
          <div class="cmp-mode-toggle" role="group" aria-label="Compare mode">
            <button id="cmp-mode-versions" class="cmp-mode-btn cmp-mode-active"
              onclick="Compare.setMode('versions')">⚖ Versions</button>
            <button id="cmp-mode-reviews"  class="cmp-mode-btn"
              onclick="Compare.setMode('reviews')">🔍 Reviews</button>
          </div>
          <h2 class="cmp-modal-title" id="cmp-mode-heading">Compare Versions</h2>
          <button class="cmp-close-btn" onclick="Compare.close()"
            aria-label="Close compare panel">✕</button>
        </div>

        <div class="cmp-modal-body">
          <div id="cmp-selectors" class="cmp-selectors-area">
            <div class="cmp-loading"><span class="cmp-spin">⟳</span> Loading data…</div>
          </div>

          <div class="cmp-actions">
            <button id="cmp-run-btn" class="cmp-run-btn" onclick="Compare.run()">
              ⇄  Compare
            </button>
            <button class="cmp-clear-btn" onclick="Compare.clearResult()"
              title="Clear results">Clear</button>
          </div>

          <div id="cmp-result" class="cmp-result-area"></div>
        </div>
      </div>
    `;

    // Close on overlay backdrop click (not on modal itself)
    overlay.addEventListener('click', e => {
      if (e.target === overlay) Compare.close();
    });

    // Close on Escape key
    overlay._keyHandler = e => { if (e.key === 'Escape') Compare.close(); };
    document.addEventListener('keydown', overlay._keyHandler);

    document.body.appendChild(overlay);
    // Trigger CSS transition
    requestAnimationFrame(() => overlay.classList.add('cmp-overlay-visible'));
  }


  // ── Public API ────────────────────────────────────────────────────────────

  const Compare = {

    /**
     * Open the compare modal for a given project.
     * Loads versions and reviews in parallel, then renders selectors.
     */
    async open(projectId) {
      if (!projectId) {
        console.error('Compare.open(): projectId is required');
        return;
      }
      _state.projectId = projectId;
      _state.result    = null;
      _state.error     = null;
      _state.mode      = MODES.VERSIONS;

      _buildModal();

      // Load data in parallel
      await Promise.all([
        _loadVersions(projectId),
        _loadReviews(projectId),
      ]);

      // Render selectors for the default mode
      _applyMode(_state.mode);
    },

    /** Close and remove the modal. */
    close() {
      const overlay = _el('cmp-modal-overlay');
      if (!overlay) return;
      // Remove key handler
      if (overlay._keyHandler) {
        document.removeEventListener('keydown', overlay._keyHandler);
      }
      overlay.classList.remove('cmp-overlay-visible');
      // Remove after transition
      setTimeout(() => { if (overlay.parentNode) overlay.remove(); }, 280);
    },

    /**
     * Switch between 'versions' and 'reviews' mode.
     * @param {'versions'|'reviews'} mode
     */
    setMode(mode) {
      if (mode !== MODES.VERSIONS && mode !== MODES.REVIEWS) return;
      _applyMode(mode);
    },

    /** Execute the current comparison. */
    run() {
      if (_state.loading) return;
      if (_state.mode === MODES.VERSIONS) {
        _runVersionCompare();
      } else {
        _runReviewCompare();
      }
    },

    /** Clear the result panel without closing. */
    clearResult() {
      _state.result = null;
      _state.error  = null;
      _setHtml('cmp-result', '');
    },
  };

  // Expose to global scope
  global.Compare = Compare;

}(window));
