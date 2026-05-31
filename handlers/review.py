"""Review handlers — run review, quality gate, weakness/decision status.

The ``handle_review`` function accepts an optional ``agent`` parameter that
satisfies the ``ReviewAgent`` protocol.  The default is ``ServiceReviewAgent``
(backed by services.review).  Tests can inject a stub without touching any
service layer.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from contracts.bus import bus
from contracts.protocols import ReviewAgent, ServiceReviewAgent
from contracts.types import Event, ReviewRequest, Topics
import services.review as svc


# Module-level default agent — can be replaced at startup for integration tests
_default_agent: ReviewAgent = ServiceReviewAgent()


def set_review_agent(agent: ReviewAgent) -> None:
    """Replace the module-level default ReviewAgent (test helper / DI hook)."""
    global _default_agent
    _default_agent = agent


def handle_review(
    body: Dict[str, Any],
    respond: Callable,
    *,
    agent: Optional[ReviewAgent] = None,
) -> None:
    """POST /api/review

    Dispatches through the ReviewAgent protocol.  Falls back to the
    module-level default (ServiceReviewAgent) when no agent is injected.
    """
    project_id = body.get("project_id")
    roles = body.get("roles") or body.get("persona")
    if not project_id:
        respond({"error": "project_id required"}, status=400)
        return
    if not roles:
        respond({"error": "roles (or persona) required"}, status=400)
        return

    roles_list = roles if isinstance(roles, list) else [roles]
    effective_agent = agent or _default_agent

    request = ReviewRequest(
        project_id=project_id,
        roles=roles_list,
        ai_backend=body.get("ai_backend", "files_only"),
        custom_prompt=body.get("custom_prompt"),
        previous_review_id=body.get("previous_review_id", ""),
        prompt_builder_state=body.get("prompt_builder_state"),
    )

    try:
        result = effective_agent.run(request)
        respond(result.raw)
    except ValueError as e:
        bus.publish(Event(
            topic=Topics.REVIEW_FAILED,
            payload={"project_id": project_id, "error": str(e)},
            source="handlers.review",
        ))
        respond({"error": str(e)}, status=400)
    except Exception as e:
        bus.publish(Event(
            topic=Topics.REVIEW_FAILED,
            payload={"project_id": project_id, "error": str(e)},
            source="handlers.review",
        ))
        respond({"error": str(e)}, status=500)


def handle_complete_review(
    project_id: str, review_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    try:
        result = svc.complete_review_gate(
            project_id, review_id,
            body.get("completed_by", ""),
            body.get("quality_status", "complete"),
        )
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=400)


def handle_delete_review(project_id: str, review_id: str, respond: Callable) -> None:
    from services.hierarchy import delete_hierarchy_review
    result = delete_hierarchy_review(project_id, review_id)
    if result.get("error"):
        respond(result, status=404)
    else:
        respond(result)


def handle_set_active_review(
    project_id: str, version_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    from services.hierarchy import set_active_review
    review_id = body.get("review_id", "")
    if not review_id:
        respond({"error": "review_id required"}, status=400)
        return
    result = set_active_review(project_id, version_id, review_id)
    if result.get("error"):
        respond(result, status=400)
    else:
        respond(result)


def handle_set_active_review_gated(
    project_id: str, version_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    result = svc.set_active_review_gated(
        project_id, version_id,
        body.get("review_id", ""),
        body.get("decided_by", ""),
        force=bool(body.get("force", False)),
    )
    if result.get("error"):
        respond(result, status=422)
    else:
        respond(result)


def handle_weakness_status(
    project_id: str, review_id: str, weakness_id: str,
    body: Dict[str, Any], respond: Callable
) -> None:
    result = svc.update_weakness_status(project_id, review_id, weakness_id, body.get("status", ""))
    if result.get("error"):
        respond(result, status=400)
    else:
        respond(result)


def handle_decision_status(
    project_id: str, review_id: str, decision_id: str,
    body: Dict[str, Any], respond: Callable
) -> None:
    result = svc.update_decision_status(project_id, review_id, decision_id, body.get("status", ""))
    if result.get("error"):
        respond(result, status=400)
    else:
        respond(result)
