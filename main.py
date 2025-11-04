#!/usr/bin/env python3
"""
FastAPI Hello World Application
Basic boilerplate for a FastAPI web application
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import subprocess
import os
import asyncio
import logging
from pathlib import Path
from typing import Optional

# Import our services
from api.services import SystemService, SearchService, TriageService
from api.rollback_service import RollbackService
from api.veo_api import router as veo_router, clip_router
from security_utils import sanitize_filename, validate_path_within_base
from universal_adaptive_learning import UniversalAdaptiveLearning

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request validation
class ClassificationRequest(BaseModel):
    file_path: str
    confirmed_category: str
    project: Optional[str] = None  # Optional hierarchical organization
    episode: Optional[str] = None  # Optional episode-level organization

class OpenFileRequest(BaseModel):
    path: str

# Create FastAPI application instance
app = FastAPI(
    title="AI File Organizer API",
    description="FastAPI application for AI File Organizer system",
    version="1.0.0"
)

# Add CORS middleware to allow frontend on localhost:5173 to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the web interface
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Initialize services
print("DEBUG: Initializing SystemService...")
system_service = SystemService()
print("DEBUG: SystemService initialized.")

print("DEBUG: Initializing SearchService...")
search_service = SearchService()
print("DEBUG: SearchService initialized.")

print("DEBUG: Initializing RollbackService...")
rollback_service = RollbackService()
print("DEBUG: RollbackService initialized.")

print("DEBUG: Initializing TriageService...")
triage_service = TriageService(rollback_service=rollback_service)
print("DEBUG: TriageService initialized.")

print("DEBUG: Initializing UniversalAdaptiveLearning...")
learning_system = UniversalAdaptiveLearning()
print("DEBUG: UniversalAdaptiveLearning initialized.")

# Include VEO API routers (Sprint 2.0)
app.include_router(veo_router)
app.include_router(clip_router)
print("DEBUG: VEO API routers included.")

# Background scanning tasks
@app.on_event("startup")
async def startup_event():
    """
    Non-blocking startup - schedule initial scan after 30-second delay.
    This keeps server startup fast while still catching existing Downloads files.
    """
    logger.info("🚀 Server started - scheduling initial Downloads scan in 30 seconds...")
    asyncio.create_task(delayed_initial_scan())
    asyncio.create_task(periodic_downloads_scan())

async def delayed_initial_scan():
    """
    Run initial Downloads scan after 30-second delay.
    Gives server time to fully initialize before expensive operations.
    """
    await asyncio.sleep(30)
    logger.info("📂 Running initial Downloads scan...")
    try:
        # Run in thread pool to avoid blocking async loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, triage_service.trigger_scan)
        logger.info(f"✅ Initial scan complete: {result.get('files_found', 0)} files found for triage")
    except Exception as e:
        logger.error(f"❌ Initial scan failed: {e}")

async def periodic_downloads_scan():
    """
    Periodically scan Downloads folder every 10 minutes.
    ADHD-friendly: Files organize automatically without manual intervention.

    With rate limiting (15 RPM, 1,500/day):
    - 10 min intervals = 6 scans/hour = 144 scans/day
    - Max 20 files/scan = max 2,880 files/day
    - Actual API calls limited by rate limiter to stay under 1,500/day
    """
    # Wait for initial scan to complete first
    await asyncio.sleep(90)  # Initial scan at 30s + 60s buffer

    while True:
        try:
            logger.info("🔄 Running periodic Downloads scan (every 10 minutes)...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, triage_service.trigger_scan)
            logger.info(f"✅ Periodic scan complete: {result.get('files_found', 0)} files found")
        except Exception as e:
            logger.error(f"❌ Periodic scan failed: {e}")

        # Wait 10 minutes before next scan
        await asyncio.sleep(600)  # 600 seconds = 10 minutes

@app.get("/")
async def serve_web_interface():
    """Serve the main web interface"""
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "AI File Organizer API"}

@app.get("/api/system/status")
async def get_system_status():
    """Get current system status including file counts and last run time"""
    return system_service.get_status()

@app.post("/api/system/emergency_cleanup")
async def emergency_cleanup():
    """Emergency cleanup: Move large files from Downloads to Google Drive"""
    result = system_service.emergency_cleanup()
    return result

@app.get("/api/settings/learning-stats")
async def get_learning_stats():
    """
    Get learning system statistics for display in Settings UI.

    Returns detailed statistics about:
    - Total learning events
    - Breakdown by media type (image/video/audio/document)
    - Unique categories learned
    - Most common category
    - Average confidence of top events

    Returns:
        JSON with learning statistics
    """
    try:
        stats = learning_system.get_learning_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get learning statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve learning statistics")

@app.get("/api/search")
async def search_files(q: str = Query(..., description="Search query", min_length=1)):
    """
    Search for files using the AI File Organizer's search capabilities
    
    Args:
        q: Search query string (required, cannot be empty)
        
    Returns:
        JSON response with search results
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty")

    try:
        results = search_service.search(q.strip())
        return {
            "query": q.strip(),
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        # Security: Log detailed error internally, return generic message to user
        logger.error(f"Search operation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while performing the search. Please try again later.")

@app.get("/api/triage/files_to_review")
async def get_files_to_review():
    """
    Get list of files that require manual review due to low confidence categorization

    WARNING: This endpoint performs EXPENSIVE AI operations (vision analysis, audio analysis, etc.)
    and should only be called when the user explicitly requests a triage scan.

    Returns:
        JSON response with files needing review
    """
    try:
        files = triage_service.get_files_for_review()
        return {
            "files": files,
            "count": len(files),
            "message": f"Found {len(files)} files requiring review"
        }
    except Exception as e:
        # Security: Log detailed error internally, return generic message to user
        logger.error(f"Failed to retrieve files for review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while retrieving files for review. Please try again later.")

@app.post("/api/triage/trigger_scan")
async def trigger_triage_scan():
    """
    Manually trigger a triage scan for files needing review

    This endpoint explicitly triggers the expensive scanning operation.
    Use this when the user navigates to the triage page or clicks "Scan for files".

    Returns:
        JSON response with scan results
    """
    try:
        result = triage_service.trigger_scan()
        return result
    except Exception as e:
        # Security: Log detailed error internally, return generic message to user
        logger.error(f"Failed to trigger triage scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while triggering the scan. Please try again later.")

@app.post("/api/triage/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and classify a file

    Args:
        file: Uploaded file

    Returns:
        JSON response with classification results
    """
    try:
        # Save file temporarily with sanitized filename (security: prevent path traversal)
        temp_dir = Path.home() / "Downloads"
        safe_filename = sanitize_filename(file.filename, fallback_prefix="upload")
        file_path = temp_dir / safe_filename

        # Validate the final path is within Downloads directory
        if not validate_path_within_base(file_path, temp_dir):
            logger.error(f"Path validation failed for upload: {file.filename}")
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Write uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        logger.info(f"File uploaded (sanitized): {file_path}")

        # Classify the file using triage service
        classification = triage_service.get_classification(str(file_path))

        # Return classification result
        return {
            "file_id": str(hash(file.filename)),
            "file_name": file.filename,
            "file_path": str(file_path),  # Add file_path for classification API
            "classification": {
                "category": classification.get("suggested_category", "Unknown"),
                "confidence": classification.get("confidence", 0.5),
                "reasoning": classification.get("reasoning", "File analyzed"),
                "needs_review": classification.get("confidence", 0.5) < 0.85
            },
            "status": "pending_review" if classification.get("confidence", 0.5) < 0.85 else "organized",
            "destination_path": str(file_path),
            "operation_id": 0
        }

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/triage/classify")
async def classify_file(request: ClassificationRequest):
    """
    Classify a file with user-confirmed category and optional hierarchical organization

    Args:
        request: Classification request containing:
            - file_path: Path to the file
            - confirmed_category: User-confirmed category
            - project: Optional project name for hierarchical organization
            - episode: Optional episode name for hierarchical organization

    Returns:
        JSON response with classification status and hierarchical metadata
    """
    try:
        result = triage_service.classify_file(
            file_path=request.file_path,
            confirmed_category=request.confirmed_category,
            project=request.project,
            episode=request.episode
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

@app.post("/api/open-file")
async def open_file(request: OpenFileRequest):
    """
    Open a file using the operating system's default application
    
    Args:
        request: OpenFileRequest containing the file path to open
        
    Returns:
        JSON response with operation status
    """
    try:
        file_path = request.path.strip()
        
        # Validate that the file path is provided
        if not file_path:
            raise HTTPException(status_code=400, detail="File path cannot be empty")
        
        # Convert to Path object for better handling
        path_obj = Path(file_path)
        
        # Check if file exists (for local files)
        if not path_obj.exists():
            # For non-existent files, still try to open (might be a URL or special path)
            # but provide a warning in the response
            pass
        
        # Use macOS 'open' command to open the file with default application
        # The 'open' command works with files, URLs, and applications
        result = subprocess.run(
            ['open', file_path],
            capture_output=True,
            text=True,
            timeout=10  # Prevent hanging
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Successfully opened file: {os.path.basename(file_path)}",
                "path": file_path
            }
        else:
            # Get error details from stderr
            error_message = result.stderr.strip() if result.stderr else "Unknown error"
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to open file: {error_message}"
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, 
            detail="File opening timed out - the file might be too large or the application unresponsive"
        )
    except subprocess.SubprocessError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"System error opening file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Unexpected error opening file: {str(e)}"
        )

# Rollback API endpoints
@app.get("/api/rollback/operations")
async def get_rollback_operations(
    days: int = Query(7, description="Number of days to look back"),
    today_only: bool = Query(False, description="Show only today's operations"),
    search: Optional[str] = Query(None, description="Search term to filter operations")
):
    """
    Get file operations that can be rolled back

    Args:
        days: Number of days to look back (default: 7)
        today_only: Only show today's operations (default: False)
        search: Optional search term

    Returns:
        JSON response with list of operations
    """
    operations = rollback_service.get_operations(days=days, today_only=today_only, search=search)
    return {
        "operations": operations,
        "count": len(operations)
    }

@app.post("/api/rollback/undo/{operation_id}")
async def undo_operation(operation_id: int):
    """
    Undo a specific file operation

    Args:
        operation_id: ID of the operation to undo

    Returns:
        JSON response with success status
    """
    result = rollback_service.undo_operation(operation_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/rollback/undo-today")
async def undo_today():
    """
    Emergency undo: Rollback all operations from today

    Returns:
        JSON response with count and status
    """
    result = rollback_service.undo_today()
    if not result["success"] and result["count"] == 0:
        raise HTTPException(status_code=404, detail="No operations found to undo")
    return result

if __name__ == "__main__":
    # Run the application directly with python main.py
    uvicorn.run("main:app", host="0.0.0.0", port=8000)