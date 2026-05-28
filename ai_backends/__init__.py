"""AI Backends – pluggable LLM adapters for persona reviews.

Supported backends:
- files_only: Deterministic pattern-based analysis (no AI, instant)
- ollama: Local LLM via Ollama API
- bedrock: AWS Bedrock (Claude models)
- gemini: Google Gemini Pro via API key

Usage:
    from ai_backends import get_backend, list_backends

    backend = get_backend("gemini")
    response = backend.generate(prompt, system_prompt="You are a Solution Architect")
"""

from ai_backends.base import AIBackend, AIResponse
from ai_backends.registry import get_backend, list_backends

__all__ = ["AIBackend", "AIResponse", "get_backend", "list_backends"]
