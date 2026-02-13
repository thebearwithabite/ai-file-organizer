"""
VEO Prompts API - Vision & Learning Prompt Management
Split from veo_api.py - contains prompt CRUD, clip endpoints, and Resolve integration.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

from gemini_vision_adapter import (
    GeminiVisionAdapter,
    LearningPromptInput,
    create_adapter_with_learning,
    analyze_and_learn
)
from api.resolve_service import resolve_instance

logger = logging.getLogger(__name__)

from gdrive_integration import get_metadata_root
DB_PATH = get_metadata_root() / "databases" / "metadata.db"

router = APIRouter(prefix="/api/veo", tags=["veo"])
clip_router = APIRouter(prefix="/api", tags=["clips"])

_adapter = None

def get_adapter() -> GeminiVisionAdapter:
    global _adapter
    if _adapter is None:
        _adapter = create_adapter_with_learning()
        logger.info("VEO Adapter initialized")
    return _adapter


class VEOPromptInput(BaseModel):
    file_path: str
    predicted_category: str
    confidence: float
    features: Dict[str, Any]
    media_type: str
    source: str = "api"

class VEOPromptResponse(BaseModel):
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
    force: bool = False


def init_veo_prompts_table():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS veo_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    predicted_category TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    features TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_id TEXT,
                    UNIQUE(file_path, timestamp)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_veo_prompts_file_path ON veo_prompts(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_veo_prompts_media_type ON veo_prompts(media_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_veo_prompts_timestamp ON veo_prompts(timestamp)")
            conn.commit()
            logger.info("VEO prompts table initialized")
    except Exception as e:
        logger.error(f"Failed to initialize veo_prompts table: {e}")
        raise


def insert_veo_prompt(prompt_input: LearningPromptInput, event_id: Optional[str] = None) -> int:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO veo_prompts
                (file_path, predicted_category, confidence, features, media_type, source, timestamp, event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prompt_input.file_path, prompt_input.predicted_category,
                prompt_input.confidence, json.dumps(prompt_input.features),
                prompt_input.media_type, prompt_input.source,
                prompt_input.timestamp, event_id
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
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, confidence, predicted_category, features, event_id
                FROM veo_prompts WHERE file_path = ? AND media_type = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (prompt_input.file_path, prompt_input.media_type))
            existing = cursor.fetchone()

            if existing:
                existing_id, existing_confidence, existing_category, existing_features, existing_event_id = existing
                confidence_delta = abs(prompt_input.confidence - existing_confidence)

                if confidence_delta > confidence_threshold or existing_category != prompt_input.predicted_category:
                    cursor.execute("""
                        UPDATE veo_prompts SET predicted_category=?, confidence=?, features=?,
                        source=?, timestamp=?, event_id=? WHERE id=?
                    """, (prompt_input.predicted_category, prompt_input.confidence,
                          json.dumps(prompt_input.features), prompt_input.source,
                          prompt_input.timestamp, event_id, existing_id))
                    conn.commit()
                    return {'id': existing_id, 'action': 'updated', 'confidence_delta': confidence_delta, 'previous_event_id': existing_event_id}
                else:
                    return {'id': existing_id, 'action': 'skipped', 'confidence_delta': confidence_delta, 'previous_event_id': existing_event_id}
            else:
                cursor.execute("""
                    INSERT INTO veo_prompts
                    (file_path, predicted_category, confidence, features, media_type, source, timestamp, event_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (prompt_input.file_path, prompt_input.predicted_category,
                      prompt_input.confidence, json.dumps(prompt_input.features),
                      prompt_input.media_type, prompt_input.source,
                      prompt_input.timestamp, event_id))
                conn.commit()
                return {'id': cursor.lastrowid, 'action': 'inserted', 'confidence_delta': 0.0, 'previous_event_id': None}
    except Exception as e:
        logger.error(f"Failed to store VEO prompt: {e}")
        raise HTTPException(status_code=500, detail="Database error")


def get_veo_prompts(media_type=None, limit=100, search=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM veo_prompts WHERE 1=1"
            params = []
            if media_type:
                query += " AND media_type = ?"; params.append(media_type)
            if search:
                query += " AND (file_path LIKE ? OR predicted_category LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            query += " ORDER BY timestamp DESC LIMIT ?"; params.append(limit)
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                d = dict(zip(columns, row)); d['features'] = json.loads(d['features']); results.append(d)
            return results
    except Exception as e:
        logger.error(f"Failed to retrieve VEO prompts: {e}")
        raise HTTPException(status_code=500, detail="Database error")


def get_veo_prompt_by_id(prompt_id: int):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM veo_prompts WHERE id = ?", (prompt_id,))
            row = cursor.fetchone()
            if not row: return None
            columns = [desc[0] for desc in cursor.description]
            d = dict(zip(columns, row)); d['features'] = json.loads(d['features']); return d
    except Exception as e:
        logger.error(f"Failed to retrieve VEO prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/prompts", response_model=List[VEOPromptResponse])
async def list_prompts(
    media_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    search: Optional[str] = Query(None)
):
    try:
        return get_veo_prompts(media_type=media_type, limit=limit, search=search)
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Error listing prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve prompts")


@router.post("/prompts", status_code=201)
async def create_prompt(prompt_input: VEOPromptInput):
    try:
        learning_input = LearningPromptInput(
            file_path=prompt_input.file_path, predicted_category=prompt_input.predicted_category,
            confidence=prompt_input.confidence, features=prompt_input.features,
            media_type=prompt_input.media_type, source=prompt_input.source,
            timestamp=datetime.now().isoformat()
        )
        store_result = store_prompt(learning_input)
        event_id = None
        if store_result['action'] in ['inserted', 'updated']:
            adapter = get_adapter()
            event_id = adapter.emit_learning_signal(learning_input)
            if event_id:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.cursor().execute("UPDATE veo_prompts SET event_id = ? WHERE id = ?", (event_id, store_result['id']))
                    conn.commit()
        else:
            event_id = store_result.get('previous_event_id')
        message_map = {'inserted': 'Prompt created and learning signal emitted',
                       'updated': 'Prompt updated and learning signal emitted',
                       'skipped': 'Prompt unchanged (confidence delta < 0.1)'}
        return {"id": store_result['id'], "action": store_result['action'],
                "confidence_delta": store_result['confidence_delta'], "event_id": event_id,
                "file_path": learning_input.file_path, "predicted_category": learning_input.predicted_category,
                "confidence": learning_input.confidence, "features": learning_input.features,
                "media_type": learning_input.media_type, "source": learning_input.source,
                "timestamp": learning_input.timestamp, "message": message_map[store_result['action']]}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to create prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create prompt")


@clip_router.post("/clip/{clip_id}/reanalyze")
async def reanalyze_clip(clip_id: int, request: ReanalyzeRequest = ReanalyzeRequest()):
    try:
        original_prompt = get_veo_prompt_by_id(clip_id)
        if not original_prompt:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
        file_path = original_prompt['file_path']
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        result = analyze_and_learn(file_path)
        learning_result = result['learning']
        learning_input = LearningPromptInput(**learning_result['prompt_input'])
        new_prompt_id = insert_veo_prompt(learning_input, event_id=learning_result.get('event_id'))
        return {"original_clip_id": clip_id, "new_prompt_id": new_prompt_id,
                "event_id": learning_result.get('event_id'), "analysis": result['analysis'],
                "learning": learning_result, "message": "Clip reanalyzed successfully"}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to reanalyze clip {clip_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reanalysis failed: {str(e)}")


@clip_router.get("/clip/{clip_id}")
async def get_clip(clip_id: int):
    prompt = get_veo_prompt_by_id(clip_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
    return prompt


@router.get("/resolve/status")
async def get_resolve_status():
    try:
        await resolve_instance.connect()
        version = await resolve_instance.get_version()
        page = await resolve_instance.call_tool("get_current_page")
        return {"connected": True, "version": version, "current_page": page.content[0].text if page.content else "Unknown"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.post("/resolve/push")
async def push_veo_to_resolve(session_id: str):
    try:
        import os
        from metadata_service import MetadataService
        ms = MetadataService()
        session = ms.get_veo_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        await resolve_instance.connect()
        session_name = session.get('session_name', session_id)
        project_name = f"VEO_{session_name}"
        await resolve_instance.call_tool("create_project", {"name": project_name})
        await resolve_instance.call_tool("open_project", {"name": project_name})
        bin_name = f"SHOT_LIST_{session_id}"
        await resolve_instance.call_tool("create_bin", {"name": bin_name})
        assets = session.get('assets', [])
        for asset in assets:
            if os.path.exists(asset):
                await resolve_instance.call_tool("import_media", {"file_path": asset})
        timeline_name = f"VEO_Timeline_{session_id}"
        await resolve_instance.call_tool("create_timeline", {"name": timeline_name})
        shot_list = session.get('shot_list', [])
        for i, shot in enumerate(shot_list):
            frame = i * 120
            await resolve_instance.call_tool("add_marker", {
                "frame": frame, "color": "Blue",
                "note": f"Shot {shot.get('shot_id')}: {shot.get('scene_context', '')[:50]}"
            })
        return {"success": True, "message": f"Session {session_id} pushed to Resolve"}
    except Exception as e:
        logger.error(f"Failed to push to Resolve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ['router', 'clip_router', 'init_veo_prompts_table']
