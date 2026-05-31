"""Proposal Document Generator — DS-05 / PDAE-MS-01.

Generates a structured proposal document FROM:
  hierarchy Version + Active Review  [single-review path — unchanged]
  hierarchy Version + Active Review + supplemental reviews  [multi-review path]

Two generation code paths:
  AI mode    — structured LLM prompt extracts/enriches each section
  files_only — template population from review findings (deterministic)

Gate: rejects if review quality_status == 'pending' (unless force=True).

Sprint 2 additions (PDAE-MS-01):
  - supplemental_review_ids param (optional, default None)
  - ProposalInputSnapshot captured on every call
  - synthesize_reviews() called when supplementals present
  - _run_proposal_review_pass() — six-domain critique (AI or deterministic)
  - All new artifacts stored on ProposalDocument and persisted to DB

Output: ProposalDocument dataclass → saved to proposal_documents table.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.proposal import (
    ProposalDocument, DeliveryPhase, GanttRow, RiskEntry, AssumptionEntry,
    ProposalInputSnapshot, ProposalReviewPass, ReviewPassDomain,
    ProposalCoverage, DecisionSummary,
)

logger = logging.getLogger(__name__)


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
        from ai_backends import get_backend
        prompt = _build_generation_prompt(version, review)
        backend = get_backend(ai_backend)
        system_prompt = (
            "You are a senior delivery consultant generating a structured client proposal. "
            "Follow the output format exactly. Use plain text only, no markdown."
        )
        response = backend.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=3000,
        )
        if not response.success:
            raise RuntimeError(f"LLM call failed: {response.error}")
        return _parse_ai_response(response.text, version, review, proposal_ver_id, ai_backend)
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
# PDAE-MS-01  Proposal Review Pass (Sprint 2 — S2-03)
# ──────────────────────────────────────────────────────────────

# Keyword signals used by the deterministic (files_only) review pass.
_BLOCKER_KEYWORDS = {"must", "required", "block", "cannot proceed", "prevent"}

_DOMAIN_SIGNALS: Dict[str, List[str]] = {
    "scope":               ["scope", "deliver", "objective", "requirement", "in scope", "out of scope"],
    "architecture":        ["architecture", "design", "integration", "platform", "infrastructure", "api", "system"],
    "delivery":            ["timeline", "phase", "milestone", "sprint", "delivery", "schedule", "deadline"],
    "security_compliance": ["security", "compliance", "gdpr", "auth", "encryption", "audit", "access", "iso"],
    "operations":          ["monitor", "sla", "runbook", "support", "handover", "alert", "incident", "operations"],
    "commercials":         ["budget", "cost", "commercial", "pricing", "contract", "margin", "invoic"],
}


def _run_proposal_review_pass(
    doc: ProposalDocument,
    conflicts: List[Any],
    ai_backend: str,
) -> ProposalReviewPass:
    """Critique the generated proposal across six domains.

    AI path:  single LLM call returning structured per-domain critique.
    files_only: deterministic scan of doc content using keyword signals.

    Always returns a fully-populated ProposalReviewPass — never None.
    """
    from datetime import datetime, timezone as _tz
    generated_at = datetime.now(_tz.utc).isoformat()

    if ai_backend != "files_only":
        try:
            result = _review_pass_ai(doc, conflicts, ai_backend, generated_at)
            if result is not None:
                return result
        except Exception as exc:
            logger.warning("Review pass LLM call failed (%s): %s — using deterministic fallback", ai_backend, exc)

    return _review_pass_deterministic(doc, conflicts, generated_at, ai_backend)


def _review_pass_ai(
    doc: ProposalDocument,
    conflicts: List[Any],
    ai_backend: str,
    generated_at: str,
) -> Optional[ProposalReviewPass]:
    """Call LLM for six-domain critique. Returns None on failure."""
    from ai_backends import get_backend

    conflict_lines = "\n".join(
        f"  - {c.description if hasattr(c, 'description') else str(c)}"
        for c in conflicts
    ) or "  (none)"

    phases_text = "\n".join(
        f"  - {p.phase}: {p.description} ({p.duration_weeks}w)"
        for p in doc.delivery_phases[:5]
    ) or "  (none)"
    risks_text = "\n".join(f"  - {r.risk}" for r in doc.risks[:8]) or "  (none)"
    assumptions_text = "\n".join(f"  - {a.assumption}" for a in doc.assumptions[:8]) or "  (none)"

    prompt = f"""You are a delivery assurance reviewer. Critique the proposal below across six domains.
For each domain provide three lists: what is covered well, what is still weak or underspecified, and what may block sign-off.

Domains: Scope | Architecture | Delivery | Security/Compliance | Operations | Commercials

PROPOSAL CONTENT:
Executive Summary: {doc.exec_summary[:400]}
Scope: {doc.scope[:400]}
Delivery Phases:
{phases_text}
Key Risks:
{risks_text}
Key Assumptions:
{assumptions_text}

UNRESOLVED CONFLICTS FROM SYNTHESIS:
{conflict_lines}

Output using EXACTLY these headers (replace DOMAIN with: SCOPE, ARCHITECTURE, DELIVERY, SECURITY_COMPLIANCE, OPERATIONS, COMMERCIALS):
---DOMAIN_COVERED_WELL---
---DOMAIN_STILL_WEAK---
---DOMAIN_BLOCKERS---
"""
    backend = get_backend(ai_backend)
    response = backend.generate(
        prompt=prompt,
        system_prompt="You are a senior delivery assurance reviewer. Be specific, concise, and evidence-based.",
        temperature=0.2,
        max_tokens=2000,
    )
    if not response.success:
        return None

    raw = response.text or ""
    domain_map = {
        "scope":               "SCOPE",
        "architecture":        "ARCHITECTURE",
        "delivery":            "DELIVERY",
        "security_compliance": "SECURITY_COMPLIANCE",
        "operations":          "OPERATIONS",
        "commercials":         "COMMERCIALS",
    }

    def _parse_domain(key: str) -> ReviewPassDomain:
        prefix = domain_map[key]
        return ReviewPassDomain(
            covered_well=_extract_review_pass_lines(raw, f"{prefix}_COVERED_WELL"),
            still_weak=_extract_review_pass_lines(raw, f"{prefix}_STILL_WEAK"),
            may_block_signoff=_extract_review_pass_lines(raw, f"{prefix}_BLOCKERS"),
        )

    return ProposalReviewPass(
        scope=_parse_domain("scope"),
        architecture=_parse_domain("architecture"),
        delivery=_parse_domain("delivery"),
        security_compliance=_parse_domain("security_compliance"),
        operations=_parse_domain("operations"),
        commercials=_parse_domain("commercials"),
        generated_by=ai_backend,
        generated_at=generated_at,
    )


def _review_pass_deterministic(
    doc: ProposalDocument,
    conflicts: List[Any],
    generated_at: str,
    ai_backend: str,
) -> ProposalReviewPass:
    """Deterministic keyword-based review pass for files_only mode."""
    # Aggregate all text content per domain signal set
    all_text = " ".join([
        doc.exec_summary, doc.scope,
        " ".join(r.risk for r in doc.risks),
        " ".join(a.assumption for a in doc.assumptions),
        " ".join(p.description for p in doc.delivery_phases),
        " ".join(doc.acceptance_criteria),
    ]).lower()

    # Count items found per domain
    risk_texts = [r.risk.lower() for r in doc.risks]
    assumption_texts = [a.assumption.lower() for a in doc.assumptions]
    action_texts = [p.description.lower() for p in doc.delivery_phases]

    conflict_descs = [
        c.description if hasattr(c, "description") else str(c)
        for c in (conflicts or [])
    ]

    def _domain_pass(domain: str) -> ReviewPassDomain:
        signals = _DOMAIN_SIGNALS[domain]
        # Items that mention domain signals
        matched_risks = [r for r in doc.risks if any(s in r.risk.lower() for s in signals)]
        matched_assumptions = [a for a in doc.assumptions if any(s in a.assumption.lower() for s in signals)]
        matched_count = len(matched_risks) + len(matched_assumptions)

        covered_well: List[str] = []
        still_weak: List[str] = []
        may_block: List[str] = []

        if matched_count >= 2:
            covered_well.append(f"{domain.replace('_', '/').title()} concerns identified with sufficient detail.")
        elif matched_count == 1:
            still_weak.append(f"{domain.replace('_', '/').title()} has limited coverage — only {matched_count} item(s) found.")
        else:
            still_weak.append(f"{domain.replace('_', '/').title()} not addressed in current proposal content.")

        # Blocker detection: look for blocker keywords in matched items
        all_matched_text = " ".join(
            [r.risk for r in matched_risks] + [a.assumption for a in matched_assumptions]
        ).lower()
        for kw in _BLOCKER_KEYWORDS:
            if kw in all_matched_text:
                may_block.append(f"Item containing '{kw}' may block sign-off: review before submission.")
                break

        # Surface conflicts that affect this domain
        for desc in conflict_descs:
            if any(s in desc.lower() for s in signals):
                may_block.append(f"Conflict detected: {desc[:120]}")

        return ReviewPassDomain(
            covered_well=covered_well,
            still_weak=still_weak,
            may_block_signoff=may_block,
        )

    return ProposalReviewPass(
        scope=_domain_pass("scope"),
        architecture=_domain_pass("architecture"),
        delivery=_domain_pass("delivery"),
        security_compliance=_domain_pass("security_compliance"),
        operations=_domain_pass("operations"),
        commercials=_domain_pass("commercials"),
        generated_by=f"{ai_backend}_deterministic" if ai_backend != "files_only" else "files_only",
        generated_at=generated_at,
    )


def _extract_review_pass_lines(raw: str, header: str) -> List[str]:
    """Extract bullet lines from a ---HEADER--- section."""
    pattern = rf"---{re.escape(header)}---\s*(.*?)(?=---[A-Z_]+---|$)"
    match = re.search(pattern, raw, re.DOTALL)
    if not match:
        return []
    block = match.group(1).strip()
    lines = [ln.strip().lstrip("- ").strip() for ln in block.splitlines()]
    return [ln for ln in lines if ln]


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
    supplemental_review_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate a proposal document from Version + Active Review.

    Gate: rejects if review quality_status == 'pending' (unless force=True)
          or if review_id != version.active_review_id.

    PDAE-MS-01 (Sprint 2):
      supplemental_review_ids — if non-empty, synthesis path is used:
        1. ProposalInputSnapshot captured
        2. synthesize_reviews() called → ReconciliationResult
        3. Reconciled findings used as proposal input
        4. _run_proposal_review_pass() always runs
        5. All artifacts stored on ProposalDocument

    PDAE-MS-01 (Sprint 3):
        6. compute_proposal_coverage() → ProposalCoverage (always runs)
        7. _run_decision_summary() → DecisionSummary (always runs)

    Returns the saved ProposalDocument dict.
    """
    from db.decision_log import save_proposal_document, log_decision

    # ── Gate check (unchanged) ────────────────────────────────
    gate = _check_generation_gate(project_id, hierarchy_version_id, review_id, force)
    if not gate["ok"]:
        return {"error": gate["reason"]}

    version = gate["version"]
    review  = gate["review"]

    # ── S2-01: ProposalInputSnapshot — always captured ────────
    supp_ids = [s for s in (supplemental_review_ids or []) if s and s != review_id]
    all_selected = [review_id] + supp_ids
    snapshot = ProposalInputSnapshot(
        anchor_review_id=review_id,
        selected_review_ids=all_selected,
        selected_version_id=hierarchy_version_id,
        generation_mode="multi" if supp_ids else "single",
        captured_at=_now(),
    )

    # ── S2-02: Synthesis path (multi-review) ──────────────────
    reconciliation_result_dict: Optional[Dict[str, Any]] = None
    findings_override: Optional[Dict[str, Any]] = None
    conflicts: List[Any] = []

    if supp_ids:
        try:
            from models.hierarchy import _make_hierarchy_store
            from processors.review_synthesizer import synthesize_reviews

            store = _make_hierarchy_store(project_id)
            supplemental_reviews = []
            for sid in supp_ids:
                sup_review = store.get_review(sid)
                if sup_review is None:
                    return {"error": f"Supplemental review '{sid}' not found"}
                supplemental_reviews.append(sup_review)

            reconciliation = synthesize_reviews(
                anchor_review=review,
                supplemental_reviews=supplemental_reviews,
                version_scope=getattr(version, "scope", "") or "",
                ai_backend=ai_backend,
            )
            reconciliation_result_dict = reconciliation.to_dict()
            findings_override = reconciliation.reconciled_findings
            conflicts = reconciliation.contradictions
        except Exception as exc:
            logger.warning(
                "Synthesis failed for project %s — falling back to single-review path. Error: %s",
                project_id, exc,
            )
            # Non-fatal: fall through to single-review generation

    # ── Generate document sections ────────────────────────────
    # If synthesis produced reconciled findings, inject them into review
    # via a lightweight shim so _generate_* functions see one consistent object.
    generation_review = review
    if findings_override is not None:
        generation_review = _FindingsShim(review, findings_override)

    if ai_backend != "files_only":
        doc = _generate_ai(version, generation_review, proposal_ver_id, ai_backend)
    else:
        doc = _generate_files_only(version, generation_review, proposal_ver_id)

    # ── S2-03: Proposal Review Pass — always runs ─────────────
    review_pass = _run_proposal_review_pass(doc, conflicts, ai_backend)

    # ── S3-01: Proposal Coverage — always runs ────────────────
    from processors.review_synthesizer import (
        extract_scope_themes,
        compute_proposal_coverage,
        merge_decision_points,
        _run_decision_summary,
    )

    # Build reconciliation object suitable for coverage (may be None on single-review path)
    _reconciliation_for_coverage = None
    if reconciliation_result_dict is not None:
        _reconciliation_for_coverage = reconciliation_result_dict
    else:
        # Single-review: wrap review.findings in the same reconciled_findings shape
        _reconciliation_for_coverage = {
            "reconciled_findings": getattr(review, "findings", {}) or {}
        }

    scope_text   = getattr(version, "scope", "") or ""
    scope_themes = extract_scope_themes(
        scope_text,
        (_reconciliation_for_coverage or {}).get("reconciled_findings", {}),
    )
    proposal_coverage: ProposalCoverage = compute_proposal_coverage(
        _reconciliation_for_coverage,
        review_pass,
        scope_themes,
    )

    # ── S3-02: Decision Summary — always runs ─────────────────
    # Collect reviews for decision-point merging
    _all_reviews_for_ds: List[Any] = [review]
    if supp_ids:
        try:
            from models.hierarchy import _make_hierarchy_store as _hs
            _store_ds = _hs(project_id)
            for sid in supp_ids:
                _sup = _store_ds.get_review(sid)
                if _sup is not None:
                    _all_reviews_for_ds.append(_sup)
        except Exception:
            pass  # non-fatal — use anchor review only

    merged_decisions = merge_decision_points(_all_reviews_for_ds)
    _recon_notes = (
        reconciliation_result_dict.get("reconciliation_notes", "")
        if reconciliation_result_dict else ""
    )
    decision_summary: DecisionSummary = _run_decision_summary(
        merged_decisions=merged_decisions,
        reconciliation_notes=_recon_notes,
        selected_review_ids=all_selected,
        ai_backend=ai_backend,
    )

    # ── Attach all artifacts ──────────────────────────────────
    doc.input_snapshot        = snapshot.to_dict()
    doc.reconciliation_result = reconciliation_result_dict   # None on single-review
    doc.review_pass           = review_pass.to_dict()
    doc.proposal_coverage     = proposal_coverage.to_dict()
    doc.decision_summary      = decision_summary.to_dict()
    # forward_guidance → Sprint 4

    # ── Persist ───────────────────────────────────────────────
    saved = save_proposal_document(doc.to_dict())

    # S7-02: annotate with Decision Readiness (non-blocking)
    try:
        from processors.review_quality import compute_decision_readiness
        from dataclasses import asdict as _asdict
        try:
            review_dict = _asdict(review)
        except TypeError:
            review_dict = review.__dict__ if hasattr(review, "__dict__") else {}
        readiness = compute_decision_readiness(review_dict)
        saved["readiness"] = readiness
    except Exception:
        pass

    # ── Audit log ─────────────────────────────────────────────
    log_decision(
        project_id=project_id,
        entity_type="proposal_version",
        entity_id=proposal_ver_id,
        action="generated",
        actor="system",
        reason=f"Generated from version {hierarchy_version_id} + review {review_id}",
        metadata={
            "doc_id":                  saved.get("doc_id", ""),
            "ai_backend":              ai_backend,
            "hierarchy_version_id":    hierarchy_version_id,
            "active_review_id":        review_id,
            "supplemental_review_ids": supp_ids,
            "generation_mode":         snapshot.generation_mode,
            "word_count":              saved.get("word_count", 0),
            "coverage_statuses": {
                d: (saved.get("proposal_coverage") or {}).get(d, {}).get("status", "")
                for d in ["scope", "architecture", "delivery",
                          "security_compliance", "operations", "commercials"]
            },
            "open_decision_count": len(
                (saved.get("decision_summary") or {}).get("open", [])
            ),
            "blocker_count": len(
                (saved.get("decision_summary") or {}).get("sign_off_blockers", [])
            ),
        },
    )

    return saved


# ──────────────────────────────────────────────────────────────
# Internal shim — inject reconciled findings without mutating Review
# ──────────────────────────────────────────────────────────────

class _FindingsShim:
    """Thin wrapper around a Review that replaces .findings with reconciled data.

    All other attributes delegate to the wrapped review unchanged.
    This avoids mutating the original Review dataclass.
    """

    def __init__(self, review: Any, reconciled_findings: Dict[str, Any]) -> None:
        self._review = review
        self.findings = reconciled_findings

    def __getattr__(self, name: str) -> Any:
        return getattr(self._review, name)
