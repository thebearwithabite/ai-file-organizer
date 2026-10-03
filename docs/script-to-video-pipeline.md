# Script-to-Video Pipeline

The end-to-end path PROMPT-MACHINE-DIRECTIVE v1.2 asks for:

```
script -> ShotSpec[] -> compiled payload -> WanGP render -> artifact
                                                      |
                                              review + bounded retry
                                                      |
                                                run manifest
```

This document is the operator's guide. For what each stage decides and why,
see the module docstrings — `backend/services/pipeline.py` has the wiring
map.

## The one-line version

```bash
# from the WSL repo root, with the renderer already running on Windows
python scripts/pipeline_live_run.py --script examples/scripts/sample_dawn.md \
    --shots examples/shotspec_pipeline.json --out runs/
```

Everything else in this document is detail about what that does when it goes
wrong.

## Who owns what

| Decision | Owner | Why not here |
|---|---|---|
| script → ShotSpec[] | `DirectorService` via `LLMRouter` | owns the knowledge seeds and the degrade-to-queue behaviour |
| ShotSpec → payload | `prompt_compiler` | owns the template registry and the six-override rule |
| payload → job | `WangPClient` | owns the MCP surface, v1/v2 detection, path translation |
| pass/fail + revisions | `review_loop` | owns the retry ceiling |
| audit record | `run_manifest` | owns reproducibility and diffing |

The pipeline module is deliberately thin. The one piece of real logic it owns
is `effective_overrides()` — see below.

## The seam that needs explaining

`compile_shot()` derives `frames` from `duration_seconds` *inside* the compile.
Its returned `overrides` therefore holds only what the caller asked for —
frequently `{}`. But the payload it returns carries the derived frame count,
and `WangPClient.submit_render()` re-derives the expected settings from
`ResolvedSettings` and rejects any payload that deviates.

Hand the client the caller-overrides verbatim and **every shot whose duration
isn't already the template's frame count fails** the boundary guard:

```
TemplateDeviationError: payload changes template field 'video_length' outside
the six allowed overrides (width, height, frames, fps, steps, loras):
template=121 payload=169
```

So the integration recovers the *effective* overrides by diffing the template
against the compiled settings. That avoids duplicating the compiler's
arithmetic — a second implementation of the frames derivation is a second
source of truth waiting to drift. `TestCompilerRendererSeam` pins all of this,
including a test asserting the naive wiring *still* fails, so a future change
that quietly makes the seam unnecessary will be noticed.

## The review loop

### The retry ceiling

At most **2** automated re-compile + re-render retries per shot, then the shot
surfaces to the operator. The ceiling is stated three ways on purpose:

1. `review_loop.MAX_RETRIES` is a module constant, and the constructor
   **raises** `RevisionBudgetExhausted` for anything larger. A caller cannot
   buy more iterations by passing a bigger number.
2. Every attempt is recorded, including the one that spends the budget, so the
   count can be asserted after the fact.
3. `run()` is a `for` over a precomputed range with an inner `break` — two
   independent guards. `tests/test_review_loop_mutations.py` breaks each in
   turn and asserts the acceptance test catches it. A test that cannot fail
   proves nothing, so this module checks that the test bites.

### What fails, and what doesn't

| Situation | Behaviour | Why |
|---|---|---|
| artifact missing / truncated / frozen | fail → retry | the review loop's job |
| no actionable revision available | surface immediately | re-rendering an unmodified shot reproduces the same artifact and wastes GPU |
| render error (connection refused) | surface immediately | a transport failure is not a review failure; retrying burns budget without ever producing something to judge |
| reviewer unreachable | **fail the shot** | silence is not a pass |
| shot passes | done | |

That last row group is the important one. A pipeline whose critic is
unavailable must not quietly approve everything.

### Two reviewers

`ArtifactProbeReviewer` (the default) judges from measurable facts: does the
file exist, is it non-trivial, does its duration match the ShotSpec, are its
frames distinct rather than a frozen still. No LLM, no network, fully
deterministic — it is the CI-safe default and the one that proves the ceiling
terminates.

`CritiqueReviewer` routes an LLM critique through the router (so it obeys the
same local-first / cloud-overflow rules as the director pass). It requires
pre-sampled frame observations: a text model cannot see an mp4, and
pretending otherwise produces a confident critique of nothing.

ffprobe is optional. When absent, the probe reviewer degrades to the
filesystem checks it can make **and says so in the verdict** rather than
quietly reporting a pass it did not earn.

### Revisions are bounded edits, not prompt appends

A revision is a narrow set of ShotSpec fields (`action`, `lighting`,
`camera.framing`, ...) plus overrides restricted to the permitted six.
Appending a reviewer's free text to a prompt is how a review loop silently
becomes a second director; anything outside the allowed set is dropped rather
than passed on, so a hallucinated override key dies in the loop instead of at
the compiler's boundary check.

A revision preserves `shot_id`, seed, and asset bindings, per the directive.

## The run manifest

`runs/<run_id>.json`. Records the ShotSpec, the template, the overrides, the
routing decisions, the render job ids, and the artifact paths — in both the
WSL and native Windows spellings.

```bash
# did anything change between two runs?
python -m backend.services.pipeline diff runs/run_a.json runs/run_b.json

# just the single-value answer
python -m backend.services.pipeline diff runs/run_a.json runs/run_b.json --fingerprint
```

Volatile fields (timestamps, job ids, artifact paths, latencies) are excluded
from the diff by default, because the renderer stamps a timestamp into every
filename. So two runs of the same script diff clean, and a changed prompt
digest shows up immediately. `--include-volatile` shows everything.

The manifest refuses to serialize anything credential-shaped, so a future
field cannot quietly start leaking a key.

## Running it

### Dry run — no renderer, no GPU

```bash
python -m backend.services.pipeline run --script examples/scripts/sample_dawn.md --dry-run
```

Runs the director pass, compiles every shot, prints the prose. Needs a local
LLM but no renderer and no cloud key.

### Against a live renderer

Start the renderer on the **Windows** side first:

```
cd C:\Users\thebe\AppData\Roaming\wan2gp-desktop\Wan2GP\Wan2GP
.\env_uv\Scripts\python.exe .\wgp.py --mcp --mcp-api-version 1 \
    --mcp-transport streamable-http --mcp-host 127.0.0.1 --mcp-port 8899
```

Then from WSL:

```bash
# preflight: does the script even work? exits 0 and prints SKIP if no renderer
python scripts/pipeline_live_run.py --script examples/scripts/sample_dawn.md

# the real thing, from a fixed shot list (skips the director LLM)
python scripts/pipeline_live_run.py \
    --script examples/scripts/sample_dawn.md \
    --shots examples/shotspec_pipeline.json \
    --out runs/ --require
```

`--require` turns an unreachable renderer into exit 2 instead of a skip. A
"successful" integration run that silently skipped is worse than no run at
all.

Exit codes: `0` all shots passed and artifacts exist · `1` a shot needs an
operator, or an artifact the renderer claimed is not on disk · `2` the run
could not start.

### Why the live script verifies artifacts

A renderer that returns a path it never wrote is the most common way a
pipeline like this reports a false win. `pipeline_live_run.py` stats every
artifact before reporting success, and
`test_live_run_detects_a_phantom_artifact` proves the check fires against a
renderer that reports paths without writing them.

## Keyless operation

The full suite passes with **no cloud key** and **no renderer running**:

```bash
env -u NIM_API_KEY -u DEEPSEEK_API_KEY .venv/bin/python -m pytest \
    tests/test_pipeline.py tests/test_pipeline_integration.py \
    tests/test_review_loop_mutations.py -q
```

`PipelineConfig.for_tests()` wires a scripted local provider and a mocked MCP
transport; every collaborator is injectable. The production objects are
exercised — only the two external edges (the LLM, the renderer) are
substituted.

## Safety properties, and how they are enforced

| Property | Enforcement |
|---|---|
| Never deletes `D:\Wan2GP` / `/mnt/d/wan2gp` | AST check over every pipeline module; `core.path_guard.assert_deletable`; a test asserting the guard is consulted *before* any write in `RunManifest.save` |
| Only the manifest is written | per-call-site AST allowance; the live script itself writes no files directly |
| No shell-out in the render path | AST check for `subprocess`/`shutil` imports; `reviewers.py` is the sole exception and must use a fixed argv with no `shell=True` |
| No secrets in manifests | `assert_no_secrets` on every serialize |
| Retry ceiling | constructor raises; two independent loop guards; mutation tests |

Note the AST checks match *dotted* targets and the receiver of a
filesystem-mutating method, not bare names. A naive name match flags
`"a-b".replace("-", "_")` — and a check that cries wolf teaches its reader to
ignore it.

## Known gaps

- **The live render has not been executed against the real renderer on this
  box.** The integration tests drive the documented path against the recorded
  MCP fixtures with real files written to temp dirs. The GPU-side run is an
  operator action; see the procedure above.
- `CritiqueReviewer` is implemented and schema-validated but is not the default
  reviewer, and no test drives a real model through it.
- Review state is per-run in the manifest; it is not yet persisted to SQLite
  for restart-survival (directive Phase 4 item 2, owned by the UI/DB lane).