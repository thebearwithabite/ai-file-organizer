"""Shared LLM provider resolution for Prompt Machine services (v1.2, Phase 2).

Extracted from DirectorService (Phase 1) so AssetService uses the identical
chain instead of duplicating it:

    Ollama (qwen3.5:4b, think:false)  →  DeepSeek (key + consent only)

Local-first (vLLM retired 2026-08-15 — Ollama serves the same model at a
third of the VRAM). The cloud fallback is reachable ONLY when a DEEPSEEK_API_KEY
exists in GCP Secret Manager AND the caller explicitly allows script content
to leave the box (``allow_cloud_script=True``).

``enqueue_llm_degrade`` is the shared parent-2.1 degrade path: a failed
schema pass lands in the review queue (batch_group='director-degrade') — the
system waits, it never floods and never silently guesses.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Optional, Tuple

from backend.llm import LLMProvider
from backend.llm.ollama_client import OllamaClient
from backend.llm.deepseek_client import DeepSeekClient
from backend.audio.review_queue import ReviewQueue

logger = logging.getLogger(__name__)

DIRECTOR_LOCAL_FALLBACK_MODEL = "qwen3.5:4b"  # local director/vision model (vLLM retired)
SHOT_LIST_MAX_TOKENS = 6000

# Pinned for reproducible shot books: the same script must produce the same
# shot list on re-run. Variance belongs in explicit regen calls, not in the
# baseline pass (directive amendment 2026-08-10).
DIRECTOR_SEED = 20260810


class DegradeReason(str, Enum):
    """Review-queue classification — 'service down' vs 'bad model output' must
    not look identical (a silent vLLM outage presented as 'schema failure'
    twice before this existed)."""
    provider_unreachable = "provider_unreachable"
    schema_invalid = "schema_invalid"
    token_limit = "token_limit"
    consent_denied = "consent_denied"


def resolve_provider(
    allow_cloud_script: bool = False,
    injected: Optional[LLMProvider] = None,
) -> Tuple[Optional[LLMProvider], str]:
    """Resolve the LLM provider chain. Returns (provider, name) or (None, 'none')."""
    if injected is not None:
        return injected, "injected"

    ollama = OllamaClient(model=DIRECTOR_LOCAL_FALLBACK_MODEL)
    if ollama.health_check():
        return ollama, "ollama"

    if allow_cloud_script:
        from secret_manager import get_secret

        key = get_secret("DEEPSEEK_API_KEY")
        if key:
            return DeepSeekClient(api_key=key), "deepseek"

    return None, "none"


def provider_kwargs(provider_name: str, max_tokens: int = SHOT_LIST_MAX_TOKENS) -> dict:
    """Per-provider generation kwargs. DeepSeek speaks max_tokens; Ollama
    speaks num_predict. Temperature and seed are pinned for reproducibility;
    Ollama gets think=False so reasoning tokens never leak (the vLLM-era
    guarantee, preserved)."""
    if provider_name == "deepseek":
        return {"max_tokens": max_tokens, "temperature": 0.1, "seed": DIRECTOR_SEED}
    return {"num_predict": max_tokens, "temperature": 0.1, "seed": DIRECTOR_SEED, "think": False}


def enqueue_llm_degrade(
    script: str,
    project_id: str,
    reason: str,
    degrade_reason: str = DegradeReason.schema_invalid.value,
) -> None:
    """Push a failed LLM pass into the review queue (daily cap enforced)."""
    try:
        pseudo_path = f"script:{project_id or 'untitled'}:{abs(hash(script)) % 100000}"
        ReviewQueue().enqueue(
            file_path=pseudo_path,
            reason=f"llm failed: {reason}",
            category_hint="prompt_machine",
            batch_group="director-degrade",
            degrade_reason=degrade_reason,
        )
        logger.warning(
            "LLM degrade enqueued: %s [%s]", pseudo_path, degrade_reason
        )
    except Exception as e:  # never let the degrade path take the API down
        logger.error("Review queue enqueue failed: %s", e)
