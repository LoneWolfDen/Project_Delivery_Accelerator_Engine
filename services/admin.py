"""Admin service — config, health, lifecycle logs, guardrails."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from admin.config import load_config, update_config as _update_config
from admin.guardrails import validate_file_types
from admin.health import get_system_health
from admin.lifecycle import get_lifecycle_log
from processors.phases import (
    get_phase_history,
    get_phase_info as _get_phase_info,
    transition_phase,
)
from services.project import PROJECTS_DIR, PROJECTS_FILE

logger = logging.getLogger(__name__)


def get_admin_config() -> Dict[str, Any]:
    return load_config().to_safe_dict()


def update_admin_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    return _update_config(updates).to_safe_dict()


def get_system_health_status() -> Dict[str, Any]:
    return get_system_health().to_dict()


def get_lifecycle_logs() -> Dict[str, Any]:
    return get_lifecycle_log().to_dict()


def validate_files_for_ingestion(file_paths: List[str]) -> Dict[str, Any]:
    all_valid, valid_paths, errors = validate_file_types(file_paths)
    return {
        "all_valid": all_valid,
        "valid_paths": valid_paths,
        "errors": errors,
        "valid_count": len(valid_paths),
        "invalid_count": len(errors),
    }


def transition_project_phase(
    project_id: str, new_phase: str, reason: str = ""
) -> Dict[str, Any]:
    return transition_phase(PROJECTS_DIR / project_id, PROJECTS_FILE, project_id, new_phase, reason)


def get_phase_history_for_project(project_id: str) -> List[Dict[str, Any]]:
    return get_phase_history(PROJECTS_DIR / project_id, PROJECTS_FILE, project_id)


def get_phase_info() -> List[Dict[str, Any]]:
    return _get_phase_info()
