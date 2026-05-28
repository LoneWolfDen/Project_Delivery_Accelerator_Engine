# Project Delivery Accelerator Engine (v2)

A **context-aware delivery intelligence platform** that helps teams move from **pre-sales → proposal → delivery → review** using structured AI workflows.

This platform converts **documents, discussions, and decisions into reusable project intelligence**, enabling better planning, faster reviews, and consistent delivery outcomes.

Runs locally. Supports multiple AI backends. Preserves project memory across iterations.

---

## What This Product Does

### 1. Turn documents into structured project context

- Upload SoW, proposals, transcripts, pricing sheets, diagrams
- Automatically extract:
  - Scope
  - Risks
  - Assumptions
  - Dependencies
  - Resource needs
- Store as reusable project intelligence

### 2. Enable persona-driven reviews (out-of-the-box)

Run structured analysis using different roles:

- **Solution Architect** → Architecture gaps, design risks
- **Delivery Manager** → Execution risks, timelines, dependencies
- **Product Owner** → Scope clarity, backlog quality
- **Resource Manager** → Skill gaps, allocation risk

Each persona uses a pre-defined prompt + format, so users do not need to write prompts.

### 3. Support multi-version pre-sales proposals

- Store multiple proposal versions per project
- Track:
  - What changed
  - What risks increased/decreased
  - What assumptions evolved
- Reuse past insights instead of restarting analysis

### 4. Act as a default entry point for SDLC

From first discussion to delivery:

```
Discovery → Proposal → SoW review → Planning → Execution → Review
```

The system:

- Carries forward context
- Avoids repeated document parsing
- Maintains continuity across phases

### 5. Optimise AI usage and cost (token discipline built-in)

- Only loads **minimum required context** per request
- Uses:
  - Structured extraction instead of long text
  - Summaries + evidence separation
- Supports:
  - Local models (Ollama)
  - Cloud models (AWS Bedrock)
  - Files-only analysis mode

---

## Core Concept

Instead of asking AI every time from scratch:

- Build a **project memory**
- Store **intermediate findings**
- Reuse them intelligently

Result:

- Faster responses
- Lower token usage
- More consistent outputs

---

## Key Features

### Project Management

- Up to 5 active projects (local)
- Each project has:
  - Files
  - Settings
  - AI configuration
  - Historical outputs

### Context Builder

- Converts uploaded files into:
  - Structured context packs
  - Extracted facts and constraints
  - Summarised sections

### Persona Review Engine

- Runs reviews using predefined personas
- Generates:
  - Risks
  - Assumptions
  - Gaps
  - Recommendations
  - Questions to resolve

### Iteration & History

- Save outputs from each run
- Compare results across versions
- See impact of changes

### AI Flexibility

| Mode        | Description                 |
| ----------- | --------------------------- |
| Ollama      | Local models, fully offline |
| AWS Bedrock | Scalable cloud models       |
| Files-only  | No AI, raw evidence view    |

---

## Architecture

```
[ Uploaded Files ]
        |
[ Ingestion Layer ]
        |
[ Context Builder ]
        |
[ Project Memory (JSON) ]
        |
[ Persona Engine ]
        |
[ API / Outputs ]
```

---

## Project Structure

```
project-accelerator/
├── README.md                       # This file
├── pyproject.toml                   # Project config and dependencies
├── server.py                        # Main API server
├── project_manager.py               # Project persistence & file management
├── processors/
│   ├── ingestion.py                 # File parsing (SoW, transcripts, CSVs)
│   └── context_builder.py           # Structured context extraction
├── personas/
│   ├── engine.py                    # Persona review engine
│   └── definitions/                 # Persona configs (YAML)
│       ├── solution_architect.yaml
│       ├── delivery_manager.yaml
│       ├── product_owner.yaml
│       └── resource_manager.yaml
├── models/
│   └── project.py                   # Core data models
├── sample_data/                     # Example input files for testing
├── outputs/                         # Generated results (gitignored)
├── docs/                            # Specs, reference documentation
├── tests/                           # Test suite
└── _archive/                        # Legacy migration demo (reference only)
```

---

## How It Works (User Flow)

1. Create or select a project
2. Upload documents
3. Build context automatically
4. Choose a persona (e.g. Delivery Manager)
5. Run analysis
6. Review outputs
7. Save and iterate

---

## Setup

### Prerequisites

- Python 3.9+
- (Optional) Ollama for local AI
- (Optional) AWS credentials for Bedrock

### Install

```bash
pip install -e .
```

### Run

```bash
python server.py
```

Server starts at `http://localhost:8080`

### API Endpoints

| Method | Path            | Description              |
| ------ | --------------- | ------------------------ |
| GET    | /api/health     | Health check             |
| GET    | /api/projects   | List projects            |
| POST   | /api/projects   | Create project           |
| POST   | /api/ingest     | Upload and ingest files  |
| POST   | /api/review     | Run persona review       |

---

## What Makes This Different

Typical tools:

- Chat-based
- Stateless
- Repetitive

This platform:

- Context-aware
- Stateful
- Version-controlled
- Persona-driven

---

## Roadmap

### v2 (In progress)

- Context packs
- Persona system
- Iteration history
- Structured outputs

### v3

- Diagram generation (.drawio)
- Proposal auto-drafts
- Export to Word / PowerPoint
- Pre-sales → delivery feedback loop

### v4 (Vision)

- Multi-project intelligence
- Cross-project learning
- Delivery benchmarking
- Copilot-style assistant layer

---

## End Goal

Create a **standard operating system for delivery teams**, where:

- AI provides structure, not just answers
- Humans refine, not reinvent
- Projects build on past intelligence, not restart

---

## Positioning

> **Context Operating System for Delivery**

Not a dashboard with AI. A platform that builds, stores, and reuses delivery intelligence.
