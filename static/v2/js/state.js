/**
 * state.js — V2 Central State Store
 *
 * TRACE: UI → State Management
 * Component: AppState (singleton)
 * Pattern: Observable store with typed subscribers
 * No reload: All UI updates triggered via state.subscribe()
 *
 * Selection loop:
 *   User action → state.set() → notify subscribers → components re-render
 *
 * Refresh loop:
 *   RefreshButton click → state.set('loading', true) → api.js fetches
 *   → state.setData() → notify 'data' subscribers → components update
 */

'use strict';

const AppState = (() => {

  // ── Private state object ──────────────────────────────────
  const _state = {
    // Project selection
    projects:        [],       // List<{id, name, phase}>
    selectedProject: null,     // {id, name, phase} | null

    // Version selection (cascades from project)
    versions:        [],       // List<VersionSummary>
    selectedVersion: null,     // VersionSummary | null

    // Review selection (cascades from version)
    reviews:         [],       // List<ReviewSummary> for selected version
    selectedReview:  null,     // ReviewSummary | null

    // Dashboard metrics (scoped to selected version + review)
    metrics:         null,     // MetricsPayload | null

    // Hierarchy tree (full Phase→Version→Review)
    hierarchy:       null,     // HierarchyPayload | null

    // Detail drawer
    drawerOpen:      false,
    drawerEntity:    null,     // { type: 'version'|'review', data: {} }

    // UI state
    loading:         false,
    loadingMetrics:  false,
    error:           null,

    // Last data refresh timestamp
    lastUpdated:     null,     // ISO string | null
  };

  // ── Subscribers registry ──────────────────────────────────
  // Map<key: string, Set<Function>>
  // key = state property name, or '*' for all-changes
  const _subscribers = new Map();

  // ── Notify helpers ────────────────────────────────────────
  function _notify(changedKeys) {
    const keys = Array.isArray(changedKeys) ? changedKeys : [changedKeys];
    const called = new Set();

    keys.forEach(key => {
      // Notify specific-key subscribers
      if (_subscribers.has(key)) {
        _subscribers.get(key).forEach(fn => {
          if (!called.has(fn)) { fn(key, _state[key], _state); called.add(fn); }
        });
      }
    });

    // Notify wildcard subscribers once per batch
    if (_subscribers.has('*')) {
      _subscribers.get('*').forEach(fn => {
        if (!called.has(fn)) { fn(keys, _state); called.add(fn); }
      });
    }
  }

  // ── Public API ────────────────────────────────────────────

  /**
   * Read a state value.
   * @param {string} key
   * @returns {*}
   */
  function get(key) {
    return _state[key];
  }

  /**
   * Read the full state snapshot (shallow copy).
   * @returns {object}
   */
  function snapshot() {
    return { ..._state };
  }

  /**
   * Set one or more state values and notify subscribers.
   * @param {string|object} keyOrObject - key string or {key: value} map
   * @param {*} [value] - value when keyOrObject is a string
   */
  function set(keyOrObject, value) {
    const changed = [];
    if (typeof keyOrObject === 'string') {
      if (_state[keyOrObject] !== value) {
        _state[keyOrObject] = value;
        changed.push(keyOrObject);
      }
    } else if (typeof keyOrObject === 'object' && keyOrObject !== null) {
      Object.entries(keyOrObject).forEach(([k, v]) => {
        if (_state[k] !== v) {
          _state[k] = v;
          changed.push(k);
        }
      });
    }
    if (changed.length > 0) {
      _notify(changed);
    }
  }

  /**
   * Select a project. Resets version, review, metrics.
   * Triggers: 'selectedProject', 'selectedVersion', 'selectedReview',
   *           'versions', 'reviews', 'metrics'
   * @param {object|null} project
   */
  function selectProject(project) {
    set({
      selectedProject: project,
      selectedVersion: null,
      selectedReview:  null,
      versions:        [],
      reviews:         [],
      metrics:         null,
    });
  }

  /**
   * Select a version. Resets review + review list.
   * Triggers: 'selectedVersion', 'selectedReview', 'reviews'
   * @param {object|null} version
   */
  function selectVersion(version) {
    set({
      selectedVersion: version,
      selectedReview:  null,
      reviews:         [],
    });
  }

  /**
   * Select a review.
   * Triggers: 'selectedReview'
   * @param {object|null} review
   */
  function selectReview(review) {
    set('selectedReview', review);
  }

  /**
   * Open the detail drawer with a version or review entity.
   * @param {'version'|'review'} type
   * @param {object} data
   */
  function openDrawer(type, data) {
    set({ drawerOpen: true, drawerEntity: { type, data } });
  }

  /**
   * Close the detail drawer.
   */
  function closeDrawer() {
    set({ drawerOpen: false, drawerEntity: null });
  }

  /**
   * Set data after a successful API load.
   * Updates lastUpdated timestamp automatically.
   * @param {object} dataMap - { key: value, ... }
   */
  function setData(dataMap) {
    set({ ...dataMap, lastUpdated: new Date().toISOString(), loading: false });
  }

  /**
   * Subscribe to state changes.
   * @param {string|string[]} keys - property name(s), or '*' for all
   * @param {Function} fn - callback(key, newValue, fullState) or callback(changedKeys, fullState)
   * @returns {Function} unsubscribe function
   */
  function subscribe(keys, fn) {
    const ks = Array.isArray(keys) ? keys : [keys];
    ks.forEach(k => {
      if (!_subscribers.has(k)) _subscribers.set(k, new Set());
      _subscribers.get(k).add(fn);
    });
    // Return unsubscribe
    return () => {
      ks.forEach(k => {
        if (_subscribers.has(k)) _subscribers.get(k).delete(fn);
      });
    };
  }

  /**
   * One-shot subscription — auto-unsubscribes after first call.
   * @param {string|string[]} keys
   * @param {Function} fn
   */
  function once(keys, fn) {
    const unsub = subscribe(keys, (...args) => { fn(...args); unsub(); });
  }

  return {
    get,
    snapshot,
    set,
    selectProject,
    selectVersion,
    selectReview,
    openDrawer,
    closeDrawer,
    setData,
    subscribe,
    once,
  };

})();

// Expose globally for inline event handlers and other scripts
window.AppState = AppState;
