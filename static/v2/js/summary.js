/**
 * summary.js — V2 Risk & Gap Summary Panel
 *
 * TRACE: UI → Logic → AppState (metrics)
 * Component: RiskGapSummary
 * Inputs:  MetricsPayload (metrics.risks_identified, metrics.gaps_identified,
 *           metrics.total_findings, metrics.trend)
 * Outputs: HTML string for #v2-summary-panel
 *
 * Responsibilities:
 *  - Count risks and gaps from current metrics
 *  - Derive risk trend by comparing to the previous version in trend[]
 *  - Detect recurring gaps (gaps present across ≥ 2 versions via trend)
 *  - Render a concise summary card inside the Snapshot section
 *  - Re-render whenever AppState metrics change (subscribe-based, no reload)
 *
 * Constraints:
 *  - No AI / LLM dependency — pure rule-based logic only
 *  - No external libraries
 */

'use strict';

const RiskGapSummary = (() => {

  // ── Constants ─────────────────────────────────────────────
  const HIGH_RISK_THRESHOLD = 5;   // risks ≥ this → "high-risk"
  const TREND_INCREASE_PCT  = 0;   // any increase in risks → "increasing"
  const RECURRING_GAP_MIN   = 2;   // gaps in ≥ this many versions → "recurring"

  // ── Utility ───────────────────────────────────────────────
  function _esc(s) {
    if (typeof s !== 'string') s = String(s == null ? '' : s);
    return s
      .replace(/&/g,  '&amp;')
      .replace(/</g,  '&lt;')
      .replace(/>/g,  '&gt;')
      .replace(/"/g,  '&quot;');
  }

  // ── Core logic ────────────────────────────────────────────

  /**
   * Derive risk trend direction by comparing the current version's risk count
   * with the previous version's in the trend array.
   *
   * trend[] is ordered oldest → newest (matches api.js mock order).
   * If only one data point exists, trend is "stable".
   *
   * @param {Array} trend  - [{version_id, stats:{risks}, created_at}]
   * @returns {'increasing'|'decreasing'|'stable'|'unknown'}
   */
  function _deriveTrend(trend) {
    if (!Array.isArray(trend) || trend.length < 2) return 'unknown';

    // Sort by created_at ascending to guarantee order
    const sorted = trend.slice().sort((a, b) =>
      (a.created_at || '').localeCompare(b.created_at || '')
    );

    const prev    = sorted[sorted.length - 2];
    const current = sorted[sorted.length - 1];
    const prevRisks    = (prev.stats    && prev.stats.risks    != null) ? prev.stats.risks    : null;
    const currentRisks = (current.stats && current.stats.risks != null) ? current.stats.risks : null;

    if (prevRisks === null || currentRisks === null) return 'unknown';
    if (currentRisks > prevRisks)  return 'increasing';
    if (currentRisks < prevRisks)  return 'decreasing';
    return 'stable';
  }

  /**
   * Count how many versions in trend[] have at least one gap recorded.
   * The trend array only carries risks in the mock; when gaps are absent
   * we fall back to the current review's gaps_identified as a proxy.
   *
   * Rule: if stats.gaps exists, count versions where stats.gaps > 0.
   *       Otherwise, treat any version entry as "gap present" when
   *       the overall gaps_identified metric is > 0 (conservative).
   *
   * @param {Array}  trend
   * @param {number} currentGaps
   * @returns {number} count of versions with at least one gap
   */
  function _countVersionsWithGaps(trend, currentGaps) {
    if (!Array.isArray(trend) || trend.length === 0) return currentGaps > 0 ? 1 : 0;

    let count = 0;
    trend.forEach(entry => {
      const statsGaps = entry.stats && entry.stats.gaps != null ? entry.stats.gaps : null;
      if (statsGaps !== null) {
        if (statsGaps > 0) count++;
      } else if (currentGaps > 0) {
        // No per-version gap data — treat every trend entry as gap-present
        count++;
      }
    });
    return count;
  }

  /**
   * Build the structured summary object from a MetricsPayload.
   *
   * @param {object|null} metrics
   * @returns {{
   *   risks:          number,
   *   gaps:           number,
   *   highRiskItems:  number,
   *   recurringGaps:  number,
   *   trend:          'increasing'|'decreasing'|'stable'|'unknown',
   *   totalFindings:  number,
   *   versionCount:   number,
   * }}
   */
  function compute(metrics) {
    if (!metrics) {
      return {
        risks: 0, gaps: 0, highRiskItems: 0,
        recurringGaps: 0, trend: 'unknown',
        totalFindings: 0, versionCount: 0,
      };
    }

    const risks         = metrics.risks_identified || 0;
    const gaps          = metrics.gaps_identified  || 0;
    const totalFindings = metrics.total_findings   || 0;
    const versionCount  = metrics.total_versions   || 0;
    const trend         = _deriveTrend(metrics.trend || []);

    // "High-risk items" = risks that meet or exceed threshold
    // With only a total count available (no severity array), we classify
    // the whole bucket as high-risk when the count >= threshold.
    const highRiskItems = risks >= HIGH_RISK_THRESHOLD ? risks : 0;

    // Recurring gaps: gap count from trend-array coverage
    const versionsWithGaps = _countVersionsWithGaps(metrics.trend || [], gaps);
    const recurringGaps    = versionsWithGaps >= RECURRING_GAP_MIN ? gaps : 0;

    return {
      risks,
      gaps,
      highRiskItems,
      recurringGaps,
      trend,
      totalFindings,
      versionCount,
    };
  }

  // ── Render helpers ────────────────────────────────────────

  function _trendIcon(trend) {
    if (trend === 'increasing') return '↑';
    if (trend === 'decreasing') return '↓';
    if (trend === 'stable')     return '→';
    return '–';
  }

  function _trendClass(trend) {
    if (trend === 'increasing') return 'summary-trend-up';
    if (trend === 'decreasing') return 'summary-trend-down';
    return 'summary-trend-stable';
  }

  function _trendLabel(trend) {
    if (trend === 'increasing') return 'Increasing';
    if (trend === 'decreasing') return 'Decreasing';
    if (trend === 'stable')     return 'Stable';
    return 'No trend data';
  }

  /**
   * Render a single summary bullet row.
   * @param {string} icon
   * @param {string} label
   * @param {string} valueClass  - CSS modifier on the value span
   * @param {string|number} value
   * @returns {string} HTML
   */
  function _bullet(icon, label, value, valueClass) {
    return `
      <div class="summary-bullet">
        <span class="summary-bullet-icon" aria-hidden="true">${icon}</span>
        <span class="summary-bullet-label">${_esc(label)}</span>
        <span class="summary-bullet-value ${_esc(valueClass || '')}">${_esc(String(value))}</span>
      </div>`;
  }

  // ── Public: render ────────────────────────────────────────

  /**
   * Render the full summary panel HTML.
   * Injected into #v2-summary-panel by RiskGapSummary.update().
   *
   * @param {object|null} metrics - MetricsPayload from AppState
   * @returns {string} HTML
   */
  function render(metrics) {
    if (!metrics) {
      return `
        <div class="summary-panel summary-panel--empty" aria-label="Risk and gap summary loading">
          <div class="summary-panel-header">
            <span class="summary-panel-title">Risk &amp; Gap Summary</span>
          </div>
          <div class="summary-panel-body">
            <div class="skeleton summary-skeleton"></div>
            <div class="skeleton summary-skeleton" style="width:70%"></div>
            <div class="skeleton summary-skeleton" style="width:55%"></div>
          </div>
        </div>`;
    }

    const s = compute(metrics);

    // Determine overall health label
    let healthLabel, healthClass;
    if (s.trend === 'increasing' && s.highRiskItems > 0) {
      healthLabel = 'Elevated';
      healthClass = 'summary-health--red';
    } else if (s.risks > 0 || s.gaps > 0) {
      healthLabel = 'Needs Attention';
      healthClass = 'summary-health--amber';
    } else {
      healthLabel = 'Clear';
      healthClass = 'summary-health--green';
    }

    const riskValueClass  = s.highRiskItems > 0 ? 'summary-value-red'   : 'summary-value-neutral';
    const gapValueClass   = s.recurringGaps > 0 ? 'summary-value-amber' : 'summary-value-neutral';
    const trendValueClass = _trendClass(s.trend);

    return `
      <div class="summary-panel" role="region" aria-label="Risk and gap summary">

        <div class="summary-panel-header">
          <span class="summary-panel-title">Risk &amp; Gap Summary</span>
          <span class="summary-health ${_esc(healthClass)}" title="Overall risk health">${_esc(healthLabel)}</span>
        </div>

        <div class="summary-panel-body">

          ${_bullet(
            '⚠',
            s.highRiskItems > 0
              ? `${s.highRiskItems} high-risk item${s.highRiskItems !== 1 ? 's' : ''}`
              : `${s.risks} risk item${s.risks !== 1 ? 's' : ''}`,
            s.risks,
            riskValueClass
          )}

          ${_bullet(
            '◉',
            s.recurringGaps > 0
              ? `${s.recurringGaps} recurring gap${s.recurringGaps !== 1 ? 's' : ''}`
              : `${s.gaps} gap${s.gaps !== 1 ? 's' : ''}`,
            s.gaps,
            gapValueClass
          )}

          <div class="summary-bullet">
            <span class="summary-bullet-icon" aria-hidden="true">📈</span>
            <span class="summary-bullet-label">Risk trend</span>
            <span class="summary-bullet-value ${_esc(trendValueClass)}">
              ${_trendIcon(s.trend)} ${_esc(_trendLabel(s.trend))}
            </span>
          </div>

          ${s.totalFindings > 0 ? _bullet(
            '🔍',
            'Total findings',
            s.totalFindings,
            'summary-value-neutral'
          ) : ''}

        </div>

        ${s.versionCount > 0 ? `
          <div class="summary-panel-footer">
            Across ${s.versionCount} version${s.versionCount !== 1 ? 's' : ''}
            ${s.trend !== 'unknown' ? `· trend based on last ${Math.min((metrics.trend || []).length, 99)} snapshot${(metrics.trend || []).length !== 1 ? 's' : ''}` : ''}
          </div>` : ''}

      </div>`;
  }

  // ── Public: mount + update ────────────────────────────────

  /**
   * Update the #v2-summary-panel DOM element with fresh render output.
   * Called by AppState subscriber in dashboard_v2.html.
   *
   * @param {object|null} metrics
   */
  function update(metrics) {
    const el = document.getElementById('v2-summary-panel');
    if (!el) return;
    el.innerHTML = render(metrics);
  }

  /**
   * Mount: subscribe to AppState 'metrics' changes and render immediately.
   * Call once after DOM is ready.
   */
  function mount() {
    const state = window.AppState;
    if (!state) return;

    // Initial render with whatever is already in state
    update(state.get('metrics'));

    // Reactive updates
    state.subscribe('metrics', (key, metrics) => update(metrics));
  }

  return { compute, render, update, mount };

})();

window.RiskGapSummary = RiskGapSummary;

// Auto-mount when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => RiskGapSummary.mount());
} else {
  RiskGapSummary.mount();
}
