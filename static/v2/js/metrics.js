/**
 * metrics.js — V2 Project Memory Score
 *
 * TRACE: UI → Logic → AppState (metrics + versions)
 * Component: ProjectMemoryScore
 * Inputs:  MetricsPayload (total_versions, total_reviews, risks_identified,
 *           gaps_identified, trend[])
 * Outputs: "Project Learning Maturity: 72%" as progress bar + card
 *
 * Responsibilities:
 *  - Compute a weighted 0–100 score from project activity signals
 *  - Render a progress bar + maturity label
 *  - Auto-mount: subscribe to AppState 'metrics' and update #v2-memory-score
 *
 * Scoring formula (weighted sum, capped at 100):
 *   versions_score  = min(total_versions  / VERSION_MAX,  1) × WEIGHT_VERSIONS  (30%)
 *   reviews_score   = min(total_reviews   / REVIEW_MAX,   1) × WEIGHT_REVIEWS   (30%)
 *   risks_score     = min(risks_identified / RISK_MAX,    1) × WEIGHT_RISKS      (20%)
 *   depth_score     = min(iter_depth       / DEPTH_MAX,   1) × WEIGHT_DEPTH      (20%)
 *
 *   total = (versions_score + reviews_score + risks_score + depth_score) × 100
 *
 * Iteration depth: max iteration_number seen across all reviews in trend.
 *
 * Maturity label bands:
 *   0–24  : Early Stage
 *   25–49 : Developing
 *   50–74 : Maturing
 *   75–89 : Advanced
 *   90–100: Expert
 *
 * Constraints:
 *  - No AI / LLM — pure arithmetic only
 *  - No external libraries
 */

'use strict';

const ProjectMemoryScore = (() => {

  // ── Weights & caps ─────────────────────────────────────────
  const WEIGHT_VERSIONS = 0.30;
  const WEIGHT_REVIEWS  = 0.30;
  const WEIGHT_RISKS    = 0.20;
  const WEIGHT_DEPTH    = 0.20;

  const VERSION_MAX = 10;   // Full score at 10 versions
  const REVIEW_MAX  = 20;   // Full score at 20 reviews
  const RISK_MAX    = 15;   // Full score at 15 identified risks
  const DEPTH_MAX   = 5;    // Full score at iteration depth of 5

  // ── Maturity bands ─────────────────────────────────────────
  const BANDS = [
    { min: 90, label: 'Expert',       colour: 'score-band--expert'    },
    { min: 75, label: 'Advanced',     colour: 'score-band--advanced'  },
    { min: 50, label: 'Maturing',     colour: 'score-band--maturing'  },
    { min: 25, label: 'Developing',   colour: 'score-band--developing'},
    { min:  0, label: 'Early Stage',  colour: 'score-band--early'     },
  ];

  // ── Utility ────────────────────────────────────────────────
  function _esc(s) {
    if (typeof s !== 'string') s = String(s == null ? '' : s);
    return s
      .replace(/&/g,  '&amp;')
      .replace(/</g,  '&lt;')
      .replace(/>/g,  '&gt;')
      .replace(/"/g,  '&quot;');
  }

  function _clamp(val, min, max) {
    return Math.min(Math.max(val, min), max);
  }

  // ── Derive iteration depth from metrics.trend[] ───────────
  /**
   * Find the max iteration_number across all reviews embedded in the
   * hierarchy tree (available via AppState 'versions').
   * Falls back to trend array length as a proxy when reviews absent.
   *
   * @param {object|null} metrics
   * @returns {number}
   */
  function _deriveDepth(metrics) {
    if (!metrics) return 0;

    // If we have the full version list from AppState, count max iteration
    const state = window.AppState;
    if (state) {
      const versions = state.get('versions') || [];
      let maxIter = 0;
      versions.forEach(v => {
        (v.reviews || []).forEach(r => {
          if (r.iteration_number > maxIter) maxIter = r.iteration_number;
        });
      });
      if (maxIter > 0) return maxIter;
    }

    // Fallback: trend array length
    return (metrics.trend || []).length;
  }

  // ── Core: compute score ────────────────────────────────────
  /**
   * Calculate the Project Memory Score.
   *
   * @param {object|null} metrics - MetricsPayload
   * @returns {{
   *   score:          number,   // 0–100 integer
   *   label:          string,   // "Project Learning Maturity: 72%"
   *   band:           string,   // "Maturing"
   *   bandColour:     string,   // CSS class
   *   components: {
   *     versions:     number,   // 0–1 contribution
   *     reviews:      number,
   *     risks:        number,
   *     depth:        number,
   *   },
   *   raw: {
   *     versions:     number,
   *     reviews:      number,
   *     risks:        number,
   *     depth:        number,
   *   }
   * }}
   */
  function compute(metrics) {
    const empty = {
      score: 0, label: 'Project Learning Maturity: 0%',
      band: 'Early Stage', bandColour: 'score-band--early',
      components: { versions: 0, reviews: 0, risks: 0, depth: 0 },
      raw: { versions: 0, reviews: 0, risks: 0, depth: 0 },
    };
    if (!metrics) return empty;

    const rawVersions = metrics.total_versions    || 0;
    const rawReviews  = metrics.total_reviews     || 0;
    const rawRisks    = metrics.risks_identified  || 0;
    const rawDepth    = _deriveDepth(metrics);

    const cVersions = _clamp(rawVersions / VERSION_MAX, 0, 1) * WEIGHT_VERSIONS;
    const cReviews  = _clamp(rawReviews  / REVIEW_MAX,  0, 1) * WEIGHT_REVIEWS;
    const cRisks    = _clamp(rawRisks    / RISK_MAX,    0, 1) * WEIGHT_RISKS;
    const cDepth    = _clamp(rawDepth    / DEPTH_MAX,   0, 1) * WEIGHT_DEPTH;

    const score = Math.round((cVersions + cReviews + cRisks + cDepth) * 100);

    const bandDef = BANDS.find(b => score >= b.min) || BANDS[BANDS.length - 1];

    return {
      score,
      label:      `Project Learning Maturity: ${score}%`,
      band:       bandDef.label,
      bandColour: bandDef.colour,
      components: {
        versions: Math.round(cVersions * 100),
        reviews:  Math.round(cReviews  * 100),
        risks:    Math.round(cRisks    * 100),
        depth:    Math.round(cDepth    * 100),
      },
      raw: {
        versions: rawVersions,
        reviews:  rawReviews,
        risks:    rawRisks,
        depth:    rawDepth,
      },
    };
  }

  // ── Render ─────────────────────────────────────────────────
  /**
   * Render the Project Memory Score card.
   * Includes a segmented progress bar showing each component's contribution.
   *
   * @param {object|null} metrics - MetricsPayload
   * @returns {string} HTML
   */
  function render(metrics) {
    if (!metrics) {
      return `
        <div class="memory-score-card memory-score-card--loading" aria-label="Project Memory Score loading">
          <div class="skeleton" style="height:14px;width:60%;margin-bottom:8px"></div>
          <div class="skeleton" style="height:8px;width:100%"></div>
        </div>`;
    }

    const s = compute(metrics);

    // Segmented bar: 4 colour blocks proportional to each component
    const segments = [
      { key: 'versions', label: 'Versions',   value: s.components.versions, cls: 'seg--versions' },
      { key: 'reviews',  label: 'Reviews',    value: s.components.reviews,  cls: 'seg--reviews'  },
      { key: 'risks',    label: 'Risks',      value: s.components.risks,    cls: 'seg--risks'    },
      { key: 'depth',    label: 'Depth',      value: s.components.depth,    cls: 'seg--depth'    },
    ].filter(seg => seg.value > 0);

    const totalFilled = s.score;

    const segHtml = totalFilled > 0
      ? segments.map(seg => `
          <div class="memory-seg ${_esc(seg.cls)}"
               style="width:${seg.value}%"
               title="${_esc(seg.label)}: ${seg.value}%"
               aria-label="${_esc(seg.label)} contributes ${seg.value}%">
          </div>`).join('')
      : '';

    // Breakdown legend
    const legendHtml = segments.map(seg => `
      <span class="memory-legend-item">
        <span class="memory-legend-dot memory-legend-dot--${_esc(seg.key)}" aria-hidden="true"></span>
        <span class="memory-legend-label">${_esc(seg.label)}</span>
        <span class="memory-legend-value">${seg.value}%</span>
      </span>`).join('');

    return `
      <div class="memory-score-card ${_esc(s.bandColour)}"
           role="region"
           aria-label="${_esc(s.label)}">

        <div class="memory-score-header">
          <span class="memory-score-title">Project Learning Maturity</span>
          <span class="memory-score-band-badge">${_esc(s.band)}</span>
        </div>

        <div class="memory-score-value" aria-live="polite">
          ${s.score}<span class="memory-score-pct">%</span>
        </div>

        <!-- Progress bar -->
        <div class="memory-bar-wrap"
             role="progressbar"
             aria-valuenow="${s.score}"
             aria-valuemin="0"
             aria-valuemax="100"
             aria-label="${_esc(s.label)}">
          <div class="memory-bar">
            ${segHtml}
          </div>
        </div>

        <!-- Breakdown legend -->
        ${legendHtml ? `<div class="memory-legend" aria-label="Score breakdown">${legendHtml}</div>` : ''}

        <!-- Raw values tooltip row -->
        <div class="memory-raw-row">
          <span title="${s.raw.versions} versions">${s.raw.versions}v</span>
          <span class="memory-raw-sep">·</span>
          <span title="${s.raw.reviews} reviews">${s.raw.reviews}r</span>
          <span class="memory-raw-sep">·</span>
          <span title="${s.raw.risks} risks">${s.raw.risks} risks</span>
          <span class="memory-raw-sep">·</span>
          <span title="Max iteration depth ${s.raw.depth}">depth ${s.raw.depth}</span>
        </div>

      </div>`;
  }

  // ── Public: update DOM ─────────────────────────────────────
  /**
   * Update the #v2-memory-score container with fresh render output.
   * @param {object|null} metrics
   */
  function update(metrics) {
    const el = document.getElementById('v2-memory-score');
    if (!el) return;
    el.innerHTML = render(metrics);
  }

  // ── Mount ──────────────────────────────────────────────────
  /**
   * Subscribe to AppState 'metrics' and 'versions' changes, render immediately.
   */
  function mount() {
    const state = window.AppState;
    if (!state) return;

    const _refresh = () => update(state.get('metrics'));

    _refresh();
    // Re-compute when metrics or versions list changes
    state.subscribe('metrics',  _refresh);
    state.subscribe('versions', _refresh);
  }

  // ── Public API ─────────────────────────────────────────────
  return {
    compute,
    render,
    update,
    mount,
    // Expose constants for tests
    WEIGHT_VERSIONS,
    WEIGHT_REVIEWS,
    WEIGHT_RISKS,
    WEIGHT_DEPTH,
    VERSION_MAX,
    REVIEW_MAX,
    RISK_MAX,
    DEPTH_MAX,
    BANDS,
  };

})();

window.ProjectMemoryScore = ProjectMemoryScore;

// Auto-mount when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => ProjectMemoryScore.mount());
} else {
  ProjectMemoryScore.mount();
}
