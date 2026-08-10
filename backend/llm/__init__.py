"""
LLM abstraction layer for AI File Organizer V2.

Provider hierarchy:
  OllamaClient (primary, local/remote — classification & audio paths)
  VLLMClient   (director/vision calls, localhost:8000 — enable_thinking=false)
  DeepSeekClient (cloud fallback, retired NIM slot)

All structured outputs go through Pydantic validation.
Repeated schema violations degrade to NEVER confidence mode.
"""
from .base import LLMProvider
from .ollama_client import OllamaClient, AutoDetectOllama
from .vllm_client import VLLMClient
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
    "VLLMClient",
    "DeepSeekClient",
    "ClassificationOutput",
    "QueryOutput",
    "AudioTranscriptionOutput",
    "SummaryOutput",
]
