from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from pathlib import Path
import logging

from identity_service import IdentityService
from gdrive_integration import get_metadata_root

router = APIRouter(prefix="/api/identities", tags=["identities"])
logger = logging.getLogger(__name__)

# Initialize Service
identity_service = IdentityService(get_metadata_root() / "config")

class IdentityModel(BaseModel):
    id: str
    name: str
    type: str = "person"
    description: Optional[str] = None
    priority: int = 1

class IdentityUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None

@router.get("/", response_model=List[Dict[str, Any]])
async def get_identities():
    """Get all registered identities"""
    return identity_service.get_all_identities()

@router.get("/{identity_id}", response_model=Dict[str, Any])
async def get_identity(identity_id: str):
    """Get a specific identity"""
    identity = identity_service.get_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    return identity

@router.post("/", response_model=Dict[str, Any])
async def create_identity(identity: IdentityModel):
    """Register a new identity"""
    success = identity_service.register_identity(
        id=identity.id,
        name=identity.name,
        type=identity.type,
        description=identity.description,
        priority=identity.priority
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to register identity (ID might already exist)")
    return identity_service.get_identity(identity.id)

@router.put("/{identity_id}", response_model=Dict[str, Any])
async def update_identity(identity_id: str, update: IdentityUpdate):
    """Update an existing identity"""
    # Simply re-registering with the same ID updates it in this implementation
    existing = identity_service.get_identity(identity_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Identity not found")
    
    success = identity_service.register_identity(
        id=identity_id,
        name=update.name if update.name is not None else existing['name'],
        type=update.type if update.type is not None else existing['type'],
        description=update.description if update.description is not None else existing['description'],
        priority=update.priority if update.priority is not None else existing['priority']
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update identity")
    return identity_service.get_identity(identity_id)

@router.delete("/{identity_id}")
async def delete_identity(identity_id: str):
    """Delete an identity"""
    success = identity_service.delete_identity(identity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Identity not found or failed to delete")
    return {"status": "success", "message": f"Identity {identity_id} deleted"}

@router.get("/stats/summary")
async def get_identity_stats():
    """Get high-level stats about registered identities"""
    all_ids = identity_service.get_all_identities()
    type_counts = {}
    for identity in all_ids:
        t = identity.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1
        
    return {
        "total": len(all_ids),
        "by_type": type_counts
    }
