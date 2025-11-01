#!/usr/bin/env python3
"""
Rollback Service for AI File Organizer API
Provides rollback operations for file management
"""

import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from easy_rollback_system import EasyRollbackSystem, FileOperation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RollbackService:
    """Service class for rollback-related operations"""

    def __init__(self):
        """Initialize RollbackService with EasyRollbackSystem"""
        try:
            self.rollback_system = EasyRollbackSystem()
            logger.info("RollbackService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RollbackService: {e}")
            self.rollback_system = None

    def get_operations(self, days: int = 7, today_only: bool = False, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get file operations that can be rolled back

        Args:
            days: Number of days to look back (default: 7)
            today_only: Only show today's operations
            search: Optional search term to filter operations

        Returns:
            List of file operations as dictionaries
        """
        if not self.rollback_system:
            return []

        try:
            # Get operations from rollback system
            operations = self.rollback_system.show_recent_operations(days=days, today_only=today_only)

            # Convert to dict format for API response
            result = []
            for op in operations:
                op_dict = {
                    "operation_id": op.rollback_id,
                    "timestamp": op.timestamp,
                    "operation_type": op.operation_type,
                    "original_filename": op.original_filename,
                    "new_filename": op.new_filename,
                    "original_path": op.original_path,
                    "new_location": op.new_location,
                    "confidence": op.confidence,
                    "status": op.status,
                    "notes": op.notes,
                    "google_drive_id": op.google_drive_id
                }

                # Apply search filter if provided
                if search:
                    search_lower = search.lower()
                    if (search_lower in op.original_filename.lower() or
                        search_lower in op.new_filename.lower() or
                        search_lower in op.original_path.lower()):
                        result.append(op_dict)
                else:
                    result.append(op_dict)

            return result

        except Exception as e:
            logger.error(f"Error getting operations: {e}")
            return []

    def undo_operation(self, operation_id: int) -> Dict[str, Any]:
        """
        Undo a specific file operation

        Args:
            operation_id: ID of the operation to undo

        Returns:
            Dict with success status and message
        """
        if not self.rollback_system:
            return {"success": False, "message": "Rollback system not available"}

        try:
            result = self.rollback_system.undo_operation(operation_id)
            return {
                "success": result.get('success', False),
                "message": result.get('message', result.get('error', 'Unknown error')),
                "operation_id": operation_id
            }
        except Exception as e:
            logger.error(f"Error undoing operation {operation_id}: {e}")
            return {
                "success": False,
                "message": f"Failed to undo operation: {str(e)}",
                "operation_id": operation_id
            }

    def undo_today(self) -> Dict[str, Any]:
        """
        Undo all operations from today (emergency rollback)

        Returns:
            Dict with success status, count, and message
        """
        if not self.rollback_system:
            return {"success": False, "message": "Rollback system not available", "count": 0}

        try:
            result = self.rollback_system.undo_today_operations()
            return {
                "success": result.get('success', False),
                "message": result.get('message', 'Unknown error'),
                "count": result.get('count', 0)
            }
        except Exception as e:
            logger.error(f"Error undoing today's operations: {e}")
            return {
                "success": False,
                "message": f"Failed to undo today's operations: {str(e)}",
                "count": 0
            }

    def record_operation(
        self,
        operation_type: str,
        original_path: str,
        original_filename: str,
        new_filename: str,
        new_location: str,
        category: str = "",
        confidence: float = 0.0,
        notes: str = "",
        google_drive_id: Optional[str] = None
    ) -> int:
        """
        Record a file operation for potential rollback

        Returns the operation_id
        """
        if not self.rollback_system:
            return -1

        try:
            return self.rollback_system.record_operation(
                operation_type=operation_type,
                original_path=original_path,
                original_filename=original_filename,
                new_filename=new_filename,
                new_location=new_location,
                category=category,
                confidence=confidence,
                notes=notes,
                google_drive_id=google_drive_id
            )
        except Exception as e:
            logger.error(f"Error recording operation: {e}")
            return -1
