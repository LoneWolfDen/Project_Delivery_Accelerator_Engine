"""Intelligence service — build and load project intelligence."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from admin.guardrails import validate_intelligence_run
from admin.health import record_intelligence_run
from db.artifact_store_sql import (
    get_artifact_text_content as _get_artifact_text,
    list_artifacts as _list_artifacts_sql,
)
from models.hierarchy import _make_hierarchy_store
from processors.context_builder import build_context, build_context_summary
from processors.history import save_context_version
from processors.pipeline import get_processed_document
from processors.version_control import create_run_record
from services.project import (
    PROJECTS_DIR,
    get_project,
    get_file_toggles,
    update_iteration_on_build,
)
from services.ingest import get_project_context

logger = logging.getLogger(__name__)


def build_project_intelligence(
    project_id: str,
    version_label: Optional[str] = None,
    ai_backend: Optional[str] = None,
) -> Dict[str, Any]:
    """Build (or rebuild) project intelligence from all ingested documents."""
    start_time = time.time()

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    documents = get_project_context(project_id)

    # Merge artifact v1 inputs
    artifact_docs: List[Dict[str, Any]] = []
    try:
        all_artifacts = _list_artifacts_sql(project_id)
        for art in all_artifacts:
            if not art.get("include", True):
                continue
            aid = art.get("artifactId") or art.get("artifact_id", "")
            if not aid:
                continue
            processed = get_processed_document(project_id, aid)
            if processed and processed.get("content", "").strip():
                content = processed["content"]
            else:
                content = _get_artifact_text(project_id, aid)
            if not content or not content.strip():
                continue
            label = art.get("title") or art.get("fileName") or aid
            artifact_docs.append({
                "filename": label,
                "is_valid": True,
                "content": content,
                "sections": [{"heading": label, "content": content, "section_type": "body"}],
                "metadata": {
                    "source_type": art.get("category", "project_artefact"),
                    "filename": art.get("fileName") or aid,
                    "artifact_id": aid,
                    "word_count": len(content.split()),
                },
            })
    except Exception:
        pass

    total_inputs = len(documents) + len(artifact_docs)

    try:
        valid, errors = validate_intelligence_run(
            project_id, total_inputs, project.get("ai_backend", "files_only")
        )
        if not valid:
            raise ValueError("; ".join(errors))
    except ImportError:
        if total_inputs == 0:
            raise ValueError(f"No documents ingested for project: {project_id}")

    if total_inputs == 0:
        raise ValueError(
            "No processable inputs found. Upload artefacts via the Ingest tab, "
            "run 'Re-process Included' to extract text, then retry."
        )

    file_toggles = get_file_toggles(project_id)
    active_docs = [
        doc for doc in documents
        if file_toggles.get(doc.get("filename", doc.get("metadata", {}).get("filename", "")), True)
    ]
    active_docs.extend(artifact_docs)

    if not active_docs:
        raise ValueError(
            "All artefacts are excluded. Mark at least one artefact as Included "
            "and ensure it has been processed (status: processed)."
        )

    effective_backend = ai_backend or project.get("ai_backend", "files_only")
    context = build_context(active_docs, ai_backend=effective_backend)

    # Persist intelligence
    project_dir = PROJECTS_DIR / project_id
    intelligence_dir = project_dir / "intelligence"
    intelligence_dir.mkdir(exist_ok=True)
    with open(intelligence_dir / "current.json", "w") as f:
        json.dump(context, f, indent=2)
    with open(project_dir / "intelligence.json", "w") as f:
        json.dump(context, f, indent=2)

    version_meta = save_context_version(project_dir, context, version_label)

    # Version control record
    try:
        file_info = [
            {"filename": d.get("filename", ""), "source_type": d.get("metadata", {}).get("source_type", "")}
            for d in documents + artifact_docs
        ]
        create_run_record(
            project_dir=project_dir,
            project_id=project_id,
            run_type="intelligence_build",
            input_files=file_info,
            ai_backend=project.get("ai_backend", "files_only"),
            file_toggles=file_toggles,
            version_label=version_label or "",
            outputs=[version_meta["version_id"]],
        )
    except Exception:
        pass

    # Hierarchy version
    try:
        store = _make_hierarchy_store(project_id)
        included = [
            {"filename": d.get("filename", ""), "category": d.get("metadata", {}).get("source_type", "")}
            for d in active_docs
        ]
        excluded_legacy = [
            {"filename": d.get("filename", ""), "category": d.get("metadata", {}).get("source_type", "")}
            for d in documents if d not in active_docs
        ]
        excluded_artifacts: List[Dict[str, Any]] = []
        try:
            for art in _list_artifacts_sql(project_id):
                aid = art.get("artifactId") or art.get("artifact_id", "")
                is_active = any(
                    d.get("metadata", {}).get("artifact_id") == aid for d in artifact_docs
                )
                if not is_active:
                    excluded_artifacts.append({
                        "filename": art.get("title") or art.get("fileName") or aid,
                        "category": art.get("category", ""),
                    })
        except Exception:
            pass
        store.create_version(
            included_artifacts=included,
            excluded_artifacts=excluded_legacy + excluded_artifacts,
            persona=project.get("settings", {}).get("default_persona", ""),
            scope=context.get("scope", ""),
            ai_backend=effective_backend,
            label=version_label or version_meta.get("label", ""),
            stats=version_meta.get("stats", {}),
        )
    except Exception:
        pass

    update_iteration_on_build(project_id, version_meta)

    duration_ms = (time.time() - start_time) * 1000
    try:
        record_intelligence_run(
            project_id=project_id,
            project_name=project.get("name", ""),
            success=True,
            version_id=version_meta["version_id"],
            duration_ms=duration_ms,
        )
    except Exception:
        pass

    context["_version"] = version_meta
    return context


def get_project_intelligence(project_id: str) -> Dict[str, Any]:
    """Load built intelligence for a project."""
    intelligence_path = PROJECTS_DIR / project_id / "intelligence.json"
    if not intelligence_path.exists():
        return {}
    with open(intelligence_path) as f:
        return json.load(f)


def get_project_summary(project_id: str) -> str:
    intelligence = get_project_intelligence(project_id)
    if not intelligence:
        return "No intelligence built yet. Run build-context first."
    return build_context_summary(intelligence)
