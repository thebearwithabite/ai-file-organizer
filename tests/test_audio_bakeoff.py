"""
Phase 1 Bake-off — four-arm model comparison over 5 golden fixtures.

Arms:
  1. gemma4:12b        (multimodal — tries base64 audio first)
  2. gemma4:e4b        (text fallback — transcribe → classify)  
  3. QAT abliterated    (text fallback — transcribe → classify)
  4. audio_analyzer.py  (control — librosa + heuristics, no LLM)

Reports: category accuracy, provenance detection, VRAM footprint, latency.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from backend.audio.gate import analyze as gate_analyze
from backend.audio.listener import listen, ListenResult, OLLAMA_URL

FIXTURES = Path(__file__).parent / "fixtures" / "audio_golden"

# Expected ground truth per fixture (for scoring)
GROUND_TRUTH = {
    "interview_sample": {
        "primary_category": "Voice/Recorded",
        "provenance": "recorded",
        "expected_speech": True,
    },
    "voice_takes": {
        "primary_category": "Voice/Character_Banks",
        "provenance": "recorded",
        "expected_speech": True,
    },
    "ElevenLabs": {
        "primary_category": "Voice/Generated",
        "provenance": "generated",
        "expected_speech": True,
    },
    "Button": {
        "primary_category": "SFX/UI_Digital",
        "provenance": "licensed",
        "expected_speech": False,
    },
    "Destructed": {
        "primary_category": "Music/Elements",
        "provenance": "licensed",
        "expected_speech": False,
    },
}


def fixture(name: str) -> Path:
    for f in FIXTURES.iterdir():
        if name.lower() in f.name.lower():
            return f
    raise FileNotFoundError(f"Fixture not found: {name}")


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_result(result: ListenResult, expected: dict) -> dict:
    """Score a single result against ground truth."""
    scores = {}

    # Category match (fuzzy — prefix match)
    cat = result.primary_category.lower()
    exp_cat = expected["primary_category"].lower()
    scores["category_match"] = cat.startswith(exp_cat.split("/")[0])  # "Voice" vs "Voice/Recorded"

    # Provenance
    scores["provenance_match"] = result.provenance.lower() == expected["provenance"].lower()

    # Speech detection
    if expected["expected_speech"]:
        scores["speech_detected"] = result.content_probs.get("speech", 0) > 0.3
    else:
        scores["speech_detected"] = result.content_probs.get("speech", 0) < 0.3

    # ElevenLabs specific: must detect as generated
    if "elevenlabs" in result.filename.lower():
        scores["generated_detected"] = "generated" in result.provenance.lower()

    return scores


# ---------------------------------------------------------------------------
# VRAM measurement
# ---------------------------------------------------------------------------

def get_vram_mb() -> int:
    """Get GPU memory used by ollama processes (MB)."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        return sum(int(line.strip()) for line in out.stdout.strip().split("\n") if line.strip())
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# Bake-off
# ---------------------------------------------------------------------------

@dataclass
class BakeOffRow:
    """One row in the bake-off report."""
    model: str
    file: str
    method: str = ""
    category: str = ""
    provenance: str = ""
    confidence: float = 0.0
    latency_s: float = 0.0
    vram_mb: int = 0
    category_ok: bool = False
    provenance_ok: bool = False
    success: bool = False
    error: str = ""


def run_bakeoff() -> list[BakeOffRow]:
    """Run all 4 arms across all 5 fixtures."""
    models = [
        "gemma4:12b",
        "gemma4:e4b",
        "jikepjikep_16HEX/gemma-4-12b-nightshift-heretic-uncensored-qat-q4",
    ]

    fixture_names = ["interview_sample", "voice_takes", "ElevenLabs", "Button", "Destructed"]
    rows = []

    for model in models:
        print(f"\n{'='*60}")
        print(f"ARM: {model}")
        print(f"{'='*60}")

        for fname in fixture_names:
            path = fixture(fname)
            expected = GROUND_TRUTH[fname]
            print(f"  Testing: {path.name}...", end=" ", flush=True)

            # VRAM before
            vram_before = get_vram_mb()

            # Listen
            gate = gate_analyze(path)
            result = listen(path, model=model, gate_report=gate, timeout=180)

            # VRAM after
            vram_after = get_vram_mb()
            vram_delta = max(0, vram_after - vram_before)

            # Score
            scores = score_result(result, expected)

            row = BakeOffRow(
                model=model,
                file=fname,
                method=result.method,
                category=result.primary_category,
                provenance=result.provenance,
                confidence=result.confidence,
                latency_s=result.latency_seconds,
                vram_mb=vram_delta,
                category_ok=scores.get("category_match", False),
                provenance_ok=scores.get("provenance_match", False),
                success=result.success,
                error=result.error,
            )
            rows.append(row)

            status = "OK" if row.success else "FAIL"
            print(f"{status} | {row.method:15s} | {row.category:25s} | {row.provenance:10s} | {row.latency_s:.1f}s")

    return rows


def print_report(rows: list[BakeOffRow]) -> None:
    """Print the bake-off report in table format."""
    print("\n")
    print("=" * 120)
    print("PHASE 1 BAKE-OFF REPORT — Audio Classification Model Comparison")
    print("=" * 120)
    print()

    # Group by model
    models = list(dict.fromkeys(r.model for r in rows))
    for model in models:
        model_rows = [r for r in rows if r.model == model]
        ok = sum(1 for r in model_rows if r.category_ok)
        prov_ok = sum(1 for r in model_rows if r.provenance_ok)
        avg_latency = sum(r.latency_s for r in model_rows) / len(model_rows) if model_rows else 0

        print(f"--- {model} ---")
        print(f"  Category accuracy:  {ok}/{len(model_rows)}")
        print(f"  Provenance accuracy: {prov_ok}/{len(model_rows)}")
        print(f"  Avg latency:         {avg_latency:.1f}s")
        print(f"  Methods used:        {', '.join(set(r.method for r in model_rows))}")
        print()

        for r in model_rows:
            status = "✓" if r.category_ok else "✗"
            print(f"  {status} {r.file:15s} → {r.category:25s} ({r.provenance:10s}, {r.confidence:.2f}) | {r.latency_s:.1f}s | {r.method}")
        print()

    # Summary
    print("--- SUMMARY ---")
    for model in models:
        model_rows = [r for r in rows if r.model == model]
        ok = sum(1 for r in model_rows if r.category_ok)
        avg_lat = sum(r.latency_s for r in model_rows) / len(model_rows)
        print(f"  {model:55s} | {ok}/{len(model_rows)} cat | {avg_lat:.1f}s avg")

    print()
    print("=" * 120)


# ---------------------------------------------------------------------------
# Control arm (audio_analyzer.py)
# ---------------------------------------------------------------------------

def run_control() -> list[dict]:
    """Run the audio_analyzer.py control over golden fixtures."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from audio_analyzer import AudioAnalyzer

    analyzer = AudioAnalyzer(base_dir=str(Path.home()))
    results = []

    for fname in ["interview_sample", "voice_takes", "ElevenLabs", "Button", "Destructed"]:
        path = fixture(fname)
        start = time.time()
        spectral = analyzer.analyze_audio_spectral(path)
        elapsed = time.time() - start

        results.append({
            "file": fname,
            "content_type": spectral.get("content_type", "unknown"),
            "mood": spectral.get("mood", "unknown"),
            "bpm": spectral.get("bpm", 0),
            "latency_s": elapsed,
        })

    return results


# ---------------------------------------------------------------------------
# Pytest integration
# ---------------------------------------------------------------------------

def test_bakeoff_runs():
    """Smoke test: bake-off runs without crashing on at least one fixture."""
    path = fixture("interview_sample")
    gate = gate_analyze(path)
    result = listen(path, model="gemma4:12b", gate_report=gate, timeout=180)
    assert result.success, f"Listen failed: {result.error}"


if __name__ == "__main__":
    rows = run_bakeoff()
    print_report(rows)

    print("\n--- CONTROL (audio_analyzer.py) ---")
    control = run_control()
    for r in control:
        print(f"  {r['file']:15s} → {r['content_type']:10s} | {r['mood']:15s} | {r['bpm']:.0f} BPM | {r['latency_s']:.1f}s")
