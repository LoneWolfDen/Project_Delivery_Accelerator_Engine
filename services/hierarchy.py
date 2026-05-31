"""Hierarchy service — Phase → Version → Review model."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.hierarchy import _make_hierarchy_store
from processors.history import (
    compare_context_versions,
    compare_reviews,
    get_context_version,
    get_evolution_timeline,
    get_review_history,
    list_context_versions,
)
from processors.version_control import get_run_history, get_file_snapshot_for_version
from services.project import PROJECTS_DIR

logger = logging.getLogger(__name__)


# ── Hierarchy tree ────────────────────────────────────────────────────────────

def get_hierarchy(project_id: str) -> Dict[str, Any]:
    return _make_hierarchy_store(project_id).get_hierarchy()


def get_hierarchy_phases(project_id: str) -> List[Dict[str, Any]]:
    return _make_hierarchy_store(project_id).get_phases()


def set_hierarchy_phase(project_id: str, phase_id: str, reason: str = "") -> Dict[str, Any]:
    return _make_hierarchy_store(project_id).set_current_phase(phase_id, reason)


def get_hierarchy_versions(
    project_id: str, phase_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    return _make_hierarchy_store(project_id).list_versions(phase_id)


def get_hierarchy_version_detail(
    project_id: str, version_id: str
) -> Optional[Dict[str, Any]]:
    store = _make_hierarchy_store(project_id)
    version = store.get_version(version_id)
    if version is None:
        return None
    result = version.to_dict()
    result["reviews"] = store.list_reviews(version_id=version_id)
    return result


def get_hierarchy_reviews(
    project_id: str,
    version_id: Optional[str] = None,
    phase_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return _make_hierarchy_store(project_id).list_reviews(version_id=version_id, phase_id=phase_id)


def get_hierarchy_review_detail(
    project_id: str, review_id: str
) -> Optional[Dict[str, Any]]:
    store = _make_hierarchy_store(project_id)
    review = store.get_review(review_id)
    if review is None:
        return None
    result = review.to_dict()
    version = store.get_version(review.version_id)
    if version:
        result["version_context"] = version.to_summary()
    return result


def get_hierarchy_metrics(
    project_id: str,
    version_id: Optional[str] = None,
    review_id: Optional[str] = None,
) -> Dict[str, Any]:
    return _make_hierarchy_store(project_id).get_metrics(version_id=version_id, review_id=review_id)


def set_active_review(project_id: str, version_id: str, review_id: str) -> Dict[str, Any]:
    return _make_hierarchy_store(project_id).set_active_review(version_id, review_id)


def delete_hierarchy_review(project_id: str, review_id: str) -> Dict[str, Any]:
    return _make_hierarchy_store(project_id).delete_review(review_id)


def get_active_review_for_version(
    project_id: str, version_id: str
) -> Optional[Dict[str, Any]]:
    store = _make_hierarchy_store(project_id)
    review = store.get_active_review_for_version(version_id)
    return review.to_dict() if review else None


# ── Version history ───────────────────────────────────────────────────────────

def get_project_versions(project_id: str) -> List[Dict[str, Any]]:
    return list_context_versions(PROJECTS_DIR / project_id)


def get_project_version(project_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    return get_context_version(PROJECTS_DIR / project_id, version_id)


def compare_project_versions(
    project_id: str, version_a: str, version_b: str
) -> Dict[str, Any]:
    return compare_context_versions(PROJECTS_DIR / project_id, version_a, version_b)


def compare_project_reviews(
    project_id: str, review_file_a: str, review_file_b: str
) -> Dict[str, Any]:
    import json
    reviews_dir = PROJECTS_DIR / project_id / "reviews"
    path_a = reviews_dir / review_file_a
    path_b = reviews_dir / review_file_b
    if not path_a.exists():
        raise ValueError(f"Review not found: {review_file_a}")
    if not path_b.exists():
        raise ValueError(f"Review not found: {review_file_b}")
    with open(path_a) as f:
        review_a = json.load(f)
    with open(path_b) as f:
        review_b = json.load(f)
    return compare_reviews(review_a, review_b)


def get_project_evolution(project_id: str, category: str = "risks") -> List[Dict[str, Any]]:
    return get_evolution_timeline(PROJECTS_DIR / project_id, category)


def get_project_review_history(
    project_id: str, persona_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    return get_review_history(PROJECTS_DIR / project_id, persona_id)


def get_run_history_for_project(project_id: str) -> List[Dict[str, Any]]:
    return get_run_history(PROJECTS_DIR / project_id)


def get_file_snapshot(project_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    return get_file_snapshot_for_version(PROJECTS_DIR / project_id, version_id)
