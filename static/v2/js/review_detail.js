/**
 * review_detail.js — Sprint 1: Review Full Details Panel
 *
 * TRACE: UI → DetailPanel → AppState.drawerEntity → Review (full)
 * Replaces the inline renderReview fallback in dashboard.js.
 *
 * Public API (window.ReviewDetail):
 *   ReviewDetail.renderReview(r)      → HTML string for drawer
 *   ReviewDetail.renderVersion(v)     → HTML string (delegates to existing logic)
 *   ReviewDetail.onWeaknessStatus()   → handles status dropdown change
 *   ReviewDetail.onWeaknessNote()     → handles note textarea input/save
 *
 * Features (Sprint 1):
 *   F1 — Always-visible header: Review ID, Version ID, Persona, Prompt,
 *          Top-3 risks, Status, Created/Updated
 *   F2 — Artifact provenance display (type-aware chips)
 *   F3 — Weakness status + optional free-text user note (persist via API)
 *   Non-regression: compare stays separate; old records render safely
 */

'use strict';

const ReviewDetail = (() => {

  // ── Constants ─────────────────────────────────────────────────────────────

  const WEAKNESS_STATUSES = ['open', 'addressed', 'validated', 'rejected'];

  const ARTIFACT_TYPE_ICONS = {
    document:      '📄',
    slides:        '📊',
    email:         '✉️',
    meeting_notes: '📝',
    spreadsheet:   '📋',
  };

  const QUALITY_LABELS = {
    complete: 'Final',
    interim:  'Draft',
    pending:  'Pending',
  };

  const QUALITY_CLASSES = {
    complete: 'badge-green',
    interim:  'badge-amber',
    pending:  'badge-default',
  };

  // ── HTML escape ────────────────────────────────────────────────────────────

  function _esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }



  function _fmtDate(iso) {
    if (!iso) return '–';
    return iso.slice(0, 16).replace('T', ' ');
  }

  // ── Shared detail-row helper ───────────────────────────────────────────────

  function _row(label, value) {
    return `<div class="rd-detail-row">
      <span class="rd-detail-label">${_esc(label)}</span>
      <span class="rd-detail-value">${value}</span>
    </div>`;
  }

  // ── Badge helpers ──────────────────────────────────────────────────────────

  function _qualityBadge(status) {
    const cls   = QUALITY_CLASSES[status] || 'badge-default';
    const label = QUALITY_LABELS[status]  || 'Pending';
    return `<span class="badge ${_esc(cls)}">${_esc(label)}</span>`;
  }

  // ── F1: Always-visible header block ───────────────────────────────────────

  function _renderHeader(r) {
    const iterLabel = r.iteration_number ? `R${r.iteration_number}` : _esc(r.review_id);
    const persona   = r.persona || r.persona_used || '–';

    return `<div class="rd-header">
      <div class="rd-header-top">
        <div class="rd-title-row">
          <span class="rd-review-id">${_esc(iterLabel)}</span>
          <span class="rd-review-raw-id">${_esc(r.review_id)}</span>
          <div class="rd-badges">
            <span class="badge badge-secondary">Review</span>
            ${_qualityBadge(r.quality_status)}
          </div>
        </div>
      </div>
      <div class="rd-meta-grid">
        ${_row('Version',  `<span class="badge badge-primary">${_esc(r.version_id || '–')}</span>`)}
        ${_row('Persona',  `<span class="rd-persona">${_esc(persona)}</span>`)}
        ${_row('Status',   _qualityBadge(r.quality_status))}
        ${_row('Created',  _esc(_fmtDate(r.created_at)))}
        ${r.completeness_score
          ? _row('Completeness', `<span class="rd-score">${r.completeness_score}%</span>`)
          : ''}
        ${r.previous_review_id
          ? _row('Builds on', `<span class="badge badge-default">${_esc(r.previous_review_id)}</span>`)
          : ''}
      </div>
    </div>`;
  }



  // ── F1: Prompt used (expandable) ──────────────────────────────────────────

  function _renderPrompt(r) {
    const prompt = r.prompt_used || r.custom_prompt || '';
    if (!prompt) return '';
    const preview = prompt.length > 180 ? prompt.slice(0, 180) + '…' : prompt;
    return `<details class="rd-expandable">
      <summary class="rd-expandable-summary">
        <span class="rd-section-label">Prompt Used</span>
        <span class="rd-expand-hint">▶</span>
      </summary>
      <div class="rd-expandable-body">
        <p class="rd-prompt-text">${_esc(preview)}</p>
        ${prompt.length > 180
          ? `<p class="rd-prompt-full" style="display:none">${_esc(prompt)}</p>
             <button class="rd-show-more-btn"
               onclick="this.previousElementSibling.style.display='block';
                        this.previousElementSibling.previousElementSibling.style.display='none';
                        this.style.display='none'">
               Show full prompt
             </button>`
          : ''}
      </div>
    </details>`;
  }

  // ── F1: Top-3 risks (always visible) ──────────────────────────────────────

  function _renderTopRisks(r) {
    const findings = r.findings || {};
    const risks = (findings.risks || []).slice(0, 3);
    if (!risks.length) {
      return `<div class="rd-section">
        <div class="rd-section-label">Top Risks</div>
        <p class="rd-empty-note">No risks identified in this review.</p>
      </div>`;
    }
    const items = risks.map(risk => {
      const text = typeof risk === 'object' ? (risk.description || risk.text || JSON.stringify(risk)) : String(risk);
      return `<div class="rd-risk-item">
        <span class="rd-risk-marker">🔴</span>
        <span class="rd-risk-text">${_esc(text)}</span>
      </div>`;
    }).join('');
    return `<div class="rd-section">
      <div class="rd-section-label">Top Risks <span class="rd-count-badge">${risks.length}</span></div>
      <div class="rd-risk-list">${items}</div>
    </div>`;
  }

  // ── F1: Summary ────────────────────────────────────────────────────────────

  function _renderSummary(r) {
    if (!r.summary) return '';
    return `<div class="rd-section">
      <div class="rd-section-label">Summary</div>
      <p class="rd-summary-text">${_esc(r.summary)}</p>
    </div>`;
  }



  // ── F2: Artifact provenance display ───────────────────────────────────────

  /**
   * Build a human-readable reference line from a provenance entry.
   * Artifact-type-aware: document, slides, email, meeting_notes, spreadsheet.
   * Degrades gracefully when fields are missing.
   */
  function _provenanceRef(ref) {
    if (!ref || typeof ref !== 'object') return null;
    const name = ref.artifact_name || ref.file_name || '';
    const type = (ref.artifact_type || 'document').toLowerCase();
    const icon = ARTIFACT_TYPE_ICONS[type] || '📎';
    let detail = '';

    if (type === 'slides') {
      const parts = [
        ref.slide_number  ? `Slide ${ref.slide_number}` : null,
        ref.slide_title   || null,
      ].filter(Boolean);
      detail = parts.join(' · ');
    } else if (type === 'email') {
      const parts = [
        ref.subject ? `"${ref.subject}"` : null,
        ref.date    || null,
        ref.sender  ? `from ${ref.sender}` : null,
      ].filter(Boolean);
      detail = parts.join(' · ');
    } else if (type === 'meeting_notes') {
      const parts = [
        ref.meeting_name || null,
        ref.date         || null,
        ref.timestamp    ? `@ ${ref.timestamp}` : (ref.section_reference || null),
      ].filter(Boolean);
      detail = parts.join(' · ');
    } else if (type === 'spreadsheet') {
      const parts = [
        ref.sheet       || null,
        ref.row_range   || null,
      ].filter(Boolean);
      detail = parts.join(' · ');
    } else {
      // document / default
      const parts = [
        ref.section_reference || null,
        ref.page_reference    ? `p. ${ref.page_reference}` : null,
      ].filter(Boolean);
      detail = parts.join(' · ');
    }

    return { icon, name, detail, excerpt: ref.excerpt || '', type };
  }

  function _renderArtifactRefs(r) {
    const refs    = r.artifact_refs || [];
    const files   = r.included_files || [];

    // If no structured refs, fall back to flat file list
    if (!refs.length && !files.length) return '';

    let content = '';
    if (refs.length) {
      const chips = refs.map(ref => {
        const p = _provenanceRef(ref);
        if (!p) return '';
        const tipLines = [p.name, p.detail, p.excerpt].filter(Boolean);
        const tip = tipLines.join(' → ');
        return `<span class="rd-prov-chip rd-prov-chip--${_esc(p.type)}"
                      title="${_esc(tip)}">
          ${p.icon} <span class="rd-prov-name">${_esc(p.name || 'Artifact')}</span>
          ${p.detail ? `<span class="rd-prov-detail">${_esc(p.detail)}</span>` : ''}
        </span>`;
      }).join('');
      content = `<div class="rd-prov-chips">${chips}</div>`;
    } else {
      // Flat fallback
      const chips = files.slice(0, 8).map(f =>
        `<span class="rd-prov-chip rd-prov-chip--document" title="${_esc(f)}">
           📄 <span class="rd-prov-name">${_esc(f)}</span>
         </span>`
      ).join('');
      const more = files.length > 8
        ? `<span class="rd-prov-chip rd-prov-chip--more">+${files.length - 8} more</span>` : '';
      content = `<div class="rd-prov-chips">${chips}${more}</div>`;
    }

    return `<details class="rd-expandable" open>
      <summary class="rd-expandable-summary">
        <span class="rd-section-label">Included Artifacts
          <span class="rd-count-badge">${refs.length || files.length}</span>
        </span>
        <span class="rd-expand-hint">▶</span>
      </summary>
      <div class="rd-expandable-body">${content}</div>
    </details>`;
  }



  // ── F1: Findings (expandable, all categories) ─────────────────────────────

  function _renderFindings(r) {
    const findings = r.findings || {};
    const cats = Object.entries(findings).filter(([, v]) => Array.isArray(v) && v.length);
    if (!cats.length) return '';

    const total = cats.reduce((s, [, v]) => s + v.length, 0);
    const CAT_ICONS = {
      risks: '🔴', assumptions: '💭', dependencies: '🔗',
      constraints: '⛔', action_items: '✅', gaps: '🔍',
      findings: '📋', recommendations: '💡', questions: '❓',
    };

    const blocks = cats.map(([cat, items]) => {
      const label = cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      const icon  = CAT_ICONS[cat] || '•';
      const rows  = items.slice(0, 5).map(item => {
        const text = typeof item === 'object'
          ? (item.description || item.text || JSON.stringify(item))
          : String(item);
        return `<div class="rd-finding-item">${_esc(text)}</div>`;
      }).join('');
      const more = items.length > 5
        ? `<p class="rd-more-note">+ ${items.length - 5} more</p>` : '';
      return `<div class="rd-finding-block">
        <div class="rd-finding-cat">${icon} ${_esc(label)}
          <span class="rd-count-badge">${items.length}</span>
        </div>
        ${rows}${more}
      </div>`;
    }).join('');

    return `<details class="rd-expandable">
      <summary class="rd-expandable-summary">
        <span class="rd-section-label">Findings
          <span class="rd-count-badge">${total}</span>
        </span>
        <span class="rd-expand-hint">▶</span>
      </summary>
      <div class="rd-expandable-body">${blocks}</div>
    </details>`;
  }

  // ── F1: Open questions (expandable) ───────────────────────────────────────

  function _renderQuestions(r) {
    const qs = r.questions || [];
    if (!qs.length) return '';
    const items = qs.map(q =>
      `<div class="rd-finding-item rd-finding-item--question">❓ ${_esc(String(q))}</div>`
    ).join('');
    return `<details class="rd-expandable">
      <summary class="rd-expandable-summary">
        <span class="rd-section-label">Open Questions
          <span class="rd-count-badge">${qs.length}</span>
        </span>
        <span class="rd-expand-hint">▶</span>
      </summary>
      <div class="rd-expandable-body">${items}</div>
    </details>`;
  }



  // ── F3: Weakness status + user note ───────────────────────────────────────

  function _renderWeaknesses(r) {
    const weaknesses = r.weaknesses || [];
    if (!weaknesses.length) return '';

    const projectId = (() => {
      const s = window.AppState;
      const p = s ? s.get('selectedProject') : null;
      return p ? p.id : '';
    })();

    const items = weaknesses.map((w, idx) => {
      if (!w || typeof w !== 'object') return '';
      const wid    = w.id || `w_${idx}`;
      const text   = w.text || w.description || '';
      const status = w.status || 'open';
      const note   = w.user_note || '';
      const cat    = w.category || '';
      const statusOpts = WEAKNESS_STATUSES.map(s =>
        `<option value="${_esc(s)}" ${s === status ? 'selected' : ''}>${_esc(s)}</option>`
      ).join('');
      const statusCls = status === 'open'     ? 'rd-weakness-status--open'
                      : status === 'resolved'  ? 'rd-weakness-status--resolved'
                      : status === 'mitigated' ? 'rd-weakness-status--mitigated'
                      : 'rd-weakness-status--other';

      return `<div class="rd-weakness-item" id="rd-w-${_esc(wid)}">
        <div class="rd-weakness-header">
          <span class="rd-weakness-icon">⚠</span>
          <span class="rd-weakness-text">${_esc(text)}</span>
          ${cat ? `<span class="rd-weakness-cat">${_esc(cat)}</span>` : ''}
        </div>
        <div class="rd-weakness-controls">
          <label class="rd-ctrl-label">Status</label>
          <select class="rd-status-select ${_esc(statusCls)}"
                  data-review-id="${_esc(r.review_id)}"
                  data-weakness-id="${_esc(wid)}"
                  data-project-id="${_esc(projectId)}"
                  onchange="ReviewDetail.onWeaknessStatus(this)">
            ${statusOpts}
          </select>
          <label class="rd-ctrl-label rd-ctrl-note-label">Note</label>
          <textarea class="rd-note-textarea"
                    rows="2"
                    placeholder="Optional note…"
                    data-review-id="${_esc(r.review_id)}"
                    data-weakness-id="${_esc(wid)}"
                    data-project-id="${_esc(projectId)}"
                    onblur="ReviewDetail.onWeaknessNote(this)">${_esc(note)}</textarea>
          <span class="rd-note-saved" id="rd-note-saved-${_esc(wid)}" aria-live="polite"></span>
        </div>
      </div>`;
    }).join('');

    return `<details class="rd-expandable">
      <summary class="rd-expandable-summary">
        <span class="rd-section-label">Weaknesses
          <span class="rd-count-badge">${weaknesses.length}</span>
        </span>
        <span class="rd-expand-hint">▶</span>
      </summary>
      <div class="rd-expandable-body">
        <div class="rd-weakness-list">${items}</div>
      </div>
    </details>`;
  }



  // ── F1: Decision points (expandable) ──────────────────────────────────────

  function _renderDecisionPoints(r) {
    const dps = r.decision_points || [];
    if (!dps.length) return '';
    const items = dps.map(dp => {
      if (!dp || typeof dp !== 'object') return '';
      const text   = dp.text || dp.description || '';
      const status = dp.status || 'open';
      const statusCls = status === 'resolved' ? 'rd-dp-status--resolved'
                      : status === 'accepted'  ? 'rd-dp-status--accepted'
                      : 'rd-dp-status--open';
      return `<div class="rd-dp-item">
        <span class="rd-dp-icon">🔷</span>
        <span class="rd-dp-text">${_esc(text)}</span>
        <span class="rd-dp-status ${_esc(statusCls)}">${_esc(status)}</span>
      </div>`;
    }).join('');
    return `<details class="rd-expandable">
      <summary class="rd-expandable-summary">
        <span class="rd-section-label">Decision Points
          <span class="rd-count-badge">${dps.length}</span>
        </span>
        <span class="rd-expand-hint">▶</span>
      </summary>
      <div class="rd-expandable-body">
        <div class="rd-dp-list">${items}</div>
      </div>
    </details>`;
  }

  // ── Compare action (secondary — explicit button only) ─────────────────────

  function _renderCompareAction(r) {
    const proj = window.AppState ? window.AppState.get('selectedProject') : null;
    if (!proj || !window.Compare) return '';
    return `<div class="rd-compare-action">
      <button class="btn btn-ghost btn-sm"
              title="Compare reviews side-by-side (secondary action)"
              onclick="Compare.open('${_esc(proj.id)}')">
        ⇄ Compare Reviews
      </button>
    </div>`;
  }

  // ── Sprint 2: Iteration lineage banner ────────────────────────────────────

  /**
   * Renders a lineage banner when this review was built from a prior review.
   * Shown only when previous_review_id is present — absent for original reviews.
   * Backward-compatible: reviews without the field render cleanly.
   *
   * TRACE: ReviewDetail._renderIterationBanner → Review.previous_review_id
   */
  function _renderIterationBanner(r) {
    const prevId = r.previous_review_id || '';
    if (!prevId) return '';

    const basePersona = r.base_review_persona || '';
    const personaChanged = (r.persona_used || r.persona || '') !== basePersona && !!basePersona;

    return `<div class="ri-lineage-banner">
      <span class="ri-lineage-icon" aria-hidden="true">🔗</span>
      <div class="ri-lineage-body">
        <span class="ri-lineage-label">Iterated from</span>
        <span class="ri-lineage-base-id">${_esc(prevId)}</span>
        ${basePersona
          ? `<span class="ri-lineage-persona">${_esc(basePersona)}</span>`
          : ''}
        ${personaChanged
          ? `<span class="ri-lineage-changed">persona changed</span>`
          : ''}
      </div>
    </div>`;
  }

  // ── Sprint 2: Create New Review from this Review ──────────────────────────

  /**
   * Renders the "Create New Review from this Review" action panel.
   * Intentional UX: requires explicit user action — no auto-trigger.
   * Persona selection is optional; defaults to this review's persona.
   *
   * TRACE: ReviewDetail._renderCreateIterationAction → API.createReviewIteration
   */
  const ITERATION_PERSONAS = [
    'Solution Architect',
    'Enterprise Architect',
    'Delivery Manager',
    'Product Owner',
    'Resource Manager',
    'DevOps Engineer',
    'Cloud Architect',
    'Platform Engineer',
    'QA / Test Lead',
    'Data Engineer',
    'Security Architect',
    'FinOps',
  ];

  function _renderCreateIterationAction(r) {
    const proj = window.AppState ? window.AppState.get('selectedProject') : null;
    if (!proj) return '';

    const rid       = r.review_id || '';
    const persona   = r.persona || r.persona_used || '';
    const uid       = `ri-form-${_esc(rid)}`;

    const personaOpts = ITERATION_PERSONAS.map(p =>
      `<option value="${_esc(p)}" ${p === persona ? 'selected' : ''}>${_esc(p)}</option>`
    ).join('');

    return `<div class="ri-create-section" id="${uid}-section">
      <div class="ri-create-header">
        <span class="ri-create-icon" aria-hidden="true">➕</span>
        <span class="ri-create-title">Create New Review from this Review</span>
        <button class="ri-create-toggle btn btn-ghost btn-sm"
                aria-expanded="false"
                onclick="ReviewDetail.onToggleIterationForm('${_esc(rid)}')"
                title="Open review iteration form">
          New Iteration
        </button>
      </div>

      <div class="ri-create-form" id="${uid}-form" style="display:none" aria-hidden="true">
        <p class="ri-create-desc">
          A new review will be created using <strong>${_esc(rid)}</strong> as context.
          The original review is preserved and unchanged.
        </p>

        <div class="ri-form-row">
          <label class="ri-form-label" for="${uid}-persona">Persona</label>
          <select id="${uid}-persona" class="ri-persona-select"
                  title="Choose same or different persona for the new review">
            ${personaOpts}
          </select>
          ${persona
            ? `<span class="ri-form-hint">Current: <em>${_esc(persona)}</em></span>`
            : ''}
        </div>

        <div class="ri-form-row">
          <label class="ri-form-label" for="${uid}-prompt">Custom Prompt <span class="ri-optional">(optional)</span></label>
          <textarea id="${uid}-prompt" class="ri-prompt-input" rows="2"
                    placeholder="Additional guidance for this iteration…"></textarea>
        </div>

        <div class="ri-form-actions">
          <button class="btn btn-primary btn-sm"
                  id="${uid}-submit"
                  data-review-id="${_esc(rid)}"
                  data-project-id="${_esc(proj.id)}"
                  data-form-uid="${_esc(uid)}"
                  onclick="ReviewDetail.onCreateIteration(this)">
            ➕ Create New Review
          </button>
          <button class="btn btn-ghost btn-sm"
                  onclick="ReviewDetail.onToggleIterationForm('${_esc(rid)}')">
            Cancel
          </button>
        </div>

        <div class="ri-result" id="${uid}-result" style="display:none" aria-live="polite"></div>
      </div>
    </div>`;
  }

  // ── Sprint 2: Event handlers ──────────────────────────────────────────────

  /**
   * Toggle the iteration form open/closed.
   * Called by the "New Iteration" button — explicit user action only.
   */
  function onToggleIterationForm(reviewId) {
    const uid   = `ri-form-${reviewId}`;
    const form  = document.getElementById(`${uid}-form`);
    const btn   = document.querySelector(`#ri-form-${reviewId}-section .ri-create-toggle`);
    if (!form) return;
    const isOpen = form.style.display !== 'none';
    form.style.display  = isOpen ? 'none' : '';
    form.setAttribute('aria-hidden', isOpen ? 'true' : 'false');
    if (btn) btn.setAttribute('aria-expanded', String(!isOpen));
    // Clear any prior result when toggling
    if (!isOpen) {
      const result = document.getElementById(`${uid}-result`);
      if (result) { result.style.display = 'none'; result.innerHTML = ''; }
    }
  }

  /**
   * Submit the review iteration form.
   * Creates a new review from the base, then renders a lineage confirmation card.
   */
  async function onCreateIteration(submitBtn) {
    const projectId = submitBtn.dataset.projectId;
    const reviewId  = submitBtn.dataset.reviewId;
    const uid       = submitBtn.dataset.formUid;

    if (!projectId || !reviewId) return;

    const personaEl  = document.getElementById(`${uid}-persona`);
    const promptEl   = document.getElementById(`${uid}-prompt`);
    const resultEl   = document.getElementById(`${uid}-result`);

    const newPersona   = personaEl  ? personaEl.value.trim()  : '';
    const customPrompt = promptEl   ? promptEl.value.trim()   : '';

    // Disable button while running
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Creating…';
    if (resultEl) { resultEl.style.display = ''; resultEl.innerHTML = _renderIterationLoading(); }

    try {
      const result = await window.API.createReviewIteration(
        projectId, reviewId, newPersona || undefined, customPrompt || undefined
      );

      if (result && result.error) {
        if (resultEl) {
          resultEl.innerHTML = `<div class="ri-result-error">⚠ ${_esc(result.error)}</div>`;
        }
      } else {
        if (resultEl) {
          resultEl.innerHTML = _renderIterationResult(result);
        }
        // Disable form controls — iteration created; user should close drawer
        if (personaEl)  personaEl.disabled  = true;
        if (promptEl)   promptEl.disabled   = true;
        submitBtn.textContent = '✓ Created';
      }
    } catch (err) {
      if (resultEl) {
        resultEl.innerHTML = `<div class="ri-result-error">⚠ Unexpected error: ${_esc(err.message || 'Unknown')}</div>`;
      }
    } finally {
      submitBtn.disabled = false;
      if (submitBtn.textContent === '⏳ Creating…') {
        submitBtn.textContent = '➕ Create New Review';
      }
    }
  }

  function _renderIterationLoading() {
    return `<div class="ri-result-loading">
      <span class="spin" aria-hidden="true">⟳</span>
      <span>Running review…</span>
    </div>`;
  }

  /**
   * Renders the confirmation card shown after a successful iteration.
   * Makes lineage clear: new ID, persona used, link to predecessor.
   */
  function _renderIterationResult(r) {
    if (!r || !r.review_id) return `<div class="ri-result-error">⚠ No review data returned.</div>`;

    const personaChanged = r.persona_changed === true;
    const iterLabel      = r.iteration_number ? `R${r.iteration_number}` : r.review_id;

    return `<div class="ri-result-card">
      <div class="ri-result-header">
        <span class="ri-result-icon" aria-hidden="true">✅</span>
        <span class="ri-result-title">New review created</span>
      </div>
      <div class="ri-result-rows">
        <div class="ri-result-row">
          <span class="ri-result-label">New Review ID</span>
          <span class="ri-result-value ri-result-value--id">
            ${_esc(iterLabel)}
            <span class="ri-result-raw-id">${_esc(r.review_id)}</span>
          </span>
        </div>
        <div class="ri-result-row">
          <span class="ri-result-label">Persona Used</span>
          <span class="ri-result-value">
            ${_esc(r.persona_used || r.persona || '–')}
            ${personaChanged
              ? `<span class="ri-persona-changed-badge">changed</span>`
              : `<span class="ri-persona-same-badge">same</span>`}
          </span>
        </div>
        <div class="ri-result-row">
          <span class="ri-result-label">Builds on</span>
          <span class="ri-result-value">
            <span class="ri-lineage-base-id">${_esc(r.previous_review_id || '–')}</span>
            ${r.base_review_persona
              ? `<span class="ri-result-base-persona">${_esc(r.base_review_persona)}</span>`
              : ''}
          </span>
        </div>
        <div class="ri-result-row">
          <span class="ri-result-label">Created</span>
          <span class="ri-result-value">${_esc(_fmtDate(r.created_at))}</span>
        </div>
        ${r.summary ? `
        <div class="ri-result-row ri-result-row--summary">
          <span class="ri-result-label">Summary</span>
          <span class="ri-result-value ri-result-summary">${_esc(r.summary.slice(0, 200))}</span>
        </div>` : ''}
      </div>
      <p class="ri-result-note">
        Refresh the review list to see the new iteration. The original review is unchanged.
      </p>
    </div>`;
  }

  // ── Public: render a full review into the drawer ──────────────────────────

  /**
   * TRACE: dashboard.js._renderDrawerContent → ReviewDetail.renderReview(r)
   * Consumes the full Review object (after async fetch).
   * Safe for partial data (summary-only) on first render.
   *
   * Sprint 2 additions:
   *   - _renderIterationBanner(r)      — lineage banner (shown when previous_review_id present)
   *   - _renderCreateIterationAction(r) — "Create New Review" form (explicit user action)
   *
   * @param {object} r  Review object (full or summary)
   * @returns {string}  HTML
   */
  function renderReview(r) {
    if (!r) return '<div class="rd-empty">No review data available.</div>';
    return [
      _renderIterationBanner(r),        // Sprint 2: lineage banner (no-op when no previous_review_id)
      _renderHeader(r),
      _renderSummary(r),
      _renderTopRisks(r),
      _renderPrompt(r),
      _renderArtifactRefs(r),
      _renderFindings(r),
      _renderWeaknesses(r),
      _renderDecisionPoints(r),
      _renderQuestions(r),
      _renderCreateIterationAction(r),   // Sprint 2: iteration form (explicit, not automatic)
      _renderCompareAction(r),
    ].filter(Boolean).join('\n');
  }



  // ── F3: Event handlers — weakness status ──────────────────────────────────

  /**
   * Called when the user changes the status dropdown for a weakness.
   * Fires POST to /api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/status
   * Falls back gracefully if backend unavailable (mock mode).
   */
  async function onWeaknessStatus(selectEl) {
    const pid = selectEl.dataset.projectId;
    const rid = selectEl.dataset.reviewId;
    const wid = selectEl.dataset.weaknessId;
    const status = selectEl.value;
    if (!pid || !rid || !wid) return;

    // Optimistic UI: update select class immediately
    selectEl.className = selectEl.className.replace(/rd-weakness-status--\S+/g, '').trim();
    const cls = status === 'open'     ? 'rd-weakness-status--open'
              : status === 'resolved'  ? 'rd-weakness-status--resolved'
              : status === 'mitigated' ? 'rd-weakness-status--mitigated'
              : 'rd-weakness-status--other';
    selectEl.classList.add(cls);

    // Persist
    if (window.API && typeof window.API.updateWeaknessStatus === 'function') {
      try {
        await window.API.updateWeaknessStatus(pid, rid, wid, status);
      } catch (_) {
        // Non-blocking: drawer already shows updated value
      }
    }
  }

  // ── F3: Event handlers — weakness note ────────────────────────────────────

  /**
   * Called on textarea blur. Persists the note text.
   * Shows a transient "Saved" confirmation next to the field.
   */
  async function onWeaknessNote(textareaEl) {
    const pid  = textareaEl.dataset.projectId;
    const rid  = textareaEl.dataset.reviewId;
    const wid  = textareaEl.dataset.weaknessId;
    const note = textareaEl.value;
    if (!pid || !rid || !wid) return;

    if (window.API && typeof window.API.updateWeaknessNote === 'function') {
      try {
        await window.API.updateWeaknessNote(pid, rid, wid, note);
        const saved = document.getElementById(`rd-note-saved-${wid}`);
        if (saved) {
          saved.textContent = '✓ Saved';
          setTimeout(() => { saved.textContent = ''; }, 2000);
        }
      } catch (_) {
        // Non-blocking
      }
    }
  }

  // ── Expose globally ────────────────────────────────────────────────────────

  return {
    renderReview,
    onWeaknessStatus,
    onWeaknessNote,
    onToggleIterationForm,  // Sprint 2
    onCreateIteration,      // Sprint 2
  };

})();

window.ReviewDetail = ReviewDetail;

// Alias as DetailPanel so dashboard.js (which calls DetailPanel.renderReview)
// picks it up automatically without requiring a dashboard.js edit.
if (!window.DetailPanel) {
  window.DetailPanel = ReviewDetail;
}

