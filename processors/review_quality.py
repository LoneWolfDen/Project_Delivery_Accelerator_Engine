"""Review Quality Gate — DS-04.

Enforces that a review meets minimum quality before it can be:
- Marked as the Active Review for a Version
- Used as the source for a Proposal Version

Quality check rules
───────────────────
- Coverage: each of 5 standard categories must have ≥ 70% of the expected
  item count (i.e. at least 1 item present — the 70% gate is per-category
  presence, not absolute count, because there is no fixed "expected" count).
  In practice: category present with ≥1 item = passes its slot (20 pts each).
- Total score 0–100 (5 categories × 20 pts).
- Gate passes at score ≥ 70 (≥ 4 out of 5 categories present).
- User can override to 'interim' status (partial review, acknowledged).
- User can mark 'complete' which requires gate pass OR explicit override.

Decision log entry written on every state change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

STANDARD_CATEGORIES = [
    "risks", "assumptions", "dependencies", "constraints", "action_items"
]
GATE_THRESHOLD = 70          # minimum score to auto-pass gate
POINTS_PER_CATEGORY = 20     # 5 categories × 20 = 100

# S4-01: phrases that signal low confidence / unresolved areas in findings text
_WEAKNESS_SIGNALS = [
    "unclear", "not defined", "not specified", "tbc", "tbd", "unknown",
    "assumed", "assumption", "to be confirmed", "to be agreed", "not documented",
    "not clear", "no information", "missing", "pending", "not yet", "not provided",
    "unresolved", "low confidence", "not stated", "unconfirmed", "not confirmed",
    "no detail", "no details", "insufficient", "vague", "undecided",
]

# S4-01: minimum word count — short findings are flagged as weak
_WEAK_ITEM_MIN_WORDS = 8

# S5-01: phrases that signal a decision must be made
_DECISION_SIGNALS = [
    "choose between", "decide", "which approach", "platform choice",
    "dr vs", "phasing", "cost trade-off", "in scope or out",
    "option a", "option b", "we need to decide", "decision required",
    "trade-off", "tradeoff", "versus", " vs ", "either", "or both",
    "make a decision", "needs a decision", "decision needed",
]

# Valid status values for a decision point (S5-03)
DECISION_STATUSES = ("open", "addressed", "validated", "rejected")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────
# Completeness scoring
# ──────────────────────────────────────────────────────────────

def compute_completeness_score(findings: Dict[str, Any]) -> Dict[str, Any]:
    """Compute completeness score from review findings dict.

    Returns:
        {
            score: int (0-100),
            categories: {cat: {present: bool, count: int}},
            missing: [str],
            passed: bool
        }
    """
    category_results: Dict[str, Any] = {}
    missing: List[str] = []
    score = 0

    for cat in STANDARD_CATEGORIES:
        items = findings.get(cat, [])
        count = len(items) if isinstance(items, list) else 0
        present = count > 0
        category_results[cat] = {"present": present, "count": count}
        if present:
            score += POINTS_PER_CATEGORY
        else:
            missing.append(cat)

    return {
        "score":      score,
        "categories": category_results,
        "missing":    missing,
        "passed":     score >= GATE_THRESHOLD,
    }


# ──────────────────────────────────────────────────────────────
# S4-01: Weakness extraction
# ──────────────────────────────────────────────────────────────

def extract_weaknesses(findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive structured weaknesses from review findings.

    A weakness is a finding item that:
    - contains a signal phrase (unclear, TBC, assumed, not defined, …), OR
    - is very short (< _WEAK_ITEM_MIN_WORDS words) suggesting low detail.

    Returns a list of dicts:
        [{id, text, category, status}]
    where status defaults to "open".

    Rules:
    - Only inspects existing findings — never invents data.
    - Deterministic: same findings always produce same weaknesses.
    - Backward-compatible: returns [] for empty or None findings.
    """
    if not findings or not isinstance(findings, dict):
        return []

    weaknesses: List[Dict[str, Any]] = []
    seen: set = set()          # deduplicate by normalised text

    for category, items in findings.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if not text:
                continue

            norm = text.lower()
            is_weak = (
                any(signal in norm for signal in _WEAKNESS_SIGNALS)
                or len(text.split()) < _WEAK_ITEM_MIN_WORDS
            )

            if is_weak and norm not in seen:
                seen.add(norm)
                weaknesses.append({
                    "id":       f"w{len(weaknesses) + 1}",
                    "text":     text,
                    "category": category,
                    "status":   "open",
                })

    return weaknesses


# ──────────────────────────────────────────────────────────────
# S4-02: Missing category detection
# ──────────────────────────────────────────────────────────────

def compute_missing_categories(findings: Dict[str, Any]) -> List[str]:
    """Return STANDARD_CATEGORIES that have zero findings.

    Computed on-read from existing findings — no new DB column needed.

    Returns a list of category names (strings), e.g. ["risks", "constraints"].
    Returns [] when all standard categories have at least one item.
    """
    if not findings or not isinstance(findings, dict):
        return list(STANDARD_CATEGORIES)

    return [
        cat for cat in STANDARD_CATEGORIES
        if not (isinstance(findings.get(cat), list) and len(findings.get(cat, [])) > 0)
    ]


# ──────────────────────────────────────────────────────────────
# S5-01: Decision point extraction
# ──────────────────────────────────────────────────────────────

def extract_decision_points(findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive structured decision points from review findings.

    A decision point is a finding item that contains one or more
    decision-signal phrases (choose between, decide, which approach, …).

    Returns a list of dicts:
        [{id, text, category, status, linked_finding}]
    where status defaults to "open" and linked_finding is the
    original finding text (same as text for traceability).

    Rules:
    - Only inspects existing findings — never invents data.
    - Deterministic: same findings always produce same decision points.
    - Backward-compatible: returns [] for empty or None findings.
    """
    if not findings or not isinstance(findings, dict):
        return []

    decision_points: List[Dict[str, Any]] = []
    seen: set = set()  # deduplicate by normalised text

    for category, items in findings.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if not text:
                continue

            norm = text.lower()
            is_decision = any(signal in norm for signal in _DECISION_SIGNALS)

            if is_decision and norm not in seen:
                seen.add(norm)
                decision_points.append({
                    "id":             f"d{len(decision_points) + 1}",
                    "text":           text,
                    "category":       category,
                    "status":         "open",
                    "linked_finding": text,
                })

    return decision_points


# ──────────────────────────────────────────────────────────────
# Gate check
# ──────────────────────────────────────────────────────────────

def check_review_gate(
    project_id: str,
    review_id: str,
) -> Dict[str, Any]:
    """Check whether a review passes the quality gate.

    Loads the review from the DB, computes its score, and returns
    a gate result dict.

    Returns:
        {
            review_id, score, passed, missing, quality_status,
            can_set_active, blockers: [str]
        }
    """
    from models.hierarchy import _make_hierarchy_store

    store = _make_hierarchy_store(project_id)
    review = store.get_review(review_id)
    if review is None:
        return {
            "review_id":    review_id,
            "score":        0,
            "passed":       False,
            "missing":      STANDARD_CATEGORIES,
            "quality_status": "pending",
            "can_set_active": False,
            "blockers":     [f"Review {review_id} not found"],
        }

    result = compute_completeness_score(review.findings)
    quality_status = review.quality_status

    blockers: List[str] = []
    if quality_status == "pending" and not result["passed"]:
        missing_fmt = ", ".join(result["missing"])
        blockers.append(
            f"Review is missing findings in: {missing_fmt}. "
            f"Score {result['score']}/100 (need ≥{GATE_THRESHOLD}). "
            f"Mark as 'interim' to proceed anyway."
        )

    can_set_active = result["passed"] or quality_status in ("interim", "complete")

    return {
        "review_id":      review_id,
        "score":          result["score"],
        "passed":         result["passed"],
        "missing":        result["missing"],
        "categories":     result["categories"],
        "quality_status": quality_status,
        "can_set_active": can_set_active,
        "blockers":       blockers,
    }


# ──────────────────────────────────────────────────────────────
# Complete review action
# ──────────────────────────────────────────────────────────────

def complete_review(
    project_id: str,
    review_id: str,
    completed_by: str,
    quality_status: str = "complete",  # complete | interim
) -> Dict[str, Any]:
    """Mark a review as complete or interim.

    - 'complete' requires gate pass (score ≥ 70) unless explicitly overriding.
    - 'interim' always allowed — acknowledges partial coverage.

    Writes completeness_score, quality_status, completed_by, completed_at
    to the reviews table. Logs to decision_log.

    Returns: updated gate result dict + action taken.
    """
    from db.database import get_db, Database
    from db.decision_log import log_decision

    if quality_status not in ("complete", "interim"):
        raise ValueError(f"quality_status must be 'complete' or 'interim', got '{quality_status}'")

    gate = check_review_gate(project_id, review_id)

    if quality_status == "complete" and not gate["passed"]:
        # Allow override but record it as an override action
        action = "gate_overridden_complete"
    elif quality_status == "interim":
        action = "marked_interim"
    else:
        action = "completed"

    now = _now()
    db = get_db()
    db.execute(
        """UPDATE reviews
           SET completeness_score=?, quality_status=?, completed_by=?, completed_at=?
           WHERE project_id=? AND review_id=?""",
        (gate["score"], quality_status, completed_by, now, project_id, review_id),
    )
    db.commit()

    # Log the decision
    log_decision(
        project_id=project_id,
        entity_type="review",
        entity_id=review_id,
        action=action,
        actor=completed_by,
        reason=f"quality_status={quality_status}, score={gate['score']}/100",
        metadata={
            "score":          gate["score"],
            "missing":        gate["missing"],
            "quality_status": quality_status,
            "gate_passed":    gate["passed"],
        },
    )

    # Rebuild file mirror
    try:
        from models.hierarchy import _make_hierarchy_store
        store = _make_hierarchy_store(project_id)
        review = store.get_review(review_id)
        if review:
            store._file_save_review(review)
    except Exception:
        pass

    return {
        **gate,
        "quality_status": quality_status,
        "completed_by":   completed_by,
        "completed_at":   now,
        "action":         action,
    }


# ──────────────────────────────────────────────────────────────
# Set active review with gate
# ──────────────────────────────────────────────────────────────

def set_active_review_with_gate(
    project_id: str,
    version_id: str,
    review_id: str,
    decided_by: str,
    force: bool = False,
) -> Dict[str, Any]:
    """Set active review for a version, enforcing quality gate.

    Gate rule: review must have quality_status = 'complete' or 'interim'.
    If 'pending' and force=False, returns error with blockers.
    If force=True, sets active and logs override.

    Also writes decided_by to the review record.
    Logs to decision_log.
    """
    from db.database import get_db
    from db.decision_log import log_decision
    from models.hierarchy import _make_hierarchy_store

    gate = check_review_gate(project_id, review_id)

    if not gate["can_set_active"] and not force:
        return {
            "error":    "Review has not passed quality gate",
            "blockers": gate["blockers"],
            "gate":     gate,
        }

    store = _make_hierarchy_store(project_id)
    result = store.set_active_review(version_id, review_id)

    if result.get("error"):
        return result

    # Write decided_by to review record
    now = _now()
    db = get_db()
    db.execute(
        "UPDATE reviews SET decided_by=? WHERE project_id=? AND review_id=?",
        (decided_by, project_id, review_id),
    )
    db.commit()

    action = "set_active_forced" if force and not gate["can_set_active"] else "set_active"
    log_decision(
        project_id=project_id,
        entity_type="review",
        entity_id=review_id,
        action=action,
        actor=decided_by,
        reason=f"Set as active review for version {version_id}",
        metadata={
            "version_id":     version_id,
            "score":          gate["score"],
            "quality_status": gate["quality_status"],
            "forced":         force,
        },
    )

    return {
        "version_id":     version_id,
        "review_id":      review_id,
        "active_review_id": review_id,
        "decided_by":     decided_by,
        "gate":           gate,
        "action":         action,
        "status":         "updated",
    }
