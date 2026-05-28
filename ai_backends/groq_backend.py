"""Groq backend – blazing fast inference via Groq Cloud (free tier available).

Uses the OpenAI-compatible chat completions API.
Requires a GROQ_API_KEY environment variable.
Get your free key at: https://console.groq.com
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from ai_backends.base import AIBackend, AIResponse

GROQ_API_BASE = "https://api.groq.com/openai/v1"


class GroqBackend(AIBackend):
    """Groq Cloud backend – free tier with Llama models.

    Features:
    - Free tier: no credit card required
    - Extremely fast inference (custom LPU hardware)
    - Models: llama-3.3-70b-versatile (default), llama-3.1-8b-instant, etc.

    Setup:
        1. Sign up at https://console.groq.com (free)
        2. Create an API key
        3. export GROQ_API_KEY="gsk_..."
    """

    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
    ):
        self.model = model
        self._api_key = api_key or os.environ.get("GROQ_API_KEY", "")

    @property
    def name(self) -> str:
        return "groq"

    @property
    def display_name(self) -> str:
        return f"Groq ({self.model})"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Call Groq /v1/chat/completions endpoint."""
        start = time.time()

        if not self._api_key:
            return AIResponse(
                text="",
                model=self.model,
                backend=self.name,
                error="GROQ_API_KEY not set. Get a free key at https://console.groq.com",
                success=False,
            )

        try:
            url = f"{GROQ_API_BASE}/chat/completions"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            body = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            data = json.dumps(body).encode()
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                    "User-Agent": "ProjectDeliveryAccelerator/2.0",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())

            elapsed = (time.time() - start) * 1000

            # Parse response
            choices = result.get("choices", [])
            if not choices:
                return AIResponse(
                    text="",
                    model=self.model,
                    backend=self.name,
                    latency_ms=round(elapsed, 1),
                    error="No choices returned from Groq",
                    success=False,
                )

            text = choices[0].get("message", {}).get("content", "")

            # Token usage
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            return AIResponse(
                text=text,
                model=result.get("model", self.model),
                backend=self.name,
                tokens_used=total_tokens,
                latency_ms=round(elapsed, 1),
                metadata={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "groq_id": result.get("id", ""),
                },
                success=True,
            )

        except urllib.error.HTTPError as e:
            elapsed = (time.time() - start) * 1000
            error_body = ""
            try:
                error_body = e.read().decode()[:500]
            except Exception:
                pass
            return AIResponse(
                text="",
                model=self.model,
                backend=self.name,
                latency_ms=round(elapsed, 1),
                error=f"Groq HTTP {e.code}: {error_body}",
                success=False,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            elapsed = (time.time() - start) * 1000
            return AIResponse(
                text="",
                model=self.model,
                backend=self.name,
                latency_ms=round(elapsed, 1),
                error=f"Groq connection error: {e}",
                success=False,
            )

    def is_available(self) -> bool:
        """Check if API key is set."""
        return bool(self._api_key)
