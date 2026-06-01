/**
 * accordion.js — V2 Version Accordion Component
 *
 * TRACE: UI → Logic → API
 * Component: VersionAccordion
 * Calls: AppState.openDrawer(), API.fetchReviews()
 * API: /hierarchy/versions, /hierarchy/reviews
 * Data: Version (1:N) Review
 *
 * Loops:
 *   - Selection loop: click version → expand → load reviews → render
 *   - State update:   AppState.selectVersion() → subscribers update header context
 *
 * Interactions:
 *   - Smooth expand/collapse (CSS max-height transition, 300ms)
 *   - Hover highlight on accordion headers and review items
 *   - Click review → open detail drawer (no navigation)
 *   - Expand all / Collapse all controls
 */

'use strict';

const VersionAccordion = (() => {

  // ── Utilities ─────────────────────────────────────────────
  function _esc(s) {
    if (typeof s !== 'string') s = String(s || '');
    return s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _fmtDate(iso) {
    if (!iso) return '–';
    return iso.slice(0, 10);
  }

  function _relTime(iso) {
    if (!iso) return '';
    const norm = (iso.endsWith('Z') || iso.includes('+')) ? iso : iso + 'Z';
    const diff = Date.now() - new Date(norm).getTime();
    if (isNaN(diff)) return '';
    const m = Math.floor(diff / 60000);
    if (m < 1)  return 'just now';
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
  }

  function _qualityClass(status) {
    if (status === 'complete') return 'badge-green';
    if (status === 'interim')  return 'badge-amber';
    return 'badge-default';
  }

  function _qualityLabel(status) {
    if (status === 'complete') return 'Final';
    if (status === 'interim')  return 'Draft';
    return 'Pending';
  }

  function _statusDotClass(status) {
    if (status === 'complete') return 'complete';
    if (status === 'interim')  return 'in-progress';
    return 'pending';
  }

  // ── Phase tag ─────────────────────────────────────────────
  /**
   * Map phase_id → a coloured inline badge.
   *
   * Colours use CSS custom properties from theme.css.
   * Unknown phase IDs fall back to a neutral badge.
   *
   * @param {string} phaseId  - e.g. 'pre-sales' | 'design' | 'delivery' | 'support'
   * @returns {string} HTML span, or '' if phaseId is blank
   */
  const _PHASE_COLOURS = {
    'pre-sales': 'phase-tag--presales',
    'design':    'phase-tag--design',
    'delivery':  'phase-tag--delivery',
    'support':   'phase-tag--support',
  };

  function _phaseTag(phaseId) {
    if (!phaseId) return '';
    const cls  = _PHASE_COLOURS[phaseId] || 'phase-tag--default';
    const label = phaseId.replace(/-/g, '\u2011');  // non-breaking hyphen for display
    return `<span class="phase-tag ${_esc(cls)}" title="Phase: ${_esc(phaseId)}">${_esc(label)}</span>`;
  }

  // ── Review quality metrics block ──────────────────────────
  /**
   * Computes and renders the Issues / Resolved / Carry Forward metrics row.
   *
   * Source fields (all optional — degrades gracefully when absent):
   *   review.total_findings      → Issues found
   *   review.issues_resolved     → Resolved (explicit field, or derived)
   *   review.issues_carry_forward→ Carry forward (explicit, or total − resolved)
   *
   * Derivation when explicit fields are absent:
   *   - If neither resolved nor carry_forward is set, show only Issues found.
   *   - If resolved is set but carry_forward is not, derive carry_forward.
   *
   * @param {object} review
   * @returns {string} HTML — empty string when no metrics are available
   */
  function _renderReviewMetrics(review) {
    const issues   = review.total_findings      != null ? Number(review.total_findings)       : null;
    const resolved = review.issues_resolved     != null ? Number(review.issues_resolved)      : null;
    let   carry    = review.issues_carry_forward != null ? Number(review.issues_carry_forward) : null;

    // Nothing to show
    if (issues == null && resolved == null && carry == null) return '';

    // Derive carry forward when missing
    if (resolved != null && carry == null && issues != null) {
      carry = Math.max(0, issues - resolved);
    }

    const issuesHtml = issues != null
      ? `<span class="review-metric" title="Issues found in this review">
           <span class="review-metric-icon">🔍</span>
           <span class="review-metric-label">Issues</span>
           <span class="review-metric-value">${issues}</span>
         </span>`
      : '';

    const resolvedHtml = resolved != null
      ? `<span class="review-metric review-metric--resolved" title="Issues resolved since previous review">
           <span class="review-metric-icon">✅</span>
           <span class="review-metric-label">Resolved</span>
           <span class="review-metric-value">${resolved}</span>
         </span>`
      : '';

    const carryHtml = carry != null
      ? `<span class="review-metric review-metric--carry" title="Issues carried forward to next review">
           <span class="review-metric-icon">⏩</span>
           <span class="review-metric-label">Carry fwd</span>
           <span class="review-metric-value">${carry}</span>
         </span>`
      : '';

    return `<div class="review-metrics" aria-label="Review quality metrics">
      ${issuesHtml}${resolvedHtml}${carryHtml}
    </div>`;
  }

  // ── Render a single review row ────────────────────────────
  /**
   * TRACE: UI → ReviewItem → AppState.openDrawer()
   * @param {object} review
   * @param {string} activeReviewId
   * @returns {string} HTML
   */
  function _renderReviewItem(review, activeReviewId) {
    const isActive = review.review_id === activeReviewId;
    const iterLabel = review.iteration_number ? `R${review.iteration_number}` : review.review_id;
    const metricsHtml = _renderReviewMetrics(review);
    return `
      <div class="review-item${isActive ? ' active-review' : ''}"
           role="button"
           tabindex="0"
           aria-label="Review ${_esc(review.review_id)}"
           data-review-id="${_esc(review.review_id)}"
           data-version-id="${_esc(review.version_id || '')}"
           onclick="VersionAccordion.onReviewClick(this)"
           onkeydown="if(event.key==='Enter'||event.key===' ')VersionAccordion.onReviewClick(this)">
        <span class="status-dot ${_statusDotClass(review.quality_status)}" title="${_esc(review.quality_status || 'pending')}"></span>
        <span class="review-item-id">${_esc(iterLabel)}</span>
        <span class="review-item-persona">${_esc(review.persona || '–')}</span>
        ${review.total_findings
          ? `<span class="badge badge-amber">${review.total_findings} findings</span>`
          : ''}
        <span class="badge ${_qualityClass(review.quality_status)}">${_qualityLabel(review.quality_status)}</span>
        ${isActive ? '<span class="badge badge-primary">Active</span>' : ''}
        <span class="review-item-date" title="${_esc(review.created_at || '')}">${_relTime(review.created_at)}</span>
        ${metricsHtml}
      </div>`;
  }

  // ── Render a single version accordion item ────────────────
  /**
   * TRACE: UI → VersionAccordion → AppState.selectVersion()
   * @param {object} version  - version summary from hierarchy tree
   * @param {number} index
   * @returns {string} HTML
   */
  function _renderVersionItem(version, index) {
    const vid = version.version_id || '';
    const label = version.label || '';
    const reviewCount = (version.reviews || []).length;
    const isExpandedByDefault = index === 0; // expand latest by default

    const reviewsHtml = (version.reviews || [])
      .map(r => _renderReviewItem(r, version.active_review_id || ''))
      .join('');

    // RAG health badge — rendered only when HealthSignal is loaded
    const healthBadgeHtml = (window.HealthSignal && version.stats != null)
      ? HealthSignal.renderVersionBadge(version)
      : '';

    // Pin button — rendered only when PinnedInsights is loaded
    const _proj = window.AppState ? window.AppState.get('selectedProject') : null;
    const _projId = _proj ? _proj.id : '';
    const pinBtnHtml = (window.PinnedInsights && _projId)
      ? PinnedInsights.renderPinButton(vid, 'version', vid + (label ? ' – ' + label : ''), _projId)
      : '';

    return `
      <div class="accordion-item${isExpandedByDefault ? ' expanded' : ''}"
           id="accordion-${_esc(vid)}"
           data-version-id="${_esc(vid)}">
        <div class="accordion-header"
             role="button"
             tabindex="0"
             aria-expanded="${isExpandedByDefault}"
             aria-controls="accordion-body-${_esc(vid)}"
             onclick="VersionAccordion.onVersionHeaderClick(this)"
             onkeydown="if(event.key==='Enter'||event.key===' ')VersionAccordion.onVersionHeaderClick(this)">
          <span class="accordion-chevron" aria-hidden="true">▶</span>
          <span class="accordion-version-id">${_esc(vid)}</span>
          ${_phaseTag(version.phase_id || '')}
          ${label ? `<span class="accordion-version-label">– ${_esc(label)}</span>` : ''}
          ${healthBadgeHtml}
          <div class="accordion-meta">
            <span class="badge badge-default">${reviewCount} review${reviewCount !== 1 ? 's' : ''}</span>
            ${version.artifact_count ? `<span class="badge badge-secondary">${version.artifact_count} artefacts</span>` : ''}
            <span class="badge badge-default fs-10">${_fmtDate(version.created_at)}</span>
          </div>
          ${pinBtnHtml}
          <button class="btn-icon btn-sm"
                  title="View version details"
                  aria-label="Open version ${_esc(vid)} detail"
                  onclick="event.stopPropagation();VersionAccordion.onVersionDetailClick(event,'${_esc(vid)}')"
                  style="margin-left:4px">
            ↗
          </button>
        </div>
        <div class="accordion-body"
             id="accordion-body-${_esc(vid)}"
             role="region"
             aria-labelledby="accordion-header-${_esc(vid)}">
          <div class="accordion-body-inner">
            ${reviewsHtml.trim()
              ? `<div class="review-list">${reviewsHtml}</div>`
              : '<p class="text-muted fs-12" style="padding:4px 0">No reviews for this version yet.</p>'
            }
          </div>
        </div>
      </div>`;
  }

  // ── Public: render the full accordion into a container ────
  /**
   * Renders all version items into the given container element.
   * @param {HTMLElement} container
   * @param {Array} versions  - sorted version list (newest first)
   */
  function render(container, versions) {
    if (!container) return;

    if (!versions || versions.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📋</div>
          <div class="empty-state-title">No versions yet</div>
          <p class="empty-state-desc">Build intelligence on the Ingest tab to create the first version snapshot.</p>
        </div>`;
      return;
    }

    container.innerHTML = versions.map(_renderVersionItem).join('');
  }

  // ── Public: render skeleton loading state ─────────────────
  function renderSkeleton(container, count = 3) {
    if (!container) return;
    container.innerHTML = Array.from({ length: count }, () =>
      '<div class="skeleton skeleton-row" style="height:52px;border-radius:12px;margin-bottom:8px"></div>'
    ).join('');
  }

  // ── Event: version header clicked ─────────────────────────
  /**
   * TRACE: UI click → toggle expanded state → update AppState
   * @param {HTMLElement} headerEl
   */
  function onVersionHeaderClick(headerEl) {
    const item = headerEl.closest('.accordion-item');
    if (!item) return;
    const isExpanded = item.classList.contains('expanded');
    const vid = item.dataset.versionId;

    // Toggle this item
    item.classList.toggle('expanded', !isExpanded);
    headerEl.setAttribute('aria-expanded', String(!isExpanded));

    // Update state — triggers header context banner + sidebar highlight
    if (!isExpanded && vid) {
      const state = window.AppState;
      if (!state) return;

      // Find version data from current state
      const versions = state.get('versions') || [];
      const version = versions.find(v => v.version_id === vid) || null;
      state.selectVersion(version);
    }
  }

  // ── Event: version detail button clicked ──────────────────
  /**
   * TRACE: UI click → AppState.openDrawer('version', data)
   * Opens the right-side detail drawer with version info.
   * @param {Event} event
   * @param {string} versionId
   */
  function onVersionDetailClick(event, versionId) {
    event.stopPropagation();
    const state = window.AppState;
    if (!state) return;

    const versions = state.get('versions') || [];
    const version = versions.find(v => v.version_id === versionId);
    if (version) {
      state.selectVersion(version);
      state.openDrawer('version', version);
    }
  }

  // ── Event: review item clicked ────────────────────────────
  /**
   * TRACE: UI click → AppState.selectReview() + AppState.openDrawer('review', data)
   * No page navigation — opens slide-in drawer only.
   * @param {HTMLElement} el - the .review-item element
   */
  function onReviewClick(el) {
    const reviewId = el.dataset.reviewId;
    const versionId = el.dataset.versionId;
    const state = window.AppState;
    if (!state) return;

    // Highlight active review in sidebar
    document.querySelectorAll('.review-item.active-review').forEach(r => {
      r.classList.remove('active-review');
    });
    el.classList.add('active-review');

    // Find review data from current state or in the hierarchy tree
    const versions = state.get('versions') || [];
    let review = null;
    for (const v of versions) {
      const found = (v.reviews || []).find(r => r.review_id === reviewId);
      if (found) { review = found; break; }
    }

    state.selectReview(review);
    state.openDrawer('review', review || { review_id: reviewId, version_id: versionId });
  }

  // ── Public: expand all accordion items ───────────────────
  function expandAll(container) {
    if (!container) return;
    container.querySelectorAll('.accordion-item').forEach(item => {
      item.classList.add('expanded');
      const header = item.querySelector('.accordion-header');
      if (header) header.setAttribute('aria-expanded', 'true');
    });
  }

  // ── Public: collapse all accordion items ─────────────────
  function collapseAll(container) {
    if (!container) return;
    container.querySelectorAll('.accordion-item').forEach(item => {
      item.classList.remove('expanded');
      const header = item.querySelector('.accordion-header');
      if (header) header.setAttribute('aria-expanded', 'false');
    });
  }

  // ── Public: toggle expand all / collapse all ──────────────
  /**
   * @param {HTMLElement} container - accordion wrapper
   * @param {HTMLElement} btn       - the toggle button (text flips)
   */
  function toggleExpandAll(container, btn) {
    const anyExpanded = container && container.querySelector('.accordion-item.expanded');
    if (anyExpanded) {
      collapseAll(container);
      if (btn) btn.textContent = 'Expand All';
    } else {
      expandAll(container);
      if (btn) btn.textContent = 'Collapse All';
    }
  }

  return {
    render,
    renderSkeleton,
    expandAll,
    collapseAll,
    toggleExpandAll,
    onVersionHeaderClick,
    onVersionDetailClick,
    onReviewClick,
  };

})();

window.VersionAccordion = VersionAccordion;
