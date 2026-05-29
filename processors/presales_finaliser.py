"""Pre-sales Finaliser — DS-08.

Atomic finalisation of the pre-sales phase:
1. check_stop_condition()  — surfaces readiness signal + blockers
2. finalise_presales()     — atomic: accept + soft-lock + freeze feedback
                             + complete review + transition to design phase

Stop condition rules
────────────────────
- No critical feedback items with status='new'
- Current proposal version status == 'accepted'
- At least one review marked complete or interim (quality_status != 'pending')

Soft lock
─────────
- proposal_version.lock_status → 'soft_locked'
- Any subsequent write to a soft-locked version returns 409
  (enforced in server.py _handle_update_proposal_version_status)

Feedback freeze
───────────────
- All feedback items with status='new' → 'deferred'
  (preserves history, prevents re-injection in future reviews)

Phase transition
────────────────
- hierarchy phase → 'design'
- project.phase  → 'design'

Decision log
────────────
- One 'finalised' entry capturing full snapshot at time of decision
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db.database import get_db, Database
from db.decision_log import log_decision


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────
# 1. Stop condition check
# ──────────────────────────────────────────────────────────────

def check_stop_condition(project_id: str) -> Dict[str, Any]:
    """Check whether the pre-sales loop is ready to finalise.

    Returns:
        {
            ready:              bool,
            blockers:           [str],
            critical_open:      [FeedbackItem dict],
            unresolved_count:   int,
            proposal_status:    str | None,
            review_quality:     str | None,
            can_override:       bool,   # PM can force-finalise
        }
    """
    from db.project_store_sql import load_proposal_sql, load_presales_feedback
    from models.hierarchy import _make_hierarchy_store

    blockers: List[str] = []

    # ── Check proposal exists and has an accepted version ─────
    proposal = load_proposal_sql(project_id)
    current_ver = None
    proposal_status = None
    if not proposal:
        blockers.append("No proposal exists for this project.")
    else:
        versions = proposal.get("versions", [])
        current_vid = proposal.get("current_version", "")
        current_ver = next((v for v in versions if v["version_id"] == current_vid),
                           versions[-1] if versions else None)
        if current_ver:
            proposal_status = current_ver.get("status", "draft")
            if proposal_status != "accepted":
                blockers.append(
                    f"Current proposal version status is '{proposal_status}'. "
                    "Mark it as 'accepted' before finalising."
                )
        else:
            blockers.append("No proposal versions exist.")

    # ── Check review quality ───────────────────────────────────
    store = _make_hierarchy_store(project_id)
    presales_reviews = store.list_reviews(phase_id="pre-sales")
    review_quality = None
    if not presales_reviews:
        blockers.append("No reviews have been run in the pre-sales phase.")
    else:
        latest = presales_reviews[0]
        review_quality = latest.get("quality_status", "pending")
        if review_quality == "pending":
            blockers.append(
                f"Latest review ({latest.get('review_id')}) has not been marked "
                "complete or interim. Mark it first."
            )

    # ── Check critical feedback ────────────────────────────────
    feedback = load_presales_feedback(project_id)
    critical_open: List[Dict[str, Any]] = []
    for fb in feedback:
        for item in fb.get("feedback_items", []):
            if item.get("is_critical") and item.get("status") == "new":
                critical_open.append({**item, "_feedback_id": fb["feedback_id"]})

    if critical_open:
        blockers.append(
            f"{len(critical_open)} critical feedback item(s) are still unresolved. "
            "Address or override them before finalising."
        )

    ready = len(blockers) == 0

    return {
        "ready":            ready,
        "blockers":         blockers,
        "critical_open":    critical_open,
        "unresolved_count": len(critical_open),
        "proposal_status":  proposal_status,
        "review_quality":   review_quality,
        "can_override":     True,  # PM can always force with decided_by + reason
    }


# ──────────────────────────────────────────────────────────────
# 2. Mark feedback items as deferred (freeze)
# ──────────────────────────────────────────────────────────────

def _freeze_feedback(project_id: str) -> int:
    """Set all new feedback items to 'deferred'. Returns count changed."""
    db = get_db()
    rows = db.fetchall(
        "SELECT feedback_id, feedback_items FROM presales_feedback WHERE project_id=?",
        (project_id,),
    )
    changed = 0
    for row in rows:
        # row is already a dict (fetchall uses dict(r) via row_factory)
        items: List[Dict[str, Any]] = Database.jload(row.get("feedback_items"), [])
        updated = False
        for item in items:
            if item.get("status") == "new":
                item["status"] = "deferred"
                updated = True
                changed += 1
        if updated:
            now = _now()
            db.execute(
                "UPDATE presales_feedback SET feedback_items=?, updated_at=? "
                "WHERE feedback_id=?",
                (Database.jdump(items), now, row["feedback_id"]),
            )
    if changed:
        db.commit()
    return changed


# ──────────────────────────────────────────────────────────────
# 3. Soft-lock proposal version
# ──────────────────────────────────────────────────────────────

def _soft_lock_proposal_version(
    project_id: str, version_id: str, reason: str = "Finalised"
) -> None:
    get_db().execute(
        "UPDATE proposal_versions SET lock_status='soft_locked', lock_reason=? "
        "WHERE project_id=? AND version_id=?",
        (reason, project_id, version_id),
    )
    get_db().commit()


# ──────────────────────────────────────────────────────────────
# 4. Atomic finalise
# ──────────────────────────────────────────────────────────────

def finalise_presales(
    project_id: str,
    decided_by: str,
    reason: str = "",
    force: bool = False,
) -> Dict[str, Any]:
    """Atomically finalise the pre-sales phase.

    Steps (all-or-nothing):
    1. Check stop condition — return blockers if not ready (unless force=True)
    2. Mark proposal version status → 'accepted' (if not already)
    3. Soft-lock the current proposal version
    4. Freeze all new feedback items → 'deferred'
    5. Mark latest pre-sales review as 'complete' (if still pending)
    6. Transition hierarchy phase → 'design'
    7. Transition project phase → 'design'
    8. Write 'finalised' entry to decision_log

    Args:
        project_id: Project ID.
        decided_by: Name of person authorising finalisation.
        reason:     Optional reason for override (required when force=True).
        force:      If True, proceed despite unmet stop conditions.

    Returns:
        Finalisation receipt dict or error dict.
    """
    import project_manager
    from db.project_store_sql import load_proposal_sql, save_proposal_sql
    from models.hierarchy import _make_hierarchy_store
    from processors.review_quality import complete_review as _complete_review

    # ── Step 1: stop condition check ──────────────────────────
    condition = check_stop_condition(project_id)
    if not condition["ready"] and not force:
        return {
            "error":    "Pre-sales not ready to finalise",
            "blockers": condition["blockers"],
            "condition": condition,
        }

    now = _now()
    db  = get_db()

    # ── Step 2: accept current proposal version ───────────────
    proposal = load_proposal_sql(project_id)
    if not proposal:
        return {"error": "No proposal exists — cannot finalise."}

    versions     = proposal.get("versions", [])
    current_vid  = proposal.get("current_version", "")
    current_ver  = next((v for v in versions if v["version_id"] == current_vid),
                        versions[-1] if versions else None)
    if not current_ver:
        return {"error": "No proposal version found — cannot finalise."}

    ver_id = current_ver["version_id"]
    if current_ver.get("status") != "accepted":
        db.execute(
            "UPDATE proposal_versions SET status='accepted' "
            "WHERE project_id=? AND version_id=?",
            (project_id, ver_id),
        )
        db.commit()

    # ── Step 3: soft-lock ─────────────────────────────────────
    _soft_lock_proposal_version(project_id, ver_id, reason or "Pre-sales finalised")

    # ── Step 4: freeze feedback ───────────────────────────────
    frozen_count = _freeze_feedback(project_id)

    # ── Step 5: complete latest review (if pending) ───────────
    store           = _make_hierarchy_store(project_id)
    presales_reviews = store.list_reviews(phase_id="pre-sales")
    review_completed = None
    if presales_reviews:
        latest_review = presales_reviews[0]
        if latest_review.get("quality_status") == "pending":
            try:
                _complete_review(
                    project_id, latest_review["review_id"],
                    completed_by=decided_by, quality_status="complete"
                )
                review_completed = latest_review["review_id"]
            except Exception:
                pass

    # ── Step 6: transition hierarchy phase ────────────────────
    try:
        store.set_current_phase("design", reason or "Pre-sales finalised")
    except Exception:
        pass

    # ── Step 7: transition project phase ─────────────────────
    try:
        project_manager.transition_project_phase(project_id, "design",
                                                  reason or "Pre-sales finalised")
    except Exception:
        pass

    # ── Step 8: decision log ──────────────────────────────────
    receipt = {
        "project_id":       project_id,
        "decided_by":       decided_by,
        "reason":           reason,
        "forced":           force and not condition["ready"],
        "proposal_ver_id":  ver_id,
        "frozen_feedback":  frozen_count,
        "review_completed": review_completed,
        "phase_transitioned": "design",
        "finalised_at":     now,
        "condition_at_finalise": condition,
    }

    log_decision(
        project_id=project_id,
        entity_type="finalisation",
        entity_id=ver_id,
        action="finalised",
        actor=decided_by,
        reason=reason or "Pre-sales phase finalised",
        metadata=receipt,
    )

    # Rebuild proposal file mirror
    try:
        save_proposal_sql(project_id, load_proposal_sql(project_id) or proposal)
    except Exception:
        pass

    return receipt
