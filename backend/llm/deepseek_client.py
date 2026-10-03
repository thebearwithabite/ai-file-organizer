"""DeepSeekClient — cloud fallback LLM (PROMPT-MACHINE-DIRECTIVE v1.2).

Vendor substitution within the unchanged fallback slot (NIM retired).
Text-only: no pixels, no audio, no weights leave the box.

Confidentiality gate: scripts are unreleased creative IP and this repo also
indexes client contracts. The CALLER decides what content reaches this
client — the director service defaults to local-only for verbatim script
bodies and requires explicit per-project consent (``allow_cloud_script``).

Credentials: the key is fetched from GCP Secret Manager via
``secret_manager.get_secret("DEEPSEEK_API_KEY")`` and passed to the
constructor. It is never written to .env, never logged, and never placed on
``os.environ`` (so it cannot reach a subprocess environment).
"""
from __future__ import annotations

import logging

from .base import LLMProvider

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
# One constant — never inlined at call sites.
DEEPSEEK_MODEL = "deepseek-chat"


class DeepSeekClient(LLMProvider):
    """DeepSeek API client via OpenAI-compatible chat completions."""

    def __init__(
        self,
        api_key: str,
        model: str = DEEPSEEK_MODEL,
        base_url: str = DEEPSEEK_BASE_URL,
        max_retries: int = 3,
        timeout: int = 120,
    ):
        super().__init__(model=model, max_retries=max_retries)
        if not api_key:
            raise ValueError("DeepSeekClient requires an API key (secret_manager.get_secret)")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

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
            create_kwargs["seed"] = kwargs["seed"]  # pinned for reproducible shot books
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
