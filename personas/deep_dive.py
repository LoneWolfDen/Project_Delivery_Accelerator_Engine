"""Persona Deep Dive Engine – Structured intelligence generation.

Triggered only when AI Mode = ON (non-files_only backend).

Inputs:
- Default persona
- User persona (custom prompt)
- Project scope
- Selected artefacts (active files)

Outputs (Deep Dive):
- Missing Areas
- Risk Flags
- Clarification Questions
- Suggested Additions to Scope

Features:
- Scope Validation (defined vs missing)
- Gap Identification (lifecycle, operational, commercial)
- Structured Prompt Generation
- Persona Feedback Loop (accept/add/re-run)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def run_deep_dive(
    persona_name: str,
    scope: str,
    intelligence: Dict[str, Any],
    active_files: List[Dict[str, Any]],
    custom_prompt: str = "",
    ai_backend: str = "files_only",
) -> Dict[str, Any]:
    """Run a Deep Dive analysis using the Persona Engine.

    Only triggered when AI Mode = ON (non-files_only backend).
    Falls back to structured heuristic analysis if AI unavailable.

    Args:
        persona_name: Persona being applied.
        scope: Project scope text.
        intelligence: Built intelligence dict.
        active_files: List of active file dicts.
        custom_prompt: User-provided persona context.
        ai_backend: AI backend (deep dive only runs for non-files_only).

    Returns:
        Deep Dive result dict.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Validate scope
    scope_validation = _validate_scope(scope, intelligence)

    # Identify gaps
    gaps = _identify_gaps(intelligence, active_files)

    # Generate structured prompts/questions
    prompts = _generate_structured_prompts(
        persona_name, scope_validation, gaps, intelligence
    )

    # Risk flags
    risk_flags = _extract_risk_flags(intelligence, gaps)

    # Suggested additions
    suggestions = _suggest_scope_additions(scope_validation, gaps, intelligence)

    deep_dive: Dict[str, Any] = {
        "timestamp": timestamp,
        "persona": persona_name,
        "ai_backend": ai_backend,
        "ai_mode": ai_backend != "files_only",
        "scope_validation": scope_validation,
        "deep_dive": {
            "missing_areas": gaps.get("missing_areas", []),
            "risk_flags": risk_flags,
            "clarification_questions": prompts.get("questions", []),
            "suggested_additions": suggestions,
        },
        "gaps": gaps,
        "structured_prompts": prompts,
        "file_coverage": {
            "active_files": len(active_files),
            "file_types": list(set(
                f.get("source_type", "unknown") for f in active_files
            )),
        },
        "feedback_loop": {
            "status": "pending",
            "accepted_suggestions": [],
            "rejected_suggestions": [],
            "added_to_prompt": [],
        },
    }

    # If AI backend is available, enhance with AI-generated insights
    if ai_backend != "files_only":
        ai_enhancement = _run_ai_deep_dive(
            persona_name, scope, intelligence, active_files, custom_prompt, ai_backend
        )
        if ai_enhancement:
            deep_dive["ai_enhancement"] = ai_enhancement
            # Merge AI-parsed structured fields back into the deep_dive output
            parsed = ai_enhancement.get("parsed", {})
            if parsed:
                dd = deep_dive["deep_dive"]
                # Extend lists — AI findings are additive to heuristic baseline
                dd["missing_areas"] = _merge_dd_list(
                    dd["missing_areas"],
                    [{"area": a, "severity": "medium", "suggestion": a}
                     for a in parsed.get("missing_areas", [])],
                )
                dd["risk_flags"] = _merge_dd_flags(
                    dd["risk_flags"],
                    parsed.get("risk_flags", []),
                )
                dd["clarification_questions"] = _dedup_strings(
                    dd["clarification_questions"] + parsed.get("clarification_questions", [])
                )
                dd["suggested_additions"] = _merge_dd_list(
                    dd["suggested_additions"],
                    [{"category": "ai", "suggestion": s, "priority": "medium"}
                     for s in parsed.get("suggested_additions", [])],
                )

    return deep_dive


def apply_feedback(
    deep_dive_result: Dict[str, Any],
    accepted: Optional[List[str]] = None,
    rejected: Optional[List[str]] = None,
    added_to_prompt: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Apply user feedback to close the persona feedback loop.

    User can:
    - Accept suggestions (add to scope)
    - Reject suggestions
    - Add to prompt for re-run

    Args:
        deep_dive_result: Previous deep dive output.
        accepted: List of accepted suggestion texts.
        rejected: List of rejected suggestion texts.
        added_to_prompt: List of items to add to next prompt.

    Returns:
        Updated deep dive result with feedback applied.
    """
    feedback = deep_dive_result.get("feedback_loop", {})
    feedback["status"] = "applied"
    feedback["applied_at"] = datetime.now(timezone.utc).isoformat()

    if accepted:
        feedback["accepted_suggestions"] = accepted
    if rejected:
        feedback["rejected_suggestions"] = rejected
    if added_to_prompt:
        feedback["added_to_prompt"] = added_to_prompt

    deep_dive_result["feedback_loop"] = feedback
    return deep_dive_result


# ──────────────────────────────────────────────────────────────
# Scope Validation
# ──────────────────────────────────────────────────────────────


def _validate_scope(scope: str, intelligence: Dict[str, Any]) -> Dict[str, Any]:
    """Validate what is defined vs missing in scope.

    Returns:
        Dict with defined_areas, missing_areas, completeness_score.
    """
    # Expected scope elements for a well-defined project
    expected_elements = [
        "objectives",
        "deliverables",
        "timeline",
        "budget",
        "stakeholders",
        "success_criteria",
        "constraints",
        "assumptions",
        "dependencies",
        "risks",
        "exclusions",
    ]

    defined_areas: List[str] = []
    missing_areas: List[str] = []

    scope_lower = scope.lower() if scope else ""
    intel_keys = set(intelligence.keys())

    # Check scope text and intelligence for each expected element
    element_keywords = {
        "objectives": ["objective", "goal", "aim", "purpose", "target"],
        "deliverables": ["deliver", "output", "artifact", "produce", "milestone"],
        "timeline": ["timeline", "schedule", "deadline", "date", "week", "month", "sprint"],
        "budget": ["budget", "cost", "fund", "spend", "price", "financial"],
        "stakeholders": ["stakeholder", "sponsor", "owner", "user", "client"],
        "success_criteria": ["success", "criteria", "kpi", "metric", "measure"],
        "constraints": ["constraint", "limit", "restrict", "boundary"],
        "assumptions": ["assum", "expect", "presume"],
        "dependencies": ["depend", "prerequisite", "block", "wait"],
        "risks": ["risk", "threat", "impact", "probability"],
        "exclusions": ["exclu", "out of scope", "not included", "excluded"],
    }

    for element, keywords in element_keywords.items():
        found = any(kw in scope_lower for kw in keywords)
        # Also check if intelligence has data for this
        if element in intel_keys and intelligence.get(element):
            found = True
        if found:
            defined_areas.append(element)
        else:
            missing_areas.append(element)

    completeness = len(defined_areas) / len(expected_elements) if expected_elements else 0

    return {
        "defined_areas": defined_areas,
        "missing_areas": missing_areas,
        "completeness_score": round(completeness, 2),
        "scope_length": len(scope),
        "has_scope": bool(scope and len(scope) > 20),
    }


# ──────────────────────────────────────────────────────────────
# Gap Identification
# ──────────────────────────────────────────────────────────────


def _identify_gaps(
    intelligence: Dict[str, Any], active_files: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Identify gaps in lifecycle, operational, and commercial areas.

    Returns:
        Dict with missing_areas, operational_blind_spots, commercial_risks.
    """
    gaps: Dict[str, Any] = {
        "missing_areas": [],
        "operational_blind_spots": [],
        "commercial_risks": [],
    }

    # Lifecycle gaps
    lifecycle_areas = {
        "testing_strategy": ["test", "qa", "quality", "validation"],
        "deployment_plan": ["deploy", "release", "rollout", "go-live"],
        "monitoring": ["monitor", "alert", "observ", "log", "dashboard"],
        "rollback_plan": ["rollback", "revert", "fallback", "disaster"],
        "training": ["train", "onboard", "knowledge", "handover"],
        "documentation": ["document", "wiki", "guide", "manual"],
    }

    all_text = " ".join([
        " ".join(intelligence.get("risks", [])),
        " ".join(intelligence.get("constraints", [])),
        " ".join(intelligence.get("action_items", [])),
        intelligence.get("scope", ""),
    ]).lower()

    for area, keywords in lifecycle_areas.items():
        if not any(kw in all_text for kw in keywords):
            gaps["missing_areas"].append({
                "area": area.replace("_", " ").title(),
                "severity": "high" if area in ("testing_strategy", "deployment_plan") else "medium",
                "suggestion": f"No {area.replace('_', ' ')} identified in project documents",
            })

    # Operational blind spots
    operational_checks = {
        "incident_response": ["incident", "response", "escalat", "on-call"],
        "capacity_planning": ["capacity", "scale", "load", "performance"],
        "backup_recovery": ["backup", "recovery", "restore", "dr"],
        "security_posture": ["security", "vulnerab", "audit", "penetration"],
    }

    for check, keywords in operational_checks.items():
        if not any(kw in all_text for kw in keywords):
            gaps["operational_blind_spots"].append({
                "area": check.replace("_", " ").title(),
                "suggestion": f"No {check.replace('_', ' ')} coverage found",
            })

    # Commercial risks
    commercial_checks = {
        "pricing_model": ["price", "cost model", "pricing", "billing"],
        "contract_terms": ["contract", "sla", "penalty", "liability"],
        "vendor_lock_in": ["vendor", "lock-in", "proprietary", "exit"],
        "roi_justification": ["roi", "return on", "business case", "payback"],
    }

    for check, keywords in commercial_checks.items():
        if not any(kw in all_text for kw in keywords):
            gaps["commercial_risks"].append({
                "area": check.replace("_", " ").title(),
                "suggestion": f"No {check.replace('_', ' ')} documentation found",
            })

    return gaps


# ──────────────────────────────────────────────────────────────
# Structured Prompt Generation
# ──────────────────────────────────────────────────────────────


def _generate_structured_prompts(
    persona_name: str,
    scope_validation: Dict[str, Any],
    gaps: Dict[str, Any],
    intelligence: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate structured questions and focus areas.

    Returns:
        Dict with questions, focus_areas, risks.
    """
    questions: List[str] = []
    focus_areas: List[str] = []

    # Questions from scope gaps
    for missing in scope_validation.get("missing_areas", []):
        questions.append(f"What is the {missing} for this project?")

    # Questions from lifecycle gaps
    for gap in gaps.get("missing_areas", []):
        area = gap["area"]
        questions.append(f"How will {area.lower()} be handled?")
        if gap.get("severity") == "high":
            focus_areas.append(f"HIGH PRIORITY: Define {area.lower()}")

    # Questions from operational blind spots
    for blind_spot in gaps.get("operational_blind_spots", []):
        questions.append(
            f"What is the plan for {blind_spot['area'].lower()}?"
        )

    # Focus areas from risks
    risks = intelligence.get("risks", [])
    if len(risks) > 5:
        focus_areas.append(f"Address {len(risks)} identified risks – prioritise top 5")
    if not risks:
        focus_areas.append("No risks identified – conduct risk workshop")

    return {
        "questions": questions[:15],  # Cap at 15 most important
        "focus_areas": focus_areas[:10],
        "risk_count": len(risks),
    }


def _extract_risk_flags(
    intelligence: Dict[str, Any], gaps: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Extract and prioritise risk flags.

    Returns:
        List of risk flag dicts with severity.
    """
    flags: List[Dict[str, str]] = []

    # From gaps
    high_gaps = [g for g in gaps.get("missing_areas", []) if g.get("severity") == "high"]
    for gap in high_gaps:
        flags.append({
            "flag": f"Missing: {gap['area']}",
            "severity": "high",
            "source": "gap_analysis",
        })

    # From intelligence risks
    risks = intelligence.get("risks", [])
    critical_keywords = ["critical", "blocker", "showstopper", "failure", "breach"]
    for risk in risks[:10]:
        risk_lower = risk.lower() if isinstance(risk, str) else ""
        severity = "high" if any(kw in risk_lower for kw in critical_keywords) else "medium"
        flags.append({
            "flag": risk if isinstance(risk, str) else str(risk),
            "severity": severity,
            "source": "intelligence",
        })

    # From scope issues
    return flags[:20]  # Cap at 20


def _suggest_scope_additions(
    scope_validation: Dict[str, Any],
    gaps: Dict[str, Any],
    intelligence: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Generate suggested additions to scope.

    Returns:
        List of suggestion dicts.
    """
    suggestions: List[Dict[str, str]] = []

    for missing in scope_validation.get("missing_areas", []):
        suggestions.append({
            "category": "scope_element",
            "suggestion": f"Add {missing} section to scope document",
            "priority": "high" if missing in ("objectives", "deliverables", "timeline") else "medium",
        })

    for gap in gaps.get("missing_areas", []):
        suggestions.append({
            "category": "lifecycle",
            "suggestion": f"Define {gap['area'].lower()} before execution",
            "priority": gap.get("severity", "medium"),
        })

    for risk in gaps.get("commercial_risks", []):
        suggestions.append({
            "category": "commercial",
            "suggestion": f"Document {risk['area'].lower()}",
            "priority": "medium",
        })

    return suggestions[:15]


# ──────────────────────────────────────────────────────────────
# AI Enhancement (when AI mode is ON)
# ──────────────────────────────────────────────────────────────


def _run_ai_deep_dive(
    persona_name: str,
    scope: str,
    intelligence: Dict[str, Any],
    active_files: List[Dict[str, Any]],
    custom_prompt: str,
    ai_backend: str,
) -> Optional[Dict[str, Any]]:
    """Run AI-enhanced deep dive analysis.

    Only called when ai_backend != 'files_only'.
    Parses the LLM response into structured fields so they are merged back
    into the heuristic baseline (missing_areas, risk_flags,
    clarification_questions, suggested_additions).
    Falls back gracefully if AI is unavailable.

    Returns:
        Dict with ``raw_output``, ``parsed`` (structured fields), and
        ``ai_metadata``.  Returns None on failure.
    """
    try:
        from ai_backends import get_backend  # noqa: PLC0415
        from processors.context_builder import build_context_summary  # noqa: PLC0415

        context_summary = build_context_summary(intelligence)

        prompt = f"""As a {persona_name}, perform a Deep Dive analysis on this project.

## Project Scope
{scope[:1000] if scope else 'No explicit scope defined.'}

## Intelligence Summary
{context_summary[:2000]}

{f'## Additional Context{chr(10)}{custom_prompt}' if custom_prompt else ''}

## Required Output
Return ONLY a JSON object with these keys (no markdown, no prose):
{{
  "missing_areas":           ["area not covered", ...],
  "risk_flags":              ["HIGH: risk description", ...],
  "clarification_questions": ["question?", ...],
  "suggested_additions":     ["add X to scope", ...]
}}

Rules:
- Each list contains plain strings (min 15 chars each).
- Prefix risk_flags items with severity: "CRITICAL:", "HIGH:", "MEDIUM:", or "LOW:".
- Maximum 10 items per list.
- Return ONLY the JSON object."""

        backend = get_backend(ai_backend)
        response = backend.generate(
            prompt=prompt,
            system_prompt=f"You are a senior {persona_name} performing deep analysis. Return only valid JSON.",
            temperature=0.3,
            max_tokens=1500,
        )

        if not response.success or not response.text:
            return None

        parsed = _parse_deep_dive_response(response.text)

        return {
            "raw_output": response.text,
            "parsed": parsed,
            "ai_metadata": {
                "model": response.model,
                "backend": ai_backend,
                "tokens_used": response.tokens_used,
                "latency_ms": response.latency_ms,
            },
        }

    except Exception:
        pass

    return None


def _parse_deep_dive_response(text: str) -> Dict[str, List[str]]:
    """Parse the LLM deep dive response into structured fields.

    Handles clean JSON, markdown-fenced JSON, and JSON embedded in prose.
    Returns empty lists on any parse failure.
    """
    import json  # noqa: PLC0415
    import re    # noqa: PLC0415

    empty: Dict[str, List[str]] = {
        "missing_areas": [],
        "risk_flags": [],
        "clarification_questions": [],
        "suggested_additions": [],
    }

    # Strip markdown fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    candidate = fenced.group(1) if fenced else text

    # Find first {...} block
    brace = re.search(r"\{[\s\S]+\}", candidate)
    if not brace:
        return empty

    try:
        data = json.loads(brace.group(0))
    except (json.JSONDecodeError, ValueError):
        return empty

    result: Dict[str, List[str]] = {}
    for key in empty:
        raw = data.get(key, [])
        result[key] = [
            str(item).strip()
            for item in (raw if isinstance(raw, list) else [])
            if isinstance(item, str) and len(str(item).strip()) >= 15
        ][:10]

    return result


# ── Merge helpers ─────────────────────────────────────────────────────────────

def _merge_dd_list(
    base: List[Any], additions: List[Any]
) -> List[Any]:
    """Add novel items to a list, deduplicating by lowercased text."""
    seen = {
        (item.get("area", "") + item.get("suggestion", "")).lower()
        for item in base
        if isinstance(item, dict)
    }
    result = list(base)
    for item in additions:
        key = (item.get("area", "") + item.get("suggestion", "")).lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _merge_dd_flags(
    base: List[Any], additions: List[str]
) -> List[Any]:
    """Merge AI risk flag strings into the structured flags list."""
    seen = {str(f.get("flag", "")).lower() for f in base if isinstance(f, dict)}
    result = list(base)
    for item in additions:
        item = str(item).strip()
        # Parse "SEVERITY: description" prefix
        sev = "medium"
        flag_text = item
        for prefix in ("CRITICAL:", "HIGH:", "MEDIUM:", "LOW:"):
            if item.upper().startswith(prefix):
                sev = prefix.rstrip(":").lower()
                flag_text = item[len(prefix):].strip()
                break
        if flag_text.lower() not in seen:
            seen.add(flag_text.lower())
            result.append({"flag": flag_text, "severity": sev, "source": "ai"})
    return result


def _dedup_strings(items: List[str]) -> List[str]:
    """Deduplicate a list of strings case-insensitively."""
    seen: set = set()
    out = []
    for item in items:
        norm = item.lower().strip()
        if norm and norm not in seen:
            seen.add(norm)
            out.append(item)
    return out
