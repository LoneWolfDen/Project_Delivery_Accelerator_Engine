"""Deep-dive handlers — SME question generation and feedback."""
from __future__ import annotations

from typing import Any, Callable, Dict

import services.deepdive as svc


def handle_deep_dive(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    persona = body.get("persona", "")
    custom_prompt = body.get("custom_prompt", "")
    review_id = body.get("review_id", "")

    # Load context from a predecessor review when provided
    context = svc.load_deep_dive_context_from_review(project_id, review_id) if review_id else {}

    try:
        result = svc.run_deep_dive_analysis(
            project_id, persona, custom_prompt,
            weaknesses=context.get("weaknesses", []),
            missing_categories=context.get("missing_categories", []),
            decision_points=context.get("decision_points", []),
        )
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=400)
    except Exception as e:
        respond({"error": str(e)}, status=500)


def handle_deep_dive_feedback(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    try:
        result = svc.apply_deep_dive_feedback(
            project_id,
            accepted=body.get("accepted"),
            rejected=body.get("rejected"),
            added_to_prompt=body.get("added_to_prompt"),
        )
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=400)
