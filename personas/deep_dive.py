"""Deep Dive Engine – v2.

Acts as an SME for the selected role(s): uses the LLM to generate a set of
targeted clarification questions that the user can review, select, and inject
into the Custom Prompt before running the full review.

Design principles
─────────────────
- AI-first: when a real backend is selected the LLM generates questions
  specifically tailored to the role(s) + custom_prompt + project intelligence
- The result is ALWAYS different when the persona or custom_prompt changes
- Heuristic fallback (files_only): keyword-based questions when no AI available
- Output is a flat list of selectable questions grouped by category
- User selects questions → clicks "Add to Prompt" → runs Review with those
  questions baked into the custom_prompt
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Public API ────────────────────────────────────────────────────────────────

def run_deep_dive(
    persona_name: str,
    scope: str,
    intelligence: Dict[str, Any],
    active_files: List[Dict[str, Any]],
    custom_prompt: str = "",
    ai_backend: str = "files_only",
    weaknesses: Optional[List[Dict[str, Any]]] = None,
    missing_categories: Optional[List[str]] = None,
    decision_points: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run a Deep Dive for the selected role.

    When AI mode is ON the LLM acts as the named SME and generates
    project-specific, context-aware questions that change with every
    different persona/prompt combination.

    When files_only the engine falls back to keyword-based heuristic questions.

    Args:
        persona_name: Visible role name (e.g. "Solution Architect") or group id.
        scope: Project scope text from built intelligence.
        intelligence: Full built intelligence dict.
        active_files: List of active file dicts (filename, source_type).
        custom_prompt: User-provided context already added by the user.
        ai_backend: Backend name.

    Returns:
        Deep Dive dict with:
            timestamp, persona, ai_backend, ai_mode,
            question_groups (list of {category, icon, questions[]}),
            all_questions (flat list for Add-to-Prompt),
            scope_completeness (0–100 pct),
            meta
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    ai_mode   = ai_backend != "files_only"

    if ai_mode:
        question_groups = _ai_questions(
            persona_name, scope, intelligence, active_files, custom_prompt, ai_backend,
            weaknesses=weaknesses, missing_categories=missing_categories,
            decision_points=decision_points,
        )
        source = "ai"
    else:
        question_groups = _heuristic_questions(
            persona_name, scope, intelligence, active_files,
            weaknesses=weaknesses, missing_categories=missing_categories,
            decision_points=decision_points,
        )
        source = "heuristic"

    # S5-02: annotate questions in each group with decision_point_id/text when a
    # decision point maps to that category
    if decision_points:
        _annotate_questions_with_decisions(question_groups, decision_points)

    # Flat list for easy "Add to Prompt"
    all_questions = [
        f"[{grp['category']}] {q}"
        for grp in question_groups
        for q in grp.get("questions", [])
    ]

    completeness = _scope_completeness(scope, intelligence)

    return {
        "timestamp":          timestamp,
        "persona":            persona_name,
        "ai_backend":         ai_backend,
        "ai_mode":            ai_mode,
        "question_groups":    question_groups,
        "all_questions":      all_questions,
        "scope_completeness": completeness,
        "meta": {
            "source":       source,
            "active_files": len(active_files),
            "file_types":   list({f.get("source_type", "unknown") for f in active_files}),
            "has_custom_prompt": bool(custom_prompt and custom_prompt.strip()),
        },
        # Legacy field kept for backward-compat with stored deep dives
        "deep_dive": {
            "clarification_questions": all_questions,
        },
    }


def apply_feedback(
    deep_dive_result: Dict[str, Any],
    accepted: Optional[List[str]] = None,
    rejected: Optional[List[str]] = None,
    added_to_prompt: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Record user feedback on a deep dive result."""
    deep_dive_result["feedback"] = {
        "applied_at":       datetime.now(timezone.utc).isoformat(),
        "accepted":         accepted or [],
        "rejected":         rejected or [],
        "added_to_prompt":  added_to_prompt or [],
    }
    return deep_dive_result


# ── S5-02: Decision-question annotation ──────────────────────────────────────

def _annotate_questions_with_decisions(
    question_groups: List[Dict[str, Any]],
    decision_points: List[Dict[str, Any]],
) -> None:
    """Mutate question_groups in-place: add decision_point_id/text to questions
    in groups whose category matches a decision point's category.

    Each group's 'questions' list is converted from plain strings to dicts:
        {question: str, decision_point_id: str, decision_point_text: str}
    for questions that map to a decision point, or
        {question: str, decision_point_id: None, decision_point_text: None}
    for those that don't.

    Only open decision points are considered for annotation.
    """
    # Build a category → first open decision_point lookup
    dp_by_category: Dict[str, Dict[str, Any]] = {}
    for dp in decision_points:
        if dp.get("status", "open") == "open":
            cat = dp.get("category", "")
            if cat and cat not in dp_by_category:
                dp_by_category[cat] = dp

    for grp in question_groups:
        annotated = []
        grp_cat = grp.get("category", "")
        # Also check the "Decisions" category group generated by heuristic
        matched_dp = dp_by_category.get(grp_cat)
        for q in grp.get("questions", []):
            if isinstance(q, dict):
                annotated.append(q)
                continue
            q_str = str(q)
            if matched_dp:
                annotated.append({
                    "question":           q_str,
                    "decision_point_id":  matched_dp["id"],
                    "decision_point_text": matched_dp["text"],
                })
            else:
                annotated.append({
                    "question":           q_str,
                    "decision_point_id":  None,
                    "decision_point_text": None,
                })
        grp["questions"] = annotated


# ── AI-powered SME questions ──────────────────────────────────────────────────

_SYSTEM = (
    "You are a senior {role} performing a deep-dive analysis before a formal review. "
    "Your job is to generate sharp, specific, project-relevant clarification questions "
    "that must be answered before the review can be completed. "
    "Return ONLY a valid JSON object — no markdown, no prose."
)

_USER_PROMPT = """You are acting as: {role}

## Project Scope
{scope}

## Intelligence Summary
{intel_summary}

## Active Documents
{file_summary}

{custom_context}

## Your Task
Generate targeted clarification questions grouped by category.
Questions should be:
- Specific to THIS project (reference actual content where possible)
- Unanswered by the existing documents
- Questions a {role} would ACTUALLY ask before signing off

Return ONLY this JSON structure:
{{
  "question_groups": [
    {{
      "category": "Category Name",
      "icon": "emoji",
      "questions": ["question 1?", "question 2?", ...]
    }},
    ...
  ]
}}

Rules:
- 3–5 categories relevant to the {role} perspective
- 3–5 questions per category
- Each question must be ≥ 20 characters
- No generic questions — every question must be grounded in the project context
- The categories and questions MUST change based on what is present or missing in the documents
"""


def _ai_questions(
    persona_name: str,
    scope: str,
    intelligence: Dict[str, Any],
    active_files: List[Dict[str, Any]],
    custom_prompt: str,
    ai_backend: str,
    weaknesses: Optional[List[Dict[str, Any]]] = None,
    missing_categories: Optional[List[str]] = None,
    decision_points: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Call LLM to generate SME questions. Falls back to heuristic on failure."""
    try:
        from ai_backends import get_backend             # noqa: PLC0415
        from processors.context_builder import build_context_summary  # noqa: PLC0415

        intel_summary = build_context_summary(intelligence)[:2000]
        file_list = ", ".join(
            f.get("filename", f.get("source_type", "?")) for f in active_files[:10]
        ) or "No active files"

        custom_section = (
            f"## User Context (already provided)\n{custom_prompt.strip()}\n\n"
            "⚠️  Do NOT repeat questions already answered by the user context above.\n"
            "    Instead focus on what is STILL missing or unclear.\n"
        ) if custom_prompt and custom_prompt.strip() else ""

        # S4-03: prepend gap context when weaknesses or missing categories are present
        gap_section = ""
        if weaknesses or missing_categories or decision_points:
            lines = ["## Known Gaps from Previous Review"]
            if weaknesses:
                lines.append("Weak findings that need clarification:")
                for w in weaknesses[:5]:
                    lines.append(f"  - [{w.get('category','')}] {w.get('text','')[:80]}")
            if missing_categories:
                lines.append(f"Missing categories (no findings): {', '.join(missing_categories)}")
            if decision_points:
                lines.append("Open decisions that need resolution:")
                for dp in decision_points[:5]:
                    if dp.get("status", "open") == "open":
                        lines.append(f"  - [{dp.get('category','')}] {dp.get('text','')[:80]}")
            lines.append("Generate questions that specifically address these gaps and weaknesses.")
            gap_section = "\n".join(lines) + "\n\n"

        prompt = _USER_PROMPT.format(
            role=persona_name,
            scope=scope[:800] if scope else "No explicit scope defined.",
            intel_summary=intel_summary,
            file_summary=file_list,
            custom_context=gap_section + custom_section,
        )

        backend = get_backend(ai_backend)
        response = backend.generate(
            prompt=prompt,
            system_prompt=_SYSTEM.format(role=persona_name),
            temperature=0.5,   # moderate creativity for varied questions
            max_tokens=1500,
        )

        if response.success and response.text:
            parsed = _parse_question_groups(response.text)
            if parsed:
                return parsed

    except Exception:
        pass

    # Graceful fallback
    return _heuristic_questions(persona_name, scope, intelligence, active_files,
                                weaknesses=weaknesses, missing_categories=missing_categories,
                                decision_points=decision_points)


def _parse_question_groups(text: str) -> List[Dict[str, Any]]:
    """Extract question_groups from LLM response."""
    # Strip markdown fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    candidate = fenced.group(1) if fenced else text

    brace = re.search(r"\{[\s\S]+\}", candidate)
    if not brace:
        return []

    try:
        data = json.loads(brace.group(0))
    except (json.JSONDecodeError, ValueError):
        return []

    groups = data.get("question_groups", [])
    if not isinstance(groups, list):
        return []

    result = []
    for grp in groups:
        if not isinstance(grp, dict):
            continue
        questions = [
            str(q).strip()
            for q in grp.get("questions", [])
            if isinstance(q, str) and len(q.strip()) >= 20
        ]
        if questions:
            result.append({
                "category": str(grp.get("category", "General")),
                "icon":     str(grp.get("icon", "❓")),
                "questions": questions[:6],
            })
    return result[:6]


# ── Heuristic fallback ────────────────────────────────────────────────────────

def _heuristic_questions(
    persona_name: str,
    scope: str,
    intelligence: Dict[str, Any],
    active_files: List[Dict[str, Any]],
    weaknesses: Optional[List[Dict[str, Any]]] = None,
    missing_categories: Optional[List[str]] = None,
    decision_points: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Keyword-based questions for files_only mode."""
    from personas.engine import _resolve_group  # noqa: PLC0415

    try:
        group_id = _resolve_group(persona_name)
    except ValueError:
        group_id = "architecture_strategy"

    risks        = intelligence.get("risks", [])
    assumptions  = intelligence.get("assumptions", [])
    dependencies = intelligence.get("dependencies", [])
    constraints  = intelligence.get("constraints", [])
    action_items = intelligence.get("action_items", [])
    all_text     = " ".join(risks + constraints + action_items + [scope or ""]).lower()

    groups: List[Dict[str, Any]] = []

    # ── Scope questions (always included) ──────────────────────────────────
    scope_qs: List[str] = []
    if not scope or len(scope) < 50:
        scope_qs.append("What are the primary objectives and success criteria for this project?")
        scope_qs.append("What is explicitly out of scope?")
    if not any(k in all_text for k in ["timeline","schedule","deadline","sprint"]):
        scope_qs.append("What is the overall timeline and key milestones?")
    if not any(k in all_text for k in ["budget","cost","fund"]):
        scope_qs.append("What is the budget and how was it estimated?")
    if scope_qs:
        groups.append({"category": "Scope & Objectives", "icon": "📄", "questions": scope_qs[:4]})

    # ── Persona-specific questions ──────────────────────────────────────────
    if group_id == "architecture_strategy":
        qs = []
        if not any(k in all_text for k in ["architect","design pattern","microservice","monolith"]):
            qs.append("What is the target architecture pattern and what drove that choice?")
        if not any(k in all_text for k in ["api","integration","interface"]):
            qs.append("How are the key system integrations designed?")
        if not any(k in all_text for k in ["disaster","recovery","failover","backup"]):
            qs.append("What is the disaster recovery and failover strategy?")
        if not any(k in all_text for k in ["monitor","observ","alert","log"]):
            qs.append("What monitoring and observability approach is planned?")
        if qs:
            groups.append({"category": "Architecture & Design", "icon": "🏗️", "questions": qs[:4]})

        nfr_qs = []
        if not any(k in all_text for k in ["sla","uptime","latency","throughput"]):
            nfr_qs.append("What are the SLA targets for availability, latency and throughput?")
        if not any(k in all_text for k in ["scale","concurrent","load","capacity"]):
            nfr_qs.append("What are the peak load and scalability requirements?")
        if nfr_qs:
            groups.append({"category": "Non-Functional Requirements", "icon": "⚙️", "questions": nfr_qs[:3]})

    elif group_id == "solution_delivery":
        qs = []
        if dependencies:
            qs.append(f"Who owns the {len(dependencies)} identified dependencies and what are their committed dates?")
        if not any(k in all_text for k in ["buffer","contingency","slack"]):
            qs.append("Is there schedule contingency built into the plan?")
        qs.append("What is the escalation path when delivery risks materialise?")
        qs.append("How is scope change managed and governed?")
        groups.append({"category": "Delivery Planning", "icon": "📅", "questions": qs[:4]})

        risk_qs = []
        if risks:
            risk_qs.append(f"Which of the {len(risks)} identified risks has an active mitigation plan?")
        risk_qs.append("What triggers an immediate escalation to the steering committee?")
        groups.append({"category": "Risk & Governance", "icon": "⚠️", "questions": risk_qs[:3]})

    elif group_id == "product_value":
        qs = []
        if not assumptions:
            qs.append("What are the key assumptions underpinning the business case?")
        qs.append("Who are the primary users and what problems are we solving for them?")
        qs.append("What does success look like 6 months after go-live?")
        qs.append("How are features prioritised and who has final sign-off?")
        groups.append({"category": "Business Value & Requirements", "icon": "💼", "questions": qs[:4]})

        acc_qs = ["What are the acceptance criteria for each major deliverable?"]
        if not any(k in all_text for k in ["user story","acceptance","criteria","done"]):
            acc_qs.append("Are user stories written to a Definition of Ready standard?")
        groups.append({"category": "Acceptance & Quality", "icon": "✅", "questions": acc_qs[:3]})

    elif group_id == "people_capacity":
        qs = []
        qs.append("Is every required skill available in the team starting from day one?")
        if risks and any("key person" in r.lower() or "single point" in r.lower() for r in risks):
            qs.append("What is the knowledge transfer plan for identified key-person risks?")
        qs.append("Are there competing project priorities that could pull team members away?")
        qs.append("What is the onboarding plan and ramp-up timeline for new hires or contractors?")
        groups.append({"category": "Skills & Capacity", "icon": "👥", "questions": qs[:4]})

    elif group_id == "platform_reliability":
        qs = []
        if not any(k in all_text for k in ["ci/cd","pipeline","automat","deploy"]):
            qs.append("Is a CI/CD pipeline defined and automated for all environments?")
        if not any(k in all_text for k in ["test","qa","quality","coverage"]):
            qs.append("What is the testing strategy including unit, integration and E2E coverage?")
        qs.append("What is the deployment and rollback procedure?")
        if not any(k in all_text for k in ["monitor","alert","log","observ"]):
            qs.append("How will production issues be detected and alerted on?")
        groups.append({"category": "Deployment & Operations", "icon": "🚀", "questions": qs[:4]})

    elif group_id == "data_security_cost":
        qs = []
        if not any(k in all_text for k in ["encrypt","tls","at rest","in transit"]):
            qs.append("Is data encrypted both at rest and in transit?")
        if not any(k in all_text for k in ["gdpr","pci","hipaa","compliance","regulation"]):
            qs.append("Which regulatory compliance standards apply and are they met?")
        qs.append("What is the data retention and deletion policy?")
        if not any(k in all_text for k in ["cost","budget","cloud spend","finops"]):
            qs.append("What is the estimated cloud cost at steady state and peak load?")
        groups.append({"category": "Data, Security & Cost", "icon": "🔒", "questions": qs[:4]})

    # ── Risk questions (always included if risks present) ──────────────────
    if risks:
        risk_qs = [f"How is '{r[:80]}' being mitigated?" for r in risks[:2]]
        risk_qs.append("Which risk is most likely to delay the project and why?")
        groups.append({"category": "Risk Clarification", "icon": "🔴", "questions": risk_qs[:3]})

    # S4-03: gap-aware questions from weaknesses and missing categories
    gap_qs = []
    for w in (weaknesses or [])[:3]:
        text = w.get("text", "")
        cat = w.get("category", "")
        if text:
            gap_qs.append(f"The finding '{text[:80]}' was flagged as unclear — what additional detail is available?")
    for mc in (missing_categories or [])[:3]:
        gap_qs.append(f"No {mc} were identified in this review — are there any that apply?")
    if gap_qs:
        groups.append({"category": "Gaps & Weaknesses", "icon": "🔍", "questions": gap_qs[:5]})

    # S5-02: open decision points generate a Decisions group
    open_dps = [dp for dp in (decision_points or []) if dp.get("status", "open") == "open"]
    if open_dps:
        decision_qs = []
        for dp in open_dps[:3]:
            text = dp.get("text", "")
            if text:
                decision_qs.append(f"A decision is required: '{text[:80]}' — what are the options and who owns this decision?")
        if decision_qs:
            groups.append({"category": "Decisions", "icon": "🎯", "questions": decision_qs[:5]})

    return groups or [{"category": "General", "icon": "❓", "questions": [
        "What are the key success criteria for this project?",
        "What constraints or assumptions need to be validated?",
        "What are the top 3 risks and their mitigation plans?",
    ]}]


# ── Scope completeness ────────────────────────────────────────────────────────

def _scope_completeness(scope: str, intelligence: Dict[str, Any]) -> int:
    """Return 0–100 completeness score based on expected scope elements."""
    elements = {
        "objectives":  ["objective","goal","aim","purpose","target"],
        "deliverables":["deliver","output","milestone","produce"],
        "timeline":    ["timeline","schedule","deadline","week","month","sprint"],
        "budget":      ["budget","cost","fund","spend"],
        "stakeholders":["stakeholder","sponsor","client","owner"],
        "constraints": ["constraint","limit","restrict"],
        "assumptions": ["assum","prerequisite","expect"],
        "risks":       ["risk","threat"],
    }
    scope_lower = (scope or "").lower()
    intel_text  = " ".join(
        " ".join(intelligence.get(k, []) if isinstance(intelligence.get(k), list) else [])
        for k in ["risks","assumptions","constraints","dependencies"]
    ).lower()
    combined = scope_lower + " " + intel_text

    found = sum(
        1 for keywords in elements.values()
        if any(kw in combined for kw in keywords)
    )
    return round(found / len(elements) * 100)
