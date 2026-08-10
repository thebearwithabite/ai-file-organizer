"""ShotSpec — engine-neutral shot schema (PROMPT-MACHINE-DIRECTIVE v1.2).

Stored in SQLite, validated by Pydantic, shared by the frontend, the director
service, and the prompt compiler. Engine-neutral by design: the compiler
emits per-engine payloads (LTX prose, WanGP settings, ComfyUI workflows).

Key design lock: ``expression_cues`` is physical cues only — no emotion
labels. LTX renders physical action, not adjectives. The validator rejects
emotion adjectives so schema violations drive the LLM retry loop.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# Emotion adjectives that must never appear in character.expression_cues.
# Whole-word, case-insensitive match. Keep unambiguous emotion labels only —
# dispositional words that double as physical demeanor (serious, thoughtful,
# calm, determined, playful) stay allowed.
EMOTION_LABELS = frozenset({
    "happy", "sad", "angry", "afraid", "scared", "excited", "nervous",
    "anxious", "joyful", "furious", "surprised", "confused", "worried",
    "pleased", "annoyed", "frustrated", "hopeful", "relieved", "bored",
    "disgusted", "jealous", "proud", "ashamed", "guilty", "lonely",
    "thrilled", "terrified", "depressed", "irritated", "upset", "glad",
    "delighted", "miserable", "embarrassed", "suspicious", "eager", "shy",
    "content",
})


class ShotStatus(str, Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    regen_requested = "regen_requested"


class AssetType(str, Enum):
    character = "character"
    location = "location"
    prop = "prop"
    style = "style"


class SceneSpec(BaseModel):
    context: str = Field(..., description="What happens in the scene")
    visual_style: str = Field(..., description="Look and feel of the imagery")
    lighting: str = Field(..., description="Lighting description (one coherent key)")
    mood: str = Field(..., description="Mood / atmosphere of the scene")
    duration_s: float = Field(6.0, ge=0.5, le=30.0, description="Target duration in seconds")
    aspect_ratio: str = Field("16:9", pattern=r"^\d+:\d+$")


class CharacterSpec(BaseModel):
    name: str = Field(..., description="Character name")
    gender_age: str = Field("", description="e.g. 'woman, mid-30s'")
    physical_description: str = Field("", description="Stable physical appearance (consistency across shots)")
    behavior: str = Field("", description="How the character moves and acts")
    expression_cues: str = Field(
        ...,
        description="PHYSICAL cues only — facial/body action, no emotion labels "
        "(never: happy, sad, angry, scared, etc.)",
    )

    @field_validator("expression_cues")
    @classmethod
    def _no_emotion_labels(cls, v: str) -> str:
        if not v:
            return v
        words = set(re.findall(r"[a-z']+", v.lower()))
        hits = sorted(words & EMOTION_LABELS)
        if hits:
            raise ValueError(
                f"expression_cues must be physical cues only, no emotion labels; "
                f"found: {', '.join(hits)}"
            )
        return v


class CameraSpec(BaseModel):
    shot_call: str = Field(..., description="e.g. 'Eye-Level Close-Up', 'Low-Angle Wide'")
    movement: str = Field("", description="Camera movement, e.g. 'slow dolly in'")
    negatives: str = Field("", description="What to avoid in the frame")


class AudioSpec(BaseModel):
    dialogue: str = Field("", description="Quoted speech, e.g. '\"That's it... Dad's lost it.\"'")
    delivery: str = Field("", description="Delivery notes (tone, pacing — physical, not emotional)")
    ambience: str = Field("", description="Room tone / environmental sound")
    sfx: str = Field("", description="Sound effects")


class AssetBinding(BaseModel):
    asset_id: str = Field(..., description="Reference to a veo_assets row")
    type: AssetType = AssetType.character
    lora_path: Optional[str] = None
    trigger_token: Optional[str] = None
    ref_image: Optional[str] = Field(None, description="StorageRef to a reference image")
    weight: float = Field(0.9, ge=0.0, le=1.0, description="Character 0.8-1.0, scene 0.5-0.7, effect 0.3-0.6")


class GenerationSpec(BaseModel):
    engine: str = Field("wangp", pattern="^(wangp|comfyui)$")
    template_id: str = Field("LTX-2 2.3 Distilled")
    overrides: dict = Field(default_factory=dict, description="Bounded overrides only: width, height, num_frames, fps, num_inference_steps, loras")
    seed: int = Field(-1)
    comfy_workflow_id: Optional[str] = None


class ShotSpec(BaseModel):
    project_id: str = Field("", description="Optional project identifier")
    shot_id: str = Field(..., pattern=r"^sc\d+_sh\d+$", description="e.g. sc01_sh01")
    sequence_index: int = Field(0, ge=0)
    status: ShotStatus = ShotStatus.draft
    version: int = Field(1, ge=1)
    scene: SceneSpec
    character: CharacterSpec
    camera: CameraSpec
    audio: AudioSpec = Field(default_factory=AudioSpec)
    assets: List[AssetBinding] = Field(default_factory=list)
    generation: GenerationSpec = Field(default_factory=GenerationSpec)


class ScenePlanScene(BaseModel):
    """One scene from the engine-agnostic scene plan (veo_latest generateScenePlan port)."""
    scene_id: str = Field(..., description="e.g. 'sc01'")
    summary: str = Field(..., description="One-paragraph beat summary")
    runtime_goal_s: float = Field(0.0, ge=0.0, description="Target runtime in seconds")
    extend_policy: str = Field("", description="How this scene extends: continuation | montage | standalone")


class ScenePlan(BaseModel):
    title: str = Field("", description="Suggested project title")
    scenes: List[ScenePlanScene] = Field(default_factory=list)
    total_runtime_s: float = Field(0.0, ge=0.0)


class ShotListOutput(BaseModel):
    """LLM output wrapper for the director pass: validated ShotSpec[]."""
    shots: List[ShotSpec] = Field(default_factory=list)
