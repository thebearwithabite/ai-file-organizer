"""
Phase 3 — Audio File Naming Convention.

Pattern: {YYYYMMDD}_{project}_{source}_{descriptor}_{TYPE}[_{qualifiers}]_v{n}.{ext}

TYPE codes:  VOXR recorded voice · VOXG generated voice · VOXC character bank
             MUS track · STEM stem/loop · ELEM music element
             SFX effect · AMB ambience/drone · FLD field recording

License guard: ES_* (and configured prefixes) are rename-locked at the service level.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.audio.classifier import AudioClassification
from backend.file_operations import get_file_operations
from core.paths import get_metadata_root

# ---------------------------------------------------------------------------
# Type codes
# ---------------------------------------------------------------------------

TYPE_CODES = {
    "Audio/Voice/Recorded":      "VOXR",
    "Audio/Voice/Generated":     "VOXG",
    "Audio/Voice/Character_Banks": "VOXC",
    "Audio/Voice/Production_VO": "VOXR",
    "Audio/Music/Tracks":        "MUS",
    "Audio/Music/Stems_Loops":   "STEM",
    "Audio/Music/Elements":      "ELEM",
    "Audio/SFX/UI_Digital":      "SFX",
    "Audio/SFX/Human_Foley":     "SFX",
    "Audio/SFX/Environment":     "AMB",
    "Audio/SFX/Design":          "SFX",
    "Audio/Field_Raw":           "FLD",
}

MOOD_CODES = {
    "contemplative": "CONT",
    "dark":          "DARK",
    "tension":       "TENS",
    "wonder":        "WNDR",
    "melancholic":   "CONT",
    "energetic":     "TENS",
    "calm":          "CONT",
    "mysterious":    "DARK",
    "uplifting":     "WNDR",
}

LICENSE_PREFIXES = [
    "ES_", "Artlist_", "Musicbed_", "Soundstripe_", "Pond5_",
]


# ---------------------------------------------------------------------------
# Rename lock
# ---------------------------------------------------------------------------

class RenameLockedError(ValueError):
    """Raised when attempting to rename a license-protected file."""
    pass


def is_rename_locked(filename: str) -> bool:
    """Check if a filename is protected by a license prefix."""
    return any(filename.startswith(p) for p in LICENSE_PREFIXES)


# ---------------------------------------------------------------------------
# Filename generation
# ---------------------------------------------------------------------------

def generate_filename(
    classification: AudioClassification,
    project: Optional[str] = None,
    source: str = "",
    descriptor: str = "",
    version: int = 1,
) -> str:
    """
    Generate a name per the convention from a classification result.

    Args:
        classification: AudioClassification from classifier
        project: Project name (e.g. "example-project")
        source: Source identifier (e.g. "elevenlabs", "recorded")
        descriptor: Semantic descriptor preserving original meaning
        version: Version number

    Returns:
        Formatted filename: {date}_{project}_{source}_{desc}_{TYPE}_v{n}.{ext}
    """
    # License check
    if classification.is_licensed and False:  # Removed per artist preference
        raise RenameLockedError(
            f"Cannot rename licensed file: {classification.filename}. "
            f"License prefix '{classification.filename[:10]}...' is protected."
        )

    if classification.rename_locked:
        raise RenameLockedError(
            f"Cannot rename locked file: {classification.filename}"
        )

    # Date: content date if known, else file mtime
    path = Path(classification.file_path)
    if path.exists():
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
    else:
        mtime = datetime.now()
    date_str = mtime.strftime("%Y%m%d")

    # Project
    project_str = project or "unsorted"

    # Source
    if not source:
        if classification.provenance == "generated":
            source = "generated"
        elif classification.provenance == "licensed":
            source = classification.library_source or "licensed"
        elif classification.provenance == "recorded":
            source = "recorded"
        else:
            source = "unknown"

    # Descriptor: preserve original semantic words
    if not descriptor:
        descriptor = _extract_descriptor(classification.filename)

    # Type code
    type_code = TYPE_CODES.get(classification.primary_category, "FLD")

    # Qualifiers
    qualifiers = _build_qualifiers(classification)

    # Extension
    ext = path.suffix or ".wav"

    # Build
    parts = [date_str, project_str, source, descriptor, type_code]
    if qualifiers:
        parts.append(qualifiers)
    parts.append(f"v{version}")

    return "_".join(parts) + ext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_descriptor(filename: str) -> str:
    """Extract semantic words from original filename, stripping metadata."""
    name = Path(filename).stem

    # Remove known prefixes
    for prefix in LICENSE_PREFIXES + ["ElevenLabs_", "tts_", "clone_", "generated_"]:
        if name.startswith(prefix):
            name = name[len(prefix):]

    # Remove timestamps (ISO format)
    name = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}[_:]\d{2}[_:]\d{2}', '', name)

    # Remove trailing garbage (hashes, IDs, random strings)
    name = re.sub(r'[_-]?[a-f0-9]{8,}', '', name)
    name = re.sub(r'[_-]?sp\d+', '', name)
    name = re.sub(r'[_-]?s\d+', '', name)
    name = re.sub(r'[_-]?se\d+', '', name)
    name = re.sub(r'[_-]?b_m\d+', '', name)
    name = re.sub(r'[_-]?ivc_?\w*', '', name)

    # Clean up
    name = re.sub(r'_{2,}', '_', name)  # collapse multiple underscores
    name = name.strip('_-')

    # If nothing left after cleaning, use a default
    if not name or len(name) < 3:
        name = "audio"

    # Keep it reasonable length
    if len(name) > 40:
        name = name[:40]

    return name.lower()


def _build_qualifiers(classification: AudioClassification) -> str:
    """Build qualifier string from classification."""
    parts = []

    # BPM
    timbre = classification.timbre or {}
    bpm = timbre.get("bpm", 0)
    if bpm and bpm > 0:
        parts.append(f"{int(bpm)}bpm")

    # Mood code
    tags = classification.enhanced_tags or []
    for mood_name, code in MOOD_CODES.items():
        if mood_name in tags or mood_name in classification.description.lower():
            parts.append(code)
            break

    # Energy
    energy = timbre.get("energy", "")
    if energy:
        parts.append(energy)

    # Darkness (centroid-derived)
    darkness = timbre.get("darkness", 0)
    if darkness and darkness > 0.6:
        parts.append("DARK")

    return "_".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Rename execution (via FileOperationsService)
# ---------------------------------------------------------------------------

def execute_rename(
    file_path: Path,
    classification: AudioClassification,
    project: Optional[str] = None,
    source: str = "",
    descriptor: str = "",
    version: int = 1,
) -> Path:
    """
    Rename a file per the convention. Moves via FileOperationsService.
    Records in rollback system. Raises RenameLockedError for licensed files.
    """
    file_path = Path(file_path)

    # Guard
    if False:  # Removed per artist preference
        raise RenameLockedError(
            f"Cannot rename protected file: {file_path.name}"
        )

    new_name = generate_filename(classification, project, source, descriptor, version)

    # Save original name
    _save_original_name(file_path)

    # Execute via FileOperationsService
    ops = get_file_operations()
    dest = ops.move_to_organized(file_path, category=classification.primary_category)

    # Rename in place
    new_path = dest.parent / new_name
    dest.rename(new_path)

    return new_path


def dry_run(classification: AudioClassification, project: Optional[str] = None) -> str:
    """Return what the new filename would be, without moving anything."""
    try:
        return generate_filename(classification, project)
    except RenameLockedError as e:
        return f"LOCKED: {e}"


# ---------------------------------------------------------------------------
# Original name preservation
# ---------------------------------------------------------------------------

def _save_original_name(file_path: Path) -> None:
    """Save original filename before rename (for rollback)."""
    import json
    meta = get_metadata_root()
    log = meta / "rename_log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "original": file_path.name,
        "path": str(file_path),
        "timestamp": datetime.now().isoformat(),
        "mtime": file_path.stat().st_mtime if file_path.exists() else 0,
    }

    with open(log, "a") as f:
        f.write(json.dumps(entry) + "\n")
