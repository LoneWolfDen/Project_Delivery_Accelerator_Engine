/**
 * api.js — V2 API Layer
 *
 * TRACE: UI → Logic → API
 * Component: API (module)
 * Calls: /api/projects, /hierarchy/metrics, /hierarchy/versions,
 *        /hierarchy/reviews, /hierarchy (full tree)
 * Pattern: fetch-based, returns parsed JSON.
 *          Falls back to MOCK_DATA when server returns error or is unreachable
 *          (Step 1 development mode — replace with live-only in Step 2).
 *
 * Mock → Live switch:
 *   Set  window.V2_USE_MOCK = false  to disable mock fallback globally.
 *   Default: true (safe for offline/dev use).
 */

'use strict';

// ── Mock data (Step 1 — development without backend) ──────────
// TRACE: Mock → State → UI
// Mirrors the real API shapes exactly so components need no changes at switch.
const MOCK_DATA = {
  projects: [
    {
      id: 'proj_demo_01',
      name: 'Cloud Migration Assessment',
      phase: 'pre-sales',
      file_count: 12,
      status: 'active',
    },
    {
      id: 'proj_demo_02',
      name: 'Platform Modernisation',
      phase: 'design',
      file_count: 7,
      status: 'active',
    },
  ],

  hierarchy: {
    project_id: 'proj_demo_01',
    current_phase: 'pre-sales',
    total_versions: 3,
    total_reviews: 7,
    tree: [
      {
        id: 'pre-sales',
        label: 'Pre-sales',
        order: 1,
        is_current: true,
        version_count: 3,
        review_count: 7,
        versions: [
          {
            version_id: 'v3',
            label: 'Post-discovery revision',
            phase_id: 'pre-sales',
            created_at: '2026-05-28T10:00:00Z',
            review_count: 3,
            artifact_count: 8,
            persona: 'solution_architect',
            active_review_id: 'r7',
            reviews: [
              { review_id: 'r7', version_id: 'v3', persona: 'solution_architect', created_at: '2026-05-28T12:00:00Z', total_findings: 14, issues_resolved: 4, issues_carry_forward: 10, quality_status: 'complete',   iteration_number: 3, summary: 'Comprehensive architecture review covering all risk areas.' },
              { review_id: 'r6', version_id: 'v3', persona: 'delivery_manager',   created_at: '2026-05-27T09:00:00Z', total_findings: 9,  issues_resolved: 3, issues_carry_forward:  6, quality_status: 'interim',    iteration_number: 2, summary: 'Delivery timeline risks identified, dependencies mapped.' },
              { review_id: 'r5', version_id: 'v3', persona: 'product_owner',      created_at: '2026-05-26T14:00:00Z', total_findings: 6,  issues_resolved: 0, issues_carry_forward:  6, quality_status: 'pending',    iteration_number: 1, summary: 'Initial scope assessment for the new version.' },
            ],
          },
          {
            version_id: 'v2',
            label: 'Scope refinement',
            phase_id: 'pre-sales',
            created_at: '2026-05-20T08:00:00Z',
            review_count: 2,
            artifact_count: 5,
            persona: 'delivery_manager',
            active_review_id: 'r4',
            reviews: [
              { review_id: 'r4', version_id: 'v2', persona: 'delivery_manager', created_at: '2026-05-21T11:00:00Z', total_findings: 11, issues_resolved: 5, issues_carry_forward: 6, quality_status: 'complete', iteration_number: 2, summary: 'Refined delivery approach after client feedback.' },
              { review_id: 'r3', version_id: 'v2', persona: 'product_owner',    created_at: '2026-05-20T15:00:00Z', total_findings: 5,  issues_resolved: 0, issues_carry_forward: 5, quality_status: 'interim',  iteration_number: 1, summary: 'Product scope boundaries established.' },
            ],
          },
          {
            version_id: 'v1',
            label: 'Initial assessment',
            phase_id: 'pre-sales',
            created_at: '2026-05-10T09:00:00Z',
            review_count: 2,
            artifact_count: 3,
            persona: 'solution_architect',
            active_review_id: 'r2',
            reviews: [
              { review_id: 'r2', version_id: 'v1', persona: 'solution_architect', created_at: '2026-05-11T10:00:00Z', total_findings: 8, issues_resolved: 3, issues_carry_forward: 5, quality_status: 'complete', iteration_number: 2, summary: 'Architecture baseline established. Key risks documented.' },
              { review_id: 'r1', version_id: 'v1', persona: 'delivery_manager',   created_at: '2026-05-10T14:00:00Z', total_findings: 4, issues_resolved: 0, issues_carry_forward: 4, quality_status: 'pending',  iteration_number: 1, summary: 'First-pass delivery assessment.' },
            ],
          },
        ],
      },
    ],
  },

  metrics: {
    total_versions: 3,
    total_reviews: 7,
    version_reviews: 3,
    current_phase: 'pre-sales',
    artifact_count: 8,
    risks_identified: 12,
    gaps_identified: 4,
    constraints: 6,
    dependencies: 9,
    assumptions: 11,
    action_items: 5,
    total_findings: 14,
    data_source: {
      version: 'v3',
      version_label: 'Post-discovery revision',
      review: 'r7',
      review_persona: 'solution_architect',
      phase: 'pre-sales',
    },
    selected_version: {
      version_id: 'v3',
      label: 'Post-discovery revision',
      created_at: '2026-05-28T10:00:00Z',
      review_count: 3,
      artifact_count: 8,
    },
    selected_review: {
      review_id: 'r7',
      persona: 'solution_architect',
      created_at: '2026-05-28T12:00:00Z',
      total_findings: 14,
      summary: 'Comprehensive architecture review covering all risk areas.',
      quality_status: 'complete',
    },
    trend: [
      { version_id: 'v1', stats: { risks: 8  }, created_at: '2026-05-10T09:00:00Z' },
      { version_id: 'v2', stats: { risks: 11 }, created_at: '2026-05-20T08:00:00Z' },
      { version_id: 'v3', stats: { risks: 12 }, created_at: '2026-05-28T10:00:00Z' },
    ],
    available_reviews: [
      { review_id: 'r7', persona: 'solution_architect', created_at: '2026-05-28T12:00:00Z', quality_status: 'complete' },
      { review_id: 'r6', persona: 'delivery_manager',   created_at: '2026-05-27T09:00:00Z', quality_status: 'interim'  },
      { review_id: 'r5', persona: 'product_owner',      created_at: '2026-05-26T14:00:00Z', quality_status: 'pending'  },
    ],
  },

  // Single review detail (used by drawer)
  reviewDetail: {
    review_id: 'r7',
    version_id: 'v3',
    phase_id: 'pre-sales',
    persona: 'solution_architect',
    ai_backend: 'files_only',
    created_at: '2026-05-28T12:00:00Z',
    quality_status: 'complete',
    completeness_score: 84,
    iteration_number: 3,
    previous_review_id: 'r6',
    prompt_used: 'Review this solution architecture from the perspective of a senior solution architect. Focus on technical risks, assumptions, and dependencies. Highlight the top 3 risks clearly.',
    summary: 'Comprehensive architecture review covering all risk areas. Key decisions around cloud strategy and data migration remain open.',
    findings: {
      risks: [
        'No DR strategy defined for the legacy data tier',
        'Single-vendor dependency on primary cloud provider',
        'Security posture unclear for API gateway layer',
        'Data migration timeline underestimated by ~30%',
      ],
      constraints: [
        'Q4 freeze window limits deployment options',
        'Existing contracts with on-prem vendors extend to 2027',
      ],
      dependencies: [
        'Identity provider integration required before Phase 2',
        'Data team availability for migration scripts',
      ],
      assumptions: [
        'Client has full access to source environment',
        'AWS Landing Zone is pre-provisioned',
      ],
      action_items: [
        'Define DR RPO/RTO targets with client',
        'Confirm identity provider vendor selection',
      ],
    },
    questions: [
      'What is the expected data volume for migration?',
      'Is there an existing monitoring solution to integrate with?',
    ],
    weaknesses: [
      { id: 'w1', text: 'DR strategy not defined for legacy data tier', category: 'resilience',   status: 'open',      user_note: '' },
      { id: 'w2', text: 'API gateway security posture is unclear',       category: 'security',    status: 'addressed', user_note: 'Flagged for follow-up with client security team in Week 2.' },
      { id: 'w3', text: 'Migration timeline may be underestimated',      category: 'delivery',    status: 'validated', user_note: 'Added 2-week buffer in revised plan.' },
    ],
    artifact_refs: [
      { artifact_id: 'a1', artifact_name: 'Solution_Architecture_v3.docx', artifact_type: 'document',   section_reference: 'Technical Assumptions', page_reference: '7' },
      { artifact_id: 'a2', artifact_name: 'Client_Presentation_Dec.pptx',  artifact_type: 'slides',     slide_number: 12, slide_title: 'Migration Approach' },
      { artifact_id: 'a3', artifact_name: 'Scope clarification',           artifact_type: 'email',      subject: 'RE: Scope Clarification v2', date: '2026-05-15', sender: 'client@example.com' },
      { artifact_id: 'a4', artifact_name: 'Discovery Workshop Notes',      artifact_type: 'meeting_notes', meeting_name: 'Discovery Workshop', date: '2026-05-12', section_reference: 'Cloud Strategy' },
    ],
    decision_points: [
      { id: 'd1', text: 'Cloud provider selection (AWS vs Azure)', status: 'open',     category: 'architecture' },
      { id: 'd2', text: 'Identity provider vendor selection',      status: 'accepted', category: 'security' },
    ],
  },
};

// ── HTTP helper ───────────────────────────────────────────────
/**
 * Low-level fetch wrapper.
 * @param {string} method
 * @param {string} path
 * @param {object} [body]
 * @returns {Promise<object>}
 */
async function _request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(path, opts);
    const data = await res.json();
    if (!res.ok) return { error: data.message || data.error || `HTTP ${res.status}` };
    return data;
  } catch (err) {
    return { error: err.message || 'Network error' };
  }
}

// ── Mock flag ─────────────────────────────────────────────────
// Set window.V2_USE_MOCK = false to route all calls to real backend.
function _useMock() {
  return window.V2_USE_MOCK !== false;
}

// ── API public interface ──────────────────────────────────────

/**
 * Fetch all active projects.
 * TRACE: API → /api/projects → Data: Project[]
 * @returns {Promise<{projects: Array}>}
 */
async function fetchProjects() {
  if (_useMock()) return { projects: MOCK_DATA.projects };
  return _request('GET', '/api/projects');
}

/**
 * Fetch full Phase→Version→Review hierarchy for a project.
 * TRACE: API → /api/projects/{pid}/hierarchy → Data: HierarchyPayload
 * @param {string} projectId
 * @returns {Promise<object>}
 */
async function fetchHierarchy(projectId) {
  if (_useMock()) return MOCK_DATA.hierarchy;
  return _request('GET', `/api/projects/${projectId}/hierarchy`);
}

/**
 * Fetch dashboard metrics, optionally scoped to a version and/or review.
 * TRACE: API → /hierarchy/metrics → Data: MetricsPayload
 * @param {string} projectId
 * @param {string} [versionId]
 * @param {string} [reviewId]
 * @returns {Promise<object>}
 */
async function fetchMetrics(projectId, versionId, reviewId) {
  if (_useMock()) return MOCK_DATA.metrics;
  let url = `/api/projects/${projectId}/hierarchy/metrics`;
  const params = [];
  if (versionId) params.push(`version_id=${encodeURIComponent(versionId)}`);
  if (reviewId)  params.push(`review_id=${encodeURIComponent(reviewId)}`);
  if (params.length) url += '?' + params.join('&');
  return _request('GET', url);
}

/**
 * Fetch all versions for a project, optionally filtered by phase.
 * TRACE: API → /hierarchy/versions → Data: Version[]
 * @param {string} projectId
 * @param {string} [phaseId]
 * @returns {Promise<{versions: Array}>}
 */
async function fetchVersions(projectId, phaseId) {
  if (_useMock()) {
    const versions = [];
    (MOCK_DATA.hierarchy.tree || []).forEach(phase => {
      (phase.versions || []).forEach(v => versions.push(v));
    });
    return { versions };
  }
  let url = `/api/projects/${projectId}/hierarchy/versions`;
  if (phaseId) url += `?phase_id=${encodeURIComponent(phaseId)}`;
  return _request('GET', url);
}

/**
 * Fetch all reviews for a project, optionally scoped to a version.
 * TRACE: API → /hierarchy/reviews → Data: Review[]
 * @param {string} projectId
 * @param {string} [versionId]
 * @returns {Promise<{reviews: Array}>}
 */
async function fetchReviews(projectId, versionId) {
  if (_useMock()) {
    const versions = [];
    (MOCK_DATA.hierarchy.tree || []).forEach(phase => {
      (phase.versions || []).forEach(v => versions.push(v));
    });
    const target = versions.find(v => v.version_id === versionId);
    return { reviews: target ? (target.reviews || []) : [] };
  }
  let url = `/api/projects/${projectId}/hierarchy/reviews`;
  if (versionId) url += `?version_id=${encodeURIComponent(versionId)}`;
  return _request('GET', url);
}

/**
 * Fetch full detail for a single review (for drawer display).
 * TRACE: API → /hierarchy/reviews/{rid} → Data: Review (full)
 * @param {string} projectId
 * @param {string} reviewId
 * @returns {Promise<object>}
 */
async function fetchReviewDetail(projectId, reviewId) {
  if (_useMock()) return MOCK_DATA.reviewDetail;
  return _request('GET', `/api/projects/${projectId}/hierarchy/reviews/${reviewId}`);
}

/**
 * Fetch full detail for a single version (for drawer display).
 * TRACE: API → /hierarchy/versions/{vid} → Data: Version (full)
 * @param {string} projectId
 * @param {string} versionId
 * @returns {Promise<object>}
 */
async function fetchVersionDetail(projectId, versionId) {
  if (_useMock()) {
    const versions = [];
    (MOCK_DATA.hierarchy.tree || []).forEach(phase => {
      (phase.versions || []).forEach(v => versions.push(v));
    });
    return versions.find(v => v.version_id === versionId) || { error: 'Not found' };
  }
  return _request('GET', `/api/projects/${projectId}/hierarchy/versions/${versionId}`);
}

/**
 * Derive recent activity events from the hierarchy tree.
 *
 * TRACE: API → /api/projects/{pid}/hierarchy → Data: ActivityEvent[]
 *
 * Events are derived client-side from the hierarchy payload — no separate
 * endpoint required. Each event has the shape:
 *   { type, id, label, timestamp, phase_id, version_id? }
 *
 * Types:
 *   'version_created'  — a Version was created
 *   'review_created'   — a Review was run
 *   'review_completed' — a Review reached quality_status 'complete'
 *
 * Returns the latest MAX_EVENTS events sorted newest-first.
 *
 * @param {string} projectId
 * @returns {Promise<{events: Array}>}
 */
const _ACTIVITY_MAX = 5;

async function fetchActivity(projectId) {
  const hierarchy = await fetchHierarchy(projectId);
  return { events: _deriveActivityEvents(hierarchy) };
}

/**
 * Pure function: derive activity events from a HierarchyPayload.
 * Exported so dashboard.js can call it synchronously when hierarchy is
 * already in state (avoids a second fetch).
 *
 * @param {object} hierarchy
 * @returns {Array<{type, id, label, timestamp, phase_id, version_id?}>}
 */
function _deriveActivityEvents(hierarchy) {
  const events = [];
  for (const phase of ((hierarchy && hierarchy.tree) || [])) {
    const phaseId = phase.id || '';
    for (const ver of (phase.versions || [])) {
      if (ver.created_at) {
        events.push({
          type:      'version_created',
          id:        ver.version_id,
          label:     ver.label ? `${ver.version_id} – ${ver.label}` : ver.version_id,
          timestamp: ver.created_at,
          phase_id:  phaseId,
        });
      }
      for (const rev of (ver.reviews || [])) {
        if (rev.created_at) {
          events.push({
            type:       rev.quality_status === 'complete' ? 'review_completed' : 'review_created',
            id:         rev.review_id,
            label:      `${rev.review_id}${rev.persona ? ' · ' + rev.persona : ''}`,
            timestamp:  rev.created_at,
            phase_id:   phaseId,
            version_id: ver.version_id,
          });
        }
      }
    }
  }
  // Sort newest first, cap at max
  events.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));
  return events.slice(0, _ACTIVITY_MAX);
}

// ── Review Iteration (Sprint 2) ──────────────────────────────

/**
 * Create a new review from an existing review (review iteration).
 *
 * TRACE: API → POST /hierarchy/reviews/{rid}/iterate → Data: Review (new, with lineage)
 *
 * Body:
 *   new_persona   — optional; defaults to base review persona
 *   custom_prompt — optional prompt suffix
 *
 * Returns the new review summary including:
 *   review_id, version_id, persona_used, previous_review_id,
 *   base_review_persona, persona_changed, iteration_number, created_at
 *
 * @param {string} projectId
 * @param {string} baseReviewId   — the review being iterated from (user-selected)
 * @param {string} [newPersona]   — optional new persona
 * @param {string} [customPrompt] — optional custom prompt
 * @returns {Promise<object>}
 */
async function createReviewIteration(projectId, baseReviewId, newPersona, customPrompt) {
  if (_useMock()) {
    // Simulate a newly created iteration review
    const base = MOCK_DATA.reviewDetail;
    const newRid = `r${Date.now()}`;
    return {
      review_id:           newRid,
      version_id:          base.version_id,
      persona_used:        newPersona || base.persona,
      previous_review_id:  baseReviewId,
      base_review_persona: base.persona,
      persona_changed:     !!(newPersona && newPersona !== base.persona),
      iteration_number:    (base.iteration_number || 1) + 1,
      created_at:          new Date().toISOString(),
      quality_status:      'pending',
      summary:             `Iteration from ${baseReviewId}. Refined analysis with updated context.`,
    };
  }
  const body = {};
  if (newPersona)   body.new_persona   = newPersona;
  if (customPrompt) body.custom_prompt = customPrompt;
  return _request(
    'POST',
    `/api/projects/${projectId}/hierarchy/reviews/${baseReviewId}/iterate`,
    body,
  );
}

// ── Weakness note + status (Sprint 1) ────────────────────────

/**
 * Persist a weakness status update.
 * TRACE: API → POST /hierarchy/reviews/{rid}/weakness/{wid}/status
 * @param {string} projectId
 * @param {string} reviewId
 * @param {string} weaknessId
 * @param {string} status
 * @returns {Promise<object>}
 */
async function updateWeaknessStatus(projectId, reviewId, weaknessId, status) {
  if (_useMock()) return { review_id: reviewId, weakness_id: weaknessId, status, updated: true };
  return _request(
    'POST',
    `/api/projects/${projectId}/hierarchy/reviews/${reviewId}/weakness/${weaknessId}/status`,
    { status },
  );
}

/**
 * Persist a weakness user note.
 * TRACE: API → POST /hierarchy/reviews/{rid}/weakness/{wid}/note
 * @param {string} projectId
 * @param {string} reviewId
 * @param {string} weaknessId
 * @param {string} note
 * @returns {Promise<object>}
 */
async function updateWeaknessNote(projectId, reviewId, weaknessId, note) {
  if (_useMock()) return { review_id: reviewId, weakness_id: weaknessId, user_note: note, updated: true };
  return _request(
    'POST',
    `/api/projects/${projectId}/hierarchy/reviews/${reviewId}/weakness/${weaknessId}/note`,
    { note },
  );
}

// ── Expose globally ───────────────────────────────────────────
window.API = {
  fetchProjects,
  fetchHierarchy,
  fetchMetrics,
  fetchVersions,
  fetchReviews,
  fetchReviewDetail,
  fetchVersionDetail,
  fetchActivity,
  _deriveActivityEvents,
  updateWeaknessStatus,
  updateWeaknessNote,
  createReviewIteration,
};
