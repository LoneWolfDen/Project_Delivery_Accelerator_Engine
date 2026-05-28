"""Agent Input Standardisation – Uniform input format for all agents.

All agents/processors receive a standardised input:
{
    "project_id": "proj-001",
    "files": [...],
    "persona": "solution_architect",
    "scope": "...",
    "metadata": {...}
}

This ensures consistent contract across all intelligence operations.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class AgentInput:
    """Standardised input for all agent/processor operations.

    Every intelligence operation receives this uniform structure,
    ensuring consistent data contracts across the system.
    """

    project_id: str = ""
    files: List[Dict[str, Any]] = field(default_factory=list)
    persona: str = ""
    scope: str = ""
    ai_backend: str = "files_only"
    custom_prompt: str = ""

    # Context data
    intelligence: Dict[str, Any] = field(default_factory=dict)
    file_toggles: Dict[str, bool] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return asdict(self)

    @property
    def active_files(self) -> List[Dict[str, Any]]:
        """Get only active (included) files."""
        return [
            f for f in self.files
            if self.file_toggles.get(f.get("filename", ""), True)
        ]

    @property
    def excluded_files(self) -> List[Dict[str, Any]]:
        """Get excluded files."""
        return [
            f for f in self.files
            if not self.file_toggles.get(f.get("filename", ""), True)
        ]

    @property
    def active_file_count(self) -> int:
        """Count of active files."""
        return len(self.active_files)

    def validate(self) -> List[str]:
        """Validate the input meets minimum requirements.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: List[str] = []

        if not self.project_id:
            errors.append("project_id is required")

        if not self.files:
            errors.append("At least one file is required")

        if self.active_file_count == 0:
            errors.append("At least one active (included) file is required")

        return errors


def build_agent_input(
    project_id: str,
    files: List[Dict[str, Any]],
    persona: str = "",
    scope: str = "",
    ai_backend: str = "files_only",
    intelligence: Optional[Dict[str, Any]] = None,
    file_toggles: Optional[Dict[str, bool]] = None,
    custom_prompt: str = "",
    **kwargs: Any,
) -> AgentInput:
    """Factory function to build a standardised AgentInput.

    Args:
        project_id: Project identifier.
        files: List of file info dicts.
        persona: Persona to apply.
        scope: Project scope text.
        ai_backend: AI backend to use.
        intelligence: Pre-built intelligence (if available).
        file_toggles: File active/inactive states.
        custom_prompt: User-provided additional context.
        **kwargs: Additional metadata.

    Returns:
        Populated AgentInput instance.
    """
    return AgentInput(
        project_id=project_id,
        files=files,
        persona=persona,
        scope=scope,
        ai_backend=ai_backend,
        custom_prompt=custom_prompt,
        intelligence=intelligence or {},
        file_toggles=file_toggles or {},
        metadata=kwargs,
    )
