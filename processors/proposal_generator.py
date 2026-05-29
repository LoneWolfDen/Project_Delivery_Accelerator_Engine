"""Proposal Document Generator — DS-05.

Generates a structured proposal document FROM:
  hierarchy Version + Active Review

Two code paths:
  AI mode    — structured LLM prompt extracts/enriches each section
  files_only — template population from review findings (deterministic)

Gate: rejects if review quality_status == 'pending' (unless force=True).

Output: ProposalDocument dataclass → saved to proposal_documents table.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.proposal import (
    ProposalDocument, DeliveryPhase, GanttRow, RiskEntry, AssumptionEntry,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────
# Gate check
# ──────────────────────────────────────────────────────────────

def _check_generation_gate(
    project_id: str,
    hierarchy_version_id: str,
    review_id: str,
    force: bool = False,
) -> Dict[str, Any]:
    """Validate that version + active review are ready for proposal generation."""
    from models.hierarchy import _make_hierarchy_store

    store = _make_hierarchy_store(project_id)
    version = store.get_version(hierarchy_version_id)
    if version is None:
        return {"ok": False, "reason": f"Version {hierarchy_version_id} not found"}

    review = store.get_review(review_id)
    if review is None:
        return {"ok": False, "reason": f"Review {review_id} not found"}

    if version.active_review_id != review_id:
        return {
            "ok": False,
            "reason": (
                f"Review {review_id} is not the active review for version "
                f"{hierarchy_version_id}. Active review is: "
                f"'{version.active_review_id or 'none set'}'. "
                "Set it as active first."
            ),
        }

    if review.quality_status == "pending" and not force:
        return {
            "ok": False,
            "reason": (
                f"Review {review_id} has not been marked complete or interim "
                "(quality_status='pending'). Mark the review first, or pass force=True."
            ),
        }

    return {"ok": True, "version": version, "review": review}



# ──────────────────────────────────────────────────────────────
# files_only — template population
# ──────────────────────────────────────────────────────────────

def _generate_files_only(
    version,
    review,
    proposal_ver_id: str,
) -> ProposalDocument:
    """Populate proposal sections from review findings deterministically."""
    findings = review.findings or {}
    scope_text = version.scope or ""

    # ── Exec summary ──────────────────────────────────────────
    risk_count = len(findings.get("risks", []))
    dep_count  = len(findings.get("dependencies", []))
    exec_summary = (
        f"This proposal covers the delivery scope identified in version "
        f"{version.version_id} ({version.label}), reviewed by {review.persona}. "
        f"The analysis identified {risk_count} risks and {dep_count} dependencies. "
        f"Scope: {scope_text[:300]}{'...' if len(scope_text) > 300 else ''}"
    )

    # ── Risks ─────────────────────────────────────────────────
    risk_entries: List[RiskEntry] = []
    for r in findings.get("risks", []):
        text = r if isinstance(r, str) else str(r)
        risk_entries.append(RiskEntry(
            risk=text,
            category=_classify_risk_category(text),
            impact="medium",
            probability="medium",
            mitigation=f"Review and mitigate: {text[:80]}",
        ))

    # ── Assumptions ───────────────────────────────────────────
    assumption_entries: List[AssumptionEntry] = []
    for a in findings.get("assumptions", []):
        text = a if isinstance(a, str) else str(a)
        assumption_entries.append(AssumptionEntry(
            assumption=text,
            category=_classify_assumption_category(text),
        ))

    # ── Delivery phases (from action_items + dependencies) ────
    phases = _build_phases_from_findings(findings)

    # ── Gantt (from phases) ───────────────────────────────────
    gantt = _build_gantt_from_phases(phases)

    # ── Exclusions (from constraints) ─────────────────────────
    exclusions = [
        c if isinstance(c, str) else str(c)
        for c in findings.get("constraints", [])
    ]

    # ── Acceptance criteria (from action_items) ───────────────
    acceptance = [
        f"Delivery of: {a[:100]}" if isinstance(a, str) else str(a)
        for a in findings.get("action_items", [])[:5]
    ]
    if not acceptance:
        acceptance = ["Solution delivered and accepted by client stakeholders"]

    # ── RACI (template) ───────────────────────────────────────
    raci = _build_raci_template()

    doc = ProposalDocument(
        project_id=review.project_id,
        proposal_ver_id=proposal_ver_id,
        ai_backend="files_only",
        hierarchy_version_id=version.version_id,
        active_review_id=review.review_id,
        version_label=version.label,
        review_persona=review.persona,
        exec_summary=exec_summary,
        scope=scope_text,
        delivery_phases=phases,
        gantt_data=gantt,
        risks=risk_entries,
        assumptions=assumption_entries,
        exclusions=exclusions,
        responsibilities=raci,
        acceptance_criteria=acceptance,
    )
    doc.word_count = _count_words(doc)
    return doc



# ──────────────────────────────────────────────────────────────
# AI mode — LLM extraction
# ──────────────────────────────────────────────────────────────

def _generate_ai(
    version,
    review,
    proposal_ver_id: str,
    ai_backend: str,
) -> ProposalDocument:
    """Use LLM to generate enriched proposal sections."""
    try:
        from ai_backends import call_llm
        prompt = _build_generation_prompt(version, review)
        raw = call_llm(ai_backend, prompt, max_tokens=3000)
        return _parse_ai_response(raw, version, review, proposal_ver_id, ai_backend)
    except Exception:
        # Graceful fallback to files_only on any LLM error
        doc = _generate_files_only(version, review, proposal_ver_id)
        doc.ai_backend = f"{ai_backend}_fallback"
        return doc


def _build_generation_prompt(version, review) -> str:
    findings = review.findings or {}
    risks_text     = "\n".join(f"- {r}" for r in findings.get("risks", [])[:10])
    assumptions_text = "\n".join(f"- {a}" for a in findings.get("assumptions", [])[:10])
    deps_text      = "\n".join(f"- {d}" for d in findings.get("dependencies", [])[:10])
    constraints_text = "\n".join(f"- {c}" for c in findings.get("constraints", [])[:8])
    actions_text   = "\n".join(f"- {a}" for a in findings.get("action_items", [])[:10])

    return f"""You are a senior delivery consultant generating a client proposal.

PROJECT SCOPE:
{version.scope[:1000]}

REVIEW FINDINGS (persona: {review.persona}):
Risks:
{risks_text or '(none identified)'}

Assumptions:
{assumptions_text or '(none identified)'}

Dependencies:
{deps_text or '(none identified)'}

Constraints:
{constraints_text or '(none identified)'}

Action Items:
{actions_text or '(none identified)'}

Generate a structured proposal with EXACTLY these sections in order.
Use plain text, no markdown. Separate sections with the exact headers shown.

---EXEC_SUMMARY---
(2-3 sentences summarising the engagement, approach, and value)

---SCOPE---
(Clear scope statement, 3-5 sentences)

---DELIVERY_PHASES---
(3-5 phases, each on its own line: "Phase Name | Description | Duration in weeks")

---RISKS---
(Each risk on its own line: "Risk text | category | impact:high/medium/low | probability:high/medium/low | mitigation")

---ASSUMPTIONS---
(Each assumption on its own line: "Assumption text | category:delivery/resource/technical/process/organizational/client")

---EXCLUSIONS---
(Each exclusion on one line)

---ACCEPTANCE_CRITERIA---
(3-5 high-level acceptance criteria, one per line)

---CLIENT_RESPONSIBILITIES---
(3-5 client responsibilities, one per line)
"""


def _parse_ai_response(
    raw: str,
    version,
    review,
    proposal_ver_id: str,
    ai_backend: str,
) -> ProposalDocument:
    """Parse the structured LLM response into a ProposalDocument."""

    def _extract(text: str, section: str) -> str:
        pattern = rf"---{section}---\s*(.*?)(?=---[A-Z_]+---|$)"
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    exec_summary  = _extract(raw, "EXEC_SUMMARY")
    scope         = _extract(raw, "SCOPE")
    phases_raw    = _extract(raw, "DELIVERY_PHASES")
    risks_raw     = _extract(raw, "RISKS")
    assumptions_raw = _extract(raw, "ASSUMPTIONS")
    exclusions_raw  = _extract(raw, "EXCLUSIONS")
    acceptance_raw  = _extract(raw, "ACCEPTANCE_CRITERIA")
    client_resp_raw = _extract(raw, "CLIENT_RESPONSIBILITIES")

    # Parse phases
    phases: List[DeliveryPhase] = []
    week_cursor = 1
    for line in phases_raw.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 2:
            dur = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 4
            phases.append(DeliveryPhase(
                phase=parts[0], description=parts[1], duration_weeks=dur
            ))
            week_cursor += dur

    # Parse risks
    risk_entries: List[RiskEntry] = []
    for line in risks_raw.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if parts and parts[0]:
            risk_entries.append(RiskEntry(
                risk=parts[0],
                category=parts[1] if len(parts) > 1 else "delivery",
                impact=_extract_level(parts[2] if len(parts) > 2 else "", "medium"),
                probability=_extract_level(parts[3] if len(parts) > 3 else "", "medium"),
                mitigation=parts[4] if len(parts) > 4 else "",
            ))

    # Parse assumptions
    assumption_entries: List[AssumptionEntry] = []
    for line in assumptions_raw.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if parts and parts[0]:
            cat = parts[1].replace("category:", "").strip() if len(parts) > 1 else "delivery"
            assumption_entries.append(AssumptionEntry(assumption=parts[0], category=cat))

    exclusions = [l.strip() for l in exclusions_raw.splitlines() if l.strip()]
    acceptance = [l.strip() for l in acceptance_raw.splitlines() if l.strip()]
    client_resp = [l.strip() for l in client_resp_raw.splitlines() if l.strip()]

    # Build RACI with client responsibilities
    raci = _build_raci_template()
    if client_resp:
        raci["client_responsibilities"] = client_resp

    if not phases:
        phases = _build_phases_from_findings(review.findings or {})
    gantt = _build_gantt_from_phases(phases)

    doc = ProposalDocument(
        project_id=review.project_id,
        proposal_ver_id=proposal_ver_id,
        ai_backend=ai_backend,
        hierarchy_version_id=version.version_id,
        active_review_id=review.review_id,
        version_label=version.label,
        review_persona=review.persona,
        exec_summary=exec_summary or _generate_files_only(version, review, proposal_ver_id).exec_summary,
        scope=scope or version.scope,
        delivery_phases=phases,
        gantt_data=gantt,
        risks=risk_entries,
        assumptions=assumption_entries,
        exclusions=exclusions,
        responsibilities=raci,
        acceptance_criteria=acceptance,
    )
    doc.word_count = _count_words(doc)
    return doc



# ──────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────

def _classify_risk_category(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["security", "compliance", "gdpr", "auth"]):
        return "security"
    if any(w in t for w in ["resource", "skill", "staff", "team", "capacity"]):
        return "resource"
    if any(w in t for w in ["commercial", "budget", "cost", "price", "contract"]):
        return "commercial"
    if any(w in t for w in ["technical", "architecture", "integration", "api", "data"]):
        return "technical"
    if any(w in t for w in ["third", "vendor", "external", "dependency"]):
        return "external"
    return "delivery"


def _classify_assumption_category(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["resource", "team", "staff", "skill", "onboard"]):
        return "resource"
    if any(w in t for w in ["technical", "system", "infrastructure", "environment"]):
        return "technical"
    if any(w in t for w in ["process", "workflow", "procedure"]):
        return "process"
    if any(w in t for w in ["client", "customer", "stakeholder", "sponsor"]):
        return "client"
    if any(w in t for w in ["organisation", "org", "team structure", "governance"]):
        return "organizational"
    return "delivery"


def _extract_level(text: str, default: str) -> str:
    t = text.lower()
    if "high" in t:
        return "high"
    if "low" in t:
        return "low"
    if "medium" in t or "med" in t:
        return "medium"
    return default


def _build_phases_from_findings(findings: Dict[str, Any]) -> List[DeliveryPhase]:
    """Build standard delivery phases from findings when no explicit phases exist."""
    action_items = findings.get("action_items", [])
    deps = findings.get("dependencies", [])

    phases = [
        DeliveryPhase(
            phase="Discovery & Setup",
            description="Project initiation, environment setup, stakeholder alignment",
            duration_weeks=2,
            milestones=["Project kickoff", "Environment access confirmed"],
        ),
        DeliveryPhase(
            phase="Design & Architecture",
            description="Solution design, technical architecture, detailed planning",
            duration_weeks=3,
            milestones=["Architecture sign-off", "Detailed plan agreed"],
        ),
        DeliveryPhase(
            phase="Implementation",
            description="Core delivery, development, configuration",
            duration_weeks=max(4, len(action_items)),
            milestones=[str(a)[:60] for a in action_items[:3]] or ["Milestone 1"],
        ),
        DeliveryPhase(
            phase="Testing & Validation",
            description="UAT, performance testing, defect resolution",
            duration_weeks=2,
            milestones=["UAT sign-off", "Performance validated"],
        ),
        DeliveryPhase(
            phase="Go-Live & Handover",
            description="Production deployment, knowledge transfer, support transition",
            duration_weeks=1,
            milestones=["Go-live", "Handover complete"],
        ),
    ]
    return phases


def _build_gantt_from_phases(phases: List[DeliveryPhase]) -> List[GanttRow]:
    rows: List[GanttRow] = []
    week = 1
    for phase in phases:
        for milestone in (phase.milestones or [phase.phase]):
            rows.append(GanttRow(
                milestone=milestone,
                start_week=week,
                end_week=week + max(1, phase.duration_weeks - 1),
                owner="Delivery Team",
                phase=phase.phase,
            ))
        week += phase.duration_weeks
    return rows


def _build_raci_template() -> Dict[str, Any]:
    return {
        "roles": [
            "Project Manager", "Solution Architect", "Lead Developer",
            "QA Lead", "Client Sponsor", "Client SME",
        ],
        "responsibilities": [
            {"activity": "Project governance",        "PM": "A", "SA": "C", "Dev": "I", "QA": "I", "Sponsor": "R", "SME": "I"},
            {"activity": "Solution design",           "PM": "C", "SA": "R", "Dev": "C", "QA": "C", "Sponsor": "A", "SME": "C"},
            {"activity": "Development & config",      "PM": "I", "SA": "C", "Dev": "R", "QA": "C", "Sponsor": "I", "SME": "I"},
            {"activity": "Testing & UAT",             "PM": "C", "SA": "C", "Dev": "C", "QA": "R", "Sponsor": "A", "SME": "R"},
            {"activity": "Go-live approval",          "PM": "C", "SA": "C", "Dev": "C", "QA": "C", "Sponsor": "R", "SME": "C"},
            {"activity": "Knowledge transfer",        "PM": "A", "SA": "R", "Dev": "R", "QA": "C", "Sponsor": "I", "SME": "R"},
        ],
        "client_responsibilities": [
            "Provide timely access to environments and systems",
            "Assign and make available client SMEs for requirements and UAT",
            "Procure and provision required hardware/licences",
            "Ensure stakeholder availability for governance checkpoints",
            "Provide sign-off at agreed milestones",
        ],
    }


def _count_words(doc: ProposalDocument) -> int:
    text = " ".join([
        doc.exec_summary, doc.scope,
        " ".join(p.description for p in doc.delivery_phases),
        " ".join(r.risk for r in doc.risks),
        " ".join(a.assumption for a in doc.assumptions),
        " ".join(doc.exclusions),
        " ".join(doc.acceptance_criteria),
    ])
    return len(text.split())


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def generate_proposal_document(
    project_id: str,
    proposal_ver_id: str,
    hierarchy_version_id: str,
    review_id: str,
    ai_backend: str = "files_only",
    force: bool = False,
) -> Dict[str, Any]:
    """Generate a proposal document from Version + Active Review.

    Gate: rejects if review quality_status == 'pending' (unless force=True)
          or if review_id != version.active_review_id.

    Returns the saved ProposalDocument dict.
    """
    from db.decision_log import save_proposal_document, log_decision

    # Gate check
    gate = _check_generation_gate(project_id, hierarchy_version_id, review_id, force)
    if not gate["ok"]:
        return {"error": gate["reason"]}

    version = gate["version"]
    review  = gate["review"]

    # Generate
    if ai_backend != "files_only":
        doc = _generate_ai(version, review, proposal_ver_id, ai_backend)
    else:
        doc = _generate_files_only(version, review, proposal_ver_id)

    # Persist
    saved = save_proposal_document(doc.to_dict())

    # Log decision
    log_decision(
        project_id=project_id,
        entity_type="proposal_version",
        entity_id=proposal_ver_id,
        action="generated",
        actor="system",
        reason=f"Generated from version {hierarchy_version_id} + review {review_id}",
        metadata={
            "doc_id":               saved["doc_id"],
            "ai_backend":           ai_backend,
            "hierarchy_version_id": hierarchy_version_id,
            "active_review_id":     review_id,
            "word_count":           saved["word_count"],
        },
    )

    return saved
