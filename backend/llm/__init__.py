"""
LLM abstraction layer for AI File Organizer V2.

Provider hierarchy:
  OllamaClient (primary — classification, audio, director & vision paths;
                qwen3.5:4b with think=False; vLLM retired 2026-08-15)
  DeepSeekClient (cloud fallback, retired NIM slot)

All structured outputs go through Pydantic validation.
Repeated schema violations degrade to NEVER confidence mode.
"""
from .base import LLMProvider
from .ollama_client import OllamaClient, AutoDetectOllama
from .deepseek_client import DeepSeekClient
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
    "DeepSeekClient",
    "ClassificationOutput",
    "QueryOutput",
    "AudioTranscriptionOutput",
    "SummaryOutput",
]
