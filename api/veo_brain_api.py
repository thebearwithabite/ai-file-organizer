"""
VEO Brain API - Brain Generation & KIE Video Endpoints
Split from veo_api.py - contains brain generation and video generation endpoints.
Requires veo_brain.py and kie_client.py to be present.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from veo_brain import VeoBrain
from kie_client import get_kie_client, KieGenerateRequest, KieExtendRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/veo", tags=["veo-brain"])

_veo_brain = None

def get_veo_brain():
    global _veo_brain
    if _veo_brain is None:
        _veo_brain = VeoBrain()
    return _veo_brain

class ScriptInput(BaseModel):
    script: str

class ShotListInput(BaseModel):
    scene_id: str
    scene_pitches: str
    script: str

class VeoShotGenInput(BaseModel):
    pitch: str
    shot_id: str
    script: str
    scene_plan: Optional[Dict[str, Any]] = None

class KeyframeGenInput(BaseModel):
    prompt: Optional[str] = None
    veo_shot: Optional[Dict[str, Any]] = None
    aspect_ratio: str = "16:9"
    ingredients: List[Dict[str, Any]] = []

@router.post("/generate/keyframe")
async def generate_keyframe_endpoint(input_data: KeyframeGenInput):
    brain = get_veo_brain()
    prompt = input_data.prompt
    if not prompt and input_data.veo_shot:
        prompt = await brain.generate_keyframe_prompt(input_data.veo_shot)
    if not prompt:
        raise HTTPException(status_code=400, detail="Must provide prompt or veo_shot")
    image_base64 = await brain.generate_keyframe_image(
        prompt, aspect_ratio=input_data.aspect_ratio, ingredients=input_data.ingredients
    )
    return {"result": image_base64, "prompt_used": prompt}

@router.post("/video/generate")
async def generate_video_endpoint(request: KieGenerateRequest):
    client = get_kie_client()
    try:
        return client.generate_video(request)
    except ValueError:
        raise HTTPException(status_code=503, detail="Video generation unavailable (Missing API Key)")
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video/extend")
async def extend_video_endpoint(request: KieExtendRequest):
    client = get_kie_client()
    try:
        return client.extend_video(request)
    except ValueError:
        raise HTTPException(status_code=503, detail="Video generation unavailable (Missing API Key)")
    except Exception as e:
        logger.error(f"Video extension failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video/status/{task_id}")
async def get_video_status_endpoint(task_id: str):
    client = get_kie_client()
    try:
        return client.get_task_details(task_id)
    except ValueError:
        raise HTTPException(status_code=503, detail="Video generation unavailable (Missing API Key)")
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

__all__ = ['router']
