"""
LLM abstraction layer for AI File Organizer V2.

Provider hierarchy:
  OllamaClient (primary, local/remote)
  NIMClient    (fallback, OpenAI-compatible)

All structured outputs go through Pydantic validation.
Repeated schema violations degrade to NEVER confidence mode.
"""
from .base import LLMProvider
from .ollama_client import OllamaClient, AutoDetectOllama
from .nim_client import NIMClient
from .schemas import (
    ClassificationOutput,
    QueryOutput,
    AudioTranscriptionOutput,
    SummaryOutput,
)

__all__ = [
    "LLMProvider",
    "OllamaClient",
    "AutoDetectOllama",
    "NIMClient",
    "ClassificationOutput",
    "QueryOutput",
    "AudioTranscriptionOutput",
    "SummaryOutput",
]
