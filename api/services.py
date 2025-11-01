#!/usr/bin/env python3
"""
System Services for AI File Organizer API
Provides system status and monitoring functionality
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

from gdrive_librarian import GoogleDriveLibrarian
from unified_classifier import UnifiedClassificationService
from gdrive_integration import get_ai_organizer_root
from hierarchical_organizer import HierarchicalOrganizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemService:
    """Service class for system-related operations"""

    # Class-level shared instance to avoid re-initialization
    _librarian_instance: Optional[GoogleDriveLibrarian] = None
    _initialization_error: Optional[str] = None
    _initialized: bool = False

    def __init__(self):
        """Initialize SystemService with lazy GoogleDriveLibrarian loading"""
        if SystemService._librarian_instance is None:
            try:
                logger.info("Creating GoogleDriveLibrarian (lazy initialization mode)...")
                SystemService._librarian_instance = GoogleDriveLibrarian(
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

    def _ensure_initialized(self):
        """Ensure librarian is initialized before use (lazy initialization)"""
        if SystemService._librarian_instance and not SystemService._initialized:
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
        Get current system status from GoogleDriveLibrarian

        Returns:
            Dict containing real system status information
        """
        if SystemService._librarian_instance is None:
            # Return fallback status when librarian failed to initialize
            return {
                "status": "error",
                "message": "GoogleDriveLibrarian not initialized",
                "error": SystemService._initialization_error,
                "indexed_files": 0,
                "files_in_staging": 0,
                "last_run": None
            }

        # Ensure initialized before getting status
        self._ensure_initialized()

        try:
            # Get real status from GoogleDriveLibrarian
            status = SystemService._librarian_instance.get_system_status()

            # Safely access nested dictionaries
            components = status.get("components", {})
            auth_info = status.get("auth_info", {})
            cache_info = components.get("cache", {})
            metadata_info = components.get("metadata_store", {})
            sync_info = components.get("sync_service", {})

            # Get disk space info
            disk_space = self.get_disk_space()

            # Transform to API-friendly format
            return {
                "indexed_files": metadata_info.get("total_files", 0),
                "files_in_staging": cache_info.get("files_cached", 0),
                "last_run": status.get("last_drive_scan", "N/A"),
                "authentication_status": "authenticated" if status.get("authenticated") else "unauthenticated",
                "google_drive_user": auth_info.get("user_name", "Unknown"),
                "cache_size_mb": cache_info.get("size_mb", 0),
                "sync_service_status": sync_info.get("status", "disabled"),
                "disk_space": disk_space
            }

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "status": "error",
                "message": "Failed to retrieve system status",
                "error": str(e),
                "indexed_files": 0,
                "files_in_staging": 0,
                "last_run": None
            }

    def get_disk_space(self) -> Dict[str, Any]:
        """
        Get current disk space information

        Returns:
            Dict with free_gb, total_gb, percent_used, and status
        """
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                total_str = parts[1].replace('Gi', '')
                used_str = parts[2].replace('Gi', '')
                avail_str = parts[3].replace('Gi', '')

                total_gb = float(total_str)
                used_gb = float(used_str)
                free_gb = float(avail_str)
                percent_used = int((used_gb / total_gb) * 100)

                # Determine status
                if free_gb > 20:
                    status = 'safe'
                elif free_gb > 10:
                    status = 'warning'
                else:
                    status = 'critical'

                return {
                    'free_gb': int(free_gb),
                    'total_gb': int(total_gb),
                    'percent_used': percent_used,
                    'status': status
                }
        except Exception as e:
            logger.error(f"Error getting disk space: {e}")

        return {
            'free_gb': 0,
            'total_gb': 0,
            'percent_used': 0,
            'status': 'unknown'
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
    """Service class for search-related operations"""

    def __init__(self):
        """Initialize SearchService using the shared GoogleDriveLibrarian instance"""
        # Use the same shared instance that SystemService created
        self.librarian = SystemService._librarian_instance
        self.system_service = SystemService()  # For accessing _ensure_initialized

        if self.librarian is None:
            logger.warning("SearchService initialized but GoogleDriveLibrarian is not available")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform search using GoogleDriveLibrarian

        Args:
            query: Search query string

        Returns:
            List of search results as dictionaries
        """
        if self.librarian is None:
            logger.error("Cannot perform search: GoogleDriveLibrarian not initialized")
            return []

        # Ensure initialized before searching (lazy initialization)
        self.system_service._ensure_initialized()

        try:
            # Call the search method on GoogleDriveLibrarian
            results = self.librarian.search(query)

            # Convert results to API-friendly format
            api_results = []
            for result in results:
                api_result = {
                    "file_id": getattr(result, 'file_id', ''),
                    "filename": getattr(result, 'filename', ''),
                    "relevance_score": getattr(result, 'relevance_score', 0.0),
                    "matching_content": getattr(result, 'matching_content', ''),
                    "file_category": getattr(result, 'file_category', 'unknown'),
                    "file_size": getattr(result, 'file_size', 0),
                    "last_modified": str(getattr(result, 'last_modified', '')),
                    "local_path": getattr(result, 'local_path', ''),
                    "drive_path": getattr(result, 'drive_path', ''),
                    "availability": getattr(result, 'availability', 'unknown'),
                    "can_stream": getattr(result, 'can_stream', False),
                    "sync_status": getattr(result, 'sync_status', 'unknown'),
                    "reasoning": getattr(result, 'reasoning', [])
                }
                api_results.append(api_result)

            logger.info(f"Search for '{query}' returned {len(api_results)} results")
            return api_results

        except Exception as e:
            logger.error(f"Error performing search for '{query}': {e}")
            return []


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

            # Common staging areas where unorganized files are found
            self.staging_areas = [
                Path.home() / "Downloads",
                Path.home() / "Desktop",
                self.base_dir / "99_TEMP_PROCESSING" / "Downloads_Staging",
                self.base_dir / "99_TEMP_PROCESSING" / "Desktop_Staging",
                self.base_dir / "99_TEMP_PROCESSING" / "Manual_Review"
            ]

            logger.info("TriageService initialized with classification engine")

        except Exception as e:
            logger.error(f"Failed to initialize TriageService: {e}")
            # Fallback to basic initialization
            self.classifier = None
            self.staging_areas = []
            self.base_dir = None
            self.rollback_service = rollback_service

    def get_files_for_review(self) -> List[Dict[str, Any]]:
        """
        Get list of files that require manual review based on low confidence scores

        IMPORTANT: This method performs EXPENSIVE operations (AI classification, vision analysis, etc.)
        It should ONLY be called when the user explicitly requests a triage scan,
        NOT during server initialization.

        Returns:
            List of files with suggested categories and confidence scores below 85%
        """
        if self.classifier is None:
            logger.error("Classification engine not available - returning empty list")
            return []

        try:
            files_for_review = []
            confidence_threshold = 0.85  # ADHD-friendly threshold from classifier

            # Scan staging areas for unorganized files
            for staging_area in self.staging_areas:
                if not staging_area.exists():
                    continue

                logger.info(f"Scanning {staging_area} for files needing review")

                # Get files from this staging area (limit to reasonable number for UI)
                area_files = list(staging_area.rglob('*'))
                file_count = 0

                for file_path in area_files:
                    # Skip directories and hidden files
                    if not file_path.is_file() or file_path.name.startswith('.'):
                        continue

                    # Skip very large files to avoid processing delays (PERFORMANCE OPTIMIZATION)
                    try:
                        file_size_bytes = file_path.stat().st_size
                        file_size_mb = file_size_bytes / (1024 * 1024)

                        # Reduce limit from 100MB to 10MB for faster processing
                        if file_size_mb > 10:  # 10MB limit
                            logger.info(f"Skipping {file_path.name} ({file_size_mb:.1f}MB) - too large for auto-processing")
                            continue
                    except (OSError, PermissionError):
                        continue

                    # Limit files per staging area to keep response manageable
                    if file_count >= 10:
                        break

                    try:
                        # Use the unified classification service for intelligent content analysis
                        result = self.classifier.classify_file(file_path)

                        # Only include files with low confidence that need manual review
                        # Handle both dict and object result formats
                        confidence = result.get('confidence', 0.0) if isinstance(result, dict) else getattr(result, 'confidence', 0.0)
                        category = result.get('category', 'unknown') if isinstance(result, dict) else getattr(result, 'category', 'unknown')
                        reasoning = result.get('reasoning', []) if isinstance(result, dict) else getattr(result, 'reasoning', [])
                        source = result.get('source', 'Unknown') if isinstance(result, dict) else getattr(result, 'source', 'Unknown')

                        if confidence < confidence_threshold:
                            # Format to match frontend TriageFile interface
                            files_for_review.append({
                                "file_id": str(hash(str(file_path))),  # Generate unique ID
                                "file_name": file_path.name,
                                "file_path": str(file_path),
                                "classification": {
                                    "category": category,
                                    "confidence": round(confidence, 2),
                                    "reasoning": reasoning if isinstance(reasoning, str) else str(reasoning),
                                    "needs_review": True  # All files in this list need review
                                },
                                "status": "pending_review"
                            })
                            file_count += 1

                    except Exception as e:
                        logger.warning(f"Error classifying {file_path}: {e}")
                        continue

                # Limit total files to keep UI responsive
                if len(files_for_review) >= 20:
                    break

            logger.info(f"Found {len(files_for_review)} files requiring manual review")

            # Sort by confidence (lowest first - most urgent)
            files_for_review.sort(key=lambda x: x['confidence'])

            return files_for_review

        except Exception as e:
            logger.error(f"Error getting files for review: {e}")
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

            if not file_obj.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }

            # --- Get the intelligent classification result from UnifiedClassificationService ---
            classification_result = self.classifier.classify_file(file_obj)

            # Handle both dict and object result formats
            original_category = classification_result.get('category', 'unknown') if isinstance(classification_result, dict) else getattr(classification_result, 'category', 'unknown')
            original_confidence = classification_result.get('confidence', 0.0) if isinstance(classification_result, dict) else getattr(classification_result, 'confidence', 0.0)
            suggested_filename = classification_result.get('suggested_filename', file_obj.name) if isinstance(classification_result, dict) else getattr(classification_result, 'suggested_filename', file_obj.name)

            # --- Learning Step (Future Implementation) ---
            logger.info(f"User classification for '{file_path}':")
            logger.info(f"  AI Analysis: {original_category} ({original_confidence:.2f}) -> User Confirmed: {confirmed_category}")
            # TODO: Implement learning from user corrections in future updates

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

            # Handle filename conflicts
            counter = 1
            original_new_path = new_file_path
            while new_file_path.exists():
                stem = original_new_path.stem
                suffix = original_new_path.suffix
                new_file_path = destination_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            # Move the file to its new intelligent location
            original_full_path = str(file_obj.absolute())
            original_name = file_obj.name
            file_obj.rename(new_file_path)

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