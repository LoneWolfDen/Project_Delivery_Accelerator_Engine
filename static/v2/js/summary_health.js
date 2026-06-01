/**
 * summary_health.js — V2 Health Signal (RAG Status)
 *
 * TRACE: UI → Logic → AppState (metrics + versions)
 * Component: HealthSignal
 * Inputs:  MetricsPayload (risks_identified, gaps_identified, trend)
 *          Version object (risk count from stats)
 * Outputs: RAG badge HTML, health level string, colour tokens
 *
 * Responsibilities:
 *  - Compute Red / Amber / Green health from risk count + unresolved issues
 *  - Expose computeHealth(metrics) → { level, label, colour, icon }
 *  - Expose renderBadge(metrics)   → HTML string for inline use
 *  - Expose renderVersionBadge(version) → HTML for Version card header
 *  - Auto-mount: subscribe to AppState 'metrics' and update #v2-health-badge
 *
 * Rules (pure, no side-effects):
 *   risks >= HIGH_RISK_THRESHOLD  → Red
 *   risks >= MED_RISK_THRESHOLD
 *     OR unresolved_issues > 0    → Amber
 *   else                          → Green
 *
 * Constraints:
 *  - No AI / LLM — pure rule-based logic only
 *  - No external libraries
 *  - Does NOT modify summary.js
 */

'use strict';

const HealthSignal = (() => {

  // ── Thresholds ─────────────────────────────────────────────
  const HIGH_RISK_THRESHOLD = 8;   // risks ≥ this → Red
  const MED_RISK_THRESHOLD  = 3;   // risks ≥ this → Amber (if not already Red)

  // ── Levels ────────────────────────────────────────────────
  const LEVELS = {
    RED:   { level: 'red',   label: 'High Risk',  icon: '🔴', colour: 'var(--red)',   badgeClass: 'health-badge--red'   },
    AMBER: { level: 'amber', label: 'Medium Risk', icon: '🟡', colour: 'var(--amber)', badgeClass: 'health-badge--amber' },
    GREEN: { level: 'green', label: 'Low Risk',   icon: '🟢', colour: 'var(--green)', badgeClass: 'health-badge--green' },
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

  // ── Core: compute health level ─────────────────────────────
  /**
   * Derive health level from metrics or version stats.
   *
   * @param {object|null} source - MetricsPayload OR Version object
   *   Supports both shapes:
   *     MetricsPayload: { risks_identified, gaps_identified, trend[] }
   *     Version:        { stats: { risks }, reviews: [{ issues_carry_forward }] }
   * @returns {{ level, label, icon, colour, badgeClass, risks, unresolvedIssues }}
   */
  function computeHealth(source) {
    if (!source) return { ...LEVELS.GREEN, risks: 0, unresolvedIssues: 0 };

    // Normalise: extract risks and unresolved from either shape
    let risks = 0;
    let unresolvedIssues = 0;

    // MetricsPayload shape
    if (source.risks_identified != null) {
      risks = source.risks_identified || 0;
      // Unresolved = gaps_identified as proxy when explicit field absent
      unresolvedIssues = source.gaps_identified || 0;
    }
    // Version shape (from accordion / sidebar)
    else if (source.stats != null) {
      risks = (source.stats && source.stats.risks) || 0;
      // Sum carry-forward from all reviews
      (source.reviews || []).forEach(r => {
        unresolvedIssues += (r.issues_carry_forward || 0);
      });
    }
    // Direct risk count passed as plain object { risks, unresolved }
    else if (source.risks != null) {
      risks = source.risks || 0;
      unresolvedIssues = source.unresolved || 0;
    }

    let levelDef;
    if (risks >= HIGH_RISK_THRESHOLD) {
      levelDef = LEVELS.RED;
    } else if (risks >= MED_RISK_THRESHOLD || unresolvedIssues > 0) {
      levelDef = LEVELS.AMBER;
    } else {
      levelDef = LEVELS.GREEN;
    }

    return { ...levelDef, risks, unresolvedIssues };
  }

  // ── Render: inline badge ───────────────────────────────────
  /**
   * Renders a compact health badge for use inside a card header.
   *
   * @param {object|null} source  - MetricsPayload or Version
   * @param {boolean} [showLabel] - show the text label alongside icon
   * @returns {string} HTML
   */
  function renderBadge(source, showLabel = true) {
    const h = computeHealth(source);
    const label = showLabel ? `<span class="health-badge-label">${_esc(h.label)}</span>` : '';
    return `
      <span class="health-badge ${_esc(h.badgeClass)}"
            role="img"
            aria-label="Health: ${_esc(h.label)}"
            title="Health: ${_esc(h.label)} · ${h.risks} risk${h.risks !== 1 ? 's' : ''}${h.unresolvedIssues ? ', ' + h.unresolvedIssues + ' unresolved' : ''}">
        <span class="health-badge-icon" aria-hidden="true">${h.icon}</span>
        ${label}
      </span>`;
  }

  /**
   * Renders a version-level health badge (icon-only, compact).
   * Used in accordion version headers and sidebar items.
   *
   * @param {object|null} version - Version summary object
   * @returns {string} HTML
   */
  function renderVersionBadge(version) {
    return renderBadge(version, false);
  }

  // ── Render: dashboard health card ─────────────────────────
  /**
   * Renders a self-contained health card for the dashboard overview.
   * Injected into #v2-health-badge by update().
   *
   * @param {object|null} metrics - MetricsPayload
   * @returns {string} HTML
   */
  function renderCard(metrics) {
    if (!metrics) {
      return `<div class="health-card health-card--loading" aria-label="Health loading">
        <div class="skeleton" style="height:14px;width:80px"></div>
      </div>`;
    }
    const h = computeHealth(metrics);
    return `
      <div class="health-card ${_esc(h.badgeClass)}" role="status" aria-label="Project health: ${_esc(h.label)}">
        <span class="health-card-icon" aria-hidden="true">${h.icon}</span>
        <div class="health-card-body">
          <span class="health-card-label">Project Health</span>
          <span class="health-card-value">${_esc(h.label)}</span>
        </div>
        <div class="health-card-detail">
          <span>${h.risks} risk${h.risks !== 1 ? 's' : ''}</span>
          ${h.unresolvedIssues > 0 ? `<span>· ${h.unresolvedIssues} unresolved</span>` : ''}
        </div>
      </div>`;
  }

  // ── Public: update DOM target ──────────────────────────────
  /**
   * Update the #v2-health-badge container with current metrics.
   * Called by AppState subscriber.
   *
   * @param {object|null} metrics
   */
  function update(metrics) {
    const el = document.getElementById('v2-health-badge');
    if (!el) return;
    el.innerHTML = renderCard(metrics);
  }

  // ── Mount: wire to AppState ────────────────────────────────
  /**
   * Subscribe to AppState 'metrics' and render immediately.
   * Safe to call multiple times (guard on window.AppState).
   */
  function mount() {
    const state = window.AppState;
    if (!state) return;
    update(state.get('metrics'));
    state.subscribe('metrics', (key, metrics) => update(metrics));
  }

  // ── Public API ─────────────────────────────────────────────
  return {
    computeHealth,
    renderBadge,
    renderVersionBadge,
    renderCard,
    update,
    mount,
    // Expose thresholds for tests
    HIGH_RISK_THRESHOLD,
    MED_RISK_THRESHOLD,
  };

})();

window.HealthSignal = HealthSignal;

// Auto-mount when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => HealthSignal.mount());
} else {
  HealthSignal.mount();
}
