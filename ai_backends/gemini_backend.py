"""Google Gemini backend – Gemini Pro via API key.

Uses the google-genai SDK (official Google AI Python SDK).
Requires a GEMINI_API_KEY environment variable.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from ai_backends.base import AIBackend, AIResponse

# Gemini API endpoint
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiBackend(AIBackend):
    """Google Gemini Pro backend.

    Authentication: Set GEMINI_API_KEY environment variable with your API key.
    Model: gemini-2.0-flash by default (fast, capable). Can use gemini-1.5-pro for deeper analysis.

    Usage:
        export GEMINI_API_KEY="your-key-here"
        # Then select 'gemini' as ai_backend in reviews
    """

    def __init__(self, model: str = "gemini-2.0-flash", api_key: Optional[str] = None):
        self.model = model
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return f"Google Gemini ({self.model})"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Call Gemini generateContent API via REST.

        Uses the REST API directly to avoid hard dependency on google-genai SDK.
        """
        start = time.time()

        if not self._api_key:
            return AIResponse(
                text="",
                model=self.model,
                backend=self.name,
                error="GEMINI_API_KEY not set. Export it as an environment variable.",
                success=False,
            )

        try:
            url = (
                f"{GEMINI_API_BASE}/models/{self.model}:generateContent"
                f"?key={self._api_key}"
            )

            # Build request body
            contents = []

            # System instruction (Gemini supports it as a separate field)
            body_dict: dict = {
                "contents": [],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "topP": 0.95,
                },
            }

            if system_prompt:
                body_dict["systemInstruction"] = {
                    "parts": [{"text": system_prompt}]
                }

            body_dict["contents"].append({
                "parts": [{"text": prompt}]
            })

            data = json.dumps(body_dict).encode()
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())

            elapsed = (time.time() - start) * 1000

            # Parse response
            candidates = result.get("candidates", [])
            if not candidates:
                error_msg = result.get("error", {}).get("message", "No candidates returned")
                return AIResponse(
                    text="",
                    model=self.model,
                    backend=self.name,
                    latency_ms=round(elapsed, 1),
                    error=f"Gemini error: {error_msg}",
                    success=False,
                )

            # Extract text from first candidate
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

            # Token usage
            usage = result.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            output_tokens = usage.get("candidatesTokenCount", 0)
            total_tokens = usage.get("totalTokenCount", prompt_tokens + output_tokens)

            return AIResponse(
                text=text,
                model=self.model,
                backend=self.name,
                tokens_used=total_tokens,
                latency_ms=round(elapsed, 1),
                metadata={
                    "prompt_tokens": prompt_tokens,
                    "output_tokens": output_tokens,
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
                error=f"Gemini HTTP {e.code}: {error_body}",
                success=False,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            elapsed = (time.time() - start) * 1000
            return AIResponse(
                text="",
                model=self.model,
                backend=self.name,
                latency_ms=round(elapsed, 1),
                error=f"Gemini connection error: {e}",
                success=False,
            )

    def is_available(self) -> bool:
        """Check if API key is set."""
        return bool(self._api_key)
