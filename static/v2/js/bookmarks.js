/**
 * bookmarks.js — V2 Pinned Insights
 *
 * TRACE: UI → LocalStorage → DOM
 * Component: PinnedInsights
 * Storage:   localStorage key 'pdae_v2_pins'
 * Inputs:    Version | Review | Risk entity objects
 * Outputs:   DOM mutations to #v2-pinned-section, pin toggle buttons
 *
 * Responsibilities:
 *  - Toggle pin/unpin on Version, Review, or Risk items
 *  - Persist pinned items to localStorage (project-scoped)
 *  - Render a "Pinned" section at the top of the dashboard (#v2-pinned-section)
 *  - Render a pin toggle button for any given item
 *  - Re-render the pinned section whenever pins change
 *
 * Pin item shape:
 *   { id, type: 'version'|'review'|'risk', label, projectId, pinnedAt }
 *
 * Constraints:
 *  - No AI / LLM — pure client-side only
 *  - No external libraries
 *  - Backward compatible: does NOT read/write any existing localStorage keys
 */

'use strict';

const PinnedInsights = (() => {

  // ── Constants ──────────────────────────────────────────────
  const STORAGE_KEY = 'pdae_v2_pins';
  const MAX_PINS    = 20;   // hard cap to prevent unbounded growth

  // ── Type config ────────────────────────────────────────────
  const TYPE_META = {
    version: { icon: '📋', label: 'Version',  colour: 'pin-type--version' },
    review:  { icon: '🔍', label: 'Review',   colour: 'pin-type--review'  },
    risk:    { icon: '⚠',  label: 'Risk',     colour: 'pin-type--risk'    },
  };

  // ── Utility ────────────────────────────────────────────────
  function _esc(s) {
    if (typeof s !== 'string') s = String(s == null ? '' : s);
    return s
      .replace(/&/g,  '&amp;')
      .replace(/</g,  '&lt;')
      .replace(/>/g,  '&gt;')
      .replace(/"/g,  '&quot;');
  }

  function _now() {
    return new Date().toISOString();
  }

  // ── Storage helpers ────────────────────────────────────────

  /**
   * Load all pins from localStorage.
   * Returns [] on parse error (fail-safe).
   * @returns {Array<PinItem>}
   */
  function _loadAll() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  /**
   * Persist pin list to localStorage.
   * Silent on write error (private browsing / quota).
   * @param {Array<PinItem>} pins
   */
  function _saveAll(pins) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(pins));
    } catch (e) {
      // Non-blocking: quota exceeded or private mode
    }
  }

  // ── Project-scoped helpers ─────────────────────────────────

  /**
   * Get pins for a specific project.
   * @param {string} projectId
   * @returns {Array<PinItem>}
   */
  function getPins(projectId) {
    if (!projectId) return [];
    return _loadAll().filter(p => p.projectId === projectId);
  }

  /**
   * Get all pins (across projects).
   * @returns {Array<PinItem>}
   */
  function getAllPins() {
    return _loadAll();
  }

  /**
   * Check whether a given item is pinned.
   * @param {string} id
   * @param {'version'|'review'|'risk'} type
   * @param {string} projectId
   * @returns {boolean}
   */
  function isPinned(id, type, projectId) {
    return getPins(projectId).some(p => p.id === id && p.type === type);
  }

  // ── Core: toggle ───────────────────────────────────────────
  /**
   * Pin or unpin an item. Idempotent.
   *
   * @param {string} id         - version_id | review_id | risk text hash
   * @param {'version'|'review'|'risk'} type
   * @param {string} label      - display label
   * @param {string} projectId
   * @returns {{ pinned: boolean }} - new state
   */
  function toggle(id, type, label, projectId) {
    const all   = _loadAll();
    const idx   = all.findIndex(p => p.id === id && p.type === type && p.projectId === projectId);
    let pinned;

    if (idx >= 0) {
      // Unpin
      all.splice(idx, 1);
      pinned = false;
    } else {
      // Pin — enforce cap (remove oldest if needed)
      const projPins = all.filter(p => p.projectId === projectId);
      if (projPins.length >= MAX_PINS) {
        // Remove the oldest project-scoped pin
        const oldest = projPins.reduce((a, b) => a.pinnedAt < b.pinnedAt ? a : b);
        const oi = all.findIndex(p => p.id === oldest.id && p.type === oldest.type && p.projectId === oldest.projectId);
        if (oi >= 0) all.splice(oi, 1);
      }
      all.push({ id, type, label, projectId, pinnedAt: _now() });
      pinned = true;
    }

    _saveAll(all);
    _notifyChange(projectId);
    return { pinned };
  }

  /**
   * Remove a pin by id + type + projectId.
   * @param {string} id
   * @param {'version'|'review'|'risk'} type
   * @param {string} projectId
   */
  function unpin(id, type, projectId) {
    const all = _loadAll();
    const idx = all.findIndex(p => p.id === id && p.type === type && p.projectId === projectId);
    if (idx >= 0) {
      all.splice(idx, 1);
      _saveAll(all);
      _notifyChange(projectId);
    }
  }

  /**
   * Clear all pins for a project.
   * @param {string} projectId
   */
  function clearProject(projectId) {
    const remaining = _loadAll().filter(p => p.projectId !== projectId);
    _saveAll(remaining);
    _notifyChange(projectId);
  }

  // ── Change notifications ───────────────────────────────────
  const _listeners = new Set();

  function _notifyChange(projectId) {
    _listeners.forEach(fn => {
      try { fn(projectId); } catch (e) {}
    });
  }

  /**
   * Subscribe to pin changes.
   * @param {Function} fn - called with (projectId) on each change
   * @returns {Function} unsubscribe
   */
  function onChange(fn) {
    _listeners.add(fn);
    return () => _listeners.delete(fn);
  }

  // ── Render: pin toggle button ──────────────────────────────
  /**
   * Renders a pin/unpin toggle button for embedding in any card.
   *
   * @param {string} id
   * @param {'version'|'review'|'risk'} type
   * @param {string} label
   * @param {string} projectId
   * @returns {string} HTML
   */
  function renderPinButton(id, type, label, projectId) {
    const pinned  = isPinned(id, type, projectId);
    const title   = pinned ? 'Unpin this item' : 'Pin this item';
    const ariaLbl = pinned ? `Unpin ${label}` : `Pin ${label}`;
    return `
      <button class="pin-btn${pinned ? ' pin-btn--active' : ''}"
              aria-label="${_esc(ariaLbl)}"
              title="${_esc(title)}"
              data-pin-id="${_esc(id)}"
              data-pin-type="${_esc(type)}"
              data-pin-label="${_esc(label)}"
              data-pin-project="${_esc(projectId)}"
              onclick="PinnedInsights.onPinClick(this)">
        ${pinned ? '📌' : '📍'}
      </button>`;
  }

  // ── Render: pinned section ─────────────────────────────────
  /**
   * Render the full "Pinned" section HTML.
   * Injected into #v2-pinned-section.
   *
   * @param {string} projectId
   * @returns {string} HTML (empty string if no pins)
   */
  function renderSection(projectId) {
    const pins = getPins(projectId);
    if (pins.length === 0) return '';

    // Sort newest-pinned first
    const sorted = pins.slice().sort((a, b) =>
      (b.pinnedAt || '').localeCompare(a.pinnedAt || '')
    );

    const items = sorted.map(p => {
      const meta = TYPE_META[p.type] || { icon: '📌', label: p.type, colour: '' };
      return `
        <div class="pinned-item ${_esc(meta.colour)}"
             data-pin-id="${_esc(p.id)}"
             data-pin-type="${_esc(p.type)}"
             data-pin-project="${_esc(projectId)}"
             role="listitem">
          <span class="pinned-item-icon" aria-hidden="true">${meta.icon}</span>
          <span class="pinned-item-label" title="${_esc(p.label)}">${_esc(p.label)}</span>
          <span class="pinned-item-type-badge">${_esc(meta.label)}</span>
          <button class="pin-remove-btn"
                  aria-label="Unpin ${_esc(p.label)}"
                  title="Remove pin"
                  data-pin-id="${_esc(p.id)}"
                  data-pin-type="${_esc(p.type)}"
                  data-pin-project="${_esc(projectId)}"
                  onclick="PinnedInsights.onRemoveClick(this)">
            ✕
          </button>
        </div>`;
    }).join('');

    return `
      <div class="pinned-section" id="v2-pinned-items" role="list" aria-label="Pinned items">
        <div class="pinned-section-header">
          <span class="pinned-section-title">📌 Pinned</span>
          <span class="pinned-section-count">${pins.length}</span>
          <button class="pinned-clear-btn btn btn-xs btn-ghost"
                  onclick="PinnedInsights.onClearClick('${_esc(projectId)}')"
                  title="Remove all pins for this project"
                  aria-label="Clear all pins">
            Clear all
          </button>
        </div>
        <div class="pinned-items-list">
          ${items}
        </div>
      </div>`;
  }

  // ── DOM update ─────────────────────────────────────────────
  /**
   * Re-render the #v2-pinned-section container.
   * @param {string} projectId
   */
  function updateSection(projectId) {
    const el = document.getElementById('v2-pinned-section');
    if (!el) return;
    el.innerHTML = renderSection(projectId);
    // Update all pin buttons currently in the DOM to reflect new state
    _syncButtonStates(projectId);
  }

  /**
   * Sync all .pin-btn elements in the DOM to reflect current pin state.
   * @param {string} projectId
   */
  function _syncButtonStates(projectId) {
    document.querySelectorAll('.pin-btn[data-pin-project]').forEach(btn => {
      if (btn.dataset.pinProject !== projectId) return;
      const pinned = isPinned(btn.dataset.pinId, btn.dataset.pinType, projectId);
      btn.classList.toggle('pin-btn--active', pinned);
      btn.textContent = pinned ? '📌' : '📍';
      btn.title = pinned ? 'Unpin this item' : 'Pin this item';
    });
  }

  // ── Event handlers (called from inline onclick) ────────────

  /**
   * Toggle pin on button click.
   * @param {HTMLElement} btn
   */
  function onPinClick(btn) {
    const { pinId, pinType, pinLabel, pinProject } = btn.dataset;
    if (!pinId || !pinType || !pinProject) return;
    toggle(pinId, pinType, pinLabel || pinId, pinProject);
  }

  /**
   * Remove a pin from the pinned section ✕ button.
   * @param {HTMLElement} btn
   */
  function onRemoveClick(btn) {
    const { pinId, pinType, pinProject } = btn.dataset;
    if (!pinId || !pinType || !pinProject) return;
    unpin(pinId, pinType, pinProject);
  }

  /**
   * Clear all pins for a project.
   * @param {string} projectId
   */
  function onClearClick(projectId) {
    clearProject(projectId);
  }

  // ── Mount ──────────────────────────────────────────────────
  /**
   * Wire up AppState listener and render initial pinned section.
   * Call once after DOM ready.
   */
  function mount() {
    const state = window.AppState;
    if (!state) return;

    const _render = () => {
      const proj = state.get('selectedProject');
      if (proj) updateSection(proj.id);
    };

    // Re-render when project changes
    state.subscribe('selectedProject', _render);

    // Re-render on any pin change
    onChange(() => _render());

    // Initial render
    _render();
  }

  // ── Public API ─────────────────────────────────────────────
  return {
    getPins,
    getAllPins,
    isPinned,
    toggle,
    unpin,
    clearProject,
    onChange,
    renderPinButton,
    renderSection,
    updateSection,
    onPinClick,
    onRemoveClick,
    onClearClick,
    mount,
    // Expose for tests
    STORAGE_KEY,
    MAX_PINS,
  };

})();

window.PinnedInsights = PinnedInsights;

// Auto-mount when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => PinnedInsights.mount());
} else {
  PinnedInsights.mount();
}
