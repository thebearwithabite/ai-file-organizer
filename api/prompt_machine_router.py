"""Prompt Machine API routes (PROMPT-MACHINE-DIRECTIVE v1.2, Phase 1 + Phase 2).

UI → FastAPI → services only. No filesystem, storage, or shutil calls here —
ref images land via AssetService → StorageProvider (no side doors).
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.services.asset_service import AssetService
from backend.services.director_service import DirectorService
from backend.services.shot_spec import ScenePlan, ShotSpec

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompt-machine", tags=["prompt-machine"])

_director_service = None
_asset_service = None


def _get_director() -> DirectorService:
    global _director_service
    if _director_service is None:
        _director_service = DirectorService()
    return _director_service


def _get_assets() -> AssetService:
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service


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


class ExtractAssetsRequest(AnalyzeScriptRequest):
    pass


class AssetResponse(BaseModel):
    asset_id: str
    name: str
    type: str
    description: str = ""
    lora_path: Optional[str] = None
    trigger_token: Optional[str] = None
    ref_image: Optional[str] = None
    weight: float = 0.9


class ExtractAssetsResponse(BaseModel):
    assets: List[AssetResponse]
    provider: str
    degraded: bool
    reason: str = ""


class AutoBindRequest(BaseModel):
    project_id: str = Field("", description="Bind assets to shots of this project (empty = all)")


class AutoBindResponse(BaseModel):
    shot_count: int
    bindings: dict


class UpdateAssetRequest(BaseModel):
    lora_path: Optional[str] = Field(None, description="Empty string clears")
    trigger_token: Optional[str] = Field(None, description="Empty string clears")
    ref_image: Optional[str] = Field(None, description="StorageRef uri. Prefer the upload endpoint.")


class ToggleAssetRequest(BaseModel):
    asset_id: str
    selected: bool = True


class ToggleAssetResponse(BaseModel):
    shot_id: str
    assets: List[dict]


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


# ---------------------------------------------------------------------------
# Phase 2 — assets
# ---------------------------------------------------------------------------


@router.post("/extract-assets", response_model=ExtractAssetsResponse)
def extract_assets(req: ExtractAssetsRequest) -> ExtractAssetsResponse:
    result = _get_assets().extract_assets(
        script=req.script,
        project_id=req.project_id,
        allow_cloud_script=req.allow_cloud_script,
    )
    return ExtractAssetsResponse(
        assets=[AssetResponse(**a.model_dump()) for a in result.assets],
        provider=result.provider,
        degraded=result.degraded,
        reason=result.reason,
    )


@router.post("/auto-bind-assets", response_model=AutoBindResponse)
def auto_bind_assets(req: AutoBindRequest) -> AutoBindResponse:
    result = _get_assets().auto_bind(project_id=req.project_id)
    return AutoBindResponse(shot_count=result["shots"], bindings=result["bindings"])


@router.get("/assets", response_model=List[AssetResponse])
def list_assets(project_id: str = "") -> List[AssetResponse]:
    return [AssetResponse(**a) for a in _get_assets().list_assets(project_id)]


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: str, req: UpdateAssetRequest) -> AssetResponse:
    row = _get_assets().update_asset(
        asset_id,
        lora_path=req.lora_path,
        trigger_token=req.trigger_token,
        ref_image=req.ref_image,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return AssetResponse(**row)


@router.post("/assets/{asset_id}/ref-image", response_model=AssetResponse)
async def upload_ref_image(asset_id: str, file: UploadFile = File(...)) -> AssetResponse:
    suffix = Path(file.filename or "ref.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        uri = _get_assets().store_ref_image(asset_id, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    row = _get_assets().get_asset(asset_id)
    if uri is None or row is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return AssetResponse(**row)


@router.post("/shots/{shot_id}/assets", response_model=ToggleAssetResponse)
def toggle_asset(shot_id: str, req: ToggleAssetRequest) -> ToggleAssetResponse:
    result = _get_assets().toggle_shot_asset(shot_id, req.asset_id, req.selected)
    if result is None:
        raise HTTPException(status_code=404, detail="shot not found")
    return ToggleAssetResponse(**result)
