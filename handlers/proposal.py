"""Proposal handlers — create, version, status, document generation."""
from __future__ import annotations

from typing import Any, Callable, Dict

from db.decision_log import log_decision
from db.project_store_sql import get_db

import services.proposal as svc


def handle_create_proposal(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    name = body.get("proposal_name") or body.get("name") or "Untitled Proposal"
    try:
        result = svc.create_proposal(
            project_id, name,
            client=body.get("client", ""),
            notes=body.get("notes", ""),
            hierarchy_version_id=body.get("hierarchy_version_id", ""),
            active_review_id=body.get("review_id", "") or body.get("active_review_id", ""),
        )
        respond(result, status=201)
    except ValueError as e:
        respond({"error": str(e)}, status=422)


def handle_add_proposal_version(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    try:
        result = svc.add_proposal_version(
            project_id,
            label=body.get("label", ""),
            notes=body.get("notes", ""),
            changes=body.get("changes", ""),
            hierarchy_version_id=body.get("hierarchy_version_id", ""),
            active_review_id=body.get("review_id", "") or body.get("active_review_id", ""),
            feedback_applied=body.get("feedback_applied", []),
            changes_summary=body.get("changes_summary", ""),
        )
        respond(result, status=201)
    except ValueError as e:
        respond({"error": str(e)}, status=422)


def handle_update_proposal_version_status(
    project_id: str, version_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    new_status = body.get("status", "")
    if not new_status:
        respond({"error": "status required"}, status=400)
        return

    # DS-08: soft-lock enforcement
    try:
        db = get_db()
        row = db.fetchone(
            "SELECT lock_status, lock_reason FROM proposal_versions "
            "WHERE project_id=? AND version_id=?",
            (project_id, version_id),
        )
        if row and row.get("lock_status") == "soft_locked":
            override_reason = body.get("override_reason", "")
            if not override_reason:
                respond({
                    "error": "This proposal version is soft-locked (finalised). "
                             "Provide 'override_reason' to proceed.",
                    "lock_reason": row.get("lock_reason", ""),
                    "lock_status": "soft_locked",
                }, status=409)
                return
            log_decision(
                project_id=project_id,
                entity_type="proposal_version",
                entity_id=version_id,
                action="lock_overridden",
                actor=body.get("decided_by", ""),
                reason=override_reason,
                metadata={"new_status": new_status},
            )
    except Exception:
        pass

    try:
        respond(svc.update_proposal_status(project_id, version_id, new_status))
    except ValueError as e:
        respond({"error": str(e)}, status=400)


def handle_generate_proposal_doc(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    result = svc.generate_proposal_doc(
        project_id=project_id,
        proposal_ver_id=body.get("proposal_ver_id", ""),
        hierarchy_version_id=body.get("hierarchy_version_id", ""),
        review_id=body.get("review_id", ""),
        ai_backend=body.get("ai_backend", "files_only"),
        force=bool(body.get("force", False)),
    )
    if result.get("error"):
        respond(result, status=422)
    else:
        respond({"document": result}, status=201)
