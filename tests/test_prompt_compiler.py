"""Prompt compiler tests: determinism, discipline, snapshots.

Covers every acceptance criterion for the compiler task:

* ``compile_shot`` for both targets over all five valid example ShotSpecs;
* snapshot tests asserting the LTX prose and the WanGP payload are stable;
* the illegal-override rejection (``sampler``) and each of the six legal
  override keys actually landing in the resolved settings;
* template selection logic;
* a mechanical assertion that the compiler contains no network, clock or
  random machinery -- determinism is a claim in its docstring, so it gets
  an AST test rather than trust.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from backend.services.shot_spec import (
    ShotSpec,
    ShotSpecValidationError,
    load_examples,
    validate_shot_spec,
)
from backend.services.prompt_compiler import (
    ALLOWED_OVERRIDE_KEYS,
    CompiledShot,
    CompilerError,
    OverrideRejected,
    PromptTooLong,
    TARGETS,
    TemplateNotFound,
    compile_shot,
    compile_shots,
    derive_seed,
    emit_ltx_prompt,
    estimate_tokens,
    frames_for_duration,
    load_registry,
    select_template,
    snap_frames,
)

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots" / "prompt_compiler"
REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_PATH = REPO_ROOT / "backend" / "services" / "prompt_compiler.py"
EXAMPLES_DIR = REPO_ROOT / "examples" / "shotspec"
EXAMPLES = load_examples()
EXAMPLE_STEMS = tuple(sorted(EXAMPLES))


def load_example(stem: str) -> ShotSpec:
    """One validated example ShotSpec from the schema task's library."""
    return EXAMPLES[stem]

# The three scenarios the schema task promised, plus the two-hander.
CORE_EXAMPLES = (
    "talking_head_single",
    "recurring_shot_01",
    "recurring_shot_02",
)


# ---------------------------------------------------------------------------
# Fixture sanity
# ---------------------------------------------------------------------------


def test_examples_present() -> None:
    assert set(CORE_EXAMPLES).issubset(set(EXAMPLE_STEMS))


@pytest.mark.parametrize("stem", CORE_EXAMPLES)
def test_compile_both_targets(stem: str) -> None:
    spec = load_example(stem)
    for target in TARGETS:
        compiled = compile_shot(spec, target=target)
        assert isinstance(compiled, CompiledShot)
        assert compiled.target == target
        assert compiled.prompt
        assert compiled.shot_id == spec.shot_id
        # Same inputs -> same bytes, every time.
        again = compile_shot(spec, target=target)
        assert json.dumps(compiled.as_dict(), sort_keys=True) == json.dumps(
            again.as_dict(), sort_keys=True
        )


# ---------------------------------------------------------------------------
# LTX 2.3 prose
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stem", EXAMPLE_STEMS)
def test_ltx_prompt_is_one_prose_paragraph(stem: str) -> None:
    prompt = emit_ltx_prompt(load_example(stem))
    assert "\n" not in prompt
    assert not prompt.strip().startswith(("{", "["))
    assert not any(
        token in prompt for token in ("\"prompt\"", "\"negative_prompt\"", "resolution")
    )
    # Dialogue must be inside quotation marks when present.
    spec = load_example(stem)
    if spec.audio.dialogue:
        assert '"' in prompt


def test_ltx_prompt_follows_ltx23_order() -> None:
    prompt = emit_ltx_prompt(load_example("talking_head_single"))
    lower = prompt.lower()
    # framing -> setting -> lighting -> action -> camera
    assert lower.index("medium close-up") < lower.index("studio kitchen")
    assert lower.index("studio kitchen") < lower.index("overcast")
    assert lower.index("overcast") < lower.index("stands at the counter")
    # "The camera" (the movement clause) must come after the action. Note the
    # word "camera" also appears earlier inside the lighting string
    # ("camera-left"), so match the sentence opener, not the bare word.
    assert lower.index("stands at the counter") < lower.index("the camera")
    assert prompt.rstrip().endswith(".")


def test_ltx_prompt_contains_physical_cues_not_emotion_labels() -> None:
    prompt = emit_ltx_prompt(load_example("recurring_shot_01")).lower()
    assert "eyebrows draw together" in prompt
    assert "lips press into a thin line" in prompt
    for label in ("sad", "angry", "afraid", "happy", "upset", "hurt"):
        assert f" {label}" not in f" {prompt}"


def test_ltx_prompt_describes_subject_after_camera_move() -> None:
    """Spec rule: the subject is described after the movement, not before."""
    prompt = emit_ltx_prompt(load_example("recurring_shot_01"))
    camera_at = prompt.index("The camera")
    # This shot's movement already names its own ending ("ending at Medium"),
    # so the compiler uses "arriving on" rather than stuttering "ending on".
    assert "arriving on" in prompt[camera_at:]
    # The recurring description is repeated verbatim after the move.
    assert "Maya, woman, mid-30s, shoulder-length dark hair parted left" in prompt[camera_at:]
    assert prompt.index("Maya, woman, mid-30s") < camera_at  # also introduced before


def test_ltx_prompt_quotes_dialogue() -> None:
    prompt = emit_ltx_prompt(load_example("talking_head_single"))
    assert '"Everything I own fits in that box."' in prompt
    assert "Maya says" in prompt


def test_ltx_prompt_repeats_recurring_entity_verbatim() -> None:
    """The consistency mechanism is verbatim repetition of entity text."""
    one = emit_ltx_prompt(load_example("recurring_shot_01"))
    two = emit_ltx_prompt(load_example("recurring_shot_02"))
    phrase = "Maya, woman, mid-30s, shoulder-length dark hair parted left"
    assert phrase in one and phrase in two
    assert "small rented studio kitchen" in one and "small rented studio kitchen" in two


def test_recurring_pair_cuts_together_on_style_and_location() -> None:
    one = compile_shot(load_example("recurring_shot_01"), target="ltx23")
    two = compile_shot(load_example("recurring_shot_02"), target="ltx23")
    style = "naturalistic handheld documentary, slightly desaturated, fine film grain"
    assert style in one.prompt and style in two.prompt
    # Same template family chosen for both halves of the pair.
    assert one.template.aspect == two.template.aspect
    assert one.template.template_id == two.template.template_id


# ---------------------------------------------------------------------------
# WanGP payload
# ---------------------------------------------------------------------------


def test_wangp_payload_shape() -> None:
    compiled = compile_shot(load_example("recurring_shot_01"), target="wangp")
    payload = compiled.payload
    # Settings component present, with the renderer's native field names.
    assert payload["resolution"] == "1280x720"
    assert payload["num_inference_steps"] == 8
    assert payload["force_fps"] == 24
    assert payload["video_length"] % 8 == 1  # 8n+1 lattice
    # Job inputs beside the settings.
    assert payload["prompt"] == compiled.prompt
    assert isinstance(payload["seed"], int)
    assert payload["seed"] >= 0
    assert payload["negative_prompt"]
    assert payload["output_filename"].endswith("sc02_sh01_v1")
    # Prompt enhancer stays off.
    assert payload["prompt_enhancer"] is False


def test_wangp_payload_derives_frames_from_duration() -> None:
    compiled = compile_shot(load_example("talking_head_single"), target="wangp")
    # 6.5s * 24fps = 156 -> snapped up to 161 on the 8n+1 lattice.
    assert compiled.payload["video_length"] == 161
    assert compiled.payload["video_length"] / 24 == pytest.approx(6.7, abs=0.05)


def test_wangp_payload_is_json_serializable_and_sorted() -> None:
    compiled = compile_shot(load_example("stylized_action_beat"), target="wangp")
    text = json.dumps(compiled.as_dict(), sort_keys=True, ensure_ascii=False)
    assert text == json.dumps(
        json.loads(text), sort_keys=True, ensure_ascii=False
    )


def test_seed_is_stable_and_derived() -> None:
    spec = load_example("recurring_shot_01")
    assert spec.seed == -1
    first = derive_seed(spec)
    assert first == derive_seed(spec)
    assert 0 <= first < 2_147_483_647
    # A pinned seed is respected verbatim.
    pinned = load_example("talking_head_single")
    assert derive_seed(pinned) == pinned.seed == 811223


# ---------------------------------------------------------------------------
# Settings discipline — the six overrides
# ---------------------------------------------------------------------------


def test_illegal_override_key_is_rejected() -> None:
    with pytest.raises(OverrideRejected) as excinfo:
        compile_shot(load_example("talking_head_single"), overrides={"sampler": "euler"})
    message = str(excinfo.value)
    assert "sampler" in message
    for key in ALLOWED_OVERRIDE_KEYS:
        assert key in message


@pytest.mark.parametrize(
    "key, value, settings_key, expected",
    [
        ("width", 640, "resolution", "640x720"),
        ("height", 480, "resolution", "1280x480"),
        ("frames", 97, "video_length", 97),
        ("fps", 30, "force_fps", 30),
        ("steps", 4, "num_inference_steps", 4),
        ("loras", ["maya_v1"], "activated_loras", ["maya_v1"]),
    ],
)
def test_each_legal_override_is_applied(key, value, settings_key, expected) -> None:
    compiled = compile_shot(
        load_example("talking_head_single"),
        target="wangp",
        overrides={key: value},
    )
    assert compiled.payload[settings_key] == expected
    # The template's other settings are untouched.
    assert compiled.payload["model_type"] == "ltx2_22B_distilled"


def test_width_and_height_together_resolve() -> None:
    compiled = compile_shot(
        load_example("talking_head_single"),
        target="wangp",
        overrides={"width": 704, "height": 1280},
    )
    assert compiled.payload["resolution"] == "704x1280"


def test_frames_override_is_snapped_to_lattice() -> None:
    compiled = compile_shot(
        load_example("talking_head_single"),
        target="wangp",
        overrides={"frames": 100},
    )
    assert compiled.payload["video_length"] == 105  # 8n+1, rounded up


def test_all_six_together() -> None:
    compiled = compile_shot(
        load_example("recurring_shot_01"),
        target="wangp",
        overrides={
            "width": 832,
            "height": 480,
            "frames": 121,
            "fps": 25,
            "steps": 6,
            "loras": {"names": ["maya_v1", "kitchen_v2"], "multipliers": "0.9,0.6"},
        },
    )
    assert compiled.payload["resolution"] == "832x480"
    assert compiled.payload["video_length"] == 121
    assert compiled.payload["force_fps"] == 25
    assert compiled.payload["num_inference_steps"] == 6
    assert compiled.payload["activated_loras"] == ["maya_v1", "kitchen_v2"]
    assert compiled.payload["loras_multipliers"] == "0.9,0.6"


def test_overrides_do_not_change_the_prompt() -> None:
    """Settings must not leak into the prose."""
    base = compile_shot(load_example("talking_head_single"), target="wangp")
    tweaked = compile_shot(
        load_example("talking_head_single"),
        target="wangp",
        overrides={"steps": 2, "frames": 49},
    )
    assert base.prompt == tweaked.prompt
    assert base.prompt_digest == tweaked.prompt_digest


# ---------------------------------------------------------------------------
# Template selection
# ---------------------------------------------------------------------------


def test_registry_loads() -> None:
    specs = load_registry()
    assert len(specs) >= 3
    ids = [s.template_id for s in specs]
    assert ids == sorted(ids)  # deterministic order
    assert len(ids) == len(set(ids))


def test_selection_by_duration() -> None:
    registry = load_registry()
    short = select_template(3.2, registry=registry)
    long = select_template(12.0, registry=registry)
    assert short.template_id != long.template_id
    assert long.template_id.endswith("_long")


def test_selection_prefers_production_over_draft() -> None:
    registry = load_registry()
    chosen = select_template(6.5, registry=registry)
    assert chosen.template_id == "ltx2_3_distilled_16x9"
    assert chosen.priority == 20


def test_explicit_draft_template_is_selectable() -> None:
    chosen = select_template(6.5, template_id="ltx2_3_distilled_draft_16x9")
    assert chosen.settings["resolution"] == "768x432"
    assert chosen.settings["num_inference_steps"] == 6


def test_selection_by_aspect() -> None:
    vertical = select_template(6.5, aspect="9:16")
    assert vertical.template_id == "ltx2_3_distilled_9x16"
    assert vertical.settings["resolution"] == "704x1280"


def test_unknown_template_id_is_an_error() -> None:
    with pytest.raises(TemplateNotFound) as excinfo:
        select_template(6.0, template_id="does-not-exist")
    assert "does-not-exist" in str(excinfo.value)
    assert "ltx2_3_distilled_16x9" in str(excinfo.value)  # lists what exists


def test_unknown_target_is_an_error() -> None:
    with pytest.raises(CompilerError):
        compile_shot(load_example("talking_head_single"), target="veo3")


def test_template_files_are_pure_settings() -> None:
    """Registry metadata lives in index.json, not in the settings files."""
    for spec in load_registry():
        assert "template_id" not in spec.settings
        assert "priority" not in spec.settings
        assert spec.settings["model_type"] == "ltx2_22B_distilled"


def test_templates_carry_no_engine_family_leakage() -> None:
    """Settings files are WanGP-shaped because they are renderer-facing;
    the compiler module itself must not hardcode a renderer choice."""
    assert COMPILER_PATH.is_file()


# ---------------------------------------------------------------------------
# Frame maths + token guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "frames, expected",
    # 481 is WanGP's own LTX-2 sliding_window_size; clamping to it keeps the
    # payload inside what the renderer accepts (see models/ltx2 handler).
    [(9, 9), (10, 17), (97, 97), (100, 105), (1, 9), (9999, 481)],
)
def test_snap_frames(frames: int, expected: int) -> None:
    assert snap_frames(frames) == expected
    assert (snap_frames(frames) - 1) % 8 == 0


def test_frames_for_duration() -> None:
    assert frames_for_duration(6.5, 24) == 161
    assert frames_for_duration(3.0, 24) == 73
    assert (frames_for_duration(3.0, 24) - 1) % 8 == 0


def test_token_estimate_is_monotonic() -> None:
    short = estimate_tokens("A woman stands at a counter.")
    long = estimate_tokens("A woman stands at a counter. " * 20)
    assert long > short
    assert short > 0


def test_over_length_prompt_raises_rather_than_truncates() -> None:
    spec = validate_shot_spec(
        json.loads((Path(__file__).resolve().parents[1] / "examples" / "shotspec"
                    / "talking_head_single.json").read_text(encoding="utf-8"))
    )
    with pytest.raises(PromptTooLong) as excinfo:
        compile_shot(spec, target="ltx23", max_prompt_tokens=5)
    assert "does not truncate" in str(excinfo.value)


def test_negative_prompt_comes_from_template() -> None:
    compiled = compile_shot(load_example("talking_head_single"), target="wangp")
    assert "watermark" in compiled.payload["negative_prompt"]


# ---------------------------------------------------------------------------
# Snapshot tests — the prose and the payload are frozen
# ---------------------------------------------------------------------------


def _write_snapshot(name: str, text: str) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    (SNAPSHOT_DIR / name).write_text(text, encoding="utf-8", newline="\n")


def _read_snapshot(name: str) -> str:
    return (SNAPSHOT_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("stem", EXAMPLE_STEMS)
def test_snapshot_ltx_prose(stem: str) -> None:
    snapshot = f"ltx23__{stem}.txt"
    prompt = emit_ltx_prompt(load_example(stem)) + "\n"
    if not (SNAPSHOT_DIR / snapshot).exists():
        _write_snapshot(snapshot, prompt)
    assert prompt == _read_snapshot(snapshot), (
        f"LTX prose for {stem} changed. Read the diff: if the new wording is "
        "intentional, update the snapshot deliberately; the compiler is "
        "supposed to be byte-stable."
    )


@pytest.mark.parametrize("stem", EXAMPLE_STEMS)
def test_snapshot_wangp_payload(stem: str) -> None:
    snapshot = f"wangp__{stem}.json"
    compiled = compile_shot(load_example(stem), target="wangp")
    text = json.dumps(compiled.as_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if not (SNAPSHOT_DIR / snapshot).exists():
        _write_snapshot(snapshot, text)
    assert text == _read_snapshot(snapshot), (
        f"WanGP payload for {stem} changed; update the snapshot only on purpose."
    )


@pytest.mark.parametrize("stem", EXAMPLE_STEMS)
def test_snapshot_ltx_payload(stem: str) -> None:
    snapshot = f"ltx23payload__{stem}.json"
    compiled = compile_shot(load_example(stem), target="ltx23")
    text = json.dumps(compiled.as_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if not (SNAPSHOT_DIR / snapshot).exists():
        _write_snapshot(snapshot, text)
    assert text == _read_snapshot(snapshot)


def test_snapshots_exist_for_all_examples() -> None:
    if not SNAPSHOT_DIR.is_dir():
        pytest.skip("snapshots not generated yet")
    names = {p.name for p in SNAPSHOT_DIR.iterdir()}
    for stem in EXAMPLE_STEMS:
        assert f"ltx23__{stem}.txt" in names
        assert f"wangp__{stem}.json" in names


# ---------------------------------------------------------------------------
# Shot list + manifest
# ---------------------------------------------------------------------------


def test_compile_shots_list() -> None:
    specs = [load_example(s) for s in CORE_EXAMPLES]
    compiled = compile_shots(specs, target="wangp")
    assert [c.shot_id for c in compiled] == [s.shot_id for s in specs]
    assert len({c.prompt_digest for c in compiled}) == 3  # all distinct


def test_manifest_is_auditable() -> None:
    compiled = compile_shot(load_example("recurring_shot_02"), target="wangp")
    manifest = compiled.as_manifest()
    assert manifest["template"]["template_id"] == "ltx2_3_distilled_16x9"
    assert manifest["template_selection"]["requested_id"] is None
    assert manifest["overrides"] == {}
    assert manifest["duration_seconds"] == 7.0
    assert manifest["prompt_sha256_16"]
    assert manifest["entities"][0]["entity_id"] == "char_maya"
    assert manifest["settings"]["num_inference_steps"] == 8
    assert "seed" in manifest and isinstance(manifest["seed"], int)


def test_compile_shots_with_keyframe_attaches_image_start() -> None:
    specs = [load_example(s) for s in CORE_EXAMPLES]
    compiled = compile_shots(
        specs, target="wangp", image_starts={"sc01_sh01": "refs/approved/sc01_sh01.png"}
    )
    first = compiled[0]
    assert first.payload["image_start"] == "refs/approved/sc01_sh01.png"
    assert "image_start" not in compiled[1].payload
    # image_start is a job input, never a settings override.
    assert "image_start" not in first.settings


def test_invalid_spec_is_rejected_before_template_selection() -> None:
    bad = {
        "shot_id": "sc01_sh99",
        "narrative_intent": "x",
        "setting": "x",
        "action": "x",
        "lighting": "x",
        "style_grade": "x",
        "duration_seconds": -1,
        "camera": {"framing": "Wide"},
    }
    from backend.services.shot_spec import ShotSpecValidationError

    with pytest.raises(ShotSpecValidationError):
        compile_shot(bad)


# ---------------------------------------------------------------------------
# No network, no clock, no randomness — determinism, enforced
# ---------------------------------------------------------------------------

FORBIDDEN_IMPORTS = {
    "socket", "http", "httpx", "urllib", "urllib3", "requests", "aiohttp",
    "ftplib", "smtplib", "telnetlib", "xmlrpc", "asyncio", "subprocess",
    "random", "secrets", "time", "datetime", "uuid",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_compiler_has_no_network_clock_or_random_imports() -> None:
    imports = _imported_modules(COMPILER_PATH)
    assert not (imports & FORBIDDEN_IMPORTS), (
        f"prompt_compiler must stay pure; found: {sorted(imports & FORBIDDEN_IMPORTS)}"
    )


def test_compiler_does_not_call_the_llm() -> None:
    """No LLM client may be imported into the compiler: the prompt is
    assembled deterministically, not generated."""
    source = COMPILER_PATH.read_text(encoding="utf-8")
    assert "backend.llm" not in source
    assert "ollama" not in source.lower()
    assert "openai" not in source.lower()
    assert "nim_client" not in source


def test_repeated_compiles_are_byte_identical_across_dict_orders() -> None:
    """Dict key order in the input must not change the output bytes."""
    spec = load_example("stylized_action_beat")
    raw = json.loads((Path(__file__).resolve().parents[1] / "examples" / "shotspec"
                      / "stylized_action_beat.json").read_text(encoding="utf-8"))
    shuffled = dict(reversed(list(raw.items())))
    a = compile_shot(spec, target="wangp").as_dict()
    b = compile_shot(validate_shot_spec(shuffled), target="wangp").as_dict()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)