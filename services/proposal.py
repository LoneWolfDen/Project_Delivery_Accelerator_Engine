"""Proposal service — proposal tracker and versioning."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from db.decision_log import get_latest_proposal_document
from db.project_store_sql import (
    _flags as _sql_flags,
    load_proposal_sql,
    save_proposal_sql,
)
from processors.proposal_generator import generate_proposal_document
from processors.proposals import (
    add_proposal_version as _add_proposal_version,
    compare_proposal_versions,
    create_proposal as _create_proposal,
    get_proposal,
    list_proposal_versions,
    update_proposal_status as _update_proposal_status,
)
from processors.prompt_logger import link_outcome as _link_outcome
from processors.review_quality import check_review_gate
from services.intelligence import get_project_intelligence
from services.project import PROJECTS_DIR, get_project

logger = logging.getLogger(__name__)


def create_proposal(
    project_id: str,
    proposal_name: str,
    client: str = "",
    files: Optional[List[Path]] = None,
    notes: str = "",
    hierarchy_version_id: str = "",
    active_review_id: str = "",
) -> Dict[str, Any]:
    if get_project(project_id) is None:
        raise ValueError(f"Project not found: {project_id}")

    if active_review_id:
        try:
            gate = check_review_gate(project_id, active_review_id)
            if not gate["can_set_active"]:
                raise ValueError(
                    f"Review {active_review_id} has not passed the quality gate. "
                    f"Mark it as complete or interim first. Blockers: {'; '.join(gate['blockers'])}"
                )
        except ImportError:
            pass

    project_dir = PROJECTS_DIR / project_id
    intel = get_project_intelligence(project_id)
    ctx_version = (
        hierarchy_version_id
        or (intel.get("_build_metadata", {}).get("built_at", "") if intel else "")
    )

    file_strs = [str(f) for f in (files or [])]
    tracker = _create_proposal(
        project_dir, proposal_name, client, file_strs, notes,
        ctx_version, hierarchy_version_id, active_review_id,
    )

    sql_on, _ = _sql_flags()
    if sql_on:
        save_proposal_sql(project_id, tracker)

    if active_review_id:
        try:
            proposal_ver_id = tracker.get("current_version", "")
            if proposal_ver_id:
                _link_outcome(active_review_id, "proposal_version", proposal_ver_id)
        except Exception:
            pass

    return tracker


def add_proposal_version(
    project_id: str,
    label: str = "",
    files: Optional[List[Path]] = None,
    notes: str = "",
    changes: str = "",
    hierarchy_version_id: str = "",
    active_review_id: str = "",
    feedback_applied: Optional[List[str]] = None,
    changes_summary: str = "",
) -> Dict[str, Any]:
    if active_review_id:
        try:
            gate = check_review_gate(project_id, active_review_id)
            if not gate["can_set_active"]:
                raise ValueError(
                    f"Review {active_review_id} has not passed the quality gate. "
                    f"Blockers: {'; '.join(gate['blockers'])}"
                )
        except ImportError:
            pass

    project_dir = PROJECTS_DIR / project_id
    intel = get_project_intelligence(project_id)
    ctx_version = (
        hierarchy_version_id
        or (intel.get("_build_metadata", {}).get("built_at", "") if intel else "")
    )

    file_strs = [str(f) for f in (files or [])]
    version = _add_proposal_version(
        project_dir, file_strs, label, notes, changes,
        ctx_version, hierarchy_version_id, active_review_id,
        feedback_applied, changes_summary,
    )

    sql_on, _ = _sql_flags()
    if sql_on:
        tracker = load_proposal_sql(project_id)
        if tracker:
            save_proposal_sql(project_id, tracker)

    return version


def get_proposal_info(project_id: str) -> Optional[Dict[str, Any]]:
    sql_on, _ = _sql_flags()
    if sql_on:
        return load_proposal_sql(project_id)
    return get_proposal(PROJECTS_DIR / project_id)


def list_proposal_versions_for_project(project_id: str) -> List[Dict[str, Any]]:
    return list_proposal_versions(PROJECTS_DIR / project_id)


def compare_proposals(
    project_id: str, version_a: str, version_b: str
) -> Dict[str, Any]:
    return compare_proposal_versions(PROJECTS_DIR / project_id, version_a, version_b)


def update_proposal_status(
    project_id: str, version_id: str, new_status: str
) -> Dict[str, Any]:
    project_dir = PROJECTS_DIR / project_id
    result = _update_proposal_status(project_dir, version_id, new_status)
    sql_on, _ = _sql_flags()
    if sql_on:
        tracker = get_proposal(project_dir)
        if tracker:
            save_proposal_sql(project_id, tracker)
    return result


def generate_proposal_doc(
    project_id: str,
    proposal_ver_id: str,
    hierarchy_version_id: str,
    review_id: str,
    ai_backend: str = "files_only",
    force: bool = False,
) -> Dict[str, Any]:
    return generate_proposal_document(
        project_id, proposal_ver_id, hierarchy_version_id, review_id, ai_backend, force,
    )


def get_proposal_doc(project_id: str, proposal_ver_id: str) -> Optional[Dict[str, Any]]:
    return get_latest_proposal_document(project_id, proposal_ver_id)
