"""Base class for AI backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AIResponse:
    """Standardised response from any AI backend."""

    text: str
    model: str
    backend: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "backend": self.backend,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
            "error": self.error,
            "success": self.success,
        }


class AIBackend(ABC):
    """Abstract base class for AI backends.

    All backends must implement `generate()` which takes a prompt
    and returns an AIResponse.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend identifier (e.g. 'gemini', 'ollama')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name."""
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Generate a response from the AI model.

        Args:
            prompt: The user/analysis prompt.
            system_prompt: Optional system-level instructions.
            temperature: Creativity control (0.0-1.0).
            max_tokens: Maximum tokens in response.

        Returns:
            AIResponse with the generated text or error info.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is configured and reachable.

        Returns:
            True if the backend can accept requests right now.
        """
        ...

    def get_info(self) -> Dict[str, Any]:
        """Return metadata about this backend."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "available": self.is_available(),
        }
