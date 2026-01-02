"""
VEO API - Vision & Learning Prompt Management
Part of Sprint 2.0 - Task 2.2

FastAPI endpoints for managing VEO (Vision Enhancement Optimization) prompts
and learning data from Gemini Vision analyses.

Endpoints:
- GET /api/veo/prompts - List stored prompts
- POST /api/veo/prompts - Store new vision analysis
- POST /api/clip/{id}/reanalyze - Re-run analysis on existing clip

Created by: RT Max / Claude Code
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

# Import our adapter and components
from gemini_vision_adapter import (
    GeminiVisionAdapter,
    LearningPromptInput,
    create_adapter_with_learning,
    analyze_and_learn
)
from api.resolve_service import resolve_instance

logger = logging.getLogger(__name__)

# Database path - local metadata system only
from gdrive_integration import get_metadata_root
DB_PATH = get_metadata_root() / "databases" / "metadata.db"

# Create routers
router = APIRouter(prefix="/api/veo", tags=["veo"])
clip_router = APIRouter(prefix="/api", tags=["clips"])

# Initialize adapter (lazy initialization)
_adapter = None


def get_adapter() -> GeminiVisionAdapter:
    """Get or create the global adapter instance"""
    global _adapter
    if _adapter is None:
        _adapter = create_adapter_with_learning()
        logger.info("VEO Adapter initialized")
    return _adapter


# ===== Pydantic Models =====

class VEOPromptInput(BaseModel):
    """Input model for creating new VEO prompts"""
    file_path: str
    predicted_category: str
    confidence: float
    features: Dict[str, Any]
    media_type: str  # 'image' or 'video'
    source: str = "api"


class VEOPromptResponse(BaseModel):
    """Response model for VEO prompts"""
    id: int
    file_path: str
    predicted_category: str
    confidence: float
    features: Dict[str, Any]
    media_type: str
    source: str
    timestamp: str
    event_id: Optional[str] = None


class ReanalyzeRequest(BaseModel):
    """Request model for reanalysis"""
    force: bool = False  # Force reanalysis even if cached


# ===== Database Functions =====

def init_veo_prompts_table():
    """
    Initialize veo_prompts table if it doesn't exist.

    Schema supports:
    - Both image and video prompts
    - Learning metadata
    - Feature storage as JSON
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS veo_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    predicted_category TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    features TEXT NOT NULL,  -- JSON blob
                    media_type TEXT NOT NULL,  -- 'image' or 'video'
                    source TEXT NOT NULL,  -- 'gemini_vision', 'veo_prompt', 'api', etc.
                    timestamp TEXT NOT NULL,
                    event_id TEXT,  -- Learning system event ID
                    UNIQUE(file_path, timestamp)
                )
            """)

            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_veo_prompts_file_path
                ON veo_prompts(file_path)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_veo_prompts_media_type
                ON veo_prompts(media_type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_veo_prompts_timestamp
                ON veo_prompts(timestamp)
            """)

            conn.commit()
            logger.info("VEO prompts table initialized")

    except Exception as e:
        logger.error(f"Failed to initialize veo_prompts table: {e}")
        raise


def insert_veo_prompt(prompt_input: LearningPromptInput, event_id: Optional[str] = None) -> int:
    """
    Insert a new VEO prompt into the database.

    Args:
        prompt_input: LearningPromptInput from adapter
        event_id: Optional learning system event ID

    Returns:
        Database row ID
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO veo_prompts
                (file_path, predicted_category, confidence, features, media_type, source, timestamp, event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prompt_input.file_path,
                prompt_input.predicted_category,
                prompt_input.confidence,
                json.dumps(prompt_input.features),
                prompt_input.media_type,
                prompt_input.source,
                prompt_input.timestamp,
                event_id
            ))

            conn.commit()
            row_id = cursor.lastrowid

            logger.info(f"Inserted VEO prompt: ID={row_id}, file={Path(prompt_input.file_path).name}")
            return row_id

    except sqlite3.IntegrityError as e:
        logger.warning(f"Duplicate VEO prompt entry: {e}")
        raise HTTPException(status_code=409, detail="Prompt already exists for this file and timestamp")
    except Exception as e:
        logger.error(f"Failed to insert VEO prompt: {e}")
        raise HTTPException(status_code=500, detail="Database error")


def store_prompt(prompt_input: LearningPromptInput, event_id: Optional[str] = None,
                confidence_threshold: float = 0.1) -> Dict[str, Any]:
    """
    Smart insert/update logic for VEO prompts.

    Handles repeated file analyses without duplication:
    - Checks if prompt exists for file_path + media_type
    - Updates if confidence change > threshold
    - Skips if no significant change
    - Inserts if new file

    Args:
        prompt_input: LearningPromptInput from adapter
        event_id: Optional learning system event ID
        confidence_threshold: Minimum confidence delta to trigger update (default: 0.1)

    Returns:
        Dict with:
            - id: Database row ID
            - action: 'inserted', 'updated', or 'skipped'
            - confidence_delta: Change in confidence (0 if new)
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Check for existing prompt with same file_path and media_type
            cursor.execute("""
                SELECT id, confidence, predicted_category, features, event_id
                FROM veo_prompts
                WHERE file_path = ? AND media_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (prompt_input.file_path, prompt_input.media_type))

            existing = cursor.fetchone()

            if existing:
                existing_id, existing_confidence, existing_category, existing_features, existing_event_id = existing
                confidence_delta = abs(prompt_input.confidence - existing_confidence)

                # Check if update is warranted
                if confidence_delta > confidence_threshold or existing_category != prompt_input.predicted_category:
                    # Significant change - update existing row
                    cursor.execute("""
                        UPDATE veo_prompts
                        SET predicted_category = ?,
                            confidence = ?,
                            features = ?,
                            source = ?,
                            timestamp = ?,
                            event_id = ?
                        WHERE id = ?
                    """, (
                        prompt_input.predicted_category,
                        prompt_input.confidence,
                        json.dumps(prompt_input.features),
                        prompt_input.source,
                        prompt_input.timestamp,
                        event_id,
                        existing_id
                    ))

                    conn.commit()
                    logger.info(
                        f"Updated VEO prompt: ID={existing_id}, file={Path(prompt_input.file_path).name}, "
                        f"confidence_delta={confidence_delta:.3f}"
                    )

                    return {
                        'id': existing_id,
                        'action': 'updated',
                        'confidence_delta': confidence_delta,
                        'previous_event_id': existing_event_id
                    }
                else:
                    # No significant change - skip
                    logger.info(
                        f"Skipped VEO prompt (no significant change): ID={existing_id}, "
                        f"file={Path(prompt_input.file_path).name}, confidence_delta={confidence_delta:.3f}"
                    )

                    return {
                        'id': existing_id,
                        'action': 'skipped',
                        'confidence_delta': confidence_delta,
                        'previous_event_id': existing_event_id
                    }
            else:
                # New file - insert
                cursor.execute("""
                    INSERT INTO veo_prompts
                    (file_path, predicted_category, confidence, features, media_type, source, timestamp, event_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prompt_input.file_path,
                    prompt_input.predicted_category,
                    prompt_input.confidence,
                    json.dumps(prompt_input.features),
                    prompt_input.media_type,
                    prompt_input.source,
                    prompt_input.timestamp,
                    event_id
                ))

                conn.commit()
                row_id = cursor.lastrowid

                logger.info(f"Inserted new VEO prompt: ID={row_id}, file={Path(prompt_input.file_path).name}")

                return {
                    'id': row_id,
                    'action': 'inserted',
                    'confidence_delta': 0.0,
                    'previous_event_id': None
                }

    except Exception as e:
        logger.error(f"Failed to store VEO prompt: {e}")
        raise HTTPException(status_code=500, detail="Database error")


def get_veo_prompts(
    media_type: Optional[str] = None,
    limit: int = 100,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve VEO prompts from database with optional filtering.

    Args:
        media_type: Filter by 'image' or 'video'
        limit: Maximum number of results
        search: Search term for file_path or category

    Returns:
        List of prompt dictionaries
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Build query with filters
            query = "SELECT * FROM veo_prompts WHERE 1=1"
            params = []

            if media_type:
                query += " AND media_type = ?"
                params.append(media_type)

            if search:
                query += " AND (file_path LIKE ? OR predicted_category LIKE ?)"
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            # Convert rows to dictionaries
            columns = [desc[0] for desc in cursor.description]
            results = []

            for row in cursor.fetchall():
                prompt_dict = dict(zip(columns, row))
                # Parse JSON features
                prompt_dict['features'] = json.loads(prompt_dict['features'])
                results.append(prompt_dict)

            return results

    except Exception as e:
        logger.error(f"Failed to retrieve VEO prompts: {e}")
        raise HTTPException(status_code=500, detail="Database error")


def get_veo_prompt_by_id(prompt_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single VEO prompt by ID.

    Args:
        prompt_id: Database row ID

    Returns:
        Prompt dictionary or None
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM veo_prompts WHERE id = ?", (prompt_id,))
            row = cursor.fetchone()

            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            prompt_dict = dict(zip(columns, row))
            prompt_dict['features'] = json.loads(prompt_dict['features'])

            return prompt_dict

    except Exception as e:
        logger.error(f"Failed to retrieve VEO prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")


# ===== API Endpoints =====

@router.on_event("startup")
async def startup():
    """Initialize database on startup"""
    init_veo_prompts_table()


@router.get("/prompts", response_model=List[VEOPromptResponse])
async def list_prompts(
    media_type: Optional[str] = Query(None, description="Filter by 'image' or 'video'"),
    limit: int = Query(100, description="Maximum number of results", le=500),
    search: Optional[str] = Query(None, description="Search file paths or categories")
):
    """
    Get list of stored VEO prompts with optional filtering.

    Args:
        media_type: Filter by media type ('image' or 'video')
        limit: Maximum results (default 100, max 500)
        search: Search term for filtering

    Returns:
        List of VEO prompts
    """
    try:
        prompts = get_veo_prompts(media_type=media_type, limit=limit, search=search)
        return prompts

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve prompts")


@router.post("/prompts", status_code=201)
async def create_prompt(prompt_input: VEOPromptInput):
    """
    Create or update a VEO prompt from vision analysis.

    This endpoint:
    1. Accepts normalized prompt input
    2. Stores in database (insert/update/skip based on confidence delta)
    3. Emits learning signal only for inserts and updates

    Args:
        prompt_input: VEO prompt data

    Returns:
        Prompt with ID, action taken, and event_id
    """
    try:
        # Convert to LearningPromptInput
        learning_input = LearningPromptInput(
            file_path=prompt_input.file_path,
            predicted_category=prompt_input.predicted_category,
            confidence=prompt_input.confidence,
            features=prompt_input.features,
            media_type=prompt_input.media_type,
            source=prompt_input.source,
            timestamp=datetime.now().isoformat()
        )

        # Store in database (smart insert/update logic)
        store_result = store_prompt(learning_input)

        # Only emit learning signal for inserts and updates, not skips
        event_id = None
        if store_result['action'] in ['inserted', 'updated']:
            adapter = get_adapter()
            event_id = adapter.emit_learning_signal(learning_input)

            # Update the database with the event_id
            if event_id:
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE veo_prompts SET event_id = ? WHERE id = ?",
                        (event_id, store_result['id'])
                    )
                    conn.commit()
        else:
            # Skipped - reuse previous event_id
            event_id = store_result.get('previous_event_id')

        # Return result
        message_map = {
            'inserted': 'Prompt created and learning signal emitted',
            'updated': 'Prompt updated and learning signal emitted',
            'skipped': 'Prompt unchanged (confidence delta < 0.1)'
        }

        return {
            "id": store_result['id'],
            "action": store_result['action'],
            "confidence_delta": store_result['confidence_delta'],
            "event_id": event_id,
            "file_path": learning_input.file_path,
            "predicted_category": learning_input.predicted_category,
            "confidence": learning_input.confidence,
            "features": learning_input.features,
            "media_type": learning_input.media_type,
            "source": learning_input.source,
            "timestamp": learning_input.timestamp,
            "message": message_map[store_result['action']]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create prompt")


@clip_router.post("/clip/{clip_id}/reanalyze")
async def reanalyze_clip(clip_id: int, request: ReanalyzeRequest = ReanalyzeRequest()):
    """
    Re-run Gemini Vision analysis on an existing clip.

    This endpoint:
    1. Looks up the file path from clip_id
    2. Runs analyze_and_learn() from adapter
    3. Stores new analysis result
    4. Emits learning signal

    Args:
        clip_id: Database ID of the clip
        request: Reanalysis options

    Returns:
        New analysis result with updated prompt
    """
    try:
        # Retrieve original prompt
        original_prompt = get_veo_prompt_by_id(clip_id)

        if not original_prompt:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

        file_path = original_prompt['file_path']

        # Verify file exists
        if not Path(file_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {file_path}"
            )

        # Run complete analysis workflow
        logger.info(f"Reanalyzing clip {clip_id}: {file_path}")

        result = analyze_and_learn(file_path)

        # Store new analysis
        learning_result = result['learning']
        prompt_input_dict = learning_result['prompt_input']

        # Convert back to LearningPromptInput for storage
        learning_input = LearningPromptInput(**prompt_input_dict)
        new_prompt_id = insert_veo_prompt(
            learning_input,
            event_id=learning_result.get('event_id')
        )

        return {
            "original_clip_id": clip_id,
            "new_prompt_id": new_prompt_id,
            "event_id": learning_result.get('event_id'),
            "analysis": result['analysis'],
            "learning": learning_result,
            "message": f"Clip reanalyzed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reanalyze clip {clip_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reanalysis failed: {str(e)}")


@clip_router.get("/clip/{clip_id}")
async def get_clip(clip_id: int):
    """
    Get details for a specific clip by ID.

    Args:
        clip_id: Database ID of the clip

    Returns:
        Full prompt details including features
    """
    prompt = get_veo_prompt_by_id(clip_id)

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

    return prompt


# ===== Resolve Automation Endpoints =====

@router.get("/resolve/status")
async def get_resolve_status():
    """Check if DaVinci Resolve is connected via MCP"""
    try:
        await resolve_instance.connect()
        version = await resolve_instance.get_version()
        page = await resolve_instance.call_tool("get_current_page")
        return {
            "connected": True,
            "version": version,
            "current_page": page.content[0].text if page.content else "Unknown"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }


@router.post("/resolve/push")
async def push_veo_to_resolve(session_id: str):
    """
    Push a VEO session (shot list and markers) into DaVinci Resolve.
    
    1. Reads session from MetadataService
    2. Creates a bin for the session
    3. Imports assets if they exist
    4. Creates a timeline
    5. Adds markers for each shot
    """
    try:
        from metadata_service import MetadataService
        ms = MetadataService()
        session = ms.get_veo_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        await resolve_instance.connect()
        
        # 0. Dedicated Project Scaffolding
        # We try to create a project named after the session, or just work in the current one if preferred.
        session_name = session.get('session_name', session_id)
        project_name = f"VEO_{session_name}"
        
        # Try to create project (will return error if exists)
        create_res = await resolve_instance.call_tool("create_project", {"name": project_name})
        # If created or already exists, try to open it
        await resolve_instance.call_tool("open_project", {"name": project_name})
        
        # 1. Create Bin (Ensure organization within the project)
        bin_name = f"SHOT_LIST_{session_id}"
        await resolve_instance.call_tool("create_bin", {"name": bin_name})
        
        # 2. Import Assets (if any)
        assets = session.get('assets', [])
        for asset in assets:
            if os.path.exists(asset):
                await resolve_instance.call_tool("import_media", {"file_path": asset})
        
        # 3. Create Timeline
        timeline_name = f"VEO_Timeline_{session_id}"
        await resolve_instance.call_tool("create_timeline", {"name": timeline_name})
        
        # 4. Add Markers for Shots
        shot_list = session.get('shot_list', [])
        for i, shot in enumerate(shot_list):
            # Example: Add markers every 5 seconds for simulation if frames aren't known
            frame = i * 120 # Assuming 24fps * 5s
            await resolve_instance.call_tool("add_marker", {
                "frame": frame,
                "color": "Blue",
                "note": f"Shot {shot.get('shot_id')}: {shot.get('scene_context', '')[:50]}"
            })
            
        return {"success": True, "message": f"Session {session_id} pushed to Resolve"}
        
    except Exception as e:
        logger.error(f"Failed to push to Resolve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== VEO Brain Generation Endpoints =====

from veo_brain import VeoBrain

# Initialize Brain
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
    """Generate a keyframe image (Local Flux or Cloud)."""
    brain = get_veo_brain()
    
    # Generate prompt if not provided but VEO shot is
    prompt = input_data.prompt
    if not prompt and input_data.veo_shot:
        prompt = await brain.generate_keyframe_prompt(input_data.veo_shot)
        
    if not prompt:
        raise HTTPException(status_code=400, detail="Must provide prompt or veo_shot")
        
    # Generate Image
    image_base64 = await brain.generate_keyframe_image(
        prompt, 
        aspect_ratio=input_data.aspect_ratio,
        ingredients=input_data.ingredients
    )
    
    return {
        "result": image_base64, # Base64 string
        "prompt_used": prompt
    }


# ===== KIE.ai Video Generation Endpoints =====

from kie_client import get_kie_client, KieGenerateRequest, KieExtendRequest

@router.post("/video/generate")
async def generate_video_endpoint(request: KieGenerateRequest):
    """
    Trigger real video generation via KIE.ai (Veo 3.1).
    Returns a taskId to poll for status.
    """
    client = get_kie_client()
    try:
        result = client.generate_video(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Video generation unavailable (Missing API Key)")
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video/extend")
async def extend_video_endpoint(request: KieExtendRequest):
    """
    Extend an existing Veo video task.
    """
    client = get_kie_client()
    try:
        result = client.extend_video(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Video generation unavailable (Missing API Key)")
    except Exception as e:
        logger.error(f"Video extension failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video/status/{task_id}")
async def get_video_status_endpoint(task_id: str):
    """
    Check the status of a video generation task.
    """
    client = get_kie_client()
    try:
        result = client.get_task_details(task_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=503, detail="Video generation unavailable (Missing API Key)")
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export routers for inclusion in main.py
__all__ = ['router', 'clip_router']
