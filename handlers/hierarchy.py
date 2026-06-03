"""Hierarchy handlers — Phase/Version/Review tree, diffs, readiness, prompts."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import services.hierarchy as svc
import services.review as review_svc


def handle_compare_versions(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    version_a = body.get("version_a")
    version_b = body.get("version_b")
    if not version_a or not version_b:
        respond({"error": "version_a and version_b required"}, status=400)
        return
    try:
        respond(svc.compare_project_versions(project_id, version_a, version_b))
    except ValueError as e:
        respond({"error": str(e)}, status=404)


def handle_compare_reviews(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    review_a = body.get("review_a")
    review_b = body.get("review_b")
    if not review_a or not review_b:
        respond({"error": "review_a and review_b filenames required"}, status=400)
        return
    try:
        respond(svc.compare_project_reviews(project_id, review_a, review_b))
    except ValueError as e:
        respond({"error": str(e)}, status=404)


def handle_reconcile_reviews(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    """POST /api/projects/{pid}/hierarchy/reconcile

    Reconciles an anchor review against zero or more supplemental reviews
    from the same version.

    Required body fields:
      anchor_review_id          – review_id of the anchor (active) review

    Optional body fields:
      supplemental_review_ids[] – list of additional review_ids to merge in
      ai_backend                – default "files_only"

    Returns a ReconciliationResult dict:
      reconciled_findings  {category: [str, ...]}
      contradictions       [{category, description, review_ids}]
      reconciliation_notes str
      source_review_ids    [str, ...]
      anchor_review_id     str
      generated_by         str
      generated_at         str
    """
    anchor_id = body.get("anchor_review_id", "")
    if not anchor_id:
        respond({"error": "anchor_review_id required"}, status=400)
        return

    supplemental_ids: list = body.get("supplemental_review_ids") or []
    ai_backend: str = body.get("ai_backend", "files_only")

    try:
        result = svc.reconcile_reviews(
            project_id=project_id,
            anchor_review_id=anchor_id,
            supplemental_review_ids=supplemental_ids,
            ai_backend=ai_backend,
        )
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=400)
    except Exception as e:
        respond({"error": str(e)}, status=500)
