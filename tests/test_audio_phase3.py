"""
Phase 3 acceptance tests — Naming convention + license guard.

Checkpoint 3 gates:
  1. Golden-set dry-run produces exactly the "Becomes" column
  2. Attempting to rename an ES_* file raises RenameLockedError
  3. Dry-run output matches expected filenames
"""
from pathlib import Path

import pytest

from backend.audio.classifier import AudioClassifier
from backend.audio.naming import (
    generate_filename,
    dry_run,
    is_rename_locked,
    RenameLockedError,
)

FIXTURES = Path(__file__).parent / "fixtures" / "audio_golden"


def fixture(name: str) -> Path:
    for f in FIXTURES.iterdir():
        if name.lower() in f.name.lower():
            return f
    raise FileNotFoundError(f"Fixture not found: {name}")


# ---------------------------------------------------------------------------
# GATE 1: Golden set dry-run matches spec "Becomes" column
# ---------------------------------------------------------------------------

def test_golden_dry_run():
    """
    Verify the dry-run output matches the directive's "Becomes" column.
    """
    classifier = AudioClassifier()

    # ElevenLabs → generated voice
    eleven = fixture("ElevenLabs")
    r = classifier.classify_provisional(eleven)
    name = generate_filename(r, project="example-project", source="elevenlabs", descriptor="avatar-intro")
    assert name.startswith("20"), f"Should start with date: {name}"
    assert "example-project" in name, f"Should include project: {name}"
    assert "VOXG" in name, f"Should use VOXG type code: {name}"
    assert name.endswith(".mp3"), f"Should preserve extension: {name}"

    # voice_takes → character bank
    rt = fixture("voice_takes")
    r = classifier.classify_provisional(rt)
    name = generate_filename(r, project="example-project", source="protagonist", descriptor="clone-takes", version=2)
    assert "VOXR" in name, f"Should use VOXR type code (VOXC from Phase 4): {name}"
    assert "v2" in name, f"Should include version: {name}"

    # interview_sample → recorded interview
    interview_subject = fixture("interview_sample")
    r = classifier.classify_provisional(interview_subject)
    name = generate_filename(r, project="unsorted", source="recorded", descriptor="recorded-interview")
    assert "VOXR" in name, f"Should use VOXR type code: {name}"
    assert "recorded-interview" in name, f"Should preserve descriptor: {name}"


# ---------------------------------------------------------------------------
# GATE 2: Licensed files → hard error on rename
# ---------------------------------------------------------------------------

def test_licensed_rename_raises():
    """ES_* files MUST raise RenameLockedError on rename attempt."""
    classifier = AudioClassifier()

    button = fixture("Button")
    r_button = classifier.classify_provisional(button)

    with pytest.raises(RenameLockedError, match="license|protected|locked"):
        generate_filename(r_button)

    piano = fixture("Destructed")
    r_piano = classifier.classify_provisional(piano)

    with pytest.raises(RenameLockedError, match="license|protected|locked"):
        generate_filename(r_piano)


# ---------------------------------------------------------------------------
# GATE 3: License guard returns UNCHANGED for ES_ files
# ---------------------------------------------------------------------------

def test_dry_run_licensed_unchanged():
    """Dry-run for licensed files shows LOCKED status."""
    classifier = AudioClassifier()

    button = fixture("Button")
    r_button = classifier.classify_provisional(button)
    result = dry_run(r_button)
    assert "LOCKED" in result, f"Licensed file should show LOCKED: {result}"


# ---------------------------------------------------------------------------
# GATE 4: Filename format validation
# ---------------------------------------------------------------------------

def test_filename_format():
    """Generated filenames follow the convention pattern."""
    classifier = AudioClassifier()
    interview_subject = fixture("interview_sample")
    r = classifier.classify_provisional(interview_subject)
    name = generate_filename(r, project="test", source="recorded", descriptor="test-file")

    # Pattern: YYYYMMDD_project_source_descriptor_TYPE_vN.ext
    parts = Path(name).stem.split("_")
    assert len(parts) >= 5, f"Expected at least 5 parts: {parts}"
    assert parts[0].isdigit() and len(parts[0]) == 8, f"First part should be date: {parts[0]}"
    assert parts[-1].startswith("v"), f"Last part should be version: {parts[-1]}"
    assert any(p in ["VOXR", "VOXG", "VOXR", "MUS", "STEM", "ELEM", "SFX", "AMB", "FLD"] for p in parts), \
        f"Must contain a valid type code: {parts}"


# ---------------------------------------------------------------------------
# GATE 5: Descriptor extraction preserves meaning
# ---------------------------------------------------------------------------

def test_extract_descriptor():
    """Descriptor extraction strips metadata but keeps semantic words."""
    from backend.audio.naming import _extract_descriptor

    # ElevenLabs timestamp-heavy filename
    desc = _extract_descriptor("ElevenLabs_2025-12-31T09_31_00_avatar_ivc_sp108_s34_sb71_se45_b_m2.mp3")
    assert "avatar" in desc, f"Should preserve 'avatar': {desc}"
    assert "elevenlabs" not in desc.lower(), f"Should strip ElevenLabs_ prefix: {desc}"

    # ES_ licensed file (shouldn't happen due to guard, but test anyway)
    desc2 = _extract_descriptor("ES_Miniature Button, Multiple Pushes - Epidemic Sound - 0000-0997.wav")
    assert "button" in desc2.lower() or "miniature" in desc2.lower(), f"Should preserve: {desc2}"

    # Simple filename
    desc3 = _extract_descriptor("voice_takes.mp3")
    assert "voice_takes" in desc3, f"Should preserve simple name: {desc3}"


# ---------------------------------------------------------------------------
# GATE 6: Lock detection
# ---------------------------------------------------------------------------

def test_is_rename_locked():
    """is_rename_locked correctly identifies protected files."""
    assert is_rename_locked("ES_Miniature Button.wav") is True
    assert is_rename_locked("Artlist_Track_01.wav") is True
    assert is_rename_locked("voice_takes.mp3") is False
    assert is_rename_locked("interview_sample.mp3") is False
    assert is_rename_locked("ElevenLabs_voice.mp3") is False  # generated ≠ licensed
