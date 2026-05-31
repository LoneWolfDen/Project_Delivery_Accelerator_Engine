"""Diagram handlers — generate and retrieve drawio diagrams."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import services.diagram as svc


def handle_generate_diagram(
    project_id: str, diagram_type: str,
    body: Dict[str, Any], respond: Callable
) -> None:
    try:
        result = svc.generate_diagram(
            project_id, diagram_type,
            version_id=body.get("version_id") or None,
            review_id=body.get("review_id") or None,
        )
        if result.get("error"):
            respond(result, status=400)
        else:
            respond(result)
    except Exception as e:
        respond({"error": str(e)}, status=500)
