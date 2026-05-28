# API Reference

The server runs on `http://localhost:8080` by default.

All endpoints return JSON. POST endpoints accept JSON request bodies.

---

## Health & Info

### `GET /api/health`

Health check.

**Response:**
```json
{"status": "ok", "version": "3.0.0-ui"}
```

### `GET /api/backends`

List available AI backends and their configuration status.

**Response:**
```json
{
  "backends": [
    {"name": "files_only", "display_name": "Files Only (No AI)", "available": true},
    {"name": "ollama", "display_name": "Ollama (llama3.2)", "available": false},
    {"name": "bedrock", "display_name": "AWS Bedrock (anthropic.claude-3-haiku)", "available": false},
    {"name": "gemini", "display_name": "Google Gemini (gemini-2.0-flash)", "available": true}
  ]
}
```

---

## Projects

### `GET /api/projects`

List all projects.

**Response:**
```json
{
  "projects": [
    {"id": "proj-001", "name": "My Project", "phase": "discovery", "file_count": 3}
  ]
}
```

### `POST /api/projects`

Create a new project.

**Request Body:**
```json
{"name": "Project Name", "description": "Optional description"}
```

**Response (201):**
```json
{"project": {"id": "proj-001", "name": "Project Name", ...}}
```

**Errors:**
- `409` – Maximum 5 active projects reached

---

## Ingestion

### `POST /api/ingest`

Ingest files into a project's context store.

**Request Body:**
```json
{
  "project_id": "proj-001",
  "file_paths": ["path/to/sow.txt", "path/to/risks.csv"]
}
```

**Response:**
```json
{
  "ingested": 2,
  "errors": [],
  "documents": [
    {"filename": "sow.txt", "source_type": "sow", "sections": 5, "word_count": 302, "is_valid": true}
  ]
}
```

---

## Intelligence

### `POST /api/projects/{id}/build-context`

Build intelligence from ingested documents. Creates a versioned snapshot.

**Request Body (optional):**
```json
{"label": "post-discovery"}
```

**Response:**
```json
{
  "scope": "...",
  "risks": [...],
  "assumptions": [...],
  "dependencies": [...],
  "constraints": [...],
  "action_items": [...],
  "_build_metadata": {"document_count": 3, "total_risks": 5, ...},
  "_version": {"version_id": "v1", "version_number": 1, "label": "post-discovery", ...}
}
```

### `GET /api/projects/{id}/intelligence`

Get built intelligence for a project.

### `GET /api/projects/{id}/summary`

Get a token-efficient text summary of project intelligence.

### `GET /api/projects/{id}/context`

Get all raw ingested documents.

---

## Reviews

### `POST /api/review`

Run a persona-driven review.

**Request Body:**
```json
{
  "project_id": "proj-001",
  "persona": "solution_architect",
  "ai_backend": "gemini",
  "custom_prompt": "Consider we must use only AWS services and have a 500K budget cap"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | yes | Target project |
| `persona` | string | yes | Persona ID (`solution_architect`, `delivery_manager`, `product_owner`, `resource_manager`) |
| `ai_backend` | string | no | `files_only` (default), `ollama`, `bedrock`, `gemini` |
| `custom_prompt` | string | no | Additional context/instructions for the AI to consider |

**Response:**
```json
{
  "persona": "Solution Architect",
  "persona_id": "solution_architect",
  "timestamp": "2025-01-15T10:30:00+00:00",
  "ai_backend": "gemini",
  "findings": {
    "risks": ["..."],
    "design_gaps": ["..."],
    "recommendations": ["..."],
    "questions": ["..."]
  },
  "summary": "Solution Architect review: 12 findings across 4 categories",
  "recommendations": ["..."],
  "questions": ["..."],
  "prompt_used": "# Role: Solution Architect\n...",
  "custom_prompt": "Consider we must use only AWS services...",
  "raw_output": "Full AI response text...",
  "ai_metadata": {
    "text": "...",
    "model": "gemini-2.0-flash",
    "backend": "gemini",
    "tokens_used": 1234,
    "latency_ms": 2500.0,
    "success": true
  }
}
```

**Key response fields:**
- `prompt_used` – The exact prompt sent to the AI (always populated)
- `custom_prompt` – The user's additional context (echoed back)
- `raw_output` – Raw AI text response (null for files_only mode)
- `ai_metadata` – Token usage, latency, model info (only for AI backends)

### `GET /api/projects/{id}/reviews?persona=solution_architect`

Get review history, optionally filtered by persona.

---

## Personas

### `POST /api/personas`

List available personas.

**Response:**
```json
{
  "personas": [
    {"id": "solution_architect", "name": "Solution Architect", "role": "Reviews architecture gaps..."}
  ]
}
```

---

## Versions & Comparison

### `GET /api/projects/{id}/versions`

List all context build versions.

### `GET /api/projects/{id}/versions/{version_id}`

Get a specific version snapshot.

### `POST /api/projects/{id}/compare-versions`

Compare two context versions.

**Request Body:**
```json
{"version_a": "v1", "version_b": "v2"}
```

### `POST /api/projects/{id}/compare-reviews`

Compare two review results.

**Request Body:**
```json
{"review_a": "solution_architect_2025-01-15T10-30-00.json", "review_b": "solution_architect_2025-01-16T10-30-00.json"}
```

### `GET /api/projects/{id}/evolution/{category}`

Get evolution timeline for a category (`risks`, `assumptions`, `dependencies`, `constraints`, `action_items`).

---

## Proposals

### `POST /api/projects/{id}/proposal`

Create a proposal.

**Request Body:**
```json
{"name": "Cloud Migration Proposal", "client": "Acme Corp", "notes": "Initial draft"}
```

### `POST /api/projects/{id}/proposal/version`

Add a new version to existing proposal.

**Request Body:**
```json
{"label": "v2 - revised scope", "notes": "Reduced to phase 1 only", "changes": "Removed phase 2 deliverables"}
```

### `GET /api/projects/{id}/proposal`

Get proposal details.

---

## Phases

### `POST /api/projects/{id}/phase`

Transition project to new SDLC phase.

**Request Body:**
```json
{"new_phase": "proposal", "reason": "Discovery complete"}
```

Valid phases: `discovery`, `proposal`, `planning`, `execution`, `review`

### `GET /api/projects/{id}/phase-history`

Get phase transition history.

---

## CORS

All endpoints include `Access-Control-Allow-Origin: *` headers.
Preflight (`OPTIONS`) is supported.
