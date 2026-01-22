"""
VEO Studio API - Phase 1 Integration
Part of VEO Prompt Machine integration into AI File Organizer

This module provides endpoints for:
- Script analysis and asset extraction
- Shot list generation
- VEO 3.1 JSON prompt creation
- Project and session management

Created by: Claude Code
Date: December 30, 2025
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import sqlite3
import logging
import re
from datetime import datetime

# Import our components
from gdrive_integration import get_metadata_root
from veo_prompt_generator import VEOPromptGenerator
from vision_analyzer import VisionAnalyzer

logger = logging.getLogger(__name__)

# Database path
DB_PATH = get_metadata_root() / "metadata.db"

# Create router
router = APIRouter(prefix="/api/veo-studio", tags=["veo-studio"])

# Global instances (lazy initialization)
_veo_generator = None
_vision_analyzer = None


def get_veo_generator() -> VEOPromptGenerator:
    """Get or create the global VEO generator instance"""
    global _veo_generator
    if _veo_generator is None:
        _veo_generator = VEOPromptGenerator()
        logger.info("VEO Prompt Generator initialized")
    return _veo_generator


def get_vision_analyzer() -> VisionAnalyzer:
    """Get or create the global vision analyzer instance"""
    global _vision_analyzer
    if _vision_analyzer is None:
        _vision_analyzer = VisionAnalyzer()
        logger.info("Vision Analyzer initialized")
    return _vision_analyzer


# ===== Pydantic Models =====

class ScriptAnalysisRequest(BaseModel):
    """Request model for script analysis"""
    script_content: str = Field(..., description="Raw script text content")
    project_name: Optional[str] = Field(None, description="Optional project name")


class Asset(BaseModel):
    """Detected asset from script"""
    type: str = Field(..., description="Asset type: character, location, prop, etc.")
    name: str = Field(..., description="Asset name")
    description: Optional[str] = Field(None, description="Asset description from script")
    occurrences: int = Field(1, description="Number of times mentioned in script")


class ScriptAnalysisResponse(BaseModel):
    """Response model for script analysis"""
    success: bool
    assets: List[Asset]
    shot_count: int
    scene_count: int
    metadata: Dict[str, Any]
    error: Optional[str] = None


class ShotListRequest(BaseModel):
    """Request model for shot list generation"""
    script_content: str = Field(..., description="Raw script text")
    project_name: Optional[str] = Field(None, description="Project name")
    existing_assets: Optional[List[Dict[str, Any]]] = Field(None, description="Pre-identified assets")


class ShotData(BaseModel):
    """Individual shot data"""
    shot_id: str
    scene_number: Optional[int] = None
    shot_number: int
    description: str
    duration_estimate: Optional[float] = None
    camera_angle: Optional[str] = None
    characters: List[str] = []
    location: Optional[str] = None
    assets_needed: List[str] = []


class ShotListResponse(BaseModel):
    """Response model for shot list generation"""
    success: bool
    shots: List[ShotData]
    total_shots: int
    total_duration_estimate: Optional[float] = None
    error: Optional[str] = None


class KeyframeRequest(BaseModel):
    """Request model for keyframe generation"""
    shot_id: str = Field(..., description="Shot ID to generate keyframe for")
    prompt: str = Field(..., description="VEO prompt for keyframe")
    use_local_flux: bool = Field(False, description="Use local Flux generator (Phase 2)")


class KeyframeResponse(BaseModel):
    """Response model for keyframe generation"""
    success: bool
    keyframe_url: Optional[str] = None
    keyframe_path: Optional[str] = None
    generation_method: str = "stub"  # "gemini", "flux", or "stub"
    error: Optional[str] = None


class VEOProject(BaseModel):
    """VEO project metadata"""
    id: int
    project_name: str
    created_at: str
    updated_at: str
    shot_count: int
    status: str = "active"  # active, archived, completed


class VEOProjectResponse(BaseModel):
    """Response model for project operations"""
    success: bool
    project: Optional[VEOProject] = None
    projects: Optional[List[VEOProject]] = None
    error: Optional[str] = None


# ===== Database Functions =====

def init_veo_studio_tables():
    """
    Initialize database tables for VEO Studio.
    
    Tables:
    - veo_projects: Project metadata
    - veo_shots: Individual shot data
    - veo_assets: Asset library
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # VEO Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS veo_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT UNIQUE NOT NULL,
                    script_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    shot_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # VEO Shots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS veo_shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    shot_id TEXT UNIQUE NOT NULL,
                    scene_number INTEGER,
                    shot_number INTEGER NOT NULL,
                    description TEXT,
                    veo_json TEXT,
                    keyframe_path TEXT,
                    duration_estimate REAL,
                    camera_angle TEXT,
                    characters TEXT,  -- JSON array
                    location TEXT,
                    assets_needed TEXT,  -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES veo_projects(id)
                )
            """)
            
            # VEO Assets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS veo_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    asset_type TEXT NOT NULL,
                    asset_name TEXT NOT NULL,
                    description TEXT,
                    reference_image_path TEXT,
                    occurrences INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, asset_name),
                    FOREIGN KEY (project_id) REFERENCES veo_projects(id)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_veo_shots_project_id
                ON veo_shots(project_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_veo_assets_project_id
                ON veo_assets(project_id)
            """)
            
            conn.commit()
            logger.info("VEO Studio tables initialized")
            
    except Exception as e:
        logger.error(f"Failed to initialize VEO Studio tables: {e}")
        raise


# ===== Script Analysis Logic =====

def extract_assets_from_script(script_content: str) -> List[Asset]:
    """
    Extract assets (characters, locations, props) from script.
    
    Uses simple regex patterns to identify:
    - Character names (capitalized dialogue headers)
    - Locations (INT./EXT. scene headers)
    - Props (mentioned in action lines)
    
    This is a basic implementation - can be enhanced with NLP/LLM in future.
    """
    assets = []
    asset_dict = {}  # Track unique assets and counts
    
    # Extract characters from dialogue headers
    # Pattern: CHARACTER NAME (on its own line, all caps)
    character_pattern = r'^([A-Z]{2,}(?:\s+[A-Z]{2,})*)$'
    for line in script_content.split('\n'):
        line = line.strip()
        match = re.match(character_pattern, line)
        if match and len(line) > 2:  # Avoid single letters
            character_name = match.group(1).strip()
            # Skip common script terms
            if character_name not in ['INT', 'EXT', 'FADE IN', 'FADE OUT', 'CUT TO', 'CONTINUED']:
                if character_name in asset_dict:
                    asset_dict[character_name]['occurrences'] += 1
                else:
                    asset_dict[character_name] = {
                        'type': 'character',
                        'name': character_name,
                        'occurrences': 1
                    }
    
    # Extract locations from scene headers
    # Pattern: INT./EXT. LOCATION - TIME
    location_pattern = r'^(INT\.|EXT\.)\s+([A-Z][A-Z\s\-/]+?)(?:\s*-\s*|\s*$)'
    for line in script_content.split('\n'):
        line = line.strip()
        match = re.match(location_pattern, line)
        if match:
            location_name = match.group(2).strip()
            if location_name in asset_dict:
                asset_dict[location_name]['occurrences'] += 1
            else:
                asset_dict[location_name] = {
                    'type': 'location',
                    'name': location_name,
                    'occurrences': 1
                }
    
    # Convert to Asset objects
    assets = [
        Asset(
            type=data['type'],
            name=data['name'],
            occurrences=data['occurrences']
        )
        for data in asset_dict.values()
    ]
    
    return assets


def count_scenes_and_shots(script_content: str) -> tuple[int, int]:
    """
    Count scenes and shots in script.
    
    Returns:
        (scene_count, estimated_shot_count)
    """
    scene_count = 0
    
    # Count scene headers (INT./EXT.)
    scene_pattern = r'^(INT\.|EXT\.)'
    for line in script_content.split('\n'):
        if re.match(scene_pattern, line.strip()):
            scene_count += 1
    
    # Estimate shots (rough heuristic: 3-5 shots per scene on average)
    # Can be refined with actual shot detection logic
    estimated_shots = scene_count * 4  # Middle estimate
    
    return scene_count, estimated_shots


# ===== API Endpoints =====

@router.on_event("startup")
async def startup():
    """Initialize database tables on startup"""
    init_veo_studio_tables()


@router.post("/analyze-script", response_model=ScriptAnalysisResponse)
async def analyze_script(request: ScriptAnalysisRequest):
    """
    Analyze script content and extract assets, scenes, shots.
    
    This endpoint:
    1. Parses script text
    2. Extracts characters, locations, props
    3. Counts scenes and estimates shots
    4. Returns structured analysis
    """
    try:
        # Extract assets
        assets = extract_assets_from_script(request.script_content)
        
        # Count scenes and shots
        scene_count, shot_count = count_scenes_and_shots(request.script_content)
        
        # Build metadata
        metadata = {
            "word_count": len(request.script_content.split()),
            "line_count": len(request.script_content.split('\n')),
            "analyzed_at": datetime.now().isoformat()
        }
        
        if request.project_name:
            metadata["project_name"] = request.project_name
        
        logger.info(
            f"Script analyzed: {len(assets)} assets, "
            f"{scene_count} scenes, ~{shot_count} shots"
        )
        
        return ScriptAnalysisResponse(
            success=True,
            assets=assets,
            shot_count=shot_count,
            scene_count=scene_count,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Script analysis failed: {e}", exc_info=True)
        return ScriptAnalysisResponse(
            success=False,
            assets=[],
            shot_count=0,
            scene_count=0,
            metadata={},
            error=str(e)
        )


@router.post("/generate-shot-list", response_model=ShotListResponse)
async def generate_shot_list(request: ShotListRequest):
    """
    Generate shot list from script content.
    
    This endpoint:
    1. Parses script into scenes
    2. Breaks scenes into shots
    3. Extracts shot metadata
    4. Returns structured shot list
    
    Note: This is a basic implementation. Can be enhanced with AI/LLM
    for smarter shot detection and camera angle suggestions.
    """
    try:
        shots = []
        shot_counter = 1
        
        # Parse script into scenes
        scene_pattern = r'^(INT\.|EXT\.)\s+(.+?)(?:\s*-\s*(.+?))?$'
        lines = request.script_content.split('\n')
        
        current_scene = None
        current_scene_number = 0
        current_location = None
        scene_description = []
        
        for line in lines:
            line = line.strip()
            
            # Check if this is a scene header
            match = re.match(scene_pattern, line)
            if match:
                # Save previous scene as a shot if exists
                if scene_description:
                    description = ' '.join(scene_description).strip()
                    if description:
                        shot_id = f"shot_{shot_counter:04d}"
                        shots.append(ShotData(
                            shot_id=shot_id,
                            scene_number=current_scene_number,
                            shot_number=shot_counter,
                            description=description[:500],  # Limit length
                            location=current_location,
                            duration_estimate=5.0  # Default 5 seconds
                        ))
                        shot_counter += 1
                    scene_description = []
                
                # Start new scene
                current_scene_number += 1
                int_ext = match.group(1)
                location = match.group(2).strip() if match.group(2) else "UNKNOWN"
                time = match.group(3).strip() if match.group(3) else ""
                current_location = f"{int_ext} {location}"
                
            elif line and not line.isupper():  # Action lines (not all caps)
                scene_description.append(line)
        
        # Don't forget the last scene
        if scene_description:
            description = ' '.join(scene_description).strip()
            if description:
                shot_id = f"shot_{shot_counter:04d}"
                shots.append(ShotData(
                    shot_id=shot_id,
                    scene_number=current_scene_number,
                    shot_number=shot_counter,
                    description=description[:500],
                    location=current_location,
                    duration_estimate=5.0
                ))
        
        # Calculate total duration
        total_duration = sum(shot.duration_estimate or 0 for shot in shots)
        
        logger.info(f"Generated {len(shots)} shots from script")
        
        return ShotListResponse(
            success=True,
            shots=shots,
            total_shots=len(shots),
            total_duration_estimate=total_duration
        )
        
    except Exception as e:
        logger.error(f"Shot list generation failed: {e}", exc_info=True)
        return ShotListResponse(
            success=False,
            shots=[],
            total_shots=0,
            error=str(e)
        )


@router.post("/generate-keyframe", response_model=KeyframeResponse)
async def generate_keyframe(request: KeyframeRequest):
    """
    Generate keyframe image for a shot.
    
    Phase 1: Returns stub response
    Phase 2: Will integrate with local Flux generator
    
    Args:
        request: Keyframe generation request with shot_id and prompt
    
    Returns:
        Keyframe generation result
    """
    try:
        # Phase 1: Stub implementation
        # In Phase 2, this will call flux_image_generator.py for local generation
        
        logger.info(
            f"Keyframe generation requested for shot {request.shot_id} "
            f"(use_local_flux={request.use_local_flux})"
        )
        
        # For now, return stub response
        return KeyframeResponse(
            success=True,
            keyframe_url=None,
            keyframe_path=None,
            generation_method="stub",
            error="Phase 2 feature - local Flux integration pending"
        )
        
    except Exception as e:
        logger.error(f"Keyframe generation failed: {e}", exc_info=True)
        return KeyframeResponse(
            success=False,
            error=str(e)
        )


@router.get("/projects", response_model=VEOProjectResponse)
async def list_projects():
    """
    Get list of all VEO projects.
    
    Returns:
        List of project metadata
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, project_name, created_at, updated_at, shot_count, status
                FROM veo_projects
                ORDER BY updated_at DESC
            """)
            
            rows = cursor.fetchall()
            
            projects = [
                VEOProject(
                    id=row[0],
                    project_name=row[1],
                    created_at=row[2],
                    updated_at=row[3],
                    shot_count=row[4],
                    status=row[5]
                )
                for row in rows
            ]
            
            return VEOProjectResponse(
                success=True,
                projects=projects
            )
            
    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        return VEOProjectResponse(
            success=False,
            error=str(e)
        )


@router.post("/projects", response_model=VEOProjectResponse)
async def create_project(project_name: str, script_content: Optional[str] = None):
    """
    Create a new VEO project.
    
    Args:
        project_name: Name for the new project
        script_content: Optional initial script content
    
    Returns:
        Created project metadata
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO veo_projects (project_name, script_content)
                VALUES (?, ?)
            """, (project_name, script_content))
            
            conn.commit()
            project_id = cursor.lastrowid
            
            # Retrieve created project
            cursor.execute("""
                SELECT id, project_name, created_at, updated_at, shot_count, status
                FROM veo_projects
                WHERE id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            project = VEOProject(
                id=row[0],
                project_name=row[1],
                created_at=row[2],
                updated_at=row[3],
                shot_count=row[4],
                status=row[5]
            )
            
            logger.info(f"Created VEO project: {project_name} (ID: {project_id})")
            
            return VEOProjectResponse(
                success=True,
                project=project
            )
            
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Project '{project_name}' already exists")
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        return VEOProjectResponse(
            success=False,
            error=str(e)
        )


# Export router for inclusion in main.py
__all__ = ['router']
