"""
TransformersAudioProvider — audio models via HuggingFace Transformers.
Supports Qwen2.5-Omni-7B (4-bit, CUDA) and similar audio-capable models.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
import librosa
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class TransformersAudioProvider:
    """Audio model served via HuggingFace Transformers (not GGUF/Ollama)."""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self.model = None
        self.processor = None

    def load(self) -> None:
        """Load model into VRAM. Call once before inference."""
        if self.model is not None:
            return

        import torch
        from transformers import BitsAndBytesConfig

        logger.info(f"Loading {self.model_id}...")
        start = time.time()

        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

        if "qwen" in self.model_id.lower() and "omni" in self.model_id.lower():
            from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
            self.model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
                self.model_id, torch_dtype=torch.bfloat16,
                device_map="auto", quantization_config=quant_config,
            )
            self.processor = Qwen2_5OmniProcessor.from_pretrained(self.model_id)
        else:
            from transformers import AutoModel, AutoProcessor
            self.model = AutoModel.from_pretrained(
                self.model_id, torch_dtype=torch.bfloat16,
                device_map="auto", quantization_config=quant_config,
                trust_remote_code=True,
            )
            self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)

        elapsed = time.time() - start
        logger.info(f"Loaded {self.model_id} on {self.model.device} in {elapsed:.0f}s")

    def listen(self, audio_path: Path, prompt: str, max_new_tokens: int = 256) -> str:
        """Process audio and return model response."""
        import torch

        if self.model is None:
            self.load()

        messages = [{"role": "user", "content": [
            {"type": "audio", "audio": str(audio_path)},
            {"type": "text", "text": prompt},
        ]}]

        text = self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        audio_arr, _ = librosa.load(str(audio_path), sr=16000, mono=True)
        inputs = self.processor(text=text, audio=[audio_arr], sampling_rate=16000, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            output = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, temperature=0.1)

        if isinstance(output, tuple):
            output_ids = output[0]
        else:
            output_ids = output

        generated_ids = output_ids[:, inputs["input_ids"].shape[1]:]
        return self.processor.decode(generated_ids[0], skip_special_tokens=True).strip()

    def unload(self) -> None:
        """Free VRAM."""
        import torch
        if self.model is not None:
            del self.model
            del self.processor
            torch.cuda.empty_cache()
            self.model = None
            self.processor = None
