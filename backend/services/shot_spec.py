"""ShotSpec — engine-neutral shot schema (PROMPT-MACHINE-DIRECTIVE v1.2).

ShotSpec is the single source of truth for what a shot *is*: narrative
intent, subjects with reference material, action, camera, lighting,
style/grade, setting, duration, audio intent, and seed. It is stored in
SQLite, shared by the director service, the review loop, asset bindings,
and the prompt compiler.

**Engine-neutral by design.** The schema carries no engine names and no
engine-specific assumptions:

* ``duration_seconds`` is a positive number of seconds — the schema encodes
  no cap and no engine limit;
* consistency is expressed as explicit entity references (stable ids,
  repeated descriptions, reference-image paths), never as a description
  lock or other shorthand;
* render settings (templates, bounded overrides, sampler options) live at
  compile time, not here. Per-engine payloads are produced by the prompt
  compiler — a separate task — from a validated ShotSpec. No renderer is
  named in this module; ``tests/test_shot_spec.py`` enforces that
  mechanically.

**Validation is strict.** Unknown keys are rejected so a stale shape (for
example an embedded generation block) can never silently re-enter the
schema. ``validate_shot_spec()`` / ``load_shot_spec()`` raise
``ShotSpecValidationError`` carrying one entry per error — field path plus
human-readable reason — which is actionable for humans and for the LLM
repair loop alike::

    invalid ShotSpec (examples/shotspec/invalid/negative_duration.json):
      - duration_seconds: Input should be greater than 0

The machine-readable JSON Schema artifact lives at
``schemas/shotspec.schema.json`` and is regenerated with
``python -m backend.services.shot_spec --emit-schema``. Hand-written
example specs live in ``examples/shotspec/`` (see ``load_examples()``).

Key design lock preserved from the director phase: ``expression_cues`` is
physical cues only — no emotion labels. Video models render physical
action, not adjectives. The validator rejects emotion adjectives so schema
violations drive the LLM retry loop.
"""
from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

# Emotion adjectives that must never appear in entity expression cues.
# Whole-word, case-insensitive match. Keep unambiguous emotion labels only —
# dispositional words that double as physical demeanor (serious, thoughtful,
# calm, determined, playful) stay allowed.
EMOTION_LABELS = frozenset({
    "happy", "sad", "angry", "afraid", "scared", "excited", "nervous",
    "anxious", "joyful", "furious", "surprised", "confused", "worried",
    "pleased", "annoyed", "frustrated", "hopeful", "relieved", "bored",
    "disgusted", "jealous", "proud", "ashamed", "guilty", "lonely",
    "thrilled", "terrified", "depressed", "irritated", "upset", "glad",
    "delighted", "miserable", "embarrassed", "suspicious", "eager", "shy",
    "content",
})


class ShotStatus(str, Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    regen_requested = "regen_requested"


class AssetType(str, Enum):
    character = "character"
    location = "location"
    prop = "prop"
    style = "style"


class _StrictModel(BaseModel):
    """Base for shot-schema models: unknown keys are rejected by contract."""

    model_config = ConfigDict(extra="forbid")


class EntityRef(_StrictModel):
    """A subject/entity in this shot, with the reference material that keeps
    it consistent across shots and its physical performance cues here.

    Consistency mechanism: a subject recurring across shots repeats the same
    ``entity_id``, ``name``, ``description`` and ``reference_images`` in every
    shot. The ``description`` is the stable phrasing the compiler carries into
    output; ``expression_cues`` is per-shot and physical only.
    """

    entity_id: str = Field(
        ..., pattern=r"^[a-z0-9_]+$",
        description="Stable slug reused verbatim across shots, e.g. 'char_maya'",
    )
    name: str = Field(..., min_length=1, description="Proper name, e.g. 'Maya'")
    kind: AssetType = Field(AssetType.character, description="character | location | prop | style")
    description: str = Field(
        ..., min_length=1,
        description="Stable appearance description — repeat verbatim across shots",
    )
    reference_images: List[str] = Field(
        default_factory=list,
        description="Reference image paths used to keep this subject consistent",
    )
    expression_cues: Optional[str] = Field(
        None,
        description="PHYSICAL cues only for this shot — facial/body action, "
        "no emotion labels (never: happy, sad, angry, scared, etc.)",
    )

    @field_validator("expression_cues")
    @classmethod
    def _no_emotion_labels(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        words = set(re.findall(r"[a-z']+", v.lower()))
        hits = sorted(words & EMOTION_LABELS)
        if hits:
            raise ValueError(
                f"expression_cues must be physical cues only, no emotion labels; "
                f"found: {', '.join(hits)}"
            )
        return v


class CameraSpec(_StrictModel):
    framing: str = Field(..., min_length=1, description="e.g. 'Eye-Level Close-Up', 'Low-Angle Wide'")
    movement: str = Field("", description="Camera movement, e.g. 'slow dolly in'")
    lens_feel: str = Field(
        "", description="Lens character, e.g. '85mm, shallow depth of field'"
    )


class AudioSpec(_StrictModel):
    dialogue: str = Field("", description="Quoted speech, e.g. '\"That's it... Dad's lost it.\"'")
    delivery: str = Field("", description="Delivery notes (physical: pacing, volume, pauses)")
    ambience: str = Field("", description="Room tone / environmental sound")
    sfx: str = Field("", description="Sound effects")


class AssetBinding(_StrictModel):
    """Production binding of an extracted asset to this shot (Phase 2)."""

    asset_id: str = Field(..., description="Reference to an extracted asset row (see AssetService)")
    type: AssetType = AssetType.character
    lora_path: Optional[str] = None
    trigger_token: Optional[str] = None
    ref_image: Optional[str] = Field(None, description="StorageRef to a reference image")
    weight: float = Field(0.9, ge=0.0, le=1.0, description="Character 0.8-1.0, scene 0.5-0.7, effect 0.3-0.6")


class ShotSpec(_StrictModel):
    """One shot, engine-neutral (see module docstring).

    Required creative core: narrative_intent, setting, action, lighting,
    style_grade, duration_seconds, camera.framing. Everything else has
    defaults; ``notes`` is the free-form escape hatch.
    """

    project_id: str = Field("", description="Optional project identifier")
    shot_id: str = Field(..., pattern=r"^sc\d+_sh\d+$", description="e.g. sc01_sh01")
    sequence_index: int = Field(0, ge=0)
    status: ShotStatus = ShotStatus.draft
    version: int = Field(1, ge=1)

    narrative_intent: str = Field(..., min_length=1, description="What this shot must accomplish dramatically")
    setting: str = Field(..., min_length=1, description="Where and when it takes place")
    action: str = Field(..., min_length=1, description="The visible action — one clear beat")
    lighting: str = Field(..., min_length=1, description="One coherent lighting description")
    style_grade: str = Field(..., min_length=1, description="Look / grade of the shot")
    duration_seconds: float = Field(
        ..., gt=0, allow_inf_nan=False,
        description="Positive seconds — no upper bound is encoded in the schema",
    )

    camera: CameraSpec
    entities: List[EntityRef] = Field(default_factory=list)
    audio: AudioSpec = Field(default_factory=AudioSpec)
    assets: List[AssetBinding] = Field(default_factory=list)
    seed: int = Field(-1, description="RNG seed; -1 = unset, derived at compile time")
    notes: str = Field("", description="Free-form escape hatch")


# ---------------------------------------------------------------------------
# Validation — actionable errors (field path + reason)
# ---------------------------------------------------------------------------


def _format_loc(loc: tuple) -> str:
    """('entities', 0, 'name') -> 'entities[0].name'."""
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out or "$"


class ShotSpecValidationError(ValueError):
    """Actionable ShotSpec validation failure.

    ``errors`` is a list of ``{"path": str, "reason": str, "type": str}``.
    ``str(err)`` renders every error as ``<field path>: <reason>``.
    """

    def __init__(self, errors: List[Dict[str, str]], source: str = ""):
        self.errors = [dict(e) for e in errors]
        self.source = source
        where = f" ({source})" if source else ""
        details = "\n".join(f"  - {e['path']}: {e['reason']}" for e in self.errors)
        super().__init__(f"invalid ShotSpec{where}:\n{details}")


def _error_entries(exc: ValidationError) -> List[Dict[str, str]]:
    entries = []
    for err in exc.errors():
        msg = err["msg"]
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        entries.append({"path": _format_loc(err["loc"]), "reason": msg, "type": err["type"]})
    return entries


def validate_shot_spec(payload: Any, *, source: str = "") -> ShotSpec:
    """Validate a payload mapping (or JSON string) as a ShotSpec.

    Raises ``ShotSpecValidationError`` with one ``(path, reason)`` entry per
    error; never returns a partially-validated model.
    """
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise ShotSpecValidationError(
                [{"path": "$", "reason": f"invalid JSON: {e}", "type": "json_invalid"}],
                source=source or "<string>",
            ) from None
    elif isinstance(payload, Mapping):
        data = dict(payload)
    else:
        raise TypeError(
            f"payload must be a mapping or JSON string, got {type(payload).__name__}"
        )
    try:
        return ShotSpec.model_validate(data)
    except ValidationError as e:
        raise ShotSpecValidationError(_error_entries(e), source=source) from None


def validate_shot_specs(payloads: List[Any], *, source: str = "") -> List[ShotSpec]:
    """Validate a list of shot payloads (each entry validated independently)."""
    out = []
    for i, p in enumerate(payloads):
        out.append(validate_shot_spec(p, source=f"{source}[{i}]" if source else f"[{i}]"))
    return out


def load_shot_spec(path: Any) -> ShotSpec:
    """Load + validate one ShotSpec JSON file. Raises ShotSpecValidationError."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ShotSpecValidationError(
            [{"path": "$", "reason": f"invalid JSON: {e}", "type": "json_invalid"}],
            source=str(p),
        ) from None
    return validate_shot_spec(data, source=str(p))


# ---------------------------------------------------------------------------
# Examples library
# ---------------------------------------------------------------------------

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples" / "shotspec"


def example_paths(include_invalid: bool = False) -> List[Path]:
    """Sorted paths of the hand-written example specs (valid by default)."""
    if not EXAMPLES_DIR.is_dir():
        return []
    paths = sorted(EXAMPLES_DIR.glob("*.json"))
    if include_invalid:
        paths += sorted((EXAMPLES_DIR / "invalid").glob("*.json"))
    return paths


def load_examples() -> Dict[str, ShotSpec]:
    """``{stem: validated ShotSpec}`` for every valid example in the library."""
    return {p.stem: load_shot_spec(p) for p in example_paths()}


# ---------------------------------------------------------------------------
# JSON Schema artifact
# ---------------------------------------------------------------------------

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "shotspec.schema.json"


def shotspec_json_schema() -> dict:
    """The machine-readable JSON Schema for ShotSpec."""
    return ShotSpec.model_json_schema()


def write_json_schema(path: Any = None) -> Path:
    """Write the JSON Schema artifact (default: ``schemas/shotspec.schema.json``)."""
    target = Path(path) if path else SCHEMA_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(shotspec_json_schema(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


def _main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="ShotSpec schema utilities")
    parser.add_argument(
        "--emit-schema", nargs="?", const=str(SCHEMA_PATH), default=None, metavar="PATH",
        help=f"write the JSON Schema artifact (default: {SCHEMA_PATH})",
    )
    parser.add_argument(
        "--validate", nargs="+", default=None, metavar="FILE",
        help="validate ShotSpec JSON file(s); exit 1 on any failure",
    )
    args = parser.parse_args(argv)

    if not args.emit_schema and not args.validate:
        parser.print_help()
        return 2

    rc = 0
    if args.emit_schema:
        print(f"wrote {write_json_schema(args.emit_schema)}")
    if args.validate:
        for f in args.validate:
            try:
                spec = load_shot_spec(f)
                print(f"ok   {f}  ({spec.shot_id})")
            except ShotSpecValidationError as e:
                rc = 1
                print(f"FAIL {f}")
                print(str(e))
    return rc


# ---------------------------------------------------------------------------
# Downstream models (unchanged from Phase 1/2 — not part of the shot schema
# contract, but stored alongside it)
# ---------------------------------------------------------------------------


class ScenePlanScene(BaseModel):
    """One scene from the engine-agnostic scene plan (veo_latest generateScenePlan port)."""

    scene_id: str = Field(..., description="e.g. 'sc01'")
    summary: str = Field(..., description="One-paragraph beat summary")
    runtime_goal_s: float = Field(0.0, ge=0.0, description="Target runtime in seconds")
    extend_policy: str = Field("", description="How this scene extends: continuation | montage | standalone")


class ScenePlan(BaseModel):
    title: str = Field("", description="Suggested project title")
    scenes: List[ScenePlanScene] = Field(default_factory=list)
    total_runtime_s: float = Field(0.0, ge=0.0)


class ShotListOutput(BaseModel):
    """LLM output wrapper for the director pass: validated ShotSpec[]."""

    shots: List[ShotSpec] = Field(default_factory=list)


class AssetSpec(BaseModel):
    """One asset extracted from a script (Phase 2) — becomes an asset row."""

    asset_id: str = Field(
        ..., pattern=r"^[a-z0-9_]+$", description="e.g. char_maya, loc_kitchen, prop_letter"
    )
    name: str = Field(..., description="Proper name as used in the script")
    type: AssetType = AssetType.character
    description: str = Field("", description="One concise line (appearance / place / object)")


class AssetExtractionOutput(BaseModel):
    """LLM output wrapper for the asset extraction pass: validated AssetSpec[]."""

    assets: List[AssetSpec] = Field(default_factory=list)


# Single source of truth for the shots table DDL — shared by DirectorService
# (creator) and AssetService (reader/writer). Do not duplicate in services.
SHOTS_TABLE_DDL = """CREATE TABLE IF NOT EXISTS shots (
    shot_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL DEFAULT '',
    sequence_index INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    version INTEGER NOT NULL DEFAULT 1,
    shot_json TEXT NOT NULL,
    created_at REAL DEFAULT (strftime('%s','now')),
    updated_at REAL DEFAULT (strftime('%s','now'))
)"""

# Explicit "do not bind this asset to this shot" intent. Toggle-off writes a
# row; auto_bind and regeneration both honor it — a human deselection must
# survive both the reconciliation pass and a shot-list rebuild.
EXCLUSIONS_TABLE_DDL = """CREATE TABLE IF NOT EXISTS shot_asset_exclusions (
    shot_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    created_at REAL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (shot_id, asset_id)
)"""


if __name__ == "__main__":
    raise SystemExit(_main())
