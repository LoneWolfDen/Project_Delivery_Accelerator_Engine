/**
 * dashboard.js — V2 Dashboard Orchestrator
 *
 * TRACE: UI → Logic → API → Data
 * Component: Dashboard (main controller)
 * Wires: Header, Sidebar, SnapshotCards, VersionAccordion, DetailPanel
 * APIs used:
 *   - /api/projects                     → project list
 *   - /hierarchy                        → full tree
 *   - /hierarchy/metrics                → snapshot card data
 *   - /hierarchy/versions               → accordion
 *   - /hierarchy/reviews                → review items
 *   - /hierarchy/reviews/{rid}          → drawer detail
 *   - /hierarchy/versions/{vid}         → drawer detail
 *
 * Loops:
 *   1. Refresh loop:   RefreshBtn → loadAll() → setData() → re-render
 *   2. Selection loop: Dropdown/Accordion → selectVersion/Review → re-render cards + context
 *   3. State loop:     AppState.subscribe() → partial DOM updates (no full reload)
 */

'use strict';

const Dashboard = (() => {

  // ── DOM refs (resolved once at init) ─────────────────────
  let _dom = {};

  function _refs() {
    _dom = {
      projectSelect:    document.getElementById('v2-project-select'),
      versionSelect:    document.getElementById('v2-version-select'),
      reviewSelect:     document.getElementById('v2-review-select'),
      refreshBtn:       document.getElementById('v2-refresh-btn'),
      lastUpdated:      document.getElementById('v2-last-updated'),
      contextVersion:   document.getElementById('v2-ctx-version'),
      contextReview:    document.getElementById('v2-ctx-review'),
      contextBanner:    document.getElementById('v2-context-banner'),
      snapshotGrid:     document.getElementById('v2-snapshot-grid'),
      activityStrip:    document.getElementById('v2-activity-strip'),
      accordionWrap:    document.getElementById('v2-accordion-wrap'),
      expandAllBtn:     document.getElementById('v2-expand-all-btn'),
      sidebarList:      document.getElementById('v2-sidebar-version-list'),
      drawer:           document.getElementById('v2-drawer'),
      drawerContent:    document.getElementById('v2-drawer-content'),
      drawerCloseBtn:   document.getElementById('v2-drawer-close'),
      main:             document.getElementById('v2-main'),
      toast:            document.getElementById('v2-toast'),
    };
  }

  // ── Toast ────────────────────────────────────────────────
  let _toastTimer = null;
  function _toast(msg, type = 'ok') {
    if (!_dom.toast) return;
    _dom.toast.textContent = msg;
    _dom.toast.className = `show toast-${type}`;
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => { _dom.toast.className = ''; }, 3000);
  }

  // ── Utilities ────────────────────────────────────────────
  function _esc(s) {
    if (typeof s !== 'string') s = String(s || '');
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function _fmtDate(iso) {
    if (!iso) return '–';
    return iso.slice(0, 16).replace('T', ' ');
  }
  function _fmtDateShort(iso) {
    if (!iso) return '–';
    return iso.slice(0, 10);
  }

  // ── Recent Activity Strip ─────────────────────────────────
  /**
   * Event type metadata: icon, label, colour class.
   * TRACE: UI → ActivityStrip → AppState (recentActivity)
   */
  const _ACTIVITY_META = {
    version_created:  { icon: '📋', label: 'created',   cls: 'activity-type--version'  },
    review_created:   { icon: '🔍', label: 'reviewed',  cls: 'activity-type--review'   },
    review_completed: { icon: '✅', label: 'completed', cls: 'activity-type--complete'  },
  };

  /**
   * Render the recent activity horizontal strip.
   * Called by renderAll(); targets #v2-activity-strip.
   *
   * @param {HTMLElement} el
   * @param {Array} events  - ActivityEvent[] sorted newest-first
   */
  function _renderActivityStrip(el, events) {
    if (!el) return;
    if (!events || events.length === 0) {
      el.innerHTML = '';
      el.style.display = 'none';
      return;
    }
    el.style.display = '';

    const items = events.map(ev => {
      const meta = _ACTIVITY_META[ev.type] || { icon: '•', label: ev.type, cls: '' };
      const relT = _relTime(ev.timestamp);
      return `
        <span class="activity-item ${_esc(meta.cls)}" title="${_esc(ev.label)} · ${_esc(relT)}">
          <span class="activity-item-icon" aria-hidden="true">${meta.icon}</span>
          <span class="activity-item-id">${_esc(ev.id)}</span>
          <span class="activity-item-label">${meta.label}</span>
          ${relT ? `<span class="activity-item-time">${_esc(relT)}</span>` : ''}
        </span>`;
    }).join('<span class="activity-sep" aria-hidden="true">·</span>');

    el.innerHTML = `
      <span class="activity-strip-label">Recent:</span>
      <div class="activity-items" role="list" aria-label="Recent activity">${items}</div>`;
  }

  /**
   * Utility: relative time (mirrors Helpers.relTime without the dependency).
   */
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

  // ── Smart Defaulting ─────────────────────────────────────
  /**
   * Resolve default version + review selection from a sorted version list.
   *
   * Rules:
   *   1. Latest version by created_at (index 0, already sorted newest-first).
   *   2. Active review for that version (active_review_id match), else newest.
   *
   * Only applies when selectedVersion is null (project just loaded or switched).
   * Does NOT override an explicit user selection.
   *
   * TRACE: SmartDefault → AppState.selectVersion() + AppState.selectReview()
   *
   * @param {Array} versions - sorted newest-first
   */
  function _resolveDefaults(versions) {
    const state = window.AppState;
    if (state.get('selectedVersion')) return;  // user already chose
    if (!versions || versions.length === 0) return;

    const latest = versions[0];
    state.selectVersion(latest);

    const reviews = latest.reviews || [];
    const activeReview =
      reviews.find(r => r.review_id === latest.active_review_id) ||
      reviews[0] ||
      null;
    state.selectReview(activeReview);
  }

  // ── Load all data for selected project ───────────────────
  /**
   * TRACE: Refresh loop → API calls → AppState.setData() → re-render
   * @param {boolean} [silent] - suppress loading indicators if true
   */
  async function loadAll(silent = false) {
    const state  = window.AppState;
    const api    = window.API;
    const proj   = state.get('selectedProject');
    if (!proj) return;

    if (!silent) state.set('loading', true);

    try {
      // Parallel: hierarchy + metrics for latest version
      const [hierarchy, metrics] = await Promise.all([
        api.fetchHierarchy(proj.id),
        api.fetchMetrics(
          proj.id,
          state.get('selectedVersion')?.version_id,
          state.get('selectedReview')?.review_id
        ),
      ]);

      // Extract flat version list from hierarchy tree (newest first)
      const versions = [];
      ((hierarchy && hierarchy.tree) || []).forEach(phase => {
        (phase.versions || []).forEach(v => versions.push(v));
      });
      versions.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

      // Derive recent activity events from hierarchy (no extra fetch)
      const recentActivity = api._deriveActivityEvents
        ? api._deriveActivityEvents(hierarchy)
        : [];

      state.setData({ hierarchy, metrics, versions, recentActivity });

      // Smart defaulting: always resolve on load (only applies when nothing selected)
      _resolveDefaults(versions);

    } catch (err) {
      _toast('Failed to load data', 'err');
      state.set('loading', false);
    }
  }

  // ── Populate project dropdown ─────────────────────────────
  function _populateProjectDropdown(projects) {
    if (!_dom.projectSelect) return;
    const current = window.AppState.get('selectedProject');
    _dom.projectSelect.innerHTML = projects.map(p =>
      `<option value="${_esc(p.id)}" ${current && current.id === p.id ? 'selected' : ''}>${_esc(p.name)}</option>`
    ).join('');
  }

  // ── Populate version dropdown (header) ────────────────────
  function _populateVersionDropdown(versions) {
    if (!_dom.versionSelect) return;
    const current = window.AppState.get('selectedVersion');
    _dom.versionSelect.innerHTML =
      '<option value="">Latest Version</option>' +
      versions.map(v =>
        `<option value="${_esc(v.version_id)}" ${current && current.version_id === v.version_id ? 'selected' : ''}>${_esc(v.version_id)}${v.label ? ' – ' + _esc(v.label) : ''} (${_fmtDateShort(v.created_at)})</option>`
      ).join('');
  }

  // ── Populate review dropdown (header) ─────────────────────
  function _populateReviewDropdown(reviews) {
    if (!_dom.reviewSelect) return;
    const current = window.AppState.get('selectedReview');
    _dom.reviewSelect.innerHTML =
      '<option value="">Active Review</option>' +
      reviews.map(r =>
        `<option value="${_esc(r.review_id)}" ${current && current.review_id === r.review_id ? 'selected' : ''}>${_esc(r.review_id)} – ${_esc(r.persona || '')} (${_fmtDateShort(r.created_at)})</option>`
      ).join('');
  }

  // ── Render snapshot cards ─────────────────────────────────
  /**
   * TRACE: UI → SnapshotCards → metrics data
   * Component: Cards.js (referenced) / rendered here for dashboard
   */
  function _renderSnapshotCards(metrics) {
    if (!_dom.snapshotGrid) return;
    if (!metrics) {
      _dom.snapshotGrid.innerHTML = '<div class="skeleton snapshot-card skeleton-card"></div>'.repeat(3);
      return;
    }
    const totalV = metrics.total_versions || 0;
    const totalR = metrics.total_reviews  || 0;
    const ds     = metrics.data_source    || {};
    const latest = ds.version_label || ds.version || '–';

    _dom.snapshotGrid.innerHTML = `
      <div class="snapshot-card" tabindex="0" role="button" title="Total versions across all phases" aria-label="${totalV} versions">
        <div class="snapshot-card-value">${totalV}</div>
        <div class="snapshot-card-label">Versions</div>
        <div class="snapshot-card-sub">across all phases</div>
      </div>
      <div class="snapshot-card" tabindex="0" role="button" title="Total reviews run" aria-label="${totalR} reviews">
        <div class="snapshot-card-value">${totalR}</div>
        <div class="snapshot-card-label">Reviews</div>
        <div class="snapshot-card-sub">all versions</div>
      </div>
      <div class="snapshot-card green" tabindex="0" role="button" title="Active version" aria-label="Active version ${latest}">
        <div class="snapshot-card-value" style="font-size:18px;padding-top:6px">${_esc(latest)}</div>
        <div class="snapshot-card-label">Active Version</div>
        <div class="snapshot-card-sub">${ds.phase ? _esc(ds.phase) : '–'}</div>
      </div>
      <div class="snapshot-card ${(metrics.risks_identified || 0) > 0 ? 'red' : 'green'}" tabindex="0" title="Risks identified in selected review">
        <div class="snapshot-card-value">${metrics.risks_identified || 0}</div>
        <div class="snapshot-card-label">Risks</div>
        <div class="snapshot-card-sub">selected review</div>
      </div>
      <div class="snapshot-card amber" tabindex="0" title="Gaps identified in selected review">
        <div class="snapshot-card-value">${metrics.gaps_identified || 0}</div>
        <div class="snapshot-card-label">Gaps</div>
        <div class="snapshot-card-sub">selected review</div>
      </div>
      ${metrics.total_findings ? `
      <div class="snapshot-card purple" tabindex="0" title="Total findings in selected review">
        <div class="snapshot-card-value">${metrics.total_findings}</div>
        <div class="snapshot-card-label">Findings</div>
        <div class="snapshot-card-sub">selected review</div>
      </div>` : ''}`;
  }

  // ── Render context banner ─────────────────────────────────
  function _renderContextBanner() {
    const state    = window.AppState;
    const version  = state.get('selectedVersion');
    const review   = state.get('selectedReview');
    if (!_dom.contextBanner) return;
    if (version) {
      _dom.contextBanner.classList.remove('hidden');
      if (_dom.contextVersion) {
        _dom.contextVersion.textContent = version.version_id + (version.label ? ' – ' + version.label : '');
      }
      if (_dom.contextReview) {
        _dom.contextReview.textContent = review
          ? (review.review_id + (review.persona ? ' · ' + review.persona : ''))
          : 'Active Review';
      }
    } else {
      _dom.contextBanner.classList.add('hidden');
    }
  }

  // ── Render sidebar version list ───────────────────────────
  /**
   * TRACE: UI → Sidebar → AppState.selectVersion()
   */
  function _renderSidebar(versions) {
    if (!_dom.sidebarList) return;
    const state   = window.AppState;
    const selVid  = state.get('selectedVersion')?.version_id;
    const selRid  = state.get('selectedReview')?.review_id;

    if (!versions || versions.length === 0) {
      _dom.sidebarList.innerHTML = '<p class="text-muted fs-11" style="padding:8px">No versions</p>';
      return;
    }

    _dom.sidebarList.innerHTML = versions.map(v => {
      const rCount = (v.reviews || []).length;
      const isSelV = v.version_id === selVid;
      const reviewItems = (v.reviews || []).map(r => {
        const isSelR = r.review_id === selRid;
        return `
          <div class="sidebar-review-item${isSelR ? ' active' : ''}"
               data-review-id="${_esc(r.review_id)}"
               data-version-id="${_esc(v.version_id)}"
               onclick="Dashboard.onSidebarReviewClick(this)"
               role="button" tabindex="0"
               onkeydown="if(event.key==='Enter')Dashboard.onSidebarReviewClick(this)">
            <span style="color:var(--text-muted);font-size:9px">R${r.iteration_number || '?'}</span>
            <span>${_esc(r.persona || r.review_id)}</span>
            ${r.review_id === v.active_review_id ? '<span class="badge badge-primary" style="font-size:9px;padding:1px 5px">●</span>' : ''}
          </div>`;
      }).join('');

      return `
        <div class="sidebar-version-item${isSelV ? ' expanded' : ''}" id="sidebar-v-${_esc(v.version_id)}">
          <div class="sidebar-version-header${isSelV ? ' active' : ''}"
               onclick="Dashboard.onSidebarVersionClick(this,'${_esc(v.version_id)}')"
               role="button" tabindex="0"
               onkeydown="if(event.key==='Enter')Dashboard.onSidebarVersionClick(this,'${_esc(v.version_id)}')">
            <span class="sidebar-chevron">▶</span>
            <span class="sidebar-version-label">${_esc(v.version_id)}${v.label ? ' – ' + _esc(v.label) : ''}</span>
            <span class="badge badge-default" style="font-size:9px">${rCount}</span>
          </div>
          <div class="sidebar-review-list">
            ${reviewItems || '<p class="text-muted fs-11" style="padding:4px 8px">No reviews</p>'}
          </div>
        </div>`;
    }).join('');
  }

  // ── Render last updated timestamp ─────────────────────────
  function _renderLastUpdated(iso) {
    if (!_dom.lastUpdated) return;
    if (!iso) { _dom.lastUpdated.textContent = ''; return; }
    const d = new Date(iso);
    _dom.lastUpdated.textContent = 'Updated ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // ── Full render cycle ─────────────────────────────────────
  /**
   * Re-renders all dynamic regions using current AppState.
   * Called after state changes; partial regions update independently.
   */
  function renderAll() {
    const state    = window.AppState;
    const metrics  = state.get('metrics');
    const versions = state.get('versions') || [];
    const activity = state.get('recentActivity') || [];

    _renderActivityStrip(_dom.activityStrip, activity);
    _renderSnapshotCards(metrics);
    _renderContextBanner();
    _renderSidebar(versions);
    _populateVersionDropdown(versions);

    // Review dropdown uses available_reviews from metrics (scoped to selected version)
    const availableReviews = (metrics && metrics.available_reviews) || [];
    _populateReviewDropdown(availableReviews);

    // Accordion
    VersionAccordion.render(_dom.accordionWrap, versions);

    // Last updated
    _renderLastUpdated(state.get('lastUpdated'));
  }

  // ── Drawer logic ─────────────────────────────────────────
  /**
   * TRACE: State → Drawer open/close
   * Listens: AppState 'drawerOpen'
   */
  function _syncDrawer(drawerOpen, drawerEntity) {
    if (!_dom.drawer || !_dom.main) return;
    if (drawerOpen && drawerEntity) {
      _dom.drawer.classList.add('open');
      _dom.main.classList.add('drawer-open');
      _renderDrawerContent(drawerEntity);
    } else {
      _dom.drawer.classList.remove('open');
      _dom.main.classList.remove('drawer-open');
    }
  }

  function _renderDrawerContent(entity) {
    if (!_dom.drawerContent) return;
    if (entity.type === 'version') {
      _dom.drawerContent.innerHTML = window.DetailPanel
        ? DetailPanel.renderVersion(entity.data)
        : _fallbackVersionDetail(entity.data);
    } else if (entity.type === 'review') {
      // Prefer ReviewDetail (Sprint 1), fall back to DetailPanel alias, then inline fallback
      const renderer = window.ReviewDetail || window.DetailPanel;
      _dom.drawerContent.innerHTML = renderer
        ? renderer.renderReview(entity.data)
        : _fallbackReviewDetail(entity.data);
    }
    // Async: load full detail and update
    _loadDrawerDetail(entity);
  }

  async function _loadDrawerDetail(entity) {
    const state = window.AppState;
    const proj  = state.get('selectedProject');
    if (!proj || !window.API) return;
    try {
      let full;
      if (entity.type === 'review' && entity.data.review_id) {
        full = await API.fetchReviewDetail(proj.id, entity.data.review_id);
        if (full && !full.error && _dom.drawerContent) {
          const renderer = window.ReviewDetail || window.DetailPanel;
          _dom.drawerContent.innerHTML = renderer
            ? renderer.renderReview(full)
            : _fallbackReviewDetail(full);
        }
      } else if (entity.type === 'version' && entity.data.version_id) {
        full = await API.fetchVersionDetail(proj.id, entity.data.version_id);
        if (full && !full.error && _dom.drawerContent) {
          _dom.drawerContent.innerHTML = window.DetailPanel
            ? DetailPanel.renderVersion(full)
            : _fallbackVersionDetail(full);
        }
      }
    } catch (e) {
      // Non-blocking: drawer already shows summary
    }
  }

  // Minimal fallback if DetailPanel not loaded yet
  function _fallbackVersionDetail(v) {
    return `<div class="detail-row"><div class="detail-row-label">Version</div><div class="detail-row-value">${_esc(v.version_id || '')}</div></div>
            <div class="detail-row"><div class="detail-row-label">Label</div><div class="detail-row-value">${_esc(v.label || '–')}</div></div>
            <div class="detail-row"><div class="detail-row-label">Created</div><div class="detail-row-value">${_fmtDate(v.created_at)}</div></div>`;
  }
  function _fallbackReviewDetail(r) {
    return `<div class="detail-row"><div class="detail-row-label">Review</div><div class="detail-row-value">${_esc(r.review_id || '')}</div></div>
            <div class="detail-row"><div class="detail-row-label">Persona</div><div class="detail-row-value">${_esc(r.persona || '–')}</div></div>
            <div class="detail-row"><div class="detail-row-label">Summary</div><div class="detail-row-value">${_esc(r.summary || '–')}</div></div>`;
  }

  // ── Event handlers ────────────────────────────────────────

  function onProjectChange(selectEl) {
    const state = window.AppState;
    const id    = selectEl.value;
    const projects = state.get('projects') || [];
    const proj = projects.find(p => p.id === id) || null;
    state.selectProject(proj);
    if (proj) loadAll();
  }

  function onVersionChange(selectEl) {
    const state    = window.AppState;
    const vid      = selectEl.value;
    const versions = state.get('versions') || [];
    const version  = versions.find(v => v.version_id === vid) || null;
    state.selectVersion(version);
    // Update review dropdown immediately from this version's reviews
    const reviews = (version && version.reviews) || [];
    _populateReviewDropdown(reviews);
    state.set('reviews', reviews);
    // Refresh metrics for new version
    const proj = state.get('selectedProject');
    if (proj) {
      state.set('loadingMetrics', true);
      API.fetchMetrics(proj.id, vid, null).then(m => {
        state.setData({ metrics: m });
        _renderSnapshotCards(m);
        _renderContextBanner();
      });
    }
  }

  function onReviewChange(selectEl) {
    const state    = window.AppState;
    const rid      = selectEl.value;
    const versions = state.get('versions') || [];
    let review = null;
    for (const v of versions) {
      review = (v.reviews || []).find(r => r.review_id === rid) || null;
      if (review) break;
    }
    state.selectReview(review);
    // Refresh metrics scoped to this review
    const proj    = state.get('selectedProject');
    const version = state.get('selectedVersion');
    if (proj) {
      API.fetchMetrics(proj.id, version?.version_id, rid).then(m => {
        state.setData({ metrics: m });
        _renderSnapshotCards(m);
        _renderContextBanner();
      });
    }
  }

  function onRefresh() {
    _toast('Refreshing…');
    loadAll();
  }

  function onExpandAll() {
    VersionAccordion.toggleExpandAll(_dom.accordionWrap, _dom.expandAllBtn);
  }

  function onCloseDrawer() {
    window.AppState.closeDrawer();
  }

  function onSidebarVersionClick(headerEl, vid) {
    const item = headerEl.closest('.sidebar-version-item');
    if (item) item.classList.toggle('expanded');
    const state    = window.AppState;
    const versions = state.get('versions') || [];
    const version  = versions.find(v => v.version_id === vid) || null;
    state.selectVersion(version);
    _renderContextBanner();
  }

  function onSidebarReviewClick(el) {
    const rid = el.dataset.reviewId;
    const vid = el.dataset.versionId;
    const state    = window.AppState;
    const versions = state.get('versions') || [];
    let review = null;
    for (const v of versions) {
      review = (v.reviews || []).find(r => r.review_id === rid) || null;
      if (review) break;
    }
    state.selectReview(review);
    state.openDrawer('review', review || { review_id: rid, version_id: vid });
    // Update sidebar highlight
    document.querySelectorAll('.sidebar-review-item.active').forEach(e => e.classList.remove('active'));
    el.classList.add('active');
    _renderContextBanner();
  }

  // ── Bootstrap ─────────────────────────────────────────────
  async function init() {
    _refs();
    const state = window.AppState;
    const api   = window.API;

    // 1. Load project list
    state.set('loading', true);
    const { projects = [] } = await api.fetchProjects();
    state.set('projects', projects);
    _populateProjectDropdown(projects);

    // 2. Auto-select first project
    if (projects.length > 0) {
      state.selectProject(projects[0]);
      await loadAll();
    } else {
      state.set('loading', false);
    }

    // 3. Wire up AppState subscribers (no-reload updates)
    //    Selection loop: project/version/review changes → re-render
    state.subscribe(['versions', 'metrics', 'hierarchy', 'recentActivity'], () => renderAll());

    state.subscribe(['drawerOpen', 'drawerEntity'], () => {
      _syncDrawer(state.get('drawerOpen'), state.get('drawerEntity'));
    });

    state.subscribe('loading', (key, isLoading) => {
      if (_dom.refreshBtn) _dom.refreshBtn.disabled = isLoading;
    });

    state.subscribe('lastUpdated', (key, val) => _renderLastUpdated(val));
  }

  // Expose onSidebarVersionClick/ReviewClick globally for inline handlers
  return {
    init,
    loadAll,
    renderAll,
    onProjectChange,
    onVersionChange,
    onReviewChange,
    onRefresh,
    onExpandAll,
    onCloseDrawer,
    onSidebarVersionClick,
    onSidebarReviewClick,
  };

})();

window.Dashboard = Dashboard;

// Auto-boot when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => Dashboard.init());
} else {
  Dashboard.init();
}
