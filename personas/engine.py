"""Persona Review Engine.

Runs structured analysis using predefined personas (roles).
Each persona has a specific prompt template and output format.
"""

from pathlib import Path
from typing import Dict, Any, Optional

PERSONAS_DIR = Path(__file__).parent / "definitions"


def load_persona(persona_name: str) -> Dict[str, Any]:
    """Load a persona definition from YAML.

    Args:
        persona_name: e.g. 'solution_architect', 'delivery_manager'

    Returns:
        Persona config dict with keys: name, role, prompt_template,
        output_format, focus_areas.
    """
    raise NotImplementedError("Persona loading not yet implemented")


def run_review(
    persona_name: str,
    context: Dict[str, Any],
    ai_backend: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a persona-driven review against project context.

    Args:
        persona_name: Which persona to use.
        context: Structured project context pack.
        ai_backend: 'ollama', 'bedrock', or None (files-only).

    Returns:
        Review output with keys: risks, assumptions, gaps,
        recommendations, questions.
    """
    raise NotImplementedError("Persona review engine not yet implemented")
