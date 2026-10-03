"""
LLM abstraction layer for AI File Organizer V2.

Provider hierarchy:
  OllamaClient (primary — classification, audio, director & vision paths;
                qwen3.5:4b with think=False; vLLM retired 2026-08-15)
  DeepSeekClient (cloud fallback, retired NIM slot)

All structured outputs go through Pydantic validation.
Repeated schema violations degrade to NEVER confidence mode.
"""
from .base import LLMProvider, TokenUsage
from .errors import DegradedRoutingError, InvalidLLMOutputError, LLMRoutingError
from .ollama_client import OllamaClient, AutoDetectOllama
from .deepseek_client import DeepSeekClient
from .nim_client import NIMClient
from .structured_output import (
    StructuredAttempt,
    StructuredResult,
    enforce_structured,
    enforce_structured_with_client,
)
from .schemas import (
    ClassificationOutput,
    QueryOutput,
    AudioTranscriptionOutput,
    SummaryOutput,
)

__all__ = [
    "LLMProvider",
    "TokenUsage",
    "OllamaClient",
    "AutoDetectOllama",
    "DeepSeekClient",
    "NIMClient",
    "LLMRoutingError",
    "DegradedRoutingError",
    "InvalidLLMOutputError",
    "StructuredAttempt",
    "StructuredResult",
    "enforce_structured",
    "enforce_structured_with_client",
    "ClassificationOutput",
    "QueryOutput",
    "AudioTranscriptionOutput",
    "SummaryOutput",
]
