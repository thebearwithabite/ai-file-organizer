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

from backend.llm import LLMProvider, OllamaClient
from backend.llm.errors import DegradedRoutingError, InvalidLLMOutputError
from backend.services.llm_resolver import (
    DIRECTOR_LOCAL_FALLBACK_MODEL,
    DegradeReason,
    enqueue_llm_degrade,
    provider_kwargs,
)
from backend.services.llm_router import LLMRouter, RouteMetrics, build_cloud_client

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
    "narrative_intent": "Maya finds the letter and the room's cheer drops away.",
    "setting": "The rented studio kitchen at dawn, one cardboard box half unpacked.",
    "action": "Maya walks in, slows at the counter, and picks up the envelope with both hands.",
    "lighting": "soft morning window light from the left, weak bounce fill from the right",
    "style_grade": "naturalistic handheld documentary, slightly desaturated, fine film grain",
    "duration_seconds": 6.0,
    "camera": {
        "framing": "Eye-Level Medium Close-Up",
        "movement": "slow push-in",
        "lens_feel": "85mm, shallow depth of field",
    },
    "entities": [
        {
            "entity_id": "char_maya",
            "name": "Maya",
            "kind": "character",
            "description": "woman, mid-30s, shoulder-length dark hair parted left, grey knit sweater, silver ring on the right hand",
            "reference_images": [],
            "expression_cues": "eyebrows draw together, lips press into a thin line, fingers still on the envelope",
        }
    ],
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
    "seed": -1,
    "notes": "",
}


@dataclass
class ShotListResult:
    shots: List[ShotSpec] = field(default_factory=list)
    provider: str = "none"
    degraded: bool = False
    reason: str = ""


class DirectorService:
    """Breaks scripts into scene plans and validated shot lists."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        provider: Optional[LLMProvider] = None,
        router: Optional[LLMRouter] = None,
        render_state=None,
    ):
        if db_path is None:
            db_path = get_metadata_root() / "organizer.db"
        self.db_path = db_path
        self._provider = provider  # injected local client (tests); otherwise Ollama
        self._router = router  # explicit routing layer (tests / production wiring)
        self._render_state = render_state  # renderer job state — never a VRAM guess
        self._metrics = RouteMetrics()
        self._default_routers: dict = {}
        self._init_shots_table()

    def _router_for(self, allow_cloud_script: bool) -> LLMRouter:
        """Routing layer for one call: local-first, cloud only with consent + key.

        ``render_state`` is the renderer's job state (or an ExplicitRenderFlag
        the renderer client sets). When it is not wired the router says so in
        its reason strings and assumes idle, so keyless local runs keep working.
        """
        if self._router is not None:
            return self._router
        router = self._default_routers.get(allow_cloud_script)
        if router is None:
            local = (
                self._provider
                if self._provider is not None
                else OllamaClient(model=DIRECTOR_LOCAL_FALLBACK_MODEL)
            )
            cloud = None
            cloud_note = "cloud fallback disabled for this call (allow_cloud_script=False)"
            if allow_cloud_script:
                from secret_manager import get_secret

                cloud, cloud_note = build_cloud_client(secret_loader=get_secret)
            router = LLMRouter(
                local=local,
                cloud=cloud,
                render_state=self._render_state,
                cloud_note=cloud_note if cloud is None else "",
                metrics=self._metrics,
            )
            self._default_routers[allow_cloud_script] = router
        return router

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
        router = self._router_for(allow_cloud_script)
        prompt = self._build_scene_plan_prompt(script)

        try:
            routed = router.complete_structured(
                prompt,
                ScenePlan,
                job="director.scene_plan",
                kwargs_for=lambda provider_name: provider_kwargs(provider_name),
            )
        except DegradedRoutingError as e:
            enqueue_llm_degrade(
                script, project_id, f"no usable LLM route: {e}",
                degrade_reason=DegradeReason.provider_unreachable.value,
            )
            return {"plan": ScenePlan(), "provider": "none", "degraded": True, "reason": str(e)}
        except InvalidLLMOutputError as e:
            enqueue_llm_degrade(
                script, project_id, f"scene plan failed schema validation ({e.provider})",
                degrade_reason=DegradeReason.schema_invalid.value,
            )
            return {"plan": ScenePlan(), "provider": e.provider, "degraded": True,
                    "reason": f"scene plan generation failed schema validation ({e.provider}) after {e.attempts} attempts"}

        return {"plan": routed.value, "provider": routed.record.provider, "degraded": False, "reason": ""}

    # ------------------------------------------------------------------
    # Shot list
    # ------------------------------------------------------------------

    def generate_shot_list(
        self,
        script: str,
        project_id: str = "",
        allow_cloud_script: bool = False,
    ) -> ShotListResult:
        """Script → validated ShotSpec[] (one repair retry, typed errors, degrade-to-queue)."""
        router = self._router_for(allow_cloud_script)
        prompt = self._build_shot_list_prompt(script)

        try:
            routed = router.director_shot_list(
                prompt,
                kwargs_for=lambda provider_name: provider_kwargs(provider_name),
            )
        except DegradedRoutingError as e:
            enqueue_llm_degrade(
                script, project_id, f"no usable LLM route: {e}",
                degrade_reason=DegradeReason.provider_unreachable.value,
            )
            return ShotListResult(provider="none", degraded=True, reason=str(e))
        except InvalidLLMOutputError as e:
            enqueue_llm_degrade(
                script, project_id, f"shot list failed schema validation ({e.provider})",
                degrade_reason=DegradeReason.schema_invalid.value,
            )
            first = (
                f"; first error: {e.errors[0]['path']}: {e.errors[0]['reason']}"
                if e.errors else ""
            )
            return ShotListResult(provider=e.provider, degraded=True,
                                  reason=f"shot list generation failed schema validation ({e.provider}) after {e.attempts} attempts{first}")

        shots = routed.value.shots
        # Normalize project_id + sequence index before persisting
        for i, shot in enumerate(shots):
            shot.project_id = project_id or shot.project_id
            shot.sequence_index = i
        self._persist_shots(shots, project_id)
        return ShotListResult(shots=shots, provider=routed.record.provider, degraded=False, reason="")

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

PROMPT GUIDE (your setting/lighting/entities/camera/audio fields are engine-neutral; a prompt compiler turns them into per-engine prompts later, so describe them precisely now):
{ltx_guide or "(none loaded)"}

TASK: Break the script into 6-12 shots. One clear dramatic action per shot. Produce STRICT JSON matching exactly this shape:
{{"shots": [<ShotSpec objects>]}}

Each ShotSpec object has EXACTLY this shape (copy the keys verbatim; adapt values to the script):
{schema_hint}

Hard constraints:
- shot_id format: "sc##_sh##" where ## is a two-digit number (sc01_sh01, sc02_sh03). Unique across the list.
- sequence_index: 0-based, in order.
- entities: one entry per subject present (characters, locations, props). entity_id is a lowercase
  underscore slug ("char_maya", "loc_kitchen") and MUST be identical every time the same subject
  appears across shots — that repeated id/name/description is what keeps a recurring character consistent.
- entities[].expression_cues: PHYSICAL cues only — facial/body action. NEVER emotion labels
  (happy, sad, angry, scared, excited, etc.). Write "eyebrows draw together", not "looks worried".
- narrative_intent: one sentence on what this shot must accomplish dramatically.
- action: the visible action, one clear beat. Not a summary of the scene.
- audio.dialogue: quote exact spoken lines with double quotes inside the string. Empty string if the shot has no dialogue.
- camera.framing: use standard framing vocabulary (Extreme Wide, Wide, Medium, Close-Up, Extreme Close-Up, etc.).
- lighting: one coherent lighting description — never conflicting sources.
- duration_seconds: a positive number of seconds. Aim for 3-10s per shot, but the field accepts any
  positive value — do not invent a cap and do not clamp.
- assets: include one entry per character present, type "character", weight 0.9. No lora_path,
  trigger_token, or ref_image for now (null).
- Do NOT add any "generation", "engine", "template", or "prompt" field. ShotSpec is engine-neutral;
  per-engine payloads are produced later by the prompt compiler.
- Output ONLY the JSON object. No markdown fences, no commentary, no trailing text.

SCRIPT:
{script}
"""
