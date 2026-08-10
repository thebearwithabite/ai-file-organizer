"""Prompt Machine API routes (PROMPT-MACHINE-DIRECTIVE v1.2, Phase 1).

UI → FastAPI → services only. No filesystem, storage, or shutil calls here.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.director_service import DirectorService
from backend.services.shot_spec import ScenePlan, ShotSpec

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompt-machine", tags=["prompt-machine"])

_director_service = None


def _get_director() -> DirectorService:
    global _director_service
    if _director_service is None:
        _director_service = DirectorService()
    return _director_service


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AnalyzeScriptRequest(BaseModel):
    script: str = Field(..., min_length=10, description="Script text (.txt/.md/.fountain/.pdf content)")
    project_id: str = Field("", description="Optional project identifier")
    allow_cloud_script: bool = Field(
        False,
        description="Allow script body to reach the cloud fallback (DeepSeek). "
        "Default False: scripts are creative IP — shot-level metadata may go "
        "cloud, verbatim script text only with explicit consent.",
    )


class GenerateShotListRequest(AnalyzeScriptRequest):
    pass


class ScenePlanResponse(BaseModel):
    plan: ScenePlan
    provider: str
    degraded: bool
    reason: str = ""


class ShotListResponse(BaseModel):
    shots: list[ShotSpec]
    provider: str
    degraded: bool
    reason: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/analyze-script", response_model=ScenePlanResponse)
def analyze_script(req: AnalyzeScriptRequest) -> ScenePlanResponse:
    result = _get_director().analyze_script(
        script=req.script,
        project_id=req.project_id,
        allow_cloud_script=req.allow_cloud_script,
    )
    return ScenePlanResponse(**result)


@router.post("/generate-shot-list", response_model=ShotListResponse)
def generate_shot_list(req: GenerateShotListRequest) -> ShotListResponse:
    result = _get_director().generate_shot_list(
        script=req.script,
        project_id=req.project_id,
        allow_cloud_script=req.allow_cloud_script,
    )
    return ShotListResponse(
        shots=result.shots,
        provider=result.provider,
        degraded=result.degraded,
        reason=result.reason,
    )
