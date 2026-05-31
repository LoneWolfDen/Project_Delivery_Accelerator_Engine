/**
 * MainLayout.js — V2 Page Shell Manager
 *
 * TRACE: UI → Layout
 * Component: MainLayout
 * Inputs:  AppState (drawerOpen, loading)
 * Outputs: CSS class mutations on #v2-main, #v2-drawer, #v2-app
 *
 * Responsibilities:
 *  - Coordinate layout regions: header, sidebar, main, drawer
 *  - Manage drawer open/close transitions (no reload)
 *  - Manage global loading overlay
 *  - Register keyboard shortcuts (Esc → close drawer)
 *  - Announce live-region changes to screen readers
 *
 * No business logic. Pure DOM layout coordination.
 */

'use strict';

const MainLayout = (() => {

  let _initialised = false;

  // ── DOM refs ──────────────────────────────────────────────
  function _el(id) { return document.getElementById(id); }

  // ── Drawer ────────────────────────────────────────────────
  /**
   * Open the right-side detail drawer.
   * TRACE: MainLayout.openDrawer → CSS: #v2-drawer.open, #v2-main.drawer-open
   */
  function openDrawer() {
    const drawer = _el('v2-drawer');
    const main   = _el('v2-main');
    if (drawer) drawer.classList.add('open');
    if (main)   main.classList.add('drawer-open');
    // Trap focus inside drawer for accessibility
    const firstFocusable = drawer && drawer.querySelector('button, [tabindex="0"]');
    if (firstFocusable) firstFocusable.focus();
  }

  /**
   * Close the right-side detail drawer.
   * TRACE: MainLayout.closeDrawer → CSS class removal
   */
  function closeDrawer() {
    const drawer = _el('v2-drawer');
    const main   = _el('v2-main');
    if (drawer) drawer.classList.remove('open');
    if (main)   main.classList.remove('drawer-open');
  }

  // ── Loading indicator ─────────────────────────────────────
  /**
   * Show or hide the global loading state.
   * Updates the refresh button aria-label and disabled state.
   * @param {boolean} isLoading
   */
  function setLoading(isLoading) {
    const btn = _el('v2-refresh-btn');
    if (btn) {
      btn.disabled = isLoading;
      btn.setAttribute('aria-label', isLoading ? 'Loading…' : 'Refresh');
      btn.textContent = isLoading ? '⟳' : '↺';
      btn.classList.toggle('spin', isLoading);
    }
  }

  // ── Sidebar toggle (mobile) ───────────────────────────────
  function toggleSidebar() {
    const sidebar = _el('v2-sidebar');
    if (!sidebar) return;
    const isVisible = sidebar.style.display !== 'none';
    sidebar.style.display = isVisible ? 'none' : '';
  }

  // ── Keyboard shortcuts ────────────────────────────────────
  function _handleKeydown(e) {
    if (e.key === 'Escape') {
      const state = window.AppState;
      if (state && state.get('drawerOpen')) {
        state.closeDrawer();
      }
    }
  }

  // ── AppState subscriptions ────────────────────────────────
  function _wireStateSubscriptions() {
    const state = window.AppState;
    if (!state) return;

    state.subscribe('drawerOpen', (key, isOpen) => {
      if (isOpen) openDrawer(); else closeDrawer();
    });

    state.subscribe('loading', (key, isLoading) => {
      setLoading(isLoading);
    });
  }

  // ── Init ──────────────────────────────────────────────────
  /**
   * Must be called once after DOM is ready.
   * Wires state subscriptions and keyboard handlers.
   */
  function init() {
    if (_initialised) return;
    _initialised = true;

    document.addEventListener('keydown', _handleKeydown);
    _wireStateSubscriptions();
  }

  return { init, openDrawer, closeDrawer, setLoading, toggleSidebar };
})();

if (typeof window !== 'undefined') window.MainLayout = MainLayout;
