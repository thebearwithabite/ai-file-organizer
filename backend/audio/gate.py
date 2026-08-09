"""
Stage-1 DSP Gate — librosa feature extraction and routing.

Pure function: audio file path → GateReport.
Always runs, zero API calls, routes files to the correct analysis path.
Ported from audio_analyzer.py, stripped of heuristics.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class GateReport:
    """Raw DSP measurements + routing decisions. No AI, no heuristics."""
    # File identity
    file_path: str = ""
    filename: str = ""

    # Basic measurements
    duration_seconds: float = 0.0
    sample_rate: int = 0

    # Amplitude
    rms_db: float = 0.0           # mean RMS in dB
    rms_linear: float = 0.0       # mean RMS linear
    silence_fraction: float = 0.0  # fraction of frames below silence threshold
    is_near_silent: bool = False   # > 40% silence or RMS < -60 dB

    # Spectral
    centroid_hz: float = 0.0       # mean spectral centroid
    rolloff_hz: float = 0.0        # mean spectral rolloff
    bandwidth_hz: float = 0.0      # mean spectral bandwidth
    flatness: float = 0.0          # spectral flatness (0 = tonal, 1 = noise)
    zero_crossing_rate: float = 0.0

    # Harmonic / percussive
    harmonic_ratio: float = 0.0    # HPSS: 0 = all percussive, 1 = all harmonic

    # Onsets
    onsets_per_second: float = 0.0

    # Tempo
    bpm: float = 0.0

    # Routing decisions (no AI — pure signal logic)
    has_speech_profile: bool = False   # centroid 1500-3500, h/p 0.5-0.8
    has_music_profile: bool = False    # harmonic > 0.6
    has_sfx_profile: bool = False      # ZCR > 0.15 or harmonic < 0.3
    anomaly_flags: list[str] = field(default_factory=list)  # "near_silent", "clipped", etc.

    # Error state
    success: bool = True
    error: str = ""


# ---------------------------------------------------------------------------
# Thresholds (tuneable)
# ---------------------------------------------------------------------------

SILENCE_DB_THRESHOLD = -60.0   # frames below this are "silent"
NEAR_SILENT_RMS_DB = -60.0     # overall RMS below this → near-silent
HIGH_SILENCE_FRACTION = 0.40   # > 40% silence → anomaly

SPEECH_CENTROID_LO = 1500.0
SPEECH_CENTROID_HI = 3500.0
SPEECH_HARMONIC_LO = 0.5
SPEECH_HARMONIC_HI = 0.8

MUSIC_HARMONIC_THRESHOLD = 0.6
SFX_ZCR_THRESHOLD = 0.15
SFX_HARMONIC_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(path: Path, max_duration: float = 120.0) -> GateReport:
    """
    Extract raw DSP features from an audio file and produce routing decisions.

    Args:
        path: Path to audio file
        max_duration: Max seconds to load (120s default)

    Returns:
        GateReport with measurements and routing flags
    """
    path = Path(path)
    report = GateReport(
        file_path=str(path),
        filename=path.name,
    )

    try:
        import librosa
    except ImportError:
        report.success = False
        report.error = "librosa not available"
        return report

    try:
        # --- Load ---
        total_duration = librosa.get_duration(path=str(path))
        offset = 0.0
        if total_duration > max_duration:
            offset = (total_duration - max_duration) / 2

        y, sr = librosa.load(str(path), offset=offset, duration=min(max_duration, total_duration), sr=None)
        report.duration_seconds = total_duration
        report.sample_rate = sr

        # --- Amplitude ---
        rms = librosa.feature.rms(y=y)[0]
        rms_linear = float(np.mean(rms))
        report.rms_linear = rms_linear
        report.rms_db = float(20 * np.log10(max(rms_linear, 1e-10)))

        # Silence detection
        silence_mask = rms_linear < (10 ** (SILENCE_DB_THRESHOLD / 20))
        report.silence_fraction = float(np.mean(silence_mask))
        report.is_near_silent = (
            report.rms_db < NEAR_SILENT_RMS_DB or
            report.silence_fraction > HIGH_SILENCE_FRACTION
        )

        # --- Spectral ---
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        report.centroid_hz = float(np.mean(centroid))

        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        report.rolloff_hz = float(np.mean(rolloff))

        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        report.bandwidth_hz = float(np.mean(bandwidth))

        report.zero_crossing_rate = float(np.mean(librosa.feature.zero_crossing_rate(y)[0]))

        # Spectral flatness
        try:
            flatness = librosa.feature.spectral_flatness(y=y)
            report.flatness = float(np.mean(flatness))
        except Exception:
            report.flatness = 0.0

        # --- Harmonic / percussive ---
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        h_energy = np.sum(y_harmonic ** 2)
        p_energy = np.sum(y_percussive ** 2)
        total_energy = h_energy + p_energy
        report.harmonic_ratio = float(h_energy / total_energy) if total_energy > 0 else 0.0

        # --- Onsets ---
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
        if len(onset_frames) > 0 and report.duration_seconds > 0:
            report.onsets_per_second = len(onset_frames) / report.duration_seconds

        # --- Tempo ---
        try:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            report.bpm = float(tempo)
        except Exception:
            report.bpm = 0.0

        # --- Routing decisions ---
        c = report.centroid_hz
        h = report.harmonic_ratio
        z = report.zero_crossing_rate

        report.has_speech_profile = (
            SPEECH_CENTROID_LO <= c <= SPEECH_CENTROID_HI and
            SPEECH_HARMONIC_LO <= h <= SPEECH_HARMONIC_HI
        )
        report.has_music_profile = h > MUSIC_HARMONIC_THRESHOLD
        report.has_sfx_profile = z > SFX_ZCR_THRESHOLD or h < SFX_HARMONIC_THRESHOLD

        # --- Anomaly flags ---
        if report.is_near_silent:
            report.anomaly_flags.append("near_silent")
        if report.duration_seconds < 1.0:
            report.anomaly_flags.append("ultra_short")

        return report

    except Exception as e:
        logger.error(f"Gate analysis failed for {path.name}: {e}")
        report.success = False
        report.error = str(e)
        return report
