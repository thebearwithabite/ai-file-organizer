"""VLLMClient — local vLLM (OpenAI-compatible) for director/vision calls (v1.2).

Replaces Ollama for director and vision calls: vLLM honours
``chat_template_kwargs.enable_thinking=false`` exactly, at 2-3s with zero
reasoning-token leakage (Ollama leaked 1-6k reasoning tokens per call, which
would silently blow the prompt compiler's token guard).
"""
from __future__ import annotations

import logging

from .base import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_VLLM_URL = "http://localhost:8000/v1"
VLLM_MODEL = "qwen3.5:4b"  # served id, not a path


class VLLMClient(LLMProvider):
    """OpenAI-compatible client for the local vLLM server (localhost:8000)."""

    def __init__(
        self,
        model: str = VLLM_MODEL,
        base_url: str = DEFAULT_VLLM_URL,
        max_retries: int = 3,
        timeout: int = 120,
    ):
        super().__init__(model=model, max_retries=max_retries)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _generate_raw(self, prompt: str, **kwargs) -> str:
        from openai import OpenAI

        client = OpenAI(
            base_url=self.base_url,
            api_key="not-needed",  # vLLM serves without auth
            timeout=self.timeout,
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 4096),
            # The whole point: vLLM honours this exactly, zero reasoning tokens.
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        return response.choices[0].message.content or ""

    def health_check(self) -> bool:
        try:
            from openai import OpenAI

            client = OpenAI(base_url=self.base_url, api_key="not-needed", timeout=5)
            client.models.list()
            return True
        except Exception:
            return False
