"""ShotSpec schema tests -- engine-neutral contract (kanban t_fe486f95).

Runs anywhere: no LLM, no network, no GPU.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.services.shot_spec import (
    EMOTION_LABELS,
    EXAMPLES_DIR,
    SCHEMA_PATH,
    AssetBinding,
    AudioSpec,
    CameraSpec,
    EntityRef,
    ShotSpec,
    ShotSpecValidationError,
    example_paths,
    load_examples,
    load_shot_spec,
    shotspec_json_schema,
    validate_shot_spec,
)

# Names that must never appear in the schema or its JSON Schema.
FORBIDDEN_ENGINE_TOKENS = (
    "veo", "kling", "sora", "runway", "ltx", "ltx23", "ltx_23", "wan2gp",
    "wangp", "wan_2", "comfy", "comfyui", "hailuo", "pika", "luma", "pika_labs",
    "openai", "anthropic", "gemini", "deepseek", "ollama", "vllm", "nim_",
    "diffusers", "stable_diffusion", "flux",
)


# ---------------------------------------------------------------------------
# Engine neutrality -- mechanical, not aspirational
# ---------------------------------------------------------------------------


def test_schema_module_contains_no_engine_names():
    """The schema names no renderer. The compiler (separate task) does that."""
    src = (Path(__file__).resolve().parents[1] / "backend/services/shot_spec.py").read_text(
        encoding="utf-8"
    )
    body = src.split("class ShotSpecValidationError")[0]  # module docs + models
    lowered = body.lower()
    hits = [t for t in FORBIDDEN_ENGINE_TOKENS if t in lowered]
    # The docstring legitimately *describes* neutrality; only flag token use
    # outside prose, which we detect by checking quoted identifiers/paths.
    code_only = re.sub(r'""".*?"""', "", body, flags=re.S)
    code_only = code_only.replace("'", " ").replace('"', " ").lower()
    hits = [t for t in FORBIDDEN_ENGINE_TOKENS if t in code_only]
    assert hits == [], f"engine names leaked into schema code: {hits}"


def test_emitted_json_schema_contains_no_engine_names():
    blob = json.dumps(shotspec_json_schema()).lower()
    hits = [t for t in FORBIDDEN_ENGINE_TOKENS if t in blob]
    assert hits == [], f"engine names leaked into JSON Schema: {hits}"


def test_schema_has_no_duration_cap():
    """duration_seconds: positive, but the schema encodes no upper bound."""
    s = shotspec_json_schema()
    dur = s["properties"]["duration_seconds"]
    numeric_bounds = [k for k in ("maximum", "exclusiveMaximum") if k in dur]
    assert numeric_bounds == [], f"duration_seconds encodes a cap: {numeric_bounds}"
    assert dur.get("exclusiveMinimum") == 0, "duration_seconds must be > 0"


def test_no_description_lock_or_generation_block():
    """Consistency is explicit entity data; render settings live at compile time."""
    s = shotspec_json_schema()
    props = set(s["properties"])
    for banned in ("generation", "engine", "template", "prompt", "description_lock",
                   "overrides", "template_id", "comfy_workflow_id", "aspect_ratio"):
        assert banned not in props, f"engine-specific field {banned!r} in ShotSpec"
    assert "entities" in props, "consistency must be expressed via entities"
    assert "notes" in props, "free-form escape hatch missing"


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------


def test_examples_library_is_present():
    names = {p.stem for p in example_paths()}
    assert {
        "talking_head_single",
        "recurring_shot_01",
        "recurring_shot_02",
        "stylized_action_beat",
        "over_the_shoulder_two_shot",
    } <= names, f"missing examples, got {sorted(names)}"


def test_all_valid_examples_pass():
    specs = load_examples()
    assert len(specs) >= 5
    for stem, spec in specs.items():
        assert isinstance(spec, ShotSpec), stem


def test_required_scenarios_are_covered():
    specs = load_examples()

    # single-subject talking shot: dialogue present, one character entity
    talk = specs["talking_head_single"]
    assert talk.audio.dialogue.strip(), "talking shot must carry dialogue"
    assert sum(1 for e in talk.entities if e.kind.value == "character") == 1

    # multi-shot scene with one recurring character
    a, b = specs["recurring_shot_01"], specs["recurring_shot_02"]
    assert a.shot_id != b.shot_id
    maya_a = next(e for e in a.entities if e.entity_id == "char_maya")
    maya_b = next(e for e in b.entities if e.entity_id == "char_maya")
    assert maya_a.description == maya_b.description, (
        "recurring entity must repeat its description verbatim -- that is the "
        "consistency mechanism"
    )
    assert maya_a.reference_images == maya_b.reference_images

    # stylized action beat
    act = specs["stylized_action_beat"]
    assert act.duration_seconds < 4.0
    assert act.camera.framing.lower().startswith("low-angle")


def test_duration_examples_prove_no_cap():
    specs = load_examples()
    durations = [s.duration_seconds for s in specs.values()]
    assert max(durations) > 8.0, (
        "library must include a shot longer than the retired 8s cap, proving "
        "the schema no longer encodes one"
    )


def test_malformed_example_fails_with_field_paths():
    bad = EXAMPLES_DIR / "invalid" / "negative_duration.json"
    assert bad.is_file(), f"missing malformed fixture: {bad}"
    with pytest.raises(ShotSpecValidationError) as exc:
        load_shot_spec(bad)

    paths = {e["path"] for e in exc.value.errors}
    assert "duration_seconds" in paths
    assert "camera.framing" in paths
    assert "entities[0].entity_id" in paths
    assert "entities[0].expression_cues" in paths

    # every entry is actionable: path + human-readable reason
    for e in exc.value.errors:
        assert e["path"] and e["reason"] and e["type"]

    text = str(exc.value)
    assert "duration_seconds:" in text
    assert "greater than 0" in text
    assert str(bad) in text, "error must name the offending source"


# ---------------------------------------------------------------------------
# Validation behaviour
# ---------------------------------------------------------------------------


def test_valid_payload_roundtrips():
    spec = validate_shot_spec(
        {
            "shot_id": "sc01_sh01",
            "narrative_intent": "Maya finds the letter.",
            "setting": "Kitchen at dawn.",
            "action": "She picks it up with both hands.",
            "lighting": "soft window light from the left",
            "style_grade": "naturalistic documentary",
            "duration_seconds": 6.0,
            "camera": CameraSpec(framing="Medium Close-Up").model_dump(),
            "entities": [
                EntityRef(
                    entity_id="char_maya",
                    name="Maya",
                    description="woman, mid-30s, dark hair",
                ).model_dump()
            ],
            "notes": "free-form escape hatch works",
        }
    )
    assert spec.duration_seconds == 6.0
    assert spec.notes == "free-form escape hatch works"


@pytest.mark.parametrize("bad_id", ["shot1", "SC01_SH01", "sc01sh01", "sc-01-sh-01"])
def test_shot_id_pattern_enforced(bad_id):
    with pytest.raises(ShotSpecValidationError) as exc:
        validate_shot_spec(
            {
                "shot_id": bad_id,
                "narrative_intent": "x",
                "setting": "x",
                "action": "x",
                "lighting": "x",
                "style_grade": "x",
                "duration_seconds": 1.0,
                "camera": {"framing": "Medium"},
            }
        )
    assert "shot_id" in {e["path"] for e in exc.value.errors}


def test_zero_and_negative_duration_rejected():
    base = {
        "shot_id": "sc01_sh01",
        "narrative_intent": "x",
        "setting": "x",
        "action": "x",
        "lighting": "x",
        "style_grade": "x",
        "camera": {"framing": "Medium"},
    }
    for bad in (0, -0.5, -8.0):
        with pytest.raises(ShotSpecValidationError) as exc:
            validate_shot_spec({**base, "duration_seconds": bad})
        assert "duration_seconds" in {e["path"] for e in exc.value.errors}


def test_large_durations_are_accepted():
    """No cap: 40 seconds is perfectly valid ShotSpec territory."""
    spec = validate_shot_spec(
        {
            "shot_id": "sc01_sh01",
            "narrative_intent": "x",
            "setting": "x",
            "action": "x",
            "lighting": "x",
            "style_grade": "x",
            "duration_seconds": 40.0,
            "camera": {"framing": "Medium"},
        }
    )
    assert spec.duration_seconds == 40.0


def test_unknown_keys_rejected():
    """A stale engine block cannot silently re-enter the schema."""
    with pytest.raises(ShotSpecValidationError) as exc:
        validate_shot_spec(
            {
                "shot_id": "sc01_sh01",
                "narrative_intent": "x",
                "setting": "x",
                "action": "x",
                "lighting": "x",
                "style_grade": "x",
                "duration_seconds": 1.0,
                "camera": {"framing": "Medium"},
                "generation": {"engine": "something", "template_id": "x"},
            }
        )
    assert "generation" in str(exc.value)


def test_expression_cues_reject_emotion_labels():
    base = {
        "shot_id": "sc01_sh01",
        "narrative_intent": "x",
        "setting": "x",
        "action": "x",
        "lighting": "x",
        "style_grade": "x",
        "duration_seconds": 1.0,
        "camera": {"framing": "Medium"},
    }
    for emotion in sorted(EMOTION_LABELS):
        payload = json.loads(json.dumps(base))
        payload["entities"] = [
            {
                "entity_id": "char_maya",
                "name": "Maya",
                "description": "woman",
                "expression_cues": f"eyes widen, looks {emotion}",
            }
        ]
        with pytest.raises(ShotSpecValidationError) as exc:
            validate_shot_spec(payload)
        assert "entities[0].expression_cues" in {e["path"] for e in exc.value.errors}
        assert "no emotion labels" in str(exc.value)


def test_expression_cues_allow_physical_cues():
    spec = validate_shot_spec(
        {
            "shot_id": "sc01_sh01",
            "narrative_intent": "x",
            "setting": "x",
            "action": "x",
            "lighting": "x",
            "style_grade": "x",
            "duration_seconds": 1.0,
            "camera": {"framing": "Medium"},
            "entities": [
                {
                    "entity_id": "char_maya",
                    "name": "Maya",
                    "description": "woman",
                    "expression_cues": "jaw tightens, breath held, gaze drops to the paper",
                }
            ],
        }
    )
    assert "jaw tightens" in spec.entities[0].expression_cues


def test_invalid_json_is_actionable():
    with pytest.raises(ShotSpecValidationError) as exc:
        validate_shot_spec("{not json", source="<inline>")
    assert exc.value.errors[0]["path"] == "$"
    assert "invalid JSON" in exc.value.errors[0]["reason"]


def test_asset_weight_bounds():
    with pytest.raises(Exception):
        AssetBinding(asset_id="x", type="character", weight=1.5)
    with pytest.raises(Exception):
        AssetBinding(asset_id="x", type="character", weight=-0.1)


def test_audio_and_camera_are_structured_not_prompt_strings():
    """Audio/camera are nested structures -- the schema is data, not prose."""
    s = shotspec_json_schema()
    assert "properties" in s["$defs"]["AudioSpec"]
    assert {"framing", "movement", "lens_feel"} <= set(s["$defs"]["CameraSpec"]["properties"])
    assert isinstance(AudioSpec().model_dump(), dict)


def test_schema_artifact_on_disk_matches_model():
    if not SCHEMA_PATH.is_file():
        pytest.skip("schema artifact not emitted yet")
    on_disk = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert set(on_disk["properties"]) == set(shotspec_json_schema()["properties"])
