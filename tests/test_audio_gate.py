"""
Golden tests for Phase 0 — Stage-1 DSP Gate.

Baselines measured in organizer venv, WSL/Linux, 2026-08-04.
Routing decisions are the acceptance criteria — numeric values are for regression.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from backend.audio.gate import analyze, GateReport

FIXTURES = Path(__file__).parent / "fixtures" / "audio_golden"


def within(actual: float, expected: float, tolerance: float = 0.10) -> bool:
    if expected == 0:
        return actual == 0 or abs(actual) < 0.001
    return abs(actual - expected) / abs(expected) <= tolerance


def fixture(name: str) -> Path:
    for f in FIXTURES.iterdir():
        if name.lower() in f.name.lower():
            return f
    raise FileNotFoundError(f"Golden fixture not found: {name}")


# ---------------------------------------------------------------------------
# interview_sample.mp3 — interview, clear speech
# ---------------------------------------------------------------------------

def test_interview_sample():
    """
    40.7s interview. Speech profile expected.
    Measured: centroid 2609 Hz, h/p 0.64, RMS -23 dB.
    """
    r = analyze(fixture("interview_sample"))
    assert r.success, r.error
    assert within(r.duration_seconds, 40.7), f"Duration: {r.duration_seconds}"
    assert r.rms_db > -30, f"RMS should be audible: {r.rms_db}"
    assert r.silence_fraction < 0.05, f"Silence: {r.silence_fraction}"

    # Routing
    assert r.has_speech_profile, "Must detect speech profile"
    assert not r.is_near_silent, "Must not flag as silent"
    assert not r.anomaly_flags, f"Anomalies: {r.anomaly_flags}"


# ---------------------------------------------------------------------------
# voice_takes.mp3 — quiet voice takes, clone training
# ---------------------------------------------------------------------------

def test_voice_takes():
    """
    40.6s quiet clone takes. NOT near-silent (has audible content at -32 dB).
    Flatness 0.38 confirms it's tonal speech, not noise.
    Gate routes it normally — the listener decides if it's usable.
    """
    r = analyze(fixture("voice_takes"))
    assert r.success, r.error
    assert within(r.duration_seconds, 40.6), f"Duration: {r.duration_seconds}"
    assert within(r.flatness, 0.38, 0.20), f"Flatness: {r.flatness}"

    # Has speech content (centroid 1506 Hz, h/p 0.63)
    assert r.has_speech_profile, "Quiet voice is still speech"
    assert not r.is_near_silent, "Has audible content"


# ---------------------------------------------------------------------------
# ElevenLabs_...mp3 — generated TTS voice
# ---------------------------------------------------------------------------

def test_elevenlabs_avatar():
    """
    7.6s generated voice. Percussive-dominant (h/p 0.02) due to TTS artifacts.
    Provenance: "generated" (prior from filename, confirmed by listener).
    """
    r = analyze(fixture("ElevenLabs"))
    assert r.success, r.error
    assert within(r.duration_seconds, 7.6), f"Duration: {r.duration_seconds}"
    assert not r.is_near_silent, "Generated voice has content"


# ---------------------------------------------------------------------------
# ES_Miniature Button...wav — licensed SFX, regression guard
# ---------------------------------------------------------------------------

def test_es_button():
    """
    1.0s button SFX. Centroid 19.9 kHz (96k sample rate), flatness 0.74.
    SFX profile. Licensed → NEVER renamed, NEVER archived.
    Ultra-short NOT equal to junk — this file guards that regression.
    """
    r = analyze(fixture("Button"))
    assert r.success, r.error
    assert within(r.duration_seconds, 1.0), f"Duration: {r.duration_seconds}"
    assert within(r.flatness, 0.74, 0.15), f"Flatness: {r.flatness}"

    # SFX profile
    assert r.has_sfx_profile, "Button click is SFX"
    # Ultra-short flag is informative, not a routing decision
    # The listener/pipeline decides, not the gate


# ---------------------------------------------------------------------------
# ES_Piano, Destructed, Dark Keys...wav — licensed music element
# ---------------------------------------------------------------------------

def test_es_dark_piano():
    """
    14s dark piano element. Centroid 322 Hz, h/p 0.98.
    Music profile. Licensed → not renamed.
    """
    r = analyze(fixture("Destructed"))
    assert r.success, r.error
    assert within(r.duration_seconds, 14.0), f"Duration: {r.duration_seconds}"
    assert r.centroid_hz < 500, f"Dark piano should have low centroid: {r.centroid_hz}"

    # Music profile
    assert r.has_music_profile, "Piano is music"


# ---------------------------------------------------------------------------
# Cross-fixture routing tests
# ---------------------------------------------------------------------------

def test_routing_decisions_correct():
    """Every fixture's routing matches its content type."""
    interview_subject = analyze(fixture("interview_sample"))
    rt = analyze(fixture("voice_takes"))
    eleven = analyze(fixture("ElevenLabs"))
    button = analyze(fixture("Button"))
    piano = analyze(fixture("Destructed"))

    # interview_subject + rt: speech
    assert interview_subject.has_speech_profile, "interview_subject = speech"
    assert rt.has_speech_profile, "rt = speech (quiet but speech)"

    # button: SFX
    assert button.has_sfx_profile, "button = SFX"

    # piano: music
    assert piano.has_music_profile, "piano = music"


def test_licensed_prefixes():
    """ES_ prefix files are licensed."""
    button = analyze(fixture("Button"))
    piano = analyze(fixture("Destructed"))
    assert button.filename.startswith("ES_")
    assert piano.filename.startswith("ES_")

    eleven = analyze(fixture("ElevenLabs"))
    assert eleven.filename.startswith("ElevenLabs_")


def test_no_false_silence_on_voiced_files():
    """Only genuinely silent files should be flagged."""
    interview_subject = analyze(fixture("interview_sample"))
    eleven = analyze(fixture("ElevenLabs"))
    rt = analyze(fixture("voice_takes"))
    button = analyze(fixture("Button"))

    # None of these are truly silent
    assert not interview_subject.is_near_silent
    assert not eleven.is_near_silent
    assert not rt.is_near_silent
    assert not button.is_near_silent
