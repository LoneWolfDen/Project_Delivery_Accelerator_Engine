# Project Context – Delivery Accelerator Engine

## Identity

- **Product**: Project Delivery Accelerator Engine
- **Codename**: Contexta
- **Version**: v2 complete (180 tests), v3 UI delivered
- **Repo**: LoneWolfDen/Project_Delivery_Accelerator_Engine

## What This Is

A context-aware delivery intelligence platform converting documents into reusable project intelligence across the SDLC. NOT a dashboard with AI – a Context Operating System for Delivery.

## Architecture (Current)

```
server.py              → HTTP API + static file serving (Web UI)
cli.py                 → CLI (13+ commands)
project_manager.py     → Project CRUD + orchestration (resolves relative paths)
static/index.html      → SPA Web UI (dark theme, vanilla JS)
processors/
  ingestion.py         → File type detection + routing (5 parsers)
  context_builder.py   → Multi-doc aggregation + summary
  history.py           → Version tracking + comparisons
  proposals.py         → Proposal versioning
  phases.py            → SDLC phase management
  extractors/          → Pattern-based intelligence extraction
  parsers/             → txt, md, csv, eml, transcript parsers
personas/
  engine.py            → Review orchestration (files_only/ollama/bedrock)
  definitions/         → 4 YAML persona configs
models/                → project.py, document.py, proposal.py
```

## Project Data Structure

```
projects_data/{project_id}/
  ├── uploads/          # raw files
  ├── context/          # ingested document JSONs
  ├── intelligence.json # current built intelligence
  ├── versions/         # v1.json, v2.json... (versioned snapshots)
  ├── reviews/          # persona review results
  ├── proposals/        # proposal tracker + versions
  └── transitions.json  # phase transition audit log
```

## V2 Design Principles

1. File paths resolve relative to project root (Path(__file__).parent)
2. Intelligence = versioned snapshots (re-runnable, comparable)
3. Personas are project-aware (receive project context, store per-project)
4. Phase = lightweight tag (not over-engineered state machine)
5. Token discipline: build_context_summary() for AI prompts (<2K chars)
6. Files-only mode = zero-cost, instant, deterministic analysis

## V2→V3 Alignment Notes

Per product direction review:
- Proposals module exists but spec says simplify to "phase tag" – keep for now, may consolidate later
- Phase system works but could be simplified to version metadata tag
- File registry needs: file_id, processed_status (partial gap)
- Version snapshots should store exact input file list (minor gap)
- Ingest path resolution: FIXED – resolves relative to project_manager.py parent

## What to IGNORE

- `_archive/` – legacy migration demo
- `projects_data/` – runtime data, gitignored
- `outputs/` – generated exports, gitignored

## Tech Stack

- Python 3.9+, pyyaml only external dep
- stdlib HTTP server + static file serving
- Vanilla JS SPA (no build step, no framework)
- pytest (180 tests)
- Optional: boto3 (Bedrock), ollama (local AI)

## Coding Standards

- Dataclasses for models, type hints everywhere
- Docstrings on all public functions
- 100-char lines (ruff)
- MIN_EXTRACTION_LENGTH = 15 for quality filtering
- Tests in tests/, fixtures in sample_data/

## Key API Endpoints (complete list)

GET: /, /api/health, /api/projects,
  /api/projects/{id}/context, /api/projects/{id}/intelligence,
  /api/projects/{id}/summary, /api/projects/{id}/versions,
  /api/projects/{id}/versions/{vid}, /api/projects/{id}/reviews,
  /api/projects/{id}/evolution/{category},
  /api/projects/{id}/proposal, /api/projects/{id}/phase-history
POST: /api/projects, /api/ingest,
  /api/projects/{id}/build-context, /api/review, /api/personas,
  /api/projects/{id}/compare-versions, /api/projects/{id}/compare-reviews,
  /api/projects/{id}/proposal, /api/projects/{id}/proposal/version,
  /api/projects/{id}/phase
