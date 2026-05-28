# Getting Started

Quick guide to set up and run the Project Delivery Accelerator Engine.

---

## Prerequisites

- Python 3.9+
- (Optional) Free API key from Groq or OpenRouter for AI-powered reviews

## Installation

```bash
git clone https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine.git
cd Project_Delivery_Accelerator_Engine
pip install -e .
```

## Configure AI Backends (Pick One)

### Groq (Recommended – free, fast)

1. Sign up at https://console.groq.com (no credit card)
2. Create an API key
3. `export GROQ_API_KEY="gsk_..."`

### OpenRouter (Free tier, many models)

1. Sign up at https://openrouter.ai (free)
2. Create an API key
3. `export OPENROUTER_API_KEY="sk-or-..."`

### Other options

```bash
export GEMINI_API_KEY="..."     # Google Gemini
# Ollama: just run `ollama serve`
# Bedrock: `aws configure`
```

Check backend status:
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

### 3. Build intelligence

```bash
python cli.py build proj-001 -l "initial-assessment"
```

### 4. Run a persona review

```bash
# Files-only (instant, no AI)
python cli.py review proj-001 solution_architect

# With Groq AI (free)
python cli.py review proj-001 delivery_manager -b groq

# With custom context
python cli.py review proj-001 product_owner -b groq \
  -c "Budget is fixed at 500K. Team has 3 senior devs."

# Show the exact prompt sent to AI
python cli.py review proj-001 resource_manager -b groq --show-prompt
```

### 5. View results

```bash
python cli.py status proj-001
python cli.py reviews proj-001
python cli.py compare proj-001 v1 v2
python cli.py evolution proj-001 risks
```

### 6. Export

```bash
python cli.py export proj-001 all -f markdown
```

---

## Quick Start (API Server)

```bash
python server.py
# Server starts at http://localhost:8080
```

```bash
# Create project
curl -X POST http://localhost:8080/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project"}'

# Ingest
curl -X POST http://localhost:8080/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj-001", "file_paths": ["sample_data/scope.txt"]}'

# Build context
curl -X POST http://localhost:8080/api/projects/proj-001/build-context

# Review with Groq
curl -X POST http://localhost:8080/api/review \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj-001", "persona": "solution_architect", "ai_backend": "groq"}'
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

## Available AI Backends

| Backend | Cost | Speed | Setup |
|---------|------|-------|-------|
| `files_only` | Free | Instant | None |
| `groq` | Free tier | Very fast | API key from console.groq.com |
| `openrouter` | Free tier | Fast | API key from openrouter.ai |
| `gemini` | Free tier (limited) | Fast | API key from Google AI Studio |
| `ollama` | Free (local) | Depends on hardware | Install Ollama |
| `bedrock` | Pay per use | Fast | AWS credentials |

---

## Next Steps

- See [API Reference](./api-reference.md) for full endpoint documentation
- See [Architecture](./architecture.md) for system design details
