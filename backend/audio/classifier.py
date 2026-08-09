"""
Phase 2.2 — Audio Classifier: fuse gate + listen + prior.

Three signals, one output. Disagreement → review queue. Corrections → learnings.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.audio.gate import analyze as gate_analyze, GateReport
from backend.audio.taxonomy_seed import detect_license_prefix, detect_generated_prefix
from backend.context import ContextStore, CorrectionEvent
from backend.audio.review_queue import ReviewQueue

# Filename keyword → content type hints (not verdicts, just weights)
FILENAME_HINTS = {
    "sfx": ["button", "click", "impact", "whoosh", "riser", "glitch", "beep", "ui", "sfx", "fx", "transition", "braam"],
    "music": ["piano", "dark", "track", "song", "loop", "stem", "bass", "drum", "melody", "chord", "element", "motif", "stinger"],
    "voice": ["voice", "speech", "talk", "interview", "memo", "narration", "dialogue", "vo", "vox", "elevenlabs", "tts", "clone", "character"],
    "ambient": ["ambient", "atmosphere", "drone", "pad", "room", "field", "nature", "wind", "rain", "environment"],
}


def _filename_signal(filename: str) -> dict:
    """Extract content-type hints from filename. Returns confidence weights 0-1."""
    lower = filename.lower()
    signals = {"sfx": 0.0, "music": 0.0, "voice": 0.0, "ambient": 0.0}
    for category, keywords in FILENAME_HINTS.items():
        matches = sum(1 for kw in keywords if kw in lower)
        if matches:
            signals[category] = min(matches * 0.3, 0.9)
    return signals


# ---------------------------------------------------------------------------
# Classification output schema
# ---------------------------------------------------------------------------

@dataclass
class AudioClassification:
    """Full audio classification output — matches directive schema."""
    file_path: str = ""
    filename: str = ""

    # Primary
    primary_category: str = ""          # e.g. "Audio/Voice/Generated"
    provenance: str = ""                # recorded | generated | licensed
    library_source: Optional[str] = None  # "epidemic_sound", "elevenlabs", etc.

    # Content
    content_probs: dict = field(default_factory=lambda: {"speech": 0.0, "music": 0.0, "sfx": 0.0})
    description: str = ""

    # Timbre (from gate)
    timbre: dict = field(default_factory=dict)

    # Tags
    enhanced_tags: list[str] = field(default_factory=list)

    # Links (Phase 4)
    character_match: Optional[dict] = None
    project_match: Optional[dict] = None

    # Confidence
    confidence: float = 0.0
    needs_review: bool = True
    reasoning: str = ""

    # Method
    tier: str = "none"           # provisional | authoritative | human
    latency_seconds: float = 0.0

    # License guard
    is_licensed: bool = False
    rename_locked: bool = False
    suggested_filename: str = ""


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class AudioClassifier:
    """
    Fuses gate + listen + prior into a classification.

    Phase 2.2 two-tier architecture:
      1. Provisional: gate + conditional Whisper + text model → fast
      2. Authoritative: Qwen2.5-Omni batch → confirms or corrects
      3. Disagreement: → review queue → learnings
    """

    CONFIDENCE_MODES = ("NEVER", "SMART", "ALWAYS")

    def __init__(self, confidence_mode: str = "SMART", daily_cap: int = 20, db_path=None):
        if confidence_mode not in self.CONFIDENCE_MODES:
            raise ValueError(f"confidence_mode must be one of {self.CONFIDENCE_MODES}")
        self.confidence_mode = confidence_mode
        self._db_path = db_path
        self._context_store: Optional[ContextStore] = None
        self._listener = None
        self._review_queue: Optional[ReviewQueue] = None

    @property
    def review_queue(self) -> ReviewQueue:
        if self._review_queue is None:
            self._review_queue = ReviewQueue(daily_cap=20, db_path=self._db_path)
        return self._review_queue

    def _can_auto_file(self, confidence: float) -> bool:
        """Decide if a classification can auto-file under the current mode."""
        if self.confidence_mode == "NEVER":
            return False
        if self.confidence_mode == "ALWAYS":
            return True
        # SMART: auto-file only with strong agreement + no red flags
        return confidence >= 0.7

    def _route_to_review(self, result: AudioClassification, reason: str, batch_group: str = "general") -> None:
        """Route a classification to the review queue."""
        result.needs_review = True
        result._review_routed = True
        self.review_queue.enqueue(
            file_path=result.file_path,
            reason=reason,
            category_hint=result.primary_category,
            batch_group=batch_group,
        )

    def _ensure_queued(self, result: AudioClassification, fallback_reason: str) -> None:
        """Final guarantee: any needs_review result must be in the queue."""
        if result.needs_review and not getattr(result, "_review_routed", False):
            self._route_to_review(result, fallback_reason, batch_group="general")

    @property
    def context_store(self) -> ContextStore:
        if self._context_store is None:
            self._context_store = ContextStore(db_path=self._db_path) if self._db_path else ContextStore()
        return self._context_store

    # ------------------------------------------------------------------
    # Provisional pass (fast — gate + text model)
    # ------------------------------------------------------------------

    def classify_provisional(self, audio_path: Path) -> AudioClassification:
        """
        Fast classification: gate + prior only. No LLM call.
        Safe to run on every file immediately.
        Result is provisional — never triggers permanent file ops.
        """
        start = time.time()
        path = Path(audio_path)

        result = AudioClassification(
            file_path=str(path),
            filename=path.name,
            tier="provisional",
        )

        # --- Gate ---
        gate = gate_analyze(path)
        result.timbre = {
            "centroid_hz": gate.centroid_hz,
            "darkness": round(1.0 - min(gate.centroid_hz / 5000.0, 1.0), 2),
            "energy": f"E{min(int(gate.rms_linear * 100), 10)}",
            "rms_db": round(gate.rms_db, 1),
        }

        # --- Prior (filename) ---
        license_prefix = detect_license_prefix(path.name)
        is_generated = detect_generated_prefix(path.name)

        if license_prefix:
            result.provenance = "licensed"
            result.library_source = license_prefix
            result.is_licensed = True
            result.rename_locked = True
        elif is_generated:
            result.provenance = "generated"

        # --- Route based on gate ---
        if gate.has_speech_profile:
            result.content_probs["speech"] = 0.8
            if result.provenance == "generated":
                result.primary_category = "Audio/Voice/Generated"
                result.enhanced_tags.append("tts")
            elif result.provenance == "licensed":
                result.primary_category = "Audio/Voice/Recorded"
            else:
                result.primary_category = "Audio/Voice/Recorded"

            # Sub-3s handling: speech needs review, SFX/music with signal confidence doesn't
            if gate.duration_seconds < 3.0:
                filename_sig = _filename_signal(path.name)
                # High-confidence SFX/music from filename → auto-file
                if filename_sig.get("sfx", 0) > 0.5 or filename_sig.get("music", 0) > 0.5:
                    result.needs_review = False
                    result.enhanced_tags.append("filename-confirmed")
                # Licensed files → auto-file (ES_ is pre-classified)
                elif result.is_licensed:
                    result.needs_review = False
                # Otherwise: speech-like short clip → review
                else:
                    result.needs_review = True
                    result.reasoning = "Short clip (<3s) — tag only, no auto-file."
                    self._route_to_review(result, "Sub-3s speech clip", "sub3s-speech")

        elif gate.has_music_profile:
            result.content_probs["music"] = 0.8
            result.primary_category = "Audio/Music/Elements"
            if gate.centroid_hz < 500:
                result.enhanced_tags.extend(["dark", "low"])
# Prior override: generated/speech filenames trump SFX detection
        elif gate.has_sfx_profile and (is_generated or "voice" in path.name.lower() or "eleven" in path.name.lower()):
            result.content_probs["speech"] = 0.6
            result.primary_category = "Audio/Voice/Generated" if is_generated else "Audio/Voice/Recorded"
        elif gate.has_sfx_profile:
            result.content_probs["sfx"] = 0.8
            result.primary_category = "Audio/SFX/UI_Digital" if gate.duration_seconds < 2.0 else "Audio/SFX/Design"
        else:
            # Can't determine — needs review
            result.primary_category = "Audio/Field_Raw"
            result.needs_review = True

        # --- Anomalies ---
        if gate.is_near_silent:
            result.needs_review = True
            result.reasoning = "Near-silent file — requires listen pass to determine if usable."
            self._route_to_review(result, "Near-silent file", "anomaly")
        if gate.anomaly_flags:
            result.enhanced_tags.append("anomaly")
            self._route_to_review(result, f"Gate anomaly: {gate.anomaly_flags}", "anomaly")

        result.confidence = 0.5  # provisional = uncertain by design
        result.latency_seconds = time.time() - start

        # Final guarantee: needs_review => queued
        if result.needs_review:
            self._ensure_queued(result, "Provisional classification unresolved")

        return result

    # ------------------------------------------------------------------
    # Authoritative pass (batch — Qwen2.5-Omni or equivalent)
    # ------------------------------------------------------------------

    def classify_authoritative(
        self,
        audio_path: Path,
        provisional: Optional[AudioClassification] = None,
    ) -> AudioClassification:
        """
        Full listen pass. Upgrade provisional → confirmed, or correct it.
        Uses the audio-capable model (Qwen2.5-Omni) when available,
        falls back to text path.
        """
        start = time.time()
        path = Path(audio_path)

        # Start from provisional if available, otherwise fresh gate
        if provisional is None:
            result = self.classify_provisional(path)
        else:
            result = provisional

        result.tier = "authoritative"

        # Try listen pass
        try:
            listen_result = self._do_listen(path)
            if listen_result:
                # Merge listen findings
                if listen_result.get("primary_category"):
                    result.primary_category = listen_result["primary_category"]
                if listen_result.get("provenance"):
                    # Prior beats listen for licensed files
                    if not result.is_licensed:
                        result.provenance = listen_result["provenance"]
                if listen_result.get("description"):
                    result.description = listen_result["description"]
                if listen_result.get("enhanced_tags"):
                    result.enhanced_tags.extend(listen_result["enhanced_tags"])
                if listen_result.get("confidence", 0) > result.confidence:
                    result.confidence = listen_result["confidence"]
                if listen_result.get("reasoning"):
                    result.reasoning = listen_result["reasoning"]
        except Exception as e:
            result.reasoning = f"Listen pass failed: {e}"
            result.needs_review = True

        # --- Resolve ---
        if result.confidence < 0.5:
            result.needs_review = True
            self._route_to_review(result, "Low confidence", "low-confidence")
        if result.provenance == "generated" and result.primary_category == "Audio/Voice/Recorded":
            # Disagreement: prior says generated, category says recorded → review
            result.needs_review = True
            result.reasoning = "Provenance-category mismatch — needs human review."
            self._route_to_review(result, "Provenance-category mismatch", "disagreement")

        # Confidence mode enforcement
        if not result.needs_review and not self._can_auto_file(result.confidence):
            result.needs_review = True
            result.reasoning = f"Confidence {result.confidence:.2f} below auto-file threshold for mode {self.confidence_mode}."
            self._route_to_review(result, f"Below {self.confidence_mode} threshold", "low-confidence")

        result.latency_seconds = time.time() - start
        return result

    # ------------------------------------------------------------------
    # Correction (closes learning loop)
    # ------------------------------------------------------------------

    def record_correction(
        self,
        file_path: str,
        predicted: str,
        corrected: str,
        confidence: float = 0.0,
        source: str = "ui",
    ) -> int:
        """Record a human correction → learnings table."""
        event = CorrectionEvent(
            file_path=file_path,
            predicted_category=predicted,
            corrected_category=corrected,
            confidence=confidence,
            source=source,
        )
        return self.context_store.record_correction(event)

    def get_learnings_for_file(self, filename: str, top_k: int = 3) -> list[dict]:
        """Get relevant learnings for context assembly."""
        ctx = self.context_store.assemble_context(filename, "", top_k=top_k)
        return ctx.get("learnings", [])

    # ------------------------------------------------------------------
    # Internal: listen pass
    # ------------------------------------------------------------------

    def _do_listen(self, audio_path: Path) -> Optional[dict]:
        """
        Attempt a listen pass. Tries:
          1. Qwen2.5-Omni (Transformers) if loaded
          2. gemma4:12b (Ollama) text fallback
        Returns parsed dict or None.
        """
        # Try Transformers provider first
        try:
            from backend.audio.tf_provider import TransformersAudioProvider
            provider = TransformersAudioProvider("Qwen/Qwen2.5-Omni-7B")

            prompt = """Listen to this audio and output ONLY valid JSON:
{
  "primary_category": "Audio/Voice/Recorded",
  "provenance": "recorded",
  "description": "detailed 1-2 sentence description",
  "content_type": "speech",
  "enhanced_tags": [],
  "confidence": 0.5,
  "reasoning": "brief explanation"
}"""

            response = provider.listen(audio_path, prompt, max_new_tokens=128)
            import json
            return json.loads(response)
        except Exception:
            pass

        # Fallback: Ollama text path
        try:
            from backend.audio.listener import listen as ollama_listen
            result = ollama_listen(audio_path, model="gemma4:12b")
            if result.success:
                return {
                    "primary_category": result.primary_category,
                    "provenance": result.provenance,
                    "description": result.description,
                    "enhanced_tags": result.enhanced_tags,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                }
        except Exception:
            pass

        return None
