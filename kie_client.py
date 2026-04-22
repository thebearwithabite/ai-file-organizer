import os
import logging
import requests
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.kie.ai/api/v1/veo'

# --- Data Models ---

class KieGenerateRequest(BaseModel):
    prompt: str
    model: str = "veo3_fast"
    aspectRatio: str = "16:9"  # '16:9' | '9:16' | 'Auto'
    generationType: Optional[str] = None # 'TEXT_2_VIDEO' | 'FIRST_AND_LAST_FRAMES_2_VIDEO' | 'REFERENCE_2_VIDEO'
    imageUrls: Optional[List[str]] = None
    seeds: Optional[int] = None
    watermark: Optional[str] = None
    enableTranslation: bool = True

class KieExtendRequest(BaseModel):
    taskId: str
    prompt: str
    seeds: Optional[int] = None
    watermark: Optional[str] = None
    callBackUrl: Optional[str] = None

class KieClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("KIE_API_KEY")
        if not self.api_key:
            logger.warning("⚠️ KIE_API_KEY not found. Video generation will fail.")

    def _headers(self):
        if not self.api_key:
            raise ValueError("KIE_API_KEY is not configured.")
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    def generate_video(self, params: KieGenerateRequest) -> Dict[str, Any]:
        """Generate a video using Veo 3.1 via KIE.ai"""
        url = f"{BASE_URL}/generate"
        
        # Determine generation type if not set
        if not params.generationType:
            if params.imageUrls and len(params.imageUrls) > 0:
                params.generationType = 'REFERENCE_2_VIDEO'
            else:
                params.generationType = 'TEXT_2_VIDEO'

        try:
            logger.info(f"🎬 KIE Generate Request: {params.dict(exclude_none=True)}")
            response = requests.post(
                url, 
                headers=self._headers(), 
                json=params.dict(exclude_none=True),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 200:
                raise Exception(f"KIE API Error ({data.get('code')}): {data.get('msg')}")
                
            return data
            
        except Exception as e:
            logger.error(f"❌ KIE Generate Failed: {e}")
            raise

    def extend_video(self, params: KieExtendRequest) -> Dict[str, Any]:
        """Extend an existing video task"""
        url = f"{BASE_URL}/extend"
        
        try:
            logger.info(f"🎬 KIE Extend Request: {params.dict(exclude_none=True)}")
            response = requests.post(
                url, 
                headers=self._headers(), 
                json=params.dict(exclude_none=True),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 200:
                raise Exception(f"KIE API Error ({data.get('code')}): {data.get('msg')}")
                
            return data
            
        except Exception as e:
            logger.error(f"❌ KIE Extend Failed: {e}")
            raise

    def get_task_details(self, task_id: str) -> Dict[str, Any]:
        """Check status of a generation task"""
        url = f"{BASE_URL}/record-info"
        
        try:
            response = requests.get(
                url, 
                headers=self._headers(), 
                params={'taskId': task_id},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ KIE Status Check Failed: {e}")
            raise

# Singleton instance
_kie_client = None

def get_kie_client():
    global _kie_client
    if _kie_client is None:
        _kie_client = KieClient()
    return _kie_client
