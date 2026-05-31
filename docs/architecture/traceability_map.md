# Traceability Map

## Purpose
End-to-end linkage from every UI component and user action through to the
API endpoint, service function, data model entity, and the architecture
diagram that documents it. Provides a single reference for onboarding,
impact analysis, and regression testing.

---

## Master Traceability Table

| UI Component / Action | JS Function | API Endpoint | Handler Function | Service Function | Data Entity | Diagram |
|---|---|---|---|---|---|---|
| Project `<select>` dropdown | `selectProject(projectId)` | `GET /api/projects` | — | `svc_project.list_projects()` | `projects` table | [System Overview](system_overview.md) |
| Dashboard stat grid | `viewDashboard()` | `GET /api/projects/{pid}/hierarchy/metrics` | — (direct svc) | `svc_hierarchy.get_hierarchy_metrics()` | `versions`, `reviews`, `phases` | [Application Flow](application_flow.md) |
| Phase progress bar | `viewDashboard()` | `GET /api/projects/{pid}/hierarchy/metrics` | — | `svc_hierarchy.get_hierarchy_metrics()` | `phases.is_current` | [Application Flow](application_flow.md) |
| Create project button | `createProject(name)` | `POST /api/projects` | `h_project.handle_create_project()` | `svc_project.create_project()` | `projects` INSERT | [System Overview](system_overview.md) |
| Upload file (Ingest tab) | `uploadArtifact(pid, file)` | `POST /api/v1/projects/{pid}/artifacts/upload` | `h_artifact.handle_artifact_upload()` | `db/artifact_store_sql.create_artifact()` | `artifacts` INSERT | [Sequence Flow 2](sequence_flows.md#sequence-2----artifact-ingest--processing) |
| Paste text (Ingest tab) | `pasteArtifactText(pid, body)` | `POST /api/v1/projects/{pid}/artifacts/text` | `h_artifact.handle_artifact_text()` | `db/artifact_store_sql.create_artifact()` | `artifacts` INSERT | [Sequence Flow 2](sequence_flows.md#sequence-2----artifact-ingest--processing) |
| Toggle artifact include/exclude | `toggleArtifact(pid, aid, active)` | `POST /api/v1/projects/{pid}/artifacts/{aid}/toggle` | `h_artifact.handle_artifact_toggle()` | `db/artifact_store_sql.set_include()` | `artifacts.include` UPDATE | [System Overview](system_overview.md) |
| Process All button | `processAllArtifacts(pid)` | `POST /api/v1/projects/{pid}/artifacts/process` | `h_artifact.handle_process_all_artifacts()` | `processors/pipeline.process_all_artifacts()` | `artifacts.status` → `processed` | [Sequence Flow 2](sequence_flows.md#sequence-2----artifact-ingest--processing) |
| Build Intelligence button | `buildIntelligence(pid)` | `POST /api/projects/{pid}/build-context` | `h_intel.handle_build_context()` | `svc_intel.build_project_intelligence()` | `versions` INSERT | [Sequence Flow 3](sequence_flows.md#sequence-3----build-intelligence--create-version) · [Logic Flow 2](logic_flow.md#flow-2----build-intelligence-version-build-intelligence-button-on-ingest-tab) |
| Versions tab accordion | `viewVersions()` | `GET /api/projects/{pid}/hierarchy/versions` | — | `svc_hierarchy.get_hierarchy_versions()` | `versions` SELECT | [Application Flow](application_flow.md) |
| Version row expand | `expandVersion(pid, vid)` | `GET /api/projects/{pid}/hierarchy/versions/{vid}` | — | `svc_hierarchy.get_hierarchy_version_detail()` | `versions` + `reviews[]` | [Application Flow](application_flow.md) |
| Decision Readiness badge | `_populateReadinessBadges(pid)` | `GET /api/projects/{pid}/hierarchy/versions/{vid}/readiness` | — | `svc_review.get_version_readiness()` | `reviews.decision_points`, `reviews.weaknesses` | [Logic Flow 4](logic_flow.md#flow-4----refresh-data) |
| Set Active Review button | `setActiveReview(pid, vid, rid)` | `POST /api/projects/{pid}/hierarchy/versions/{vid}/set-active-review-gated` | `h_review.handle_set_active_review_gated()` | `svc_review.set_active_review_gated()` | `versions.active_review_id` UPDATE | [Sequence Flow 5](sequence_flows.md#sequence-5----review-quality-gate--set-active-review) |
| Reviews tab list | `viewReviews()` | `GET /api/projects/{pid}/hierarchy/reviews?version_id=` | — | `svc_hierarchy.get_hierarchy_reviews()` | `reviews` SELECT | [Application Flow](application_flow.md) |
| Review row click (detail panel) | `showReviewDetail(pid, rid)` | `GET /api/projects/{pid}/hierarchy/reviews/{rid}` | — | `svc_hierarchy.get_hierarchy_review_detail()` | `reviews` full row | [Application Flow](application_flow.md) |
| Weakness status toggle | `updateWeaknessStatus(pid, rid, wid, status)` | `POST /api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/status` | `h_review.handle_weakness_status()` | `svc_review.update_weakness_status()` | `reviews.weaknesses[].status` UPDATE | [Logic Flow 3](logic_flow.md#flow-3----run-review-post-apireview) |
| Decision point status toggle | `updateDecisionStatus(pid, rid, did, status)` | `POST /api/projects/{pid}/hierarchy/reviews/{rid}/decision/{did}/status` | `h_review.handle_decision_status()` | `svc_review.update_decision_status()` | `reviews.decision_points[].status` UPDATE | [Logic Flow 3](logic_flow.md#flow-3----run-review-post-apireview) |
| View Diff button | `viewReviewDiff(pid, rid)` | `GET /api/projects/{pid}/hierarchy/reviews/{rid}/diff` | — | `svc_review.get_review_diff()` | `reviews.previous_review_id` chain | [Application Flow](application_flow.md) |
| Run Review button | `runReview(pid, roles, backend, opts)` | `POST /api/review` | `h_review.handle_review()` | `svc_review.run_persona_review()` | `reviews` INSERT + `versions` UPDATE | [Sequence Flow 4](sequence_flows.md#sequence-4----run-persona-review) · [Logic Flow 3](logic_flow.md#flow-3----run-review-post-apireview) |
| Complete Review button | `completeReview(pid, rid, completedBy)` | `POST /api/projects/{pid}/hierarchy/reviews/{rid}/complete` | `h_review.handle_complete_review()` | `svc_review.complete_review_gate()` | `reviews.quality_status` = `complete` | [Sequence Flow 5](sequence_flows.md#sequence-5----review-quality-gate--set-active-review) |
| Delete Review button | `deleteReview(pid, rid)` | `POST /api/projects/{pid}/hierarchy/reviews/{rid}/delete` | `h_review.handle_delete_review()` | `svc_hierarchy.delete_hierarchy_review()` | `reviews` DELETE + `versions.review_ids` UPDATE | [Data Model](data_model.md) |
| Inject questions chip list | `_renderInjectedQuestions()` | _(client-side only)_ | — | — | `state` → `prompt_builder_state.injected_questions[]` | [Application Flow](application_flow.md) |
| Compare Versions button | `compareVersions(pid, va, vb)` | `POST /api/projects/{pid}/compare-versions` | `h_hierarchy.handle_compare_versions()` | `svc_hierarchy.compare_project_versions()` | `versions` × 2 | [System Overview](system_overview.md) |
| Diagrams tab — Generate | `generateDiagram(pid, dtype)` | `POST /api/projects/{pid}/diagrams/{dtype}/generate` | `h_diagram.handle_generate_diagram()` | `svc_diagram.generate_diagram()` | `projects_data/{pid}/diagrams/` | [System Overview](system_overview.md) |
| Diagrams tab — Download | `downloadDiagram(pid, dtype)` | `GET /api/projects/{pid}/diagrams/{dtype}` | _(raw bytes in server.py)_ | `svc_diagram.get_diagram()` | drawio XML file | [System Overview](system_overview.md) |
| Pre-sales feedback form | `submitExternalFeedback(body)` | `POST /api/feedback/submit` | `h_presales.handle_external_feedback_submit()` | `svc_presales.submit_feedback()` | `presales_feedback` INSERT | [System Overview](system_overview.md) |
| Presales — Finalise | `finalisePresales(pid, decidedBy)` | `POST /api/projects/{pid}/presales/finalise` | _(inline in server.py)_ | `svc_presales.finalise_presales()` | `phases.is_current` transition | [Data Model](data_model.md) |
| Admin config panel | `viewAdmin()` | `GET /api/admin/config` | `h_admin.handle_update_config()` | `svc_admin.get_admin_config()` | `admin.config` JSON | [System Overview](system_overview.md) |
| Phase transition button | `transitionPhase(pid, phaseId)` | `POST /api/projects/{pid}/hierarchy/phase` | `h_admin.handle_hierarchy_phase_transition()` | `svc_hierarchy.set_hierarchy_phase()` | `phases.is_current` UPDATE | [Data Model](data_model.md) |
| Deep Dive panel | `runDeepDive(pid, body)` | `POST /api/projects/{pid}/deep-dive` | `h_deepdive.handle_deep_dive()` | `svc_deepdive.run_deep_dive()` | `reviews.deep_dive` field | [Logic Flow 3](logic_flow.md) |
| Prompt history panel | `viewPromptHistory(pid)` | `GET /api/projects/{pid}/prompt-history` | _(inline in server.py)_ | `svc_review.get_prompt_history()` | `prompt_log` SELECT | [System Overview](system_overview.md) |

---

## API → Data Entity Map

| API Endpoint | HTTP Method | Data Entity | Operation |
|---|---|---|---|
| `/api/projects` | GET | `projects` | SELECT WHERE status='active' |
| `/api/projects` | POST | `projects` | INSERT |
| `/api/projects/{pid}/hierarchy` | GET | `phases`, `versions`, `reviews` | SELECT tree JOIN |
| `/api/projects/{pid}/hierarchy/metrics` | GET | `versions`, `reviews`, `phases` | SELECT + aggregate |
| `/api/projects/{pid}/hierarchy/versions` | GET | `versions` | SELECT ORDER BY created_at DESC |
| `/api/projects/{pid}/hierarchy/versions/{vid}` | GET | `versions`, `reviews` | SELECT + list |
| `/api/projects/{pid}/hierarchy/versions/{vid}/readiness` | GET | `reviews.decision_points`, `reviews.weaknesses` | SELECT + compute |
| `/api/projects/{pid}/hierarchy/reviews` | GET | `reviews` | SELECT WHERE version_id= |
| `/api/projects/{pid}/hierarchy/reviews/{rid}` | GET | `reviews`, `versions` (context) | SELECT + join |
| `/api/projects/{pid}/hierarchy/reviews/{rid}/quality` | GET | `reviews` | SELECT + compute gate |
| `/api/projects/{pid}/hierarchy/reviews/{rid}/diff` | GET | `reviews` × 2 | SELECT + diff logic |
| `/api/review` | POST | `reviews`, `versions`, `phases`, `prompt_log` | INSERT + UPDATE × 3 |
| `/api/projects/{pid}/hierarchy/reviews/{rid}/complete` | POST | `reviews`, `decision_log` | UPDATE + INSERT |
| `/api/projects/{pid}/hierarchy/versions/{vid}/set-active-review-gated` | POST | `versions`, `reviews`, `decision_log` | UPDATE + INSERT |
| `/api/v1/projects/{pid}/artifacts/upload` | POST | `artifacts` | INSERT |
| `/api/v1/projects/{pid}/artifacts/process` | POST | `artifacts`, `jobs` | UPDATE × N + INSERT × N |
| `/api/projects/{pid}/build-context` | POST | `versions`, `phases`, `intelligence/current.json` | INSERT + UPDATE |
| `/api/projects/{pid}/presales/finalise` | POST | `phases`, `decision_log` | UPDATE + INSERT |
| `/api/admin/config` | GET/POST | `admin.config` (JSON file) | READ/WRITE |

---

## Diagram ↔ Code File Map

| Diagram | Primary Code Files It Documents |
|---|---|
| [System Overview](system_overview.md) | `server.py`, `handlers/*.py`, `services/*.py`, `personas/engine.py`, `ai_backends/`, `contracts/bus.py`, `db/database.py` |
| [Application Flow](application_flow.md) | `static/index.html` (`state`, `render()`, `viewDashboard()`, `viewVersions()`, `viewReviews()`, `switchTab()`) |
| [Logic Flow](logic_flow.md) | `services/review.py`, `services/intelligence.py`, `services/hierarchy.py`, `processors/review_quality.py`, `processors/context_builder.py`, `personas/engine.py` |
| [Sequence Flows](sequence_flows.md) | `handlers/review.py`, `handlers/artifact.py`, `handlers/intelligence.py`, `services/review.py`, `processors/pipeline.py`, `processors/prompt_logger.py`, `contracts/bus.py` |
| [Data Model](data_model.md) | `db/database.py`, `models/hierarchy.py`, `models/project.py`, `models/artifact.py`, `db/hierarchy_store_sql.py` |
| [Traceability Map](traceability_map.md) | ALL files (cross-cutting) |

---

## State Variable → API Call Map

| `state` Variable | Set By | Triggers API Call | API Endpoint |
|---|---|---|---|
| `state.projects` | Boot `init()` | `GET /api/projects` | `/api/projects` |
| `state.current` | `selectProject()` | Full `render()` re-fetch | Multiple |
| `state.tab` | `switchTab()` | View function dispatch | Tab-specific |
| `state._dashVersion` | Dashboard init / post-build | `GET …/hierarchy/metrics?version_id=` | `/hierarchy/metrics` |
| `state._dashReview` | Review run / tab init | `GET …/hierarchy/metrics?review_id=` | `/hierarchy/metrics` |
| `state._versionSort` | Sort bar click | Client-only re-sort | None |
| `state._reviewSort` | Sort bar click | Client-only re-sort | None |
| `state._lastRenderedProject` | After `render()` | Guards against redundant re-render | None |
| `state.backends` | Boot `init()` | `GET /api/backends` | `/api/backends` |
| `state._diagVersion` | Diagrams tab | `GET …/diagrams` | `/api/projects/{pid}/diagrams` |

---

## Naming Consistency Check

The following names are used consistently across UI, API, services, and DB:

| Concept | UI Variable | API Field | Service Param | DB Column |
|---|---|---|---|---|
| Project identifier | `state.current.id` | `project_id` | `project_id` | `projects.id` |
| Version identifier | `state._dashVersion` | `version_id` | `version_id` | `versions.version_id` |
| Review identifier | `state._dashReview` | `review_id` | `review_id` | `reviews.review_id` |
| Phase identifier | `phase.id` in UI | `phase_id` | `phase_id` | `phases.phase_id` |
| Persona name | `roles[]` in UI form | `roles` / `persona` | `persona_name` / `roles` | `reviews.persona` |
| AI backend | backend `<select>` value | `ai_backend` | `ai_backend` | `reviews.ai_backend` |
| Quality status | badge text | `quality_status` | `quality_status` | `reviews.quality_status` |
| Active review | accordion badge | `active_review_id` | `active_review_id` | `versions.active_review_id` |

**Known Inconsistency**: `roles` is used in the API request body (`POST /api/review`), but stored as `persona` (joined string) in the DB. The mapping occurs in `services/review.py` at `canonical_persona = " / ".join(roles_used)`.

---

## Linked Components (All)

`static/index.html` · `server.py` · `handlers/project.py` · `handlers/review.py` ·
`handlers/hierarchy.py` · `handlers/artifact.py` · `handlers/intelligence.py` ·
`handlers/presales.py` · `handlers/proposal.py` · `handlers/diagram.py` ·
`handlers/deepdive.py` · `handlers/admin.py` · `services/project.py` ·
`services/review.py` · `services/hierarchy.py` · `services/intelligence.py` ·
`services/ingest.py` · `services/presales.py` · `services/proposal.py` ·
`services/diagram.py` · `services/admin.py` · `processors/pipeline.py` ·
`processors/review_quality.py` · `processors/context_builder.py` ·
`processors/prompt_logger.py` · `processors/version_control.py` ·
`personas/engine.py` · `personas/deep_dive.py` · `ai_backends/__init__.py` ·
`contracts/bus.py` · `contracts/types.py` · `contracts/protocols.py` ·
`db/database.py` · `db/hierarchy_store_sql.py` · `db/artifact_store_sql.py` ·
`db/project_store_sql.py` · `models/hierarchy.py` · `models/project.py` ·
`models/artifact.py` · `models/proposal.py`
