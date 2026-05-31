"""Presales handlers — feedback CRUD, tokens, external submit, finalisation."""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict

from db.project_store_sql import (
    create_feedback_token,
    load_presales_feedback,
    load_presales_feedback_item,
    mark_token_used,
    save_presales_feedback,
    validate_feedback_token,
)
from processors.feedback_classifier import classify_feedback
from processors.presales_feedback import attach_feedback_to_context

import services.presales as svc
import services.proposal as proposal_svc
import services.project as project_svc


# ── GET ────────────────────────────────────────────────────────────────────────

def handle_get_presales_summary(project_id: str, respond: Callable) -> None:
    respond(svc.get_presales_summary_for_project(project_id))


def handle_list_presales_feedback(project_id: str, respond: Callable) -> None:
    items = load_presales_feedback(project_id)
    respond({"project_id": project_id, "feedback": items, "count": len(items)})


def handle_get_presales_feedback_item(
    project_id: str, feedback_id: str, respond: Callable
) -> None:
    item = load_presales_feedback_item(feedback_id)
    if item and item.get("project_id") == project_id:
        respond(item)
    else:
        respond({"error": "Feedback not found"}, status=404)


def handle_feedback_form(token: str, respond: Callable) -> None:
    row = validate_feedback_token(token)
    if not row:
        respond({"error": "Invalid or expired token"}, status=404)
        return
    project_id = row["project_id"]
    proposal = None
    try:
        proposal = proposal_svc.get_proposal_info(project_id)
    except Exception:
        pass
    project = project_svc.get_project(project_id)
    respond({
        "valid": True,
        "project_id": project_id,
        "project_name": project.get("name", "") if project else "",
        "proposal_ver_id": row.get("proposal_ver_id", ""),
        "review_id": row.get("review_id", ""),
        "proposal": proposal,
    })


# ── POST ───────────────────────────────────────────────────────────────────────

def handle_classify_feedback(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    raw_text = body.get("raw_text", "")
    if not raw_text.strip():
        respond({"error": "raw_text is required"}, status=400)
        return
    respond(classify_feedback(raw_text, project_id, body.get("ai_backend", "files_only")))


def handle_create_presales_feedback(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    feedback_id = f"fb_{uuid.uuid4().hex[:8]}"
    feedback_items = body.get("feedback_items") or None
    item = save_presales_feedback(
        project_id=project_id,
        feedback_id=feedback_id,
        proposal_ver_id=body.get("proposal_ver_id", ""),
        review_id=body.get("review_id", ""),
        source=body.get("source", "internal"),
        responder_name=body.get("responder_name", ""),
        responder_email=body.get("responder_email", ""),
        feedback_items=feedback_items,
        raw_text=body.get("raw_text", ""),
        accepted=body.get("accepted", []),
        rejected=body.get("rejected", []),
        concerns=body.get("concerns", []),
        notes=body.get("notes", ""),
        next_action=body.get("next_action", ""),
        status="open",
        version_id=body.get("version_id", ""),
    )
    try:
        attach_feedback_to_context(project_id, item)
    except Exception:
        pass
    respond({"feedback": item}, status=201)


def handle_action_presales_feedback(
    project_id: str, feedback_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    item = load_presales_feedback_item(feedback_id)
    if not item or item.get("project_id") != project_id:
        respond({"error": "Feedback not found"}, status=404)
        return
    updated = save_presales_feedback(
        project_id=project_id,
        feedback_id=feedback_id,
        proposal_ver_id=item["proposal_ver_id"],
        review_id=item["review_id"],
        source=item["source"],
        responder_name=item["responder_name"],
        responder_email=item["responder_email"],
        accepted=item["accepted"],
        rejected=item["rejected"],
        concerns=item["concerns"],
        notes=body.get("notes", item["notes"]),
        next_action=body.get("next_action", item["next_action"]),
        status=body.get("status", item["status"]),
    )
    respond({"feedback": updated})


def handle_create_feedback_token(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    token = create_feedback_token(
        project_id=project_id,
        proposal_ver_id=body.get("proposal_ver_id", ""),
        review_id=body.get("review_id", ""),
        expires_days=int(body.get("expires_days", 7)),
    )
    respond({
        "token": token,
        "share_url": f"/feedback?token={token}",
        "expires_days": body.get("expires_days", 7),
    }, status=201)


def handle_external_feedback_submit(body: Dict[str, Any], respond: Callable) -> None:
    token = body.get("token", "")
    if not token:
        respond({"error": "Token required"}, status=400)
        return
    row = validate_feedback_token(token)
    if not row:
        respond({"error": "Invalid or expired token"}, status=403)
        return
    project_id = row["project_id"]
    feedback_id = f"fb_{uuid.uuid4().hex[:8]}"
    item = save_presales_feedback(
        project_id=project_id,
        feedback_id=feedback_id,
        proposal_ver_id=row.get("proposal_ver_id", ""),
        review_id=row.get("review_id", ""),
        source="external",
        responder_name=body.get("responder_name", ""),
        responder_email=body.get("responder_email", ""),
        accepted=body.get("accepted", []),
        rejected=body.get("rejected", []),
        concerns=body.get("concerns", []),
        notes=body.get("notes", ""),
        next_action="",
        status="open",
    )
    mark_token_used(token)
    try:
        attach_feedback_to_context(project_id, item)
    except Exception:
        pass
    respond({"status": "submitted", "feedback_id": feedback_id}, status=201)
