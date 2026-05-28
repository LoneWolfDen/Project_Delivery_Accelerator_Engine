# Architecture

System design overview for the Project Delivery Accelerator Engine.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                           │
├──────────────────┬──────────────────┬───────────────────────────┤
│   CLI (cli.py)   │  API (server.py) │   Web UI (static/)        │
└────────┬─────────┴────────┬─────────┴──────────┬────────────────┘
         │                  │                    │
         ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Project Manager                                │
│                  (project_manager.py)                             │
│  - CRUD operations                                               │
│  - File management                                               │
│  - Orchestrates processors                                       │
└────────┬─────────┬────────────────┬─────────────────────────────┘
         │         │                │
         ▼         ▼                ▼
┌────────────┐ ┌──────────────┐ ┌──────────────────────────┐
│ Processors │ │   Personas   │ │      AI Backends          │
│            │ │              │ │                            │
│ ingestion  │ │ engine.py    │ │ files_only (heuristic)    │
│ context_   │ │ definitions/ │ │ gemini (Google)           │
│   builder  │ │  *.yaml      │ │ ollama (local)            │
│ history    │ │              │ │ bedrock (AWS)             │
│ proposals  │ │              │ │                            │
│ phases     │ │              │ │ base.py (abstract)        │
│ extractors │ │              │ │ registry.py (factory)     │
└────────────┘ └──────────────┘ └──────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                   │
│                                                                   │
│  projects_data/                                                   │
│  ├── projects.json          (project registry)                   │
│  ├── proj-001/                                                   │
│  │   ├── uploads/           (raw uploaded files)                 │
│  │   ├── context/           (ingested document JSONs)            │
│  │   ├── outputs/           (generated artifacts)                │
│  │   ├── reviews/           (review result JSONs)                │
│  │   ├── versions/          (context version snapshots)          │
│  │   ├── intelligence.json  (current built intelligence)         │
│  │   └── proposal.json      (proposal tracker)                   │
│  └── proj-002/                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### Project Manager (`project_manager.py`)

Central orchestrator. Handles:
- Project CRUD (max 5 active projects)
- File ingestion routing
- Intelligence build triggers
- Review execution
- Version and iteration tracking
- Proposal management
- Phase transitions

### Processors (`processors/`)

| Module | Responsibility |
|--------|---------------|
| `ingestion.py` | Parse files into `IngestedDocument` (txt, md, csv, email, transcript) |
| `context_builder.py` | Extract structured intelligence (risks, assumptions, etc.) from documents |
| `extractors.py` | Low-level extraction patterns (keywords, tables, heuristics) |
| `history.py` | Version tracking, comparisons, evolution timelines |
| `proposals.py` | Multi-version proposal management |
| `phases.py` | SDLC phase transitions and validation |

### Persona Engine (`personas/`)

- Loads persona definitions from YAML
- Builds structured prompts (role + focus + context + custom instructions)
- Routes to appropriate AI backend
- Parses AI output into structured findings
- Falls back to heuristic analysis if AI unavailable

### AI Backends (`ai_backends/`)

Pluggable adapter pattern:

```python
from ai_backends import get_backend

backend = get_backend("gemini")  # or "ollama", "bedrock", "files_only"
response = backend.generate(prompt, system_prompt="...")
```

Each backend implements:
- `generate(prompt, system_prompt, temperature, max_tokens) → AIResponse`
- `is_available() → bool`
- `name` / `display_name` properties

Graceful fallback: if any AI backend fails, the system falls back to `files_only` heuristic analysis and reports the fallback in the response.

---

## Data Flow

### Ingestion → Intelligence → Review

```
1. User uploads files
2. Ingestion parser detects file type and extracts sections
3. Context builder runs extraction patterns across all documents
4. Intelligence is built: risks, assumptions, dependencies, constraints, scope
5. Persona engine receives intelligence + persona definition
6. Prompt is constructed (persona template + context summary + custom user prompt)
7. AI backend generates response (or heuristic analysis runs)
8. Response is parsed into structured findings
9. Review is stored and iteration metadata updated
```

### Version Tracking

Every `build-context` creates a versioned snapshot:
- `v1`, `v2`, etc. stored in `projects_data/{id}/versions/`
- Enables diff between builds
- Evolution timeline shows how categories change over iterations

---

## Design Decisions

### Token Discipline

- Context is summarized before sending to AI (not raw documents)
- Only relevant intelligence is included per persona
- Prompts are structured with clear sections for consistent output
- Max 2000 output tokens per review

### Stateful, Not Stateless

Unlike chat-based tools:
- Project memory persists across sessions
- Intelligence is built once, reused many times
- Reviews accumulate and can be compared
- Context carries forward across phases

### No Database

- JSON file storage for simplicity and portability
- No external dependencies for persistence
- Easy to inspect, back up, version control

### Graceful Degradation

- Every AI backend falls back to `files_only` on failure
- System always produces output, even without AI
- Error information is preserved in response for debugging

---

## Extension Points

### Adding a new AI backend

1. Create `ai_backends/my_backend.py` extending `AIBackend`
2. Implement `generate()`, `is_available()`, `name`, `display_name`
3. Register in `ai_backends/registry.py`

### Adding a new persona

1. Create `personas/definitions/my_persona.yaml`
2. Add entry to `AVAILABLE_PERSONAS` in `personas/engine.py`
3. (Optional) Add persona-specific heuristic in `_analyse_by_persona()`

### Adding a new file parser

1. Add parser function in `processors/ingestion.py`
2. Route by file extension in `ingest_file()`
3. Return `IngestedDocument` with proper metadata
