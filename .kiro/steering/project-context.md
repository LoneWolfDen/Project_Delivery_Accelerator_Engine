# Contexta – Project Delivery Accelerator Engine

Context-aware **decision and learning system**: documents → intelligence → gated proposals → client feedback → decisions.

## Constraints

Single-container Docker, offline-first, non-technical users, open-source only.
Python 3.9+ (pyyaml only dep). Vanilla JS SPA (no build/framework).

## Decision Chain

```
Intelligence Version (Vn)
  └── Review (Rn)  ← gate: completeness_score ≥70% + sign-off
       └── Proposal Version (PVn)  ← gate: version_id + review_id required
            └── Feedback Items (structured: accepted/rejected/change_requested/concerns)
                 └── Inject (new-only, version-scoped) → next Review
                      └── Stop condition → Finalise (atomic, soft-lock, phase→design)
```

## Layout

| Path | Role |
|------|------|
| `server.py` | HTTP API + static serving |
| `project_manager.py` | Project CRUD + orchestration |
| `static/index.html` | SPA UI (dark, vanilla JS) — tabs: dashboard, ingest, intelligence, versions, reviews, diagrams, phases, **presales**, admin |
| `static/feedback.html` | External client feedback form (token-gated) |
| `processors/review_quality.py` | Completeness scoring, quality gate, `complete_review`, `set_active_review_with_gate` |
| `processors/proposal_generator.py` | Proposal document generation (files_only template + AI); all document sections |
| `processors/proposals.py` | Proposal CRUD; DS-07 gates on `create_proposal` + `add_proposal_version` |
| `processors/feedback_classifier.py` | `split_into_paragraphs`, heuristic + AI classify, hybrid tagger entry point |
| `processors/presales_feedback.py` | Summary, structured injection (new-only), cache scoping, feedback delta |
| `processors/presales_finaliser.py` | `check_stop_condition`, `finalise_presales` (atomic) |
| `personas/` | Review orchestration (files_only/ollama/bedrock); prepends feedback injection |
| `models/proposal.py` | FeedbackItem, ProposalVersion (+traceability/lock), PresalesFeedback, ProposalDocument |
| `models/hierarchy.py` | Version, Review (+completeness_score/quality_status/decided_by), HierarchyStore |
| `db/` | SQLite layer: database, hierarchy_store_sql, artifact_store_sql, project_store_sql, decision_log |
| `scripts/seed_sqlite.py` | Fresh SQLite test data |
| `scripts/migrate_decision_system.py` | Idempotent DS-01 schema migration |

## Storage (Dual-Write)

Two stores in parallel (Admin → Storage Mode):

| Flag | Default | Effect |
|------|---------|--------|
| `sqlite_write_enabled` | `True` | Write to `projects_data/accelerator.db` |
| `file_write_enabled` | `True` | Mirror to JSON files |

SQLite tables: `projects`, `phases`, `versions`, `reviews`, `artifacts`, `proposals`, `proposal_versions`, `jobs`, `presales_feedback`, `feedback_tokens`, **`proposal_documents`**, **`decision_log`**.

## Key API Routes

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/projects/{id}/hierarchy/reviews/{rid}/quality` | Review gate check |
| POST | `/api/projects/{id}/hierarchy/reviews/{rid}/complete` | Mark review complete/interim |
| POST | `/api/projects/{id}/hierarchy/versions/{vid}/set-active-review-gated` | Gated active-review set |
| GET | `/api/projects/{id}/decision-log` | Immutable audit trail |
| POST | `/api/projects/{id}/proposal/generate` | Generate proposal document |
| GET | `/api/projects/{id}/proposal/document` | Retrieve generated document |
| POST | `/api/projects/{id}/presales/feedback/classify` | Hybrid tagger pre-classify |
| GET | `/api/projects/{id}/presales/summary` | Pre-sales tab data |
| GET | `/api/projects/{id}/presales/stop-condition` | Finalisation readiness |
| POST | `/api/projects/{id}/presales/finalise` | Atomic finalise (requires `decided_by`) |
| POST | `/api/projects/{id}/presales/share` | One-time client share token |
| POST | `/api/feedback/submit` | External client submission |

## Decision System Rules

1. **Review gate**: `quality_status` must be `complete` or `interim` before setting as active review. `decided_by` recorded.
2. **Proposal gate**: `hierarchy_version_id` + `active_review_id` required on every proposal version. Raises 422 if missing.
3. **Feedback items**: structured `FeedbackItem` (category, mapped_to, confidence, is_critical, status). `change_requested + scope_change/risk` → auto-flag critical.
4. **Injection**: only `status=new` items injected into next review. Cache cleared per version on new proposal version.
5. **Stop condition**: all critical items addressed + proposal `accepted` + review not `pending`.
6. **Finalise** (atomic): accept → soft-lock → freeze feedback (new→deferred) → complete review → phase→design → decision_log.
7. **Soft lock**: 409 on write to locked version unless `override_reason` provided; logged to decision_log.

## Patterns

- Paths resolve via `Path(__file__).parent`
- Intelligence = versioned snapshots (re-runnable, comparable)
- Hierarchy: Phase → Version → Review (Phase default: `pre-sales`)
- Files-only mode = deterministic, zero-cost (graceful fallback for all AI paths)
- Dataclasses + type hints + docstrings on public API

## Ignore

`_archive/` (legacy), `projects_data/` (runtime, gitignored)
