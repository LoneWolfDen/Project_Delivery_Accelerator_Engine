"""Diagram service — drawio diagram generation and storage."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.hierarchy import _make_hierarchy_store
from processors.diagram_generator import DIAGRAM_TYPES as VALID_DIAGRAM_TYPES
from processors.diagram_generator import generate as _generate_diagram
from services.intelligence import get_project_intelligence
from services.project import PROJECTS_DIR

logger = logging.getLogger(__name__)


def generate_diagram(
    project_id: str,
    diagram_type: str,
    version_id: Optional[str] = None,
    review_id: Optional[str] = None,
) -> Dict[str, Any]:
    if diagram_type not in VALID_DIAGRAM_TYPES:
        raise ValueError(
            f"Unknown diagram type '{diagram_type}'. "
            f"Available: {', '.join(VALID_DIAGRAM_TYPES)}"
        )
    intelligence = get_project_intelligence(project_id)
    if not intelligence:
        raise ValueError(f"No intelligence built for project '{project_id}'. Run Intelligence first.")

    if review_id or version_id:
        try:
            store = _make_hierarchy_store(project_id)
            target_review = None
            if review_id:
                target_review = store.get_review(review_id)
            elif version_id:
                target_review = store.get_active_review_for_version(version_id)

            if target_review and target_review.findings:
                findings = target_review.findings
                for cat in ("risks", "assumptions", "dependencies", "constraints", "action_items"):
                    base: List[Any] = list(intelligence.get(cat) or [])
                    extra = findings.get(cat) or []
                    seen = {str(x).lower() for x in base}
                    for item in extra:
                        if str(item).lower() not in seen:
                            base.append(item)
                            seen.add(str(item).lower())
                    intelligence[cat] = base

                if version_id and not intelligence.get("scope"):
                    ver = store.get_version(version_id)
                    if ver and ver.scope:
                        intelligence["scope"] = ver.scope

                intelligence["_review_context"] = {
                    "version_id": version_id or target_review.version_id,
                    "review_id": target_review.review_id,
                    "persona": target_review.persona,
                }
        except Exception:
            pass

    xml = _generate_diagram(diagram_type, intelligence)
    diagram_dir = PROJECTS_DIR / project_id / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    out_path = diagram_dir / f"{diagram_type}.drawio"
    out_path.write_text(xml, encoding="utf-8")

    return {
        "project_id": project_id,
        "diagram_type": diagram_type,
        "xml": xml,
        "path": str(out_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(xml.encode()),
    }


def get_diagram(project_id: str, diagram_type: str) -> Dict[str, Any]:
    if diagram_type not in VALID_DIAGRAM_TYPES:
        return {"error": f"Unknown diagram type '{diagram_type}'."}
    out_path = PROJECTS_DIR / project_id / "diagrams" / f"{diagram_type}.drawio"
    if not out_path.exists():
        return {"error": f"Diagram '{diagram_type}' not yet generated."}
    xml = out_path.read_text(encoding="utf-8")
    return {
        "project_id": project_id,
        "diagram_type": diagram_type,
        "xml": xml,
        "path": str(out_path),
        "size_bytes": len(xml.encode()),
    }


def list_diagrams(project_id: str) -> Dict[str, Any]:
    diagram_dir = PROJECTS_DIR / project_id / "diagrams"
    diagrams = []
    for dtype in VALID_DIAGRAM_TYPES:
        p = diagram_dir / f"{dtype}.drawio"
        if p.exists():
            diagrams.append({"diagram_type": dtype, "path": str(p), "size_bytes": p.stat().st_size})
    return {"project_id": project_id, "diagrams": diagrams, "available_types": VALID_DIAGRAM_TYPES}
