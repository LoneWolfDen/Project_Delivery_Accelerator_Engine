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

  // ── Public: render a full review into the drawer ──────────────────────────

  /**
   * TRACE: dashboard.js._renderDrawerContent → ReviewDetail.renderReview(r)
   * Consumes the full Review object (after async fetch).
   * Safe for partial data (summary-only) on first render.
   *
   * @param {object} r  Review object (full or summary)
   * @returns {string}  HTML
   */
  function renderReview(r) {
    if (!r) return '<div class="rd-empty">No review data available.</div>';
    return [
      _renderHeader(r),
      _renderSummary(r),
      _renderTopRisks(r),
      _renderPrompt(r),
      _renderArtifactRefs(r),
      _renderFindings(r),
      _renderWeaknesses(r),
      _renderDecisionPoints(r),
      _renderQuestions(r),
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
  };

})();

window.ReviewDetail = ReviewDetail;

// Alias as DetailPanel so dashboard.js (which calls DetailPanel.renderReview)
// picks it up automatically without requiring a dashboard.js edit.
if (!window.DetailPanel) {
  window.DetailPanel = ReviewDetail;
}

