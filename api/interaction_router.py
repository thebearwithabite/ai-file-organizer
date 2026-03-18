from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from metadata_service import MetadataService
from pathlib import Path

router = APIRouter(prefix="/api/interactions", tags=["interactions"])
metadata_service = MetadataService()

class InteractionResponse(BaseModel):
    interaction_id: str
    file_path: str
    question: str
    options: List[str]
    context: Optional[str]
    status: str
    created_at: str

@router.get("/pending", response_model=List[InteractionResponse])
async def get_pending_interactions():
    """Get all pending user review tasks"""
    try:
        interactions = metadata_service.get_pending_interactions()
        # Parse JSON options string back to list for Pydantic
        import json
        for int_ in interactions:
            if isinstance(int_['options'], str):
                int_['options'] = json.loads(int_['options'])
        return interactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{interaction_id}/resolve")
async def resolve_interaction(interaction_id: str, decision: str):
    """Resolve a pending interaction with a user decision"""
    # Logic to execute the decision would go here
    # For now, we'll just mark it as resolved in the DB
    try:
        import sqlite3
        from datetime import datetime
        with sqlite3.connect(metadata_service.db_path) as conn:
            conn.execute(
                "UPDATE interaction_queue SET status = 'resolved', resolved_at = ? WHERE interaction_id = ?",
                (datetime.now().isoformat(), interaction_id)
            )
            conn.commit()
        return {"status": "success", "message": f"Interaction {interaction_id} resolved with decision: {decision}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
