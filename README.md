# Project Delivery Accelerator Engine

> **Context-aware delivery intelligence for non-technical teams.**  
> Convert SoWs, proposals, and meeting notes into structured intelligence — then apply persona-driven review to catch every PM blind spot before it becomes a problem.

[![CI](https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine/actions/workflows/ci.yml/badge.svg)](https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What it does

Most delivery teams review proposals and SoWs the same way every time: one person reads through, flags a few things they happen to notice, and the team moves on. Entire dimensions — governance, change management, commercial risk, key-person dependencies — go unchecked because no single person holds every lens simultaneously.

This platform solves that by:

1. **Extracting structured intelligence** from your documents (risks, assumptions, dependencies, constraints, action items, scope)
2. **Running persona-driven reviews** that apply a specific professional lens — Solution Architect, Delivery Manager, Product Owner, Resource Manager — each with its own focus areas and PM coverage dimensions
3. **Tracking every version** so you can see how your risk profile changes as the proposal evolves
4. **Running a Deep Dive** that surfaces missing areas, risk flags, and clarification questions your team needs to resolve before committing

Everything runs in a single Docker container. No database. No external services required. Fully offline-capable.

---

## Screenshots

> _Screenshots will be added here. To contribute screenshots, run the app locally and capture the Dashboard, Review Detail (coverage assessment), and Deep Dive views._

---

## Quick Start

### First-run checklist

Use these steps in order for a clean local setup.

#### 1. Install dependencies

```bash
cd /path/to/Project_Delivery_Accelerator_Engine
pip install -e .
```

#### 2. Set a local admin PIN

For a local/dev machine, any non-empty value is fine. This is only required for archive/delete actions.

```bash
export ADMIN_PIN=dev-pin-1234
```

> You do not need a production-grade PIN for local testing, and there is no critical data in the repo by default.

#### 3. Seed the demo/test projects

The UI does not show the sample projects until the database has been created.

```bash
python scripts/seed_sqlite.py
```

This creates demo projects such as:

- `proj-test-001` — Cloud Platform Migration (Test)
- `proj-test-002` — Digital Transformation Programme (Test)

#### 4. Start the app with the same data directory

```bash
export PROJECTS_DATA_DIR="$PWD/projects_data"
python server.py
```

Then open:

- http://localhost:8080
- or http://localhost:8080/?ui=v2

#### 5. Verify the projects are visible

```bash
curl http://localhost:8080/api/projects
```

You should see JSON including the seeded project IDs.

If you do not see any projects, the usual cause is that the app started in a different data folder than the one used to seed the database.

### Reset demo data

```bash
rm -rf projects_data
mkdir -p projects_data
export ADMIN_PIN=dev-pin-1234
python scripts/seed_sqlite.py
```

### Troubleshooting: no test projects in the UI

If the project list is empty, check these in order:

```bash
# 1. Confirm the database was seeded
ls -la projects_data

# 2. Confirm the data file exists
ls -la projects_data/accelerator.db

# 3. Confirm current env points to the same folder
echo "$PROJECTS_DATA_DIR"

# 4. Confirm the app is returning project data
curl http://localhost:8080/api/projects
```

Common fixes:

- If the API returns an empty list, start the app with the same `PROJECTS_DATA_DIR` used during seeding.
- If you started the app before seeding, stop it and re-run:

```bash
export ADMIN_PIN=dev-pin-1234
export PROJECTS_DATA_DIR="$PWD/projects_data"
python scripts/seed_sqlite.py
python server.py
```

- If you are using Docker or a different machine, make sure the mounted volume points to the same `/data` or `projects_data` location.
- If you are prompted for a PIN during archive/delete, set it again in the terminal before starting the app:

```bash
export ADMIN_PIN=dev-pin-1234
```

---

### Docker option

```bash
docker run -d \
  --name delivery-accelerator \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e ADMIN_PIN=your-secure-pin \
  delivery-accelerator
```

Then open http://localhost:8080.

---

## User Workflow

```
  ┌─────────────────────────────────────────────────────────┐
  │  1  Add Documents                                        │
  │     Upload files or paste text in the Ingest tab        │
  │     .txt  .md  .csv  .eml  .json  .yaml  .pdf  .docx    │
  └────────────────────────┬────────────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────────────┐
  │  2  Analyse Documents                                    │
  │     Extract: risks · assumptions · dependencies          │
  │              constraints · action items · scope          │
  │     Each run creates a versioned snapshot                │
  └────────────────────────┬────────────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────────────┐
  │  3  Run a Review                                         │
  │     Choose a Review Role  ──►  Solution Architect        │
  │     Choose an AI Model         Delivery Manager          │
  │     Add optional context       Product Owner             │
  │                                Resource Manager          │
  └────────────────────────┬────────────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────────────┐
  │  4  Review the Output                                    │
  │     · PM Coverage Assessment  (persona-aware, 10–12 dims)│
  │     · Findings per category                              │
  │     · Open questions to resolve                          │
  │     · Files included                                     │
  └────────────────────────┬────────────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────────────┐
  │  5  Compare & Iterate                                    │
  │     Add more documents → rebuild → re-run reviews        │
  │     Versions tab: full Phase → Version → Review history  │
  └─────────────────────────────────────────────────────────┘
```

---

## Review Roles (Personas)

Each persona applies a distinct professional lens with its own PM coverage dimensions:

| Role | Focus | Coverage Dimensions |
|------|-------|---------------------|
| **Solution Architect** | Architecture gaps, technology choices, integration risks, NFRs | Architecture & Design, NFRs, Tech Choices, Security Architecture, Integration & APIs, Data & Storage |
| **Delivery Manager** | Execution risks, timeline feasibility, dependencies, scope control | Execution Plan, Scope Control, Resource & Capacity, Quality & Testing, Reporting & RAG, Change Management |
| **Product Owner** | Scope clarity, requirements quality, business value, user needs | Scope Definition, Requirements Quality, Business Value & ROI, User Needs & UX, Prioritisation, Commercials |
| **Resource Manager** | Skill gaps, allocation conflicts, capacity planning, key-person risk | Skills & Capability, Allocation & Conflicts, Capacity Planning, Onboarding & Ramp, Key-Person Risk, Contractors & Vendors |

All personas also assess 6 **baseline dimensions** present in every review: Risk Management, Timeline & Schedule, Budget & Cost, Stakeholders, Dependencies, and Governance & Compliance.

---

## PM Coverage Assessment

Every Review Full Details page shows a **Coverage Assessment** specific to the persona used:

```
📊 Coverage Assessment for Solution Architect      8/12 areas covered
████████████████████████░░░░░░░░  67%

✓ Risk Management    ✓ Architecture & Design    ✓ Security Architecture
✓ NFRs               ✓ Integration & APIs       ✓ Stakeholders
✓ Dependencies       ✓ Governance & Compliance
○ Timeline & Schedule   ○ Budget & Cost   ○ Tech Choices   ○ Data & Storage

⬆️ Consider adding context on: Timeline & Schedule, Budget & Cost, Tech Choices
```

Coverage expands as AI models mature and more document context is provided.

---

## AI Backends

The platform is fully operational without any AI key — `Files Only` mode gives instant, deterministic, heuristic-based analysis.

| Backend | Requirement | Notes |
|---------|-------------|-------|
| **Files Only** | Nothing | Default. Instant, deterministic, fully offline |
| **Groq** | `GROQ_API_KEY` | Free tier. Fast. Recommended for teams getting started |
| **OpenRouter** | `OPENROUTER_API_KEY` | Free tier. Access to 300+ models |
| **Gemini** | `GEMINI_API_KEY` | Google Gemini 2.0 Flash |
| **Ollama** | Ollama running locally | Fully offline AI — run any open model |
| **AWS Bedrock** | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | Claude, pay-per-use |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_PIN` | **Yes** (for archive/delete) | _(none)_ | PIN for destructive operations. For local development you can safely set a temporary value such as `dev-pin-1234`. |
| `PROJECTS_DATA_DIR` | No | `projects_data/` | Override data directory (e.g. Docker volume mount) |
| `HOST` | No | `localhost` | Server bind address |
| `PORT` | No | `8080` | Server port |
| `APP_NAME` | No | `Project Delivery Accelerator Engine` | Displayed in UI header and health endpoint |
| `GROQ_API_KEY` | No | _(none)_ | Enables Groq AI backend |
| `OPENROUTER_API_KEY` | No | _(none)_ | Enables OpenRouter AI backend |
| `GEMINI_API_KEY` | No | _(none)_ | Enables Gemini AI backend |
| `AWS_ACCESS_KEY_ID` | No | _(none)_ | Enables AWS Bedrock backend |
| `AWS_SECRET_ACCESS_KEY` | No | _(none)_ | Required with `AWS_ACCESS_KEY_ID` |

A simple example for local testing:

```bash
export ADMIN_PIN=dev-pin-1234
export PROJECTS_DATA_DIR="$PWD/projects_data"
python server.py
```

---

## Docker Compose Example

```yaml
# docker-compose.yml
services:
  delivery-accelerator:
    image: delivery-accelerator:latest
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    environment:
      - ADMIN_PIN=${ADMIN_PIN}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - PROJECTS_DATA_DIR=/data
    restart: unless-stopped
```

```bash
# .env
ADMIN_PIN=your-secure-pin
GROQ_API_KEY=gsk_...
```

```bash
docker compose up -d
```

---

## Project Structure

```
Project_Delivery_Accelerator_Engine/
├── server.py               # HTTP API server + static file serving
├── project_manager.py      # Orchestration: project CRUD + business logic
├── cli.py                  # CLI (13+ commands)
├── Dockerfile
├── pyproject.toml
│
├── admin/                  # Config, guardrails, health, lifecycle
├── ai_backends/            # Pluggable AI adapters (files_only, groq, etc.)
├── models/                 # Dataclasses: Project, Artifact, Hierarchy, etc.
├── personas/
│   ├── engine.py           # Review orchestration
│   ├── deep_dive.py        # Gap analysis engine
│   └── definitions/        # Persona YAML configs
├── processors/
│   ├── ingestion.py        # File parsing
│   ├── context_builder.py  # Intelligence extraction + aggregation
│   ├── history.py          # Version snapshots
│   ├── artifact_store.py   # Artifact registry
│   └── extractors/         # Pattern-based extraction
│
├── static/
│   └── index.html          # Single-file SPA (vanilla JS, no build step)
│
├── sample_data/            # Example inputs for testing
├── docs/                   # API reference, architecture docs
└── tests/                  # 180+ tests (pytest)
```

---

## API Reference

Full API documentation: [`docs/api-reference.md`](docs/api-reference.md)

Key endpoints:

```
GET  /api/health                              Health check + version
GET  /api/projects                            List active projects
POST /api/projects                            Create project
POST /api/v1/projects/{id}/artifacts/upload   Upload a file
POST /api/v1/projects/{id}/artifacts/text     Add pasted text
POST /api/projects/{id}/build-context         Analyse documents
POST /api/review                              Run persona review
GET  /api/projects/{id}/hierarchy             Full Phase→Version→Review tree
POST /api/projects/{id}/compare-versions      Diff two versions
GET  /api/projects/{id}/hierarchy/reviews/{id} Review full detail
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to add a new persona (YAML + engine + coverage dimensions)
- How to add a new AI backend (adapter class + registry)
- Dev setup, test commands, and coding standards
- PR checklist

---

## Roadmap

| Version | Status | Focus |
|---------|--------|-------|
| **v2** | ✅ Done | Context packs, persona engine, 180 tests |
| **v3** | ✅ Done | Hierarchy model, Deep Dive, Admin, UI/UX, Docker |
| **v3.3** | ✅ Current | Persona-aware coverage, Deep Dive UX, open-source ready |
| **v4** | 🔜 Planned | PDF/DOCX ingestion, AI-powered extraction, diagram generation, export to Word/PPTX |
| **v5** | 💭 Vision | Multi-project intelligence, RAG pipeline, copilot assistant |

---

## License

MIT — see [LICENSE](LICENSE) for details.
