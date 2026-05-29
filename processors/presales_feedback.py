"""Pre-sales Feedback Loop Processor — DS-06.

DS-06 changes from P9:
- attach_feedback_to_context(): only caches items with status='new'
- get_feedback_prompt_injection(): formats structured FeedbackItems
  (grouped by mapped_to, flags critical items, excludes addressed/deferred)
- clear_feedback_cache_for_version(): scoped reset per proposal version
- get_presales_summary(): adds structured feedback counts + stop condition hint
- build_feedback_delta(): now reads structured feedback_items field
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_DIR = Path("projects_data")
_CACHE_FILENAME = "presales_feedback_cache.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cache_path(project_id: str) -> Path:
    p = PROJECTS_DIR / project_id / "intelligence"
    p.mkdir(parents=True, exist_ok=True)
    return p / _CACHE_FILENAME


# ──────────────────────────────────────────────────────────────
# 1. Pre-sales summary (DS-06: adds structured counts + stop hint)
# ──────────────────────────────────────────────────────────────

def get_presales_summary(project_id: str) -> Dict[str, Any]:
    """Return a consolidated pre-sales view for the UI tab."""
    from db.project_store_sql import load_proposal_sql, load_presales_feedback
    from models.hierarchy import _make_hierarchy_store
    import project_manager

    proposal = load_proposal_sql(project_id)
    feedback = load_presales_feedback(project_id)
    store    = _make_hierarchy_store(project_id)
    intel    = project_manager.get_project_intelligence(project_id)

    current_ver = None
    if proposal:
        versions    = proposal.get("versions", [])
        current_vid = proposal.get("current_version", "")
        current_ver = next(
            (v for v in versions if v["version_id"] == current_vid),
            versions[-1] if versions else None,
        )

    # Reviews scoped to pre-sales phase, with quality fields
    presales_reviews = store.list_reviews(phase_id="pre-sales")
    active_review = presales_reviews[0] if presales_reviews else None

    # Aggregate across ALL feedback records for this project
    all_items: List[Dict[str, Any]] = []
    for fb in feedback:
        all_items.extend(fb.get("feedback_items", []))

    open_fb     = [f for f in feedback if f["status"] == "open"]
    actioned_fb = [f for f in feedback if f["status"] == "actioned"]

    new_items      = [i for i in all_items if i.get("status") == "new"]
    addressed      = [i for i in all_items if i.get("status") == "addressed"]
    critical_open  = [i for i in new_items if i.get("is_critical")]
    change_req     = [i for i in new_items if i.get("category") == "change_requested"]

    # backward-compat flat views (still used by legacy UI paths)
    all_accepted = [i["text"] for i in all_items if i.get("category") == "accepted"]
    all_rejected = [i["text"] for i in all_items if i.get("category") == "rejected"]
    all_concerns = [i["text"] for i in all_items if i.get("category") == "concerns"]

    next_actions = [f["next_action"] for f in open_fb if f.get("next_action")]

    # Stop condition hint
    ready_to_finalise = (
        len(critical_open) == 0
        and current_ver is not None
        and current_ver.get("status") == "accepted"
    )

    return {
        "project_id":     project_id,
        "proposal":       proposal,
        "current_version": current_ver,
        "active_review":  active_review,
        "presales_reviews": presales_reviews,
        "feedback_summary": {
            "total":            len(feedback),
            "open":             len(open_fb),
            "actioned":         len(actioned_fb),
            # DS-06 structured counts
            "total_items":      len(all_items),
            "new_items":        len(new_items),
            "addressed_items":  len(addressed),
            "critical_open":    len(critical_open),
            "change_requested": len(change_req),
            # backward-compat
            "accepted_count":   len(all_accepted),
            "rejected_count":   len(all_rejected),
            "concerns_count":   len(all_concerns),
            "top_accepted":     all_accepted[:5],
            "top_rejected":     all_rejected[:5],
            "top_concerns":     all_concerns[:5],
            "next_actions":     next_actions,
        },
        "stop_condition": {
            "ready":           ready_to_finalise,
            "critical_open":   len(critical_open),
            "blockers": (
                [] if ready_to_finalise else
                ([f"{len(critical_open)} critical feedback item(s) unresolved"] if critical_open else [])
                + (["Proposal version not yet accepted"] if current_ver and current_ver.get("status") != "accepted" else [])
                + (["No proposal exists"] if not current_ver else [])
            ),
        },
        "intelligence_stats": intel.get("_build_metadata", {}) if intel else {},
        "generated_at": _now(),
    }


# ──────────────────────────────────────────────────────────────
# 2. Attach feedback to context cache (DS-06: new-only items)
# ──────────────────────────────────────────────────────────────

def attach_feedback_to_context(project_id: str, feedback_record: Dict[str, Any]) -> None:
    """Cache new (unaddressed) FeedbackItems for prompt injection.

    DS-06: only items with status='new' are injected — addressed/deferred
    items are excluded to prevent noise in repeated reviews.
    """
    path = _cache_path(project_id)
    cache: List[Dict[str, Any]] = []
    if path.exists():
        try:
            with open(path) as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            cache = []

    existing_ids = {e.get("feedback_id") for e in cache}
    if feedback_record.get("feedback_id") not in existing_ids:
        # Only include the record if it has new items
        new_items = [
            i for i in feedback_record.get("feedback_items", [])
            if i.get("status") == "new"
        ]
        if new_items or feedback_record.get("notes"):
            cache.append({
                **feedback_record,
                "feedback_items": new_items,  # strip non-new items from cache
            })

    with open(path, "w") as f:
        json.dump(cache, f, indent=2)


def clear_feedback_cache(project_id: str) -> None:
    """Clear the entire feedback prompt cache for a project."""
    path = _cache_path(project_id)
    if path.exists():
        path.unlink()


def clear_feedback_cache_for_version(
    project_id: str, proposal_ver_id: str
) -> None:
    """Remove feedback items linked to a specific proposal version from the cache.

    Called when a new proposal version is created — prior version's
    feedback becomes historical, not active injection context.
    """
    path = _cache_path(project_id)
    if not path.exists():
        return
    try:
        with open(path) as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    updated = [
        e for e in cache
        if e.get("proposal_ver_id") != proposal_ver_id
    ]
    with open(path, "w") as f:
        json.dump(updated, f, indent=2)


# ──────────────────────────────────────────────────────────────
# 3. Prompt injection (DS-06: structured format, new-only)
# ──────────────────────────────────────────────────────────────

def get_feedback_prompt_injection(
    project_id: str,
    max_records: int = 5,
) -> str:
    """Build a structured prompt block from cached new feedback items.

    DS-06: formats items by mapped_to category, flags critical items,
    excludes addressed/deferred. Returns empty string if no new items.
    """
    path = _cache_path(project_id)
    if not path.exists():
        return ""

    try:
        with open(path) as f:
            cache: List[Dict[str, Any]] = json.load(f)
    except (json.JSONDecodeError, OSError):
        return ""

    # Collect all new items across recent feedback records
    recent = sorted(cache, key=lambda x: x.get("created_at", ""), reverse=True)[:max_records]
    all_new_items: List[Dict[str, Any]] = []
    for rec in recent:
        for item in rec.get("feedback_items", []):
            if item.get("status") == "new":
                all_new_items.append({**item, "_source": rec.get("responder_name", "Unknown")})

    if not all_new_items:
        return ""

    # Group by mapped_to
    grouped: Dict[str, List] = {}
    for item in all_new_items:
        key = item.get("mapped_to") or item.get("category", "general")
        grouped.setdefault(key, []).append(item)

    critical = [i for i in all_new_items if i.get("is_critical")]

    lines: List[str] = [
        "─── Prior Client Feedback — Active Items ───",
        f"{len(all_new_items)} unresolved feedback item(s) from {len(recent)} interaction(s).",
        "Address these in your analysis.\n",
    ]

    if critical:
        lines.append(f"⚠ CRITICAL ({len(critical)} item(s)) — must be resolved before finalisation:")
        for item in critical:
            lines.append(
                f"  [{item.get('category','?').upper()}→{item.get('mapped_to','?')}] "
                f"{item['text']} (confidence: {item.get('confidence','?')})"
            )
        lines.append("")

    for group_key, items in sorted(grouped.items()):
        non_critical = [i for i in items if not i.get("is_critical")]
        if non_critical:
            lines.append(f"[{group_key.upper()}]")
            for item in non_critical:
                cat_label = {
                    "accepted": "✓",
                    "rejected": "✗",
                    "change_requested": "↻",
                    "concerns": "?",
                }.get(item.get("category", ""), "·")
                lines.append(f"  {cat_label} {item['text']}")
            lines.append("")

    lines.append("─── End of Active Feedback ───\n")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# 4. Feedback delta (DS-06: reads structured feedback_items)
# ──────────────────────────────────────────────────────────────

def build_feedback_delta(
    project_id: str,
    version_a_id: str,
    version_b_id: str,
) -> Dict[str, Any]:
    """Compare structured feedback between two proposal versions."""
    from db.database import get_db, Database

    db = get_db()

    def _get_items(ver_id: str) -> List[Dict[str, Any]]:
        rows = db.fetchall(
            "SELECT * FROM presales_feedback WHERE project_id=? AND proposal_ver_id=?",
            (project_id, ver_id),
        )
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.extend(Database.jload(r.get("feedback_items"), []))
        return items

    def _texts_by_cat(items: List[Dict], cat: str) -> set:
        return {i["text"].lower().strip() for i in items if i.get("category") == cat}

    items_a = _get_items(version_a_id)
    items_b = _get_items(version_b_id)

    result: Dict[str, Any] = {"version_a": version_a_id, "version_b": version_b_id}
    for cat in ("accepted", "rejected", "change_requested", "concerns"):
        set_a = _texts_by_cat(items_a, cat)
        set_b = _texts_by_cat(items_b, cat)
        result[cat] = {
            "new":       sorted(set_b - set_a),
            "resolved":  sorted(set_a - set_b),
            "persisted": len(set_a & set_b),
        }

    critical_a = sum(1 for i in items_a if i.get("is_critical") and i.get("status") == "new")
    critical_b = sum(1 for i in items_b if i.get("is_critical") and i.get("status") == "new")
    result["summary"] = {
        "critical_open_a": critical_a,
        "critical_open_b": critical_b,
        "direction": (
            "improving"       if critical_b < critical_a else
            "stable"          if critical_b == critical_a else
            "needs_attention"
        ),
    }
    return result
