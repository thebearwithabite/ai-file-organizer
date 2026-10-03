# ShotSpec

**ShotSpec is engine-neutral. It is the interface every downstream stage compiles
against, and it names no renderer.**

Per-engine payloads (LTX 2.3 prose, WanGP payload, anything added later) are
produced by the **prompt compiler** -- a separate task (`t_1d748aed`). The
compiler takes a validated `ShotSpec` plus a template name and a bounded set of
overrides, and emits the payload for one engine. Nothing in this schema needs to
change when an engine is added, replaced, or removed.

## What "engine-neutral" means here, concretely

| Concern | Where it lives | Not here |
|---|---|---|
| Clip length limits | compiler / template settings | `duration_seconds` is a positive number with **no cap encoded** |
| Prompt format (prose vs JSON vs keyword list) | compiler | the schema is structured data, never a prompt string |
| Sampler, steps, resolution, loras | compiler | only six overrides exist downstream; none are schema fields |
| Consistency | explicit entity fields | no description-lock shorthand |
| Cloud/local routing | nowhere in the schema | no engine, provider, or endpoint names |

`tests/test_shot_spec.py` enforces this mechanically: it greps the module and
the emitted JSON Schema for engine names and fails the suite if any appear.

## Fields

Required creative core:

- `shot_id` -- `sc##_sh##`
- `narrative_intent` -- what the shot must accomplish dramatically
- `setting` -- where and when
- `action` -- the visible action, one clear beat
- `lighting` -- one coherent description, never conflicting sources
- `style_grade` -- look / grade
- `duration_seconds` -- positive seconds, **no upper bound in the schema**
- `camera` -- `framing` (required), `movement`, `lens_feel`

Structure:

- `entities[]` -- `entity_id` (stable slug, `^[a-z0-9_]+$`), `name`, `kind`
  (character/location/prop/style), `description`, `reference_images[]`,
  `expression_cues`
- `audio` -- `dialogue`, `delivery`, `ambience`, `sfx`
- `assets[]` -- `asset_id`, `type`, `weight`, plus optional `lora_path`,
  `trigger_token`, `ref_image` (Phase 2 production bindings)
- `sequence_index`, `status`, `version`, `project_id`
- `seed` -- RNG seed, `-1` means unset and is derived at compile time
- `notes` -- free-form escape hatch

## Consistency without a lock

A subject recurring across shots repeats the **same** `entity_id`, `name`,
`description`, and `reference_images` in each shot. That repetition is the whole
mechanism. `description` is the stable phrasing the compiler carries forward;
`expression_cues` is per-shot and physical only.

`expression_cues` rejects emotion labels (`EMOTION_LABELS`): write "eyebrows draw
together, lips press into a thin line", never "looks happy". Video models render
physical action, not adjectives. Dispositional words that double as physical
demeanor (serious, calm, determined) are allowed.

## Validation

`backend/services/shot_spec.py`:

- `validate_shot_spec(payload, source=...)` -> `ShotSpec`
- `load_shot_spec(path)` -> `ShotSpec`
- `validate_shot_specs(payloads)` -> `list[ShotSpec]`
- `load_examples()` -> `{stem: ShotSpec}`
- `shotspec_json_schema()` / `write_json_schema()`

Failures raise `ShotSpecValidationError` with `.errors`, one
`{"path", "reason", "type"}` per problem, so both humans and the LLM repair loop
get a field path:

```
invalid ShotSpec (examples/shotspec/invalid/negative_duration.json):
  - duration_seconds: Input should be greater than 0
  - camera.framing: String should have at least 1 character
  - entities[0].entity_id: String should match pattern '^[a-z0-9_]+$'
  - entities[0].expression_cues: Value error, expression_cues must be physical
    cues only, no emotion labels; found: happy
```

Unknown keys are **rejected** (`extra="forbid"`), so a stale shape -- an embedded
`generation` block, a cloud `engine` field -- can never silently re-enter.

## Artifacts

- Pydantic models: `backend/services/shot_spec.py`
- JSON Schema: `schemas/shotspec.schema.json`
  (regenerate: `python -m backend.services.shot_spec --emit-schema`)
- Examples: `examples/shotspec/` -- `load_examples()` loads the valid set
- Tests: `tests/test_shot_spec.py`

## Examples

| File | Covers |
|---|---|
| `talking_head_single.json` | single-subject talking shot |
| `recurring_shot_01.json` / `recurring_shot_02.json` | multi-shot scene, one recurring character (`char_maya` identical across both) |
| `stylized_action_beat.json` | stylized action beat, short and graphic |
| `over_the_shoulder_two_shot.json` | two-handers, 11s -- legal despite exceeding typical clip limits |
| `invalid/negative_duration.json` | deliberately malformed; must fail with field paths |

## CLI

```bash
python -m backend.services.shot_spec --emit-schema
python -m backend.services.shot_spec --validate examples/shotspec/*.json
```
