import os
import json
import logging
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

# We use the VertexAI/Gemini adapter for reasoning
from vision_analyzer import VisionAnalyzer
# from gemini_vision_adapter import get_adapter # Removing unused/incorrect import

# For local generation routing
import requests
from hybrid_librarian import HybridLibrarian  # To access hybrid config if needed, or read directly

logger = logging.getLogger(__name__)

# --- Data Models (matching TS interfaces) ---

class VeoScenePlanBeat(BaseModel):
    beat_id: str
    label: str
    priority: float
    min_s: float
    max_s: float

class VeoExtendPolicy(BaseModel):
    allow_extend: bool
    extend_granularity_s: float
    criteria: List[str]

class VeoScenePlan(BaseModel):
    scene_id: str
    scene_title: str
    goal_runtime_s: int
    beats: List[VeoScenePlanBeat]
    extend_policy: VeoExtendPolicy

class VeoShotScene(BaseModel):
    context: str
    visual_style: str
    lighting: str
    mood: str
    aspect_ratio: str
    duration_s: int

class VeoShotCharacter(BaseModel):
    name: str
    gender_age: str
    description_lock: str
    behavior: str
    expression: str

class VeoShotCamera(BaseModel):
    shot_call: str
    movement: str
    negatives: str

class VeoShotAudio(BaseModel):
    dialogue: str
    delivery: str
    ambience: str
    sfx: str

class VeoShotFlags(BaseModel):
    continuity_lock: bool
    do_not: List[str] = []
    anti_artifacts: List[str] = []
    conflicts: List[str] = []
    warnings: List[str] = []
    cv_updates: List[str] = []

class VeoShot(BaseModel):
    shot_id: str
    scene: VeoShotScene
    character: VeoShotCharacter
    camera: VeoShotCamera
    audio: VeoShotAudio
    flags: VeoShotFlags

class VeoShotWrapper(BaseModel):
    unit_type: str  # 'shot' | 'extend'
    chain_id: Optional[str] = None
    segment_number: Optional[int] = None
    segment_count: Optional[int] = None
    target_duration_s: Optional[int] = None
    stitching_notes: Optional[str] = None
    clip_strategy: Optional[str] = None
    directorNotes: Optional[str] = None
    veo_shot: VeoShot


# --- SYSTEM PROMPTS (Ported from TS) ---

SYSTEM_PROMPT_PROJECT_NAME = """
You are a creative assistant. Your task is to read the provided creative script or treatment and generate a short, descriptive, filesystem-safe project name.
The name should be in kebab-case (all lowercase, words separated by hyphens).
For example, if the script is about a robot detective in neo-tokyo, a good name would be 'robot-detective-neo-tokyo'.
The name should be concise, ideally 2-5 words.
Your output MUST be only the generated name string, with no other text or explanation.
"""

SYSTEM_PROMPT_SHOTLIST = """
You are a Script Analysis Engine. Your task is to break down the provided creative input (script, treatment, or concept) into a sequence of discrete shots.
For each shot, provide a unique 'shot_id' (e.g., 'ep1_scene1_shot1') and a concise, 1-2 sentence natural language 'pitch' describing the shot's action and mood.
Your final output MUST be a single, valid JSON array of objects, where each object contains only the 'shot_id' and 'pitch' keys. Do not output any other text or explanation.
"""

SYSTEM_PROMPT_SCENE_NAME = """
You are a creative assistant. Your task is to analyze the provided script context and a list of shot pitches that belong to a single scene, then generate a short, descriptive, filesystem-safe name for that scene.
The name should be in kebab-case (all lowercase, words separated by hyphens).
The name should be concise, ideally 2-4 words.
Your output MUST be only the generated name string, with no other text or explanation.
"""

SYSTEM_PROMPT_SCENE_PLAN = """
You are a Scene Runtime Planner. Your task is to analyze a creative script and the pitches for shots within a specific scene to produce a coherent JSON scene plan. This plan defines the narrative beats, their target durations, and the rules for extending shots to create longer, continuous sequences.
Your goal is to maximize segment duration and continuity while adhering to the scene's narrative goals.
You MUST follow the provided JSON schema strictly.
"""

SYSTEM_PROMPT_SINGLE_SHOT_JSON = """
You are the DIRECTOR'S FIRST AD AGENT - a Script Analysis Engine that transforms unstructured creative input into structured production specifications optimized for Google’s VEO3.1 video generation system.
YOUR TASK:
1. Read the user's FULL SCRIPT CONTEXT and the SCENE PLAN provided.
2. Based on the FULL SCRIPT CONTEXT, the SCENE PLAN, and the specific PITCH for a single shot, generate ONE complete, valid JSON object that conforms to the WRAPPER_SCHEMA.
3. You MUST use the "extend" unit_type when the SCENE PLAN's 'extend_policy' criteria are met. Otherwise, use the "shot" unit_type.
4. The 'shot_id' in the nested 'veo_shot' object MUST EXACTLY MATCH the provided shot_id.
5. IMPORTANT: Your response MUST be valid JSON. Do NOT repeat the script or scene context in your output. Be concise.

--- WRAPPER_SCHEMA ---
{
  "unit_type": "'shot' | 'extend'",
  "chain_id": "OPTIONAL_STRING",
  "segment_number": "OPTIONAL_INTEGER",
  "segment_count": "OPTIONAL_INTEGER",
  "target_duration_s": "OPTIONAL_INTEGER",
  "stitching_notes": "OPTIONAL_STRING",
  "clip_strategy": "OPTIONAL_STRING",
  "directorNotes": "OPTIONAL_STRING",
  "veo_shot": {
      "shot_id": "STRING",
      "scene": { "context": "STRING", "visual_style": "STRING", "lighting": "STRING", "mood": "STRING", "aspect_ratio": "16:9|9:16", "duration_s": 4|6|8 },
      "character": { "name": "STRING", "gender_age": "STRING", "description_lock": "STRING", "behavior": "STRING", "expression": "STRING" },
      "camera": { "shot_call": "STRING", "movement": "STRING", "negatives": "STRING" },
      "audio": { "dialogue": "STRING", "delivery": "STRING", "ambience": "STRING", "sfx": "STRING" },
      "flags": { "continuity_lock": BOOLEAN, "do_not": [], "anti_artifacts": [], "conflicts": [], "warnings": [], "cv_updates": [] }
  }
}
"""

SYSTEM_PROMPT_KEYFRAME_TEXT = """
You are a Visual Prompt Engineer. Your task is to convert a structured VEO Shot JSON object into a highly descriptive, natural language image generation prompt.
Focus on visual details: lighting, composition, subject appearance, background, and style.
Do not include technical JSON keys or brackets in the output. Just the descriptive text.
"""

SYSTEM_PROMPT_ASSET_EXTRACTION = """
You are a Film Pre-Production Assistant.
Analyze the script and extract a list of key "Assets" (Characters, Locations, Significant Props).
Return a valid JSON object with a key "assets", which is a list of objects.
Each object must have:
- id: string (unique, snake_case, e.g. "hero_car")
- name: string (Human readable)
- type: "character" | "location" | "object"
- description: string (Visual description for image generation)
"""


# --- VeoBrain Logic ---

class VeoBrain:
    def __init__(self, base_dir: str = None):
        self.vision_analyzer = VisionAnalyzer(base_dir=base_dir)
        self.hybrid_config = self._load_hybrid_config(base_dir)

    def _load_hybrid_config(self, base_dir: Optional[str]) -> Dict[str, Any]:
        """Load hybrid config to check for local Flux capability"""
        try:
            config_path = Path("/Users/ryanthomson/Github/ai-file-organizer/hybrid_config.json")
            if config_path.exists():
                with open(config_path) as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to load hybrid config: {e}")
            return {}

    async def generate_project_name(self, script: str) -> str:
        """Generate a kebab-case project name from the script."""
        response = await self.vision_analyzer.generate_text_async(
            prompt=f"Generate a project name for this script: {script[:2000]}...",
            system_instruction=SYSTEM_PROMPT_PROJECT_NAME
        )
        return response.strip()

    async def generate_shot_list(self, script: str) -> List[Dict[str, str]]:
        """Generate a list of shots (shot_id, pitch)."""
        response = await self.vision_analyzer.generate_text_async(
            prompt=f"Analyze this script and generate a shot list JSON:\n\n{script}",
            system_instruction=SYSTEM_PROMPT_SHOTLIST
        )
        # Clean markdown code blocks
        clean_json = response.replace('```json', '').replace('```', '').strip()
        try:
            shot_list = json.loads(clean_json)
            # Normalize list items to ensure they contain shot_id and pitch
            normalized = []
            if isinstance(shot_list, list):
                for item in shot_list:
                    if 'shot_id' in item and 'pitch' in item:
                        normalized.append({
                            'id': item['shot_id'],
                            'shot_id': item['shot_id'],
                            'pitch': item['pitch']
                        })
            return normalized
        except json.JSONDecodeError:
            logger.error("Failed to parse shot list JSON.")
            return []

    async def generate_scene_plan(self, scene_id: str, scene_pitches: str, script: str) -> Dict[str, Any]:
        """Generate a detailed Scene Plan JSON."""
        prompt = f"Scene ID: {scene_id}\n\nShot Pitches:\n{scene_pitches}\n\nFull Script:\n{script}"
        
        response = await self.vision_analyzer.generate_text_async(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT_SCENE_PLAN
        )
        
        clean_json = response.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(clean_json)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse scene plan for {scene_id}")
            # Return a minimal valid fallback? Or raise
            return {"scene_id": scene_id, "error": "Failed to generate plan"}

    async def generate_veo_json(self, pitch: str, shot_id: str, script: str, scene_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate the detailed VEO Shot JSON (The Director Agent)."""
        
        scene_plan_str = json.dumps(scene_plan) if scene_plan else "No Scene Plan"
        content = f"SHOT ID: {shot_id}\nPITCH: {pitch}\nSCENE PLAN: {scene_plan_str}\nSCRIPT: {script}"
        
        response = await self.vision_analyzer.generate_text_async(
            prompt=content,
            system_instruction=SYSTEM_PROMPT_SINGLE_SHOT_JSON
        )
        
        clean_json = response.replace('```json', '').replace('```', '').strip()
        
        try:
             # Basic repair logic if cut off
            if clean_json.strip().startswith('{') and not clean_json.strip().endswith('}'):
                clean_json += '}'
            
            return json.loads(clean_json)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse VEO JSON for shot {shot_id}")
            return {}

    async def generate_keyframe_prompt(self, veo_shot: Dict[str, Any]) -> str:
        """Convert VEO JSON to a text prompt for image generation."""
        response = await self.vision_analyzer.generate_text_async(
            prompt=json.dumps(veo_shot),
            system_instruction=SYSTEM_PROMPT_KEYFRAME_TEXT
        )
        return response.strip()

    async def generate_keyframe_image(self, prompt: str, aspect_ratio: str = "16:9", ingredients: List[Dict[str, Any]] = []) -> str:
        """
        Generate a keyframe image.
        Uses Local Flux (on 5090) if available/configured, otherwise falls back to Gemini Imagen.
        """
        if ingredients:
            logger.info(f"🎨 Received {len(ingredients)} asset ingredients for generation.")

        
        # 1. Check Local Flux Availability (RTX 5090)
        local_service = self.hybrid_config.get('services', {}).get('flux', {})
        if local_service.get('enabled', False):
            try:
                ip = local_service.get('ip', '100.102.52.93')
                port = local_service.get('port', 8188) # ComfyUI default
                
                logger.info(f"🎨 Routing Image Gen to Local Powerhouse: {ip}:{port}")
                
                # Assume a ComfyUI /simple endpoint or similar wrapper payload
                # For this MVP, we'll try a generic POST to the configured endpoint
                # If using raw ComfyUI API, the payload is complex. 
                # Assuming user has an 'api/generate' wrapper on the 5090 side.
                
                payload = {
                    "prompt": prompt,
                    "width": 1920 if aspect_ratio == "16:9" else 1024,
                    "height": 1080 if aspect_ratio == "16:9" else 1024,
                    "ingredients": ingredients
                }
                
                resp = requests.post(f"http://{ip}:{port}/generate", json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    # Expecting base64 image in response
                    if 'image_base64' in data:
                        return data['image_base64']
                        
            except Exception as e:
                logger.warning(f"⚠️ Local Flux generation failed: {e}. Falling back to Cloud.")

        # 2. Cloud Fallback (Gemini/Imagen)
        logger.info("☁️ Using Gemini 3 Pro / Imagen for Image Generation")
        
        # Use existing vision_analyzer for image generation (assuming it has this capability configured)
        # Note: 'generate_image' might not be fully exposed in VisionAnalyzer yet, 
        # so we might need to access the VertexAI/GenAI model directly here.
        
        # Simulating Cloud Gen via prompt for now if method not found on analyzer
        if hasattr(self.vision_analyzer, 'generate_image'):
            return await self.vision_analyzer.generate_image(prompt, aspect_ratio)
        
        return "" # Placeholder if no gen available

    async def generate_assets_from_script(self, script: str) -> List[Dict[str, Any]]:
        """Extract assets (characters, locations) from the script."""
        response = await self.vision_analyzer.generate_text_async(
            prompt=f"Extract assets from this script:\n\n{script}",
            system_instruction=SYSTEM_PROMPT_ASSET_EXTRACTION
        )
        
        clean_json = response.replace('```json', '').replace('```', '').strip()
        try:
            data = json.loads(clean_json)
            # Normalize: Ensure list of assets.
            # If root is list, return it. If root has 'assets' key, return that.
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and 'assets' in data:
                return data['assets']
            return []
        except json.JSONDecodeError:
            logger.error("Failed to parse assets JSON.")
            return []

