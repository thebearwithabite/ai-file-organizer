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
from typing import List, Optional, Tuple

from core.paths import get_metadata_root

from backend.llm import LLMProvider, VLLMClient
from backend.llm.ollama_client import OllamaClient
from backend.llm.deepseek_client import DeepSeekClient
from backend.audio.review_queue import ReviewQueue

from .shot_spec import (
    ScenePlan,
    ShotListOutput,
    ShotSpec,
)

logger = logging.getLogger(__name__)

DIRECTOR_LOCAL_FALLBACK_MODEL = "gemma4:12b"
SHOT_LIST_MAX_TOKENS = 6000

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
            conn.execute(
                """CREATE TABLE IF NOT EXISTS shots (
                    shot_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL DEFAULT '',
                    sequence_index INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'draft',
                    version INTEGER NOT NULL DEFAULT 1,
                    shot_json TEXT NOT NULL,
                    created_at REAL DEFAULT (strftime('%s','now')),
                    updated_at REAL DEFAULT (strftime('%s','now'))
                )"""
            )
            conn.commit()

    def _persist_shots(self, shots: List[ShotSpec], project_id: str = "") -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            for i, shot in enumerate(shots):
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
            conn.commit()
        logger.info("Persisted %d shots (project=%s)", len(shots), project_id or "(none)")

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
    # Provider resolution
    # ------------------------------------------------------------------

    def _resolve_provider(self, allow_cloud_script: bool = False) -> Tuple[Optional[LLMProvider], str]:
        if self._provider is not None:
            return self._provider, "injected"

        vllm = VLLMClient()
        if vllm.health_check():
            return vllm, "vllm"

        ollama = OllamaClient(model=DIRECTOR_LOCAL_FALLBACK_MODEL)
        if ollama.health_check():
            return ollama, "ollama"

        if allow_cloud_script:
            from secret_manager import get_secret

            key = get_secret("DEEPSEEK_API_KEY")
            if key:
                return DeepSeekClient(api_key=key), "deepseek"

        return None, "none"

    # ------------------------------------------------------------------
    # Scene plan
    # ------------------------------------------------------------------

    def analyze_script(self, script: str, project_id: str = "", allow_cloud_script: bool = False) -> dict:
        """Script → engine-agnostic ScenePlan (beats, runtime goals, extend policy)."""
        provider, name = self._resolve_provider(allow_cloud_script)
        if provider is None:
            self._enqueue_degrade(script, project_id, "no local LLM provider available")
            return {"plan": ScenePlan(), "provider": "none", "degraded": True,
                    "reason": "no local LLM provider available (vLLM and Ollama unreachable)"}

        prompt = self._build_scene_plan_prompt(script)
        kwargs = self._provider_kwargs(name)
        plan, ok = provider.generate_structured(prompt, ScenePlan, degrade_value=None, **kwargs)

        if not ok or plan is None:
            self._enqueue_degrade(script, project_id, f"scene plan schema failure ({name})")
            return {"plan": ScenePlan(), "provider": name, "degraded": True,
                    "reason": f"scene plan schema failure after retries ({name})"}

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
        provider, name = self._resolve_provider(allow_cloud_script)
        if provider is None:
            self._enqueue_degrade(script, project_id, "no local LLM provider available")
            return ShotListResult(provider="none", degraded=True,
                                  reason="no local LLM provider available (vLLM and Ollama unreachable)")

        prompt = self._build_shot_list_prompt(script)
        kwargs = self._provider_kwargs(name)
        output, ok = provider.generate_structured(prompt, ShotListOutput, degrade_value=None, **kwargs)

        if not ok or output is None:
            self._enqueue_degrade(script, project_id, f"shot list schema failure ({name})")
            return ShotListResult(provider=name, degraded=True,
                                  reason=f"shot list schema failure after retries ({name})")

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

    def _provider_kwargs(self, provider_name: str) -> dict:
        if provider_name in ("vllm", "deepseek"):
            return {"max_tokens": SHOT_LIST_MAX_TOKENS, "temperature": 0.1}
        return {"num_predict": SHOT_LIST_MAX_TOKENS, "temperature": 0.1}

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

    # ------------------------------------------------------------------
    # Degrade path
    # ------------------------------------------------------------------

    def _enqueue_degrade(self, script: str, project_id: str, reason: str) -> None:
        """Push a failed script into the review queue (daily cap enforced)."""
        try:
            pseudo_path = f"script:{project_id or 'untitled'}:{abs(hash(script)) % 100000}"
            ReviewQueue().enqueue(
                file_path=pseudo_path,
                reason=f"director failed: {reason}",
                category_hint="prompt_machine",
                batch_group="director-degrade",
            )
            logger.warning("Director degrade enqueued: %s", pseudo_path)
        except Exception as e:  # never let the degrade path take the API down
            logger.error("Review queue enqueue failed: %s", e)
