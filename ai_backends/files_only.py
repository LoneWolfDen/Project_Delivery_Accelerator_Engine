"""Files-only backend – no AI, returns empty response for structured analysis.

This backend signals to the persona engine to use its built-in
heuristic/pattern-based analysis instead of calling an LLM.
"""

from typing import Optional

from ai_backends.base import AIBackend, AIResponse


class FilesOnlyBackend(AIBackend):
    """Deterministic analysis mode – no external AI calls."""

    @property
    def name(self) -> str:
        return "files_only"

    @property
    def display_name(self) -> str:
        return "Files Only (No AI)"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Returns a marker response indicating files-only mode."""
        return AIResponse(
            text="",
            model="none",
            backend=self.name,
            tokens_used=0,
            metadata={"mode": "heuristic_analysis"},
            success=True,
        )

    def is_available(self) -> bool:
        """Always available – no dependencies."""
        return True
