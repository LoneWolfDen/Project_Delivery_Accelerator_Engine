"""Persona Review Engine – v2.

Role-to-group mapping: users select familiar role names; the engine maps
them to grouped intelligence personas behind the scenes.

Key design decisions
────────────────────
- UI shows role names ("Solution Architect", "DevOps Engineer", …)
- Internally each role maps to a persona group YAML
- Up to 3 roles per run; multiple roles in the same group are deduplicated
- Each group produces one structured review; results are merged with
  per-role attribution in the output
- Output structure: summary, findings_by_role, deep_dive, recommended_actions
- files_only falls back to heuristic keyword analysis (unchanged)
- Any real AI backend calls the LLM once per persona group
- custom_prompt is appended to every prompt; findings vary per persona+context
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from models.project import ReviewOutput

PERSONAS_DIR = Path(__file__).parent / "definitions"

# ── Role → persona group mapping ─────────────────────────────────────────────
ROLE_TO_GROUP: Dict[str, str] = {
    "Solution Architect":  "architecture_strategy",
    "Enterprise Architect":"architecture_strategy",
    "Delivery Manager":    "solution_delivery",
    "Product Owner":       "product_value",
    "Resource Manager":    "people_capacity",
    "DevOps Engineer":     "platform_reliability",
    "Cloud Architect":     "platform_reliability",
    "Platform Engineer":   "platform_reliability",
    "QA / Test Lead":      "platform_reliability",
    "Data Engineer":       "data_security_cost",
    "Security Architect":  "data_security_cost",
    "FinOps":              "data_security_cost",
}

# ── Persona group → YAML filename ────────────────────────────────────────────
GROUP_TO_FILE: Dict[str, str] = {
    "architecture_strategy": "architecture_strategy.yaml",
    "solution_delivery":     "solution_delivery.yaml",
    "product_value":         "product_value.yaml",
    "people_capacity":       "people_capacity.yaml",
    "platform_reliability":  "platform_reliability.yaml",
    "data_security_cost":    "data_security_cost.yaml",
}

# Legacy persona IDs (kept for backward-compatibility with stored reviews)
LEGACY_PERSONAS: Dict[str, str] = {
    "solution_architect": "architecture_strategy",
    "delivery_manager":   "solution_delivery",
    "product_owner":      "product_value",
    "resource_manager":   "people_capacity",
}

MAX_ROLES_PER_RUN = 3
DEFAULT_ROLES = ["Solution Architect", "Delivery Manager", "Product Owner"]

VALID_BACKENDS = {"files_only", "ollama", "bedrock", "gemini", "groq", "openrouter"}


# ── Public API ────────────────────────────────────────────────────────────────

def list_roles() -> List[Dict[str, str]]:
    """Return all visible roles with their group metadata.

    Returns:
        List of dicts: {id, name, group_id, group_name, purpose, prompt_template}
        prompt_template reflects any admin override saved in AdminConfig.persona_prompts;
        falls back to the YAML default when no override exists.
    """
    roles = []
    seen_groups: Dict[str, Dict[str, Any]] = {}

    # Load admin overrides once — graceful fallback if config unavailable
    admin_prompts: Dict[str, str] = {}
    try:
        from admin.config import load_config  # noqa: PLC0415
        admin_prompts = load_config().persona_prompts or {}
    except Exception:
        pass

    for role, group_id in ROLE_TO_GROUP.items():
        if group_id not in seen_groups:
            try:
                grp = _load_group(group_id)
                seen_groups[group_id] = grp
            except Exception:
                seen_groups[group_id] = {}

        grp = seen_groups[group_id]
        # Admin override takes precedence over YAML default
        prompt_template = admin_prompts.get(group_id) or grp.get("prompt_template", "")
        roles.append({
            "id":              role,
            "name":            role,
            "group_id":        group_id,
            "group_name":      grp.get("name", group_id),
            "purpose":         grp.get("purpose", ""),
            "prompt_template": prompt_template,
        })
    return roles


def list_personas() -> List[Dict[str, str]]:
    """Backward-compatible alias — returns roles list."""
    return list_roles()


def run_review(
    roles: List[str] | str,
    context: Dict[str, Any],
    ai_backend: Optional[str] = None,
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a multi-role review against project context.

    Args:
        roles: One role name or list of role names (max 3).
            Accepts legacy persona IDs (e.g. ``"solution_architect"``) too.
        context: Built project intelligence dict.
        ai_backend: Backend name; defaults to ``"files_only"``.
        custom_prompt: Free-text additional context from the user.
            Included in every AI prompt — so results vary when changed.

    Returns:
        Review dict with keys:
            persona, persona_id, roles, timestamp, ai_backend,
            findings_by_role, findings, summary, recommendations,
            questions, prompt_used, raw_output, ai_metadata
    """
    backend = ai_backend or "files_only"
    if backend not in VALID_BACKENDS:
        raise ValueError(f"Unknown AI backend: '{backend}'. Use: {sorted(VALID_BACKENDS)}")

    # Normalise roles input
    role_list = _normalise_roles(roles)
    if not role_list:
        raise ValueError("At least one role must be specified.")

    # P9: prepend any captured pre-sales feedback to the custom_prompt
    # when the project is in the pre-sales phase.
    project_id = context.get("_project_id", "")
    if project_id:
        try:
            from processors.presales_feedback import get_feedback_prompt_injection
            feedback_block = get_feedback_prompt_injection(project_id)
            if feedback_block:
                custom_prompt = (
                    feedback_block + "\n" + (custom_prompt or "")
                ).strip()
        except Exception:
            pass

    # Map roles → distinct groups (preserve order, deduplicate groups)
    groups_needed: Dict[str, List[str]] = {}  # group_id → [role names]
    for role in role_list:
        gid = _resolve_group(role)
        groups_needed.setdefault(gid, []).append(role)

    # Run one review per group
    group_results: Dict[str, Dict[str, Any]] = {}
    for gid, contributing_roles in groups_needed.items():
        try:
            group_results[gid] = _run_group_review(
                group_id=gid,
                contributing_roles=contributing_roles,
                context=context,
                backend=backend,
                custom_prompt=custom_prompt,
            )
        except Exception as exc:
            group_results[gid] = {
                "error": str(exc),
                "roles": contributing_roles,
                "findings": {},
            }

    # Merge results
    return _merge_group_results(group_results, role_list, backend, custom_prompt)


# ── Group review runner ───────────────────────────────────────────────────────

def _run_group_review(
    group_id: str,
    contributing_roles: List[str],
    context: Dict[str, Any],
    backend: str,
    custom_prompt: Optional[str],
) -> Dict[str, Any]:
    """Run a review for one persona group."""
    persona = _load_group(group_id)

    if backend == "files_only":
        return _run_files_only_review(persona, contributing_roles, context, custom_prompt)
    return _run_ai_review(persona, contributing_roles, context, backend, custom_prompt)


# ── Files-only (heuristic) ────────────────────────────────────────────────────

def _run_files_only_review(
    persona: Dict[str, Any],
    contributing_roles: List[str],
    context: Dict[str, Any],
    custom_prompt: Optional[str],
) -> Dict[str, Any]:
    """Heuristic review — keyword-based, no LLM call."""
    persona_name = persona["name"]
    group_id     = persona.get("id", "")
    output_sections = persona.get("output_format", {}).get("sections", [])

    prompt = _build_prompt(persona, contributing_roles, context, custom_prompt)

    risks       = context.get("risks", [])
    assumptions = context.get("assumptions", [])
    dependencies= context.get("dependencies", [])
    constraints = context.get("constraints", [])
    resources   = context.get("resources", [])
    action_items= context.get("action_items", [])
    scope       = context.get("scope", "")

    findings = _heuristic_findings(
        group_id, output_sections,
        risks, assumptions, dependencies, constraints, resources, action_items, scope,
    )

    return {
        "persona":      persona_name,
        "group_id":     group_id,
        "roles":        contributing_roles,
        "ai_backend":   "files_only",
        "findings":     findings,
        "summary":      _summarise(persona_name, contributing_roles, findings),
        "recommendations": findings.get("recommendations", []),
        "questions":    findings.get("questions", []),
        "prompt_used":  prompt,
        "raw_output":   None,
        "ai_metadata":  {},
    }


# ── AI review ─────────────────────────────────────────────────────────────────

def _run_ai_review(
    persona: Dict[str, Any],
    contributing_roles: List[str],
    context: Dict[str, Any],
    backend_name: str,
    custom_prompt: Optional[str],
) -> Dict[str, Any]:
    """AI-powered review — calls LLM once per persona group."""
    from ai_backends import get_backend  # noqa: PLC0415

    prompt = _build_prompt(persona, contributing_roles, context, custom_prompt)

    system_prompt = (
        f"You are an expert reviewer acting as: {', '.join(contributing_roles)}.\n"
        f"{persona.get('role', '')}\n"
        "Provide structured analysis with bullet points. "
        "Flag severity: Critical / High / Medium / Low. "
        "Be concise, specific, and evidence-based."
    )

    backend = get_backend(backend_name)
    response = backend.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.3,
        max_tokens=2500,
    )

    if not response.success:
        review = _run_files_only_review(persona, contributing_roles, context, custom_prompt)
        review["ai_backend"]  = f"{backend_name}_fallback"
        review["raw_output"]  = f"{backend_name} unavailable: {response.error}"
        review["prompt_used"] = prompt
        return review

    findings = _parse_ai_output(response.text, persona)

    return {
        "persona":      persona["name"],
        "group_id":     persona.get("id", ""),
        "roles":        contributing_roles,
        "ai_backend":   backend_name,
        "findings":     findings,
        "summary":      _summarise(persona["name"], contributing_roles, findings),
        "recommendations": findings.get("recommendations", []),
        "questions":    findings.get("questions", []),
        "prompt_used":  prompt,
        "raw_output":   response.text,
        "ai_metadata":  response.to_dict(),
    }


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(
    persona: Dict[str, Any],
    contributing_roles: List[str],
    context: Dict[str, Any],
    custom_prompt: Optional[str],
) -> str:
    """Build the full prompt sent to the LLM.

    The persona's prompt_template is resolved with the following priority:
      1. Admin-saved override in AdminConfig.persona_prompts (keyed by group_id)
      2. The prompt_template field in the persona YAML
    """
    from processors.context_builder import build_context_summary  # noqa: PLC0415

    context_summary = build_context_summary(context)
    role_str  = " / ".join(contributing_roles)
    focus     = persona.get("focus_areas", [])
    sections  = persona.get("output_format", {}).get("sections", [])

    # Resolve prompt_template: admin override > YAML default
    group_id = persona.get("id", "")
    template = persona.get("prompt_template", "").strip()
    try:
        from admin.config import load_config  # noqa: PLC0415
        override = load_config().persona_prompts.get(group_id, "")
        if override:
            template = override.strip()
    except Exception:
        pass

    parts = [
        f"# Review: {role_str}",
        "",
        template,
        "",
        "## Focus Areas",
        *[f"- {f}" for f in focus],
        "",
        "## Required Output Sections",
        *[f"- {s}" for s in sections],
        "",
        "## Project Context",
        "",
        context_summary,
    ]

    if custom_prompt and custom_prompt.strip():
        parts += [
            "",
            "## Additional Context (User-Provided)",
            "",
            custom_prompt.strip(),
            "",
            "⚠️  The above user context MUST influence your findings.",
            "    Findings that contradict the user context should be flagged explicitly.",
        ]

    parts += [
        "",
        "## Instructions",
        "",
        "Provide your review. For each output section list specific findings with evidence.",
        "Use bullet points. Include severity labels. End with open questions.",
    ]

    return "\n".join(parts)


# ── Merge results ─────────────────────────────────────────────────────────────

def _merge_group_results(
    group_results: Dict[str, Dict[str, Any]],
    all_roles: List[str],
    backend: str,
    custom_prompt: Optional[str],
) -> Dict[str, Any]:
    """Merge per-group results into a single review dict."""
    findings_by_role: Dict[str, Any] = {}
    all_findings: Dict[str, List[str]] = {}
    all_recommendations: List[str] = []
    all_questions: List[str] = []
    all_prompts: List[str] = []
    summaries: List[str] = []

    for gid, result in group_results.items():
        if result.get("error"):
            findings_by_role[gid] = {"error": result["error"], "roles": result.get("roles", [])}
            continue

        roles_in_group = result.get("roles", [])
        label = " / ".join(roles_in_group)
        findings = result.get("findings", {})

        # Attribute findings to roles
        findings_by_role[label] = {
            "group_id":  gid,
            "roles":     roles_in_group,
            "findings":  findings,
        }

        # Aggregate into flat findings (deduplicated)
        for cat, items in findings.items():
            if isinstance(items, list):
                existing = all_findings.setdefault(cat, [])
                for item in items:
                    item_s = str(item)
                    if not any(item_s.lower() in str(e).lower() or str(e).lower() in item_s.lower()
                               for e in existing):
                        existing.append(item)

        all_recommendations += [
            r for r in result.get("recommendations", [])
            if r not in all_recommendations
        ]
        all_questions += [
            q for q in result.get("questions", [])
            if q not in all_questions
        ]
        if result.get("prompt_used"):
            all_prompts.append(result["prompt_used"])
        if result.get("summary"):
            summaries.append(result["summary"])

    # Recommended actions: deduplicated flat list
    recommended_actions = list(dict.fromkeys(all_recommendations))

    total_findings = sum(
        len(v) for v in all_findings.values() if isinstance(v, list)
    )

    # Primary persona label (first group)
    first_result = next(iter(group_results.values()), {})
    primary_persona = first_result.get("persona", all_roles[0] if all_roles else "Review")
    primary_persona_id = first_result.get("group_id", "")

    return {
        # Legacy-compatible fields
        "persona":          primary_persona,
        "persona_id":       primary_persona_id,
        # v2 fields
        "roles":            all_roles,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "ai_backend":       backend,
        "custom_prompt":    custom_prompt,
        # Findings
        "findings":         all_findings,          # flat merged dict (legacy consumers)
        "findings_by_role": findings_by_role,      # attributed per role
        "recommended_actions": recommended_actions,
        "recommendations":  recommended_actions,   # alias
        "questions":        all_questions[:15],
        # Output section (spec)
        "output_structure": {
            "summary":             " | ".join(summaries),
            "findings_by_role":    findings_by_role,
            "recommended_actions": recommended_actions,
        },
        # Display
        "summary":          _build_consolidated_summary(
                                all_roles, total_findings, backend, custom_prompt
                            ),
        "prompt_used":      "\n\n---\n\n".join(all_prompts) if all_prompts else "",
        "raw_output":       None,
        "ai_metadata":      first_result.get("ai_metadata", {}),
    }


def _build_consolidated_summary(
    roles: List[str],
    total_findings: int,
    backend: str,
    custom_prompt: Optional[str],
) -> str:
    role_str = ", ".join(roles)
    cp_note  = " (with user context)" if custom_prompt else ""
    return (
        f"{role_str} review{cp_note}: "
        f"{total_findings} findings via {backend}"
    )


# ── AI output parser ──────────────────────────────────────────────────────────

def _parse_ai_output(raw: str, persona: Dict[str, Any]) -> Dict[str, List[str]]:
    """Parse LLM text into per-section lists."""
    sections = persona.get("output_format", {}).get("sections", [])
    findings: Dict[str, List[str]] = {s: [] for s in sections}
    current = ""

    for line in raw.splitlines():
        stripped = line.strip()
        # Section heading detection
        m = re.match(r"^(?:#{1,3}\s*|(?:\*\*|__))?(.+?)(?:\*\*|__)?:?\s*$", stripped)
        if m:
            candidate = m.group(1).lower().replace(" ", "_").replace("-", "_")
            for sec in sections:
                if sec.lower() in candidate or candidate in sec.lower():
                    current = sec
                    break
        elif current and re.match(r"^\s*[-*•]\s+", stripped):
            item = re.sub(r"^\s*[-*•]\s+", "", stripped)
            if len(item) > 5:
                findings[current].append(item)
        elif current and re.match(r"^\s*\d+[.)]\s+", stripped):
            item = re.sub(r"^\s*\d+[.)]\s+", "", stripped)
            if len(item) > 5:
                findings[current].append(item)

    # Fallback: dump all bullets into first section
    if not any(findings.values()) and sections:
        bullets = re.findall(r"[-*•]\s+(.+)", raw)
        findings[sections[0]] = bullets[:20]

    return findings


# ── Heuristic fallback ────────────────────────────────────────────────────────

def _heuristic_findings(
    group_id: str,
    sections: List[str],
    risks: List[str],
    assumptions: List[str],
    dependencies: List[str],
    constraints: List[str],
    resources: List[Any],
    action_items: List[str],
    scope: str,
) -> Dict[str, List[str]]:
    """Simple keyword-based heuristic for files_only mode."""
    f: Dict[str, List[str]] = {s: [] for s in sections}

    def _fil(items: List[str], keywords: List[str]) -> List[str]:
        kws = [k.lower() for k in keywords]
        return [i for i in items if any(k in i.lower() for k in kws)]

    def _put(key: str, items: List[Any]) -> None:
        if key in f:
            f[key] = [str(i) for i in items]

    if group_id == "architecture_strategy":
        arch_kw = ["architect","design","integration","api","cloud","security","scalab","infra","deploy"]
        _put("risks",         _fil(risks, arch_kw))
        _put("design_gaps",   [f"Compliance requirement: {c}" for c in constraints if any(
            k in c.lower() for k in ["encrypt","security","hipaa","pci","gdpr","sla","uptime"])])
        _put("recommendations",["Document architecture decisions for each constraint"] if constraints else [])
        _put("questions",     _arch_questions(risks, constraints))

    elif group_id == "solution_delivery":
        exec_kw = ["timeline","delay","risk","dependency","blocked","resource","milestone","sprint"]
        _put("execution_risks",  _fil(risks, exec_kw))
        _put("dependency_issues",[f"Dependency: {d}" for d in dependencies])
        res_list = [r.get("description", str(r)) if isinstance(r, dict) else str(r) for r in resources]
        _put("timeline_concerns",
             [f"Resource requirements: {len(res_list)} identified"] if res_list
             else ["No explicit resource plan found"])
        _put("recommendations",
             [f"Track {len(action_items)} action items"] if action_items else [])
        _put("questions",["Is there schedule contingency built in?",
                          "Are all dependency owners confirmed?"])

    elif group_id == "product_value":
        _put("scope_gaps",
             ["No explicit scope statement found"] if not scope
             else ([f"Unvalidated assumption: {a}" for a in assumptions[:5]]
                   or ["Scope present but no assumptions documented"]))
        val_kw = ["user","customer","business","value","roi","cost","saving"]
        _put("value_alignment",  _fil(constraints, val_kw) or ["No ROI statements found"])
        _put("backlog_quality_issues",
             [] if assumptions else ["No assumptions documented — possible requirements gap"])
        _put("recommendations",["Define acceptance criteria for each deliverable"])
        _put("questions",["Who are the key stakeholders and their success criteria?",
                          "What is the definition of done?"])

    elif group_id == "people_capacity":
        skill_kw = ["skill","knowledge","training","expertise","key person"]
        alloc_kw = ["shared","part-time","stretch","overload"]
        _put("skill_gaps",
             _fil(risks, skill_kw) or ["No skill gap analysis found — recommend assessment"])
        _put("allocation_risks",
             _fil(risks, alloc_kw)
             + (["Key-person dependency identified"] if any("key person" in r.lower() or
                "single point" in r.lower() for r in risks) else []))
        res_list = [r.get("description", str(r)) if isinstance(r, dict) else str(r) for r in resources]
        _put("capacity_concerns",
             [f"Resource needed: {r}" for r in res_list]
             or ["No explicit resource requirements found"])
        _put("recommendations",["Create skills matrix for project needs"])
        _put("questions",["What is the onboarding timeline for new members?",
                          "Are there competing priorities for key resources?"])

    elif group_id == "platform_reliability":
        deploy_kw = ["deploy","ci/cd","pipeline","release","rollout"]
        test_kw   = ["test","qa","quality","validation"]
        rel_kw    = ["monitor","sla","uptime","availability","backup","recovery","dr"]
        _put("deployment_risks", _fil(risks, deploy_kw))
        _put("reliability_gaps", _fil(constraints, rel_kw))
        _put("testing_concerns",
             _fil(risks, test_kw) or ["No testing strategy mentioned in documents"])
        _put("recommendations",["Define deployment runbook and rollback procedure"])
        _put("questions",["Is a CI/CD pipeline defined?","What is the testing strategy?"])

    elif group_id == "data_security_cost":
        sec_kw  = ["security","encrypt","auth","compliance","pci","hipaa","gdpr","audit"]
        cost_kw = ["cost","budget","spend","pricing","cloud cost","finops"]
        _put("data_risks",     _fil(risks, sec_kw + ["data","pipeline","migration"]))
        _put("security_gaps",  [f"Compliance req: {c}" for c in constraints
                                if any(k in c.lower() for k in sec_kw)])
        _put("cost_concerns",  _fil(constraints, cost_kw)
                                or ["No cost model or FinOps strategy found"])
        _put("recommendations",["Conduct security threat model","Define cost baseline"])
        _put("questions",["Is data residency and sovereignty addressed?",
                          "What is the cloud cost estimate at full scale?"])
    else:
        # Generic fallback
        for sec in sections:
            if "risk" in sec:       f[sec] = risks[:8]
            elif "question" in sec: f[sec] = ["Are all stakeholders aligned on scope and timeline?"]
            elif "recommend" in sec:f[sec] = ["Review all identified risks and assign owners"]

    return f


def _arch_questions(risks: List[str], constraints: List[str]) -> List[str]:
    q = []
    all_text = " ".join(risks + constraints).lower()
    if not any(k in all_text for k in ["dr", "disaster", "failover", "backup"]):
        q.append("What is the disaster recovery strategy?")
    if not any(k in all_text for k in ["monitor", "observ", "alert", "log"]):
        q.append("What monitoring and observability approach is planned?")
    if any(k in all_text for k in ["encrypt", "transit", "rest", "tls"]):
        q.append("Is end-to-end encryption architecture documented?")
    return q or ["Are all non-functional requirements covered in the architecture?"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_roles(roles: List[str] | str) -> List[str]:
    """Accept string or list; resolve legacy IDs; cap at MAX_ROLES_PER_RUN."""
    if isinstance(roles, str):
        roles = [roles]

    resolved = []
    for r in roles[:MAX_ROLES_PER_RUN]:
        # Accept legacy persona IDs transparently
        if r in LEGACY_PERSONAS:
            # Map to a visible role name for the first visible role in that group
            target_group = LEGACY_PERSONAS[r]
            for role_name, gid in ROLE_TO_GROUP.items():
                if gid == target_group:
                    resolved.append(role_name)
                    break
        else:
            resolved.append(r)
    return resolved


def _resolve_group(role: str) -> str:
    """Map a role name to its persona group id."""
    if role in ROLE_TO_GROUP:
        return ROLE_TO_GROUP[role]
    # Fuzzy fallback: match any keyword in role name
    role_lower = role.lower()
    for known_role, gid in ROLE_TO_GROUP.items():
        if known_role.lower() in role_lower or role_lower in known_role.lower():
            return gid
    # Last resort: treat as literal group id
    if role in GROUP_TO_FILE:
        return role
    raise ValueError(
        f"Unknown role: '{role}'. "
        f"Available: {', '.join(ROLE_TO_GROUP.keys())}"
    )


def _load_group(group_id: str) -> Dict[str, Any]:
    """Load a persona group YAML."""
    filename = GROUP_TO_FILE.get(group_id)
    if not filename:
        raise ValueError(f"Unknown persona group: '{group_id}'")
    path = PERSONAS_DIR / filename
    if not path.exists():
        raise ValueError(f"Persona definition not found: {path}")
    with open(path) as fh:
        return yaml.safe_load(fh)


def _summarise(
    persona_name: str, roles: List[str], findings: Dict[str, List[str]]
) -> str:
    total = sum(len(v) for v in findings.values() if isinstance(v, list))
    cats  = sum(1 for v in findings.values() if isinstance(v, list) and v)
    return f"{' / '.join(roles)}: {total} findings across {cats} categories"
