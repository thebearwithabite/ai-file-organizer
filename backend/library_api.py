"""
Phase 3c · Library API Backend Routes
-------------------------------------
FastAPI service exposing REST endpoints for the VEO Prompt Library.
"""

from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import sqlite3, json, logging
from pathlib import Path
import sys

# Add parent directory to path for security_utils import
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security_utils import sanitize_filename, validate_path_within_base

DB_PATH = Path(__file__).resolve().parents[1] / "04_METADATA_SYSTEM" / "metadata.db"
app = FastAPI(title="AI File Organizer – Library API")
logger = logging.getLogger(__name__)

# ------------------------------------------------------
#  CORS CONFIG
# ------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------
#  SCHEMAS
# ------------------------------------------------------
class ClipMeta(BaseModel):
    id: int
    file_path: str
    shot_id: str
    confidence_score: float
    mood: str | None = None
    lighting_type: str | None = None

# ------------------------------------------------------
#  HELPERS
# ------------------------------------------------------
def _connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return sqlite3.connect(DB_PATH)

# ------------------------------------------------------
#  ENDPOINTS
# ------------------------------------------------------

@app.get("/api/clips", response_model=List[ClipMeta])
def list_clips():
    """Return all clips with basic metadata."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, file_path, shot_id, confidence_score, mood, lighting_type FROM veo_prompts LIMIT 200;")
        rows = cur.fetchall()
    return [ClipMeta(id=r[0], file_path=r[1], shot_id=r[2],
                     confidence_score=r[3] or 0.0,
                     mood=r[4], lighting_type=r[5]) for r in rows]

@app.get("/api/clip/{clip_id}")
def get_clip(clip_id: int):
    """Return a single clip and its full VEO JSON."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT veo_json FROM veo_prompts WHERE id=?;", (clip_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Clip not found")
    return json.loads(row[0])

@app.get("/api/manifest/{project}")
def get_manifest(project: str):
    """Return the manifest and continuity data for a project."""
    # Security: Sanitize project parameter to prevent path traversal
    safe_project = sanitize_filename(project, fallback_prefix="project")

    # Construct path with sanitized filename
    base_dir = Path("./05_VEO_PROMPTS").resolve()
    manifest_path = base_dir / f"{safe_project}_manifest.json"

    # Validate the path is within the VEO_PROMPTS directory
    if not validate_path_within_base(manifest_path, base_dir):
        logger.error(f"Path validation failed for manifest: {project}")
        raise HTTPException(status_code=400, detail="Invalid project name")

    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    return json.loads(manifest_path.read_text())

@app.post("/api/clip/{clip_id}/update")
def update_clip_json(clip_id: int, payload: Dict[str, Any]):
    """Save JSON edits to DB."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE veo_prompts SET veo_json=? WHERE id=?;",
                    (json.dumps(payload), clip_id))
        conn.commit()
    return {"status": "ok", "clip_id": clip_id}

@app.post("/api/clip/{clip_id}/reanalyze")
def reanalyze_clip(clip_id: int):
    """Trigger Gemini Vision re-analysis for a clip (placeholder)."""
    logger.info(f"Triggering reanalyze for clip {clip_id}")
    # Actual Gemini call inserted later
    return {"status": "queued", "clip_id": clip_id}

@app.get("/api/adaptive/stats")
def get_adaptive_stats():
    """Return adaptive learning summary."""
    from universal_adaptive_learning import get_current_summary
    try:
        stats = get_current_summary()
    except Exception as e:
        logger.warning(f"Adaptive summary error: {e}")
        stats = {}
    return {"adaptive_summary": stats}
