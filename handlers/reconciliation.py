"""Reconciliation handlers — Sprint 3.

Routes (all under /api/projects/{pid}/hierarchy/versions/{vid}/reconciliation):

  POST   /select          — save explicit review selection (anchor + supplemental)
  GET    /selection       — return stored selection for a version
  POST   /run             — run reconciliation, return ReconciliationOutput
  GET    /                — return stored ReconciliationOutput for a version

All handlers are thin: validate → delegate to services/reconciliation.py → respond.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

import services.reconciliation as svc


# ──────────────────────────────────────────────────────────────────────────────
# POST /select
# ──────────────────────────────────────────────────────────────────────────────

def handle_save_selection(
    project_id: str,
    version_id: str,
    body: Dict[str, Any],
    respond: Callable,
) -> None:
    """Save the user's explicit review selection for a version.

    Body:
        anchor_review_id    : str   — required
        selected_review_ids : list  — required; must include anchor
        selected_by         : str   — optional

    Returns:
        ReconciliationSelection dict or error.
    """
    if not project_id:
        respond({"error": "project_id required"}, status=400)
        return
    if not version_id:
        respond({"error": "version_id required"}, status=400)
        return

    anchor_id      = (body.get("anchor_review_id") or "").strip()
    selected_ids   = body.get("selected_review_ids") or []
    selected_by    = (body.get("selected_by") or "").strip()

    if not anchor_id:
        respond({"error": "anchor_review_id is required"}, status=400)
        return
    if not isinstance(selected_ids, list):
        respond({"error": "selected_review_ids must be a list"}, status=400)
        return

    result = svc.save_reconciliation_selection(
        project_id=project_id,
        version_id=version_id,
        anchor_review_id=anchor_id,
        selected_review_ids=selected_ids,
        selected_by=selected_by,
    )

    if result.get("error"):
        respond(result, status=400)
    else:
        respond(result)


# ──────────────────────────────────────────────────────────────────────────────
# GET /selection
# ──────────────────────────────────────────────────────────────────────────────

def handle_get_selection(
    project_id: str,
    version_id: str,
    respond: Callable,
) -> None:
    """Return the stored ReconciliationSelection for a version.

    Returns 404 when no selection has been saved yet.
    """
    if not project_id:
        respond({"error": "project_id required"}, status=400)
        return

    result = svc.get_reconciliation_selection(project_id, version_id)
    if result is None:
        respond({"error": "No reconciliation selection found for this version"}, status=404)
    else:
        respond(result)


# ──────────────────────────────────────────────────────────────────────────────
# POST /run
# ──────────────────────────────────────────────────────────────────────────────

def handle_run_reconciliation(
    project_id: str,
    version_id: str,
    body: Dict[str, Any],
    respond: Callable,
) -> None:
    """Run reconciliation across explicitly selected reviews.

    Body (all optional when a selection was already saved via /select):
        anchor_review_id    : str   — overrides stored selection if provided
        selected_review_ids : list  — overrides stored selection if provided

    If body is empty the handler uses the stored selection for this version.
    Returns a ReconciliationOutput dict.
    """
    if not project_id:
        respond({"error": "project_id required"}, status=400)
        return

    anchor_id    = (body.get("anchor_review_id") or "").strip()
    selected_ids = body.get("selected_review_ids") or []

    # Fall back to stored selection when body omits them
    if not anchor_id or not selected_ids:
        stored = svc.get_reconciliation_selection(project_id, version_id)
        if stored is None and not anchor_id:
            respond(
                {"error": (
                    "No review selection found. "
                    "POST anchor_review_id + selected_review_ids first."
                )},
                status=400,
            )
            return
        if stored and not anchor_id:
            anchor_id    = stored.get("anchor_review_id", "")
        if stored and not selected_ids:
            selected_ids = stored.get("selected_review_ids", [])

    try:
        output = svc.run_reconciliation(
            project_id=project_id,
            version_id=version_id,
            anchor_review_id=anchor_id,
            selected_review_ids=selected_ids,
        )
        respond(output.to_dict())
    except ValueError as exc:
        respond({"error": str(exc)}, status=400)
    except Exception as exc:
        respond({"error": str(exc)}, status=500)


# ──────────────────────────────────────────────────────────────────────────────
# GET /
# ──────────────────────────────────────────────────────────────────────────────

def handle_get_reconciliation(
    project_id: str,
    version_id: str,
    respond: Callable,
) -> None:
    """Return the stored ReconciliationOutput for a version.

    Returns 404 when reconciliation has not been run yet.
    """
    if not project_id:
        respond({"error": "project_id required"}, status=400)
        return

    output = svc.get_reconciliation(project_id, version_id)
    if output is None:
        respond(
            {"error": "No reconciliation found for this version. Run POST /run first."},
            status=404,
        )
    else:
        respond(output.to_dict())
