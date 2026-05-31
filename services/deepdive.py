"""Deep-dive service — SME question generation and feedback."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from admin.config import load_config
from models.hierarchy import _make_hierarchy_store
from personas.deep_dive import apply_feedback, run_deep_dive as _run_deep_dive
from processors.review_quality import compute_missing_categories, extract_weaknesses
from services.ingest import get_project_context
from services.intelligence import get_project_intelligence
from services.project import PROJECTS_DIR, get_file_toggles, get_project

logger = logging.getLogger(__name__)


def run_deep_dive_analysis(
    project_id: str,
    persona_name: str = "",
    custom_prompt: str = "",
    weaknesses: Optional[List[Dict[str, Any]]] = None,
    missing_categories: Optional[List[str]] = None,
    decision_points: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run explicit Deep Dive analysis (standalone, not part of review)."""
    if get_project(project_id) is None:
        raise ValueError(f"Project not found: {project_id}")

    intelligence = get_project_intelligence(project_id)
    if not intelligence:
        raise ValueError("No intelligence built. Run intelligence first.")

    documents = get_project_context(project_id)
    file_toggles = get_file_toggles(project_id)
    active_files = [
        {"filename": d.get("filename", ""), "source_type": d.get("metadata", {}).get("source_type", "")}
        for d in documents
        if file_toggles.get(d.get("filename", ""), True)
    ]

    if not persona_name:
        try:
            persona_name = load_config().default_persona
        except Exception:
            persona_name = "solution_architect"

    project = get_project(project_id)
    result = _run_deep_dive(
        persona_name=persona_name,
        scope=intelligence.get("scope", ""),
        intelligence=intelligence,
        active_files=active_files,
        custom_prompt=custom_prompt,
        ai_backend=(project or {}).get("ai_backend", "files_only"),
        weaknesses=weaknesses,
        missing_categories=missing_categories,
        decision_points=decision_points,
    )

    project_dir = PROJECTS_DIR / project_id
    intelligence_dir = project_dir / "intelligence"
    intelligence_dir.mkdir(parents=True, exist_ok=True)
    with open(intelligence_dir / "last_deep_dive.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def apply_deep_dive_feedback(
    project_id: str,
    accepted: Optional[List[str]] = None,
    rejected: Optional[List[str]] = None,
    added_to_prompt: Optional[List[str]] = None,
) -> Dict[str, Any]:
    feedback_file = PROJECTS_DIR / project_id / "intelligence" / "last_deep_dive.json"
    if not feedback_file.exists():
        return {"error": "No deep dive result found. Run deep dive first."}
    with open(feedback_file) as f:
        deep_dive = json.load(f)
    updated = apply_feedback(deep_dive, accepted, rejected, added_to_prompt)
    with open(feedback_file, "w") as f:
        json.dump(updated, f, indent=2)
    return {
        "status": "feedback_applied",
        "accepted_count": len(accepted or []),
        "rejected_count": len(rejected or []),
        "added_to_prompt_count": len(added_to_prompt or []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def load_deep_dive_context_from_review(
    project_id: str, review_id: str
) -> Dict[str, Any]:
    """Load weakness/missing/decision context from a stored review for the handler."""
    result: Dict[str, Any] = {"weaknesses": [], "missing_categories": [], "decision_points": []}
    try:
        store = _make_hierarchy_store(project_id)
        review = store.get_review(review_id)
        if review:
            result["weaknesses"] = extract_weaknesses(review.findings)
            result["missing_categories"] = compute_missing_categories(review.findings)
            result["decision_points"] = [
                dp for dp in (review.decision_points or [])
                if dp.get("status", "open") == "open"
            ]
    except Exception:
        pass
    return result
