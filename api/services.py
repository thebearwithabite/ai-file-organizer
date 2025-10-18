#!/usr/bin/env python3
"""
System Services for AI File Organizer API
Provides system status and monitoring functionality
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from gdrive_librarian import GoogleDriveLibrarian
from unified_classifier import UnifiedClassificationService
from gdrive_integration import get_ai_organizer_root

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemService:
    """Service class for system-related operations"""

    # Class-level shared instance to avoid re-initialization
    _librarian_instance: Optional[GoogleDriveLibrarian] = None
    _initialization_error: Optional[str] = None

    def __init__(self):
        """Initialize SystemService with shared GoogleDriveLibrarian instance"""
        if SystemService._librarian_instance is None:
            try:
                logger.info("Initializing GoogleDriveLibrarian for SystemService...")
                SystemService._librarian_instance = GoogleDriveLibrarian(
                    cache_size_gb=2.0,
                    auto_sync=False  # Disable auto-sync for API stability
                )
                SystemService._librarian_instance.initialize()
                logger.info("GoogleDriveLibrarian initialized successfully")
            except Exception as e:
                SystemService._initialization_error = str(e)
                logger.error(f"Failed to initialize GoogleDriveLibrarian: {e}")
                SystemService._librarian_instance = None

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

        try:
            # Get real status from GoogleDriveLibrarian
            status = SystemService._librarian_instance.get_system_status()

            # Safely access nested dictionaries
            components = status.get("components", {})
            auth_info = status.get("auth_info", {})
            cache_info = components.get("cache", {})
            metadata_info = components.get("metadata_store", {})
            sync_info = components.get("sync_service", {})

            # Transform to API-friendly format
            return {
                "indexed_files": metadata_info.get("total_files", 0),
                "files_in_staging": cache_info.get("files_cached", 0),
                "last_run": status.get("last_drive_scan", "N/A"),
                "authentication_status": "authenticated" if status.get("authenticated") else "unauthenticated",
                "google_drive_user": auth_info.get("user_name", "Unknown"),
                "cache_size_mb": cache_info.get("size_mb", 0),
                "sync_service_status": sync_info.get("status", "disabled")
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

    def __init__(self):
        """Initialize TriageService with classification engine"""
        try:
            # Initialize with AI Organizer root directory
            self.base_dir = get_ai_organizer_root()

            # Initialize the unified classification service with AI-powered content analysis
            self.classifier = UnifiedClassificationService()

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

    def get_files_for_review(self) -> List[Dict[str, Any]]:
        """
        Get list of files that require manual review based on low confidence scores
        
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

                    # Skip very large files to avoid processing delays
                    try:
                        if file_path.stat().st_size > 100 * 1024 * 1024:  # 100MB limit
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
                            files_for_review.append({
                                "file_path": str(file_path),
                                "suggested_category": category,
                                "confidence": round(confidence, 2),
                                "reasoning": reasoning,
                                "source": source
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

    def classify_file(self, file_path: str, confirmed_category: str) -> Dict[str, Any]:
        """
        Classify a file with user-confirmed category, learn from the decision, and move the file
        with an intelligent new name.
        
        Args:
            file_path: Path to the file being classified
            confirmed_category: Category confirmed by the user
            
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
            
            # --- Intelligent File Organization ---
            # Create destination directory based on confirmed category
            category_mapping = {
                'entertainment': '01_ACTIVE_PROJECTS/Entertainment_Industry',
                'financial': '01_ACTIVE_PROJECTS/Business_Operations/Financial_Records',
                'creative': '01_ACTIVE_PROJECTS/Creative_Projects',
                'development': '01_ACTIVE_PROJECTS/Development_Projects',
                'audio': '01_ACTIVE_PROJECTS/Creative_Projects/Audio_Content',
                'image': '01_ACTIVE_PROJECTS/Creative_Projects/Visual_Content',
                'text_document': '02_REFERENCE/Documents',
                'unknown': '99_TEMP_PROCESSING/Manual_Review'
            }
            
            relative_dest_path = category_mapping.get(confirmed_category.lower(), '99_TEMP_PROCESSING/Manual_Review')
            destination_dir = self.base_dir / relative_dest_path

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
            file_obj.rename(new_file_path)
            
            logger.info(f"Successfully moved and renamed file to: {new_file_path}")

            return {
                "status": "success",
                "message": f"File '{file_obj.name}' classified and moved successfully.",
                "new_path": str(new_file_path),
                "user_decision": confirmed_category
            }

        except Exception as e:
            logger.error(f"Error classifying and moving file '{file_path}': {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to process file '{file_path}': {str(e)}"
            }