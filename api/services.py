#!/usr/bin/env python3
"""
System Services for AI File Organizer API
Provides system status and monitoring functionality
"""

import logging
import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import datetime as dt_module

from gdrive_librarian import GoogleDriveLibrarian
from unified_classifier import UnifiedClassificationService
from gdrive_integration import get_ai_organizer_root, get_metadata_root
from hierarchical_organizer import HierarchicalOrganizer
from security_utils import validate_path_within_base
from universal_adaptive_learning import UniversalAdaptiveLearning

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemService:
    """Service class for system-related operations"""

    # Class-level shared instance to avoid re-initialization
    _librarian_instance: Optional[GoogleDriveLibrarian] = None
    _initialization_error: Optional[str] = None
    _initialized: bool = False
    
    # Injected dependencies
    _background_monitor = None
    _last_orchestration_stats = {"last_run": None, "files_processed": 0}

    def __init__(self):
        """Initialize SystemService with lazy GoogleDriveLibrarian loading"""
        if SystemService._librarian_instance is None:
            try:
                logger.info("Creating GoogleDriveLibrarian (lazy initialization mode)...")
                # Use centralized metadata root for config
                from gdrive_integration import get_metadata_root
                config_path = get_metadata_root() / "config"
                
                SystemService._librarian_instance = GoogleDriveLibrarian(
                    config_dir=config_path,
                    cache_size_gb=2.0,
                    auto_sync=False  # Disable auto-sync for API stability
                )
                # DO NOT call initialize() here - defer until first actual use
                # This avoids blocking server startup with Google Drive API calls
                logger.info("GoogleDriveLibrarian created (not yet initialized - will initialize on first use)")
            except Exception as e:
                SystemService._initialization_error = str(e)
                logger.error(f"Failed to create GoogleDriveLibrarian: {e}")
                SystemService._librarian_instance = None

    @classmethod
    def set_monitor(cls, monitor):
        """Inject the background monitor instance"""
        cls._background_monitor = monitor

    @classmethod
    def update_orchestration_status(cls, stats: Dict[str, Any]):
        """Update the last orchestration run stats"""
        cls._last_orchestration_stats = stats

    @classmethod
    def get_librarian(cls) -> Optional[GoogleDriveLibrarian]:
        """Get the singleton GoogleDriveLibrarian instance, initializing if necessary"""
        if cls._librarian_instance is None:
            try:
                logger.info("Creating GoogleDriveLibrarian (lazy initialization mode)...")
                # Use centralized metadata root for config
                from gdrive_integration import get_metadata_root
                config_path = get_metadata_root() / "config"
                
                cls._librarian_instance = GoogleDriveLibrarian(
                    config_dir=config_path,
                    cache_size_gb=2.0,
                    auto_sync=False
                )
            except Exception as e:
                logger.error(f"Failed to create GoogleDriveLibrarian: {e}")
                return None

        if not cls._initialized and cls._librarian_instance:
            try:
                logger.info("Performing lazy initialization of GoogleDriveLibrarian...")
                cls._librarian_instance.initialize()
                cls._initialized = True
                logger.info("GoogleDriveLibrarian initialized successfully")
            except Exception as e:
                logger.error(f"Lazy initialization failed: {e}")
                
        return cls._librarian_instance

    def _ensure_initialized(self):
        """Ensure the librarian is initialized before use"""
        if not SystemService._initialized and SystemService._librarian_instance:
            try:
                logger.info("Performing lazy initialization of GoogleDriveLibrarian...")
                SystemService._librarian_instance.initialize()
                SystemService._initialized = True
                logger.info("GoogleDriveLibrarian initialized successfully")
            except Exception as e:
                logger.error(f"Lazy initialization failed: {e}")
                SystemService._initialization_error = str(e)

    def get_status(self) -> Dict[str, Any]:
        """
        Get unified system status (Backend + Monitor + Orchestration)
        
        Returns:
            Dict matching the unified status shape
        """
        # Ensure core services
        self._ensure_initialized()

        backend_status = "ok"
        monitor_info = None
        orchestration_info = self._last_orchestration_stats

        # Pull monitor stats
        if self._background_monitor:
            try:
                monitor_stats = self._background_monitor.status()
                # Handle both dict access and direct attribute access depending on implementation
                active_rules = len(getattr(self._background_monitor, "adaptive_rules", []))
                
                monitor_info = {
                    "watching_paths": len(monitor_stats.get("watch_directories", {})),
                    "status": "active" if monitor_stats.get("running") else "paused",
                    "rules_loaded": active_rules,
                    "stats": {
                        "processed_files": monitor_stats.get("processed_files", 0),
                        "errors_24h": monitor_stats.get("errors_24h", 0),
                        "last_scan": monitor_stats.get("last_scan")
                    }
                }
            except Exception as e:
                logger.error(f"Error getting monitor stats: {e}")
                backend_status = "degraded"
                monitor_info = None
        else:
            monitor_info = {
                "watching_paths": 0,
                "status": "offline",
                "rules_loaded": 0,
                "stats": {"processed_files": 0, "errors_24h": 0, "last_scan": None}
            }

        # Get Google Drive status
        gdrive_status = {
            "connected": False,
            "user_name": None,
            "quota_used_gb": 0,
            "quota_total_gb": 0
        }

        librarian = self.get_librarian()
        if librarian:
            try:
                # Get detailed status from librarian
                lib_status = librarian.get_system_status()
                
                if lib_status.get("authenticated", False):
                    auth_info = lib_status.get("auth_info", {})
                    gdrive_status = {
                        "connected": True,
                        "user_name": auth_info.get("user_name", "Unknown"),
                        "quota_used_gb": auth_info.get("storage_used_gb", 0),
                        "quota_total_gb": auth_info.get("storage_quota_gb", 0),
                        "drive_root": lib_status.get("drive_root")
                    }
            except Exception as e:
                logger.error(f"Error getting Google Drive status: {e}")

        # DEBUG LOGGING for Status Issue
        logger.info(f"SystemStatus Debug - Sending Google Drive Status: {gdrive_status}")

        # Orchestration Status (Read from shared JSON)
        orchestration_info = {
            "last_run": None,
            "files_processed": 0,
            "files_moved": 0,
            "status": "idle"
        }
        
        try:
            stats_path = get_metadata_root() / "orchestration_stats.json"
            if stats_path.exists():
                with open(stats_path, 'r') as f:
                    stats = json.load(f)
                    orchestration_info = {
                        "last_run": stats.get("last_run"),
                        "files_processed": stats.get("files_processed", 0),
                        "status": stats.get("status", "idle")
                    }
        except Exception as e:
            logger.error(f"Error reading orchestration stats: {e}")
            # Fallback to in-memory if file read fails (though likely stale)
            orchestration_info["status"] = "error"

        return {
            "backend_status": backend_status,
            "monitor": monitor_info,
            "orchestration": orchestration_info,
            "disk_space": self.get_disk_space(),
            "google_drive": gdrive_status
        }

    def get_disk_space(self) -> Dict[str, Any]:
        """
        Get current disk space information
        
        Returns:
            Dict with free_gb, total_gb, percent_used, and status
        """
        try:
            # Use shutil.disk_usage for reliable cross-platform stats
            total, used, free = shutil.disk_usage("/")
            
            total_gb = round(total / (1024**3), 1)
            free_gb = round(free / (1024**3), 1)
            percent_used = round((used / total) * 100, 1)
            
            # Determine status based on free space
            if percent_used > 95:
                status = "critical"
            elif percent_used > 85:
                status = "warning"
            else:
                status = "safe"
                
            return {
                "free_gb": free_gb,
                "total_gb": total_gb,
                "percent_used": int(percent_used),
                "status": status
            }
        except Exception as e:
            logger.error(f"Error getting disk space: {e}")
            return {
                "free_gb": 0,
                "total_gb": 0,
                "percent_used": 0,
                "status": "unknown"
            }

    def emergency_cleanup(self) -> Dict[str, Any]:
        """
        Emergency cleanup: Move large files from Downloads to Google Drive

        Returns:
            Dict with moved_count, freed_mb, and status
        """
        try:
            gdrive_staging = Path.home() / "Google Drive" / "My Drive" / "99_STAGING_EMERGENCY"
            downloads = Path.home() / "Downloads"

            # Find large files (>50MB)
            large_files = []
            for file_path in downloads.glob('*'):
                if file_path.is_file():
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if size_mb >= 50:
                        large_files.append((file_path, size_mb))

            large_files.sort(key=lambda x: x[1], reverse=True)

            moved_count = 0
            freed_mb = 0

            gdrive_staging.mkdir(parents=True, exist_ok=True)

            for file_path, size_mb in large_files[:10]:  # Move up to 10 largest
                try:
                    dest_path = gdrive_staging / file_path.name
                    shutil.move(str(file_path), str(dest_path))
                    moved_count += 1
                    freed_mb += size_mb
                    logger.info(f"Moved {file_path.name} to Google Drive staging")
                except Exception as e:
                    logger.error(f"Failed to move {file_path.name}: {e}")

            return {
                'moved_count': moved_count,
                'freed_mb': int(freed_mb),
                'status': 'success' if moved_count > 0 else 'no_action_needed'
            }
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
            return {
                'moved_count': 0,
                'freed_mb': 0,
                'status': 'error',
                'error': str(e)
            }

    def get_maintenance_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent maintenance task logs from adaptive_rules.db"""
        import sqlite3
        from gdrive_integration import get_metadata_root
        
        db_path = get_metadata_root() / "adaptive_rules.db"
        logs = []
        
        if not db_path.exists():
            return []
            
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT task_name, last_run, success, details FROM maintenance_history ORDER BY last_run DESC LIMIT ?",
                    (limit,)
                )
                for row in cursor:
                    logs.append(dict(row))
        except Exception as e:
            logger.error(f"Error fetching maintenance logs: {e}")
            
        return logs

    def get_emergency_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent emergency events from adaptive_rules.db"""
        import sqlite3
        from gdrive_integration import get_metadata_root
        
        db_path = get_metadata_root() / "adaptive_rules.db"
        logs = []
        
        if not db_path.exists():
            return []
            
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT timestamp, emergency_type, severity_level, details, action_taken FROM emergency_events ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                for row in cursor:
                    logs.append(dict(row))
        except Exception as e:
            logger.error(f"Error fetching emergency logs: {e}")
            
        return logs

    @classmethod
    def cleanup(cls):
        """Cleanup shared resources when shutting down"""
        if cls._librarian_instance:
            try:
                # Any cleanup needed for GoogleDriveLibrarian
                logger.info("Cleaning up GoogleDriveLibrarian instance")
                cls._librarian_instance = None
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


class SearchService:
    """Service class for search-related operations - uses GoogleDriveLibrarian via SystemService"""

    def __init__(self):
        """Initialize SearchService"""
        # No local initialization needed - uses SystemService singleton
        pass

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform search using the unified GoogleDriveLibrarian
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of search results as dictionaries
        """
        librarian = SystemService.get_librarian()
        if not librarian:
            logger.error("Cannot perform search: System librarian not available")
            return []

        try:
            # Perform search using hybrid librarian (auto mode)
            # Access the hybrid_librarian property which lazy-loads the semantic engine
            results = librarian.hybrid_librarian.search(query, search_mode="auto", limit=limit)

            # Convert EnhancedQueryResult to API-friendly format
            api_results = []
            for result in results:
                api_result = {
                    "filename": result.filename,
                    "file_path": str(result.file_path),
                    "relevance_score": round(result.relevance_score, 2),
                    "semantic_score": round(result.semantic_score, 4),
                    "matching_content": result.matching_content,
                    "file_category": result.file_category,
                    "tags": result.tags,
                    "file_size": result.file_size,
                    "last_modified": result.last_modified.isoformat() if result.last_modified else None,
                    "reasoning": result.reasoning,
                    "content_summary": result.content_summary,
                    "key_concepts": result.key_concepts or []
                }
                api_results.append(api_result)

            logger.info(f"Search for '{query}' returned {len(api_results)} results")
            return api_results

        except Exception as e:
            logger.error(f"Error performing search for '{query}': {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_indexed_count(self) -> int:
        """Get the number of documents in the database"""
        librarian = SystemService.get_librarian()
        if not librarian:
            return 0

        try:
            stats = librarian.get_system_status()
            return stats.get('components', {}).get('metadata_store', {}).get('total_files', 0)
        except Exception as e:
            logger.error(f"Error getting indexed count: {e}")
            return 0


class TriageService:
    """Service class for file triage and review operations"""

    def __init__(self, rollback_service=None):
        """Initialize TriageService with classification engine and rollback service"""
        try:
            # Initialize with AI Organizer root directory
            self.base_dir = get_ai_organizer_root()

            # Initialize the unified classification service with AI-powered content analysis
            self.classifier = UnifiedClassificationService()

            # Initialize hierarchical organizer for deep folder structures
            self.hierarchical_organizer = HierarchicalOrganizer()

            # Store rollback service for operation tracking
            self.rollback_service = rollback_service

            # Initialize learning system for adaptive learning from user classifications
            self.learning_system = UniversalAdaptiveLearning()

            # Common staging areas where unorganized files are found
            self.staging_areas = [
                Path.home() / "Downloads",
                Path.home() / "Desktop",
                self.base_dir / "99_TEMP_PROCESSING" / "Downloads_Staging",
                self.base_dir / "99_TEMP_PROCESSING" / "Desktop_Staging",
                self.base_dir / "99_TEMP_PROCESSING" / "Manual_Review",
                self.base_dir / "99_STAGING_EMERGENCY",  # Emergency staging for bulk file dumps
                self.base_dir / "00_INBOX_STAGING",  # New Primary Input Queue
                # Add iCloud Staging
                Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Documents/GDRIVE_STAGING"
            ]

            # Security: Validate all staging areas are within allowed base directories
            # This prevents path traversal if staging areas ever become user-configurable
            validated_staging_areas = []
            user_home = Path.home()

            for area in self.staging_areas:
                # Validate each staging area is within either user home or base_dir
                is_in_home = validate_path_within_base(area, user_home)
                is_in_base = validate_path_within_base(area, self.base_dir) if self.base_dir else False

                if is_in_home or is_in_base:
                    validated_staging_areas.append(area)
                else:
                    logger.warning(f"Skipping invalid staging area (outside safe directories): {area}")

            self.staging_areas = validated_staging_areas
            logger.info(f"TriageService initialized with {len(self.staging_areas)} validated staging areas")

        except Exception as e:
            logger.error(f"Failed to initialize TriageService: {e}")
            # Fallback to basic initialization
            self.classifier = None
            self.staging_areas = []
            self.base_dir = None
            self.rollback_service = rollback_service

    def get_files_for_review(self) -> List[Dict[str, Any]]:
        """
        Get files requiring triage/review.
        Prioritizes the Adaptive Review Queue, then falls back to live scanning of Staging Areas.
        """
        if self.classifier is None:
            logger.error("Classification engine not available - returning empty list")
            return []

        try:
            logger.info("Getting files for review...")
            files_for_review = []
            
            # 1. READ QUEUE (V3 Priority)
            # ------------------------------------------------------------------
            try:
                queue_path = get_metadata_root() / "review_queue.jsonl"
                if queue_path.exists():
                    logger.debug(f"Reading from Review Queue: {queue_path}")
                    with open(queue_path, 'r') as f:
                        for line in f:
                            if not line.strip(): continue
                            try:
                                item = json.loads(line)
                                path_str = item.get('path', '')
                                if not path_str: continue

                                file_path = Path(path_str)
                                if not file_path.exists():
                                    continue
                                
                                # Convert Queue Item -> Triage Interface
                                files_for_review.append({
                                    "file_id": item.get('queue_id', str(hash(str(file_path)))),
                                    "file_name": file_path.name,
                                    "file_path": str(file_path),
                                    "classification": {
                                        # Use 'current_category' from queue (latest state)
                                        "category": item.get("current_category", "unknown"),
                                        "confidence": item.get("confidence", 0.0),
                                        "reasoning": item.get("reasoning", "Flagged for review by Adaptive System"),
                                        "needs_review": True
                                    },
                                    "status": "pending_review",
                                    "source": "queue"
                                })
                            except Exception as e:
                                logger.warning(f"Skipping malformed queue line: {e}")
            except Exception as e:
                logger.error(f"Error reading review queue: {e}")

            # 2. FAILBACK SCAN (V2 Legacy/Hybrid)
            # ------------------------------------------------------------------
            # If queue is empty (or < 20 items), scan staging areas for new files
            if len(files_for_review) < 20:
                logger.debug("Queue low/empty - scanning staging areas for new files...")
                confidence_threshold = 0.85 # Triage threshold
                queued_paths = {f['file_path'] for f in files_for_review}
                
                for area in self.staging_areas:
                    if len(files_for_review) >= 20: break
                    if not area.exists(): continue
                    
                    try:
                        # Scan recent files
                        for file_path in area.iterdir():
                            if len(files_for_review) >= 20: break
                            
                            # Filter obvious junk
                            if not file_path.is_file() or file_path.name.startswith('.'): continue
                            if str(file_path) in queued_paths: continue
                            if file_path.stat().st_size > 100 * 1024 * 1024: continue # Skip >100MB
                            
                            try:
                                # Quick Classification
                                result = self.classifier.classify_file(file_path)
                                
                                # Extract stats safely
                                if isinstance(result, dict):
                                    conf = result.get('confidence', 0.0)
                                    cat = result.get('category', 'unknown')
                                    rsn = result.get('reasoning', [])
                                else:
                                    conf = getattr(result, 'confidence', 0.0)
                                    cat = getattr(result, 'category', 'unknown')
                                    rsn = getattr(result, 'reasoning', [])

                                # If low confidence, add to review list
                                if conf < confidence_threshold:
                                    files_for_review.append({
                                        "file_id": str(hash(str(file_path))),
                                        "file_name": file_path.name,
                                        "file_path": str(file_path),
                                        "classification": {
                                            "category": cat,
                                            "confidence": round(conf, 2),
                                            "reasoning": str(rsn),
                                            "needs_review": True
                                        },
                                        "status": "pending_review",
                                        "source": "scan"
                                    })
                            except Exception as e:
                                continue # Skip file on error
                    except Exception as e:
                        logger.warning(f"Error scanning staging area {area}: {e}")

            logger.info(f"Returning {len(files_for_review)} items for Triage")
            
            # Sort: Priority to Queue items? Or by confidence?
            # Let's sort by confidence (lowest = most ambiguous = highest priority)
            files_for_review.sort(key=lambda x: x['classification']['confidence'])
            
            return files_for_review

        except Exception as e:
            logger.error(f"Critical error in get_files_for_review: {e}")
            return []

    def trigger_scan(self) -> Dict[str, Any]:
        """
        Triggers a new scan for files needing review and returns them.

        Returns:
            A dictionary containing the files found for review.
        """
        logger.info("Manual scan for triage files triggered via API.")
        try:
            files = self.get_files_for_review()
            return {
                "status": "success",
                "message": f"Scan complete. Found {len(files)} files for triage.",
                "files_found": len(files),
                "files": files
            }
        except Exception as e:
            logger.error(f"Error during triggered scan: {e}")
            return {
                "status": "error",
                "message": "An error occurred during the scan.",
                "error": str(e)
            }

    def scan_custom_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Scan a custom folder for files needing review (any folder, not just staging areas).

        This method allows users to organize ANY folder through the triage center,
        with all the same features: classification, nested categories, adaptive learning, etc.

        Args:
            folder_path: Absolute path to the folder to scan

        Returns:
            Dictionary with status, message, files_found count, and files list
        """
        logger.info(f"Custom folder scan triggered for: {folder_path}")

        try:
            # Validate that the path exists and is a directory
            folder = Path(folder_path)

            if not folder.exists():
                return {
                    "status": "error",
                    "message": f"Folder does not exist: {folder_path}",
                    "files_found": 0,
                    "files": []
                }

            if not folder.is_dir():
                return {
                    "status": "error",
                    "message": f"Path is not a directory: {folder_path}",
                    "files_found": 0,
                    "files": []
                }

            # Security: Validate path is within user's home directory or AI Organizer root
            user_home = Path.home()
            is_in_home = validate_path_within_base(folder, user_home)
            is_in_base = validate_path_within_base(folder, self.base_dir) if self.base_dir else False

            if not (is_in_home or is_in_base):
                logger.warning(f"Security: Attempted to scan folder outside safe directories: {folder_path}")
                return {
                    "status": "error",
                    "message": "Security: Can only scan folders within your home directory or AI Organizer directory",
                    "files_found": 0,
                    "files": []
                }

            # Supported file extensions (from interactive_batch_processor.py)
            supported_extensions = {
                '.pdf', '.docx', '.doc', '.txt', '.md', '.pages', '.rtf',
                '.jpg', '.png', '.gif', '.jpeg', '.mp4', '.mov', '.avi',
                '.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aiff',
                '.ipynb', '.json', '.csv', '.xlsx'
            }

            files_for_review = []
            confidence_threshold = 0.85  # ADHD-friendly threshold

            # Scan folder recursively for files
            logger.info(f"Scanning {folder_path} recursively for supported files...")
            file_count = 0
            total_scanned = 0

            for file_path in folder.rglob('*'):
                # Skip directories and hidden files
                if not file_path.is_file() or file_path.name.startswith('.'):
                    continue

                # Skip files with unsupported extensions
                if file_path.suffix.lower() not in supported_extensions:
                    continue

                total_scanned += 1

                # Skip very large files to avoid processing delays (PERFORMANCE OPTIMIZATION)
                try:
                    file_size_bytes = file_path.stat().st_size
                    file_size_mb = file_size_bytes / (1024 * 1024)

                    # 10MB limit for faster processing
                    if file_size_mb > 10:
                        logger.info(f"Skipping {file_path.name} ({file_size_mb:.1f}MB) - too large for auto-processing")
                        continue
                except (OSError, PermissionError):
                    continue

                # Limit to 50 files for UI responsiveness (can be increased if needed)
                if file_count >= 50:
                    logger.info(f"Reached limit of 50 files for custom folder scan")
                    break

                try:
                    # Use the unified classification service for intelligent content analysis
                    result = self.classifier.classify_file(file_path)

                    # Handle both dict and object result formats
                    confidence = result.get('confidence', 0.0) if isinstance(result, dict) else getattr(result, 'confidence', 0.0)
                    category = result.get('category', 'unknown') if isinstance(result, dict) else getattr(result, 'category', 'unknown')
                    reasoning = result.get('reasoning', []) if isinstance(result, dict) else getattr(result, 'reasoning', [])

                    # Include ALL files (not just low confidence) for custom folder scan
                    # This allows user to review and organize entire folders
                    files_for_review.append({
                        "file_id": str(hash(str(file_path))),
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "classification": {
                            "category": category,
                            "confidence": round(confidence, 2),
                            "reasoning": reasoning if isinstance(reasoning, str) else str(reasoning),
                            "needs_review": confidence < confidence_threshold
                        },
                        "status": "pending_review" if confidence < confidence_threshold else "ready"
                    })
                    file_count += 1

                except Exception as e:
                    logger.warning(f"Error classifying {file_path}: {e}")
                    continue

            logger.info(f"Custom folder scan complete: {file_count} files found (out of {total_scanned} scanned)")

            # Sort by confidence (lowest first for files needing review)
            files_for_review.sort(key=lambda x: x['classification']['confidence'])

            return {
                "status": "success",
                "message": f"Scan complete. Found {file_count} files in {folder_path}",
                "files_found": file_count,
                "files": files_for_review,
                "folder_scanned": str(folder_path),
                "total_files_scanned": total_scanned
            }

        except Exception as e:
            logger.error(f"Error during custom folder scan: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"An error occurred during the scan: {str(e)}",
                "files_found": 0,
                "files": []
            }

    def get_classification(self, file_path: str) -> Dict[str, Any]:
        """
        Get classification for a file without moving it (for upload preview)

        Args:
            file_path: Path to the file to classify

        Returns:
            Dict with category, confidence, reasoning, and suggested_filename
        """
        if self.classifier is None:
            logger.error("Classification engine not available")
            return {
                "suggested_category": "unknown",
                "confidence": 0.0,
                "reasoning": "Classification engine not available",
                "suggested_filename": Path(file_path).name
            }

        try:
            file_obj = Path(file_path)

            if not file_obj.exists():
                return {
                    "suggested_category": "unknown",
                    "confidence": 0.0,
                    "reasoning": f"File not found: {file_path}",
                    "suggested_filename": file_obj.name
                }

            # Get classification from unified classifier
            result = self.classifier.classify_file(file_obj)

            # Handle both dict and object result formats
            category = result.get('category', 'unknown') if isinstance(result, dict) else getattr(result, 'category', 'unknown')
            confidence = result.get('confidence', 0.0) if isinstance(result, dict) else getattr(result, 'confidence', 0.0)
            reasoning = result.get('reasoning', []) if isinstance(result, dict) else getattr(result, 'reasoning', [])
            suggested_filename = result.get('suggested_filename', file_obj.name) if isinstance(result, dict) else getattr(result, 'suggested_filename', file_obj.name)

            return {
                "suggested_category": category,
                "confidence": round(confidence, 2),
                "reasoning": reasoning if isinstance(reasoning, str) else ', '.join(reasoning) if reasoning else "AI-powered content analysis",
                "suggested_filename": suggested_filename
            }

        except Exception as e:
            logger.error(f"Error classifying file '{file_path}': {e}")
            return {
                "suggested_category": "unknown",
                "confidence": 0.0,
                "reasoning": f"Classification error: {str(e)}",
                "suggested_filename": Path(file_path).name
            }

    def get_known_projects(self) -> Dict[str, str]:
        """
        Get list of known projects for predictive text/autocomplete
        
        Returns:
            Dict mapping project keys to display names
        """
        if self.hierarchical_organizer:
            return self.hierarchical_organizer.KNOWN_PROJECTS
        return {}

    def classify_file(self, file_path: str, confirmed_category: str, project: str = None, episode: str = None) -> Dict[str, Any]:
        """
        Classify a file with user-confirmed category, learn from the decision, and move the file
        with intelligent hierarchical organization (project → episode → media type).

        Args:
            file_path: Path to the file being classified
            confirmed_category: Category confirmed by the user
            project: Optional project name for hierarchical organization
            episode: Optional episode name for hierarchical organization

        Returns:
            Success response with classification status and new file path.
        """
        if self.classifier is None or self.base_dir is None:
            logger.error("Classification engine or base directory not available")
            return {
                "status": "error",
                "message": "Classification engine not available"
            }

        try:
            file_obj = Path(file_path)
            original_name = file_obj.name

            if not file_obj.exists():
                logger.warning(f"File already gone before processing: {file_path}")
                return {
                    "status": "success",
                    "message": f"File '{original_name}' already processed or moved.",
                    "already_processed": True
                }

            # --- Get the intelligent classification result from UnifiedClassificationService ---
            classification_result = self.classifier.classify_file(file_obj)

            # Handle both dict and object result formats
            if isinstance(classification_result, dict):
                original_category = classification_result.get('category', 'unknown')
                original_confidence = classification_result.get('confidence', 0.0)
                suggested_filename = classification_result.get('suggested_filename', file_obj.name)
                # Extract keywords for learning system
                found_keywords = classification_result.get('keywords', [])
            else:
                original_category = getattr(classification_result, 'category', 'unknown')
                original_confidence = getattr(classification_result, 'confidence', 0.0)
                suggested_filename = getattr(classification_result, 'suggested_filename', file_obj.name)
                found_keywords = getattr(classification_result, 'keywords', [])

            # --- Learning Step: Will record classification after successful file move ---
            logger.info(f"User classification for '{file_path}':")
            logger.info(f"  AI Analysis: {original_category} ({original_confidence:.2f}) -> User Confirmed: {confirmed_category}")
            # Learning event will be recorded after file move completes successfully

            # --- Hierarchical File Organization ---
            # Use hierarchical organizer to build deep folder structure
            relative_dest_path, hierarchy_metadata = self.hierarchical_organizer.build_hierarchical_path(
                base_category=confirmed_category,
                file_path=file_obj,
                project_override=project,
                episode_override=episode
            )

            destination_dir = self.base_dir / relative_dest_path
            logger.info(f"Hierarchical organization: {relative_dest_path}")
            logger.info(f"  Project: {hierarchy_metadata.get('project', 'N/A')}")
            logger.info(f"  Episode: {hierarchy_metadata.get('episode', 'N/A')}")
            logger.info(f"  Media Type: {hierarchy_metadata.get('media_type', 'N/A')}")
            logger.info(f"  Hierarchy Level: {hierarchy_metadata.get('hierarchy_level', 0)}")

            # Create the directory if it doesn't exist
            destination_dir.mkdir(parents=True, exist_ok=True)

            # Use intelligent filename suggestion or keep original name
            if suggested_filename and suggested_filename != file_obj.name:
                new_file_path = destination_dir / suggested_filename
            else:
                new_file_path = destination_dir / file_obj.name

            # SAFETY CHECK: Prevent self-collision/recursion
            # If the file is already in the target location, skip the move/rename logic
            # This prevents infinite loops where 'file.txt' -> 'file_1.txt' -> 'file_1_1.txt'
            if new_file_path.resolve() != file_obj.resolve():
                # Handle filename conflicts only if we are actually moving to a new path/name
                counter = 1
                original_new_path = new_file_path
                # --- FIX: Don't treat the source file itself as a conflict! ---
                while new_file_path.exists():
                    if new_file_path.resolve() == file_obj.resolve():
                        break # This is the same file, no conflict
                        
                    stem = original_new_path.stem
                    suffix = original_new_path.suffix
                    new_file_path = destination_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                # Move the file to its new intelligent location
                original_full_path = str(file_obj.absolute())
                # original_name defined at top now
                
                # Use shutil.move to handle cross-device moves (Local -> Google Drive)
                import shutil
                new_file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(original_full_path, str(new_file_path))
                
                logger.info(f"Successfully moved and renamed file to: {new_file_path}")

                # Record operation in rollback system for easy undo
                if self.rollback_service:
                    try:
                        hierarchy_notes = f"Project: {hierarchy_metadata.get('project', 'N/A')}, Episode: {hierarchy_metadata.get('episode', 'N/A')}, Media: {hierarchy_metadata.get('media_type', 'N/A')}"
                        operation_id = self.rollback_service.record_operation(
                            operation_type='organize',
                            original_path=original_full_path,
                            original_filename=original_name,
                            new_filename=new_file_path.name,
                            new_location=str(new_file_path.parent),
                            category=confirmed_category,
                            confidence=original_confidence,
                            notes=f"AI: {original_category} ({original_confidence:.2f}), User: {confirmed_category} | {hierarchy_notes}"
                        )
                        logger.info(f"Recorded rollback operation ID: {operation_id}")
                    except Exception as e:
                        logger.warning(f"Failed to record rollback operation: {e}")
            else:
                logger.info(f"File is already in correct location: {new_file_path}. Skipping move.")

                # Save Metadata Sidecar (JSON)
                # This ensures the rich classification data travels with the file
                try:
                    from unified_classifier import save_metadata_sidecar
                    
                    # Prepare metadata dictionary
                    metadata = {
                        "original_filename": original_name,
                        "classification": {
                            "category": confirmed_category,
                            "confidence": original_confidence,
                            "ai_suggestion": original_category,
                            "reasoning": classification_result.get('reasoning', []) if isinstance(classification_result, dict) else getattr(classification_result, 'reasoning', []),
                            "keywords": found_keywords  # Save keywords in sidecar too
                        },
                        "hierarchy": hierarchy_metadata,
                        "project": project,
                        "episode": episode,
                        "timestamp": dt_module.datetime.now().isoformat()
                    }
                    
                    # Save sidecar next to the new file
                    save_metadata_sidecar(new_file_path, metadata)
                    logger.info(f"Saved metadata sidecar for: {new_file_path.name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to save metadata sidecar: {e}")

            # --- Record Learning Event for Adaptive Learning System ---
            try:
                # Determine media type from file extension
                ext = file_obj.suffix.lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.heic', '.heif']:
                    media_type = 'image'
                elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v', '.wmv']:
                    media_type = 'video'
                elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.aiff']:
                    media_type = 'audio'
                elif ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.pages', '.md']:
                    media_type = 'document'
                else:
                    media_type = 'unknown'

                # Record the classification event with rich context
                # Pass FOUND KEYWORDS to the learning context
                # This enables the system to learn "If keyword X is present -> User Chose Category Y"
                context_features = {
                        'user_confirmed': confirmed_category,
                        'original_filename': original_name,
                        'hierarchy_project': hierarchy_metadata.get('project', 'N/A'),
                        'hierarchy_episode': hierarchy_metadata.get('episode', 'N/A'),
                        'hierarchy_level': hierarchy_metadata.get('hierarchy_level', 0),
                        'media_type_detected': hierarchy_metadata.get('media_type', 'N/A'),
                        'content_keywords': found_keywords  # CRITICAL FOR LEARNING
                }
                
                self.learning_system.record_classification(
                    file_path=str(new_file_path),
                    predicted_category=original_category,
                    confidence=original_confidence,
                    features=context_features,
                    media_type=media_type
                )
                logger.info(f"✅ Learning event recorded: {original_category} ({original_confidence:.2f}) → {confirmed_category} [{media_type}]")
            except Exception as e:
                logger.warning(f"Failed to record learning event: {e}")

            return {
                "status": "success",
                "message": f"File '{original_name}' organized with hierarchical structure.",
                "new_path": str(new_file_path),
                "user_decision": confirmed_category,
                "hierarchy": hierarchy_metadata
            }

        except Exception as e:
            logger.error(f"Error classifying and moving file '{file_path}': {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to process file '{file_path}': {str(e)}"
            }