"""
OllamaClient — primary LLM backend via local/remote Ollama.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

from .base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaClient(LLMProvider):
    """
    Ollama HTTP client (local or remote).

    Usage:
        client = OllamaClient(model="gemma4:12b", base_url="http://192.168.1.100:11434")
        result, ok = client.generate_structured(prompt, ClassificationOutput)
    """

    def __init__(
        self,
        model: str = "qwen3:32b",
        base_url: str = "http://localhost:11434",
        max_retries: int = 3,
        timeout: int = 60,
    ):
        super().__init__(model=model, max_retries=max_retries)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _generate_raw(self, prompt: str, **kwargs) -> str:
        """Send prompt to Ollama /api/generate, return raw response text."""
        use_json_mode = kwargs.pop("json_mode", False)

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        if use_json_mode:
            payload["format"] = "json"

        # Additional Ollama options
        payload.update(kwargs)

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        result = response.json()

        return result.get("response", "")

    def health_check(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=10)
            r.raise_for_status()
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []

    def pull_model(self) -> bool:
        """Pull the configured model if not present."""
        models = self.list_models()
        if any(self.model in m or m in self.model for m in models):
            logger.info(f"Model '{self.model}' already present")
            return True

        logger.info(f"Pulling model '{self.model}'...")
        try:
            r = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model, "stream": False},
                timeout=600,
            )
            r.raise_for_status()
            logger.info(f"Model '{self.model}' pulled successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model '{self.model}': {e}")
            return False


class AutoDetectOllama(OllamaClient):
    """
    OllamaClient that auto-detects the remote 5090 box.
    Falls back to localhost if no remote found.
    """

    def __init__(
        self,
        model: str = "qwen3:32b",
        remote_ip: Optional[str] = None,
        remote_port: int = 11434,
        max_retries: int = 3,
    ):
        self.remote_ip = remote_ip
        self.remote_port = remote_port

        # Try remote first, fall back to local
        if remote_ip:
            base_url = f"http://{remote_ip}:{remote_port}"
        else:
            base_url = "http://localhost:11434"

        super().__init__(model=model, base_url=base_url, max_retries=max_retries)

    @classmethod
    def from_vision_config(cls, vision_analyzer, model: str = "qwen3:32b") -> "AutoDetectOllama":
        """
        Create from an existing VisionAnalyzer's remote config.
        """
        if vision_analyzer and getattr(vision_analyzer, "remote_enabled", False):
            ip = getattr(vision_analyzer, "remote_ip", "")
            port = getattr(vision_analyzer, "remote_ollama_port", 11434)
            return cls(model=model, remote_ip=ip, remote_port=port)
        return cls(model=model)
