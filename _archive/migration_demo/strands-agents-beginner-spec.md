# Strands Agents — 101 Development Specification

> Target audience: developers who are new to Strands Agents but have basic Python knowledge.
> Examples are drawn from the MAP Migration Accelerator project.

---

## 1. What is Strands Agents?

Strands Agents is a Python SDK for building AI agents that can **reason, use tools, and coordinate with other agents**. Instead of writing procedural "call LLM → parse output → call API" code yourself, you define tools and hand them to an Agent. The Agent decides which tools to use, calls them, and builds its response — all in a loop.

Think of it like hiring a smart contractor: you tell them what tools they have and what job to do, and they figure out the steps.

---

## 2. Prerequisites & Setup

### Requirements

- Python 3.10 or higher
- AWS credentials configured (Strands uses Amazon Bedrock with Claude by default)

### Install packages

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install strands-agents
pip install strands-agents-tools   # community pre-built tools
```

**Configure AWS credentials** (one of these options)

```bash
# Option A — environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Option B — AWS CLI (recommended)
aws configure
```

### Default Model and Switching Providers

Strands uses **Amazon Bedrock with Claude Sonnet 4** as the default. No model config is needed if you have AWS credentials set up.

All examples below use `BedrockModel` — the same provider used in this project. Pick the model that matches the task:

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

# Amazon Nova Pro — general-purpose, cost-effective for most tasks
nova_agent = Agent(
    system_prompt="You are a migration analyst.",
    model=BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        temperature=0.3,
        streaming=True,
    ),
)

# Claude Sonnet 4 — stronger reasoning, good for strategy and planning
sonnet_agent = Agent(
    system_prompt="You are a senior cloud migration architect.",
    model=BedrockModel(
        model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        temperature=0.5,
        streaming=True,
    ),
)

# Claude Haiku — fastest and cheapest, ideal for classification and simple extraction
haiku_agent = Agent(
    system_prompt="Classify each app as legacy, modern, or unknown. Return JSON only.",
    model=BedrockModel(
        model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
        temperature=0.1,
        streaming=False,
    ),
)
```

**Key `BedrockModel` parameters:**

| Parameter | What it does |
| --- | --- |
| `model_id` | Which Bedrock model to invoke |
| `temperature` | Creativity vs. determinism (0.0 = precise, 1.0 = creative) |
| `streaming` | Stream tokens as they arrive (`True`) or wait for full response (`False`) |

**Choosing a model for the job:**

| Model | Best for |
| --- | --- |
| `nova-pro-v1:0` | General analysis, summaries, cost-sensitive workloads |
| `claude-sonnet-4` | Strategy, complex reasoning, structured output |
| `claude-haiku-4-5` | Classification, preprocessing, fast yes/no decisions |

> The MAP Migration Accelerator uses `BedrockModel` — see [utils/config.py](map-migration-accelerator/backend/utils/config.py) for `DEFAULT_MODEL_ID`.
> To use the direct Anthropic API or OpenAI instead, install `strands-agents[anthropic]` or `strands-agents[openai]` and swap in `AnthropicModel` / `OpenAIModel`.

---

## 3. Your First Agent

The minimum viable agent: import `Agent`, give it a prompt.

```python
from strands import Agent

agent = Agent()
agent("What are the 7 Rs of cloud migration?")
```

To give your agent tools and a focused role:

```python
from strands import Agent
from strands_tools import calculator, current_time

agent = Agent(
    system_prompt="You are a migration cost analyst. Be concise.",
    tools=[calculator, current_time],
)

agent("How many days until 2026-01-01? Today is 2025-06-01.")
```

**What just happened:**

1. The Agent received your question
2. It decided `current_time` and `calculator` were relevant
3. It called those tools and used the results to answer
4. You got a response

**Using two different models in the same workflow:**

Sometimes you want a cheap/fast model for simple tasks and a more capable model for complex reasoning. Pass a different `model=` to each agent:

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

# Nova Pro — cost-effective, handles classification and simple extraction well
classifier_agent = Agent(
    name="classifier",
    system_prompt="Classify each application as 'legacy', 'modern', or 'unknown'. Return JSON only.",
    model=BedrockModel(model_id="us.amazon.nova-pro-v1:0", temperature=0.1, streaming=True),
)

# Claude Sonnet — stronger reasoning for migration strategy
strategy_agent = Agent(
    name="strategist",
    system_prompt="You are a senior cloud migration architect. Produce a detailed migration strategy.",
    model=BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0", temperature=0.5, streaming=True),
)

# Run in sequence — classify first, then strategise on the result
classification = classifier_agent("PayrollSvc: Java 6, on-prem, 15 years old, no tests.")
strategy_agent(f"Build a migration strategy for this classification result: {classification}")
```

> Using a lighter model (Haiku) for preprocessing and a heavier model (Sonnet/Opus) for synthesis keeps costs low without sacrificing quality where it matters.

---

## 4. Multi-Agent Patterns

Use multiple agents when a task is too broad for one agent, or when you want to run work in parallel. Strands offers three patterns — pick the one that fits your task.

---

### Pattern A — Agent as a Tool (Simple Delegation)

Wrap one agent inside another. The outer agent calls the inner one like any other tool.

**When to use:** you have a specialist agent (e.g. an analyser) that a coordinator should be able to invoke on demand.

```python
from strands import Agent, tool
from strands_tools import calculator

# Specialist agent — knows about migration complexity
@tool
def run_complexity_check(app_name: str, dependency_count: int) -> str:
    """Assess migration complexity for a single application."""
    analyst = Agent(
        system_prompt="You are a migration complexity analyst. Score apps 1-100.",
        tools=[calculator],
    )
    result = analyst(
        f"App: {app_name}. Dependencies: {dependency_count}. Give a complexity score."
    )
    return str(result)

# Orchestrator agent — uses the specialist as a tool
orchestrator = Agent(
    system_prompt="You coordinate migration assessments.",
    tools=[run_complexity_check],
)

orchestrator("Check complexity for PayrollService which has 12 dependencies.")
```

> This is the simplest pattern. No extra imports needed beyond `strands`.

---

### Pattern B — Graph Workflow (Parallel or Sequential Nodes)

`GraphBuilder` lets you run multiple agents as **nodes in a graph**. Nodes with no dependency between them run **in parallel**. This is the most powerful pattern for complex pipelines.

**When to use:** you have independent sub-tasks that can run at the same time (e.g. analyse apps AND analyse infrastructure simultaneously), then feed results into a later step.

The MAP Migration Accelerator uses this exact pattern in [orchestrator_agent.py](map-migration-accelerator/backend/orchestrator_agent.py):

```python
# orchestrator_agent.py (simplified from the real project)
from strands import Agent
from strands.multiagent import GraphBuilder

# Two specialist agents — independent, can run in parallel
app_agent = Agent(
    name="app_analyst",
    system_prompt="Analyse application inventory and return JSON.",
)

infra_agent = Agent(
    name="infra_analyst",
    system_prompt="Analyse infrastructure inventory and return JSON.",
)

# Build the graph
builder = GraphBuilder()
builder.add_node(app_agent, "app_analysis")
builder.add_node(infra_agent, "infra_analysis")

# Both are entry points → they run in PARALLEL
builder.set_entry_point("app_analysis")
builder.set_entry_point("infra_analysis")

builder.set_execution_timeout(300)
graph = builder.build()

# Run and stream results
import asyncio

async def run():
    async for event in graph.stream_async("Analyse the data and return JSON."):
        event_type = event.get("type", "")

        if event_type == "multiagent_node_start":
            print(f"Started: {event.get('node_id')}")

        elif event_type == "multiagent_node_stop":
            node_id = event.get("node_id")
            result = event.get("node_result")
            print(f"Finished: {node_id} → {str(result)[:80]}")

asyncio.run(run())
```

**Key graph events to handle:**

| Event type | Meaning |
| --- | --- |
| `multiagent_node_start` | A node (agent) just started |
| `multiagent_node_stop` | A node finished — `node_result` has the output |
| `multiagent_graph_complete` | All nodes finished |

**Sequential nodes** (one feeds the next):

```python
builder.add_node(discovery_agent, "discovery")
builder.add_node(strategy_agent, "strategy")
builder.add_edge("discovery", "strategy")   # strategy runs AFTER discovery
builder.set_entry_point("discovery")
```

---

### Pattern C — Workflow (Structured Step-by-Step)

Workflow is a lighter alternative to Graph for strictly sequential pipelines. Each step's output is passed to the next step automatically.

**When to use:** you have a clear, ordered pipeline (Step 1 → Step 2 → Step 3) with no parallelism needed.

```python
from strands import Agent
from strands.multiagent import Workflow

# Define agents for each step
discovery_agent = Agent(
    name="discovery",
    system_prompt="Extract and structure application inventory data.",
)

strategy_agent = Agent(
    name="strategy",
    system_prompt="Given discovery output, recommend a migration strategy.",
)

wave_agent = Agent(
    name="wave_planner",
    system_prompt="Given a strategy, produce a wave-by-wave migration plan.",
)

# Chain them into a workflow
workflow = Workflow(agents=[discovery_agent, strategy_agent, wave_agent])

result = workflow.run("We have 40 applications to migrate to AWS.")
print(result)
```

> Each agent receives the previous agent's output as its input. Simple and readable.

**Graph vs Workflow — when to pick which:**

| | Graph | Workflow |
| --- | --- | --- |
| Parallel execution | Yes | No |
| Sequential execution | Yes (via edges) | Yes (built-in) |
| Complex routing | Yes | No |
| Simplicity | More setup | Less setup |
| Use in this project | `orchestrator_agent.py` | Single-pipeline tasks |

---

## 5. Using MCP Tools

**Model Context Protocol (MCP)** is an open standard that lets agents connect to external tool servers — AWS documentation, databases, file systems, APIs — without you writing the tools yourself. You point the agent at an MCP server and it discovers the available tools automatically.

### When to use MCP

Use MCP when you need tools that are already packaged as MCP servers (e.g. `awslabs.aws-documentation-mcp-server`) rather than writing them yourself. It's also the right choice when tools live in a separate process or remote service.

### Transport options

MCP servers communicate over two transports:

| Transport | Use when |
| --- | --- |
| **stdio** | Tool server runs as a local command-line process |
| **SSE** | Tool server is a running HTTP service |

### stdio — local process

```python
from strands import Agent
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp import MCPClient

# Connect to a locally installed MCP server via subprocess
mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command="uvx",
        args=["awslabs.aws-documentation-mcp-server@latest"],
    )
))

# Pass the client directly — Strands manages the connection lifecycle
agent = Agent(
    system_prompt="You are a migration analyst. Use AWS documentation to answer questions.",
    tools=[mcp_client],
)

agent("What are the best practices for migrating a Java app to AWS Lambda?")
```

### SSE — remote HTTP server

```python
from strands import Agent
from mcp.client.sse import sse_client
from strands.tools.mcp import MCPClient

# Connect to an MCP server already running at a URL
sse_mcp_client = MCPClient(lambda: sse_client("http://localhost:8000/sse"))

agent = Agent(
    system_prompt="You are a migration cost analyst.",
    tools=[sse_mcp_client],
)

agent("Estimate the monthly cost for running 3 t3.medium EC2 instances in us-east-1.")
```

### Combining MCP servers with custom tools

MCP clients and `@tool` functions can be mixed freely in the same `tools=` list:

```python
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from mcp.client.sse import sse_client

cost_mcp = MCPClient(lambda: sse_client("http://cost-service/sse"))

@tool
def get_app_count(inventory_json: str) -> int:
    """Return the total number of applications in an inventory JSON array."""
    import json
    return len(json.loads(inventory_json))

agent = Agent(
    system_prompt="You are a migration planner.",
    tools=[cost_mcp, get_app_count],   # MCP server + custom tool together
)
```

### Filtering tools from an MCP server

If a server exposes many tools, use `tool_filters` to keep only the ones you need:

```python
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

mcp_client = MCPClient(
    lambda: stdio_client(StdioServerParameters(command="uvx", args=["some-mcp-server"])),
    tool_filters=["search_docs", "get_pricing"],   # only expose these two tools
    prefix="aws",                                   # avoid name collisions: aws_search_docs
)
```

> Always use the managed form (`tools=[mcp_client]`) rather than manually calling `mcp_client.list_tools_sync()` — it handles connection open/close automatically.

---

## 6. Writing Your Own Tool

Any Python function decorated with `@tool` becomes a tool an agent can call.

### The minimum required structure

```python
from strands import Agent, tool

@tool
def count_high_risk_apps(apps_json: str, threshold: int) -> str:
    """Count applications with a risk score above the given threshold.

    Args:
        apps_json: JSON array of app objects, each with a 'risk_score' field.
        threshold: Integer score above which an app is considered high risk.

    Returns:
        A summary string with the count and app names.
    """
    import json
    apps = json.loads(apps_json)
    high_risk = [a["name"] for a in apps if a.get("risk_score", 0) > threshold]
    return f"{len(high_risk)} high-risk apps: {', '.join(high_risk)}"

agent = Agent(
    system_prompt="You are a migration risk reviewer.",
    tools=[count_high_risk_apps],
)

agent("From this list, count apps with risk above 70: [{'name':'PayrollSvc','risk_score':85}, {'name':'WebFrontend','risk_score':30}]")
```

The `discovery_agent.py` in this project follows this pattern — see [discovery_agent.py:149-186](map-migration-accelerator/backend/discovery_agent.py#L149-L186).

### Best practices

**1. Docstring = the tool's interface**
The first paragraph becomes the tool's description. The `Args:` block describes each parameter. The agent reads both to decide when and how to call the tool. Vague docstrings produce unpredictable tool use.

```python
# BAD — agent cannot tell what this does or what to pass
@tool
def analyse(data: str) -> str:
    """Analyse data."""
    ...

# GOOD — agent knows exactly when to use it and what to pass
@tool
def analyse_app_risk(app_inventory_json: str) -> str:
    """Identify high-risk applications from an inventory JSON array.

    Args:
        app_inventory_json: JSON array where each item has 'name' and 'risk_score' fields.

    Returns:
        JSON array of high-risk app names with their scores.
    """
    ...
```

**2. Parameters = what the LLM should reason about**
Only put values in parameters that the agent should decide based on user input (search queries, thresholds, app names). Put fixed context — user IDs, API keys, session tokens — outside the tool, not as parameters.

```python
# BAD — agent should not receive or decide the API key
@tool
def fetch_migration_report(app_name: str, api_key: str) -> str: ...

# GOOD — api_key is fixed config, not an agent decision
API_KEY = os.environ["REPORT_API_KEY"]

@tool
def fetch_migration_report(app_name: str) -> str:
    """Fetch the latest migration report for a named application."""
    return requests.get(f"/reports/{app_name}", headers={"key": API_KEY}).text
```

**3. Return strings or JSON-serialisable values**
Tools can return strings, dicts, lists, numbers, or booleans — all are automatically converted. Return structured data (dicts/JSON strings) when the agent needs to reason over the result.

```python
# Returning a dict — agent can pick out specific fields
@tool
def get_app_details(app_name: str) -> dict:
    """Return metadata for a named application."""
    return {"name": app_name, "risk_score": 72, "type": "legacy", "wave": 2}
```

**4. Handle errors explicitly — don't let tools crash**
Unhandled exceptions become agent errors. Catch expected failures and return a descriptive string so the agent can react gracefully instead of stopping.

**5. Use `async` tools for I/O — they run concurrently**
If your tool makes network calls or reads files, make it `async`. Strands runs all async tools concurrently, which speeds up agents that call multiple I/O tools in one turn.

```python
import httpx

@tool
async def fetch_app_metadata(app_name: str) -> str:
    """Fetch live metadata for an application from the registry API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://registry.internal/apps/{app_name}")
        return response.text
```

---

## 7. What NOT to Do (Gotchas)

**1. Missing AWS credentials**
Strands defaults to Amazon Bedrock. If credentials are not configured, every `Agent()` call will fail with an auth error. Run `aws sts get-caller-identity` to verify before debugging your agent code.

**2. Missing type hints or docstring on `@tool`**

```python
# BAD — agent cannot understand what this does or what to pass
@tool
def analyse(data):
    return data.upper()

# GOOD
@tool
def analyse(data: str) -> str:
    """Convert analysis input to uppercase for testing."""
    return data.upper()
```

**3. Calling an async agent with `agent()` instead of `await`**

```python
# BAD — blocks the event loop or silently does nothing in async context
result = agent("analyse this")

# GOOD — in an async function
async for event in agent.stream_async("analyse this"):
    if "data" in event:
        print(event["data"])
```

See how `strategy_agent.py` uses `stream_async` correctly: [strategy_agent.py:55](map-migration-accelerator/backend/strategy_agent.py#L55).

**4. Putting logic in the system prompt instead of tools**
If your agent needs to parse a CSV, compute scores, or call an API — put that in a `@tool`, not in the system prompt. The system prompt should describe the agent's role, not encode business logic. Long, logic-heavy prompts are fragile and hard to test.

**5. Building a Graph when you just need one agent**
Start with a single `Agent`. Only reach for `GraphBuilder` or `Workflow` when you have a genuine reason to split work (parallelism, specialisation, reuse). Unnecessary multi-agent setups add latency and complexity.

---

## 8. Quick Reference Card

```bash
# Install
pip install strands-agents strands-agents-tools
pip install 'strands-agents[anthropic]'   # only if using direct Anthropic API
pip install 'strands-agents[openai]'      # only if using OpenAI
```

```python
# Core imports
from strands import Agent, tool
from strands_tools import calculator, current_time, file_read, http_request

# Simplest agent (uses Bedrock + Claude Sonnet by default)
agent = Agent()
agent("Your prompt here")

# Agent with tools and role
agent = Agent(
    system_prompt="You are a migration analyst.",
    tools=[calculator, current_time],
)

# Model swap
from strands.models.bedrock import BedrockModel
from strands.models.anthropic import AnthropicModel
agent = Agent(model=BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0"))
agent = Agent(model=AnthropicModel(model_id="claude-sonnet-4-6"))

# Custom tool
@tool
def my_tool(input_text: str) -> str:
    """One-line description of what this tool does."""
    return input_text.upper()

# Pattern A — agent as a tool (wrap specialist in @tool, pass to orchestrator)

# Pattern B — Graph (parallel nodes)
from strands.multiagent import GraphBuilder
builder = GraphBuilder()
builder.add_node(agent_a, "node_a")
builder.add_node(agent_b, "node_b")
builder.set_entry_point("node_a")   # set both for parallel
builder.set_entry_point("node_b")
graph = builder.build()
async for event in graph.stream_async("prompt"):
    ...

# Pattern C — Workflow (sequential)
from strands.multiagent import Workflow
workflow = Workflow(agents=[step1_agent, step2_agent, step3_agent])
result = workflow.run("prompt")
```

### Graph event types

| Event | When |
| --- | --- |
| `multiagent_node_start` | Node begins |
| `multiagent_node_stop` | Node ends, `node_result` has output |
| `multiagent_graph_complete` | All nodes done |

---

## Advanced Topics (not covered here)

- The Agent Loop internals and `AgentResult` / observability traces
- Full community tools catalogue (`strands-agents-tools`)
- Model configuration: token limits, temperature, custom providers
- Streaming with async iterators and callback handlers
- A2A Server / Client — remote agents over HTTP (`strands-agents[a2a]`)
