"""Prompt Logger — S7-03 / S7-04.

Captures the full prompt state and outcome links on every review so the
system can learn from past prompts in future sprints.

Public API
──────────
log_prompt(project_id, review_id, prompt_builder_state, final_prompt,
           persona_name, scenario_type)
    → INSERT a row into prompt_log.

link_outcome(review_id, outcome_type, outcome_id)
    → UPDATE prompt_log to record the proposal_version or follow-up review
      linked to a logged prompt.

query_prompts(project_id, persona_name=None, scenario_type=None, limit=20)
    → SELECT from prompt_log with optional equality filters.
      Returns a list of dicts.

Rules
─────
- All operations are non-blocking; callers catch exceptions.
- persona_name / scenario_type come from prompt_builder_state when present
  (AR-04), otherwise from explicit arguments.
- No retraining, ranking, or autonomous behaviour.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_prompt(
    project_id: str,
    review_id: str,
    prompt_builder_state: Dict[str, Any],
    final_prompt: str,
    persona_name: str = "",
    scenario_type: str = "",
) -> str:
    """Insert a prompt_log row for a newly created review.

    Args:
        project_id:           Project identifier.
        review_id:            The review that was just created.
        prompt_builder_state: The prompt_builder_state dict from the review
                              (may be empty dict — never None at this point).
        final_prompt:         The assembled prompt string sent to the LLM
                              (review.prompt_used).
        persona_name:         Canonical persona label (fallback when not in state).
        scenario_type:        Scenario type string (fallback when not in state).

    Returns:
        The log_id of the inserted row.
    """
    from db.database import get_db

    state = prompt_builder_state or {}

    # AR-04: prefer values from prompt_builder_state; fall back to arguments
    resolved_persona = state.get("persona_name") or persona_name or ""
    resolved_scenario = state.get("scenario_type") or scenario_type or ""

    baseline_prompt = state.get("baseline_prompt", "")
    injected_questions_raw = state.get("injected_questions", [])
    injected_questions = (
        json.dumps(injected_questions_raw)
        if isinstance(injected_questions_raw, (list, dict))
        else str(injected_questions_raw)
    )
    user_notes = state.get("user_notes", "")

    log_id = f"pl-{uuid.uuid4().hex[:12]}"

    db = get_db()
    db.execute(
        """
        INSERT INTO prompt_log
            (log_id, project_id, review_id, persona_name, scenario_type,
             baseline_prompt, injected_questions, user_notes, final_prompt,
             outcome_review_id, outcome_proposal_ver_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', ?)
        """,
        (
            log_id, project_id, review_id, resolved_persona, resolved_scenario,
            baseline_prompt, injected_questions, user_notes, final_prompt,
            _now(),
        ),
    )
    db.commit()
    return log_id


def link_outcome(
    review_id: str,
    outcome_type: str,
    outcome_id: str,
) -> None:
    """Update a prompt_log row with an outcome link.

    Called after a proposal version is created to record which proposal
    version was produced from a logged prompt.

    Args:
        review_id:    The review whose prompt log entry should be updated.
        outcome_type: "proposal_version" or "review".
        outcome_id:   The ID of the outcome (proposal_ver_id or review_id).
    """
    from db.database import get_db

    db = get_db()
    if outcome_type == "proposal_version":
        db.execute(
            "UPDATE prompt_log SET outcome_proposal_ver_id = ? WHERE review_id = ?",
            (outcome_id, review_id),
        )
    elif outcome_type == "review":
        db.execute(
            "UPDATE prompt_log SET outcome_review_id = ? WHERE review_id = ?",
            (outcome_id, review_id),
        )
    db.commit()


def query_prompts(
    project_id: str,
    persona_name: Optional[str] = None,
    scenario_type: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Retrieve logged prompt entries for a project.

    Supports optional equality filtering on persona_name and/or
    scenario_type (AR-04).  Returns up to ``limit`` rows ordered newest
    first.

    Args:
        project_id:   Project to query.
        persona_name: Optional exact-match filter.
        scenario_type: Optional exact-match filter.
        limit:        Maximum rows to return (default 20).

    Returns:
        List of dicts, each representing one prompt_log row.
    """
    from db.database import get_db

    db = get_db()
    conditions = ["project_id = ?"]
    params: List[Any] = [project_id]

    if persona_name is not None:
        conditions.append("persona_name = ?")
        params.append(persona_name)

    if scenario_type is not None:
        conditions.append("scenario_type = ?")
        params.append(scenario_type)

    where = " AND ".join(conditions)
    params.append(limit)

    rows = db.fetchall(
        f"SELECT * FROM prompt_log WHERE {where} ORDER BY created_at DESC LIMIT ?",
        tuple(params),
    )
    return rows
