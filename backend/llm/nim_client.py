"""
NIMClient — NVIDIA NIM fallback (OpenAI-compatible endpoint).

Used when Ollama is unavailable or for heavy jobs.
Implements the same interface so it's a drop-in replacement.
"""
from __future__ import annotations

import logging
from typing import Optional

from .base import LLMProvider

logger = logging.getLogger(__name__)


class NIMClient(LLMProvider):
    """
    NVIDIA NIM client via OpenAI-compatible API.

    Usage:
        client = NIMClient(
            model="qwen/qwen3-32b",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="nvapi-...",
        )
    """

    def __init__(
        self,
        model: str = "qwen/qwen3-32b",
        base_url: str = "https://integrate.api.nvidia.com/v1",
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        super().__init__(model=model, max_retries=max_retries)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _generate_raw(self, prompt: str, **kwargs) -> str:
        """Send prompt to NIM chat completions endpoint."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package required for NIMClient. Install: pip install openai"
            )

        client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "not-needed",  # NIM may not require key
            timeout=self.timeout,
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 1024),
        )

        return response.choices[0].message.content or ""

    def health_check(self) -> bool:
        """Check if NIM is reachable."""
        try:
            from openai import OpenAI
            client = OpenAI(base_url=self.base_url, api_key=self.api_key or "na", timeout=5)
            client.models.list()
            return True
        except Exception:
            return False
