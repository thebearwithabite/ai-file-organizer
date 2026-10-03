"""Typed LLM routing errors (PROMPT-MACHINE-DIRECTIVE v1.2, intelligence routing layer).

Deliberately distinct exception types so callers react correctly:

* ``DegradedRoutingError`` — no usable route: local inference was busy (render
  in flight) or unreachable, AND no cloud fallback was configured. The message
  explains both causes and the actionable fix; the request failed fast.
* ``InvalidLLMOutputError`` — a provider answered, but the output did not
  validate against the requested schema even after the single repair retry.
  Carries provider name, raw output, and the structured validation errors so
  the director can enqueue a precise degrade record.

Both derive from ``LLMRoutingError`` so one ``except`` can catch the family.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class LLMRoutingError(RuntimeError):
    """Base class for routing-layer failures."""


class DegradedRoutingError(LLMRoutingError):
    """No route could serve the request; both causes are explained in the message."""

    def __init__(
        self,
        message: str,
        *,
        job: str = "",
        local_reason: str = "",
        cloud_reason: str = "",
    ) -> None:
        super().__init__(message)
        self.job = job
        self.local_reason = local_reason
        self.cloud_reason = cloud_reason


class InvalidLLMOutputError(LLMRoutingError):
    """Output failed schema validation after the single repair retry."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        model: str = "",
        raw: str = "",
        errors: Optional[List[Dict[str, Any]]] = None,
        attempts: int = 0,
        job: str = "",
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.raw = raw
        self.errors = list(errors or [])
        self.attempts = attempts
        self.job = job
