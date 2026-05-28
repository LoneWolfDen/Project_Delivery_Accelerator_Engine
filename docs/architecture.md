# Architecture

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
└────────┬─────────┬────────────────┬─────────────────────────────┘
         │         │                │
         ▼         ▼                ▼
┌────────────┐ ┌──────────────┐ ┌──────────────────────────┐
│ Processors │ │   Personas   │ │      AI Backends          │
│            │ │              │ │                            │
│ ingestion  │ │ engine.py    │ │ files_only (heuristic)    │
│ context_   │ │ definitions/ │ │ groq (free, fast)         │
│   builder  │ │  *.yaml      │ │ openrouter (free, multi)  │
│ history    │ │              │ │ gemini (Google)            │
│ proposals  │ │              │ │ ollama (local)             │
│ phases     │ │              │ │ bedrock (AWS)              │
│ extractors │ │              │ │                            │
└────────────┘ └──────────────┘ └──────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer (JSON files)                      │
│  projects_data/{project_id}/                                     │
│  ├── context/   ├── reviews/   ├── versions/                    │
│  ├── intelligence.json   └── proposal.json                       │
└─────────────────────────────────────────────────────────────────┘
```

## AI Backend Architecture

Pluggable adapter pattern — all backends implement the same interface:

```python
from ai_backends import get_backend

backend = get_backend("groq")  # or "openrouter", "gemini", etc.
response = backend.generate(prompt, system_prompt="...")
# Returns AIResponse(text, model, tokens_used, latency_ms, success, error)
```

Graceful fallback: if any AI backend fails, the system falls back to `files_only`
heuristic analysis and reports the fallback in the response.

## Extension Points

### Adding a new AI backend

1. Create `ai_backends/my_backend.py` extending `AIBackend`
2. Implement `generate()`, `is_available()`, `name`, `display_name`
3. Register in `ai_backends/registry.py`
4. Add to `VALID_BACKENDS` in `personas/engine.py`

### Adding a new persona

1. Create `personas/definitions/my_persona.yaml`
2. Add entry to `AVAILABLE_PERSONAS` in `personas/engine.py`
