/**
 * DetailPanel.js — V2 Right-Side Detail Drawer Component
 *
 * TRACE: UI → Logic → API → Data
 * Component: DetailPanel
 * Inputs:  Version | Review entity (full object from API)
 * Outputs: HTML string injected into #v2-drawer-content
 * API:     /hierarchy/versions/{vid}, /hierarchy/reviews/{rid}
 * Data:    Version (attributes + FK to reviews), Review (findings, questions)
 *
 * Responsibilities:
 *  - Render version detail (metadata, artefact count, review list)
 *  - Render review detail (summary, findings by category, quality status,
 *    persona, questions, weaknesses)
 *  - No page navigation — slide-in drawer only
 *  - Loading skeleton while full data is fetched
 *
 * Selection loop:
 *   Click entity → AppState.openDrawer(type, data) → drawer renders summary
 *   → fetchDetail() resolves → drawer updates to full detail
 */

'use strict';

const DetailPanel = (() => {

  // ── Utilities ─────────────────────────────────────────────
  function _esc(s) {
    if (typeof s !== 'string') s = String(s || '');
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _fmtDate(iso) {
    if (!iso) return '–';
    return iso.slice(0, 16).replace('T', ' ');
  }

  function _qualityBadge(status) {
    if (status === 'complete') return '<span class="badge badge-green">Final</span>';
    if (status === 'interim')  return '<span class="badge badge-amber">Draft</span>';
    return '<span class="badge badge-default">Pending</span>';
  }

  function _row(label, value) {
    return `
      <div class="detail-row">
        <div class="detail-row-label">${_esc(label)}</div>
        <div class="detail-row-value">${value}</div>
      </div>`;
  }

  function _divider() {
    return '<div class="divider"></div>';
  }

  // ── Version detail ────────────────────────────────────────
  /**
   * TRACE: DetailPanel.renderVersion → Data: Version entity
   * @param {object} v - Version object (summary or full)
   * @returns {string} HTML
   */
  function renderVersion(v) {
    if (!v) return _renderEmpty('No version data');

    const reviewCount   = (v.reviews || []).length || v.review_count || 0;
    const artifactCount = v.artifact_count || (v.included_artifacts || []).length || 0;

    const reviewRows = (v.reviews || []).map(r => `
      <div class="review-item" style="margin-bottom:4px"
           role="button" tabindex="0"
           onclick="VersionAccordion.onReviewClick(this)"
           data-review-id="${_esc(r.review_id)}"
           data-version-id="${_esc(v.version_id)}">
        <span class="status-dot ${r.quality_status === 'complete' ? 'complete' : r.quality_status === 'interim' ? 'in-progress' : 'pending'}"></span>
        <span class="review-item-id">${_esc(r.review_id)}</span>
        <span class="review-item-persona">${_esc(r.persona || '–')}</span>
        ${_qualityBadge(r.quality_status)}
        ${r.review_id === v.active_review_id ? '<span class="badge badge-primary">Active</span>' : ''}
      </div>`).join('');

    return `
      <div class="drawer-section">
        <div class="flex flex-between align-center">
          <span class="fw-700 fs-13">${_esc(v.version_id)}</span>
          <span class="badge badge-primary">Version</span>
        </div>
        ${v.label ? `<p class="text-secondary fs-12 mt-2">${_esc(v.label)}</p>` : ''}
      </div>

      <div class="drawer-section">
        <div class="drawer-label">Details</div>
        ${_row('Phase',      _esc(v.phase_id || '–'))}
        ${_row('Created',    _fmtDate(v.created_at))}
        ${_row('Persona',    _esc(v.persona || '–'))}
        ${_row('AI Backend', _esc(v.ai_backend || 'files_only'))}
        ${_row('Artefacts',  String(artifactCount))}
        ${_row('Reviews',    String(reviewCount))}
        ${v.active_review_id ? _row('Active Review', `<span class="badge badge-green">${_esc(v.active_review_id)}</span>`) : ''}
      </div>

      ${v.scope ? `
        <div class="drawer-section">
          <div class="drawer-label">Scope</div>
          <p class="fs-12 text-secondary" style="white-space:pre-wrap;line-height:1.6">
            ${_esc(v.scope.slice(0, 400))}${v.scope.length > 400 ? '…' : ''}
          </p>
        </div>` : ''}

      ${reviewRows ? `
        <div class="drawer-section">
          <div class="drawer-label">Reviews in this Version</div>
          <div class="review-list">${reviewRows}</div>
        </div>` : ''}`;
  }

  // ── Review detail ─────────────────────────────────────────
  /**
   * TRACE: DetailPanel.renderReview → Data: Review entity
   * API: /hierarchy/reviews/{rid}
   * @param {object} r - Review object (summary or full)
   * @returns {string} HTML
   */
  function renderReview(r) {
    if (!r) return _renderEmpty('No review data');

    // Build findings sections
    const findings = r.findings || {};
    const findingCats = Object.entries(findings).filter(([, items]) => Array.isArray(items) && items.length > 0);

    const findingsHtml = findingCats.map(([cat, items]) => {
      const catLabel = cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      const rows = items.slice(0, 5).map(item =>
        `<div class="findings-item">${_esc(typeof item === 'object' ? (item.description || JSON.stringify(item)) : String(item))}</div>`
      ).join('');
      const moreCount = items.length - 5;
      return `
        <div class="findings-block">
          <div class="findings-block-title">${_esc(catLabel)} <span class="badge badge-default">${items.length}</span></div>
          ${rows}
          ${moreCount > 0 ? `<p class="text-muted fs-11 mt-2">+ ${moreCount} more</p>` : ''}
        </div>`;
    }).join('');

    const questionsHtml = (r.questions || []).length > 0
      ? `<div class="drawer-section">
          <div class="drawer-label">Open Questions (${(r.questions || []).length})</div>
          ${(r.questions || []).map(q =>
            `<div class="findings-item" style="border-left-color:var(--amber)">❓ ${_esc(String(q))}</div>`
          ).join('')}
        </div>` : '';

    const weaknesses = (r.weaknesses || []).filter(w => w.status === 'open' || !w.status);
    const weaknessHtml = weaknesses.length > 0
      ? `<div class="drawer-section">
          <div class="drawer-label">Open Weaknesses (${weaknesses.length})</div>
          ${weaknesses.slice(0, 4).map(w =>
            `<div class="findings-item" style="border-left-color:var(--red)">⚠ ${_esc((w.text || '').slice(0, 100))}</div>`
          ).join('')}
        </div>` : '';

    const totalFindings = findingCats.reduce((sum, [, items]) => sum + items.length, 0)
                          || r.total_findings || 0;

    return `
      <div class="drawer-section">
        <div class="flex flex-between align-center gap-2 wrap">
          <span class="fw-700 fs-13">${_esc(r.review_id)}</span>
          <div class="flex gap-2 wrap">
            <span class="badge badge-secondary">Review</span>
            ${_qualityBadge(r.quality_status)}
            ${r.iteration_number ? `<span class="badge badge-default">R${r.iteration_number}</span>` : ''}
          </div>
        </div>
        ${r.persona ? `<p class="text-secondary fs-12 mt-2">${_esc(r.persona)}</p>` : ''}
      </div>

      <div class="drawer-section">
        <div class="drawer-label">Details</div>
        ${_row('Version',    `<span class="badge badge-primary">${_esc(r.version_id || '–')}</span>`)}
        ${_row('Phase',      _esc(r.phase_id || '–'))}
        ${_row('Created',    _fmtDate(r.created_at))}
        ${_row('AI Backend', _esc(r.ai_backend || 'files_only'))}
        ${totalFindings ? _row('Total Findings', `<span class="badge badge-amber">${totalFindings}</span>`) : ''}
        ${r.completeness_score ? _row('Completeness', `${r.completeness_score}%`) : ''}
      </div>

      ${r.summary ? `
        <div class="drawer-section">
          <div class="drawer-label">Summary</div>
          <p class="fs-12 text-secondary" style="line-height:1.6">${_esc(r.summary.slice(0, 300))}${r.summary.length > 300 ? '…' : ''}</p>
        </div>` : ''}

      ${findingsHtml ? `
        <div class="drawer-section">
          <div class="drawer-label">Findings by Category</div>
          ${findingsHtml}
        </div>` : ''}

      ${questionsHtml}
      ${weaknessHtml}

      <div class="drawer-section">
        <button class="btn btn-outline btn-sm"
                onclick="AppState.closeDrawer()"
                style="width:100%">
          Close Panel
        </button>
      </div>`;
  }

  // ── Loading skeleton ──────────────────────────────────────
  function renderSkeleton() {
    return `
      <div class="drawer-section">
        <div class="skeleton" style="height:18px;width:50%;margin-bottom:8px"></div>
        <div class="skeleton" style="height:12px;width:80%"></div>
      </div>
      <div class="drawer-section">
        <div class="skeleton" style="height:12px;width:40%;margin-bottom:6px"></div>
        <div class="skeleton" style="height:12px;width:100%;margin-bottom:4px"></div>
        <div class="skeleton" style="height:12px;width:90%;margin-bottom:4px"></div>
        <div class="skeleton" style="height:12px;width:75%"></div>
      </div>`;
  }

  // ── Empty state ───────────────────────────────────────────
  function _renderEmpty(msg) {
    return `<div class="empty-state">
      <div class="empty-state-icon">🔍</div>
      <div class="empty-state-title">${_esc(msg)}</div>
    </div>`;
  }

  return { renderVersion, renderReview, renderSkeleton };
})();

if (typeof window !== 'undefined') window.DetailPanel = DetailPanel;
