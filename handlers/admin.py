"""Admin handlers — config, health, phase transitions."""
from __future__ import annotations

from typing import Any, Callable, Dict

import services.admin as svc


def handle_update_config(body: Dict[str, Any], respond: Callable) -> None:
    try:
        respond({"config": svc.update_admin_config(body)})
    except Exception as e:
        respond({"error": str(e)}, status=500)


def handle_phase_transition(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    new_phase = body.get("new_phase", "")
    if not new_phase:
        respond({"error": "new_phase required"}, status=400)
        return
    try:
        respond(svc.transition_project_phase(project_id, new_phase, body.get("reason", "")))
    except ValueError as e:
        respond({"error": str(e)}, status=400)


def handle_hierarchy_phase_transition(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    from services.hierarchy import set_hierarchy_phase
    phase_id = body.get("phase_id", "")
    if not phase_id:
        respond({"error": "phase_id required"}, status=400)
        return
    try:
        respond(set_hierarchy_phase(project_id, phase_id, body.get("reason", "")))
    except ValueError as e:
        respond({"error": str(e)}, status=400)
