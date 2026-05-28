"""Persona Review Engine.

Runs structured analysis using predefined personas (roles).
Each persona has a specific prompt template and output format.

Supports backends:
- files_only: Pattern-based analysis (no AI, instant, deterministic)
- ollama: Local LLM via Ollama API
- bedrock: AWS Bedrock (Claude, etc.)
- gemini: Google Gemini Pro via API key

The engine:
1. Loads the persona YAML definition
2. Builds a focused prompt from context summary + persona template
3. Optionally appends user-supplied custom context
4. Runs analysis (AI or heuristic)
5. Returns structured ReviewOutput with prompt visibility
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml

from models.project import ReviewOutput

PERSONAS_DIR = Path(__file__).parent / "definitions"

# Available personas (maps user-friendly names to filenames)
AVAILABLE_PERSONAS = {
    "solution_architect": "solution_architect.yaml",
    "delivery_manager": "delivery_manager.yaml",
    "product_owner": "product_owner.yaml",
    "resource_manager": "resource_manager.yaml",
}

# Valid AI backends
VALID_BACKENDS = {"files_only", "ollama", "bedrock", "gemini", "groq", "openrouter"}


def list_personas() -> List[Dict[str, str]]:
    """List all available personas with their metadata.

    Returns:
        List of dicts with keys: id, name, role.
    """
    personas = []
    for persona_id, filename in AVAILABLE_PERSONAS.items():
        persona = load_persona(persona_id)
        personas.append({
            "id": persona_id,
            "name": persona["name"],
            "role": persona["role"],
        })
    return personas


def load_persona(persona_name: str) -> Dict[str, Any]:
    """Load a persona definition from YAML.

    Args:
        persona_name: e.g. 'solution_architect', 'delivery_manager'

    Returns:
        Persona config dict with keys: name, role, prompt_template,
        output_format, focus_areas.

    Raises:
        ValueError: If persona not found.
    """
    filename = AVAILABLE_PERSONAS.get(persona_name)
    if not filename:
        raise ValueError(
            f"Unknown persona: '{persona_name}'. "
            f"Available: {', '.join(AVAILABLE_PERSONAS.keys())}"
        )

    persona_path = PERSONAS_DIR / filename
    if not persona_path.exists():
        raise ValueError(f"Persona definition file not found: {persona_path}")

    with open(persona_path) as f:
        return yaml.safe_load(f)


def run_review(
    persona_name: str,
    context: Dict[str, Any],
    ai_backend: Optional[str] = None,
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a persona-driven review against project context.

    Args:
        persona_name: Which persona to use (e.g. 'solution_architect').
        context: Built project intelligence dict (from build_context).
        ai_backend: 'files_only', 'ollama', 'bedrock', or 'gemini' (default: files_only).
        custom_prompt: Optional additional user context/instructions that the AI
            must consider when evaluating. Appended to the persona prompt.

    Returns:
        Review output dict with keys: persona, timestamp, findings (per section),
        summary, recommendations, questions, prompt_used, raw_output.
        The 'prompt_used' field shows exactly what was sent to the AI.
    """
    persona = load_persona(persona_name)
    backend = ai_backend or "files_only"

    if backend not in VALID_BACKENDS:
        available = ", ".join(sorted(VALID_BACKENDS))
        raise ValueError(f"Unknown AI backend: '{backend}'. Use: {available}")

    if backend == "files_only":
        return _run_files_only_review(persona, context, custom_prompt)
    else:
        return _run_ai_review(persona, context, backend, custom_prompt)


def build_review_prompt(
    persona: Dict[str, Any],
    context: Dict[str, Any],
    custom_prompt: Optional[str] = None,
) -> str:
    """Build a structured prompt for AI review.

    Combines persona template with context summary for token-efficient prompts.
    If custom_prompt is provided, it's appended as additional user context.

    Args:
        persona: Loaded persona definition.
        context: Project intelligence dict.
        custom_prompt: Optional additional context/instructions from the user.

    Returns:
        Full prompt string ready for AI submission.
    """
    from processors.context_builder import build_context_summary

    context_summary = build_context_summary(context)
    prompt_template = persona.get("prompt_template", "")
    focus_areas = persona.get("focus_areas", [])
    output_sections = persona.get("output_format", {}).get("sections", [])

    prompt_parts = [
        f"# Role: {persona['name']}",
        "",
        prompt_template.strip(),
        "",
        "## Focus Areas",
        "",
    ]
    for area in focus_areas:
        prompt_parts.append(f"- {area}")

    prompt_parts.extend([
        "",
        "## Required Output Sections",
        "",
    ])
    for section in output_sections:
        prompt_parts.append(f"- {section}")

    prompt_parts.extend([
        "",
        "## Project Context",
        "",
        context_summary,
    ])

    # Append custom user prompt if provided
    if custom_prompt and custom_prompt.strip():
        prompt_parts.extend([
            "",
            "## Additional Context (User-Provided)",
            "",
            custom_prompt.strip(),
        ])

    prompt_parts.extend([
        "",
        "## Instructions",
        "",
        "Based on the project context above, provide your review.",
        "For each output section, list specific findings with evidence.",
        "Be concise. Use bullet points. Flag severity (Critical/High/Medium/Low).",
        "End with open questions that need resolution.",
    ])

    return "\n".join(prompt_parts)


# ──────────────────────────────────────────────────────────────
# Files-only mode (heuristic, no AI)
# ──────────────────────────────────────────────────────────────


def _run_files_only_review(
    persona: Dict[str, Any], context: Dict[str, Any], custom_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Run a deterministic, pattern-based review without AI.

    Analyses the context using persona focus areas to filter
    and categorise existing extractions.
    """
    persona_name = persona["name"]
    focus_areas = persona.get("focus_areas", [])
    output_sections = persona.get("output_format", {}).get("sections", [])

    # Build prompt for display even in files-only mode
    prompt = build_review_prompt(persona, context, custom_prompt)

    # Get extracted intelligence
    risks = context.get("risks", [])
    assumptions = context.get("assumptions", [])
    dependencies = context.get("dependencies", [])
    constraints = context.get("constraints", [])
    resources = context.get("resources", [])
    action_items = context.get("action_items", [])
    scope = context.get("scope", "")

    # Run persona-specific analysis
    findings = _analyse_by_persona(
        persona_name, focus_areas, output_sections,
        risks, assumptions, dependencies, constraints, resources, action_items, scope
    )

    # Build review output
    timestamp = datetime.now(timezone.utc).isoformat()
    review = {
        "persona": persona_name,
        "persona_id": _get_persona_id(persona_name),
        "timestamp": timestamp,
        "ai_backend": "files_only",
        "findings": findings,
        "summary": _build_review_summary(persona_name, findings),
        "recommendations": findings.get("recommendations", []),
        "questions": findings.get("questions", []),
        "prompt_used": prompt,
        "custom_prompt": custom_prompt,
        "raw_output": None,
    }

    return review


def _run_ai_review(
    persona: Dict[str, Any],
    context: Dict[str, Any],
    backend_name: str,
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Run review using any AI backend (unified handler).

    Uses the ai_backends module for consistent behavior across all providers.
    Falls back to files-only analysis if the backend is unavailable.
    """
    from ai_backends import get_backend

    prompt = build_review_prompt(persona, context, custom_prompt)

    # System prompt for the AI
    system_prompt = (
        f"You are a {persona['name']}. {persona.get('role', '')}\n"
        "Provide structured analysis with bullet points per section.\n"
        "Flag severity levels: Critical, High, Medium, Low.\n"
        "Be concise and evidence-based."
    )

    backend = get_backend(backend_name)
    response = backend.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.3,
        max_tokens=2000,
    )

    if not response.success:
        # Fall back to files-only with a note about the failure
        review = _run_files_only_review(persona, context, custom_prompt)
        review["ai_backend"] = f"{backend_name}_fallback"
        review["raw_output"] = f"{backend_name} unavailable: {response.error}. Fell back to files-only analysis."
        review["prompt_used"] = prompt
        review["custom_prompt"] = custom_prompt
        return review

    # Parse AI output into structured findings
    findings = _parse_ai_output(response.text, persona)

    return {
        "persona": persona["name"],
        "persona_id": _get_persona_id(persona["name"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_backend": backend_name,
        "findings": findings,
        "summary": _build_review_summary(persona["name"], findings),
        "recommendations": findings.get("recommendations", []),
        "questions": findings.get("questions", []),
        "prompt_used": prompt,
        "custom_prompt": custom_prompt,
        "raw_output": response.text,
        "ai_metadata": response.to_dict(),
    }


def _analyse_by_persona(
    persona_name: str,
    focus_areas: List[str],
    output_sections: List[str],
    risks: List[str],
    assumptions: List[str],
    dependencies: List[str],
    constraints: List[str],
    resources: List[Any],
    action_items: List[str],
    scope: str,
) -> Dict[str, List[str]]:
    """Route to persona-specific analysis logic."""
    if "Solution Architect" in persona_name:
        return _analyse_solution_architect(
            risks, dependencies, constraints, scope
        )
    elif "Delivery Manager" in persona_name:
        return _analyse_delivery_manager(
            risks, dependencies, constraints, resources, action_items
        )
    elif "Product Owner" in persona_name:
        return _analyse_product_owner(
            risks, assumptions, dependencies, constraints, scope
        )
    elif "Resource Manager" in persona_name:
        return _analyse_resource_manager(
            risks, resources, dependencies, action_items
        )
    else:
        # Generic analysis
        return _analyse_generic(output_sections, risks, assumptions, dependencies, constraints)


def _analyse_solution_architect(
    risks: List[str],
    dependencies: List[str],
    constraints: List[str],
    scope: str,
) -> Dict[str, List[str]]:
    """Solution Architect: focus on architecture, technology, integration."""
    arch_keywords = [
        "architect", "design", "pattern", "integration", "api", "database",
        "scalab", "security", "infra", "cloud", "container", "micro",
        "monolith", "latency", "performance", "migration", "deploy",
        "network", "data flow", "storage", "cache", "queue", "event",
    ]

    findings: Dict[str, List[str]] = {
        "risks": _filter_by_relevance(risks, arch_keywords),
        "design_gaps": [],
        "recommendations": [],
        "questions": [],
    }

    # Detect design gaps from constraints
    for c in constraints:
        if _is_relevant(c, ["encrypt", "security", "auth", "compliance", "pci", "hipaa"]):
            findings["design_gaps"].append(f"Security/compliance requirement: {c}")
        elif _is_relevant(c, ["uptime", "sla", "availability", "latency"]):
            findings["design_gaps"].append(f"NFR may require architecture decision: {c}")

    # Generate recommendations based on gaps
    if findings["design_gaps"]:
        findings["recommendations"].append(
            "Document architecture decisions for each compliance constraint"
        )
    if _any_relevant(dependencies, ["database", "data", "migration"]):
        findings["recommendations"].append(
            "Define data migration strategy with rollback plan"
        )
    if _any_relevant(risks, ["skill gap", "key person", "single point"]):
        findings["recommendations"].append(
            "Mitigate key-person risk with architecture documentation and knowledge transfer"
        )

    # Generate questions
    if not _any_relevant(risks + constraints, ["dr", "disaster", "recovery", "failover", "backup"]):
        findings["questions"].append("What is the disaster recovery strategy?")
    if not _any_relevant(risks + constraints, ["monitor", "observ", "alert", "log"]):
        findings["questions"].append("What monitoring and observability approach is planned?")
    if _any_relevant(constraints, ["encrypt", "transit", "rest"]):
        findings["questions"].append("Is end-to-end encryption architecture documented?")

    return findings


def _analyse_delivery_manager(
    risks: List[str],
    dependencies: List[str],
    constraints: List[str],
    resources: List[Any],
    action_items: List[str],
) -> Dict[str, List[str]]:
    """Delivery Manager: focus on execution, timelines, dependencies."""
    exec_keywords = [
        "timeline", "delay", "slip", "resource", "capacity", "staffing",
        "dependency", "blocked", "risk", "scope", "milestone", "deadline",
        "phase", "sprint", "week", "month", "overdue",
    ]

    findings: Dict[str, List[str]] = {
        "execution_risks": _filter_by_relevance(risks, exec_keywords),
        "dependency_issues": [],
        "timeline_concerns": [],
        "recommendations": [],
        "questions": [],
    }

    # Analyse dependencies
    for dep in dependencies:
        findings["dependency_issues"].append(f"Dependency: {dep}")

    # Analyse resource gaps
    resource_descriptions = [
        r.get("description", r) if isinstance(r, dict) else str(r)
        for r in resources
    ]
    if resource_descriptions:
        findings["timeline_concerns"].append(
            f"Resource requirements identified: {len(resource_descriptions)} items"
        )
    if not resource_descriptions:
        findings["timeline_concerns"].append(
            "No explicit resource plan found – potential planning gap"
        )

    # Check action items for overdue risks
    if action_items:
        findings["recommendations"].append(
            f"Track {len(action_items)} action items for completion and blockers"
        )

    # Recommendations
    if dependencies:
        findings["recommendations"].append(
            "Create dependency map with owners and target dates"
        )
    if _any_relevant(risks, ["skill", "resource", "capacity", "staffing"]):
        findings["recommendations"].append(
            "Escalate resourcing gaps before they impact critical path"
        )

    # Questions
    if not _any_relevant(constraints + risks, ["buffer", "contingency", "slack"]):
        findings["questions"].append("Is there schedule contingency/buffer built in?")
    findings["questions"].append("Are all dependency owners confirmed and committed?")

    return findings


def _analyse_product_owner(
    risks: List[str],
    assumptions: List[str],
    dependencies: List[str],
    constraints: List[str],
    scope: str,
) -> Dict[str, List[str]]:
    """Product Owner: focus on scope, requirements, value."""
    findings: Dict[str, List[str]] = {
        "scope_gaps": [],
        "backlog_quality_issues": [],
        "value_alignment": [],
        "recommendations": [],
        "questions": [],
    }

    # Check scope definition
    if not scope:
        findings["scope_gaps"].append("No explicit scope statement found in documents")
    elif len(scope) < 100:
        findings["scope_gaps"].append("Scope definition is very brief – may lack detail")

    # Assumptions as scope risk
    if assumptions:
        for a in assumptions[:5]:
            findings["scope_gaps"].append(f"Unvalidated assumption: {a}")
    else:
        findings["backlog_quality_issues"].append(
            "No assumptions documented – may indicate incomplete requirements gathering"
        )

    # Value alignment from constraints
    value_keywords = ["user", "customer", "business", "value", "roi", "cost", "saving"]
    value_items = _filter_by_relevance(constraints, value_keywords)
    if value_items:
        findings["value_alignment"] = value_items
    else:
        findings["value_alignment"].append(
            "No explicit business value or ROI statements found"
        )

    # Recommendations
    findings["recommendations"].append(
        "Define clear acceptance criteria for each major deliverable"
    )
    if not assumptions:
        findings["recommendations"].append(
            "Conduct assumptions workshop with stakeholders"
        )

    # Questions
    findings["questions"].append("Who are the key stakeholders and their success criteria?")
    findings["questions"].append("What is the definition of done for the overall engagement?")
    if dependencies:
        findings["questions"].append(
            "Are dependencies reflected in prioritisation and sprint planning?"
        )

    return findings


def _analyse_resource_manager(
    risks: List[str],
    resources: List[Any],
    dependencies: List[str],
    action_items: List[str],
) -> Dict[str, List[str]]:
    """Resource Manager: focus on skills, allocation, capacity."""
    findings: Dict[str, List[str]] = {
        "skill_gaps": [],
        "allocation_risks": [],
        "capacity_concerns": [],
        "recommendations": [],
        "questions": [],
    }

    # Analyse resources
    resource_descriptions = [
        r.get("description", r) if isinstance(r, dict) else str(r)
        for r in resources
    ]

    if resource_descriptions:
        for rd in resource_descriptions:
            findings["capacity_concerns"].append(f"Resource needed: {rd}")
    else:
        findings["capacity_concerns"].append(
            "No explicit resource requirements found – needs clarification"
        )

    # Skill gap indicators from risks
    skill_keywords = ["skill", "knowledge", "experience", "training", "expertise", "key person"]
    skill_risks = _filter_by_relevance(risks, skill_keywords)
    if skill_risks:
        findings["skill_gaps"] = skill_risks
    else:
        findings["skill_gaps"].append(
            "No explicit skill gap analysis found – recommend assessment"
        )

    # Allocation risks
    alloc_keywords = ["shared", "part-time", "split", "multiple", "stretch", "overload"]
    alloc_risks = _filter_by_relevance(risks, alloc_keywords)
    findings["allocation_risks"].extend(alloc_risks)
    if _any_relevant(risks, ["key person", "single point", "bus factor"]):
        findings["allocation_risks"].append(
            "Key-person dependency identified – single point of failure risk"
        )

    # Recommendations
    findings["recommendations"].append(
        "Create a skills matrix mapping team capabilities to project needs"
    )
    if resource_descriptions:
        findings["recommendations"].append(
            "Confirm resource availability and start dates with line managers"
        )

    # Questions
    findings["questions"].append("What is the onboarding timeline for new team members?")
    findings["questions"].append("Are there competing priorities for the identified resources?")

    return findings


def _analyse_generic(
    output_sections: List[str],
    risks: List[str],
    assumptions: List[str],
    dependencies: List[str],
    constraints: List[str],
) -> Dict[str, List[str]]:
    """Generic analysis fallback."""
    findings: Dict[str, List[str]] = {}
    for section in output_sections:
        if "risk" in section.lower():
            findings[section] = risks[:10]
        elif "assumption" in section.lower():
            findings[section] = assumptions[:10]
        elif "depend" in section.lower():
            findings[section] = dependencies[:10]
        elif "constraint" in section.lower():
            findings[section] = constraints[:10]
        elif "recommend" in section.lower():
            findings[section] = ["Review all identified risks and assign owners"]
        elif "question" in section.lower():
            findings[section] = ["Are all stakeholders aligned on scope and timeline?"]
        else:
            findings[section] = []
    return findings


# ──────────────────────────────────────────────────────────────
# AI output parsing
# ──────────────────────────────────────────────────────────────


def _parse_ai_output(raw_output: str, persona: Dict[str, Any]) -> Dict[str, List[str]]:
    """Parse AI text output into structured findings.

    Looks for section headings matching persona output_format.
    Falls back to bullet-point extraction.
    """
    import re

    output_sections = persona.get("output_format", {}).get("sections", [])
    findings: Dict[str, List[str]] = {s: [] for s in output_sections}

    lines = raw_output.splitlines()
    current_section = ""

    for line in lines:
        stripped = line.strip()

        # Detect section heading
        heading_match = re.match(r"^(?:#{1,3}\s+|(?:\*\*|__))?(.+?)(?:\*\*|__)?:?\s*$", stripped)
        if heading_match:
            potential_heading = heading_match.group(1).lower().replace(" ", "_").replace("-", "_")
            for section in output_sections:
                if section.lower() in potential_heading or potential_heading in section.lower():
                    current_section = section
                    break

        # Extract bullet items into current section
        elif current_section and re.match(r"^\s*[-*•]\s+", stripped):
            item = re.sub(r"^\s*[-*•]\s+", "", stripped)
            if item and len(item) > 5:
                findings[current_section].append(item)

        # Numbered items
        elif current_section and re.match(r"^\s*\d+[.)]\s+", stripped):
            item = re.sub(r"^\s*\d+[.)]\s+", "", stripped)
            if item and len(item) > 5:
                findings[current_section].append(item)

    # If parsing found nothing, put all content as raw
    total_items = sum(len(v) for v in findings.values())
    if total_items == 0:
        # Fall back: extract all bullet points
        all_bullets = re.findall(r"[-*•]\s+(.+)", raw_output)
        if all_bullets and output_sections:
            findings[output_sections[0]] = all_bullets[:20]

    return findings


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _filter_by_relevance(items: List[str], keywords: List[str]) -> List[str]:
    """Filter items that contain any of the keywords."""
    return [item for item in items if _is_relevant(item, keywords)]


def _is_relevant(text: str, keywords: List[str]) -> bool:
    """Check if text contains any keyword."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _any_relevant(items: List[str], keywords: List[str]) -> bool:
    """Check if any item in list is relevant to keywords."""
    return any(_is_relevant(item, keywords) for item in items)


def _get_persona_id(persona_name: str) -> str:
    """Convert persona display name to ID."""
    for pid, filename in AVAILABLE_PERSONAS.items():
        if pid.replace("_", " ") in persona_name.lower():
            return pid
    return persona_name.lower().replace(" ", "_")


def _build_review_summary(persona_name: str, findings: Dict[str, List[str]]) -> str:
    """Build a one-line summary of review findings."""
    total = sum(len(v) for v in findings.values())
    sections_with_items = sum(1 for v in findings.values() if v)
    return (
        f"{persona_name} review: {total} findings across "
        f"{sections_with_items} categories"
    )
