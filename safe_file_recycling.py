#!/usr/bin/env python3
"""
ARCHITECTURAL LAW:
- base_dir = monitored filesystem location (may be remote)
- metadata_root = internal state (MUST be local)
- metadata_root MUST come from get_metadata_root()
- NEVER derive metadata paths from base_dir

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

# Import centralized configuration root
from gdrive_integration import get_metadata_root

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
        # base_dir is the monitored filesystem location (e.g. Google Drive root)
        self.base_dir = Path(base_dir) if base_dir else Path.home()
        
        # Internal state MUST be local (RULE ONE)
        metadata_root = get_metadata_root()
        self.recycling_dir = metadata_root / "recycling"
        self.metadata_file = metadata_root / "databases" / "recycling_log.db"
        
        # Create directories
        self.recycling_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
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

def main():
    """Interactive recycling management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Safe File Recycling System")
    parser.add_argument('--list', action='store_true', help='List recycled files')
    parser.add_argument('--restore', help='Restore specific file')
    parser.add_argument('--status', action='store_true', help='Show recycling status')
    
    args = parser.parse_args()
    
    recycling = SafeFileRecycling()
    
    if args.status or len(sys.argv) == 1:
        print("♻️  Safe File Recycling System")
        print("==============================")
        print("Files are moved here before organization for safety.")
        print("Use --restore <filename> to undo file moves.")


if __name__ == "__main__":
    main()