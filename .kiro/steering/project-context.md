# Project Context – Delivery Accelerator Engine

## Identity

- **Product**: Project Delivery Accelerator Engine
- **Codename**: Contexta
- **Version**: v2 complete, v3 in progress
- **Repo**: LoneWolfDen/Project_Delivery_Accelerator_Engine

## What This Is

A **context-aware delivery intelligence platform** that converts documents, discussions, and decisions into reusable project intelligence across the full SDLC.

## v2 Status: COMPLETE (180 tests passing)

All v2 features are implemented and merged:
- Ingestion pipeline (5 parsers: txt, md, csv, eml, transcripts)
- Context builder (pattern-based extraction with dedup)
- Persona review engine (4 personas, 3 backends: files_only/ollama/bedrock)
- Iteration & history (versioned builds, comparisons, evolution timelines)
- Enhanced extraction (table parsing, noise filtering, fuzzy dedup)
- CLI interface (13 commands covering full workflow)
- Proposal version tracking (multi-version with status lifecycle)
- SDLC phase transitions (validated, with audit trail)

## v3 In Progress

Current focus: **Web UI** (single-page app consuming existing API)

Upcoming:
- Diagram generation (.drawio)
- Proposal auto-drafts
- Export to Word/PowerPoint
- Pre-sales → delivery feedback loop

## Architecture

```
cli.py                 → CLI (13 commands)
server.py              → HTTP API (GET / for endpoint list)
project_manager.py     → Project CRUD + orchestration
processors/
  ingestion.py         → File type detection + routing
  context_builder.py   → Multi-doc aggregation + summary
  history.py           → Version tracking + comparisons
  proposals.py         → Proposal versioning
  phases.py            → SDLC phase management
  extractors/
    patterns.py        → Regex patterns (enhanced)
    intelligence_extractor.py → Section-aware extraction
  parsers/             → 5 format parsers
personas/
  engine.py            → Review orchestration (3 backends)
  definitions/         → 4 YAML persona configs
models/
  project.py           → Project, ProjectContext, ReviewOutput, IterationMetadata
  document.py          → IngestedDocument, DocumentSection, DocumentMetadata
  proposal.py          → ProposalVersion, ProposalTracker
```

## What to IGNORE

- `_archive/` – legacy migration demo, never load into context
- `projects_data/` – runtime data, gitignored
- `outputs/` – generated exports, gitignored

## Tech Stack

- Python 3.9+, no external deps except pyyaml
- stdlib HTTP server (no framework)
- YAML for persona definitions, JSON for persistence
- pytest (180 tests)
- Optional: boto3 (Bedrock), ollama (local AI)

## Coding Standards

- Dataclasses for models, type hints everywhere
- Docstrings on all public functions
- NotImplementedError for stubs
- 100-char lines (ruff), MIN_EXTRACTION_LENGTH = 15
- Tests in tests/, sample fixtures in sample_data/

## Key API Endpoints

GET /, /api/health, /api/projects, /api/projects/{id}/context,
/api/projects/{id}/intelligence, /api/projects/{id}/summary,
/api/projects/{id}/versions, /api/projects/{id}/versions/{vid},
/api/projects/{id}/reviews, /api/projects/{id}/evolution/{category}
POST /api/projects, /api/ingest, /api/projects/{id}/build-context,
/api/review, /api/personas, /api/projects/{id}/compare-versions,
/api/projects/{id}/compare-reviews
