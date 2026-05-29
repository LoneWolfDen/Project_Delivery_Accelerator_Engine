"""Ollama backend – local LLM via Ollama API."""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from ai_backends.base import AIBackend, AIResponse

# Allow OLLAMA_HOST to override the default (useful for Docker Compose sidecar).
# Accepts either a bare host:port or a full URL.
_DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
if _DEFAULT_OLLAMA_URL and not _DEFAULT_OLLAMA_URL.startswith("http"):
    _DEFAULT_OLLAMA_URL = f"http://{_DEFAULT_OLLAMA_URL}"


class OllamaBackend(AIBackend):
    """Local Ollama LLM backend.

    Requires Ollama running on localhost:11434 (or OLLAMA_HOST env var).
    Default model: llama3.2 (configurable).
    """

    def __init__(self, model: str = "llama3.2", base_url: str = _DEFAULT_OLLAMA_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def display_name(self) -> str:
        return f"Ollama ({self.model})"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Call Ollama /api/generate endpoint."""
        start = time.time()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())

            elapsed = (time.time() - start) * 1000
            text = result.get("response", "")
            tokens = result.get("eval_count", None)

            return AIResponse(
                text=text,
                model=self.model,
                backend=self.name,
                tokens_used=tokens,
                latency_ms=round(elapsed, 1),
                success=True,
            )

        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError) as e:
            elapsed = (time.time() - start) * 1000
            return AIResponse(
                text="",
                model=self.model,
                backend=self.name,
                latency_ms=round(elapsed, 1),
                error=f"Ollama unavailable: {e}",
                success=False,
            )

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False
