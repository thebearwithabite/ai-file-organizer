"""
Listen Pass — multimodal audio classification via LLM provider.

Phase 1 bake-off: tries base64 audio in Ollama chat API first,
falls back to faster-whisper transcription + text classification.
"""
from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

from backend.audio.gate import analyze as gate_analyze, GateReport

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"


@dataclass
class ListenResult:
    """Output from a listen pass — one model's analysis of one file."""
    model: str = ""
    file_path: str = ""
    filename: str = ""

    # Classification
    primary_category: str = ""
    provenance: str = ""        # recorded | generated | licensed
    library_source: Optional[str] = None  # "epidemic_sound", "elevenlabs", etc.

    content_probs: dict = field(default_factory=dict)  # {"speech": 0.9, "music": 0.1}
    description: str = ""

    # Tags
    enhanced_tags: list[str] = field(default_factory=list)

    # Confidence
    confidence: float = 0.0
    needs_review: bool = True
    reasoning: str = ""

    # Performance
    method: str = "none"       # multimodal | text_fallback | control
    latency_seconds: float = 0.0
    success: bool = False
    error: str = ""


# ---------------------------------------------------------------------------
# Listen pass
# ---------------------------------------------------------------------------

def listen(
    audio_path: Path,
    model: str = "gemma4:12b",
    gate_report: Optional[GateReport] = None,
    timeout: int = 120,
) -> ListenResult:
    """
    Analyze an audio file using the specified model.

    Strategy:
      1. If model has vision/audio capability → send base64 audio
      2. Otherwise → transcribe with Whisper, classify the transcript
      3. Merge with gate report for timbre/tempo context
    """
    start = time.time()
    audio_path = Path(audio_path)

    result = ListenResult(
        model=model,
        file_path=str(audio_path),
        filename=audio_path.name,
    )

    # Run gate if not provided
    if gate_report is None:
        gate_report = gate_analyze(audio_path)

    # Build context from gate
    gate_context = _gate_to_context(gate_report)

    # Try multimodal first (only gemma4:12b has vision capability)
    if False:  # No model has audio capability in Ollama yet
        try:
            mm_result = _listen_multimodal(audio_path, model, gate_context, timeout)
            if mm_result:
                result.method = "multimodal"
                _merge_mm_result(result, mm_result, gate_report)
                result.latency_seconds = time.time() - start
                result.success = True
                return result
        except Exception as e:
            logger.warning(f"Multimodal listen failed for {model}: {e}")

    # Text fallback: transcribe → classify
    try:
        transcript = _transcribe(audio_path)
        if transcript:
            text_result = _classify_transcript(transcript, model, gate_context, timeout)
            if text_result:
                result.method = "text_fallback"
                _merge_mm_result(result, text_result, gate_report)
                result.latency_seconds = time.time() - start
                result.success = True
                return result
    except Exception as e:
        logger.warning(f"Text fallback failed for {model}: {e}")

    result.latency_seconds = time.time() - start
    result.success = False
    result.error = "All listen methods failed"
    result.needs_review = True
    return result


# ---------------------------------------------------------------------------
# Multimodal (base64 audio)
# ---------------------------------------------------------------------------

def _model_has_multimodal(model: str) -> bool:
    """Check if a model supports audio/vision input."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        for m in r.json().get("models", []):
            if model in m["name"]:
                caps = m.get("capabilities", [])
                return any(c in caps for c in ["vision", "audio"])
    except Exception:
        pass
    return False


def _listen_multimodal(
    audio_path: Path,
    model: str,
    gate_context: str,
    timeout: int,
) -> Optional[dict]:
    """Send raw audio to a multimodal model via Ollama chat API."""
    audio_bytes = audio_path.read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    prompt = f"""Listen to this audio file carefully and output ONLY valid JSON.

Gate analysis context:
{gate_context}

Task:
1. Determine the CONTENT TYPE: speech, music, sfx, or mixed
2. Guess PROVENANCE: "recorded" (live), "generated" (TTS/AI), or "licensed" (library)
3. Provide a detailed DESCRIPTION of what you hear (2-3 sentences)
4. Suggest TAGS: genre, mood, instruments, format, quality notes

Output STRICT JSON with these exact keys:
{{"primary_category": "Voice/Recorded", "provenance": "recorded", "content_probs": {{"speech": 0.9, "music": 0.05, "sfx": 0.05}}, "description": "...", "enhanced_tags": ["..."], "confidence": 0.85, "reasoning": "..."}}

Do not include markdown. Only the JSON object."""

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": prompt,
            "images": [audio_b64],
        }],
        "stream": False,
        "format": "json",
    }

    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=timeout,
    )
    r.raise_for_status()
    response = r.json()
    content = response.get("message", {}).get("content", "{}")
    return _extract_json(content)


# ---------------------------------------------------------------------------
# Text fallback (transcribe → classify)
# ---------------------------------------------------------------------------

def _transcribe(audio_path: Path) -> Optional[str]:
    """Transcribe audio with faster-whisper (local)."""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path))
        return " ".join(seg.text for seg in segments)
    except ImportError:
        logger.warning("faster-whisper not available")
        return None
    except Exception as e:
        logger.warning(f"Transcription error: {e}")
        return None


def _classify_transcript(
    transcript: str,
    model: str,
    gate_context: str,
    timeout: int,
) -> Optional[dict]:
    """Classify a transcript using an LLM (no audio needed)."""
    prompt = f"""Analyze this audio transcript and output ONLY valid JSON.

Gate analysis context:
{gate_context}

Transcript:
"{transcript[:1000]}"

Classify into: Voice/Recorded, Voice/Generated, Voice/Character, Music/Tracks, Music/Elements, SFX/UI, SFX/Environment, Field_Raw.
Guess provenance: recorded, generated, or licensed.
Output STRICT JSON: {{"primary_category": "...", "provenance": "...", "content_probs": {{"speech": 0.0, "music": 0.0, "sfx": 0.0}}, "description": "...", "enhanced_tags": [...], "confidence": 0.0, "reasoning": "..."}}"""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=payload,
        timeout=timeout,
    )
    r.raise_for_status()
    return _extract_json(r.json().get("response", "{}"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gate_to_context(g: GateReport) -> str:
    """Format gate report as context for the LLM prompt."""
    return (
        f"Duration: {g.duration_seconds:.1f}s, RMS: {g.rms_db:.0f}dB, "
        f"Centroid: {g.centroid_hz:.0f}Hz, BPM: {g.bpm:.0f}, "
        f"Harmonic: {g.harmonic_ratio:.2f}, Flatness: {g.flatness:.2f}, "
        f"Silence: {g.silence_fraction:.0%}, "
        f"Profiles: speech={g.has_speech_profile}, music={g.has_music_profile}, sfx={g.has_sfx_profile}"
    )


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def _merge_mm_result(
    result: ListenResult,
    parsed: dict,
    gate: GateReport,
) -> None:
    """Merge parsed LLM output into a ListenResult."""
    result.primary_category = parsed.get("primary_category", "")
    result.provenance = parsed.get("provenance", "")
    result.content_probs = parsed.get("content_probs", {})
    result.description = parsed.get("description", "")
    result.enhanced_tags = parsed.get("enhanced_tags", [])
    result.confidence = float(parsed.get("confidence", 0.5))
    result.reasoning = parsed.get("reasoning", "")
    result.needs_review = result.confidence < 0.6
