"""OpenRouter backend – access 300+ models including free ones.

Uses the OpenAI-compatible chat completions API.
Requires an OPENROUTER_API_KEY environment variable.
Get your free key at: https://openrouter.ai

Free models available (no credit card needed):
- meta-llama/llama-3.1-8b-instruct:free
- deepseek/deepseek-chat-v3-0324:free
- qwen/qwen3-8b:free
- google/gemma-3-4b-it:free
- openrouter/free (auto-routes to best available free model)
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from ai_backends.base import AIBackend, AIResponse

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"


class OpenRouterBackend(AIBackend):
    """OpenRouter backend – free tier with many model options.

    Features:
    - Free tier available (no credit card)
    - 300+ models accessible via single API
    - Default uses free model router (auto-picks best free model)

    Setup:
        1. Sign up at https://openrouter.ai (free)
        2. Create an API key
        3. export OPENROUTER_API_KEY="sk-or-..."
    """

    def __init__(
        self,
        model: str = "openrouter/free",
        api_key: Optional[str] = None,
    ):
        self.model = model
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def display_name(self) -> str:
        model_short = self.model.split("/")[-1] if "/" in self.model else self.model
        return f"OpenRouter ({model_short})"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Call OpenRouter /v1/chat/completions endpoint."""
        start = time.time()

        if not self._api_key:
            return AIResponse(
                text="",
                model=self.model,
                backend=self.name,
                error="OPENROUTER_API_KEY not set. Get a free key at https://openrouter.ai",
                success=False,
            )

        try:
            url = f"{OPENROUTER_API_BASE}/chat/completions"

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
                    "HTTP-Referer": "https://github.com/LoneWolfDen/Project_Delivery_Accelerator_Engine",
                    "X-Title": "Project Delivery Accelerator",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())

            elapsed = (time.time() - start) * 1000

            # Parse response
            choices = result.get("choices", [])
            if not choices:
                error_msg = result.get("error", {}).get("message", "No choices returned")
                return AIResponse(
                    text="",
                    model=self.model,
                    backend=self.name,
                    latency_ms=round(elapsed, 1),
                    error=f"OpenRouter error: {error_msg}",
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
                    "openrouter_id": result.get("id", ""),
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
                error=f"OpenRouter HTTP {e.code}: {error_body}",
                success=False,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            elapsed = (time.time() - start) * 1000
            return AIResponse(
                text="",
                model=self.model,
                backend=self.name,
                latency_ms=round(elapsed, 1),
                error=f"OpenRouter connection error: {e}",
                success=False,
            )

    def is_available(self) -> bool:
        """Check if API key is set."""
        return bool(self._api_key)
