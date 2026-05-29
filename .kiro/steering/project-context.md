# Contexta – Project Delivery Accelerator Engine

Context-aware delivery intelligence: documents → reusable project intelligence across SDLC phases.

## Constraints

Single-container Docker, offline-first, non-technical users, open-source only.
Python 3.9+ (pyyaml only dep). Vanilla JS SPA (no build/framework).

## Layout

| Path | Role |
|------|------|
| `server.py` | HTTP API + static serving |
| `project_manager.py` | Project CRUD + orchestration |
| `static/index.html` | SPA UI (dark theme, vanilla JS) |
| `static/feedback.html` | External client feedback form (P9) |
| `processors/` | Ingestion, context, extractors, parsers |
| `processors/presales_feedback.py` | P9 feedback loop processor + prompt injection |
| `personas/` | Review orchestration (files_only/ollama/bedrock) |
| `models/` | Dataclasses: project, document, hierarchy, proposal |
| `db/` | SQLite layer (P8): database, hierarchy_store_sql, artifact_store_sql, project_store_sql |
| `scripts/seed_sqlite.py` | Seed fresh SQLite test data |

## Storage (P8 — Dual-Write)

Two stores run in parallel by default (configurable in Admin → Storage Mode):

| Flag | Default | Effect |
|------|---------|--------|
| `sqlite_write_enabled` | `True` | Write to `projects_data/accelerator.db` |
| `file_write_enabled` | `True` | Mirror to JSON files (backward compat) |

SQLite tables: `projects`, `phases`, `versions`, `reviews`, `artifacts`, `proposals`, `proposal_versions`, `jobs`, `presales_feedback`, `feedback_tokens`.

## Pre-Sales Feedback Loop (P9)

Hierarchy: Proposal → ProposalVersion → PresalesFeedback

| API | Purpose |
|-----|---------|
| `GET /api/projects/{id}/presales/summary` | Aggregated pre-sales view |
| `GET/POST /api/projects/{id}/presales/feedback` | List / capture feedback (internal) |
| `POST /api/projects/{id}/presales/feedback/{fid}/action` | Update status / next action |
| `POST /api/projects/{id}/presales/share` | Generate one-time client share token |
| `GET /api/feedback/form?token=` | Return form context for external page |
| `POST /api/feedback/submit` | External client submission (token-validated) |

Feedback auto-injects into next review prompt via `processors/presales_feedback.get_feedback_prompt_injection()`.
`personas/engine.run_review()` reads `context._project_id` and prepends feedback block to `custom_prompt`.

## Patterns

- Paths resolve via `Path(__file__).parent`
- Intelligence = versioned snapshots (re-runnable, comparable)
- Hierarchy: Phase → Version → Review
- Files-only mode = deterministic, zero-cost analysis
- Dataclasses + type hints + docstrings on public API

## Ignore

`_archive/` (legacy), `projects_data/` (runtime, gitignored)
