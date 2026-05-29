"""Decision Log and Proposal Documents — DB persistence (DS-03).

Two responsibilities:
1. log_decision()          — write an immutable audit event to decision_log
2. save_proposal_document() / get_proposal_document() — persist generated docs
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from db.database import get_db, Database

PROJECTS_DIR = Path("projects_data")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────
# Decision Log
# ──────────────────────────────────────────────────────────────

def log_decision(
    project_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str = "",
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Write an immutable audit event to the decision_log table.

    entity_type: review | proposal_version | feedback_item | finalisation
    action:      completed | set_active | generated | feedback_structured |
                 finalised | lock_overridden | gate_passed | gate_failed |
                 loop_started | loop_ended

    Returns the written log entry.
    """
    log_id = f"dl_{uuid.uuid4().hex[:10]}"
    now = _now()
    db = get_db()
    db.execute(
        """INSERT INTO decision_log
           (log_id, project_id, entity_type, entity_id, action,
            actor, reason, metadata, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            log_id, project_id, entity_type, entity_id, action,
            actor, reason, Database.jdump(metadata or {}), now,
        ),
    )
    db.commit()
    return {
        "log_id":      log_id,
        "project_id":  project_id,
        "entity_type": entity_type,
        "entity_id":   entity_id,
        "action":      action,
        "actor":       actor,
        "reason":      reason,
        "metadata":    metadata or {},
        "created_at":  now,
    }


def get_decision_log(
    project_id: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Retrieve decision log entries for a project, newest first.

    Optionally filter by entity_type and/or entity_id.
    """
    sql = "SELECT * FROM decision_log WHERE project_id=?"
    params: list = [project_id]
    if entity_type:
        sql += " AND entity_type=?"
        params.append(entity_type)
    if entity_id:
        sql += " AND entity_id=?"
        params.append(entity_id)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = get_db().fetchall(sql, tuple(params))
    return [_row_to_log(r) for r in rows]


def _row_to_log(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "log_id":      row["log_id"],
        "project_id":  row["project_id"],
        "entity_type": row["entity_type"],
        "entity_id":   row["entity_id"],
        "action":      row["action"],
        "actor":       row.get("actor", ""),
        "reason":      row.get("reason", ""),
        "metadata":    Database.jload(row.get("metadata"), {}),
        "created_at":  row.get("created_at", ""),
    }


# ──────────────────────────────────────────────────────────────
# Proposal Documents
# ──────────────────────────────────────────────────────────────

def save_proposal_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a generated ProposalDocument to proposal_documents.

    Accepts the dict form returned by ProposalDocument.to_dict().
    Returns the saved dict.
    """
    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO proposal_documents
           (doc_id, project_id, proposal_ver_id, generated_at, ai_backend,
            exec_summary, scope, delivery_phases, gantt_data,
            risks, assumptions, exclusions, responsibilities, acceptance_criteria,
            version_label, review_persona, hierarchy_version_id,
            active_review_id, word_count)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            doc.get("doc_id", f"doc_{uuid.uuid4().hex[:8]}"),
            doc.get("project_id", ""),
            doc.get("proposal_ver_id", ""),
            doc.get("generated_at", _now()),
            doc.get("ai_backend", "files_only"),
            doc.get("exec_summary", ""),
            doc.get("scope", ""),
            Database.jdump(doc.get("delivery_phases", [])),
            Database.jdump(doc.get("gantt_data", [])),
            Database.jdump(doc.get("risks", [])),
            Database.jdump(doc.get("assumptions", [])),
            Database.jdump(doc.get("exclusions", [])),
            Database.jdump(doc.get("responsibilities", {})),
            Database.jdump(doc.get("acceptance_criteria", [])),
            doc.get("version_label", ""),
            doc.get("review_persona", ""),
            doc.get("hierarchy_version_id", ""),
            doc.get("active_review_id", ""),
            doc.get("word_count", 0),
        ),
    )
    db.commit()
    return get_proposal_document(doc.get("doc_id", "")) or doc


def get_proposal_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Load a proposal document by doc_id."""
    row = get_db().fetchone(
        "SELECT * FROM proposal_documents WHERE doc_id=?", (doc_id,)
    )
    return _row_to_doc(row) if row else None


def get_latest_proposal_document(
    project_id: str, proposal_ver_id: str
) -> Optional[Dict[str, Any]]:
    """Load the most recent document for a proposal version."""
    row = get_db().fetchone(
        """SELECT * FROM proposal_documents
           WHERE project_id=? AND proposal_ver_id=?
           ORDER BY generated_at DESC LIMIT 1""",
        (project_id, proposal_ver_id),
    )
    return _row_to_doc(row) if row else None


def list_proposal_documents(project_id: str) -> List[Dict[str, Any]]:
    """List all documents for a project (summary, no section blobs)."""
    rows = get_db().fetchall(
        """SELECT doc_id, project_id, proposal_ver_id, generated_at,
                  ai_backend, version_label, review_persona, word_count
           FROM proposal_documents WHERE project_id=?
           ORDER BY generated_at DESC""",
        (project_id,),
    )
    return [dict(r) for r in rows]


def _row_to_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "doc_id":               row["doc_id"],
        "project_id":           row["project_id"],
        "proposal_ver_id":      row["proposal_ver_id"],
        "generated_at":         row["generated_at"],
        "ai_backend":           row.get("ai_backend", "files_only"),
        "exec_summary":         row.get("exec_summary", ""),
        "scope":                row.get("scope", ""),
        "delivery_phases":      Database.jload(row.get("delivery_phases"), []),
        "gantt_data":           Database.jload(row.get("gantt_data"), []),
        "risks":                Database.jload(row.get("risks"), []),
        "assumptions":          Database.jload(row.get("assumptions"), []),
        "exclusions":           Database.jload(row.get("exclusions"), []),
        "responsibilities":     Database.jload(row.get("responsibilities"), {}),
        "acceptance_criteria":  Database.jload(row.get("acceptance_criteria"), []),
        "version_label":        row.get("version_label", ""),
        "review_persona":       row.get("review_persona", ""),
        "hierarchy_version_id": row.get("hierarchy_version_id", ""),
        "active_review_id":     row.get("active_review_id", ""),
        "word_count":           row.get("word_count", 0),
    }
