/**
 * helpers.js — V2 Shared Utility Functions
 *
 * TRACE: UI → Utilities
 * Used by: All v2 components and dashboard.js
 * No side-effects. Pure functions only.
 */

'use strict';

const Helpers = (() => {

  // ── String escaping ───────────────────────────────────────
  /**
   * Escape HTML special characters to prevent XSS.
   * @param {*} s
   * @returns {string}
   */
  function esc(s) {
    if (typeof s !== 'string') s = String(s == null ? '' : s);
    return s
      .replace(/&/g,  '&amp;')
      .replace(/</g,  '&lt;')
      .replace(/>/g,  '&gt;')
      .replace(/"/g,  '&quot;')
      .replace(/'/g,  '&#39;');
  }

  // ── Date formatting ───────────────────────────────────────
  /**
   * Format ISO timestamp to "YYYY-MM-DD HH:MM".
   * @param {string} iso
   * @returns {string}
   */
  function fmtDate(iso) {
    if (!iso) return '–';
    return iso.slice(0, 16).replace('T', ' ');
  }

  /**
   * Format ISO timestamp to "YYYY-MM-DD".
   * @param {string} iso
   * @returns {string}
   */
  function fmtDateShort(iso) {
    if (!iso) return '–';
    return iso.slice(0, 10);
  }

  /**
   * Relative time string from ISO timestamp.
   * "just now", "5m ago", "2h ago", "3d ago"
   * @param {string} iso
   * @returns {string}
   */
  function relTime(iso) {
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

  // ── Pluralise ─────────────────────────────────────────────
  /**
   * @param {number} count
   * @param {string} singular
   * @param {string} [plural]  - defaults to singular + 's'
   * @returns {string}  e.g. "1 review", "3 reviews"
   */
  function plural(count, singular, pluralForm) {
    return `${count} ${count === 1 ? singular : (pluralForm || singular + 's')}`;
  }

  // ── Quality status helpers ────────────────────────────────
  /**
   * Map quality_status string to badge CSS class.
   * @param {string} status
   * @returns {string}
   */
  function qualityClass(status) {
    if (status === 'complete') return 'badge-green';
    if (status === 'interim')  return 'badge-amber';
    return 'badge-default';
  }

  /**
   * Human-readable quality status label.
   * @param {string} status
   * @returns {string}
   */
  function qualityLabel(status) {
    if (status === 'complete') return 'Final';
    if (status === 'interim')  return 'Draft';
    return 'Pending';
  }

  /**
   * CSS class for status dot.
   * @param {string} status
   * @returns {string}
   */
  function statusDotClass(status) {
    if (status === 'complete') return 'complete';
    if (status === 'interim')  return 'in-progress';
    return 'pending';
  }

  // ── Capitalise ────────────────────────────────────────────
  /**
   * Convert snake_case category key to Title Case label.
   * @param {string} key  e.g. "action_items"
   * @returns {string}    e.g. "Action Items"
   */
  function catLabel(key) {
    return (key || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  // ── Truncate ──────────────────────────────────────────────
  /**
   * Truncate a string to maxLen characters with ellipsis.
   * @param {string} s
   * @param {number} maxLen
   * @returns {string}
   */
  function truncate(s, maxLen) {
    if (!s || s.length <= maxLen) return s || '';
    return s.slice(0, maxLen) + '…';
  }

  // ── Debounce ──────────────────────────────────────────────
  /**
   * Returns a debounced version of fn.
   * @param {Function} fn
   * @param {number}   ms
   * @returns {Function}
   */
  function debounce(fn, ms) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  return {
    esc,
    fmtDate,
    fmtDateShort,
    relTime,
    plural,
    qualityClass,
    qualityLabel,
    statusDotClass,
    catLabel,
    truncate,
    debounce,
  };
})();

if (typeof window !== 'undefined') window.Helpers = Helpers;
