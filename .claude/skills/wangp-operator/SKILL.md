---
name: wangp-operator
description: Operate the WanGP renderer (launcher install, MCP over streamable-http) from the Prompt Machine pipeline — topology, discovery, LTX-2.3 I2V + lip-sync recipes, async jobs, path translation, VRAM etiquette. Use when generating video via WanGP or debugging renders.
---

# WanGP Operator (Prompt Machine renderer)

> **Authority:** the Hermes skill store (`wangp-agent`, `ltx2-lipsync-production`, `ltx-video-production`, `wan-video-prompting`, `comfyui-production`) is the living source and its newest edits TRUMP this file. Sync this file when those change. Specialized deep-dives live there; this file is the operator's core for the organizer's `wangp_client`.

## Topology (launcher install, NOT Docker)

- **LIVE renderer**: `C:\Users\thebe\AppData\Roaming\wan2gp-desktop\Wan2GP\Wan2GP` (upstream, clean tracked tree). Managed by the [wan2gp-desktop launcher](https://github.com/GKartist75/wan2gp-desktop) — the launcher overwrites source on update; **never patch WanGP source** (`wgp.py`, `shared/`, `models/`, `defaults/`).
- **`D:\Wan2GP` is the RETIRED Sparge fork** — NOT the renderer. It holds the model stores, mapped by the live install's `wgp_config.json`: `ckpts_root=D:\Wan2GP\ckpts`, `loras_root=D:\Wan2GP\loras`, `save_path/image_save_path/audio_save_path=D:\Wan2GP\outputs`. `D:\Wan2GP` == `/mnt/d/wan2gp` (case-insensitive).
- **venv**: `env_uv` (uv, CPython 3.11.14). Python: `env_uv\Scripts\python.exe`.
- **MCP flags** (`shared/cli_args.py:78-82`): `--mcp`, `--mcp-transport stdio|sse|streamable-http`, `--mcp-host`, `--mcp-port`, `--mcp-console-output`. streamable-http = `json_response=True` + `stateless_http=True`. Endpoint: `http://<host>:<port>/mcp/`.
- **Integrity check** (WINDOWS-side): `cd "<live install>" && git status --porcelain --untracked-files=no` must be empty. Not from WSL (drvfs git times out >60s). Not against `D:\Wan2GP` (corpse).
- **Escape hatch**: plugins in `plugins/` via `plugins_local.json` — never a source patch.

## Launch (headless MCP server)

**PYTHONPATH MUST be scrubbed at the MSYS level** (Hermes desktop exports `PYTHONPATH=<hermes-agent>;<hermes venv>`; WSL interop leaks it into Windows pythons — packages resolve from the HERMES venv):

```bash
PYTHONPATH= wsl -e bash -c "cd /mnt/c/Users/thebe/AppData/Roaming/wan2gp-desktop/Wan2GP/Wan2GP && ./env_uv/Scripts/python.exe ./wgp.py --mcp --mcp-transport streamable-http --mcp-host 0.0.0.0 --mcp-port 8899"
```

- WSL-level `env -u PYTHONPATH` does NOT work; MSYS-level `PYTHONPATH=` prefix does.
- WSL→Windows under NAT: use the default gateway (`ip route | grep default`). Mirrored networking (planned) makes `localhost` work directly.
- Startup ~90s. Ready when the log shows `Uvicorn running on http://0.0.0.0:<port>`.
- **venv drift pitfall**: transformers 4.54.0 pins `tokenizers>=0.21,<0.22` + `huggingface-hub<1.0`. Repair: `pip install 'tokenizers>=0.21,<0.22' 'huggingface-hub>=0.34,<1.0'` (venv-only; git tree stays clean). `wangp_client` verifies the pins at startup.

## MCP protocol (streamable-http)

JSON-RPC 2.0 POSTs to `/mcp/`, headers `Content-Type: application/json` + `Accept: application/json, text/event-stream`. Stateless — no session header.

1. `initialize` → `{"protocolVersion":"2025-03-26","serverInfo":{"name":"WanGP"}}`
2. `tools/list` → **11 tools**: `wangp_list_models`, `wangp_list_model_defs`, `wangp_get_model`, `wangp_get_model_metadata`, `wangp_get_model_availability`, `wangp_list_model_availability`, `wangp_get_default_settings`, `wangp_get_model_schema`, `wangp_generate`, `wangp_get_job`, `wangp_cancel_job`
3. `tools/call` `{"name": ..., "arguments": {...}}`

**Response shapes**: `result.structuredContent` is primary (e.g. `wangp_list_models` → `structuredContent.result` = 210 model dicts). `result.content[].text` fallback — for list_models it's ONE JSON-per-model chunk. Errors: `isError: true` + text.

## Discovery workflow

1. `wangp_list_models` filters: `family`, `base_model_type`, `finetune`, `model_type`, `main_output`, `inputs`, `include_availability`. LTX-2 family: `ltx2_22B_distilled` (int8), `ltx2_22B_distilled_gguf_q4_k_m` (Q4 GGUF), `_1_1`, `_edit_anything`, `_msr`, `ltx2_19B`, `ltxv_13B`. Weights in `D:\Wan2GP\ckpts` (`ltx-2.3-22b-*`).
2. `wangp_get_default_settings(model_type)` → settings dict (`resolution`, `video_length` in frames, `num_inference_steps`, `video_prompt_type`, `settings_version`). Templates also at `settings/<model>_settings.json`.
3. `wangp_get_model_schema(model_type)` → allowed values for flag fields. Fetch before composing flags.
4. Generate → poll → cancel (below).

## LTX-2.3 standard I2V recipe (verified 2026-08-10, Chapter 9 run)

Wan-family settings (`image_mode: 1`, `video_prompt_type: "standard"`) do NOT map to LTX-2.3. The LTX-2.3 I2V switch:

```python
settings = {
    "model_type": "ltx2_22B_distilled_gguf_q4_k_m",  # Q4 co-resides with vLLM
    "image_mode": 0,              # video generation mode — NOT 1
    "image_prompt_type": "S",     # Start image = the I2V switch
    "video_prompt_type": "",      # "" = standard I2V (KFI = inject frames)
    "image_start": "<abs keyframe path>",
    "image_refs": ["<abs identity anchor path>"],   # single_reference models take EXACTLY 1
    "activated_loras": ["Ltx2.3-Licon-VBVR-I2V-96000-R32.safetensors"],  # IC-LoRA — refs do NOTHING without it
    "loras_multipliers": "1",
    "guidance_scale": 3.5, "guidance2_scale": 3.5, "guidance_phases": 2,  # CFG key is guidance_scale; both phases equal
    "resolution": "1280x704",     # LTX-2.3 native 16:9 = multiple of 32; 1280x720 is NOT valid
    "video_length": 97, "force_fps": 24,   # 97 = 8k+1 (VAE 8x temporal)
    "num_inference_steps": 30,
    "prompt_enhancer": "",        # "" = off
    "config": "PrunaAI VAE",      # faster VAE decode
    "audio_prompt_type": "",      # Null audio for MOS shots
    "negative_prompt": "warp, morph, extra fingers, watermark",
    "output_filename": "Ch-9-{date(YYYY-MM-DD_HH-mm-ss)}{seed}{prompt(50)}, {num_inference_steps}",
}
```

- Hold shots (unblinking ECU): drop `guidance_scale`/`guidance2_scale` to 3.0 to prevent face shimmer.
- Lock the seed per shot-unit; changing seed per shot breaks grain continuity.
- `wan2_1_i2v_720p` does NOT exist in current builds; the LTX-2.3 GGUF family is the actual I2V renderer. Run discovery before assuming a model exists.

## Lip-sync / audio-guided generation (LTX-2.3, verified 2026-08-10)

**The one setting that matters:** `audio_prompt_type: "A"` (Generate Video based on Soundtrack and Text Prompt) + `audio_guide: <wav path>`. WITHOUT this the lips never move.

```python
settings = {
    ...standard I2V recipe above...,
    "audio_prompt_type": "A",     # ← THE lip-sync switch
    "audio_guide": r"D:\path\to\VO.wav",
    "audio_scale": 1.0,
}
```

- Words in the prompt IN QUOTES with who says them: `He speaks: "The system told me you'd ask for that."`
- **Verification signature**: model-native output audio = 48kHz AAC. If output is 44.1kHz and correlates ~1.0 with the source wav → audio was REMUXED post-gen, the model never conditioned, lips are dead (the LTX-Director plugin queue path failure mode).

### THE THREE LIP-SYNC PITFALLS (2026-08-13 ground truth)

1. **`"V"` flag kills lip-sync** (`audio_prompt_type: "AV"` routes the guide through `get_vocals()` → WanGP reuses the source audio unchanged → corr 1.000 → dead mouth). **Correct: plain `"A"` only.**
2. **Internal sliding window breaks audio conditioning** — on `video_length > 481`, windows 2+ condition on misaligned audio. **Never exceed the single-window cap (481f); chunk manually.**
3. **Audio must NOT exactly fill the window** — when the guide length ≥ the window, WanGP drops the model's generated audio and reuses the guide → no synthesis → dead lips. **The window MUST be ~1s LONGER than the audio guide.** (`video_length = snap_8k1(audio_sec + 1.0)`, ≤ 481.) The `"O"` flag does NOT fix this.

### Working long-shot recipe (all three pitfalls avoided)

```python
{
  "model_type": "ltx2_25_22B_distilled",   # or ltx2_22B_distilled_gguf_q4_k_m
  "image_mode": 0, "image_prompt_type": "S", "video_prompt_type": "",
  "image_start": "<keyframe>", "image_refs": ["<identity ref>"],
  "resolution": "1280x704", "force_fps": 24,
  "num_inference_steps": 8, "sample_solver": "distilled_8_steps",
  "audio_prompt_type": "A",           # plain A only (no V, no O)
  "audio_guide": "<wav SLICED to be ~1s SHORTER than the window>",
  "audio_scale": 1.0,
  "guidance_scale": 3.0, "audio_guidance_scale": 7.0, "alt_guidance_scale": 3.0, "alt_scale": 0.7,
  "guidance_phases": 2, "config": "PrunaAI VAE", "seed": 145624434,
}
```

- Chunk long stems ≤457f (~19s) audio; window = `snap_8k1(audio_sec + 1.0)` ≤ 481.
- Chunk 1 `image_start` = stem keyframe; chunk N+1 `image_start` = last frame of chunk N (chain continuity).
- QC tells: **48kHz** = in-model (44.1kHz = remux = dead). **Waveform corr vs source** ≈ 0.02 = re-synthesized ✅ / 1.000 = reused ❌. Mouth-motion↔audio-envelope corr ≥ 0.3 @ lag 3-4f = synced.
- Multi-clip timelines: assemble audio FIRST (trim + place, 44.1kHz stereo), feed ONE combined wav as `audio_guide`. Verified: 369f/15.375s single-window timeline works; do NOT exceed 481f.

## Generation (async)

```json
{"source": {"model_type": "ltx2_22B_distilled_gguf_q4_k_m", "prompt": "...", "resolution": "512x320", "video_length": 9, "num_inference_steps": 8}}
```

- `wangp_generate` returns `job_id` immediately (or `isError` on validation, before model load).
- Poll `wangp_get_job(job_id)` — event kinds: `progress`, `stream`, `preview`, `output`, `completed`. Artifact in a completed/output event: `generated_files: ["D:\\Wan2GP\\outputs\\<name>.mp4"]` — **translate `D:\…` → `/mnt/d/…` at the client boundary** (paths.py) for WSL-side reads.
- `wangp_cancel_job(job_id)` → `cancel_requested: true`.
- Settings discipline (Deepy pattern): template + bounded overrides only (`width, height, num_frames, fps, num_inference_steps, loras`). Prompt enhancer OFF. Settings JSON = UTF-8 no BOM.

## VRAM etiquette (RTX 5090 Laptop, 24.5 GB — measured)

- vLLM (Qwen3.5-4B) holds ~9.7-13 GB permanently. Managed via systemd user unit: `systemctl --user stop vllm-qwen35.service` / start. (~2 min warmup on start.)
- **Q4 GGUF co-resides** with vLLM (validated: dozens of overnight renders; peak 24,038/24,463 MiB on a small job). Do NOT stop vLLM for Q4 jobs.
- **int8 does NOT co-reside**: memory scheduler stalls (`done:false`, flat VRAM). Stop vLLM first. **Stall signature when vLLM comes back MID-run**: GPU 100% util but ~80W power, sampling stuck at step 0/8 forever, no artifact. Check before ANY int8 render: `curl -s -m 2 http://127.0.0.1:8000/v1/models` — if it answers, `systemctl --user stop vllm-qwen35.service`; restart after the batch.
- `nvidia-smi.exe` (Windows binary, callable from WSL) reports true global state; WSL pynvml may miss Windows-side renderer VRAM.
- Dispatch watchdog (Prompt Machine Phase 3): no progress event AND no VRAM movement within N seconds → failed-to-start, cancel, surface.

## Guardrails

- Never patch WanGP source. Missing capability → `plugins_local.json` escape hatch or Gradio HTTP API — not a diff.
- Surface structured errors; don't silently swap models/media inputs.
- In-memory results only when needed (`_api.return_media`); artifact paths usually suffice.
- Prompt Library / Prompt Manager plugins: fine hands-on, never wire into the pipeline (two stores = two truths).
- WanGP attribution required in any integrating product's UI + docs.
- Every generation must be visible to Ryan (Hermes chat inline player; stage to `C:\Users\thebe\AppData\Local\Temp\ch9_clips\`; durable copy in the project vault).
