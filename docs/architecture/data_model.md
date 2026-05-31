# Data Model

## Purpose
Entity-relationship diagram for all persisted entities, their attributes,
primary keys, foreign keys, and relationship cardinalities.
Sourced directly from `db/database.py` DDL and `models/` dataclasses.

---

## Core Entity Diagram

```mermaid
erDiagram

    %% ── Core hierarchy ────────────────────────────────────────

    PROJECT {
        TEXT id PK "e.g. p_uuid"
        TEXT name
        TEXT description
        TEXT phase "discovery|pre-sales|design|delivery|support"
        TEXT ai_backend "ollama|bedrock|gemini|files_only"
        TEXT status "active|archived"
        TEXT settings "JSON {}"
        TEXT files "JSON []"
        TEXT file_toggles "JSON {filename: bool}"
        TEXT iteration "JSON {current_version, total_builds, total_reviews, ...}"
        TEXT created_at "ISO 8601 UTC"
        TEXT updated_at "ISO 8601 UTC"
        TEXT archived_at
        TEXT restored_at
    }

    PHASE {
        TEXT project_id FK
        TEXT phase_id PK "pre-sales|design|delivery|support"
        TEXT label "Pre-sales|Design|Delivery|Support"
        INTEGER phase_order "1-4"
        TEXT description
        TEXT entered_at "ISO 8601 UTC"
        TEXT exited_at "ISO 8601 UTC"
        INTEGER is_current "0|1"
        INTEGER version_count "denormalized counter"
        INTEGER review_count "denormalized counter"
    }

    VERSION {
        TEXT version_id PK "e.g. v1 v2 v3"
        TEXT project_id FK
        TEXT phase_id FK "→ phases.phase_id"
        TEXT label "Version N"
        TEXT persona "selected persona name"
        TEXT scope "max 2000 chars"
        TEXT ai_backend
        TEXT included_artifacts "JSON [{artifactId, title, category}]"
        TEXT excluded_artifacts "JSON [{artifactId, title, category}]"
        TEXT stats "JSON {risks:N, deps:N, constraints:N, assumptions:N}"
        TEXT review_ids "JSON [r1, r2, ...]"
        TEXT active_review_id "FK → reviews.review_id"
        TEXT created_at "ISO 8601 UTC"
    }

    REVIEW {
        TEXT review_id PK "e.g. r1 r2 r3"
        TEXT project_id FK
        TEXT version_id FK "→ versions.version_id"
        TEXT phase_id FK "→ phases.phase_id"
        TEXT persona "e.g. Solution Architect"
        TEXT ai_backend
        TEXT prompt_used "full assembled prompt"
        TEXT custom_prompt "user override"
        TEXT output "JSON raw LLM output"
        TEXT findings "JSON {risks:[], gaps:[], recommendations:[], action_items:[], ...}"
        TEXT questions "JSON []"
        TEXT summary "120-char preview"
        TEXT included_files "JSON [filename, ...]"
        TEXT categories "JSON [category, ...]"
        TEXT ai_metadata "JSON {model, tokens, latency}"
        TEXT deep_dive "JSON | NULL"
        TEXT feedback "JSON | NULL"
        INTEGER completeness_score "0-100"
        TEXT quality_status "pending|interim|complete"
        TEXT completed_by
        TEXT completed_at
        TEXT decided_by "who set this as active review"
        TEXT previous_review_id "FK → reviews.review_id (self-ref)"
        INTEGER iteration_number "1-based within version"
        TEXT prompt_builder_state "JSON {injected_questions:[], user_notes:str} | NULL"
        TEXT weaknesses "JSON [{id,text,category,severity,status}]"
        TEXT decision_points "JSON [{id,text,category,status}]"
        TEXT created_at "ISO 8601 UTC"
    }

    %% ── Artifacts ─────────────────────────────────────────────

    ARTIFACT {
        TEXT artifact_id PK "e.g. a_abc12345"
        TEXT project_id FK
        TEXT type "file|text"
        TEXT file_name
        TEXT title
        TEXT category "project_artefact|meetings_comms|delivery_notes|client_context|architecture_design|external_data"
        TEXT metadata "JSON (category-specific fields)"
        INTEGER include "0|1"
        TEXT status "ingested|processing|processed|failed"
        TEXT raw_path "path to raw file on disk"
        TEXT text_content "extracted text (for text type)"
        TEXT created_at
    }

    %% ── Proposals ─────────────────────────────────────────────

    PROPOSAL {
        TEXT project_id PK_FK "1:1 with PROJECT"
        TEXT proposal_name
        TEXT client
        TEXT current_version "FK → proposal_versions.version_id"
        INTEGER total_versions
        TEXT created_at
        TEXT updated_at
    }

    PROPOSAL_VERSION {
        TEXT version_id PK "e.g. pv_uuid"
        TEXT project_id FK
        INTEGER version_number
        TEXT label
        TEXT status "draft|interim|complete"
        TEXT files "JSON []"
        TEXT notes
        TEXT changes_from_previous
        TEXT context_version
        TEXT feedback "JSON | NULL"
        TEXT hierarchy_version_id "FK → versions.version_id"
        TEXT active_review_id "FK → reviews.review_id"
        TEXT previous_version_id "FK → proposal_versions.version_id"
        TEXT feedback_applied "JSON [feedback_id, ...]"
        TEXT changes_summary
        TEXT quality_status "draft|interim|complete"
        INTEGER quality_score
        TEXT completed_by
        TEXT completed_at
        TEXT lock_status "unlocked|soft_locked"
        TEXT lock_reason
        TEXT created_at
    }

    PROPOSAL_DOCUMENT {
        TEXT doc_id PK
        TEXT project_id FK
        TEXT proposal_ver_id FK
        TEXT generated_at
        TEXT ai_backend
        TEXT exec_summary
        TEXT scope
        TEXT delivery_phases "JSON [{phase, description, duration_weeks}]"
        TEXT gantt_data "JSON [{milestone, start_week, end_week, owner}]"
        TEXT risks "JSON [{risk, category, impact, probability, mitigation}]"
        TEXT assumptions "JSON [{category, assumption}]"
        TEXT exclusions "JSON [str]"
        TEXT responsibilities "JSON RACI matrix"
        TEXT acceptance_criteria "JSON [str]"
        TEXT hierarchy_version_id "FK → versions.version_id"
        TEXT active_review_id "FK → reviews.review_id"
        INTEGER word_count
    }

    %% ── Pre-sales ─────────────────────────────────────────────

    PRESALES_FEEDBACK {
        TEXT feedback_id PK
        TEXT project_id FK
        TEXT proposal_ver_id "FK → proposal_versions.version_id"
        TEXT review_id "FK → reviews.review_id"
        TEXT version_id "FK → versions.version_id"
        TEXT source "internal|external"
        TEXT responder_name
        TEXT responder_email
        TEXT feedback_items "JSON [{id, text, type, status}]"
        TEXT raw_text
        TEXT change_requested "JSON [str]"
        TEXT accepted "JSON [str]"
        TEXT rejected "JSON [str]"
        TEXT concerns "JSON [str]"
        TEXT notes
        TEXT next_action
        TEXT status "open|actioned|closed"
        TEXT created_at
        TEXT updated_at
    }

    FEEDBACK_TOKEN {
        TEXT token PK
        TEXT project_id FK
        TEXT proposal_ver_id
        TEXT review_id
        TEXT expires_at
        INTEGER used "0|1"
        TEXT created_at
    }

    %% ── Audit & Logging ──────────────────────────────────────

    DECISION_LOG {
        TEXT log_id PK
        TEXT project_id FK
        TEXT entity_type "review|proposal_version|feedback_item|finalisation"
        TEXT entity_id "FK (polymorphic)"
        TEXT action "completed|set_active|generated|finalised|gate_passed|gate_failed"
        TEXT actor
        TEXT reason
        TEXT metadata "JSON snapshot at time of decision"
        TEXT created_at
    }

    PROMPT_LOG {
        TEXT log_id PK
        TEXT project_id FK
        TEXT review_id FK
        TEXT persona_name
        TEXT scenario_type
        TEXT baseline_prompt
        TEXT injected_questions
        TEXT user_notes
        TEXT final_prompt
        TEXT outcome_review_id
        TEXT outcome_proposal_ver_id
        TEXT created_at
    }

    JOB {
        TEXT job_id PK "e.g. j_uuid6"
        TEXT artifact_id FK
        TEXT project_id FK
        TEXT status "queued|processing|succeeded|failed"
        TEXT started_at
        TEXT ended_at
        TEXT error
        TEXT created_at
    }

    %% ── Relationships ────────────────────────────────────────

    PROJECT ||--o{ PHASE : "has 1:N"
    PROJECT ||--o{ VERSION : "has 1:N"
    PROJECT ||--o| PROPOSAL : "has 0:1"
    PROJECT ||--o{ ARTIFACT : "owns 1:N"
    PROJECT ||--o{ PRESALES_FEEDBACK : "has 1:N"
    PROJECT ||--o{ DECISION_LOG : "audits 1:N"
    PROJECT ||--o{ PROMPT_LOG : "logs 1:N"
    PROJECT ||--o{ JOB : "has 1:N"

    PHASE ||--o{ VERSION : "groups 1:N"
    PHASE ||--o{ REVIEW : "groups 1:N"

    VERSION ||--o{ REVIEW : "has 1:N"
    VERSION ||--o| REVIEW : "active_review_id 0:1"

    REVIEW ||--o| REVIEW : "previous_review_id 0:1 (self-ref)"
    REVIEW ||--o{ PROMPT_LOG : "logged by 1:N"

    PROPOSAL ||--o{ PROPOSAL_VERSION : "has 1:N"
    PROPOSAL_VERSION ||--o{ PROPOSAL_DOCUMENT : "generates 1:N"
    PROPOSAL_VERSION ||--o{ PRESALES_FEEDBACK : "receives 1:N"
    PROPOSAL_VERSION }o--|| VERSION : "references hierarchy version"
    PROPOSAL_VERSION }o--|| REVIEW : "references active review"

    ARTIFACT ||--o{ JOB : "processed by 1:N"
```

---

## Key Relationships Summary

| Relationship | Cardinality | FK Location | Notes |
|---|---|---|---|
| Project → Phase | 1:N | `phases.project_id` | 4 standard phases seeded on first access |
| Project → Version | 1:N | `versions.project_id` | Versions are snapshots; never deleted |
| Phase → Version | 1:N | `versions.phase_id` | Version belongs to the active phase at creation time |
| Version → Review | 1:N | `reviews.version_id` | Multiple review iterations per version |
| Version → Review (active) | 0:1 | `versions.active_review_id` | Denormalized pointer; validated on read |
| Review → Review (predecessor) | 0:1 self-ref | `reviews.previous_review_id` | Chains review iterations |
| Project → Artifact | 1:N | `artifacts.project_id` | Artifacts are the raw input documents |
| Artifact → Job | 1:N | `jobs.artifact_id` | One job per processing run |
| Project → Proposal | 0:1 | `proposals.project_id` (PK=FK) | Optional; created in pre-sales phase |
| Proposal → ProposalVersion | 1:N | `proposal_versions.project_id` | Versioned proposal iterations |
| ProposalVersion → Version | N:1 | `proposal_versions.hierarchy_version_id` | Traceability to intelligence version |
| ProposalVersion → Review | N:1 | `proposal_versions.active_review_id` | Traceability to specific review |

---

## Persistence Strategy

| Store | Primary Use | Location | Enabled By |
|---|---|---|---|
| SQLite (`accelerator.db`) | Primary read/write | `projects_data/accelerator.db` | `sqlite_write_enabled=True` (default) |
| Flat JSON files | Human-readable backup / legacy support | `projects_data/{pid}/hierarchy/` | `file_write_enabled=True` (default) |
| Processed documents | Artifact text extraction output | `projects_data/{pid}/processed/{aid}.json` | Always |
| Job files | Async job status | `projects_data/jobs/{jid}.json` | Always |
| Intelligence cache | Assembled context for review | `projects_data/{pid}/intelligence/current.json` | Always |

---

## Key Assumptions

1. **SQLite as source of truth**: When `sqlite_write_enabled=True`, all reads go to SQLite. Flat files are written in parallel only as a backup.
2. **version_id / review_id are sequential integers**: `v1`, `v2`, `v3` and `r1`, `r2`, `r3` — computed from `COUNT(*)+1` at insert time. Not UUIDs.
3. **No cascading deletes in SQLite schema**: Soft deletes for projects (`status='archived'`); hard deletes for reviews via `DELETE` + manual parent update.
4. **All JSON columns**: SQLite stores complex objects as JSON strings; `Database.jload()` / `Database.jdump()` handle serialisation.
5. **Denormalized counters**: `phases.version_count` and `phases.review_count` are incremented/decremented on write; they are not computed from joins at query time.

---

## Linked Components

| Component | File |
|---|---|
| SQLite schema DDL | `db/database.py` |
| File-based hierarchy store | `models/hierarchy.py` → `HierarchyStore` |
| SQLite-backed hierarchy store | `db/hierarchy_store_sql.py` → `HierarchyStoreSQLite` |
| Project model dataclass | `models/project.py` → `Project`, `ProjectContext`, `ReviewOutput` |
| Hierarchy model dataclasses | `models/hierarchy.py` → `Phase`, `Version`, `Review` |
| Artifact model dataclass | `models/artifact.py` → `Artifact` |
| Proposal model dataclass | `models/proposal.py` |
| Store factory | `models/hierarchy.py` → `_make_hierarchy_store()` |
