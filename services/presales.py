"""Presales service — feedback, tokens, finalisation."""
from __future__ import annotations

import logging
from typing import Any, Dict

from processors.presales_feedback import get_presales_summary
from processors.presales_finaliser import (
    check_stop_condition,
    finalise_presales as _finalise_presales,
)

logger = logging.getLogger(__name__)


def get_presales_stop_condition(project_id: str) -> Dict[str, Any]:
    return check_stop_condition(project_id)


def finalise_presales(
    project_id: str,
    decided_by: str,
    reason: str = "",
    force: bool = False,
) -> Dict[str, Any]:
    return _finalise_presales(project_id, decided_by, reason, force)


def get_presales_summary_for_project(project_id: str) -> Dict[str, Any]:
    return get_presales_summary(project_id)
