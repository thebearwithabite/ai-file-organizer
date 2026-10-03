"""NIMClient — NVIDIA NIM cloud fallback/overflow client (OpenAI-compatible).

This is the fallback client named by the routing card. Directive v1.2 later
substituted DeepSeek as the *configured* fallback vendor; both implement the
same ``base.LLMProvider`` contract and the router treats them identically —
vendors are selectable, the local-first order is not.

Keyless construction refuses (``ValueError``): a half-configured cloud path
must fail loudly at build time, never mid-request. ``from_env`` reads
``NIM_API_KEY`` from the process environment only — never a repo file,
never logged, never pushed into a subprocess environment.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from .base import LLMProvider

logger = logging.getLogger(__name__)

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
# One constant — never inlined at call sites.
NIM_MODEL = "deepseek-ai/deepseek-v4-pro"


class NIMClient(LLMProvider):
    """NVIDIA NIM chat-completions client (the routing card's fallback vendor)."""

    def __init__(
        self,
        api_key: str,
        model: str = NIM_MODEL,
        base_url: str = NIM_BASE_URL,
        max_retries: int = 3,
        timeout: int = 120,
    ) -> None:
        super().__init__(model=model, max_retries=max_retries)
        if not api_key:
            raise ValueError(
                "NIMClient requires an API key (env NIM_API_KEY or explicit api_key)"
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_env(cls, env_var: str = "NIM_API_KEY", **kwargs) -> "NIMClient":
        """Build from the environment only; refuses when the key is absent."""
        key = os.environ.get(env_var)
        if not key:
            raise ValueError(
                f"{env_var} is not set — cloud fallback stays unavailable (local-only run)"
            )
        return cls(api_key=key, **kwargs)

    def _generate_raw(self, prompt: str, **kwargs) -> str:
        from openai import OpenAI

        client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        create_kwargs = dict(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        if kwargs.get("seed") is not None:
            create_kwargs["seed"] = kwargs["seed"]
        response = client.chat.completions.create(**create_kwargs)
        usage = getattr(response, "usage", None)
        if usage is not None:
            self._record_usage(
                getattr(usage, "prompt_tokens", None),
                getattr(usage, "completion_tokens", None),
            )
        return response.choices[0].message.content or ""

    def health_check(self) -> bool:
        try:
            from openai import OpenAI

            client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=5)
            client.models.list()
            return True
        except Exception:
            return False
