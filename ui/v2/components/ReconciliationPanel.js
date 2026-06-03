/**
 * ReconciliationPanel.js — V2 Reconciliation Workflow Component
 *
 * TRACE: UI → Logic → API → Data
 * Component: ReconciliationPanel
 * API:
 *   GET  /hierarchy/reviews           → review list for current version
 *   POST /hierarchy/reconcile         → synthesize anchor + supplementals
 * Data:  ReconciliationResult
 *   { reconciled_findings, contradictions, reconciliation_notes,
 *     source_review_ids, anchor_review_id, generated_by, generated_at }
 *
 * Responsibilities:
 *  - Render a self-contained reconciliation form inside any container element
 *  - Multi-select: anchor review (dropdown) + supplemental reviews (checkboxes)
 *  - Validates that ≥1 review is selected before calling the API
 *  - Displays reconciled findings by category, conflicts, and reconciliation notes
 *  - Calls onComplete(result) callback on successful reconciliation
 *
 * Phase 4 design:
 *  - Single-review reconciliation is valid (anchor only, no supplementals)
 *    → produces deterministic dedup output for that review
 *  - All reviews shown come from the currently selected version in AppState
 *  - Container is injected by Dashboard into the drawer or a modal area
 *
 * Usage:
 *   ReconciliationPanel.render(containerEl, projectId, versionId, reviews, onComplete)
 *   ReconciliationPanel.onAnchorChange(selectEl)   ← inline onchange handler
 *   ReconciliationPanel.onRunReconcile(btnEl)       ← inline onclick handler
 */

'use strict';

const ReconciliationPanel = (() => {

  // ── Utilities ─────────────────────────────────────────────
  function _esc(s) {
    if (typeof s !== 'string') s = String(s || '');
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _fmtDate(iso) {
    if (!iso) return '–';
    return iso.slice(0, 16).replace('T', ' ');
  }

  // ── Category labels ───────────────────────────────────────
  const _CAT_LABELS = {
    risks:        '🔴 Risks',
    constraints:  '⛔ Constraints',
    dependencies: '🔗 Dependencies',
    assumptions:  '💭 Assumptions',
    action_items: '✅ Action Items',
  };

  // ── State (per rendered panel — stored in container dataset) ──
  // We persist minimal state in the DOM so multiple panels can coexist.

  // ── Public: render the panel into a container ─────────────
  /**
   * Renders the full reconciliation panel (form + results area) into containerEl.
   * Replaces any existing content in the container.
   *
   * @param {HTMLElement} containerEl  - target DOM element
   * @param {string}      projectId
   * @param {string}      versionId    - currently selected version
   * @param {Array}       reviews      - review summaries [{review_id, persona, quality_status, ...}]
   * @param {Function}    [onComplete] - optional callback(ReconciliationResult) called on success
   */
  function render(containerEl, projectId, versionId, reviews, onComplete) {
    if (!containerEl) return;

    // Store context in dataset so event handlers can retrieve it without closure refs
    containerEl.dataset.recPid   = projectId  || '';
    containerEl.dataset.recVid   = versionId  || '';
    containerEl.dataset.recReady = '1';

    if (!reviews || reviews.length === 0) {
      containerEl.innerHTML = `
        <div style="padding:16px;text-align:center;color:var(--text-muted);font-size:12px">
          <div style="font-size:24px;margin-bottom:8px">🔍</div>
          No reviews available for this version to reconcile.
        </div>`;
      return;
    }

    // Store serialised reviews list for use in handlers
    containerEl.dataset.recReviews = JSON.stringify(reviews.map(r => ({
      review_id:      r.review_id,
      persona:        r.persona || '–',
      quality_status: r.quality_status || 'pending',
      iteration_number: r.iteration_number || null,
    })));

    // Store onComplete as a named window function keyed by container id
    const cbKey = 'recCb_' + (containerEl.id || Math.random().toString(36).slice(2));
    containerEl.dataset.recCbKey = cbKey;
    if (typeof onComplete === 'function') window[cbKey] = onComplete;

    const anchorOpts = reviews.map(r => {
      const label = `${_esc(r.review_id)} — ${_esc(r.persona || '–')} (${_esc(r.quality_status || 'pending')})`;
      return `<option value="${_esc(r.review_id)}">${label}</option>`;
    }).join('');

    containerEl.innerHTML = `
      <div style="padding:12px 0">

        <div style="margin-bottom:10px">
          <label style="font-size:10px;font-weight:600;color:var(--text-muted);
                 text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:4px">
            Anchor Review
          </label>
          <p style="font-size:10px;color:var(--text-muted);margin-bottom:5px">
            The primary review. Its findings take precedence on any conflict.
          </p>
          <select id="rec-anchor-${_esc(versionId)}"
            style="width:100%;font-size:12px;padding:5px 8px;background:var(--surface);
                   border:1px solid var(--border);color:var(--text);border-radius:var(--radius)"
            onchange="ReconciliationPanel.onAnchorChange(this)">
            ${anchorOpts}
          </select>
        </div>

        <div id="rec-supp-area-${_esc(versionId)}" style="margin-bottom:12px">
          ${_renderSupplementalCheckboxes(reviews, reviews[0] && reviews[0].review_id, versionId)}
        </div>

        <div style="margin-bottom:12px">
          <label style="font-size:10px;font-weight:600;color:var(--text-muted);
                 text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:4px">
            AI Backend
          </label>
          <select id="rec-backend-${_esc(versionId)}"
            style="width:100%;font-size:12px;padding:5px 8px;background:var(--surface);
                   border:1px solid var(--border);color:var(--text);border-radius:var(--radius)">
            <option value="files_only" selected>Files Only (deterministic)</option>
          </select>
        </div>

        <button class="btn btn-sm"
          data-vid="${_esc(versionId)}"
          onclick="ReconciliationPanel.onRunReconcile(this)"
          id="rec-run-btn-${_esc(versionId)}">
          ⇄ Reconcile Reviews
        </button>
        <div id="rec-status-${_esc(versionId)}" style="margin-top:6px"></div>
        <div id="rec-result-${_esc(versionId)}" style="margin-top:12px"></div>

      </div>`;

    // Populate backend dropdown from window.state if available (v1 state)
    _populateBackendSelect('rec-backend-' + versionId);
  }

  // ── Supplemental checkboxes ───────────────────────────────
  function _renderSupplementalCheckboxes(reviews, anchorId, versionId) {
    const others = reviews.filter(r => r.review_id !== anchorId);
    if (others.length === 0) {
      return `<p style="font-size:11px;color:var(--text-muted);font-style:italic">
        Only one review in this version — reconciliation will deduplicate and normalise it.
      </p>`;
    }
    const checkboxes = others.map(r => {
      const label = `${_esc(r.review_id)} — ${_esc(r.persona || '–')} (${_esc(r.quality_status || 'pending')})`;
      return `
        <label style="display:flex;align-items:center;gap:8px;font-size:11px;
               padding:4px 0;cursor:pointer;color:var(--text-dim)">
          <input type="checkbox" class="rec-supp-check-${_esc(versionId)}"
            value="${_esc(r.review_id)}"
            style="accent-color:var(--accent);width:13px;height:13px">
          ${label}
        </label>`;
    }).join('');
    return `
      <label style="font-size:10px;font-weight:600;color:var(--text-muted);
             text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:5px">
        Supplemental Reviews <span style="font-weight:400;text-transform:none">(optional — check to include)</span>
      </label>
      ${checkboxes}`;
  }

  function _populateBackendSelect(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    // Try to read available backends from window.state (v1 state object)
    const backends = (window.state && window.state.backends) || [];
    if (backends.length > 1) {
      sel.innerHTML = backends.map(b =>
        `<option value="${_esc(b.name)}">${_esc(b.display_name || b.name)}${b.available ? '' : ' (not configured)'}</option>`
      ).join('');
    }
  }

  // ── Event: anchor dropdown changed ────────────────────────
  /**
   * Rebuilds the supplemental checkboxes when the anchor selection changes.
   * @param {HTMLSelectElement} selectEl
   */
  function onAnchorChange(selectEl) {
    const vid = selectEl.id.replace('rec-anchor-', '');
    const newAnchorId = selectEl.value;
    const container = selectEl.closest('[data-rec-ready]');
    if (!container) return;

    let reviews = [];
    try { reviews = JSON.parse(container.dataset.recReviews || '[]'); } catch (e) {}

    const suppArea = document.getElementById('rec-supp-area-' + vid);
    if (suppArea) {
      suppArea.innerHTML = _renderSupplementalCheckboxes(reviews, newAnchorId, vid);
    }
  }

  // ── Event: run reconcile button clicked ───────────────────
  /**
   * Collects anchor + checked supplementals, calls API.reconcileReviews(),
   * renders the result.
   * @param {HTMLButtonElement} btnEl
   */
  async function onRunReconcile(btnEl) {
    const vid = btnEl.dataset.vid;
    if (!vid) return;

    const container  = btnEl.closest('[data-rec-ready]');
    if (!container) return;

    const projectId  = container.dataset.recPid;
    const anchorSel  = document.getElementById('rec-anchor-' + vid);
    const backendSel = document.getElementById('rec-backend-' + vid);
    const statusEl   = document.getElementById('rec-status-' + vid);
    const resultEl   = document.getElementById('rec-result-' + vid);

    const anchorId   = anchorSel  ? anchorSel.value  : '';
    const aiBackend  = backendSel ? backendSel.value : 'files_only';

    if (!anchorId) {
      if (statusEl) statusEl.innerHTML =
        '<p style="color:var(--red);font-size:11px">⚠ Select an anchor review.</p>';
      return;
    }

    // Collect checked supplementals
    const suppChecks = container.querySelectorAll('.rec-supp-check-' + vid + ':checked');
    const supplementalIds = Array.from(suppChecks).map(cb => cb.value);

    const api = window.API;
    if (!api || !api.reconcileReviews) {
      if (statusEl) statusEl.innerHTML =
        '<p style="color:var(--red);font-size:11px">⚠ API not available.</p>';
      return;
    }

    btnEl.disabled = true;
    btnEl.textContent = '⟳ Reconciling…';
    if (statusEl) statusEl.innerHTML =
      '<p style="color:var(--text-muted);font-size:11px">Reconciling reviews…</p>';
    if (resultEl) resultEl.innerHTML = '';

    try {
      const result = await api.reconcileReviews(projectId, anchorId, supplementalIds, aiBackend);

      if (result && result.error) {
        if (statusEl) statusEl.innerHTML =
          `<p style="color:var(--red);font-size:11px">⚠ ${_esc(result.error)}</p>`;
      } else {
        if (statusEl) statusEl.innerHTML =
          '<p style="color:var(--green);font-size:11px">✓ Reconciliation complete.</p>';
        if (resultEl) resultEl.innerHTML = renderResult(result);

        // Fire onComplete callback if registered
        const cbKey = container.dataset.recCbKey;
        if (cbKey && typeof window[cbKey] === 'function') {
          try { window[cbKey](result); } catch (e) {}
        }
      }
    } catch (e) {
      if (statusEl) statusEl.innerHTML =
        `<p style="color:var(--red);font-size:11px">⚠ ${_esc(e.message || 'Unexpected error')}</p>`;
    } finally {
      btnEl.disabled = false;
      btnEl.textContent = '⇄ Reconcile Reviews';
    }
  }

  // ── Result rendering ──────────────────────────────────────
  /**
   * Renders a ReconciliationResult dict as HTML.
   * Used both by the inline panel and by any external consumer.
   *
   * @param {object} result  - ReconciliationResult.to_dict() shape
   * @returns {string}       - HTML string
   */
  function renderResult(result) {
    if (!result) return '';

    const findings    = result.reconciled_findings || {};
    const conflicts   = result.contradictions      || [];
    const notes       = result.reconciliation_notes || '';
    const sourceIds   = result.source_review_ids   || [];
    const generatedBy = result.generated_by        || '–';
    const generatedAt = result.generated_at        || '';

    // Header bar
    const header = `
      <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;
           padding:8px 12px;background:var(--surface2);border:1px solid var(--border);
           border-radius:var(--radius-lg);margin-bottom:10px">
        <span style="font-size:12px;font-weight:600;color:var(--accent)">Reconciled</span>
        <span style="font-size:10px;color:var(--text-muted)">·</span>
        <span style="font-size:11px;color:var(--text-dim)">${sourceIds.map(id => _esc(id)).join(' + ')}</span>
        <span style="margin-left:auto;font-size:10px;color:var(--text-muted)">${_esc(generatedBy)} · ${_fmtDate(generatedAt)}</span>
        ${conflicts.length ? `<span style="font-size:11px;font-weight:700;color:var(--yellow)">⚠ ${conflicts.length} conflict${conflicts.length !== 1 ? 's' : ''}</span>` : ''}
      </div>`;

    // Findings per category
    const findingsHtml = Object.entries(_CAT_LABELS).map(([cat, label]) => {
      const items = findings[cat] || [];
      if (items.length === 0) return '';
      const rows = items.slice(0, 8).map(t =>
        `<div style="font-size:11px;padding:3px 0 3px 8px;color:var(--text-dim);
              border-left:2px solid var(--border);margin-bottom:2px">${_esc(String(t))}</div>`
      ).join('');
      const more = items.length > 8
        ? `<p style="font-size:10px;color:var(--text-muted);margin-top:2px">+ ${items.length - 8} more</p>` : '';
      return `
        <details open style="border:1px solid var(--border);border-radius:var(--radius);
                margin-bottom:6px;overflow:hidden">
          <summary style="list-style:none;cursor:pointer;display:flex;align-items:center;gap:8px;
            padding:7px 10px;background:var(--surface2);font-size:11px;font-weight:600">
            <span>${label}</span>
            <span style="font-size:10px;background:var(--surface3);border-radius:20px;
                   padding:1px 7px;color:var(--text-dim)">${items.length}</span>
          </summary>
          <div style="padding:6px 10px 8px">${rows}${more}</div>
        </details>`;
    }).join('');

    // Conflicts
    const conflictsHtml = conflicts.length > 0 ? `
      <div style="margin-top:10px;padding:10px 12px;
           background:rgba(210,153,34,.08);border:1px solid rgba(210,153,34,.4);
           border-radius:var(--radius-lg)">
        <div style="font-size:11px;font-weight:700;color:var(--yellow);margin-bottom:6px">
          ⚠ Conflicts Detected (${conflicts.length})
        </div>
        ${conflicts.map(c => `
          <div style="font-size:11px;color:var(--text-dim);padding:3px 0 3px 8px;
               border-left:2px solid var(--yellow);margin-bottom:4px">
            ${_esc(c.description || String(c))}
            ${c.review_ids && c.review_ids.length ?
              `<span style="font-size:10px;color:var(--text-muted);margin-left:6px">[${c.review_ids.map(id => _esc(id)).join(', ')}]</span>` : ''}
          </div>`).join('')}
      </div>` : '';

    // Reconciliation notes
    const notesHtml = notes ? `
      <div style="margin-top:10px;padding:8px 10px;background:var(--surface2);
           border:1px solid var(--border);border-radius:var(--radius)">
        <div style="font-size:10px;font-weight:700;color:var(--text-muted);
             text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">
          Reconciliation Notes
        </div>
        <p style="font-size:11px;color:var(--text-dim);line-height:1.6;
                  white-space:pre-wrap">${_esc(notes.slice(0, 600))}${notes.length > 600 ? '…' : ''}</p>
      </div>` : '';

    return header + findingsHtml + conflictsHtml + notesHtml;
  }

  return {
    render,
    renderResult,
    onAnchorChange,
    onRunReconcile,
  };

})();

if (typeof window !== 'undefined') window.ReconciliationPanel = ReconciliationPanel;
