# LLM Router — local-first director intelligence (PROMPT-MACHINE-DIRECTIVE v1.2)

`backend/services/llm_router.py` is the routing layer every director/QA LLM
job goes through. Local-first, cloud-fallback, functional with no cloud key.

| decision | when | notes |
|---|---|---|
| `local` | render state idle | `OllamaClient` (qwen3.5:4b) is PRIMARY |
| `overflow-cloud` | the renderer reports an ACTIVE render job | VRAM reserved -> route to cloud instead of blocking/OOM |
| `fallback-cloud` | local failed in flight (down, context limit) | one transport retry on the cloud client |
| `degraded` | local busy/unreachable AND no cloud key | `DegradedRoutingError`, fail-fast, both causes in the message |

Order is never inverted: cloud is fallback/overflow only.

## Division of labour

The router **routes**; it does not validate. Parse/validate/repair against the
live ShotSpec schema lives in exactly one place — `backend/llm/structured_output.py`
(`enforce_structured`) — and the router composes it. This matters: two copies of
that contract drift, and the drift is invisible until a repair prompt names
`shots.0.shot_id` in one place and `shots[0].shot_id` in the other.
`tests/test_llm_router.py` guards the single-implementation property with an AST
check.

Transport exceptions are the router's alone. A schema violation is **not** a
transport failure and never changes provider: re-asking a different vendor hides
a malformed reply behind that model's guesswork.

## Render state — from the renderer, never a VRAM guess

The router asks the renderer's own job state. Any object exposing
`render_in_flight()` satisfies the protocol structurally, so the renderer client
goes in directly — no adapter, no flag bookkeeping:

```python
from backend.services.llm_router import LLMRouter, build_cloud_client
from backend.integrations.wangp_client import WangPClient

cloud, note = build_cloud_client()                  # (None, reason) when keyless
router = LLMRouter(
    local=OllamaClient(model=DIRECTOR_LOCAL_FALLBACK_MODEL),
    cloud=cloud,
    render_state=wangp_client,                      # <- the renderer itself
    cloud_note=note if cloud is None else "",
)

svc = DirectorService(render_state=wangp_client)    # or wire once at startup
```

Three states, three behaviours:

| render state | router does |
|---|---|
| object wired, answers | trusts it — never samples VRAM, GPU load, or processes |
| `render_state=None` | assumes idle, and **says so** in the reason string ("render-state provider not wired; assumed idle"), so keyless local runs keep working without pretending to know the GPU |
| wired but **raises** | fails **safe to busy** — an unanswerable probe is not evidence of an idle GPU, and an OOM beside a live render costs far more than one unnecessary cloud call |

`ExplicitRenderFlag` remains for callers that want to bracket a render window by
hand; `CallableRenderState(predicate)` adapts any zero-arg predicate.

## Degradation

Busy render + no cloud key is a fail-fast, not a slow local call: the VRAM
belongs to the render, and there is no cloud path to try. `DegradedRoutingError`
names both causes and the actionable fix —

```
local inference unavailable (VRAM is occupied by an active render job — render in
flight per renderer job state; local inference skipped to avoid blocking or OOM-ing
the render); cloud fallback unavailable (no fallback cloud key is configured ...)
```

`local_reason` / `cloud_reason` are available as structured attributes, so a
caller can branch without string-matching. On the overflow route the cloud's
failure is never attributed to local: local was not called and must not be
blamed for it.

## Records

Every request emits exactly one record — a log line and a metrics entry:

```
llm.route decision=overflow-cloud job=director.shot_list provider=nim model=... \
  latency_ms=12.3 prompt_tokens=812 completion_tokens=640 attempts=1 attempt=primary \
  ok=True reason='...' error=''
```

`router.metrics.snapshot()` -> `{requests, counts, tokens, last}`.

Token counts are **summed across every real provider call in the request**,
including a repair retry, because `LLMProvider.last_usage` only holds the most
recent call and a per-request record that bills one of two calls understates
cost. Providers that report nothing (`None`, missing attribute, non-numeric
string) contribute zero — a missing count must never crash the director pass.
`attempts` always equals the number of provider calls actually made.

## Keys

Cloud keys are read from the process environment only: `build_cloud_client()`
looks at `NIM_API_KEY` and nothing else. `LLMRouter.from_env()` takes an optional
`env=` mapping so tests inject one instead of mutating the real environment.
`DirectorService` enforces the consent gate by *not building* a cloud client when
`allow_cloud_script=False`, so there is no cloud path to call even if a key is
present in the environment.

Keys are never logged, never written to disk, never placed on a subprocess
environment. A whitespace-only value is treated as no key: sending it as a bearer
token produces a confusing 401 instead of the actionable "no fallback cloud key"
message.

Keyless runs: `build_cloud_client()` returns `(None, reason)` and every request
either uses the local model or raises the actionable degraded error.