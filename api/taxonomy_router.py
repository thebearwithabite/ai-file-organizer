
from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Dict, Any, List, Optional
from pathlib import Path
from pydantic import BaseModel

from gdrive_integration import get_metadata_root, get_ai_organizer_root
from taxonomy_service import TaxonomyService

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])

# Dependency to get TaxonomyService
def get_taxonomy_service():
    config_dir = get_metadata_root() / "config"
    return TaxonomyService(config_dir)

class CategoryUpdate(BaseModel):
    display_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    extensions: Optional[List[str]] = None
    locked: Optional[bool] = None

class CategoryCreate(BaseModel):
    id: str
    display_name: str
    folder_name: str
    parent_path: Optional[str] = ""
    aliases: Optional[List[str]] = []
    keywords: Optional[List[str]] = []
    extensions: Optional[List[str]] = []
    confidence: Optional[float] = 0.5

class RenameRequest(BaseModel):
    new_name: str

@router.get("/")
def get_taxonomy(service: TaxonomyService = Depends(get_taxonomy_service)):
    """Get entire taxonomy"""
    return service.get_all_categories()

@router.post("/create")
def create_category(
    category: CategoryCreate,
    service: TaxonomyService = Depends(get_taxonomy_service)
):
    """Create a new category"""
    try:
        service.add_category(category.dict())
        return {"status": "success", "category": service.get_category(category.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{category_id}")
def get_category(category_id: str, service: TaxonomyService = Depends(get_taxonomy_service)):
    """Get single category details"""
    cat = service.get_category(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat

@router.put("/{category_id}")
def update_category(
    category_id: str, 
    update: CategoryUpdate, 
    service: TaxonomyService = Depends(get_taxonomy_service)
):
    """
    Update category metadata (aliases, keywords, etc.)
    Does NOT handle renaming/moving folders. Use /rename for that.
    """
    try:
        # Filter None values
        data = update.dict(exclude_unset=True)
        service.update_category(category_id, data)
        return {"status": "success", "category": service.get_category(category_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Category not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{category_id}/rename")
def rename_category(
    category_id: str, 
    request: RenameRequest, 
    service: TaxonomyService = Depends(get_taxonomy_service)
):
    """
    Rename a category AND its physical folder.
    """
    # Fix root path resolution to support Google Drive
    root_dir = get_ai_organizer_root()
    
    # Perform Rename
    result = service.rename_category(category_id, request.new_name, root_dir)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    elif result["status"] == "blocked":
        # Return 409 Conflict with details
        raise HTTPException(status_code=409, detail=result)
    elif result["status"] == "skipped":
        return {"status": "skipped", "message": "No change"}
        
    return result
