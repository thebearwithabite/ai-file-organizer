#!/usr/bin/env python3
"""
ARCHITECTURAL LAW:
- base_dir = monitored filesystem location (may be remote)
- metadata_root = internal state (MUST be local)
- metadata_root MUST come from get_metadata_root()
- NEVER derive metadata paths from base_dir

FastAPI Hello World Application
Basic boilerplate for a FastAPI web application
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import subprocess
import os
import re
import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Import our services
from api.services import SystemService, SearchService, TriageService
from api.rollback_service import RollbackService
from api.veo_api import router as veo_router, clip_router
from security_utils import sanitize_filename, validate_path_within_base
from gdrive_integration import get_metadata_root, get_ai_organizer_root
from universal_adaptive_learning import UniversalAdaptiveLearning
from easy_rollback_system import ensure_rollback_db
from adaptive_background_monitor import AdaptiveBackgroundMonitor
from confidence_system import ADHDFriendlyConfidenceSystem, ConfidenceLevel
from automated_deduplication_service import AutomatedDeduplicationService
from emergency_space_protection import EmergencySpaceProtection
from orchestrate_staging import orchestrate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request validation
class ClassificationRequest(BaseModel):
    file_path: str
    confirmed_category: str
    project: Optional[str] = None  # Optional hierarchical organization
    episode: Optional[str] = None  # Optional episode-level organization

class ScanFolderRequest(BaseModel):
    folder_path: str

class OpenFileRequest(BaseModel):
    path: str

class ConfidenceModeRequest(BaseModel):
    mode: str  # "NEVER", "MINIMAL", "SMART", or "ALWAYS"

# Create FastAPI application instance
app = FastAPI(
    title="AI File Organizer API",
    description="FastAPI application for AI File Organizer system",
    version="1.0.0"
)

# Add CORS middleware to allow frontend on localhost:5173 and localhost:5175 to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (default)
        "http://127.0.0.1:5173",
        "http://localhost:5175",  # Vite dev server (alternate port)
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the web interface


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

# Final Initialization Check
try:
    import re
    import subprocess
    from pathlib import Path
    logger.info("✅ Core dependencies verified.")
except ImportError as e:
    logger.error(f"❌ CRITICAL ERROR: Missing dependency during startup: {e}")
    # In a production environment, we might want to exit here
    # sys.exit(1)

print("DEBUG: Application initialization sequence complete.")

print("DEBUG: Initializing UniversalAdaptiveLearning...")
learning_system = UniversalAdaptiveLearning()
print("DEBUG: UniversalAdaptiveLearning initialized.")

print("DEBUG: Initializing ADHDFriendlyConfidenceSystem...")
confidence_system = ADHDFriendlyConfidenceSystem()
print("DEBUG: ADHDFriendlyConfidenceSystem initialized.")

print("DEBUG: Initializing AutomatedDeduplicationService...")
deduplication_service = AutomatedDeduplicationService()
print("DEBUG: AutomatedDeduplicationService initialized.")

print("DEBUG: Initializing EmergencySpaceProtection...")
space_protection = EmergencySpaceProtection()
print("DEBUG: EmergencySpaceProtection initialized.")

# Global state for background monitor
background_monitor = None
monitor_paths = []

from api.taxonomy_router import router as taxonomy_router
from api.identity_router import router as identity_router

# Include VEO API routers (Sprint 2.0)
app.include_router(veo_router)
app.include_router(clip_router)
app.include_router(taxonomy_router)
app.include_router(identity_router)
print("DEBUG: VEO, Taxonomy, & Identity API routers included.")

# Background scanning tasks
@app.on_event("startup")
async def startup_event():
    """
    Non-blocking startup - schedule initial scan after 30-second delay.
    This keeps server startup fast while still catching existing Downloads files.
    """
    global background_monitor, monitor_paths

    # Initialize rollback database first
    try:
        ensure_rollback_db()
        logger.info("✅ Rollback DB ready")
    except Exception as e:
        logger.exception("Failed to initialize rollback DB: %s", e)

    # Initialize adaptive background monitor
    try:
        paths_str = os.getenv("AUTO_MONITOR_PATHS", "")
        paths_list = []
        if paths_str.strip():
            paths_list = [
                os.path.expanduser(p.strip())
                for p in paths_str.split(",")
                if p.strip()
            ]
            
        # Add default paths if not specified or alongside env vars depending on logic
        # Here we just add defaults if env is empty, but let's ensure we contain defaults anyway
        # if the user wants strictly only AUTO_MONITOR_PATHS, they should set it validation
        
        default_paths = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents")
        ]
        
        # Combine and deduplicate smartly
        # 1. Normalize user paths
        # Current policy: Always include all paths
        all_paths = set(paths_list)
        all_paths.update(default_paths)
        
        # CRITICAL: Watch the Library Root so we learn from internal organization
        try:
            library_root = get_ai_organizer_root()
            all_paths.add(str(library_root))
            logger.info(f"📚 Added Library Root to monitor: {library_root}")
        except Exception as e:
            logger.warning(f"Could not determine Library Root for monitoring: {e}")
             
        monitor_paths = list(all_paths)

        logger.info(f"🛡️  Initializing Adaptive Monitor for: {monitor_paths}")
        
        background_monitor = AdaptiveBackgroundMonitor(
            additional_watch_paths=monitor_paths
        )
        background_monitor.start()
        SystemService.set_monitor(background_monitor)
        logger.info("✅ Adaptive Background Monitor started")

        # Schedule background tasks
        logger.info("🚀 Server started - scheduling initial Downloads scan in 30 seconds...")
        asyncio.create_task(delayed_initial_scan())
        asyncio.create_task(periodic_orchestration())

    except Exception as e:
        logger.error(f"❌ Failed to start background monitor: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Graceful shutdown handler.
    """
    global background_monitor
    logger.info("🛑 Shutting down services...")
    
    if background_monitor:
        logger.info("   Stopping background monitor...")
        background_monitor.stop()
        
    logger.info("✅ Shutdown complete")

if __name__ == "__main__":
    # Enforce single instance
    from pid_lock import enforce_single_instance
    lock = enforce_single_instance("server.lock")
    
    # Run the application directly with python main.py
    # Enable reload=True for better development    # Print database paths for debugging
    try:
        from easy_rollback_system import EasyRollbackSystem
        from universal_adaptive_learning import UniversalAdaptiveLearning
        
        rollback_db_path = EasyRollbackSystem().db_path
        learning_db_path = UniversalAdaptiveLearning().db_path
        
        logger.info(f"DEBUG: Rollback DB Path: {rollback_db_path}")
        logger.info(f"DEBUG: Learning DB Path: {learning_db_path}")
        
        if triage_service.rollback_service:
             logger.info("DEBUG: TriageService has RollbackService initialized")
        else:
             logger.error("DEBUG: TriageService MISSING RollbackService")
             
    except Exception as e:
        logger.error(f"DEBUG: Failed to print DB paths: {e}")

    try:
        # Start uvicorn server
        # Disable reload in production-like run to prevent signal handling issues
        # Use --reload flag only when developing
        use_reload = os.getenv("DEV_MODE", "False").lower() == "true"
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=use_reload)
    finally:
        lock.release()



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

async def periodic_orchestration():
    """
    Periodically run the full orchestration workflow every 15 minutes.
    Replaces simple downloads scan with full Staging -> Triage -> Auto-Organize pipeline.
    """
    # Wait for initial scan to complete first
    await asyncio.sleep(90)

    while True:
        try:
            logger.info("🎼 Starting periodic orchestration...")
            
            # Update status to running
            SystemService.update_orchestration_status({
                "last_run": datetime.now().isoformat(),
                "files_touched": 0, # Will update after run
                "status": "running"
            })
            
            loop = asyncio.get_event_loop()
            # Run orchestration with dry_run=False and default threshold
            # Capture result if orchestrate returns stats (it currently doesn't return much, but we can track time)
            await loop.run_in_executor(None, lambda: orchestrate(dry_run=False))
            
            # Update status to complete
            SystemService.update_orchestration_status({
                "last_run": datetime.now().isoformat(),
                "files_touched": 0, # TODO: Capture actual count
                "status": "idle"
            })
            
            logger.info("✅ Periodic orchestration complete")
        except Exception as e:
            logger.error(f"❌ Periodic orchestration failed: {e}")
            SystemService.update_orchestration_status({
                "last_run": datetime.now().isoformat(),
                "files_touched": 0,
                "status": "error"
            })

        # Wait 15 minutes before next run
        await asyncio.sleep(900)

# Mount React App static assets
# Vite builds to dist/assets, so we mount that to /assets
if os.path.exists("frontend_v2/dist/assets"):
    app.mount("/assets", StaticFiles(directory="frontend_v2/dist/assets"), name="assets")

@app.get("/")
async def serve_spa():
    """Serve the React App"""
    # Verify build exists
    if not os.path.exists("frontend_v2/dist/index.html"):
        return {"error": "Frontend build not found. Please run 'cd frontend_v2 && npm run build'"}
    return FileResponse("frontend_v2/dist/index.html")



@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "AI File Organizer API"}

@app.get("/api/system/status")
async def get_system_status():
    """Get current system status including file counts, monitor status, and last run time"""
    # SystemService now handles aggregation of all status data
    return system_service.get_status()

@app.post("/api/system/orchestrate")
async def trigger_orchestration():
    """Manually trigger the orchestration process in the background"""
    try:
        # Run in a background thread to avoid blocking
        thread = threading.Thread(target=orchestrate)
        thread.start()
        
        logger.info("Manual orchestration triggered via API")
        
        return {
            "status": "success",
            "message": "Orchestration triggered in the background"
        }
    except Exception as e:
        logger.error(f"Failed to trigger orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recent-activity")
async def get_recent_activity(limit: int = 50):
    """Get recent system activity"""
    try:
        activities = learning_system.get_recent_activity(limit)
        return {"activities": activities}
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/system/emergency_cleanup")
async def emergency_cleanup():
    """Emergency cleanup: Move large files from Downloads to Google Drive"""
    result = system_service.emergency_cleanup()
    return result

@app.get("/api/system/monitor-status")
async def get_monitor_status():
    """
    Get background monitor status for health checking and debugging

    Returns:
        JSON matching MonitorStatus interface for frontend
    """
    global background_monitor

    if not background_monitor:
        return {
            "status": "paused",
            "paths": [],
            "last_event": None,
            "events_processed": 0,
            "uptime_seconds": 0
        }

    try:
        # Get real status from the monitor
        status = background_monitor.status()
        
        # Get list of monitored paths
        paths = []
        if hasattr(background_monitor, 'watch_directories'):
            for info in background_monitor.watch_directories.values():
                if 'path' in info:
                    paths.append(str(info['path']))
        
        # Map to frontend interface
        return {
            "status": "active" if status.get('running') else "paused",
            "paths": paths,
            "last_event": status.get('last_scan').isoformat() if status.get('last_scan') else None,
            "events_processed": status.get('files_processed_24h', 0),
            "uptime_seconds": status.get('uptime_seconds', 0),
            "rules_count": len(getattr(background_monitor, "adaptive_rules", []))
        }
    except Exception as e:
        logger.error(f"Error getting monitor status: {e}")
        return {
            "status": "paused",
            "paths": [],
            "last_event": None,
            "events_processed": 0,
            "uptime_seconds": 0
        }

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
        
        # Add files organized today from rollback service
        try:
            today_ops = rollback_service.get_operations(today_only=True)
            stats["files_organized_today"] = len(today_ops)
        except Exception:
            stats["files_organized_today"] = 0
            
        return stats
    except Exception as e:
        logger.error(f"Failed to get learning statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve learning statistics")

@app.get("/api/settings/database-stats")
async def get_database_stats():
    """
    Get database statistics including record counts and storage information.

    Returns:
        JSON with database statistics including:
        - Total rollback operations
        - Recent operations count (last 7 days)
        - Database file sizes
        - Growth metrics
    """
    try:
        import sqlite3
        from pathlib import Path
        import os
        from datetime import datetime, timedelta

        stats = {}

        # Calculate time periods (used by multiple database queries)
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        today = datetime.now().date().isoformat()
        
        # Metadata root for all DBs
        metadata_root = get_metadata_root()

        # Rollback database statistics
        rollback_db = metadata_root / "databases" / "rollback.db"
        if rollback_db.exists():
            try:
                conn = sqlite3.connect(str(rollback_db))
                cursor = conn.cursor()

                # Total operations
                cursor.execute("SELECT COUNT(*) FROM file_operations")
                stats["total_operations"] = cursor.fetchone()[0]

                # Operations in last 7 days
                cursor.execute("SELECT COUNT(*) FROM file_operations WHERE timestamp >= ?", (seven_days_ago,))
                stats["recent_operations"] = cursor.fetchone()[0]

                # Operations today
                cursor.execute("SELECT COUNT(*) FROM file_operations WHERE DATE(timestamp) = ?", (today,))
                stats["today_operations"] = cursor.fetchone()[0]

                # Database size
                stats["rollback_db_size_mb"] = round(rollback_db.stat().st_size / (1024 * 1024), 2)

                conn.close()
            except sqlite3.OperationalError:
                # Database exists but table doesn't exist yet - treat as empty
                stats["total_operations"] = 0
                stats["recent_operations"] = 0
                stats["today_operations"] = 0
                stats["rollback_db_size_mb"] = 0
        else:
            stats["total_operations"] = 0
            stats["recent_operations"] = 0
            stats["today_operations"] = 0
            stats["rollback_db_size_mb"] = 0

        # ChromaDB statistics (vector database for semantic search)
        chroma_db = metadata_root / "chroma_db"
        if chroma_db.exists():
            total_size = sum(f.stat().st_size for f in chroma_db.rglob('*') if f.is_file())
            stats["vector_db_size_mb"] = round(total_size / (1024 * 1024), 2)
        else:
            stats["vector_db_size_mb"] = 0

        # Learning events database - MUST match path from UniversalAdaptiveLearning
        # UniversalAdaptiveLearning uses adaptive_learning.db in databases/
        learning_db = metadata_root / "databases" / "adaptive_learning.db"
        if learning_db.exists():
            try:
                conn = sqlite3.connect(str(learning_db))
                cursor = conn.cursor()

                # Total learning events
                cursor.execute("SELECT COUNT(*) FROM learning_events")
                stats["total_learning_events_db"] = cursor.fetchone()[0]

                # Learning events in last 7 days
                cursor.execute("SELECT COUNT(*) FROM learning_events WHERE timestamp >= ?", (seven_days_ago,))
                stats["recent_learning_events"] = cursor.fetchone()[0]

                # Database size
                stats["learning_db_size_mb"] = round(learning_db.stat().st_size / (1024 * 1024), 2)

                conn.close()
            except sqlite3.OperationalError:
                # Database exists but table doesn't exist yet - treat as empty
                stats["total_learning_events_db"] = 0
                stats["recent_learning_events"] = 0
                stats["learning_db_size_mb"] = 0
        else:
            stats["total_learning_events_db"] = 0
            stats["recent_learning_events"] = 0
            stats["learning_db_size_mb"] = 0

        # Total database footprint
        stats["total_db_size_mb"] = round(
            stats["rollback_db_size_mb"] +
            stats["vector_db_size_mb"] +
            stats["learning_db_size_mb"],
            2
        )

        # Activity metrics
        stats["avg_operations_per_day"] = round(stats["recent_operations"] / 7, 1) if stats["recent_operations"] > 0 else 0
        stats["avg_learning_per_day"] = round(stats["recent_learning_events"] / 7, 1) if stats["recent_learning_events"] > 0 else 0

        return stats
    except Exception as e:
        logger.error(f"Failed to get database statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve database statistics")

@app.get("/api/settings/confidence-mode")
async def get_confidence_mode():
    """
    Get current confidence mode setting

    Returns:
        JSON with current confidence mode and statistics
    """
    try:
        # Get current mode from user config
        current_mode = confidence_system.user_config.get("default_level", "SMART")

        # Get confidence statistics
        stats = confidence_system.get_confidence_stats()

        return {
            "status": "success",
            "message": f"Current confidence mode: {current_mode}",
            "data": {
                "current_mode": current_mode,
                "available_modes": ["NEVER", "MINIMAL", "SMART", "ALWAYS"],
                "mode_descriptions": {
                    "NEVER": "Never move automatically, always ask (0% confidence threshold)",
                    "MINIMAL": "Minimal questions, quick decisions (40% confidence threshold)",
                    "SMART": "Smart suggestions with confirmation (70% confidence threshold)",
                    "ALWAYS": "Move automatically when very confident (100% confidence threshold)"
                },
                "statistics": stats
            }
        }
    except Exception as e:
        logger.error(f"Failed to get confidence mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve confidence mode")

@app.post("/api/settings/confidence-mode")
async def set_confidence_mode(request: ConfidenceModeRequest):
    """
    Set confidence mode setting

    Args:
        request: ConfidenceModeRequest containing new mode (NEVER, MINIMAL, SMART, or ALWAYS)

    Returns:
        JSON with success status and new mode
    """
    try:
        # Validate mode
        valid_modes = ["NEVER", "MINIMAL", "SMART", "ALWAYS"]
        mode = request.mode.upper()

        if mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode '{request.mode}'. Must be one of: {', '.join(valid_modes)}"
            )

        # Update user config
        confidence_system.user_config["default_level"] = mode
        confidence_system.save_user_config()

        logger.info(f"Confidence mode changed to: {mode}")

        return {
            "status": "success",
            "message": f"Confidence mode set to {mode}",
            "data": {
                "new_mode": mode,
                "description": {
                    "NEVER": "Never move automatically, always ask",
                    "MINIMAL": "Minimal questions, quick decisions",
                    "SMART": "Smart suggestions with confirmation",
                    "ALWAYS": "Move automatically when very confident"
                }[mode]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set confidence mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set confidence mode")

@app.get("/api/system/deduplicate")
async def scan_for_duplicates():
    """
    Scan for duplicate files across the system

    Returns:
        JSON with duplicate scan results including:
        - status: success or error
        - message: Human-readable message
        - data: Duplicate statistics and threat information
    """
    try:
        # Get deduplication service statistics
        stats = deduplication_service.get_service_stats()

        logger.info(f"Duplicate scan requested - returning current statistics")

        return {
            "status": "success",
            "message": f"Deduplication statistics retrieved",
            "data": {
                "service_stats": stats,
                "monitoring_active": deduplication_service.monitoring_active,
                "config": {
                    "real_time_enabled": deduplication_service.config["real_time_enabled"],
                    "proactive_scanning": deduplication_service.config["proactive_scanning"],
                    "emergency_threshold": deduplication_service.config["emergency_threshold"]
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to scan for duplicates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to scan for duplicates")

@app.post("/api/system/deduplicate")
async def perform_deduplication_cleanup():
    """
    Perform safe duplicate cleanup with rollback protection

    Returns:
        JSON with cleanup results including:
        - status: success or error
        - message: Human-readable message
        - data: Duplicates removed, space freed, and rollback information
    """
    try:
        # Get current stats before cleanup
        before_stats = deduplication_service.get_service_stats()

        # Check if there are any active threats to process
        active_threats = before_stats.get("active_threats", 0)

        if active_threats == 0:
            return {
                "status": "success",
                "message": "No duplicates found to clean up",
                "data": {
                    "duplicates_removed": 0,
                    "space_freed_mb": 0,
                    "service_stats": before_stats
                }
            }

        # Process all threats in the queue
        # This will automatically handle cleanup with rollback protection
        deduplication_service._process_threats()

        # Get updated stats after cleanup
        after_stats = deduplication_service.get_service_stats()

        duplicates_removed = after_stats["service_stats"]["duplicates_removed"]
        space_freed = after_stats["service_stats"]["space_saved_mb"]

        return {
            "status": "success",
            "message": f"Cleanup completed - {duplicates_removed} duplicates removed, {space_freed:.1f} MB freed",
            "data": {
                "duplicates_removed": duplicates_removed,
                "space_freed_mb": space_freed,
                "threats_detected": after_stats["service_stats"]["threats_detected"],
                "threats_resolved": after_stats["service_stats"]["threats_resolved"],
                "rollback_available": True,
                "service_stats": after_stats
            }
        }
    except Exception as e:
        logger.error(f"Failed to perform deduplication cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to perform deduplication cleanup")

@app.get("/api/system/space-protection")
async def get_space_protection_status():
    """
    Get disk space protection status and statistics

    Returns:
        JSON with space protection status including:
        - status: success or error
        - message: Human-readable message
        - data: Disk usage statistics, emergency details, and protection settings
    """
    try:
        # Get protection statistics
        stats = space_protection.get_protection_stats()

        # Force emergency check to get current disk status
        emergency_check = space_protection.force_emergency_check()
        
        # Get current disk space info directly
        disk_space = system_service.get_disk_space()

        return {
            "status": "success",
            "message": "Space protection status retrieved",
            "data": {
                "free_gb": disk_space["free_gb"],
                "total_gb": disk_space["total_gb"],
                "used_percent": disk_space["percent_used"],
                "status": disk_space["status"],
                "protection_stats": stats,
                "current_emergency_check": emergency_check,
                "monitoring_active": space_protection.monitoring_active,
                "config": {
                    "warning_threshold": space_protection.config["warning_threshold"],
                    "critical_threshold": space_protection.config["critical_threshold"],
                    "emergency_threshold": space_protection.config["emergency_threshold"],
                    "target_free_space": space_protection.config["target_free_space"]
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get space protection status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get space protection status")

@app.post("/api/system/space-protection")
async def trigger_space_cleanup():
    """
    Trigger emergency space cleanup

    Returns:
        JSON with cleanup results including:
        - status: success or error
        - message: Human-readable message
        - data: Space freed, files processed, and cleanup details
    """
    try:
        # Force emergency check first
        emergency_check = space_protection.force_emergency_check()

        if emergency_check["emergencies_detected"] == 0:
            return {
                "status": "success",
                "message": "No cleanup needed - disk space is healthy",
                "data": {
                    "space_freed_gb": 0,
                    "files_processed": 0,
                    "emergency_check": emergency_check
                }
            }

        # Get the first emergency and handle it
        emergency = space_protection.current_emergencies[0] if space_protection.current_emergencies else None

        if not emergency:
            return {
                "status": "success",
                "message": "No active emergencies to handle",
                "data": {
                    "space_freed_gb": 0,
                    "files_processed": 0
                }
            }

        # Handle the emergency (this triggers cleanup internally)
        space_protection._handle_space_emergency(emergency)

        # Get updated stats after cleanup
        updated_stats = space_protection.get_protection_stats()

        return {
            "status": "success",
            "message": f"Cleanup completed - {updated_stats['protection_stats']['space_recovered_gb']:.1f} GB freed",
            "data": {
                "space_freed_gb": updated_stats['protection_stats']['space_recovered_gb'],
                "files_offloaded": updated_stats['protection_stats']['files_offloaded'],
                "emergency_resolved": emergency.severity,
                "protection_stats": updated_stats
            }
        }
    except Exception as e:
        logger.error(f"Failed to trigger space cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger space cleanup")

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

@app.post("/api/triage/scan_folder")
async def scan_custom_folder(request: ScanFolderRequest):
    """
    Scan a custom folder for files needing review (any folder, not just Downloads)

    This endpoint allows users to organize ANY folder through the triage center,
    with all the same features: classification, nested categories, adaptive learning, etc.

    Args:
        request: ScanFolderRequest containing folder_path

    Returns:
        JSON response with scan results including:
        - files: List of files needing review
        - count: Total files found
        - message: Status message
    """
    try:
        # Security check: Ensure path is valid and accessible
        folder_path = Path(request.folder_path)
        if not folder_path.exists():
             raise HTTPException(status_code=404, detail=f"Folder not found: {request.folder_path}")
             
        if not folder_path.is_dir():
             raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.folder_path}")

        # Trigger scan on the custom folder
        result = triage_service.scan_custom_folder(str(folder_path))
        return result
    except HTTPException:
        raise

@app.post("/api/open-file")
async def open_file(request: OpenFileRequest):
    """
    Open a file in the system default application (Finder/Explorer)
    """
    try:
        path = Path(request.path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
        # Use 'open' command on macOS
        subprocess.run(['open', str(path)], check=True)
        
        return {"status": "success", "message": f"Opened {path.name}"}
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open file: {e}")
        raise HTTPException(status_code=500, detail="Failed to open file")
    except Exception as e:
        logger.error(f"Error opening file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Security: Log detailed error internally, return generic message to user
        logger.error(f"Failed to scan custom folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while scanning the folder. Please try again later.")

@app.get("/api/triage/projects")
async def get_known_projects():
    """
    Get list of known projects for predictive text/autocomplete in Triage UI
    
    Returns:
        JSON response with list of projects
    """
    try:
        projects = triage_service.get_known_projects()
        # Convert dict to list of objects for frontend
        project_list = [{"id": k, "name": v} for k, v in projects.items()]
        return {
            "projects": project_list,
            "count": len(project_list)
        }
    except Exception as e:
        logger.error(f"Failed to retrieve known projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve known projects")

# --- File Preview Endpoints ---

def range_requests_response(
    request: Request, file_path: str, content_type: str
):
    """
    Returns a StreamingResponse that supports Range requests (critical for video/audio seeking).
    """
    path = Path(file_path)
    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    headers = {
        "content-type": content_type,
        "accept-ranges": "bytes",
        "content-encoding": "identity",
        "access-control-expose-headers": "content-type, accept-ranges, content-length, content-range, content-encoding"
    }

    start = 0
    end = file_size - 1
    status_code = 200

    if range_header is not None:
        headers["content-length"] = str(file_size)
        byte1, byte2 = 0, None
        
        m = re.search(r"(\d+)-(\d*)", range_header)
        if m:
            g = m.groups()
            byte1 = int(g[0])
            if g[1]:
                byte2 = int(g[1])

        if byte1 < file_size:
            start = byte1
            if byte2:
                end = byte2
            status_code = 206
            headers["content-range"] = f"bytes {start}-{end}/{file_size}"
            headers["content-length"] = str(end - start + 1)

    def iterfile():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk_size = min(64 * 1024, remaining)
                data = f.read(chunk_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(iterfile(), status_code=status_code, headers=headers)

@app.get("/api/files/content")
async def get_file_content(request: Request, path: str = Query(..., description="Absolute path to file")):
    """
    Stream file content with support for Range requests (video/audio).
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Security: Prevent accessing system files
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
             raise HTTPException(status_code=403, detail="Access denied to hidden/system files")

        # Determine content type
        import mimetypes
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "application/octet-stream"

        return range_requests_response(request, str(file_path), content_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving file content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to serve file content")

@app.get("/api/files/preview-text")
async def get_file_preview_text(path: str = Query(..., description="Absolute path to file")):
    """
    Get text preview for a file (supports Office docs, PDF, etc via ContentExtractor).
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Initialize ContentExtractor
        from content_extractor import ContentExtractor
        extractor = ContentExtractor()
        
        # Extract content
        content = extractor.extract_content(file_path)
        
        if not content or not content.get('text'):
            return {"text": "No text content could be extracted from this file."}
            
        return {"text": content['text']}

    except Exception as e:
        logger.error(f"Error extracting preview text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to extract preview: {str(e)}")


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
            "suggested_filename": classification.get("suggested_filename", file.filename),
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
        JSON response with list of operations in {status, message, data} format
    """
    try:
        operations = rollback_service.get_operations(days=days, today_only=today_only, search=search)

        time_range = "today" if today_only else f"last {days} days"
        message = f"Found {len(operations)} operations from {time_range}"
        if search:
            message += f" matching '{search}'"

        return {
            "status": "success",
            "message": message,
            "data": {
                "operations": operations,
                "count": len(operations),
                "days": days,
                "today_only": today_only,
                "search_term": search
            }
        }
    except Exception as e:
        logger.error(f"Failed to get rollback operations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve rollback operations")

@app.post("/api/rollback/undo/{operation_id}")
async def undo_operation(operation_id: int):
    """
    Undo a specific file operation

    Args:
        operation_id: ID of the operation to undo

    Returns:
        JSON response with success status in {status, message, data} format
    """
    try:
        result = rollback_service.undo_operation(operation_id)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        return {
            "status": "success",
            "message": result["message"],
            "data": {
                "operation_id": operation_id,
                "rollback_successful": True
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to undo operation {operation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to undo operation")

@app.post("/api/rollback/undo-today")
async def undo_today():
    """
    Emergency undo: Rollback all operations from today

    Returns:
        JSON response with count and status in {status, message, data} format
    """
    try:
        result = rollback_service.undo_today()

        if not result["success"] and result["count"] == 0:
            raise HTTPException(status_code=404, detail="No operations found to undo")

        return {
            "status": "success" if result["success"] else "partial",
            "message": result["message"],
            "data": {
                "operations_undone": result["count"],
                "rollback_successful": result["success"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to undo today's operations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to undo today's operations")

# Catch-all to support React Router (client-side routing)
# Must be defined LAST to avoid blocking API routes
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # Skip API routes - they should have been handled above, but just in case
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    # Serve index.html for any other route to let React handle it
    if os.path.exists("frontend_v2/dist/index.html"):
        return FileResponse("frontend_v2/dist/index.html")
    return {"error": "Frontend build not found"}


# End of file