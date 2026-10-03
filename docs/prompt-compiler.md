# Prompt compiler (ShotSpec -> render payload)

`backend/services/prompt_compiler.py` turns a validated `ShotSpec` into the
thing a specific renderer actually needs to be told. The schema stays
engine-neutral; this module is where LTX 2.3 and the WanGP headless MCP path
diverge.

The compiler produces payloads only. It does not talk to the renderer
(D:\Wan2GP natively, venv `env_uv`), open a socket, or call an LLM.

## Usage

```python
from backend.services.prompt_compiler import compile_shot

payload = compile_shot(spec, target="ltx23")
payload = compile_shot(spec, target="wangp",
                       overrides={"frames": 193, "fps": 24})
```

`CompiledShot` carries `.payload` (what the renderer gets), `.settings` (the
resolved generation settings), `.overrides`, `.template`, and `.manifest`
(which template, which overrides, which derived seed, and a digest of the
prompt so two runs can be diffed without re-reading prose).

CLI:

```
python -m backend.services.prompt_compiler --validate examples/shotspec/*.json
python -m backend.services.prompt_compiler --compile examples/shotspec/talking_head_single.json
```

## The six overrides, and nothing else

Generation settings are **never** inferred. A template settings file supplies
them, and a caller may touch exactly six keys:

| override | WanGP field |
| --- | --- |
| `width`, `height` | `resolution` (`"WxH"`) |
| `frames` | `video_length` |
| `fps` | `force_fps` |
| `steps` | `num_inference_steps` |
| `loras` | `activated_loras` (+ `loras_multipliers`) |

Any other key raises `OverrideRejected`, naming the offending key and the six
legal ones. A silently dropped override is a render that looks fine and is not
the one that was asked for, so it is a hard error rather than a warning. The
allow-list lives in `backend/integrations/wangp_settings.py` and is reused, not
reimplemented, so there is one definition of "the six" in the codebase.

`loras` takes a list of names (`["film_grain"]`) or a mapping with optional
multipliers (`{"names": [...], "multipliers": "0.8"}`).

## Frame maths

Frames sit on the 8n+1 lattice LTX-2 and WanGP require, and are clamped to
`[9, 481]`. 481 is WanGP's own LTX-2 `sliding_window_size` (see
`models/ltx2/ltx2_handler.py`), so a clamped payload stays inside what the
renderer accepts. Requests round **up** to the lattice so requested duration is
never silently lost.

## Template selection

Selection is pure arithmetic over the registry at `templates/wangp/index.json`
-- aspect, duration band, target support, then priority. No LLM is consulted.
Four templates ship: 16:9 production, 16:9 long (beats over 8s), 9:16
vertical, and a low-priority 16:9 draft pass for review-loop iterations.

## Emitters

**`emit_ltx_prompt`** returns one flowing prose paragraph following the LTX 2.3
order: shot establish (framing, then setting), scene and lighting as one
coherent block, action, subject with physical cues, camera movement with the
subject described *after* the move, then audio with dialogue in quotation
marks. Present tense. Never JSON, never keyword soup, never two lighting
schemes, never emotion labels -- `expression_cues` carries physical cues only
and the ShotSpec validator is the enforcement point.

Recurring entities repeat their `description` **verbatim**. That repetition is
the consistency mechanism: two shots sharing an `entity_id` produce
byte-identical subject phrasing. There is no description lock, so there is no
description-lock text to drift.

**`emit_wangp_payload`** returns the WanGP-compatible request for the headless
MCP path: resolved settings plus per-shot job inputs (prompt, seed, negative
prompt, media anchors). The negative prompt comes from the template, never from
the model. `prompt_enhancer` stays **off** -- an enhancer rewrites the prose
that was just carefully composed, which would undo the ShotSpec.

## Determinism

Same ShotSpec + template + overrides produces byte-identical output. The seed
is a SHA-256 digest of `project_id:shot_id` (no RNG, no clock), frame counts
are integer math, and nothing is ordered by dict-iteration luck. That is what
makes the snapshot tests meaningful and the payload cacheable.

## Tests

`tests/test_prompt_compiler.py` (72 tests) covers all example ShotSpecs,
freezes the prose and both payloads in `tests/snapshots/prompt_compiler/`,
asserts each of the six overrides applies and that illegal keys are rejected,
and statically asserts the module imports no network, clock, random, or LLM
dependency.

Run with the repo venv:

```
.venv/bin/python -m pytest tests/test_prompt_compiler.py -q
```

Note: the wider suite includes golden integration tests that make a live local
LLM (Ollama) call and hang without one -- run them with `-k "not golden"`.