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
