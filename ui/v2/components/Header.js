/**
 * Header.js — V2 Sticky Header Component
 *
 * TRACE: UI → Logic → API
 * Component: Header
 * Inputs:  AppState (projects, selectedProject, selectedVersion, selectedReview)
 * Outputs: DOM mutations to #v2-header children
 * API:     None (reads from AppState only)
 *
 * Responsibilities:
 *  - Project dropdown (searchable via datalist)
 *  - Version dropdown (filtered by selectedProject)
 *  - Review dropdown (filtered by selectedVersion)
 *  - Last-updated timestamp display
 *  - Refresh button (triggers Dashboard.loadAll, no page reload)
 *  - Context label: "Version → Review" always visible
 *
 * Selection loop:
 *   User selects project → Dashboard.onProjectChange()
 *     → AppState.selectProject() → state subscribers re-render
 *   User selects version → Dashboard.onVersionChange()
 *     → AppState.selectVersion() → review dropdown updates
 *   User selects review  → Dashboard.onReviewChange()
 *     → AppState.selectReview()  → metrics refresh
 */

'use strict';

const Header = (() => {

  function _esc(s) {
    if (typeof s !== 'string') s = String(s || '');
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _fmtDateShort(iso) {
    if (!iso) return '';
    return iso.slice(0, 10);
  }

  /**
   * Build the full header HTML string.
   * Called once at init; dropdowns update in-place via DOM after that.
   *
   * @param {Array}  projects        - [{id, name, phase}]
   * @param {object|null} selProject
   * @param {Array}  versions        - [{version_id, label, created_at}]
   * @param {object|null} selVersion
   * @param {Array}  reviews         - [{review_id, persona, created_at}]
   * @param {object|null} selReview
   * @returns {string} HTML
   */
  function render(projects, selProject, versions, selVersion, reviews, selReview) {
    const projectOpts = (projects || []).map(p =>
      `<option value="${_esc(p.id)}" ${selProject && selProject.id === p.id ? 'selected' : ''}>${_esc(p.name)}</option>`
    ).join('');

    const versionOpts =
      '<option value="">Latest Version</option>' +
      (versions || []).map(v =>
        `<option value="${_esc(v.version_id)}" ${selVersion && selVersion.version_id === v.version_id ? 'selected' : ''}>${_esc(v.version_id)}${v.label ? ' – ' + _esc(v.label) : ''} (${_fmtDateShort(v.created_at)})</option>`
      ).join('');

    const reviewOpts =
      '<option value="">Active Review</option>' +
      (reviews || []).map(r =>
        `<option value="${_esc(r.review_id)}" ${selReview && selReview.review_id === r.review_id ? 'selected' : ''}>${_esc(r.review_id)} – ${_esc(r.persona || '')} (${_fmtDateShort(r.created_at)})</option>`
      ).join('');

    const ctxVersion = selVersion
      ? `<span class="ctx-value">${_esc(selVersion.version_id)}${selVersion.label ? ' · ' + _esc(selVersion.label) : ''}</span>`
      : '<span class="ctx-value text-muted">–</span>';

    const ctxReview = selReview
      ? `<span class="ctx-value">${_esc(selReview.review_id)}${selReview.persona ? ' · ' + _esc(selReview.persona) : ''}</span>`
      : '<span class="text-muted">Active</span>';

    return `
      <div class="header-logo">
        ⚡ <span>Contexta <span class="logo-accent">v2</span></span>
        <span class="v2-badge">BETA</span>
      </div>

      <div class="header-controls">
        <!-- Project dropdown -->
        <div class="v2-select-wrap" style="min-width:180px">
          <select id="v2-project-select"
                  aria-label="Select project"
                  onchange="Dashboard.onProjectChange(this)">
            ${projectOpts}
          </select>
        </div>

        <!-- Version dropdown -->
        <div class="v2-select-wrap" style="min-width:160px">
          <select id="v2-version-select"
                  aria-label="Select version"
                  onchange="Dashboard.onVersionChange(this)">
            ${versionOpts}
          </select>
        </div>

        <!-- Review dropdown -->
        <div class="v2-select-wrap" style="min-width:170px">
          <select id="v2-review-select"
                  aria-label="Select review"
                  onchange="Dashboard.onReviewChange(this)">
            ${reviewOpts}
          </select>
        </div>

        <!-- Refresh button (no reload) -->
        <button id="v2-refresh-btn"
                class="btn-icon"
                title="Refresh data (no page reload)"
                aria-label="Refresh"
                onclick="Dashboard.onRefresh()">
          ↺
        </button>
      </div>

      <!-- Context label: Version → Review always visible -->
      <div class="header-context" aria-label="Current context">
        <span class="ctx-label">Showing:</span>
        <span id="v2-ctx-version">${ctxVersion}</span>
        <span class="ctx-sep">→</span>
        <span id="v2-ctx-review">${ctxReview}</span>
      </div>

      <div class="header-last-updated" id="v2-last-updated" aria-live="polite"></div>`;
  }

  /**
   * Mount the header into its container element.
   * @param {HTMLElement} container - #v2-header
   * @param {object} stateSnapshot
   */
  function mount(container, stateSnapshot) {
    if (!container) return;
    const s = stateSnapshot || {};
    container.innerHTML = render(
      s.projects       || [],
      s.selectedProject || null,
      s.versions        || [],
      s.selectedVersion || null,
      (s.metrics && s.metrics.available_reviews) || [],
      s.selectedReview  || null
    );
  }

  return { render, mount };
})();

// Expose for use in dashboard_v2.html and dashboard.js
if (typeof window !== 'undefined') window.Header = Header;
