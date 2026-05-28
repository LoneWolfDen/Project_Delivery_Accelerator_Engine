"""AWS Bedrock backend – Claude models via AWS SDK."""

import json
import time
from typing import Optional

from ai_backends.base import AIBackend, AIResponse


class BedrockBackend(AIBackend):
    """AWS Bedrock backend using Claude models.

    Requires:
    - boto3 installed (pip install project-delivery-accelerator[ai])
    - Valid AWS credentials configured (env vars, profile, or IAM role)

    Default model: Claude 3 Haiku (fast, cost-effective).
    """

    def __init__(self, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0", region: str = "us-east-1"):
        self.model_id = model_id
        self.region = region

    @property
    def name(self) -> str:
        return "bedrock"

    @property
    def display_name(self) -> str:
        model_short = self.model_id.split("/")[-1].split("-")[0:3]
        return f"AWS Bedrock ({'-'.join(model_short)})"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Call Bedrock InvokeModel API."""
        start = time.time()

        try:
            import boto3
        except ImportError:
            return AIResponse(
                text="",
                model=self.model_id,
                backend=self.name,
                error="boto3 not installed. Run: pip install project-delivery-accelerator[ai]",
                success=False,
            )

        try:
            client = boto3.client("bedrock-runtime", region_name=self.region)

            messages = [{"role": "user", "content": prompt}]
            body_dict = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
            if system_prompt:
                body_dict["system"] = system_prompt

            response = client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body_dict),
            )
            result = json.loads(response["body"].read())
            text = result.get("content", [{}])[0].get("text", "")
            input_tokens = result.get("usage", {}).get("input_tokens", 0)
            output_tokens = result.get("usage", {}).get("output_tokens", 0)

            elapsed = (time.time() - start) * 1000

            return AIResponse(
                text=text,
                model=self.model_id,
                backend=self.name,
                tokens_used=input_tokens + output_tokens,
                latency_ms=round(elapsed, 1),
                metadata={"input_tokens": input_tokens, "output_tokens": output_tokens},
                success=True,
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return AIResponse(
                text="",
                model=self.model_id,
                backend=self.name,
                latency_ms=round(elapsed, 1),
                error=f"Bedrock error: {e}",
                success=False,
            )

    def is_available(self) -> bool:
        """Check if AWS credentials are configured."""
        try:
            import boto3
            session = boto3.Session()
            credentials = session.get_credentials()
            return credentials is not None
        except Exception:
            return False
