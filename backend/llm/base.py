"""
Abstract LLM provider with structured output validation and bounded retry.

Key safety property: after max_retries consecutive schema-validation failures,
the provider degrades to NEVER confidence mode — it returns a safe default
rather than silently guessing.
"""
from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Type

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract interface for LLM backends (Ollama, NVIDIA NIM, etc.)."""

    def __init__(self, model: str, max_retries: int = 3):
        self.model = model
        self.max_retries = max_retries
        self._consecutive_failures = 0

    @abstractmethod
    def _generate_raw(self, prompt: str, **kwargs) -> str:
        """Send prompt to the backend, return raw text. Implemented by subclasses."""
        ...

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate raw text with retry on transient failures."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = self._generate_raw(prompt, **kwargs)
                self._consecutive_failures = 0
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"LLM attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff

        self._consecutive_failures += 1
        raise RuntimeError(f"LLM generation failed after {self.max_retries} attempts: {last_error}")

    def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        degrade_value: Any = None,
        **kwargs,
    ) -> tuple[Optional[BaseModel], bool]:
        """
        Generate text and validate against a Pydantic schema.

        Returns (instance, is_valid).
        On repeated schema violations, returns (degrade_value, False) 
        — the system degrades to NEVER confidence mode.
        """
        if self._consecutive_failures >= self.max_retries:
            logger.error(
                f"LLMProvider degraded: {self._consecutive_failures} consecutive "
                f"schema violations. Returning degrade_value={degrade_value}"
            )
            return degrade_value, False

        for attempt in range(self.max_retries):
            try:
                raw = self._generate_raw(prompt, **kwargs)
                # Try to parse JSON from the response
                data = self._extract_json(raw)
                instance = schema.model_validate(data)
                self._consecutive_failures = 0
                return instance, True
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(
                    f"Schema validation attempt {attempt + 1}/{self.max_retries} "
                    f"failed for {schema.__name__}: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        self._consecutive_failures += 1

        if self._consecutive_failures >= self.max_retries:
            logger.critical(
                f"LLMProvider permanently degraded after {self.max_retries} "
                f"consecutive schema violations. All future calls return degrade_value."
            )

        return degrade_value, False

    def reset_degradation(self) -> None:
        """Reset the degradation counter (called after a successful call)."""
        self._consecutive_failures = 0

    @property
    def is_degraded(self) -> bool:
        """True if the provider has degraded to safe mode."""
        return self._consecutive_failures >= self.max_retries

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract a JSON object from LLM output (handles markdown fences)."""
        text = text.strip()

        # Remove markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove opening fence
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # Find the outermost { } pair
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

        return json.loads(text)
