"""Pre-sales Feedback Loop Processor (P9).

Responsibilities:
1. get_presales_summary()     – aggregated view for the Pre-Sales tab
2. attach_feedback_to_context() – writes accepted/rejected/concerns into a
   per-project JSON cache so they are injected into the next review prompt
3. get_feedback_prompt_injection() – returns the formatted prompt block
   that personas/engine.py prepends when running a pre-sales review
4. build_feedback_delta()     – compares two proposal versions' feedback
   to surface "what changed" across client iterations
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_DIR = Path("projects_data")


# ──────────────────────────────────────────────────────────────
# 1. Pre-sales summary
# ──────────────────────────────────────────────────────────────

def get_presales_summary(project_id: str) -> Dict[str, Any]:
    """Return a consolidated pre-sales view for the UI tab.

    Aggregates:
    - Current proposal (latest version, status, client)
    - All feedback items (counts + latest)
    - Open action items
    - Intelligence snapshot stats
    - Active review for the pre-sales phase
    """
    from db.project_store_sql import load_proposal_sql, load_presales_feedback
    from models.hierarchy import _make_hierarchy_store
    import project_manager

    proposal   = load_proposal_sql(project_id)
    feedback   = load_presales_feedback(project_id)
    store      = _make_hierarchy_store(project_id)
    intel      = project_manager.get_project_intelligence(project_id)

    # Proposal summary
    current_ver = None
    if proposal:
        versions = proposal.get("versions", [])
        current_vid = proposal.get("current_version", "")
        current_ver = next(
            (v for v in versions if v["version_id"] == current_vid), versions[-1] if versions else None
        )

    # Reviews scoped to pre-sales phase
    presales_reviews = store.list_reviews(phase_id="pre-sales")
    active_review = None
    if presales_reviews:
        active_review = presales_reviews[0]  # newest first

    # Feedback aggregation
    open_fb    = [f for f in feedback if f["status"] == "open"]
    actioned   = [f for f in feedback if f["status"] == "actioned"]
    all_accepted  = [i for f in feedback for i in f.get("accepted", [])]
    all_rejected  = [i for f in feedback for i in f.get("rejected", [])]
    all_concerns  = [i for f in feedback for i in f.get("concerns", [])]

    # Next actions across all open feedback
    next_actions = [f["next_action"] for f in open_fb if f.get("next_action")]

    return {
        "project_id":    project_id,
        "proposal":      proposal,
        "current_version": current_ver,
        "active_review": active_review,
        "presales_reviews": presales_reviews,
        "feedback_summary": {
            "total":    len(feedback),
            "open":     len(open_fb),
            "actioned": len(actioned),
            "accepted_count": len(all_accepted),
            "rejected_count": len(all_rejected),
            "concerns_count": len(all_concerns),
            "top_accepted":  all_accepted[:5],
            "top_rejected":  all_rejected[:5],
            "top_concerns":  all_concerns[:5],
            "next_actions":  next_actions,
        },
        "intelligence_stats": intel.get("_build_metadata", {}) if intel else {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────────────────────
# 2. Attach feedback to context cache (prompt injection source)
# ──────────────────────────────────────────────────────────────

_CACHE_FILENAME = "presales_feedback_cache.json"


def _cache_path(project_id: str) -> Path:
    p = PROJECTS_DIR / project_id / "intelligence"
    p.mkdir(parents=True, exist_ok=True)
    return p / _CACHE_FILENAME


def attach_feedback_to_context(project_id: str, feedback_item: Dict[str, Any]) -> None:
    """Append a feedback item to the project's feedback prompt cache.

    The cache is a list of feedback records.  The next time a pre-sales
    review runs, get_feedback_prompt_injection() reads this cache and
    prepends the context block to the custom_prompt.
    """
    path = _cache_path(project_id)
    cache: List[Dict[str, Any]] = []
    if path.exists():
        try:
            with open(path) as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            cache = []

    # Avoid duplicates
    existing_ids = {e.get("feedback_id") for e in cache}
    if feedback_item.get("feedback_id") not in existing_ids:
        cache.append(feedback_item)

    with open(path, "w") as f:
        json.dump(cache, f, indent=2)


def get_feedback_prompt_injection(project_id: str, max_items: int = 10) -> str:
    """Build a formatted prompt block from cached pre-sales feedback.

    Called by personas/engine.py before running a pre-sales review so the
    LLM is aware of prior client responses.

    Returns an empty string if no feedback exists.
    """
    path = _cache_path(project_id)
    if not path.exists():
        return ""

    try:
        with open(path) as f:
            cache: List[Dict[str, Any]] = json.load(f)
    except (json.JSONDecodeError, OSError):
        return ""

    if not cache:
        return ""

    # Use the most recent N items
    recent = sorted(cache, key=lambda x: x.get("created_at", ""), reverse=True)[:max_items]

    lines: List[str] = [
        "─── Prior Client Feedback (Pre-sales Loop) ───",
        f"The following feedback has been captured from {len(recent)} interaction(s).",
        "Use this to refine your analysis and flag unresolved concerns.\n",
    ]

    for i, fb in enumerate(recent, 1):
        src   = fb.get("source", "internal").upper()
        name  = fb.get("responder_name") or "Unknown"
        date  = (fb.get("created_at") or "")[:10]
        lines.append(f"[Feedback {i} — {src} from {name} on {date}]")

        accepted = fb.get("accepted", [])
        rejected = fb.get("rejected", [])
        concerns = fb.get("concerns", [])
        notes    = fb.get("notes", "")

        if accepted:
            lines.append(f"  Accepted: {'; '.join(accepted)}")
        if rejected:
            lines.append(f"  Rejected: {'; '.join(rejected)}")
        if concerns:
            lines.append(f"  Concerns: {'; '.join(concerns)}")
        if notes:
            lines.append(f"  Notes: {notes}")
        lines.append("")

    lines.append("─── End of Prior Feedback ───\n")
    return "\n".join(lines)


def clear_feedback_cache(project_id: str) -> None:
    """Clear the prompt injection cache (e.g. after a new proposal version is created)."""
    path = _cache_path(project_id)
    if path.exists():
        path.unlink()


# ──────────────────────────────────────────────────────────────
# 3. Feedback delta (compare two proposal versions)
# ──────────────────────────────────────────────────────────────

def build_feedback_delta(
    project_id: str, version_a_id: str, version_b_id: str
) -> Dict[str, Any]:
    """Compare feedback between two proposal versions.

    Returns sets of: newly accepted, newly rejected, resolved concerns,
    new concerns, and persistence counts.
    """
    from db.project_store_sql import get_db
    from db.database import Database

    db = get_db()

    def _get_feedback_for_version(ver_id: str) -> List[Dict[str, Any]]:
        rows = db.fetchall(
            "SELECT * FROM presales_feedback WHERE project_id=? AND proposal_ver_id=?",
            (project_id, ver_id),
        )
        return [
            {
                "accepted": Database.jload(r.get("accepted"), []),
                "rejected": Database.jload(r.get("rejected"), []),
                "concerns": Database.jload(r.get("concerns"), []),
            }
            for r in rows
        ]

    def _flatten(items: List[Dict], key: str) -> set:
        return {i.lower().strip() for fb in items for i in fb.get(key, [])}

    fb_a = _get_feedback_for_version(version_a_id)
    fb_b = _get_feedback_for_version(version_b_id)

    acc_a, acc_b = _flatten(fb_a, "accepted"),  _flatten(fb_b, "accepted")
    rej_a, rej_b = _flatten(fb_a, "rejected"),  _flatten(fb_b, "rejected")
    con_a, con_b = _flatten(fb_a, "concerns"),  _flatten(fb_b, "concerns")

    return {
        "version_a": version_a_id,
        "version_b": version_b_id,
        "accepted": {
            "new":       sorted(acc_b - acc_a),
            "lost":      sorted(acc_a - acc_b),
            "persisted": len(acc_a & acc_b),
        },
        "rejected": {
            "new":       sorted(rej_b - rej_a),
            "resolved":  sorted(rej_a - rej_b),
            "persisted": len(rej_a & rej_b),
        },
        "concerns": {
            "new":       sorted(con_b - con_a),
            "resolved":  sorted(con_a - con_b),
            "persisted": len(con_a & con_b),
        },
        "summary": {
            "direction": (
                "improving"   if len(acc_b) > len(acc_a) and len(con_b) < len(con_a)
                else "mixed"  if len(acc_b) > len(acc_a)
                else "needs_attention"
            ),
        },
    }
