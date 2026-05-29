# Project Context – Delivery Accelerator Engine

## Identity

- **Product**: Project Delivery Accelerator Engine (Contexta)
- **Purpose**: Context-aware delivery intelligence platform – converts documents into reusable project intelligence across SDLC phases.

## Constraints

- Single-container Docker deployment
- Offline-first operation
- Non-technical users as primary audience
- Open-source components only
- Python 3.9+, pyyaml only external dep
- Vanilla JS SPA (no build step, no framework)

## Architecture

- `server.py` – HTTP API + static file serving
- `project_manager.py` – Project CRUD + orchestration
- `static/index.html` – SPA Web UI (dark theme, vanilla JS)
- `processors/` – Ingestion, context building, extractors, parsers
- `personas/` – Review orchestration (files_only/ollama/bedrock)
- `models/` – Dataclass models (project, document, hierarchy, proposal)

## Key Patterns

- File paths resolve relative to `Path(__file__).parent`
- Intelligence = versioned snapshots (re-runnable, comparable)
- Hierarchy model: Phase → Version → Review
- Files-only mode = zero-cost, deterministic analysis
- Dataclasses + type hints + docstrings on public functions

## Ignore

- `_archive/` – legacy demo code
- `projects_data/` – runtime data (gitignored)
