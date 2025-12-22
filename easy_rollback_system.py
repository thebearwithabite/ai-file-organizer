#!/usr/bin/env python3
"""
Easy Rollback System - ADHD-Friendly Undo for File Operations
Simple, visual interface for undoing any AI file operations that went wrong.

ADHD-Friendly Design Principles:
- Visual file previews with before/after names
- One-click undo operations  
- Clear success/failure feedback
- No complex menus or confusing options
- Grouped by date for easy navigation
- Search functionality to find specific files

Usage:
    python easy_rollback_system.py              # Interactive GUI mode
    python easy_rollback_system.py --list       # Show recent operations
    python easy_rollback_system.py --undo 123   # Undo specific operation
    python easy_rollback_system.py --today      # Show today's operations only

Created by: Claude AI Assistant
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import argparse

# Import centralized configuration root
from gdrive_integration import get_metadata_root

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google_drive_auth import GoogleDriveAuth
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("⚠️  Google Drive API not available. Local rollback only.")

# ==============================================================================
# ROLLBACK DATABASE SCHEMA (Single Source of Truth)
# ==============================================================================

ROLLBACK_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS file_operations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,             -- ISO8601
  action TEXT NOT NULL,                -- 'move' | 'rename' | 'delete' | 'restore'
  src_path TEXT,                       -- NULL for deletes
  dst_path TEXT,                       -- NULL for deletes
  confidence REAL,                     -- optional
  details TEXT                         -- JSON: {"category": "...", "notes": "..."}
);
CREATE INDEX IF NOT EXISTS idx_file_operations_time ON file_operations(timestamp);
CREATE INDEX IF NOT EXISTS idx_file_operations_src ON file_operations(src_path);
CREATE INDEX IF NOT EXISTS idx_file_operations_dst ON file_operations(dst_path);
"""

def ensure_rollback_db() -> Path:
    """
    Ensure rollback database exists with proper schema.

    This function is idempotent and safe to call at any time.
    Creates ~/.ai_organizer_config/rollback.db if it doesn't exist.

    Returns:
        Path: Path to the rollback database
    """
    db_path = get_metadata_root() / "databases" / "rollback.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(ROLLBACK_SCHEMA_SQL)
    return db_path

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def log_file_op(action: str, src_path: Optional[str] = None, dst_path: Optional[str] = None,
                confidence: Optional[float] = None, details: Optional[Dict[str, Any]] = None) -> int:
    """
    Log a file operation to the rollback database.

    Args:
        action: Operation type ('move', 'rename', 'delete', 'restore')
        src_path: Source file path (optional for deletes)
        dst_path: Destination file path (optional for deletes)
        confidence: Classification confidence (optional)
        details: Additional details as dict (optional)

    Returns:
        int: Operation ID
    """
    db = ensure_rollback_db()
    with sqlite3.connect(db) as conn:
        cursor = conn.execute(
            """INSERT INTO file_operations (timestamp, action, src_path, dst_path, confidence, details)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(timespec="seconds"),
                action,
                str(src_path) if src_path else None,
                str(dst_path) if dst_path else None,
                float(confidence) if confidence is not None else None,
                json.dumps(details) if details else None,
            ),
        )
        return cursor.lastrowid

# ==============================================================================
# LEGACY CLASSES (Backwards Compatibility)
# ==============================================================================

@dataclass
class FileOperation:
    """Represents a file operation that can be rolled back"""
    rollback_id: int
    timestamp: str
    operation_type: str  # rename, move, delete, upload
    original_path: str
    original_filename: str
    new_filename: str
    new_location: str
    confidence: float
    status: str  # active, executed, failed
    google_drive_id: Optional[str] = None
    notes: str = ""

class EasyRollbackSystem:
    """
    ADHD-Friendly Rollback System
    
    Makes it super easy to undo file operations that went wrong.
    No complex interfaces - just "what happened" and "undo this".
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        # Use centralized config DB
        self.rollback_db = get_metadata_root() / "databases" / "rollback.db"
        
        # Google Drive integration
        self.gdrive_auth = None
        self.gdrive_service = None
        
        if GOOGLE_DRIVE_AVAILABLE:
            try:
                self.gdrive_auth = GoogleDriveAuth()
                # Don't auto-authenticate - only when needed
            except Exception as e:
                print(f"⚠️  Google Drive authentication failed: {e}")
        
        self._ensure_database_exists()

    def record_operation(self, operation_type: str, original_path: str, original_filename: str, 
                        new_filename: str, new_location: str, category: str, 
                        confidence: float, notes: str, google_drive_id: Optional[str] = None) -> int:
        """Record an operation to the database (API wrapper)"""
        details = {
            "category": category,
            "notes": notes,
            "original_filename": original_filename,
            "google_drive_id": google_drive_id
        }
        return log_file_op(
            action=operation_type,
            src_path=original_path,
            dst_path=str(Path(new_location) / new_filename),
            confidence=confidence,
            details=details
        )

    @property
    def db_path(self) -> Path:
        """Get path to rollback database (for debug logging compatibility)"""
        return self.rollback_db

    def was_ai_operation(self, file_path: str) -> bool:
        """Check if a file was recently moved/renamed by the AI (within last 60s)"""
        try:
            with sqlite3.connect(self.rollback_db) as conn:
                cutoff = (datetime.now() - timedelta(seconds=60)).isoformat(timespec="seconds")
                cursor = conn.execute(
                    "SELECT id FROM file_operations WHERE (src_path = ? OR dst_path = ?) AND timestamp > ?",
                    (str(file_path), str(file_path), cutoff)
                )
                return cursor.fetchone() is not None
        except Exception:
            return False

    def start_operation(self, operation_type: str, description: str, confidence: float = 1.0) -> int:
        """Start a high-level operation tracking entry"""
        return log_file_op(
            action=operation_type,
            confidence=confidence,
            details={"notes": description, "status": "started"}
        )

    def record_file_operation(self, operation_id: int, original_path: str, new_path: str, operation_type: str = "move"):
        """Record a specific file-level action linked to an operation"""
        log_file_op(
            action=operation_type,
            src_path=original_path,
            dst_path=new_path,
            details={"parent_op_id": operation_id}
        )

    def complete_operation(self, operation_id: int, success: bool = True, error: str = None):
        """Finalize an operation entry"""
        try:
            with sqlite3.connect(self.rollback_db) as conn:
                # Load current details
                cursor = conn.execute("SELECT details FROM file_operations WHERE id = ?", (operation_id,))
                row = cursor.fetchone()
                details = json.loads(row[0]) if row and row[0] else {}
                
                details["status"] = "success" if success else "failed"
                if error:
                    details["error"] = error
                
                conn.execute(
                    "UPDATE file_operations SET details = ? WHERE id = ?",
                    (json.dumps(details), operation_id)
                )
        except Exception as e:
            print(f"⚠️ Failed to complete rollback operation record: {e}")
    
    def _ensure_database_exists(self):
        """Ensure rollback database exists with proper schema"""
        
        if not self.rollback_db.exists():
            print("📄 Creating rollback database...")
            self.rollback_db.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.rollback_db) as conn:
            # Create table if it doesn't exist (using centralized schema)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_operations (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT NOT NULL,
                  action TEXT NOT NULL,
                  src_path TEXT,
                  dst_path TEXT,
                  confidence REAL,
                  details TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_operations_time ON file_operations(timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_operations_src ON file_operations(src_path);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_operations_dst ON file_operations(dst_path);")
    
    def show_recent_operations(self, days: int = 7, today_only: bool = False) -> List[FileOperation]:
        """Show recent file operations that can be rolled back"""
        
        with sqlite3.connect(self.rollback_db) as conn:
            if today_only:
                # Show only today's operations
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = conn.execute("""
                    SELECT * FROM file_operations 
                    WHERE DATE(timestamp) = ?
                    ORDER BY timestamp DESC
                    LIMIT 200
                """, (today,))
            else:
                # Show operations from last N days
                if days >= 30:
                    # Show all operations for large day ranges
                    cursor = conn.execute("""
                        SELECT * FROM file_operations 
                        ORDER BY timestamp DESC
                    """)
                else:
                    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                    cursor = conn.execute("""
                        SELECT * FROM file_operations 
                        WHERE DATE(timestamp) >= ?
                        ORDER BY timestamp DESC
                        LIMIT 200
                    """, (since_date,))
            
            operations = []
            for row in cursor.fetchall():
                # Map columns from file_operations schema:
                # [0]=id, [1]=timestamp, [2]=action, [3]=src_path, [4]=dst_path, [5]=confidence, [6]=details
                
                details = {}
                if len(row) > 6 and row[6]:
                    try:
                        details = json.loads(row[6])
                    except:
                        pass
                
                # Extract fields from details or columns
                original_filename = Path(row[3]).name if row[3] else "unknown"
                new_filename = Path(row[4]).name if row[4] else "unknown"
                new_location = str(Path(row[4]).parent) if row[4] else ""
                
                op = FileOperation(
                    rollback_id=row[0],
                    timestamp=row[1],
                    operation_type=row[2],
                    original_path=row[3] if row[3] else '',
                    original_filename=original_filename,
                    new_filename=new_filename,
                    new_location=new_location,
                    confidence=row[5] if row[5] else 0.0,
                    status='active', # file_operations doesn't track status yet, assume active
                    google_drive_id=details.get('google_drive_id'),
                    notes=details.get('notes', '')
                )
                operations.append(op)
        
        return operations
    
    def display_operations_friendly(self, operations: List[FileOperation]):
        """Display operations in an ADHD-friendly format"""
        
        if not operations:
            print("✅ No recent file operations found!")
            print("💡 This means no files have been automatically renamed or moved recently.")
            return
        
        print(f"\n📋 RECENT FILE OPERATIONS ({len(operations)} found)")
        print("=" * 80)
        
        # Group by date for easier navigation
        operations_by_date = {}
        for op in operations:
            date_key = op.timestamp[:10]  # YYYY-MM-DD
            if date_key not in operations_by_date:
                operations_by_date[date_key] = []
            operations_by_date[date_key].append(op)
        
        for date, date_ops in operations_by_date.items():
            date_obj = datetime.fromisoformat(date)
            friendly_date = date_obj.strftime("%B %d, %Y")
            
            print(f"\n📅 {friendly_date}")
            print("-" * 40)
            
            for op in date_ops:
                time_part = op.timestamp[11:19]  # HH:MM:SS
                status_icon = self._get_status_icon(op.status)
                confidence_color = self._get_confidence_color(op.confidence)
                
                print(f"\n{status_icon} [{op.rollback_id:3d}] {time_part}")
                print(f"    📁 Original: '{op.original_filename}'")
                print(f"    ➡️  Renamed: '{op.new_filename}'")
                print(f"    📍 Location: {op.new_location}")
                print(f"    {confidence_color} Confidence: {op.confidence:.1f}%")
                
                if op.notes:
                    print(f"    💬 Notes: {op.notes}")
                
                if op.status == 'active':
                    print(f"    🔧 Rollback: python easy_rollback_system.py --undo {op.rollback_id}")
                elif op.status == 'executed':
                    print(f"    ✅ Already rolled back")
                
        print(f"\n💡 QUICK ACTIONS:")
        print(f"   • Undo specific operation: python easy_rollback_system.py --undo ID")
        print(f"   • Undo ALL today's operations: python easy_rollback_system.py --undo-today")
        print(f"   • Show today only: python easy_rollback_system.py --today")
    
    def _get_status_icon(self, status: str) -> str:
        """Get icon for operation status"""
        icons = {
            'active': '🔴',     # Can be undone
            'executed': '✅',   # Already undone
            'failed': '❌',     # Undo failed
            'expired': '⏰'     # Too old to undo
        }
        return icons.get(status, '❓')
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get colored confidence indicator"""
        if confidence >= 90:
            return '🟢'  # High confidence - probably correct
        elif confidence >= 75:
            return '🟡'  # Medium confidence - might be wrong
        else:
            return '🔴'  # Low confidence - likely wrong
    
    def undo_operation(self, rollback_id: int) -> Dict[str, Any]:
        """Undo a specific file operation"""
        
        # Get operation details
        with sqlite3.connect(self.rollback_db) as conn:
            cursor = conn.execute("""
                SELECT * FROM file_operations WHERE id = ?
            """, (rollback_id,))
            
            row = cursor.fetchone()
            if not row:
                return {
                    'success': False,
                    'error': f"Operation {rollback_id} not found"
                }
            
            details = {}
            if len(row) > 6 and row[6]:
                try:
                    details = json.loads(row[6])
                except:
                    pass

            original_filename = Path(row[3]).name if row[3] else "unknown"
            new_filename = Path(row[4]).name if row[4] else "unknown"
            new_location = str(Path(row[4]).parent) if row[4] else ""

            operation = FileOperation(
                rollback_id=row[0],
                timestamp=row[1],
                operation_type=row[2],
                original_path=row[3] if row[3] else '',
                original_filename=original_filename,
                new_filename=new_filename,
                new_location=new_location,
                confidence=row[5] if row[5] else 0.0,
                status='active', # file_operations doesn't track status yet
                google_drive_id=details.get('google_drive_id'),
                notes=details.get('notes', '')
            )
        
        # Check if already rolled back (need to implement status tracking in file_operations)
        # For now, we trust the user's intent to undo
        
        print(f"🔄 ROLLING BACK OPERATION {rollback_id}")
        print(f"   📁 File: '{operation.new_filename}' → '{operation.original_filename}'")
        print(f"   📍 Location: {operation.new_location}")
        
        # Perform rollback based on operation type
        if operation.google_drive_id:
            result = self._rollback_google_drive_operation(operation)
        else:
            result = self._rollback_local_operation(operation)
        
        # Update database (append to details since we don't have status/notes columns)
        with sqlite3.connect(self.rollback_db) as conn:
            if result['success']:
                # Append success note to details
                details['rollback_status'] = 'executed'
                details['rollback_timestamp'] = datetime.now().isoformat()
                conn.execute("""
                    UPDATE file_operations 
                    SET details = ?
                    WHERE id = ?
                """, (json.dumps(details), rollback_id))
                print(f"✅ Rollback successful!")
            else:
                # Append failure note
                details['rollback_status'] = 'failed'
                details['rollback_error'] = result['error']
                conn.execute("""
                    UPDATE file_operations 
                    SET details = ?
                    WHERE id = ?
                """, (json.dumps(details), rollback_id))
                print(f"❌ Rollback failed: {result['error']}")
        
        return result
    
    def _rollback_google_drive_operation(self, operation: FileOperation) -> Dict[str, Any]:
        """Rollback a Google Drive file operation"""
        
        if not GOOGLE_DRIVE_AVAILABLE:
            return {
                'success': False,
                'error': 'Google Drive API not available'
            }
        
        try:
            # Authenticate if needed
            if not self.gdrive_service:
                test_result = self.gdrive_auth.test_authentication()
                if not test_result['success']:
                    return {
                        'success': False,
                        'error': f"Google Drive authentication failed: {test_result['error']}"
                    }
                self.gdrive_service = self.gdrive_auth.get_authenticated_service()
            
            # Rename file back to original name
            file_metadata = {
                'name': operation.original_filename
            }
            
            self.gdrive_service.files().update(
                fileId=operation.google_drive_id,
                body=file_metadata
            ).execute()
            
            return {
                'success': True,
                'message': f"Renamed '{operation.new_filename}' back to '{operation.original_filename}' in Google Drive"
            }
            
        except HttpError as e:
            return {
                'success': False,
                'error': f"Google Drive API error: {e}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error: {e}"
            }
    
    def _rollback_local_operation(self, operation: FileOperation) -> Dict[str, Any]:
        """Rollback a local file operation"""
        
        # For local operations, try to find and rename the file
        from gdrive_integration import get_ai_organizer_root
        possible_locations = [
            Path(operation.new_location) / operation.new_filename,
            Path(operation.original_path),
            get_ai_organizer_root() / operation.new_filename,
            Path.home() / "Downloads" / operation.new_filename,
            Path.home() / "Desktop" / operation.new_filename
        ]
        
        for file_path in possible_locations:
            if file_path.exists():
                try:
                    original_path = file_path.parent / operation.original_filename
                    file_path.rename(original_path)
                    
                    return {
                        'success': True,
                        'message': f"Renamed '{file_path}' back to '{original_path}'"
                    }
                except Exception as e:
                    continue
        
        return {
            'success': False,
            'error': f"Could not find file '{operation.new_filename}' to rollback"
        }
    
    def undo_today_operations(self) -> Dict[str, Any]:
        """Undo all operations from today"""
        
        today_ops = self.show_recent_operations(today_only=True)
        active_ops = [op for op in today_ops if op.status == 'active']
        
        if not active_ops:
            return {
                'success': True,
                'message': 'No active operations from today to undo',
                'count': 0
            }
        
        print(f"🔄 ROLLING BACK {len(active_ops)} OPERATIONS FROM TODAY")
        
        success_count = 0
        failed_count = 0
        
        for op in active_ops:
            result = self.undo_operation(op.rollback_id)
            if result['success']:
                success_count += 1
            else:
                failed_count += 1
        
        return {
            'success': success_count > 0,
            'message': f"Rolled back {success_count} operations, {failed_count} failed",
            'count': success_count,
            'failed': failed_count
        }
    
    def search_operations(self, search_term: str) -> List[FileOperation]:
        """Search for operations by filename"""
        
        all_operations = self.show_recent_operations(days=30)  # Search last 30 days
        
        search_lower = search_term.lower()
        matching_ops = []
        
        for op in all_operations:
            if (search_lower in op.original_filename.lower() or 
                search_lower in op.new_filename.lower() or
                search_lower in op.new_location.lower()):
                matching_ops.append(op)
        
        return matching_ops
    
    def create_gui_interface(self):
        """Create a simple GUI for non-technical users"""
        
        print("🖥️  GUI Interface not yet implemented.")
        print("💡 For now, use the command-line interface:")
        print()
        print("   📋 View recent operations:")
        print("       python easy_rollback_system.py --list")
        print()
        print("   🔄 Undo specific operation:")
        print("       python easy_rollback_system.py --undo 123")
        print()
        print("   🔄 Undo all today's operations:")
        print("       python easy_rollback_system.py --undo-today")
        print()
        print("   🔍 Search for specific files:")
        print("       python easy_rollback_system.py --search 'demo reel'")

def main():
    """Command-line interface for rollback system"""
    
    parser = argparse.ArgumentParser(
        description='Easy Rollback System - Undo AI file operations that went wrong',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python easy_rollback_system.py --list           # Show recent operations
  python easy_rollback_system.py --today          # Show today's operations only
  python easy_rollback_system.py --undo 123       # Undo operation #123
  python easy_rollback_system.py --undo-today     # Undo all today's operations
  python easy_rollback_system.py --search "demo"  # Search for operations containing "demo"
        """
    )
    
    parser.add_argument('--list', action='store_true', help='Show recent file operations')
    parser.add_argument('--today', action='store_true', help='Show only today\'s operations')
    parser.add_argument('--undo', type=int, metavar='ID', help='Undo specific operation by ID')
    parser.add_argument('--undo-today', action='store_true', help='Undo all operations from today')
    parser.add_argument('--search', metavar='TERM', help='Search for operations containing term')
    parser.add_argument('--days', type=int, default=7, help='Number of days to show (default: 7)')
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface')
    
    args = parser.parse_args()
    
    # Initialize rollback system
    rollback = EasyRollbackSystem()
    
    try:
        if args.gui:
            rollback.create_gui_interface()
        
        elif args.undo:
            result = rollback.undo_operation(args.undo)
            if not result['success']:
                print(f"❌ {result['error']}")
                exit(1)
        
        elif args.undo_today:
            result = rollback.undo_today_operations()
            print(f"📊 {result['message']}")
        
        elif args.search:
            matching_ops = rollback.search_operations(args.search)
            print(f"🔍 Search results for '{args.search}':")
            rollback.display_operations_friendly(matching_ops)
        
        elif args.list or args.today:
            operations = rollback.show_recent_operations(
                days=args.days, 
                today_only=args.today
            )
            rollback.display_operations_friendly(operations)
        
        else:
            # Default: show recent operations
            operations = rollback.show_recent_operations(days=3)  # Last 3 days
            if operations:
                rollback.display_operations_friendly(operations)
            else:
                print("✅ No recent file operations found!")
                print()
                print("💡 This rollback system tracks AI file operations so you can easily undo them.")
                print("💡 Operations include: file renaming, moving, and Google Drive uploads.")
                print()
                print("📋 To see older operations: python easy_rollback_system.py --list --days 30")
    
    except KeyboardInterrupt:
        print("\n👋 Cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()