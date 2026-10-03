# WanGP renderer client (MCP over streamable-http)

`backend/integrations/wangp_client.py` is the orchestrator's only door to the
renderer. It speaks MCP (JSON-RPC 2.0) to a headless WanGP instance over the
`streamable-http` transport, discovers the live tool surface at connect time,
submits renders under the template + six-override discipline, polls jobs, and
returns artifact paths translated for WSL.

WanGP is by deepbeepmeep (https://github.com/deepbeepmeep/WanGP). WanGP's
terms require any integrating product to disclose its use of WanGP in both
its UI and its documentation — the UI credit ships with Prompt Machine
(Phase 4); this file is the documentation half.

## Launch the renderer (Windows side)

```bat
cd C:\Users\thebe\AppData\Roaming\wan2gp-desktop\Wan2GP\Wan2GP
.\env_uv\Scripts\python.exe .\wgp.py --mcp --mcp-api-version 1 ^
    --mcp-transport streamable-http --mcp-host 127.0.0.1 --mcp-port 8899
```

- The live, launcher-managed install is the path above. `D:\Wan2GP` is the
  retired fork that holds the model stores (ckpts/loras/outputs). Never edit
  WanGP source — the launcher overwrites it on update.
- `--mcp-api-version 1` pins the historical tool contract
  (`wangp_generate` / `wangp_get_job` / `wangp_cancel_job`, async by default).
  The v2 default surface is also supported (see "API flavors" below).
- The desktop launcher's *Configurable launch args* accepts the same flags if
  you prefer launching headless from the app.
- Add `--mcp-async` if you run the v2 surface and want true async submit
  (`wait=false`); without it v2 rejects `wait=false` before submission and the
  client parks with `timeout_s=0` + polls instead.

## WSL2 → Windows networking

The orchestrator is in WSL2; the renderer is native Windows. Two topologies:

1. **Mirrored networking (recommended).** `%UserProfile%\.wslconfig`:

   ```ini
   [wsl2]
   networkingMode=mirrored
   ```

   Then `wsl --shutdown` (kills everything running in WSL — schedule it) and
   restart. `127.0.0.1:8899` now resolves identically from both sides, the
   server can stay bound to loopback, and no firewall rule is needed.
   Verify: `curl -s -m 2 http://127.0.0.1:8899/mcp/ -X POST -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'`

2. **NAT mode (current default until mirrored is enabled).** WSL cannot reach
   the Windows loopback; it reaches the host at the default-gateway IP of its
   virtual network. Bind the server to that specific Windows-side adapter
   address — never `0.0.0.0`:

   ```bat
   .\env_uv\Scripts\python.exe .\wgp.py --mcp --mcp-api-version 1 ^
       --mcp-transport streamable-http --mcp-host 172.24.16.1 --mcp-port 8899
   ```

   From WSL: `ip route | grep default` gives the same address; export it as
   `WANGP_MCP_HOST` for the client. This exact path is verified — the
   recorded fixtures under `tests/fixtures/wangp_mcp/` were captured live at
   `http://172.24.16.1:8899/mcp/` (2026-08-09).

   Firewall: inbound TCP 8899 on the WSL virtual adapter. If a fresh reboot
   makes the connection refused/reset, re-check the gateway IP (it changes)
   and, if needed, add a scoped rule:

   ```bat
   netsh advfirewall firewall add rule name="WanGP MCP WSL" dir=in action=allow ^
       protocol=TCP localport=8899 remoteip=172.24.16.0/20 profile=any
   ```

   Scope `remoteip` to the WSL subnet so the port never appears on the LAN.

Client-side configuration (all optional; defaults shown):

| Env var | Meaning | Default |
|---|---|---|
| `WANGP_MCP_HOST` | renderer host | `127.0.0.1` |
| `WANGP_MCP_PORT` | renderer port | `8899` |
| `WANGP_MCP_ENDPOINT` | MCP path | `/mcp/` |
| `WANGP_MCP_CONNECT_TIMEOUT_S` | initialize/tools-list timeout | `10` |
| `WANGP_MCP_REQUEST_TIMEOUT_S` | per-request timeout | `60` |
| `WANGP_MCP_SUBMIT_TIMEOUT_S` | generate submit timeout | `120` |
| `WANGP_MCP_POLL_INTERVAL_S` | poll cadence | `2` |
| `WANGP_MCP_POLL_TIMEOUT_S` | render wait budget | `3600` |
| `WANGP_MCP_PARK_TIMEOUT_S` | `timeout_s` used when async is disabled | `0` |
| `WANGP_MCP_RETRY_ATTEMPTS` / `_BACKOFF_S` / `_BACKOFF_MAX_S` | retry policy for idempotent calls | `3 / 0.5 / 8` |
| `WANGP_MCP_DIR` | renderer dir used in help text | live install path |

## API flavors (auto-detected, never assumed)

`tools/list` is inspected at connect time:

- **v1** (`--mcp-api-version 1`): `wangp_generate(source=...)`, default
  `wait=false` → submit returns a `job_id` immediately; poll
  `wangp_get_job(job_id)`; `wangp_cancel_job(job_id)`. Model tools:
  `wangp_list_models`, `wangp_get_default_settings`. This is the pinned
  contract used by the pipeline.
- **v2** (server default): `wangp_generate(settings=...)`; jobs move under
  `wangp_session(action="get_job"|"cancel_job")`; defaults via
  `wangp_model(model_type, action="defaults")`. `wait=true` by default, and
  `wait=false` is rejected unless the server was started with `--mcp-async`;
  the client then parks with `timeout_s=0` (a timeout never cancels the job)
  and polls.

The client surfaces both behind one API: `submit_render` → `wait_for_job` /
`render`.

## Template discipline (the six overrides)

Settings are never composed ad hoc. The caller supplies a template (a WanGP
settings JSON — e.g. the renderer's own pristine defaults from
`get_default_settings`, or a checked-in template file) plus overrides limited
exactly to:

```
width, height  -> resolution "WxH"
frames         -> video_length
fps            -> force_fps
steps          -> num_inference_steps
loras          -> activated_loras (+ optional loras_multipliers)
```

`enforce_bounded_settings` runs at the transport boundary — before any HTTP
call — and rejects: unknown override keys, payloads that change any other
template field, and payload fields that are neither template fields nor
recognized per-shot job inputs (`prompt`, `seed`, `image_start`, `image_refs`,
`audio_guide`, ...). A rejected request reaches the renderer never.

```python
from backend.integrations import WangPClient, WangPMCPConfig, ResolvedSettings

client = WangPClient(WangPMCPConfig.from_env())
client.connect()

defaults = client.get_default_settings("ltx2_22B_distilled_gguf_q4_k_m")
resolved = ResolvedSettings.from_template(
    defaults, {"width": 1280, "height": 704, "frames": 97, "steps": 30}
)
payload = resolved.build_payload({"prompt": "..."})
result = client.render(payload, resolved, timeout=3600)
print(result.artifacts)  # ('/mnt/d/Wan2GP/outputs/....mp4',)
```

## Artifacts and path translation

The renderer emits Windows paths (`D:\Wan2GP\outputs\<name>.mp4`).
`RenderResult.artifacts` are already translated to WSL form
(`/mnt/d/Wan2GP/outputs/<name>.mp4`) via
`backend/integrations/paths.py`; `artifacts_native` keeps the raw form for
manifests. Note `D:\Wan2GP` and `/mnt/d/wan2gp` are the same directory —
Windows is case-insensitive.

## Failure modes

- `WangPConnectionError` — refused/reset/unreachable; the message includes
  the exact launch command and the networking note above.
- `WangPTimeoutError` — no response in time, or a job outlived its wait
  budget (carries `job_id`; the job keeps running server-side).
- `WangPProtocolError` — non-MCP/malformed responses, JSON-RPC `error`.
- `WangPRendererError` — renderer answered `isError` (validation, unknown
  model/job): nothing was submitted or nothing was rendered.
- `WangPJobFailedError` — job completed with `success=false`; carries
  `errors` and `job_id`.

Retry policy: idempotent calls (initialize, tools/list, job reads, model
queries) retry with exponential backoff. `wangp_generate` and
`wangp_cancel_job` are **never** retried automatically — a retried submit can
double-render.

## Render in-flight state (the VRAM overflow signal)

`WangPClient.render_in_flight()` is the explicit signal the LLM router asks for
(`backend/services/llm_router.py` names it in its `RenderStateProvider`
protocol). It is `True` while an accepted render job is queued or running, and
`False` once that job is completed, failed, or cancelled.

It is derived from the renderer's own job state — the same `JobStatus` the poll
loop uses — and never from GPU utilization, VRAM free/total, or process
liveness. `is_in_flight_status()` is the single classifier behind it:

| status | `in_flight` |
| --- | --- |
| `queued`, `pending`, `accepted`, `submitted`, `starting`, `running` | `True` |
| `completed`, `cancelled`, `canceled`, `failed`, `error`, `timeout` | `False` |
| missing / unrecognized | `True` (fails safe) |

The fail-safe default matters: if a future renderer snapshot reports a state
word this client has never heard of, the signal stays `True` so the router
sends the director job to the cloud rather than risking an OOM next to a render
whose real state we cannot name.

The client tracks jobs in a lock-guarded table reconciled by `_track()` on
every `submit`/`get_job`/`cancel_job` result, so terminal states clear the
signal without waiting for the caller to poll. `JobStatus.in_flight` and
`RenderJob.in_flight` expose the same classification per job; `is_busy()` is a
back-compat alias; `render_state()` returns a `RenderStateSnapshot` shaped for
logs and metrics.

Two limits worth knowing:

- **Client-local only.** The renderer exposes job state by id, so a render
  submitted by another process is invisible to this client. That is inherent to
  the signal as specified, not an oversight.
- **Unwatched jobs linger.** Nothing clears an entry for a job that finished
  while nobody was polling. `refresh_render_state()` re-polls tracked jobs and
  reconciles the table; a probe that cannot reach the renderer does *not*
  clear the signal (`stale=True` plus `probe_error`) until a probe succeeds or
  `forget_job()` is called.

## Safety guarantees

- No code path in `backend/integrations/` or `scripts/wangp_live_smoke.py`
  writes to or deletes `D:\Wan2GP`, `/mnt/d/wan2gp`, or anywhere else on the
  renderer install. The package performs no filesystem writes at all; the
  guard is enforced by `tests/test_wangp_guardrails.py` (AST scan).
- The renderer's own source tree stays untouched: configuration is a CLI flag,
  a settings JSON, or an MCP call — never a patch (WanGP source integrity).

## Tests

```bash
cd ~/Projects/ai-file-organizer
.venv/bin/python -m pytest tests/test_wangp_paths.py tests/test_wangp_settings.py \
    tests/test_wangp_client.py tests/test_wangp_render_state.py \
    tests/test_wangp_guardrails.py -q
```

Unit tests run fully offline against a mocked MCP server and replay the
recorded live fixtures (`tests/fixtures/wangp_mcp/`). The live path is
exercised by `scripts/wangp_live_smoke.py`, which skips cleanly (exit 0)
when no renderer is reachable.
