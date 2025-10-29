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

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google_drive_auth import GoogleDriveAuth
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("⚠️  Google Drive API not available. Local rollback only.")

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
        self.rollback_db = self.project_root / "file_rollback.db"
        
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
    
    def _ensure_database_exists(self):
        """Ensure rollback database exists with proper schema"""
        
        if not self.rollback_db.exists():
            print("📄 Creating rollback database...")
        
        with sqlite3.connect(self.rollback_db) as conn:
            # Create table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_rollback (
                    rollback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_timestamp TEXT,
                    operation_type TEXT DEFAULT 'rename',
                    original_path TEXT,
                    original_filename TEXT,
                    new_filename TEXT,
                    new_location TEXT,
                    gdrive_folder TEXT,
                    gdrive_file_id TEXT,
                    category TEXT,
                    confidence REAL,
                    rollback_status TEXT DEFAULT 'active',
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add missing columns if they don't exist
            try:
                conn.execute("ALTER TABLE file_rollback ADD COLUMN operation_type TEXT DEFAULT 'rename'")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                conn.execute("ALTER TABLE file_rollback ADD COLUMN new_location TEXT")
            except sqlite3.OperationalError:
                pass
                
            try:
                conn.execute("ALTER TABLE file_rollback ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
            except sqlite3.OperationalError:
                pass
    
    def show_recent_operations(self, days: int = 7, today_only: bool = False) -> List[FileOperation]:
        """Show recent file operations that can be rolled back"""
        
        with sqlite3.connect(self.rollback_db) as conn:
            if today_only:
                # Show only today's operations
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = conn.execute("""
                    SELECT * FROM file_rollback 
                    WHERE DATE(operation_timestamp) = ?
                    ORDER BY operation_timestamp DESC
                """, (today,))
            else:
                # Show operations from last N days
                if days >= 30:
                    # Show all operations for large day ranges
                    cursor = conn.execute("""
                        SELECT * FROM file_rollback 
                        ORDER BY operation_timestamp DESC
                    """)
                else:
                    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                    cursor = conn.execute("""
                        SELECT * FROM file_rollback 
                        WHERE DATE(operation_timestamp) >= ?
                        ORDER BY operation_timestamp DESC
                    """, (since_date,))
            
            operations = []
            for row in cursor.fetchall():
                # Map columns based on actual database schema discovered in debug
                # [0]=rollback_id, [1]=timestamp, [2]=original_path, [3]=original_filename, 
                # [4]=new_filename, [5]=gdrive_folder, [6]=gdrive_file_id, [7]=category, 
                # [8]=confidence, [9]=rollback_status, [10]=notes, [11]=operation_type, [12]=new_location
                op = FileOperation(
                    rollback_id=row[0],                     # rollback_id
                    timestamp=row[1],                       # operation_timestamp
                    operation_type=row[11] if len(row) > 11 and row[11] else 'rename',  # operation_type
                    original_path=row[2] if row[2] else '', # original_path
                    original_filename=row[3],               # original_filename
                    new_filename=row[4],                    # new_filename
                    new_location=row[12] if len(row) > 12 and row[12] else row[5],  # new_location or gdrive_folder
                    confidence=row[8] if row[8] else 0.0,   # confidence
                    status=row[9],                          # rollback_status
                    google_drive_id=row[6],                 # gdrive_file_id
                    notes=row[10] if row[10] else ''        # notes
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
                SELECT * FROM file_rollback WHERE rollback_id = ?
            """, (rollback_id,))
            
            row = cursor.fetchone()
            if not row:
                return {
                    'success': False,
                    'error': f"Operation {rollback_id} not found"
                }
            
            operation = FileOperation(
                rollback_id=row[0],                     # rollback_id
                timestamp=row[1],                       # operation_timestamp
                operation_type=row[11] if len(row) > 11 and row[11] else 'rename',  # operation_type
                original_path=row[2] if row[2] else '', # original_path
                original_filename=row[3],               # original_filename
                new_filename=row[4],                    # new_filename
                new_location=row[12] if len(row) > 12 and row[12] else row[5],  # new_location or gdrive_folder
                confidence=row[8] if row[8] else 0.0,   # confidence
                status=row[9],                          # rollback_status
                google_drive_id=row[6],                 # gdrive_file_id
                notes=row[10] if row[10] else ''        # notes
            )
        
        # Check if already rolled back
        if operation.status == 'executed':
            return {
                'success': False,
                'error': f"Operation {rollback_id} already rolled back"
            }
        
        print(f"🔄 ROLLING BACK OPERATION {rollback_id}")
        print(f"   📁 File: '{operation.new_filename}' → '{operation.original_filename}'")
        print(f"   📍 Location: {operation.new_location}")
        
        # Perform rollback based on operation type
        if operation.google_drive_id:
            result = self._rollback_google_drive_operation(operation)
        else:
            result = self._rollback_local_operation(operation)
        
        # Update database
        with sqlite3.connect(self.rollback_db) as conn:
            if result['success']:
                conn.execute("""
                    UPDATE file_rollback 
                    SET rollback_status = 'executed', 
                        notes = notes || ? || ?
                    WHERE rollback_id = ?
                """, (
                    ' | ROLLBACK EXECUTED: ',
                    datetime.now().isoformat(),
                    rollback_id
                ))
                print(f"✅ Rollback successful!")
            else:
                conn.execute("""
                    UPDATE file_rollback 
                    SET rollback_status = 'failed',
                        notes = notes || ? || ?
                    WHERE rollback_id = ?
                """, (
                    ' | ROLLBACK FAILED: ',
                    result['error'],
                    rollback_id
                ))
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