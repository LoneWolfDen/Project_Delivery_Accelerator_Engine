# Getting Started

Quick guide to set up and run the Project Delivery Accelerator Engine.

---

## Prerequisites

- Python 3.9+
- (Optional) [Ollama](https://ollama.ai) for local AI models
- (Optional) AWS credentials for Bedrock
- (Optional) Gemini API key for Google Gemini Pro

## Installation

```bash
# Clone the repo
git clone https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine.git
cd Project_Delivery_Accelerator_Engine

# Install (editable mode for development)
pip install -e .

# Install with AI backends
pip install -e ".[ai]"

# Install dev tools (pytest, ruff)
pip install -e ".[dev]"
```

## Configure AI Backends

Set up at least one backend (or use `files_only` for no-AI mode):

```bash
# Google Gemini (recommended – fast, high quality)
export GEMINI_API_KEY="your-gemini-api-key"

# Ollama (local, offline)
# Ensure ollama is running: ollama serve
# Pull a model: ollama pull llama3.2

# AWS Bedrock
# Configure via: aws configure
```

Check which backends are available:

```bash
python cli.py backends
```

---

## Quick Start (CLI)

### 1. Create a project

```bash
python cli.py create "My Migration Project" -d "Cloud migration assessment"
```

### 2. Ingest documents

```bash
python cli.py ingest proj-001 docs/sow.txt docs/proposal.md data/risks.csv
```

Supported formats: `.txt`, `.md`, `.csv`, `.eml` (email), transcript files.

### 3. Build intelligence

```bash
python cli.py build proj-001 -l "initial-assessment"
```

### 4. Run a persona review

```bash
# Files-only (instant, no AI)
python cli.py review proj-001 solution_architect

# With Gemini AI
python cli.py review proj-001 delivery_manager -b gemini

# With custom context
python cli.py review proj-001 product_owner -b gemini \
  -c "Budget is fixed at 500K. Team has 3 senior devs and 1 junior."

# Show the exact prompt sent to AI
python cli.py review proj-001 resource_manager -b gemini --show-prompt
```

### 5. View results

```bash
# Project status
python cli.py status proj-001

# Review history
python cli.py reviews proj-001

# Compare context versions
python cli.py compare proj-001 v1 v2

# Track risk evolution
python cli.py evolution proj-001 risks
```

### 6. Export

```bash
python cli.py export proj-001 all -f markdown
python cli.py export proj-001 intelligence -f json -o output.json
```

---

## Quick Start (API Server)

```bash
python server.py
# Server starts at http://localhost:8080
```

### Create a project

```bash
curl -X POST http://localhost:8080/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "description": "Assessment"}'
```

### Ingest files

```bash
curl -X POST http://localhost:8080/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj-001", "file_paths": ["sample_data/scope.txt"]}'
```

### Build intelligence

```bash
curl -X POST http://localhost:8080/api/projects/proj-001/build-context \
  -H "Content-Type: application/json" \
  -d '{"label": "initial"}'
```

### Run a review

```bash
curl -X POST http://localhost:8080/api/review \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-001",
    "persona": "solution_architect",
    "ai_backend": "gemini",
    "custom_prompt": "Consider we must be PCI-DSS compliant"
  }'
```

### List backends

```bash
curl http://localhost:8080/api/backends
```

---

## Available Personas

| ID | Role | Focus |
|----|------|-------|
| `solution_architect` | Solution Architect | Architecture gaps, design risks, technology alignment |
| `delivery_manager` | Delivery Manager | Execution risks, timelines, dependencies |
| `product_owner` | Product Owner | Scope clarity, backlog quality, value alignment |
| `resource_manager` | Resource Manager | Skill gaps, allocation risks, team composition |

---

## Project Lifecycle

```
Discovery → Proposal → Planning → Execution → Review
```

Transition phases via CLI:

```bash
python cli.py phase transition proj-001 proposal -r "Discovery complete, moving to proposal"
python cli.py phase history proj-001
```

---

## Next Steps

- See [API Reference](./api-reference.md) for full endpoint documentation
- See [Architecture](./architecture.md) for system design details
