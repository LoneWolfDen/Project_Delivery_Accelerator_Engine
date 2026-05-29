# Contributing to Project Delivery Accelerator Engine

Thank you for taking the time to contribute. This document covers everything you need to go from zero to a merged pull request.

---

## Table of Contents

1. [What This Project Is](#what-this-project-is)
2. [Workflow Guide (User Perspective)](#workflow-guide-user-perspective)
3. [Architecture Overview](#architecture-overview)
4. [Dev Setup](#dev-setup)
5. [Running Tests](#running-tests)
6. [How to Add a Persona](#how-to-add-a-persona)
7. [How to Add an AI Backend](#how-to-add-an-ai-backend)
8. [Coding Standards](#coding-standards)
9. [Pull Request Checklist](#pull-request-checklist)

---

## What This Project Is

A **context-aware delivery intelligence platform** that converts project documents (SoW, proposals, meeting notes, transcripts) into structured intelligence, then applies persona-driven review to surface risks, gaps, and blind spots — targeted at non-technical delivery team members.

**Design constraints that every change must respect:**
- Single Docker container (no external services required)
- Offline-first (all core functionality works without internet)
- Non-technical users are the primary audience (plain language, no jargon)
- Open-source components only (no proprietary dependencies)

---

## Workflow Guide (User Perspective)

Understanding the intended user journey helps you contribute features in the right place:

```
Step 1 — Add Documents
  Upload files or paste text in the Ingest tab.
  Supported: .txt .md .csv .eml .json .yaml .pdf .docx .xlsx .pptx

Step 2 — Analyse Documents
  Click "Analyse Documents" to extract structured intelligence:
  risks, assumptions, dependencies, constraints, action items.
  Each build creates a versioned snapshot.

Step 3 — Run a Review
  Choose a Review Role (persona) and AI Model.
  The engine applies a structured lens to the intelligence.
  Each persona covers a specific set of PM dimensions.

Step 4 — Review the Output
  Full Details shows: files included, PM coverage assessment,
  findings per category, open questions, prompt used.

Step 5 — Compare & Iterate
  Add more documents, rebuild, re-run reviews.
  The Versions tab shows the full Phase → Version → Review history.
```

---

## Architecture Overview

```
static/index.html           ← Single-file SPA (vanilla JS, no build step)
server.py                   ← stdlib HTTP server, all API routes
project_manager.py          ← Orchestration layer (CRUD + business logic)
│
├── processors/
│   ├── ingestion.py        ← File type detection + routing to parsers
│   ├── context_builder.py  ← Aggregation, dedup, ProjectContext assembly
│   ├── history.py          ← Version snapshots + comparison
│   ├── artifact_store.py   ← Artifact registry (JSON file-based)
│   ├── pipeline.py         ← Processing pipeline: ingested→processed
│   ├── version_control.py  ← Run records (traceability)
│   ├── extractors/         ← Pattern-based intelligence extraction
│   └── parsers/            ← txt, md, csv, eml, transcript parsers
│
├── personas/
│   ├── engine.py           ← Review orchestration (files_only + AI)
│   ├── deep_dive.py        ← Gap analysis: scope validation + risk flags
│   └── definitions/        ← Per-persona YAML configs (focus areas, prompts)
│
├── models/
│   ├── project.py          ← Project, ProjectContext, ReviewOutput
│   ├── document.py         ← IngestedDocument, DocumentSection
│   ├── artifact.py         ← Artifact, ArtifactCategory, CATEGORY_METADATA_SCHEMA
│   ├── hierarchy.py        ← Phase → Version → Review (HierarchyStore)
│   └── proposal.py         ← ProposalTracker
│
├── ai_backends/
│   ├── base.py             ← AIBackend ABC + AIResponse dataclass
│   ├── registry.py         ← get_backend() factory
│   ├── files_only.py       ← Zero-cost heuristic (no AI)
│   ├── groq_backend.py     ← Groq (free tier)
│   ├── openrouter_backend.py
│   ├── gemini_backend.py
│   ├── ollama_backend.py   ← Local offline LLM
│   └── bedrock_backend.py  ← AWS Bedrock
│
└── admin/
    ├── config.py           ← AdminConfig dataclass + env var loading
    ├── guardrails.py       ← Pre-flight validation
    ├── health.py           ← System health tracking
    └── lifecycle.py        ← Archive/delete audit log

Data layout (all JSON, no database):
projects_data/
  projects.json             ← All project metadata
  admin_config.json         ← System config (API keys, limits, PIN)
  jobs/                     ← Processing job records
  {project_id}/
    raw/                    ← Uploaded files
    artifacts.json          ← Artifact registry
    context/                ← Legacy ingested document JSONs
    intelligence/
      current.json          ← Latest built intelligence
    versions/               ← Versioned context snapshots
    reviews/                ← Persona review results
    hierarchy/              ← Phase/Version/Review hierarchy
    run_history/            ← Version control records
```

---

## Dev Setup

### Prerequisites

- Python 3.9+ (3.11 recommended)
- pip

### Install

```bash
# Clone
git clone https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine.git
cd Project_Delivery_Accelerator_Engine

# Install with dev extras
pip install -e ".[dev]"

# Optional: install AI backend dependencies
pip install -e ".[ai]"
```

### Run locally

```bash
# Set required env vars
export ADMIN_PIN=your-secure-pin

# Optional: point to a custom data directory
export PROJECTS_DATA_DIR=/path/to/your/data

# Start the server
python server.py
# → http://localhost:8080
```

### Run with Docker

```bash
docker build -t delivery-accelerator .

docker run -d \
  --name delivery-accelerator \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e ADMIN_PIN=your-secure-pin \
  -e GROQ_API_KEY=your-key \
  delivery-accelerator
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage (must stay above 80%)
pytest --cov=. --cov-report=term-missing

# Run a single test file
pytest tests/test_context_builder.py -v

# Lint
ruff check .
ruff format --check .
```

The CI pipeline (`.github/workflows/ci.yml`) runs lint + tests on Python 3.9, 3.11, and 3.12 on every push and pull request.

---

## How to Add a Persona

Personas are pure YAML — no Python changes needed for simple additions.

### 1. Create the YAML definition

```bash
# personas/definitions/my_persona.yaml
name: My Persona
role: One-sentence description of what this persona focuses on.
focus_areas:
  - First focus area
  - Second focus area
  - Third focus area
output_format:
  sections:
    - section_one
    - section_two
    - recommendations
    - questions
prompt_template: |
  You are a My Persona reviewing project documentation.
  Focus on [your areas].
  Provide structured output with: section_one, section_two, recommendations, and open questions.
```

### 2. Register in the engine

```python
# personas/engine.py  —  AVAILABLE_PERSONAS dict
AVAILABLE_PERSONAS = {
    ...
    "my_persona": "my_persona.yaml",
}
```

### 3. (Optional) Add persona-specific analysis for files_only mode

Add a `_analyse_my_persona()` function in `personas/engine.py` following the same pattern as `_analyse_solution_architect()`, then route to it in `_analyse_by_persona()`.

### 4. (Optional) Add PM coverage dimensions

```javascript
// static/index.html  —  COVERAGE_PERSONA object
COVERAGE_PERSONA['my_persona'] = [
  {id:'area1', label:'My Area 1', icon:'🔍',
   keywords:['keyword1','keyword2','keyword3']},
  // ...
];
```

---

## How to Add an AI Backend

### 1. Create the backend class

```python
# ai_backends/my_backend.py
from ai_backends.base import AIBackend, AIResponse

class MyBackend(AIBackend):
    name = "my_backend"
    display_name = "My Backend (model-name)"

    def is_available(self) -> bool:
        import os
        return bool(os.environ.get("MY_BACKEND_API_KEY"))

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.3, max_tokens: int = 2000) -> AIResponse:
        import time
        start = time.time()
        try:
            # Call your API here
            response_text = "..."
            return AIResponse(
                text=response_text,
                model="my-model-name",
                tokens_used=0,
                latency_ms=(time.time() - start) * 1000,
                success=True,
            )
        except Exception as e:
            return AIResponse(text="", model="", tokens_used=0,
                              latency_ms=0, success=False, error=str(e))
```

### 2. Register in the registry

```python
# ai_backends/registry.py
from ai_backends.my_backend import MyBackend

_BACKENDS: Dict[str, Type[AIBackend]] = {
    ...
    "my_backend": MyBackend,
}
```

### 3. Add to valid backends list

```python
# personas/engine.py
VALID_BACKENDS = {"files_only", "ollama", "bedrock", "gemini", "groq", "openrouter", "my_backend"}
```

### 4. Document the env var in Dockerfile

```dockerfile
# ENV MY_BACKEND_API_KEY=
```

---

## Coding Standards

| Rule | Detail |
|------|--------|
| **Type hints** | All public functions must have full type annotations |
| **Docstrings** | All public functions and classes require docstrings |
| **Line length** | 100 characters (enforced by ruff) |
| **Models** | Use `@dataclass` for all data models |
| **Error handling** | Catch specific exceptions; never bare `except:` |
| **Logging** | Use `print()` for now (stdlib, no external deps) |
| **Tests** | New features need tests; coverage must stay ≥ 80% |
| **No new deps** | Core functionality must use Python stdlib only |
| **HTML safety** | Always use `escHtml()` in the JS frontend |

---

## Pull Request Checklist

Before opening a PR, confirm:

- [ ] All tests pass: `pytest`
- [ ] Lint passes: `ruff check . && ruff format --check .`
- [ ] No new hardcoded secrets, PINs, or API keys
- [ ] New public functions have docstrings and type hints
- [ ] If adding a persona: YAML + engine registration + coverage dimensions
- [ ] If adding a backend: backend class + registry + VALID_BACKENDS
- [ ] If changing data models: tests updated
- [ ] `README.md` updated if user-facing behaviour changed
- [ ] PR description explains *what*, *why*, and *how to test*
