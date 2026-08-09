"""
V2 API routes — Phase 3 Library UI backend.

Every endpoint here routes through the designated services ONLY.
No direct filesystem, storage SDK, or shutil calls.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.context import ContextStore, CorrectionEvent
from backend.query import QueryService
from backend.file_operations import get_file_operations

router = APIRouter(prefix="/api/v2", tags=["v2"])

# Singleton services (lazy)
_query_service = None
_context_store = None


def _get_query() -> QueryService:
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service


def _get_context() -> ContextStore:
    global _context_store
    if _context_store is None:
        _context_store = ContextStore()
    return _context_store


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CorrectionRequest(BaseModel):
    file_path: str
    predicted_category: str
    corrected_category: str
    confidence: float = 0.0
    source: str = "ui"


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

@router.get("/query")
async def query_files(
    q: str = Query(default="", description="Natural language or keyword query"),
    category: str = Query(default=""),
    file_type: str = Query(default=""),
    tier: str = Query(default=""),
    limit: int = Query(default=50, le=200),
):
    """NL-powered file search over metadata DB (read-only)."""
    qs = _get_query()
    result = qs.search_files(
        query_text=q,
        category=category,
        file_type=file_type,
        tier=tier,
        limit=limit,
    )
    return {
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "query_time_ms": result.query_time_ms,
        "explanation": result.explanation,
    }


# ---------------------------------------------------------------------------
# Corrections (the learning loop)
# ---------------------------------------------------------------------------

@router.post("/corrections")
async def record_correction(req: CorrectionRequest):
    """Record a user correction → writes to corrections + learnings tables."""
    ctx = _get_context()
    event = CorrectionEvent(
        file_path=req.file_path,
        predicted_category=req.predicted_category,
        corrected_category=req.corrected_category,
        confidence=req.confidence,
        source=req.source,
    )
    cid = ctx.record_correction(event)
    return {"correction_id": cid, "status": "recorded"}


@router.get("/learnings")
async def get_learnings(limit: int = Query(default=10, le=50)):
    """Get recent learning patterns from corrections."""
    ctx = _get_context()
    corrections = ctx.get_recent_corrections(limit=limit)
    return {"learnings": corrections, "count": len(corrections)}


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

@router.get("/activity")
async def get_activity(limit: int = Query(default=20, le=100)):
    """Recent activity: corrections + learnings with citations."""
    ctx = _get_context()
    corrections = ctx.get_recent_corrections(limit=limit)
    return {"activity": corrections, "count": len(corrections)}


# ---------------------------------------------------------------------------
# Tiering status
# ---------------------------------------------------------------------------

@router.get("/tiering/status")
async def get_tiering_status():
    """Get local vs cloud tiering status."""
    ops = get_file_operations()
    disk = ops.disk_usage()

    # Count local files
    local_files = ops.list_organized_files()
    local_count = len(local_files)
    local_bytes = sum(f["size_bytes"] for f in local_files)

    return {
        "local": {
            "file_count": local_count,
            "total_bytes": local_bytes,
            "total_gb": round(local_bytes / (1024 ** 3), 1),
        },
        "cloud": {
            "file_count": 0,  # populated when GCSProvider wired in
            "total_bytes": 0,
            "total_gb": 0,
        },
        "disk": disk,
    }


# ---------------------------------------------------------------------------
# Stream URL (cold-tier preview)
# ---------------------------------------------------------------------------

@router.get("/stream")
async def get_stream_url(key: str = Query(...)):
    """Get a signed URL for streaming a cold-tier file."""
    # For now, return a local file:// URL if the file exists locally
    ops = get_file_operations()
    path = ops.root / key
    if path.exists():
        return {"url": f"file://{path}", "tier": "local"}
    # TODO: wire GCSProvider for cold-tier signed URLs
    raise HTTPException(status_code=404, detail=f"File not found: {key}")


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

@router.get("/review-queue")
async def get_review_queue():
    """Files awaiting human decision (staging area)."""
    ops = get_file_operations()
    files = ops.list_staging_files()
    return {"files": files, "count": len(files)}
