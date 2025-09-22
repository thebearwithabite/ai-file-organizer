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
from classification_engine import FileClassificationEngine
from interactive_classifier_fixed import ADHDFriendlyClassifier
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

            # Initialize the ADHD-friendly classifier which wraps the classification engine
            self.classifier = ADHDFriendlyClassifier(str(self.base_dir))

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
                        # Use the base classification engine for speed (skip interactive questions)
                        result = self.classifier.base_classifier.classify_file(file_path)

                        # Only include files with low confidence that need manual review
                        if result.confidence < confidence_threshold:
                            files_for_review.append({
                                "file_path": str(file_path),
                                "suggested_category": result.category,
                                "confidence": round(result.confidence, 2)
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

    def classify_file(self, file_path: str, confirmed_category: str) -> Dict[str, Any]:
        """
        Classify a file with user-confirmed category and learn from the decision
        
        Args:
            file_path: Path to the file being classified
            confirmed_category: Category confirmed by the user
            
        Returns:
            Success response with classification status
        """
        if self.classifier is None:
            logger.error("Classification engine not available")
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

            # Get current classification to understand what changed
            original_result = self.classifier.base_classifier.classify_file(file_obj)

            # Log the classification decision with context
            logger.info(f"User classification decision for '{file_path}':")
            logger.info(f"  Original suggestion: {original_result.category} (confidence: {original_result.confidence:.2f})")
            logger.info(f"  User confirmed: {confirmed_category}")

            # If available, use the ADHD-friendly classifier to learn from this decision
            # This helps improve future classifications
            if hasattr(self.classifier, '_learn_from_manual_classification'):
                self.classifier._learn_from_manual_classification(
                    file_obj,
                    confirmed_category,
                    original_result
                )

            # TODO: In a full implementation, you might want to actually move the file
            # to the confirmed category location here, but that depends on your workflow

            return {
                "status": "success",
                "message": f"File '{file_path}' classified as '{confirmed_category}'. System learned from this decision.",
                "original_suggestion": original_result.category,
                "original_confidence": round(original_result.confidence, 2),
                "user_decision": confirmed_category
            }

        except Exception as e:
            logger.error(f"Error classifying file '{file_path}': {e}")
            return {
                "status": "error",
                "message": f"Failed to classify file '{file_path}': {str(e)}"
            }