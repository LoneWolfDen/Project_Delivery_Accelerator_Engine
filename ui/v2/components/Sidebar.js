/**
 * Sidebar.js — V2 Left Panel Component
 *
 * TRACE: UI → Logic → API
 * Component: Sidebar
 * Inputs:  AppState (versions, selectedVersion, selectedReview)
 * Outputs: DOM mutations to #v2-sidebar-version-list
 * API:     None (reads from AppState; triggers Dashboard.onSidebarVersionClick)
 *
 * Responsibilities:
 *  - Render version list (collapsed by default)
 *  - Expand a version to reveal its reviews inline
 *  - Highlight the currently selected version and review
 *  - Compact toggle (smaller row height)
 *  - Expand all / Collapse all controls
 *
 * Selection loop:
 *   Click version  → toggle expand + AppState.selectVersion()
 *   Click review   → AppState.selectReview() + AppState.openDrawer()
 *   AppState change → re-render highlights (no full rebuild)
 */

'use strict';

const Sidebar = (() => {

  function _esc(s) {
    if (typeof s !== 'string') s = String(s || '');
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  let _compact = false;

  // ── Render one review row ─────────────────────────────────
  function _reviewRow(r, versionId, activeReviewId, selectedReviewId) {
    const isActive   = r.review_id === activeReviewId;
    const isSelected = r.review_id === selectedReviewId;
    const iter = r.iteration_number ? `R${r.iteration_number}` : r.review_id;
    return `
      <div class="sidebar-review-item${isSelected ? ' active' : ''}"
           data-review-id="${_esc(r.review_id)}"
           data-version-id="${_esc(versionId)}"
           role="button" tabindex="0"
           aria-label="Review ${_esc(r.review_id)}"
           onclick="Dashboard.onSidebarReviewClick(this)"
           onkeydown="if(event.key==='Enter'||event.key===' ')Dashboard.onSidebarReviewClick(this)">
        <span class="text-muted" style="font-size:9px;flex-shrink:0">${_esc(iter)}</span>
        <span class="truncate">${_esc(r.persona || r.review_id)}</span>
        ${isActive
          ? '<span class="badge badge-primary" style="font-size:9px;padding:1px 5px;flex-shrink:0">●</span>'
          : ''}
      </div>`;
  }

  // ── Render one version row ────────────────────────────────
  function _versionRow(v, selectedVersionId, selectedReviewId, isFirstItem) {
    const isSelected = v.version_id === selectedVersionId;
    // Expand: first item OR currently selected version
    const isExpanded = isFirstItem || isSelected;
    const rCount     = (v.reviews || []).length;
    const rowsHtml   = (v.reviews || [])
      .map(r => _reviewRow(r, v.version_id, v.active_review_id, selectedReviewId))
      .join('');

    return `
      <div class="sidebar-version-item${isExpanded ? ' expanded' : ''}"
           id="sidebar-v-${_esc(v.version_id)}">
        <div class="sidebar-version-header${isSelected ? ' active' : ''}"
             role="button" tabindex="0"
             aria-expanded="${isExpanded}"
             aria-label="Version ${_esc(v.version_id)}"
             onclick="Dashboard.onSidebarVersionClick(this,'${_esc(v.version_id)}')"
             onkeydown="if(event.key==='Enter'||event.key===' ')Dashboard.onSidebarVersionClick(this,'${_esc(v.version_id)}')">
          <span class="sidebar-chevron">▶</span>
          <span class="sidebar-version-label">
            <strong>${_esc(v.version_id)}</strong>${v.label ? ' <span class="text-muted">– ' + _esc(v.label) + '</span>' : ''}
          </span>
          <span class="badge badge-default" style="font-size:9px">${rCount}</span>
        </div>
        <div class="sidebar-review-list">
          ${rowsHtml || '<p class="text-muted" style="font-size:11px;padding:4px 8px">No reviews</p>'}
        </div>
      </div>`;
  }

  // ── Render controls bar ───────────────────────────────────
  function _controlsBar() {
    return `
      <div class="sidebar-controls">
        <button class="btn btn-xs btn-ghost" id="sidebar-expand-all-btn"
                onclick="Sidebar.toggleExpandAll()"
                aria-label="Expand or collapse all versions">
          Expand All
        </button>
        <button class="btn btn-xs btn-ghost" id="sidebar-compact-btn"
                onclick="Sidebar.toggleCompact()"
                aria-label="Toggle compact view"
                title="Compact view">
          ${_compact ? 'Full' : 'Compact'}
        </button>
      </div>`;
  }

  // ── Public: render full sidebar list ─────────────────────
  /**
   * @param {HTMLElement} container   - #v2-sidebar-version-list
   * @param {Array}  versions         - sorted version list
   * @param {string} selectedVersionId
   * @param {string} selectedReviewId
   */
  function render(container, versions, selectedVersionId, selectedReviewId) {
    if (!container) return;

    if (!versions || versions.length === 0) {
      container.innerHTML = `
        <p class="text-muted" style="font-size:11px;padding:8px 4px">
          No versions yet. Build intelligence to create a snapshot.
        </p>`;
      return;
    }

    const rows = versions
      .map((v, idx) => _versionRow(v, selectedVersionId, selectedReviewId, idx === 0))
      .join('');

    container.innerHTML = _controlsBar() + rows;

    if (_compact) container.classList.add('compact');
    else          container.classList.remove('compact');
  }

  // ── Public: highlight selected version/review in-place ───
  // Called when state changes without full re-render
  function updateHighlights(selectedVersionId, selectedReviewId) {
    document.querySelectorAll('.sidebar-version-header').forEach(el => {
      const item = el.closest('.sidebar-version-item');
      const vid  = item ? item.id.replace('sidebar-v-', '') : '';
      el.classList.toggle('active', vid === selectedVersionId);
    });
    document.querySelectorAll('.sidebar-review-item').forEach(el => {
      el.classList.toggle('active', el.dataset.reviewId === selectedReviewId);
    });
  }

  // ── Public: toggle expand all / collapse all ──────────────
  function toggleExpandAll() {
    const btn  = document.getElementById('sidebar-expand-all-btn');
    const items = document.querySelectorAll('.sidebar-version-item');
    const anyExpanded = [...items].some(i => i.classList.contains('expanded'));
    items.forEach(i => {
      i.classList.toggle('expanded', !anyExpanded);
      const h = i.querySelector('.sidebar-version-header');
      if (h) h.setAttribute('aria-expanded', String(!anyExpanded));
    });
    if (btn) btn.textContent = anyExpanded ? 'Expand All' : 'Collapse All';
  }

  // ── Public: toggle compact mode ───────────────────────────
  function toggleCompact() {
    _compact = !_compact;
    const btn = document.getElementById('sidebar-compact-btn');
    if (btn) btn.textContent = _compact ? 'Full' : 'Compact';
    const list = document.getElementById('v2-sidebar-version-list');
    if (list) list.classList.toggle('compact', _compact);
  }

  return { render, updateHighlights, toggleExpandAll, toggleCompact };
})();

if (typeof window !== 'undefined') window.Sidebar = Sidebar;
