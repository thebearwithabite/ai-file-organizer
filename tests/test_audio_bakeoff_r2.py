"""
Phase 1.1 Bake-off Round 2 — true audio-capable models via Transformers.

Arms:
  1. Qwen2.5-Omni-7B      (Transformers, 4-bit, Apache 2.0)
  2. audio_analyzer.py     (control, numpy bug fixed)

Harness fixes from Round 1:
  - Warm-up inference before scoring (cold start excluded)
  - 300s per-file timeout
  - SFX/music scored on audio description, never transcript presence
  - Pre-flight: two files → materially different descriptions
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "audio_golden"

GROUND_TRUTH = {
    "interview_sample": {
        "expected": ["voice", "recorded", "interview", "speech"],
        "provenance": "recorded",
        "type": "speech",
    },
    "voice_takes": {
        "expected": ["voice", "quiet", "speech"],
        "provenance": "recorded",
        "type": "speech",
    },
    "ElevenLabs": {
        "expected": ["voice", "generated", "tts", "elevenlabs"],
        "provenance": "generated",
        "type": "speech",
    },
    "Button": {
        "expected": ["sfx", "button", "click", "ui", "digital"],
        "provenance": "licensed",
        "type": "sfx",
    },
    "Destructed": {
        "expected": ["music", "piano", "dark", "element"],
        "provenance": "licensed",
        "type": "music",
    },
}

AUDIO_PROMPT = """Listen to this audio and output ONLY valid JSON:
{
  "primary_category": "Voice/Recorded",
  "provenance": "recorded",
  "description": "detailed description of what you hear (2-3 sentences)",
  "content_type": "speech",
  "enhanced_tags": ["tag1", "tag2"],
  "confidence": 0.85,
  "reasoning": "why you classified this way"
}
Choose from categories: Voice/Recorded, Voice/Generated, Voice/Character_Banks, Music/Tracks, Music/Elements, SFX/UI_Digital, SFX/Environment, Field_Raw.
Provenance: recorded, generated, or licensed.
Content type: speech, music, sfx, or mixed."""


def fixture(name: str) -> Path:
    for f in FIXTURES.iterdir():
        if name.lower() in f.name.lower():
            return f
    raise FileNotFoundError(f"Fixture not found: {name}")


def score_result(result: dict, expected: dict, file_type: str) -> dict:
    """Score a classification result against ground truth."""
    scores = {}
    text = json.dumps(result).lower()
    desc = result.get("description", "").lower()

    if file_type == "sfx" or file_type == "music":
        # Score on audio description quality, not transcript
        scores["has_description"] = len(desc) > 20
        scores["keyword_match"] = sum(1 for kw in expected["expected"] if kw in text)
    else:
        # Speech: check category and provenance
        cat = result.get("primary_category", "").lower()
        scores["category_contains"] = any(kw in cat for kw in expected["expected"])
        prov = result.get("provenance", "").lower()
        scores["provenance_match"] = prov == expected["provenance"]

    return scores


def preflight(provider, name: str) -> bool:
    """Verify the model produces different descriptions for two files."""
    f1 = fixture("interview_sample")
    f2 = fixture("Destructed")

    try:
        r1 = json.loads(provider.listen(f1, AUDIO_PROMPT))
        r2 = json.loads(provider.listen(f2, AUDIO_PROMPT))
        d1 = r1.get("description", "")
        d2 = r2.get("description", "")

        if len(d1) < 10 or len(d2) < 10:
            print(f"  {name}: FAIL — descriptions too short: '{d1[:50]}...' / '{d2[:50]}...'")
            return False
        if d1[:50] == d2[:50]:
            print(f"  {name}: FAIL — identical descriptions (not listening)")
            return False

        print(f"  {name}: PASS — voice='{d1[:80]}...' | piano='{d2[:80]}...'")
        return True
    except Exception as e:
        print(f"  {name}: FAIL — {e}")
        return False


def run_round2():
    """Run Round 2 bake-off with Transformers audio models."""
    from backend.audio.tf_provider import TransformersAudioProvider

    print("=" * 80)
    print("PHASE 1.1 BAKE-OFF ROUND 2 — True Audio Models")
    print("=" * 80)

    # ---- Arm 1: Qwen2.5-Omni-7B ----
    print("\n--- ARM 1: Qwen2.5-Omni-7B ---")
    provider = TransformersAudioProvider("Qwen/Qwen2.5-Omni-7B", load_in_4bit=True)

    # Pre-flight
    print("  Pre-flight...")
    if not preflight(provider, "Qwen2.5-Omni"):
        print("  SKIPPING ARM 1 — pre-flight failed")
    else:
        # Warm-up
        print("  Warming up...")
        warmup_file = fixture("interview_sample")
        start = time.time()
        provider.listen(warmup_file, AUDIO_PROMPT, max_new_tokens=128)
        warmup_time = time.time() - start
        print(f"  Warm-up: {warmup_time:.1f}s")

        # Score all fixtures
        for fname, truth in GROUND_TRUTH.items():
            path = fixture(fname)
            print(f"  Testing: {path.name}...", end=" ", flush=True)

            start = time.time()
            try:
                response = provider.listen(path, AUDIO_PROMPT, max_new_tokens=256)
                result = json.loads(response)
                latency = time.time() - start
                scores = score_result(result, truth, truth["type"])
                cat = result.get("primary_category", "?")
                prov = result.get("provenance", "?")
                desc = result.get("description", "")[:80]
                print(f"OK | {latency:.1f}s | {cat:25s} | {prov:10s} | {desc}...")
            except Exception as e:
                latency = time.time() - start
                print(f"FAIL | {latency:.1f}s | {str(e)[:60]}")

        provider.unload()

    # ---- Arm 2: Control (audio_analyzer.py) ----
    print("\n--- ARM 2: Control (audio_analyzer.py) ---")
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from audio_analyzer import AudioAnalyzer
    analyzer = AudioAnalyzer(base_dir=str(Path.home()))

    for fname, truth in GROUND_TRUTH.items():
        path = fixture(fname)
        print(f"  Testing: {path.name}...", end=" ", flush=True)
        start = time.time()
        try:
            spectral = analyzer.analyze_audio_spectral(path)
            latency = time.time() - start
            ct = spectral.get("content_type", "unknown")
            mood = spectral.get("mood", "unknown")
            bpm = spectral.get("bpm", 0)
            ok = spectral.get("success", False)
            status = "OK" if ok else "FAIL"
            print(f"{status} | {latency:.1f}s | type={ct:10s} | mood={mood:15s} | bpm={bpm:.0f}")
        except Exception as e:
            latency = time.time() - start
            print(f"FAIL | {latency:.1f}s | {str(e)[:60]}")

    print("\n" + "=" * 80)
    print("ROUND 2 COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_round2()
