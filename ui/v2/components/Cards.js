/**
 * Cards.js — V2 Snapshot Cards Component
 *
 * TRACE: UI → Logic → API → Data
 * Component: Cards (SnapshotCards)
 * Inputs:  MetricsPayload from /hierarchy/metrics
 * Outputs: HTML string for #v2-snapshot-grid
 * API:     /api/projects/{pid}/hierarchy/metrics
 * Data:    MetricsPayload {total_versions, total_reviews, risks_identified,
 *           gaps_identified, constraints, dependencies, assumptions,
 *           action_items, total_findings, data_source}
 *
 * Responsibilities:
 *  - Render Total Versions, Total Reviews, Active Version cards
 *  - Render finding-category metric tiles (risks, gaps, etc.)
 *  - Show "Showing data for: Vx → Review y" context badge
 *  - Skeleton state when metrics == null
 *  - Each card is keyboard-navigable and announces its value
 */

'use strict';

const Cards = (() => {

  function _esc(s) {
    if (typeof s !== 'string') s = String(s || '');
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Single snapshot card ──────────────────────────────────
  /**
   * @param {string|number} value
   * @param {string}        label
   * @param {string}        [sub]     - small sub-label
   * @param {string}        [colour]  - '' | 'green' | 'amber' | 'red' | 'purple'
   * @param {string}        [title]   - tooltip
   * @returns {string} HTML
   */
  function _card(value, label, sub, colour, title) {
    const cls = colour ? ` ${colour}` : '';
    return `
      <div class="snapshot-card${cls}"
           tabindex="0"
           role="button"
           title="${_esc(title || label)}"
           aria-label="${_esc(String(value))} ${_esc(label)}">
        <div class="snapshot-card-value">${_esc(String(value))}</div>
        <div class="snapshot-card-label">${_esc(label)}</div>
        ${sub ? `<div class="snapshot-card-sub">${_esc(sub)}</div>` : ''}
      </div>`;
  }

  // ── Skeleton grid ─────────────────────────────────────────
  function renderSkeleton(count = 5) {
    return Array.from({ length: count }, () =>
      '<div class="skeleton snapshot-card skeleton-card"></div>'
    ).join('');
  }

  // ── Context badge ─────────────────────────────────────────
  /**
   * Shows "Showing data for: V3 → r7 · solution_architect"
   * TRACE: Cards → data_source → MetricsPayload.data_source
   */
  function _contextBadge(ds) {
    if (!ds || !ds.version) return '';
    const vLabel = ds.version_label ? `${ds.version} – ${ds.version_label}` : ds.version;
    const rLabel = ds.review
      ? `${ds.review}${ds.review_persona ? ' · ' + ds.review_persona : ''}`
      : 'latest review';
    return `
      <div class="context-banner" id="v2-context-banner" aria-live="polite">
        <span class="ctx-label">Showing data for:</span>
        <strong id="v2-ctx-version">${_esc(vLabel)}</strong>
        <span class="ctx-sep">→</span>
        <strong id="v2-ctx-review">${_esc(rLabel)}</strong>
      </div>`;
  }

  // ── Full render ───────────────────────────────────────────
  /**
   * TRACE: Cards.render → MetricsPayload → snapshot-grid DOM
   * @param {object|null} metrics
   * @returns {string} HTML for the grid container innerHTML
   */
  function render(metrics) {
    if (!metrics) return renderSkeleton();

    const totalV     = metrics.total_versions    || 0;
    const totalR     = metrics.total_reviews     || 0;
    const risks      = metrics.risks_identified  || 0;
    const gaps       = metrics.gaps_identified   || 0;
    const findings   = metrics.total_findings    || 0;
    const constraints = metrics.constraints      || 0;
    const deps       = metrics.dependencies      || 0;
    const ds         = metrics.data_source       || {};
    const activeVer  = ds.version_label || ds.version || '–';
    const phase      = ds.phase || '–';

    // Context banner is part of the rendered output
    // (inserted above the grid by dashboard.js if available)
    return [
      _card(totalV,   'Versions',       'across all phases',  '',       'Total versions created'),
      _card(totalR,   'Reviews',        'all versions',       '',       'Total reviews run'),
      _card(activeVer,'Active Version', phase,                'green',  'Currently selected version'),
      risks
        ? _card(risks, 'Risks',         'selected review',   risks > 5 ? 'red' : 'amber', 'Risks identified in selected review')
        : null,
      gaps
        ? _card(gaps,  'Gaps',          'selected review',   'amber',  'Gaps identified in selected review')
        : null,
      findings
        ? _card(findings, 'Findings',   'selected review',   'purple', 'Total findings in selected review')
        : null,
      constraints
        ? _card(constraints, 'Constraints', 'selected review', '',     'Constraints identified')
        : null,
      deps
        ? _card(deps,  'Dependencies',  'selected review',   '',       'Dependencies identified')
        : null,
    ].filter(Boolean).join('');
  }

  return { render, renderSkeleton, _contextBadge };
})();

if (typeof window !== 'undefined') window.Cards = Cards;
