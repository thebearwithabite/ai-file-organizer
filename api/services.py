#!/usr/bin/env python3
"""
System Services for AI File Organizer API
Provides system status and monitoring functionality
"""

import logging
from typing import Dict, Any, Optional, List

from gdrive_librarian import GoogleDriveLibrarian

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
        """Initialize TriageService"""
        logger.info("TriageService initialized")

    def get_files_for_review(self) -> List[Dict[str, Any]]:
        """
        Get list of files that require manual review
        
        Returns:
            List of files with suggested categories and confidence scores
        """
        try:
            # Mock data matching V3 spec format - files with low confidence needing review
            mock_files = [
                {
                    "file_path": "/Users/ryan/Documents/Entertainment/Client_Agreement_2024.pdf",
                    "suggested_category": "contracts",
                    "confidence": 0.65
                },
                {
                    "file_path": "/Users/ryan/Downloads/Creative_Project_Episode_Script.docx",
                    "suggested_category": "creative_projects",
                    "confidence": 0.58
                },
                {
                    "file_path": "/Users/ryan/Documents/Business/Q4_Commission_Report.xlsx",
                    "suggested_category": "business_operations",
                    "confidence": 0.72
                }
            ]

            logger.info(f"Retrieved {len(mock_files)} files for review")
            return mock_files

        except Exception as e:
            logger.error(f"Error getting files for review: {e}")
            return []

    def classify_file(self, file_path: str, confirmed_category: str) -> Dict[str, Any]:
        """
        Classify a file with user-confirmed category
        
        Args:
            file_path: Path to the file being classified
            confirmed_category: Category confirmed by the user
            
        Returns:
            Success response with classification status
        """
        try:
            # Log the classification information as requested
            logger.info(f"Received classification for '{file_path}'. User confirmed category: '{confirmed_category}'.")

            # Return success message
            return {
                "status": "success",
                "message": f"File '{file_path}' classified as '{confirmed_category}'."
            }

        except Exception as e:
            logger.error(f"Error classifying file '{file_path}': {e}")
            return {
                "status": "error",
                "message": f"Failed to classify file '{file_path}': {str(e)}"
            }