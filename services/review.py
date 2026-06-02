"""Review service — persona review runs, quality, weakness/decision tracking."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from admin.guardrails import validate_review_prerequisites
from db.artifact_store_sql import list_artifacts as _list_artifacts_sql
from models.hierarchy import _make_hierarchy_store
from personas.deep_dive import run_deep_dive as _run_deep_dive
from personas.engine import run_review as _run_review
from processors.prompt_logger import log_prompt as _log_prompt
from processors.review_quality import (
    DECISION_STATUSES,
    check_review_gate,
    complete_review,
    compute_decision_readiness,
    compute_missing_categories,
    extract_decision_points,
    extract_weaknesses,
    set_active_review_with_gate,
)
from contracts.bus import bus
from contracts.types import Event, ReviewResult, Topics
from processors.version_control import create_run_record
from services.ingest import get_project_context
from services.intelligence import get_project_intelligence
from services.project import (
    PROJECTS_DIR,
    get_file_toggles,
    get_project,
    load_projects,
    save_projects,
    update_iteration_on_review,
)

logger = logging.getLogger(__name__)


def roles_list(persona_name: Union[str, List[str]]) -> List[str]:
    """Normalise persona_name to a list of role strings."""
    if isinstance(persona_name, list):
        return persona_name
    return [persona_name] if persona_name else []


def run_persona_review(
    project_id: str,
    persona_name: Union[str, List[str]],
    ai_backend: str = "files_only",
    custom_prompt: Optional[str] = None,
    previous_review_id: str = "",
    prompt_builder_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run a persona-driven review for a project."""
    bus.publish(Event(
        topic=Topics.REVIEW_STARTED,
        payload={"project_id": project_id, "roles": roles_list(persona_name), "ai_backend": ai_backend},
        source="services.review",
    ))
    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    intelligence = get_project_intelligence(project_id)
    if not intelligence:
        raise ValueError(
            f"No intelligence built for project: {project_id}. "
            "Run build-context first."
        )

    store = _make_hierarchy_store(project_id)
    if not store.list_versions():
        raise ValueError(
            "No intelligence version found for this project. "
            "Run 'Build Intelligence' on the Ingest tab first, then run a review."
        )

    try:
        validate_review_prerequisites(project_id, bool(intelligence), ai_backend)
    except ImportError:
        pass

    intelligence["_project_id"] = project_id
    review = _run_review(
        roles=persona_name,
        context=intelligence,
        ai_backend=ai_backend,
        custom_prompt=custom_prompt,
    )

    roles_used = review.get("roles", [persona_name] if isinstance(persona_name, str) else persona_name)
    canonical_persona = " / ".join(roles_used) if roles_used else str(persona_name)

    if ai_backend != "files_only":
        try:
            documents = get_project_context(project_id)
            file_toggles = get_file_toggles(project_id)
            active_files = [
                {"filename": d.get("filename", ""), "source_type": d.get("metadata", {}).get("source_type", "")}
                for d in documents
                if file_toggles.get(d.get("filename", ""), True)
            ]
            deep_dive = _run_deep_dive(
                persona_name=persona_name,
                scope=intelligence.get("scope", ""),
                intelligence=intelligence,
                active_files=active_files,
                custom_prompt=custom_prompt or "",
                ai_backend=ai_backend,
            )
            review["deep_dive"] = deep_dive
        except Exception:
            pass

    _store_review(project_id, review)

    try:
        project_dir = PROJECTS_DIR / project_id
        documents = get_project_context(project_id)
        file_info = [
            {"filename": d.get("filename", ""), "source_type": d.get("metadata", {}).get("source_type", "")}
            for d in documents
        ]
        file_toggles = get_file_toggles(project_id)
        create_run_record(
            project_dir=project_dir,
            project_id=project_id,
            run_type="persona_review",
            input_files=file_info,
            persona_used=canonical_persona,
            ai_backend=ai_backend,
            file_toggles=file_toggles,
            outputs=[review.get("timestamp", "")],
        )
    except Exception:
        pass

    versions = store.list_versions()
    if not versions:
        raise ValueError(
            "No intelligence version found. "
            "Run 'Build Intelligence' on the Ingest tab before running a review."
        )
    latest_version_id = versions[0]["version_id"]

    documents = get_project_context(project_id)
    file_toggles = get_file_toggles(project_id)
    legacy_included_files = [
        d.get("filename", "")
        for d in documents
        if file_toggles.get(d.get("filename", ""), True) and d.get("filename", "")
    ]
    legacy_categories = list(set(
        d.get("metadata", {}).get("source_type", "")
        for d in documents
        if file_toggles.get(d.get("filename", ""), True)
        and d.get("metadata", {}).get("source_type", "")
    ))

    artifact_included_files: List[str] = []
    artifact_categories: List[str] = []
    try:
        for art in _list_artifacts_sql(project_id):
            if art.get("include", True):
                label = art.get("title") or art.get("fileName") or art.get("artifactId", "")
                if label:
                    artifact_included_files.append(label)
                cat = art.get("category", "")
                if cat:
                    artifact_categories.append(cat)
    except Exception:
        pass

    included_files = list(dict.fromkeys(legacy_included_files + artifact_included_files))
    categories = list(dict.fromkeys(legacy_categories + artifact_categories))

    review_findings = review.get("findings", {})
    computed_weaknesses = extract_weaknesses(review_findings)
    computed_missing = compute_missing_categories(review_findings)
    computed_decision_points = extract_decision_points(review_findings)

    if previous_review_id:
        try:
            pred = store.get_review(previous_review_id)
            if pred:
                inherited = [dp for dp in (pred.decision_points or []) if dp.get("status") == "open"]
                existing_texts = {dp["text"] for dp in computed_decision_points}
                for dp in inherited:
                    if dp["text"] not in existing_texts:
                        new_dp = dict(dp)
                        new_dp["id"] = f"d{len(computed_decision_points) + 1}"
                        computed_decision_points.append(new_dp)
                        existing_texts.add(dp["text"])
        except Exception:
            pass

    store.create_review(
        version_id=latest_version_id,
        persona=canonical_persona,
        ai_backend=ai_backend,
        prompt_used=review.get("prompt_used", ""),
        custom_prompt=custom_prompt or "",
        findings=review.get("findings", {}),
        questions=review.get("questions", []),
        summary=review.get("summary", ""),
        included_files=included_files,
        categories=categories,
        ai_metadata=review.get("ai_metadata", {}),
        deep_dive=review.get("deep_dive"),
        previous_review_id=previous_review_id,
        prompt_builder_state=prompt_builder_state,
        weaknesses=computed_weaknesses,
        decision_points=computed_decision_points,
    )

    try:
        created_reviews = store.list_reviews(version_filter=latest_version_id)
        created_review_id = created_reviews[0]["review_id"] if created_reviews else ""
        _log_prompt(
            project_id=project_id,
            review_id=created_review_id,
            prompt_builder_state=prompt_builder_state or {},
            final_prompt=review.get("prompt_used", ""),
            persona_name=canonical_persona,
            scenario_type=(prompt_builder_state or {}).get("scenario_type", ""),
        )
    except Exception:
        pass

    review["weaknesses"] = computed_weaknesses
    review["missing_categories"] = computed_missing
    review["decision_points"] = computed_decision_points

    update_iteration_on_review(project_id)

    # Publish completion event so subscribers (logging, metrics, future agents) are notified
    bus.publish(Event(
        topic=Topics.REVIEW_COMPLETED,
        payload={
            "project_id": project_id,
            "review_id": review.get("review_id", ""),
            "persona": canonical_persona,
            "ai_backend": ai_backend,
            "weakness_count": len(computed_weaknesses),
            "decision_point_count": len(computed_decision_points),
            "missing_category_count": len(computed_missing),
        },
        source="services.review",
    ))

    return review


def _store_review(project_id: str, review: Dict[str, Any]) -> None:
    reviews_dir = PROJECTS_DIR / project_id / "reviews"
    reviews_dir.mkdir(exist_ok=True)
    persona_id = review.get("persona_id", "unknown")
    timestamp = review.get("timestamp", "").replace(":", "-").replace("+", "")[:19]
    filename = f"{persona_id}_{timestamp}.json"
    with open(reviews_dir / filename, "w") as f:
        json.dump(review, f, indent=2)


def get_project_reviews(project_id: str) -> List[Dict[str, Any]]:
    reviews_dir = PROJECTS_DIR / project_id / "reviews"
    if not reviews_dir.exists():
        return []
    reviews = []
    for json_file in sorted(reviews_dir.glob("*.json"), reverse=True):
        with open(json_file) as f:
            reviews.append(json.load(f))
    return reviews


# ── Quality gate ──────────────────────────────────────────────────────────────

def get_review_quality(project_id: str, review_id: str) -> Dict[str, Any]:
    return check_review_gate(project_id, review_id)


def complete_review_gate(
    project_id: str, review_id: str, completed_by: str, quality_status: str = "complete"
) -> Dict[str, Any]:
    return complete_review(project_id, review_id, completed_by, quality_status)


def set_active_review_gated(
    project_id: str, version_id: str, review_id: str, decided_by: str, force: bool = False
) -> Dict[str, Any]:
    return set_active_review_with_gate(project_id, version_id, review_id, decided_by, force)


# ── Weakness / decision status ────────────────────────────────────────────────

def update_weakness_status(
    project_id: str, review_id: str, weakness_id: str, status: str
) -> Dict[str, Any]:
    if status not in DECISION_STATUSES:
        return {"error": f"Invalid status '{status}'. Must be one of: {', '.join(DECISION_STATUSES)}"}
    store = _make_hierarchy_store(project_id)
    review = store.get_review(review_id)
    if review is None:
        return {"error": f"Review not found: {review_id}"}
    weaknesses = list(review.weaknesses or [])
    target = next((w for w in weaknesses if w.get("id") == weakness_id), None)
    if target is None:
        return {"error": f"Weakness '{weakness_id}' not found in review {review_id}"}
    target["status"] = status
    store.update_review_weaknesses(review_id, weaknesses)
    return {"review_id": review_id, "weakness_id": weakness_id, "status": status, "updated": True}


def update_decision_status(
    project_id: str, review_id: str, decision_id: str, status: str
) -> Dict[str, Any]:
    if status not in DECISION_STATUSES:
        return {"error": f"Invalid status '{status}'. Must be one of: {', '.join(DECISION_STATUSES)}"}
    store = _make_hierarchy_store(project_id)
    review = store.get_review(review_id)
    if review is None:
        return {"error": f"Review not found: {review_id}"}
    dps = list(review.decision_points or [])
    target = next((dp for dp in dps if dp.get("id") == decision_id), None)
    if target is None:
        return {"error": f"Decision point '{decision_id}' not found in review {review_id}"}
    target["status"] = status
    store.update_review_decision_points(review_id, dps)
    return {"review_id": review_id, "decision_id": decision_id, "status": status, "updated": True}


# ── Diff ──────────────────────────────────────────────────────────────────────

def get_review_diff(project_id: str, review_id: str) -> Dict[str, Any]:
    store = _make_hierarchy_store(project_id)
    review = store.get_review(review_id)
    if review is None:
        return {"error": f"Review not found: {review_id}"}
    if not review.previous_review_id:
        return {"error": "Review has no predecessor — diff not available"}
    pred = store.get_review(review.previous_review_id)
    if pred is None:
        return {"error": f"Predecessor review '{review.previous_review_id}' not found"}

    def _diff_findings(curr: Dict, prev: Dict) -> Dict[str, Any]:
        def _flatten(f):
            pairs: set = set()
            for cat, items in (f or {}).items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str):
                            pairs.add((cat, item.strip()))
            return pairs
        curr_set = _flatten(curr)
        prev_set = _flatten(prev)
        return {
            "new": sorted([{"category": c, "text": t} for c, t in curr_set - prev_set], key=lambda x: (x["category"], x["text"])),
            "resolved": sorted([{"category": c, "text": t} for c, t in prev_set - curr_set], key=lambda x: (x["category"], x["text"])),
            "unchanged": len(curr_set & prev_set),
        }

    def _diff_list(curr: List, prev: List) -> Dict[str, Any]:
        curr_map = {(i.get("text", "").strip(), i.get("category", "")): i for i in (curr or []) if isinstance(i, dict)}
        prev_map = {(i.get("text", "").strip(), i.get("category", "")): i for i in (prev or []) if isinstance(i, dict)}
        new_keys = set(curr_map) - set(prev_map)
        resolved_keys = set(prev_map) - set(curr_map)
        return {
            "new": sorted([curr_map[k] for k in new_keys], key=lambda x: x.get("text", "")),
            "resolved": sorted([prev_map[k] for k in resolved_keys], key=lambda x: x.get("text", "")),
            "unchanged": len(set(curr_map) & set(prev_map)),
        }

    return {
        "review_id": review_id,
        "previous_review_id": review.previous_review_id,
        "findings": _diff_findings(review.findings, pred.findings),
        "weaknesses": _diff_list(review.weaknesses, pred.weaknesses),
        "decision_points": _diff_list(review.decision_points, pred.decision_points),
    }


# ── Readiness ─────────────────────────────────────────────────────────────────

def get_version_readiness(project_id: str, version_id: str) -> Dict[str, Any]:
    from dataclasses import asdict as _asdict
    store = _make_hierarchy_store(project_id)
    version = store.get_version(version_id)
    if version is None:
        return {"error": f"Version not found: {version_id}"}
    if not version.active_review_id:
        return {
            "version_id": version_id, "review_id": "", "level": "Low",
            "open_decisions": 0, "open_weaknesses": 0,
            "note": "No active review set for this version",
        }
    review = store.get_review(version.active_review_id)
    if review is None:
        return {"error": f"Active review not found: {version.active_review_id}"}
    try:
        review_dict = _asdict(review)
    except TypeError:
        review_dict = review.__dict__ if hasattr(review, "__dict__") else {}
    readiness = compute_decision_readiness(review_dict)
    return {"version_id": version_id, "review_id": version.active_review_id, **readiness}


# ── Prompt history ────────────────────────────────────────────────────────────

def get_prompt_history(
    project_id: str,
    persona_name: Optional[str] = None,
    scenario_type: Optional[str] = None,
) -> Dict[str, Any]:
    from processors.prompt_logger import query_prompts
    prompts = query_prompts(project_id, persona_name=persona_name, scenario_type=scenario_type)
    return {"prompts": prompts, "count": len(prompts)}
