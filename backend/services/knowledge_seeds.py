"""Knowledge seeds for the Prompt Machine (PROMPT-MACHINE-DIRECTIVE v1.2).

Three seeds land in the existing ``knowledge`` table (organizer.db, parent
2.2 pattern — same table ContextStore uses):

  - FILMMAKING_PRINCIPLES — engine-agnostic film craft. Authored fresh
    (2026-08-09): the legacy asset was searched and does not exist in this
    repo, dev-archive/, or /tmp/veo_latest_repo. This file is the canonical
    version per the directive.
  - LTX23_PROMPT_GUIDE      — the prompt-compiler emitter rules as prose, for
    the director LLM (and prompt QA).
  - ENGINE_ROUTING          — render engine selection + GPU co-residency and
    watchdog rules, for the director/orchestrator.

Seeds are upserted on category_id so re-running updates content in place.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from core.paths import get_metadata_root

logger = logging.getLogger(__name__)

FILMMAKING_PRINCIPLES = """\
FILMMAKING PRINCIPLES — engine-agnostic craft rules for shot planning.

Coverage:
- Open a scene with an establishing beat that orients the viewer (location, time, spatial layout).
- Vary shot scale deliberately: wide establishes, medium carries action, close-ups land emotional beats.
- One clear dramatic action per shot. If a scene has multiple beats, split them across shots.
- End a shot on a beat that gives the next shot a reason to exist (a look, a movement, a sound).

Continuity (the #1 viewer-killer is inconsistency):
- Characters keep a stable physical appearance across every shot: same build, hair, wardrobe, props.
- Screen direction is consistent: if a character exits frame left, they enter the next shot from the opposite edge.
- Lighting stays coherent within a scene: one dominant key direction, no unexplained mood swings.
- Props do not teleport or change state between shots unless the action shows the change.

Camera:
- Camera movement must be motivated: dolly follows motion, push-in lands a realization, pull-back reveals context.
- Cut on action or on a glance; do not cut mid-gesture.
- The camera describes the SUBJECT after the move completes.

Performance:
- Emotion is communicated through physical action, not labels: hands, posture, breath, eye focus, weight shift.
- Dialogue beats belong in closer framing; ambient action can play wide.

Frame hygiene:
- No readable text, logos, watermarks, or signage in frame unless the story requires it.
- No visible crew, rigging, or modern artifacts in period scenes.
- Keep the frame uncluttered: one subject of interest per shot.
""".strip()

LTX23_PROMPT_GUIDE = """\
LTX 2.3 PROMPT GUIDE — how to write a video-generation prompt.

FORM: ONE flowing prose paragraph. Present tense. 4-8 sentences.

ORDER (fixed):
1. Establish the shot: framing, subject, location.
2. Scene and lighting: environment, light quality and direction.
3. Action: what happens, in the order it happens.
4. Character: physical cues only — appearance, movement, hands, breath, eye focus.
5. Camera movement: describe the SUBJECT after the move completes.
6. Audio: dialogue in quotes ("..."), delivery, ambience, sfx.

NEVER emit:
- Readable text or logos in frame.
- Emotion labels (happy, sad, angry, scared). Render the physical evidence instead.
- Conflicting lighting (e.g. "soft window light" + "harsh neon glare" in one shot).
- Overloaded multi-action scenes: one action per shot, more shots if needed.

Length: stay within the engine's token budget. Estimate tokens before emitting;
over budget -> run an LLM compression pass that preserves the ordered structure,
never silently truncate.
""".strip()

ENGINE_ROUTING = """\
ENGINE ROUTING — which renderer for which job, and the GPU rules.

- WanGP (MCP over streamable-http): drafts and turnaround. Default template
  LTX-2 2.3 Distilled. Settings come from template files + six bounded
  overrides only (width, height, num_frames, fps, num_inference_steps, loras).
- ComfyUI (Gateway REST :3000): precision passes — effect LoRAs, style
  transfer, upscale. Never direct websockets.

GPU co-residency (measured 2026-08-09, RTX 5090 Laptop 24.5 GB):
- vLLM (Qwen3.5-4B) holds ~11 GB at --gpu-memory-utilization 0.45; it never
  releases memory while running.
- Q4 GGUF renders (ltx2_22B_distilled_gguf_q4_k_m) CO-RESIDE with vLLM for
  small jobs (measured peak 24,038/24,463 MiB on a 9-frame job — 425 MiB
  headroom; validated in practice over dozens of overnight renders).
- int8 renders (ltx2_22B_distilled) DO NOT co-reside: the memory scheduler
  stalls silently (done:false, no error, flat VRAM). Stop vLLM before
  dispatching int8-class jobs; start it after (~2 min warmup).
- Residency policy is PER-JOB-SIZE, not per-model, until a frame x pixel
  budget is measured at production resolution. Above the budget, the
  lifecycle rule applies regardless of model.

Dispatch watchdog (mandatory):
- A render showing no progress event AND no VRAM movement within N seconds of
  dispatch is failed-to-start: cancel, mark the render_jobs row, surface it.
  Never trust done:false indefinitely.

Post-render health probe:
- After any render that ran alongside vLLM, re-probe vLLM with a known-answer
  inference and compare latency to the 2-3 s baseline. A paged-out model can
  still answer /v1/models while silently degrading.

One render at a time: render_jobs is the authoritative serialization; VRAM
polling is advisory only.
""".strip()

SEEDS = {
    "FILMMAKING_PRINCIPLES": {
        "display_name": "Filmmaking Principles (engine-agnostic)",
        "description": FILMMAKING_PRINCIPLES,
        "keywords": ["coverage", "continuity", "camera", "performance", "frame hygiene"],
        "examples": [],
        "naming_rules": "",
    },
    "LTX23_PROMPT_GUIDE": {
        "display_name": "LTX 2.3 Prompt Guide",
        "description": LTX23_PROMPT_GUIDE,
        "keywords": ["ltx", "prompt", "emitter", "token guard", "prose"],
        "examples": [],
        "naming_rules": "",
    },
    "ENGINE_ROUTING": {
        "display_name": "Engine Routing & GPU Rules",
        "description": ENGINE_ROUTING,
        "keywords": ["wangp", "comfyui", "vllm", "co-residency", "watchdog", "gpu"],
        "examples": [],
        "naming_rules": "",
    },
}


def seed_prompt_machine_knowledge(db_path: Optional[Path] = None) -> dict[str, str]:
    """Upsert the three Prompt Machine seeds into the knowledge table.

    Returns {category_id: 'inserted'|'updated'}.
    """
    if db_path is None:
        db_path = get_metadata_root() / "organizer.db"

    status: dict[str, str] = {}
    with sqlite3.connect(str(db_path)) as conn:
        # Self-sufficient: ensure the knowledge table exists (ContextStore
        # normally creates it; standalone seeding must not depend on that).
        conn.execute(
            """CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id TEXT NOT NULL,
                display_name TEXT,
                description TEXT,
                examples TEXT,
                naming_rules TEXT,
                keywords TEXT,
                parent_category TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                updated_at REAL DEFAULT (strftime('%s', 'now'))
            )"""
        )
        for category_id, data in SEEDS.items():
            existing = conn.execute(
                "SELECT id FROM knowledge WHERE category_id = ?", (category_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE knowledge SET
                           display_name = ?, description = ?, keywords = ?,
                           examples = ?, naming_rules = ?, updated_at = strftime('%s','now')
                       WHERE category_id = ?""",
                    (
                        data["display_name"],
                        data["description"],
                        json.dumps(data["keywords"]),
                        json.dumps(data["examples"]),
                        data["naming_rules"],
                        category_id,
                    ),
                )
                status[category_id] = "updated"
            else:
                conn.execute(
                    """INSERT INTO knowledge
                           (category_id, display_name, description, examples,
                            naming_rules, keywords, parent_category)
                       VALUES (?, ?, ?, ?, ?, ?, 'prompt_machine')""",
                    (
                        category_id,
                        data["display_name"],
                        data["description"],
                        json.dumps(data["examples"]),
                        json.dumps(data["naming_rules"]),
                        json.dumps(data["keywords"]),
                    ),
                )
                status[category_id] = "inserted"
        conn.commit()
    logger.info("Prompt Machine knowledge seeds: %s", status)
    return status


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(seed_prompt_machine_knowledge())
