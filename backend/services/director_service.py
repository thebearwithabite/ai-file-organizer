"""DirectorService — script → ShotSpec[] (PROMPT-MACHINE-DIRECTIVE v1.2, Phase 1).

A script (.txt/.md/.fountain/.pdf) becomes an engine-agnostic scene plan
(``analyze_script``) and a Pydantic-validated ``ShotSpec[]``
(``generate_shot_list``) via the ``backend/llm/`` provider chain:

    vLLM (localhost:8000, qwen3.5:4b)  →  Ollama (gemma4:12b)  →  DeepSeek (key + consent only)

Local-first. The cloud fallback is reachable ONLY when a DEEPSEEK_API_KEY
exists in GCP Secret Manager AND the caller explicitly allows script content
to leave the box (``allow_cloud_script=True``). The Checkpoint 1 gate: the
full pipeline completes keyless on local models alone.

Degradation (parent 2.1 pattern): repeated schema failure is handled inside
LLMProvider (3 attempts, then permanent degrade). When the director receives
a failed result it enqueues the script to the review queue
(batch_group='director-degrade') and returns degraded=True — the system
waits, it never floods and never silently guesses.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from core.paths import get_metadata_root

from backend.llm import LLMProvider
from backend.services.llm_resolver import (
    DegradeReason,
    enqueue_llm_degrade,
    provider_kwargs,
    resolve_provider,
)

from .shot_spec import (
    EXCLUSIONS_TABLE_DDL,
    SHOTS_TABLE_DDL,
    ScenePlan,
    ShotListOutput,
    ShotSpec,
)

logger = logging.getLogger(__name__)

# One example ShotSpec — shown to the LLM as the output shape to copy.
EXAMPLE_SHOT = {
    "shot_id": "sc01_sh01",
    "sequence_index": 0,
    "status": "draft",
    "version": 1,
    "scene": {
        "context": "Maya enters the kitchen and finds the letter on the counter.",
        "visual_style": "naturalistic, handheld documentary feel",
        "lighting": "soft morning window light from the left",
        "mood": "quiet, suspended",
        "duration_s": 6.0,
        "aspect_ratio": "16:9",
    },
    "character": {
        "name": "Maya",
        "gender_age": "woman, mid-30s",
        "physical_description": "shoulder-length dark hair, grey knit sweater, silver ring on right hand",
        "behavior": "walks slowly, stops at the counter, picks up the envelope with both hands",
        "expression_cues": "eyebrows draw together, lips press into a thin line, fingers still on the envelope",
    },
    "camera": {
        "shot_call": "Eye-Level Medium Close-Up",
        "movement": "slow push-in",
        "negatives": "no readable text on the letter, no other people in frame",
    },
    "audio": {
        "dialogue": "",
        "delivery": "",
        "ambience": "faint street traffic, refrigerator hum",
        "sfx": "paper rustling",
    },
    "assets": [
        {
            "asset_id": "char_maya",
            "type": "character",
            "lora_path": None,
            "trigger_token": None,
            "ref_image": None,
            "weight": 0.9,
        }
    ],
    "generation": {
        "engine": "wangp",
        "template_id": "LTX-2 2.3 Distilled",
        "overrides": {},
        "seed": -1,
        "comfy_workflow_id": None,
    },
}


@dataclass
class ShotListResult:
    shots: List[ShotSpec] = field(default_factory=list)
    provider: str = "none"
    degraded: bool = False
    reason: str = ""


class DirectorService:
    """Breaks scripts into scene plans and validated shot lists."""

    def __init__(self, db_path: Optional[Path] = None, provider: Optional[LLMProvider] = None):
        if db_path is None:
            db_path = get_metadata_root() / "organizer.db"
        self.db_path = db_path
        self._provider = provider  # injected (tests); otherwise resolved per call
        self._init_shots_table()

    # ------------------------------------------------------------------
    # Shots table
    # ------------------------------------------------------------------

    def _init_shots_table(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(SHOTS_TABLE_DDL)
            conn.execute(EXCLUSIONS_TABLE_DDL)
            conn.commit()

    def _persist_shots(self, shots: List[ShotSpec], project_id: str = "") -> None:
        """Replace the project's shot list atomically.

        Delete-then-insert scoped to (project_id) inside ONE transaction: a
        regeneration that yields fewer shots must remove the orphans that
        plain INSERT OR REPLACE leaves behind (observed live: a 10-shot run
        followed by a 6-shot run left 4 stale rows on the project).

        Stored asset bindings are carried forward by shot_id, so manual
        toggles survive regeneration — the human's selection outranks the
        LLM's guess on the same shot.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            old = conn.execute(
                "SELECT shot_id, shot_json FROM shots WHERE project_id = ?", (project_id,)
            ).fetchall()
            old_assets: dict[str, list] = {}
            for sid, sj in old:
                try:
                    spec = ShotSpec.model_validate_json(sj)
                    if spec.assets:
                        old_assets[sid] = spec.assets
                except Exception:
                    continue  # unparseable old row — do not let it block the replace

            conn.execute("DELETE FROM shots WHERE project_id = ?", (project_id,))
            for i, shot in enumerate(shots):
                if shot.shot_id in old_assets:
                    shot.assets = old_assets[shot.shot_id]
                conn.execute(
                    """INSERT OR REPLACE INTO shots
                       (shot_id, project_id, sequence_index, status, version, shot_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        shot.shot_id,
                        project_id or shot.project_id,
                        i,
                        shot.status.value,
                        shot.version,
                        shot.model_dump_json(),
                    ),
                )
            # Orphan hygiene for exclusions: a shot removed by this regeneration
            # takes its deselection rows with it.
            gone = {sid for sid, _ in old} - {s.shot_id for s in shots}
            if gone:
                placeholders = ",".join("?" * len(gone))
                conn.execute(
                    f"DELETE FROM shot_asset_exclusions WHERE shot_id IN ({placeholders})",
                    tuple(gone),
                )
            conn.commit()
        logger.info("Replaced %d shots (project=%s)", len(shots), project_id or "(none)")

    # ------------------------------------------------------------------
    # Knowledge
    # ------------------------------------------------------------------

    def _load_knowledge(self, category_id: str) -> str:
        """Pull a knowledge seed's description text from the knowledge table."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                row = conn.execute(
                    "SELECT description FROM knowledge WHERE category_id = ?",
                    (category_id,),
                ).fetchone()
            return row[0] if row else ""
        except sqlite3.Error as e:
            logger.warning("knowledge read failed for %s: %s", category_id, e)
            return ""

    # ------------------------------------------------------------------
    # Provider resolution (shared with AssetService — see llm_resolver.py)
    # ------------------------------------------------------------------

    def analyze_script(self, script: str, project_id: str = "", allow_cloud_script: bool = False) -> dict:
        """Script → engine-agnostic ScenePlan (beats, runtime goals, extend policy)."""
        provider, name = resolve_provider(allow_cloud_script, injected=self._provider)
        if provider is None:
            enqueue_llm_degrade(
                script, project_id, "no local LLM provider available",
                degrade_reason=DegradeReason.provider_unreachable.value,
            )
            return {"plan": ScenePlan(), "provider": "none", "degraded": True,
                    "reason": "no local LLM provider available (vLLM and Ollama unreachable)"}

        prompt = self._build_scene_plan_prompt(script)
        kwargs = provider_kwargs(name)
        plan, ok = provider.generate_structured(prompt, ScenePlan, degrade_value=None, **kwargs)

        if not ok or plan is None:
            reason = getattr(provider, "last_failure", "") or DegradeReason.schema_invalid.value
            enqueue_llm_degrade(
                script, project_id, f"scene plan generation failed ({name})",
                degrade_reason=reason,
            )
            return {"plan": ScenePlan(), "provider": name, "degraded": True,
                    "reason": f"scene plan generation failed after retries ({name})"}

        return {"plan": plan, "provider": name, "degraded": False, "reason": ""}

    # ------------------------------------------------------------------
    # Shot list
    # ------------------------------------------------------------------

    def generate_shot_list(
        self,
        script: str,
        project_id: str = "",
        allow_cloud_script: bool = False,
    ) -> ShotListResult:
        """Script → validated ShotSpec[] (Pydantic-validated, bounded retry, degrade-to-queue)."""
        provider, name = resolve_provider(allow_cloud_script, injected=self._provider)
        if provider is None:
            enqueue_llm_degrade(
                script, project_id, "no local LLM provider available",
                degrade_reason=DegradeReason.provider_unreachable.value,
            )
            return ShotListResult(provider="none", degraded=True,
                                  reason="no local LLM provider available (vLLM and Ollama unreachable)")

        prompt = self._build_shot_list_prompt(script)
        kwargs = provider_kwargs(name)
        output, ok = provider.generate_structured(prompt, ShotListOutput, degrade_value=None, **kwargs)

        if not ok or output is None:
            reason = getattr(provider, "last_failure", "") or DegradeReason.schema_invalid.value
            enqueue_llm_degrade(
                script, project_id, f"shot list generation failed ({name})",
                degrade_reason=reason,
            )
            return ShotListResult(provider=name, degraded=True,
                                  reason=f"shot list generation failed after retries ({name})")

        shots = output.shots
        # Normalize project_id + sequence index before persisting
        for i, shot in enumerate(shots):
            shot.project_id = project_id or shot.project_id
            shot.sequence_index = i
        self._persist_shots(shots, project_id)
        return ShotListResult(shots=shots, provider=name, degraded=False, reason="")

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    def _build_scene_plan_prompt(self, script: str) -> str:
        principles = self._load_knowledge("FILMMAKING_PRINCIPLES")
        return f"""You are a film director breaking a script into an engine-agnostic scene plan for AI video generation.

FILMMAKING PRINCIPLES:
{principles or "(none loaded)"}

TASK: Analyze the script and produce a scene plan as STRICT JSON matching exactly this shape:
{{
  "title": "suggested project title",
  "scenes": [
    {{
      "scene_id": "sc01",
      "summary": "one-paragraph beat summary",
      "runtime_goal_s": 45.0,
      "extend_policy": "continuation | montage | standalone"
    }}
  ],
  "total_runtime_s": 180.0
}}

Rules:
- One scene per location/time block; scenes in script order.
- runtime_goal_s: honest estimate of screen time for the beat (5-90s).
- extend_policy: "continuation" for sequential beats, "montage" for time-lapse/compression, "standalone" for self-contained moments.
- Output ONLY the JSON object. No markdown fences, no commentary, no trailing text.

SCRIPT:
{script}
"""

    def _build_shot_list_prompt(self, script: str) -> str:
        principles = self._load_knowledge("FILMMAKING_PRINCIPLES")
        ltx_guide = self._load_knowledge("LTX23_PROMPT_GUIDE")
        schema_hint = json.dumps(EXAMPLE_SHOT, indent=2)
        return f"""You are a director breaking a script into discrete shots for AI video generation (LTX 2.3).

FILMMAKING PRINCIPLES:
{principles or "(none loaded)"}

LTX 2.3 PROMPT GUIDE (your scene/lighting/character/camera/audio fields will later be compiled into LTX prompts, so follow these rules now):
{ltx_guide or "(none loaded)"}

TASK: Break the script into 6-12 shots. One clear dramatic action per shot. Produce STRICT JSON matching exactly this shape:
{{"shots": [<ShotSpec objects>]}}

Each ShotSpec object has EXACTLY this shape (copy the keys verbatim; adapt values to the script):
{schema_hint}

Hard constraints:
- shot_id format: "sc##_sh##" where ## is a two-digit number (sc01_sh01, sc02_sh03). Unique across the list.
- sequence_index: 0-based, in order.
- expression_cues: PHYSICAL cues only — facial/body action. NEVER emotion labels (happy, sad, angry, scared, excited, etc.).
- audio.dialogue: quote exact spoken lines with double quotes inside the string. Empty string if the shot has no dialogue.
- camera.shot_call: use standard framing vocabulary (Extreme Wide, Wide, Medium, Close-Up, Extreme Close-Up, etc.).
- scene.lighting: one coherent lighting description — never conflicting sources.
- scene.duration_s: 3-10 seconds per shot.
- assets: include one entry per character present, type "character", weight 0.9. No lora_path, trigger_token, or ref_image for now (null).
- generation: leave as the template defaults shown above (engine "wangp", template_id "LTX-2 2.3 Distilled", seed -1).
- Output ONLY the JSON object. No markdown fences, no commentary, no trailing text.

SCRIPT:
{script}
"""
