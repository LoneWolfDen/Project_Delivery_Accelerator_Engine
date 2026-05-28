# Project Context – Delivery Accelerator Engine v2

## What This Is

A **context-aware delivery intelligence platform** (not a migration dashboard).
Product name: **Project Delivery Accelerator Engine**
Internal codename: **Contexta**

## Core Mission

Convert documents, discussions, and decisions into **reusable project intelligence** across the full SDLC:
Discovery → Proposal → SoW review → Planning → Execution → Review

## Key Design Principles

1. **Token discipline** – Only load minimum required context per AI request. Use structured extraction, not long text.
2. **Stateful, not stateless** – Build project memory. Store intermediate findings. Reuse them.
3. **Persona-driven** – Reviews use predefined role prompts (Solution Architect, Delivery Manager, Product Owner, Resource Manager). Users never write prompts.
4. **Multi-backend** – Support Ollama (local), AWS Bedrock (cloud), and files-only (no AI) modes.
5. **Iteration over repetition** – Save outputs, compare versions, track how risks/assumptions evolve.

## Architecture (Current v2)

```
server.py              → Lightweight HTTP API
project_manager.py     → Project CRUD + persistence
processors/            → Ingestion + context building
personas/              → Review engine + YAML persona definitions
models/                → Data models (Project, Context, ReviewOutput)
sample_data/           → Test input files
outputs/               → Generated results (gitignored)
_archive/              → Legacy migration demo (reference only, ignore)
```

## What to IGNORE

- `_archive/` folder – old migration-specific demo code. Do not reference for v2 work.
- Any files mentioning "AnyCompany", "migration dashboard", or hardcoded GANTT data are legacy.

## Tech Stack

- Python 3.9+
- YAML for persona definitions
- JSON for project persistence
- HTTP server (stdlib, no framework yet)
- pytest for testing
- Optional: boto3 (Bedrock), ollama (local AI), strands-agents

## Coding Standards

- Keep modules small and focused
- Use dataclasses for models
- Type hints on all function signatures
- Docstrings on all public functions
- Raise NotImplementedError for stubs (not pass)
- Max 100 chars line length (ruff enforced)

## When Working on This Repo

- Always check current project structure before making changes
- Don't load _archive/ files into context unless explicitly asked
- Prefer structured outputs (dicts, dataclasses) over raw strings
- Keep sample_data/ as test fixtures – don't hardcode data in source
