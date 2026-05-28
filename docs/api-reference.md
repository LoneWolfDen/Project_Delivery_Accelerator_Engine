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
    {"name": "gemini", "display_name": "Google Gemini (gemini-2.0-flash)", "available": true},
    {"name": "groq", "display_name": "Groq (llama-3.3-70b-versatile)", "available": true},
    {"name": "openrouter", "display_name": "OpenRouter (free)", "available": true}
  ]
}
```

---

## Projects

### `GET /api/projects`

List all projects.

### `POST /api/projects`

Create a new project.

**Request Body:**
```json
{"name": "Project Name", "description": "Optional description"}
```

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

---

## Intelligence

### `POST /api/projects/{id}/build-context`

Build intelligence from ingested documents.

### `GET /api/projects/{id}/intelligence`

Get built intelligence.

### `GET /api/projects/{id}/summary`

Get token-efficient text summary.

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
  "ai_backend": "groq",
  "custom_prompt": "Consider we must use only AWS services and have a 500K budget cap"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | string | yes | Target project |
| `persona` | string | yes | Persona ID (`solution_architect`, `delivery_manager`, `product_owner`, `resource_manager`) |
| `ai_backend` | string | no | `files_only` (default), `ollama`, `bedrock`, `gemini`, `groq`, `openrouter` |
| `custom_prompt` | string | no | Additional context/instructions for the AI to consider |

**Response includes:**
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

---

## Versions & Comparison

### `GET /api/projects/{id}/versions`

List all context build versions.

### `POST /api/projects/{id}/compare-versions`

**Request Body:** `{"version_a": "v1", "version_b": "v2"}`

### `POST /api/projects/{id}/compare-reviews`

**Request Body:** `{"review_a": "filename_a.json", "review_b": "filename_b.json"}`

### `GET /api/projects/{id}/evolution/{category}`

Get evolution timeline (`risks`, `assumptions`, `dependencies`, `constraints`, `action_items`).

---

## Proposals

### `POST /api/projects/{id}/proposal`

Create a proposal.

### `POST /api/projects/{id}/proposal/version`

Add a new version.

### `GET /api/projects/{id}/proposal`

Get proposal details.

---

## Phases

### `POST /api/projects/{id}/phase`

Transition project to new phase.

**Request Body:** `{"new_phase": "proposal", "reason": "Discovery complete"}`

Valid phases: `discovery`, `proposal`, `planning`, `execution`, `review`

### `GET /api/projects/{id}/phase-history`

Get phase transition history.
