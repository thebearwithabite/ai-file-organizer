---
name: comfyui-gateway
description: Drive ComfyUI through the Gateway REST API (:3000) for precision passes — effect LoRAs, style transfer, upscale. Workflow templating, marker-based addressing, job polling, VRAM etiquette. Use when the Prompt Machine routes a shot to comfyui engine.
---

# ComfyUI Gateway (precision passes)

> **Authority:** the Hermes skill store (`comfyui-production`) is the living source and its newest edits TRUMP this file. Its `references/gateway-api.md` holds the full REST reference — read it before heavy Gateway work.
> **BOUNDARY:** this skill is the ComfyUI stack only. WanGP render settings live in `wangp-operator` — ComfyUI node params (cfg, steps, sampler names, EmptyLatentVideo) do NOT map 1:1 to the WanGP API. When a task is a WanGP render, do NOT copy ComfyUI params into WanGP settings.

## When to route here (Prompt Machine ENGINE_ROUTING)

- Effect LoRAs, style transfer (paper cutout, stop motion, anime, Malick, glitch), upscale passes (512p → 1080p).
- Precise LoRA stacking and denoise control.
- NOT for drafts/turnaround — those go to WanGP.

## Gateway REST (:3000)

The Gateway wraps ComfyUI's WebSocket API into REST with job queuing and output storage. No direct websockets — Gateway only.

```bash
# Health
curl -s http://<gateway>:3000/health | jq .

# Submit a job (workflow template + inputs)
curl -X POST http://<gateway>:3000/jobs \
  -H "Content-Type: application/json" -H "X-API-Key: ***" \
  -d '{"workflowId": "ltx-paper-cutout",
       "inputs": {"prompt": "A city breathing through fog at dawn",
                  "width": 1280, "height": 720, "steps": 25}}'

# Poll
curl -s http://<gateway>:3000/jobs/$JOB_ID -H "X-API-Key: ***" | jq '.status'

# Download output
curl -s "http://<gateway>:3000/outputs/$JOB_ID/$FILENAME" -H "X-API-Key: ***" -o output.mp4
```

Job lifecycle: submit → poll `.status` → download. The Gateway does queuing/polling — never hand-roll websockets.

## Workflow templating

ComfyUI workflows are DAGs serialized as JSON; nodes have numeric IDs, `class_type`, and `inputs` referencing other nodes by `[node_id, output_index]`.

- The Gateway supports `{{ variable }}` substitution in workflow JSONs (defined in the workflow's `inputSchema`, replaced at submission).
- **Marker discipline (Prompt Machine compiler — `emit_comfy_workflow`)**: node addressing uses `_meta.title` markers — `[PROMPT_POS]`, `[PROMPT_NEG]`, `[LORA_LOADER_1]`, `[SAMPLER]`, `[IMAGE_START]` — **never numeric node IDs**, which drift the moment a workflow is edited in the ComfyUI graph. The compiler validates every required marker exists before submit; a missing marker is a HARD error, never a silent default.
- Asset mapping: assets → LoRA loaders (weight hierarchy below), seed → sampler.

Minimal T2V workflow shape (template variables):

```json
{
  "1": {"inputs": {"ckpt_name": "LTX-2.3-Base.safetensors"}, "class_type": "CheckpointLoaderSimple"},
  "2": {"inputs": {"text": "{{ prompt }}", "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
  "3": {"inputs": {"text": "{{ negative_prompt }}", "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
  "4": {"inputs": {"width": 1280, "height": 720, "length": 97, "batch_size": 1}, "class_type": "EmptyLatentVideo"},
  "5": {"inputs": {"seed": 0, "steps": 25, "cfg": 3.0, "sampler_name": "euler", "scheduler": "normal",
                   "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                   "latent_image": ["4", 0]}, "class_type": "KSampler"},
  "6": {"inputs": {"samples": ["5", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"},
  "7": {"inputs": {"filename_prefix": "LTX_output", "fps": 24, "format": "video/h264-mp4",
                   "images": ["6", 0]}, "class_type": "VideoCombine"}
}
```

## LoRA stacking (weight hierarchy)

- Character/ID LoRA: **0.8–1.0** (identity must dominate)
- Scene LoRA: **0.5–0.7**
- Effect LoRA: **0.3–0.6** (style layer, must not overpower identity)

Effect pass denoise: 0.3 = subtle style hint, 0.5 = strong, 0.7+ = heavy transformation (may lose source content).

I2V prompting rule: describe only what happens NEXT — motion, change, temporal arc. Do not describe what's already visible in the guidance frame.

## VRAM etiquette

- One render at a time across the whole stack — `render_jobs` table is the authoritative serializer (WanGP + ComfyUI combined). Never queue a ComfyUI pass while a WanGP render is active.
- Keep 3–4 GB free for ComfyUI overhead, OS, preview buffers. If `nvidia-smi` shows >20 GB used, reduce complexity before the next generation.
- Never download models during a render session — pre-stage everything.
- One checkpoint loaded at a time; LTX-2.3 + 2–3 LoRAs is the comfortable config; a second checkpoint risks OOM on long videos.
- Don't queue during LoRA training (14–22 GB depending on rank).

## QC loop (Director's Gate)

1. GENERATE → queue the job
2. REVIEW → present output to the Director (Ryan)
3. VERDICT → **LOCK / ITERATE / REJECT** (never auto-approve)
4. LOCK → move to locked folder, update shot tracker. ITERATE → adjust params, re-queue (max 3 iterations per shot). REJECT → log why (prompt + artifact ref = future LoRA training data).

## Connectivity quick checks

```bash
curl -s http://<comfyui-ip>:8188/ | head -5          # ComfyUI up?
curl -s http://<gateway-ip>:3000/health | jq .        # Gateway up?
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader
```

| Symptom | Likely cause | Fix |
|---|---|---|
| `COMFYUI_UNREACHABLE` | Wrong IP / not started | Check URL + process |
| `CUDA out of memory` | Stack too heavy | Reduce to 720p, drop a LoRA, reduce steps |
| Job stuck "running" | ComfyUI crashed mid-gen | `POST /jobs/{id}/cancel`, restart ComfyUI |
| Wrong style output | LoRA not loaded / wrong triggers | Verify LoRA path + trigger words |
| GPU util 0% | CPU fallback | Check `CUDA_VISIBLE_DEVICES`, torch sees GPU |
