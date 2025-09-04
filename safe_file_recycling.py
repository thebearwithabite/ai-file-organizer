#!/usr/bin/env python3
"""
Safe File Recycling System
Creates a temporary "recycling box" for file organization operations
Allows easy undo of file moves with automatic cleanup after 7 days
ADHD-friendly with simple recovery commands
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3

@dataclass
class RecycledFile:
    """Track a file that was moved to recycling"""
    original_path: str
    recycled_path: str
    destination_path: str  # Where it was supposed to go
    recycled_time: str
    operation_type: str  # "organize", "duplicate", "manual"
    can_restore: bool
    file_size: int
    reason: str  # Why it was moved

class SafeFileRecycling:
    """
    Safe file recycling system with easy undo
    Files are moved to a recycling directory before final organization
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home()
        self.recycling_dir = self.base_dir / ".ai_organizer_recycling"
        self.metadata_file = self.recycling_dir / "recycling_log.db"
        
        # Create recycling directory
        self.recycling_dir.mkdir(exist_ok=True)
        
        # ADHD-friendly settings
        self.auto_cleanup_days = 7  # Auto-delete after 7 days
        self.max_recycled_files = 500  # Prevent accumulation
        self.show_progress = True
        
        self._init_database()
    
    def _init_database(self):
        """Initialize recycling database"""
        with sqlite3.connect(self.metadata_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recycled_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path TEXT NOT NULL,
                    recycled_path TEXT NOT NULL,
                    destination_path TEXT NOT NULL,
                    recycled_time TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    can_restore BOOLEAN NOT NULL,
                    file_size INTEGER NOT NULL,
                    reason TEXT,
                    restored BOOLEAN DEFAULT FALSE,
                    auto_cleanup_eligible BOOLEAN DEFAULT TRUE
                )
            """)
            conn.commit()
    
    def recycle_file(self, file_path: Path, destination_path: Path, 
                    operation_type: str = "organize", reason: str = "") -> Optional[Path]:
        """
        Move file to recycling directory instead of direct organization
        Returns path to recycled file or None if failed
        """
        
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return None
        
        try:
            # Create unique recycled filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recycled_name = f"{file_path.stem}_{timestamp}_{file_path.suffix.lstrip('.')}"
            if not file_path.suffix:
                recycled_name = f"{file_path.name}_{timestamp}"
            
            recycled_path = self.recycling_dir / recycled_name
            
            # Ensure unique name
            counter = 1
            original_recycled = recycled_path
            while recycled_path.exists():
                recycled_path = original_recycled.with_name(f"{original_recycled.stem}_{counter}{original_recycled.suffix}")
                counter += 1
            
            # Move file to recycling
            shutil.move(str(file_path), str(recycled_path))
            
            # Log the recycling
            recycled_file = RecycledFile(
                original_path=str(file_path),
                recycled_path=str(recycled_path),
                destination_path=str(destination_path),
                recycled_time=datetime.now().isoformat(),
                operation_type=operation_type,
                can_restore=True,
                file_size=recycled_path.stat().st_size,
                reason=reason
            )
            
            self._log_recycled_file(recycled_file)
            
            if self.show_progress:
                print(f"♻️  Recycled: {file_path.name} → {recycled_path.name}")
                print(f"   Can restore with: python safe_file_recycling.py --restore {recycled_path.name}")
            
            return recycled_path
        
        except Exception as e:
            print(f"❌ Failed to recycle {file_path.name}: {e}")
            return None
    
    def _log_recycled_file(self, recycled_file: RecycledFile):
        """Log recycled file to database"""
        with sqlite3.connect(self.metadata_file) as conn:
            conn.execute("""
                INSERT INTO recycled_files 
                (original_path, recycled_path, destination_path, recycled_time, 
                 operation_type, can_restore, file_size, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recycled_file.original_path,
                recycled_file.recycled_path, 
                recycled_file.destination_path,
                recycled_file.recycled_time,
                recycled_file.operation_type,
                recycled_file.can_restore,
                recycled_file.file_size,
                recycled_file.reason
            ))
            conn.commit()
    
    def list_recycled_files(self, limit: int = 50) -> List[Dict]:
        """List recently recycled files"""
        with sqlite3.connect(self.metadata_file) as conn:
            cursor = conn.execute("""
                SELECT * FROM recycled_files 
                WHERE restored = FALSE AND can_restore = TRUE
                ORDER BY recycled_time DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def restore_file(self, recycled_name: str) -> bool:
        """Restore a recycled file to its original location"""
        
        recycled_path = self.recycling_dir / recycled_name
        if not recycled_path.exists():
            print(f"❌ Recycled file not found: {recycled_name}")
            return False
        
        # Find in database
        with sqlite3.connect(self.metadata_file) as conn:
            cursor = conn.execute("""
                SELECT * FROM recycled_files 
                WHERE recycled_path = ? AND restored = FALSE
            """, (str(recycled_path),))
            
            record = cursor.fetchone()
            if not record:
                print(f"❌ No restore record found for: {recycled_name}")
                return False
            
            columns = [description[0] for description in cursor.description]
            file_record = dict(zip(columns, record))
        
        original_path = Path(file_record['original_path'])
        
        try:
            # Ensure parent directory exists
            original_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle name conflicts
            restore_path = original_path
            if restore_path.exists():
                # Add suffix to avoid overwriting
                counter = 1
                while restore_path.exists():
                    restore_path = original_path.with_name(
                        f"{original_path.stem}_restored_{counter}{original_path.suffix}"
                    )
                    counter += 1
                print(f"⚠️  Original location occupied, restoring as: {restore_path.name}")
            
            # Move file back
            shutil.move(str(recycled_path), str(restore_path))
            
            # Mark as restored
            with sqlite3.connect(self.metadata_file) as conn:
                conn.execute("""
                    UPDATE recycled_files 
                    SET restored = TRUE 
                    WHERE recycled_path = ?
                """, (str(recycled_path),))
                conn.commit()
            
            print(f"✅ Restored: {recycled_name} → {restore_path}")
            return True
        
        except Exception as e:
            print(f"❌ Failed to restore {recycled_name}: {e}")
            return False
    
    def complete_organization(self, recycled_name: str) -> bool:
        """Complete the organization by moving recycled file to its intended destination"""
        
        recycled_path = self.recycling_dir / recycled_name
        if not recycled_path.exists():
            print(f"❌ Recycled file not found: {recycled_name}")
            return False
        
        # Find intended destination
        with sqlite3.connect(self.metadata_file) as conn:
            cursor = conn.execute("""
                SELECT destination_path FROM recycled_files 
                WHERE recycled_path = ? AND restored = FALSE
            """, (str(recycled_path),))
            
            result = cursor.fetchone()
            if not result:
                print(f"❌ No destination found for: {recycled_name}")
                return False
            
            destination_path = Path(result[0])
        
        try:
            # Ensure destination directory exists
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle name conflicts
            final_path = destination_path
            if final_path.exists():
                counter = 1
                while final_path.exists():
                    final_path = destination_path.with_name(
                        f"{destination_path.stem}_{counter}{destination_path.suffix}"
                    )
                    counter += 1
                print(f"⚠️  Destination occupied, saving as: {final_path.name}")
            
            # Move to final destination
            shutil.move(str(recycled_path), str(final_path))
            
            # Mark as completed
            with sqlite3.connect(self.metadata_file) as conn:
                conn.execute("""
                    UPDATE recycled_files 
                    SET restored = TRUE, can_restore = FALSE 
                    WHERE recycled_path = ?
                """, (str(recycled_path),))
                conn.commit()
            
            print(f"✅ Organized: {recycled_name} → {final_path}")
            return True
        
        except Exception as e:
            print(f"❌ Failed to complete organization for {recycled_name}: {e}")
            return False
    
    def auto_cleanup_old_files(self):
        """Automatically clean up old recycled files"""
        cutoff_date = datetime.now() - timedelta(days=self.auto_cleanup_days)
        
        with sqlite3.connect(self.metadata_file) as conn:
            cursor = conn.execute("""
                SELECT recycled_path FROM recycled_files 
                WHERE recycled_time < ? AND auto_cleanup_eligible = TRUE AND restored = FALSE
            """, (cutoff_date.isoformat(),))
            
            old_files = [row[0] for row in cursor.fetchall()]
        
        cleaned_count = 0
        for file_path_str in old_files:
            file_path = Path(file_path_str)
            if file_path.exists():
                try:
                    file_path.unlink()
                    cleaned_count += 1
                    
                    # Mark as cleaned
                    with sqlite3.connect(self.metadata_file) as conn:
                        conn.execute("""
                            UPDATE recycled_files 
                            SET restored = TRUE, can_restore = FALSE 
                            WHERE recycled_path = ?
                        """, (file_path_str,))
                        conn.commit()
                
                except Exception as e:
                    print(f"⚠️  Failed to cleanup {file_path.name}: {e}")
        
        if cleaned_count > 0:
            print(f"🧹 Auto-cleaned {cleaned_count} old recycled files")
        
        return cleaned_count
    
    def show_status(self):
        """Show recycling status"""
        recycled_files = self.list_recycled_files(100)
        
        print(f"♻️  FILE RECYCLING STATUS")
        print(f"=" * 50)
        print(f"📂 Recycling directory: {self.recycling_dir}")
        print(f"📄 Currently recycled: {len(recycled_files)} files")
        
        if recycled_files:
            total_size = sum(f['file_size'] for f in recycled_files)
            print(f"💾 Total size: {total_size / (1024**2):.1f} MB")
            
            print(f"\n📋 Recent files:")
            for file_record in recycled_files[:10]:
                recycled_time = datetime.fromisoformat(file_record['recycled_time'])
                age = datetime.now() - recycled_time
                
                print(f"   {Path(file_record['recycled_path']).name}")
                print(f"     From: {file_record['original_path']}")
                print(f"     Age: {age.days} days, {age.seconds // 3600} hours")
        
        print(f"\n💡 Commands:")
        print(f"   --list: Show all recycled files")
        print(f"   --restore <filename>: Restore file to original location") 
        print(f"   --complete <filename>: Complete organization to intended destination")
        print(f"   --cleanup: Remove files older than {self.auto_cleanup_days} days")


def main():
    """Interactive recycling management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Safe File Recycling System")
    parser.add_argument('--list', action='store_true', help='List recycled files')
    parser.add_argument('--restore', help='Restore specific file')
    parser.add_argument('--complete', help='Complete organization for specific file')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old files')
    parser.add_argument('--status', action='store_true', help='Show recycling status')
    
    args = parser.parse_args()
    
    recycling = SafeFileRecycling()
    
    if args.list:
        recycled_files = recycling.list_recycled_files(50)
        if not recycled_files:
            print("✅ No files currently in recycling")
        else:
            print(f"📋 {len(recycled_files)} files in recycling:")
            for file_record in recycled_files:
                name = Path(file_record['recycled_path']).name
                print(f"   {name} ({file_record['operation_type']}) - {file_record['reason']}")
    
    elif args.restore:
        recycling.restore_file(args.restore)
    
    elif args.complete:
        recycling.complete_organization(args.complete)
    
    elif args.cleanup:
        recycling.auto_cleanup_old_files()
    
    elif args.status or len(sys.argv) == 1:
        recycling.show_status()


if __name__ == "__main__":
    main()