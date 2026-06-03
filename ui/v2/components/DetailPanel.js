/**
 * DetailPanel.js — V2 Right-Side Detail Drawer Component
 *
 * TRACE: UI → Logic → API → Data
 * Component: DetailPanel
 * Inputs:  Version | Review entity (full object from API)
 * Outputs: HTML string injected into #v2-drawer-content
 * API:
 *   GET  /hierarchy/versions/{vid}              → version full detail
 *   GET  /hierarchy/reviews/{rid}               → review full detail
 *   POST /hierarchy/reviews/{rid}/weakness/{wid}/status  → Phase 2: weakness status + note
 *   POST /hierarchy/reviews/{rid}/decision/{did}/status  → Phase 2: decision status
 * Data:    Version (attributes + FK to reviews), Review (findings, questions,
 *          weaknesses, decision_points, included_files, persona, categories)
 *
 * Responsibilities:
 *  - Render version detail (metadata, artefact count, review list)
 *  - Render review detail (summary, findings by category with provenance line,
 *    quality status, persona, questions, weaknesses with status+note controls,
 *    decision points with status controls)
 *  - No page navigation — slide-in drawer only
 *  - Loading skeleton while full data is fetched
 *
 * Phase 2 additions:
 *  - Weakness row: status <select> (open/addressed/validated/rejected) + note
 *    <textarea> with onblur save; both wire to API.updateWeaknessStatus()
 *  - Decision points section: status <select> wired to API.updateDecisionStatus()
 *  - Provenance line under each finding block: shows included_files count +
 *    persona drawn directly from the review object (no extra API call)
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

  // ── Provenance line ───────────────────────────────────────
  /**
   * Phase 2.3: Lightweight provenance line for a findings block.
   * Uses data already present in the full review object — no extra API call.
   * Shows:  persona • N artefacts included • [category chips]
   * @param {object} r - full review object
   * @returns {string} HTML
   */
  function _renderProvenanceLine(r) {
    const persona       = r.persona || '';
    const fileCount     = (r.included_files || []).length;
    const cats          = (r.categories || []).slice(0, 4);
    const catChips      = cats.map(c =>
      `<span class="badge badge-default" style="font-size:9px;padding:1px 5px">${_esc(c)}</span>`
    ).join('');
    const moreCount     = (r.categories || []).length - cats.length;
    const moreBadge     = moreCount > 0
      ? `<span class="badge badge-default" style="font-size:9px;padding:1px 5px">+${moreCount}</span>`
      : '';

    if (!persona && !fileCount && !cats.length) return '';

    return `
      <div class="provenance-line" style="display:flex;flex-wrap:wrap;align-items:center;gap:5px;
           margin-bottom:8px;padding:5px 8px;background:var(--surface2);
           border-radius:var(--radius);border:1px solid var(--border);font-size:10px;color:var(--text-muted)">
        <span style="font-size:10px">🔍</span>
        ${persona ? `<span style="color:var(--text-dim)">${_esc(persona)}</span>` : ''}
        ${fileCount ? `<span>· ${fileCount} artefact${fileCount !== 1 ? 's' : ''}</span>` : ''}
        ${catChips}
        ${moreBadge}
      </div>`;
  }

  // ── Weakness row (interactive) ────────────────────────────
  /**
   * Phase 2: Renders a single weakness with status dropdown + note textarea.
   * Status change → POST .../weakness/{wid}/status immediately (status-only).
   * Note textarea blur → POST with current status + note text.
   *
   * Handlers use inline data attributes so they survive innerHTML injection
   * without requiring a component lifecycle.
   *
   * @param {object} w         - weakness object {id, text, category, status, user_note}
   * @param {string} reviewId
   * @param {string} projectId - read from AppState at call time
   * @returns {string} HTML
   */
  function _renderWeaknessRow(w, reviewId, projectId) {
    const wid    = _esc(w.id || '');
    const rid    = _esc(reviewId);
    const pid    = _esc(projectId);
    const status = w.status || 'open';
    const note   = w.user_note || '';

    const statusOpts = ['open', 'addressed', 'validated', 'rejected'].map(s =>
      `<option value="${s}" ${status === s ? 'selected' : ''}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`
    ).join('');

    // Status colour hint
    const statusColor = status === 'addressed' || status === 'validated'
      ? 'var(--green)'
      : status === 'rejected' ? 'var(--text-muted)' : 'var(--red)';

    return `
      <div class="weakness-row" style="border:1px solid var(--border);border-radius:var(--radius);
           padding:8px 10px;margin-bottom:6px;background:var(--surface)">
        <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">
          <span style="color:${statusColor};flex-shrink:0;margin-top:2px">⚠</span>
          <span style="font-size:12px;color:var(--text-dim);line-height:1.5;flex:1">${_esc((w.text || '').slice(0, 160))}</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
          <span style="font-size:10px;color:var(--text-muted);text-transform:capitalize">${_esc(w.category || '')}</span>
          <select
            style="font-size:11px;padding:2px 6px;background:var(--surface2);border:1px solid var(--border);
                   color:var(--text);border-radius:var(--radius);cursor:pointer"
            data-pid="${pid}" data-rid="${rid}" data-wid="${wid}"
            onchange="DetailPanel._onWeaknessStatusChange(this)">
            ${statusOpts}
          </select>
        </div>
        <textarea
          rows="2"
          placeholder="Add note…"
          style="width:100%;font-size:11px;background:var(--surface2);border:1px solid var(--border);
                 color:var(--text);border-radius:var(--radius);padding:5px 7px;resize:vertical;
                 font-family:inherit;line-height:1.5"
          data-pid="${pid}" data-rid="${rid}" data-wid="${wid}"
          onblur="DetailPanel._onWeaknessNoteBlur(this)">${_esc(note)}</textarea>
      </div>`;
  }

  // ── Decision point row (interactive) ─────────────────────
  /**
   * Phase 2: Renders a single decision point with status dropdown.
   * Status change → POST .../decision/{did}/status immediately.
   *
   * @param {object} dp        - decision point {id, text, status}
   * @param {string} reviewId
   * @param {string} projectId
   * @returns {string} HTML
   */
  function _renderDecisionRow(dp, reviewId, projectId) {
    const did    = _esc(dp.id || '');
    const rid    = _esc(reviewId);
    const pid    = _esc(projectId);
    const status = dp.status || 'open';

    const statusOpts = ['open', 'addressed', 'validated', 'rejected'].map(s =>
      `<option value="${s}" ${status === s ? 'selected' : ''}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`
    ).join('');

    const statusColor = status === 'addressed' || status === 'validated'
      ? 'var(--green)'
      : status === 'rejected' ? 'var(--text-muted)' : 'var(--yellow)';

    return `
      <div class="decision-row" style="border:1px solid var(--border);border-radius:var(--radius);
           padding:8px 10px;margin-bottom:6px;background:var(--surface)">
        <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">
          <span style="color:${statusColor};flex-shrink:0;margin-top:2px">◆</span>
          <span style="font-size:12px;color:var(--text-dim);line-height:1.5;flex:1">${_esc((dp.text || '').slice(0, 160))}</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          ${dp.category ? `<span style="font-size:10px;color:var(--text-muted);text-transform:capitalize">${_esc(dp.category)}</span>` : ''}
          <select
            style="font-size:11px;padding:2px 6px;background:var(--surface2);border:1px solid var(--border);
                   color:var(--text);border-radius:var(--radius);cursor:pointer"
            data-pid="${pid}" data-rid="${rid}" data-did="${did}"
            onchange="DetailPanel._onDecisionStatusChange(this)">
            ${statusOpts}
          </select>
        </div>
      </div>`;
  }

  // ── Inline event handlers (called from HTML via DetailPanel.*) ────────────

  /**
   * Status dropdown changed on a weakness row.
   * Performs a status-only update (user_note=null → not sent → preserved).
   * @param {HTMLSelectElement} sel
   */
  async function _onWeaknessStatusChange(sel) {
    const { pid, rid, wid } = sel.dataset;
    if (!pid || !rid || !wid) return;
    const api = window.API;
    if (!api || !api.updateWeaknessStatus) return;
    const result = await api.updateWeaknessStatus(pid, rid, wid, sel.value, null);
    if (result && result.error) {
      // Revert to the previous value on failure — find previously selected option
      console.warn('DetailPanel: weakness status update failed:', result.error);
    }
  }

  /**
   * Note textarea blurred on a weakness row.
   * Reads the sibling status select for current status value, then POSTs both.
   * @param {HTMLTextAreaElement} ta
   */
  async function _onWeaknessNoteBlur(ta) {
    const { pid, rid, wid } = ta.dataset;
    if (!pid || !rid || !wid) return;
    const api = window.API;
    if (!api || !api.updateWeaknessStatus) return;
    // Find the status select within the same .weakness-row container
    const row    = ta.closest('.weakness-row');
    const selEl  = row ? row.querySelector('select') : null;
    const status = selEl ? selEl.value : 'open';
    await api.updateWeaknessStatus(pid, rid, wid, status, ta.value);
  }

  /**
   * Status dropdown changed on a decision point row.
   * @param {HTMLSelectElement} sel
   */
  async function _onDecisionStatusChange(sel) {
    const { pid, rid, did } = sel.dataset;
    if (!pid || !rid || !did) return;
    const api = window.API;
    if (!api || !api.updateDecisionStatus) return;
    const result = await api.updateDecisionStatus(pid, rid, did, sel.value);
    if (result && result.error) {
      console.warn('DetailPanel: decision status update failed:', result.error);
    }
  }

  // ── Iteration handlers ────────────────────────────────────

  /**
   * Called when the "Iterate from this review" <summary> is clicked.
   * Lazily loads /api/personas into the persona <select> the first time
   * the panel is opened.
   * @param {HTMLElement} summaryEl
   */
  async function _onIterateSummaryClick(summaryEl) {
    const detailsEl = summaryEl.closest('details');
    if (!detailsEl) return;
    // Derive review_id from the details element id: v2-iterate-panel-{rid}
    const rid = detailsEl.id.replace('v2-iterate-panel-', '');
    const selectEl = document.getElementById('v2-iterate-persona-' + rid);
    if (!selectEl || selectEl.dataset.loaded) return;

    // Fetch personas from /api/personas
    try {
      const res = await fetch('/api/personas', { method: 'GET' });
      const data = await res.json();
      const roles = (data.personas || data.roles || []);
      if (roles.length) {
        selectEl.innerHTML = roles.map(r =>
          `<option value="${_esc(r.id || r.name)}">${_esc(r.name)}</option>`
        ).join('');
        selectEl.dataset.loaded = '1';
      } else {
        selectEl.innerHTML = '<option value="solution_architect">Solution Architect</option>'
          + '<option value="delivery_manager">Delivery Manager</option>'
          + '<option value="product_owner">Product Owner</option>';
        selectEl.dataset.loaded = '1';
      }
    } catch (e) {
      selectEl.innerHTML = '<option value="solution_architect">Solution Architect</option>'
        + '<option value="delivery_manager">Delivery Manager</option>'
        + '<option value="product_owner">Product Owner</option>';
      selectEl.dataset.loaded = '1';
    }
  }

  /**
   * Called when "Run Iteration" button is clicked inside the iteration panel.
   * POSTs to /iterate, shows inline result, refreshes hierarchy on success.
   * @param {HTMLButtonElement} btn
   */
  async function _onIterateSubmit(btn) {
    const rid = btn.dataset.reviewId;
    if (!rid) return;

    const state = window.AppState;
    const api   = window.API;
    if (!state || !api || !api.iterateReview) return;

    const proj = state.get('selectedProject');
    if (!proj) return;

    const personaSel  = document.getElementById('v2-iterate-persona-' + rid);
    const promptTa    = document.getElementById('v2-iterate-prompt-' + rid);
    const resultEl    = document.getElementById('v2-iterate-result-' + rid);

    const persona     = personaSel ? personaSel.value : 'solution_architect';
    const customPrompt = promptTa  ? promptTa.value.trim() : '';

    if (!persona) {
      if (resultEl) resultEl.innerHTML =
        '<p style="color:var(--red);font-size:11px">⚠ Select a persona to continue.</p>';
      return;
    }

    // Disable button while running
    btn.disabled = true;
    btn.textContent = '⟳ Running…';
    if (resultEl) resultEl.innerHTML =
      '<p style="color:var(--text-muted);font-size:11px">Running review iteration…</p>';

    try {
      const result = await api.iterateReview(
        proj.id, rid, persona,
        'files_only',
        customPrompt || undefined,
      );

      if (result && result.error) {
        if (resultEl) resultEl.innerHTML =
          `<p style="color:var(--red);font-size:11px">⚠ ${_esc(result.error)}</p>`;
      } else {
        const newRid = result.review_id || '(new review)';
        if (resultEl) resultEl.innerHTML =
          `<p style="color:var(--green);font-size:11px">✓ Iteration created: <strong>${_esc(newRid)}</strong></p>`;
        // Close the panel
        const detailsEl = document.getElementById('v2-iterate-panel-' + rid);
        if (detailsEl) detailsEl.open = false;
        // Refresh hierarchy so the new review appears in the accordion
        state.closeDrawer();
        if (window.Dashboard && window.Dashboard.loadAll) {
          await window.Dashboard.loadAll(true);
        }
      }
    } catch (e) {
      if (resultEl) resultEl.innerHTML =
        `<p style="color:var(--red);font-size:11px">⚠ ${_esc(e.message || 'Unexpected error')}</p>`;
    } finally {
      btn.disabled = false;
      btn.textContent = '▶ Run Iteration';
    }
  }

  // ── Review detail ─────────────────────────────────────────
  /**
   * TRACE: DetailPanel.renderReview → Data: Review entity
   * API: /hierarchy/reviews/{rid}
   *
   * Phase 2 additions:
   *  - Provenance line above findings (Phase 2.3)
   *  - Weaknesses section: status select + note textarea per item (Phase 2.1)
   *  - Decision points section: status select per item (Phase 2.2)
   *
   * @param {object} r - Review object (summary or full)
   * @returns {string} HTML
   */
  function renderReview(r) {
    if (!r) return _renderEmpty('No review data');

    // Resolve project_id from AppState (needed for API calls in event handlers)
    const projectId = (window.AppState && window.AppState.get('selectedProject'))
      ? window.AppState.get('selectedProject').id
      : '';

    // ── Findings sections ─────────────────────────────────
    const findings    = r.findings || {};
    const findingCats = Object.entries(findings).filter(([, items]) => Array.isArray(items) && items.length > 0);

    // Phase 2.3: single provenance line, rendered once above all finding blocks
    const provenanceLine = _renderProvenanceLine(r);

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

    // ── Questions ─────────────────────────────────────────
    const questionsHtml = (r.questions || []).length > 0
      ? `<div class="drawer-section">
          <div class="drawer-label">Open Questions (${(r.questions || []).length})</div>
          ${(r.questions || []).map(q =>
            `<div class="findings-item" style="border-left-color:var(--amber)">❓ ${_esc(String(q))}</div>`
          ).join('')}
        </div>` : '';

    // ── Weaknesses (Phase 2.1) ────────────────────────────
    // All weaknesses rendered, not just open, so user can update status from any state.
    const weaknesses = r.weaknesses || [];
    const weaknessHtml = weaknesses.length > 0
      ? `<div class="drawer-section">
          <div class="drawer-label" style="display:flex;align-items:center;gap:8px">
            Weaknesses
            <span class="badge badge-default">${weaknesses.length}</span>
            ${weaknesses.filter(w => !w.status || w.status === 'open').length > 0
              ? `<span class="badge badge-red">${weaknesses.filter(w => !w.status || w.status === 'open').length} open</span>`
              : '<span class="badge badge-green">all resolved</span>'}
          </div>
          ${weaknesses.map(w => _renderWeaknessRow(w, r.review_id || '', projectId)).join('')}
        </div>`
      : '';

    // ── Decision Points (Phase 2.2) ───────────────────────
    const decisionPoints = r.decision_points || [];
    const decisionHtml = decisionPoints.length > 0
      ? `<div class="drawer-section">
          <div class="drawer-label" style="display:flex;align-items:center;gap:8px">
            Decision Points
            <span class="badge badge-default">${decisionPoints.length}</span>
            ${decisionPoints.filter(dp => !dp.status || dp.status === 'open').length > 0
              ? `<span class="badge badge-amber">${decisionPoints.filter(dp => !dp.status || dp.status === 'open').length} open</span>`
              : '<span class="badge badge-green">all resolved</span>'}
          </div>
          ${decisionPoints.map(dp => _renderDecisionRow(dp, r.review_id || '', projectId)).join('')}
        </div>`
      : '';

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
        ${r.completeness_score != null ? _row('Completeness', `${r.completeness_score}%`) : ''}
      </div>

      ${r.summary ? `
        <div class="drawer-section">
          <div class="drawer-label">Summary</div>
          <p class="fs-12 text-secondary" style="line-height:1.6">${_esc(r.summary.slice(0, 300))}${r.summary.length > 300 ? '…' : ''}</p>
        </div>` : ''}

      ${findingsHtml ? `
        <div class="drawer-section">
          <div class="drawer-label">Findings by Category</div>
          ${provenanceLine}
          ${findingsHtml}
        </div>` : ''}

      ${questionsHtml}
      ${weaknessHtml}
      ${decisionHtml}

      <div class="drawer-section">
        <div class="drawer-label">Actions</div>
        <div id="v2-iterate-result-${_esc(r.review_id)}" style="margin-bottom:8px"></div>
        <details id="v2-iterate-panel-${_esc(r.review_id)}">
          <summary style="list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:6px;
            padding:5px 10px;background:var(--surface2);border:1px solid var(--border);
            border-radius:var(--radius);font-size:11px;font-weight:600;color:var(--accent);
            user-select:none"
            onclick="DetailPanel._onIterateSummaryClick(this)">
            ↩ Iterate from this review
          </summary>
          <div style="margin-top:8px;padding:10px;background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius)">
            <p style="font-size:11px;color:var(--text-dim);margin-bottom:8px">
              Creates a new review chained to <strong>${_esc(r.review_id)}</strong> as its predecessor.
              Open decision points are carried forward automatically.
            </p>
            <div style="margin-bottom:8px">
              <label style="font-size:10px;color:var(--text-muted);display:block;margin-bottom:4px">Persona</label>
              <select id="v2-iterate-persona-${_esc(r.review_id)}"
                style="width:100%;font-size:12px;padding:5px 8px;background:var(--surface);
                       border:1px solid var(--border);color:var(--text);border-radius:var(--radius)">
                <option value="">Loading personas…</option>
              </select>
            </div>
            <div style="margin-bottom:10px">
              <label style="font-size:10px;color:var(--text-muted);display:block;margin-bottom:4px">
                Additional context <span style="font-style:italic">(optional)</span>
              </label>
              <textarea id="v2-iterate-prompt-${_esc(r.review_id)}" rows="2"
                placeholder="e.g. Focus on security and DR gaps from prior review"
                style="width:100%;font-size:11px;background:var(--surface);border:1px solid var(--border);
                       color:var(--text);border-radius:var(--radius);padding:5px 8px;resize:vertical;
                       font-family:inherit;line-height:1.5"></textarea>
            </div>
            <button class="btn btn-sm"
              data-review-id="${_esc(r.review_id)}"
              onclick="DetailPanel._onIterateSubmit(this)">
              ▶ Run Iteration
            </button>
          </div>
        </details>
      </div>

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

  return {
    renderVersion,
    renderReview,
    renderSkeleton,
    // Phase 2: expose event handlers so inline onclick/onblur can reach them
    _onWeaknessStatusChange,
    _onWeaknessNoteBlur,
    _onDecisionStatusChange,
    // Phase 3: iteration handlers
    _onIterateSummaryClick,
    _onIterateSubmit,
  };
})();

if (typeof window !== 'undefined') window.DetailPanel = DetailPanel;
