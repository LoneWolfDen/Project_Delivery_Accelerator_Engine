"""Intelligence handlers — build context, list personas."""
from __future__ import annotations

from typing import Any, Callable, Dict

import services.intelligence as svc
from personas.engine import list_roles


def handle_build_context(project_id: str, body: Dict[str, Any], respond: Callable) -> None:
    try:
        result = svc.build_project_intelligence(
            project_id,
            version_label=body.get("label"),
            ai_backend=body.get("ai_backend"),
        )
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=404)
    except Exception as e:
        respond({"error": str(e)}, status=500)


def handle_list_personas(respond: Callable) -> None:
    roles = list_roles()
    respond({"personas": roles, "roles": roles})
