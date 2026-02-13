#!/usr/bin/env python3
"""
Safe File Moving with Collision Handling for AI File Organizer
Ensures files are never lost or overwritten during organization
ADHD-friendly design with clear confirmation and recovery options
"""
import re

import sys
import os
import shutil
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import sqlite3
from dataclasses import dataclass
from enum import Enum
from gdrive_integration import get_metadata_root

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

class MoveStrategy(Enum):
    """Strategies for handling file name collisions"""
    SKIP = "skip"                    # Don't move if target exists
    RENAME = "rename"                # Add suffix like "_2", "_3"
    REPLACE_IF_SAME = "replace_same" # Replace if content is identical
    REPLACE_IF_NEWER = "replace_new" # Replace if source is newer
    BACKUP_AND_REPLACE = "backup"    # Backup existing then replace
    ASK_USER = "ask"                 # Ask user what to do (interactive mode)

@dataclass
class MoveOperation:
    """Represents a single file move operation"""
    source_path: Path
    target_path: Path
    strategy: MoveStrategy
    backup_path: Optional[Path] = None
    success: bool = False
    error_message: Optional[str] = None
    skipped: bool = False
    renamed_to: Optional[Path] = None

@dataclass
class MoveResult:
    """Result of file moving operation"""
    total_operations: int
    successful_moves: int
    failed_moves: int
    skipped_moves: int
    operations: List[MoveOperation]
    backup_operations: List[Path]  # Files that were backed up

class SafeFileMover:
    """
    Handles safe file moving with collision detection and recovery
    Like AudioAI file organization but with ADHD-friendly safety features
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.backup_dir = self.base_dir / "99_BACKUP_ARCHIVE" / "file_moves"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for tracking file moves
        self.db_path = get_metadata_root() / "file_moves.db"
        self._init_moves_db()
        
        # Default strategies per interaction mode
        self.strategy_defaults = {
            'smart': MoveStrategy.ASK_USER,
            'minimal': MoveStrategy.RENAME,
            'always': MoveStrategy.ASK_USER,
            'never': MoveStrategy.REPLACE_IF_SAME
        }
    
    def _init_moves_db(self):
        """Initialize SQLite database for tracking file moves"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    move_session_id TEXT,
                    source_path TEXT,
                    target_path TEXT,
                    final_path TEXT,
                    backup_path TEXT,
                    move_strategy TEXT,
                    success BOOLEAN,
                    skipped BOOLEAN,
                    error_message TEXT,
                    file_size INTEGER,
                    source_checksum TEXT,
                    target_checksum TEXT,
                    move_date TEXT,
                    interaction_mode TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS move_sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    total_files INTEGER,
                    successful_moves INTEGER,
                    failed_moves INTEGER,
                    skipped_moves INTEGER,
                    interaction_mode TEXT,
                    dry_run BOOLEAN,
                    notes TEXT
                )
            """)
            
            conn.commit()
    
    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file for duplicate detection"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def files_are_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical content"""
        if not (file1.exists() and file2.exists()):
            return False
        
        # Quick check: different sizes = different files
        if file1.stat().st_size != file2.stat().st_size:
            return False
        
        # Checksum comparison for accuracy
        return self.calculate_file_checksum(file1) == self.calculate_file_checksum(file2)
    
    def find_available_name(self, target_path: Path, max_attempts: int = 999) -> Path:
        """Find an available filename by adding numerical suffix"""
        if not target_path.exists():
            return target_path
        
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent
        
        # Strip existing _N suffix to avoid _1_2_3_4 accumulation
        match = re.match(r"^(.+?)(?:_(\d+))?$", stem)
        if match:
            base_stem = match.group(1)
            existing_num = int(match.group(2)) if match.group(2) else 1
        else:
            base_stem = stem
            existing_num = 1
        
        # Start from the next number after existing suffix
        for i in range(existing_num + 1, max_attempts + existing_num):
            candidate = parent / f"{base_stem}_{i}{suffix}"
            if not candidate.exists():
                return candidate
        
        # If we get here, add timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return parent / f"{base_stem}_{timestamp}{suffix}"
    
    def create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file before moving/replacing"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        # Ensure backup directory structure
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def move_single_file(self, source_path: Path, target_path: Path, 
                        strategy: MoveStrategy = MoveStrategy.ASK_USER,
                        dry_run: bool = False) -> MoveOperation:
        """Move a single file with collision handling"""
        
        operation = MoveOperation(
            source_path=source_path,
            target_path=target_path,
            strategy=strategy
        )
        
        if dry_run:
            # In dry run, just simulate the operation
            if target_path.exists():
                if strategy == MoveStrategy.RENAME:
                    operation.renamed_to = self.find_available_name(target_path)
                elif strategy == MoveStrategy.SKIP:
                    operation.skipped = True
            operation.success = True
            return operation
        
        try:
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle collision if target exists
            if target_path.exists():
                operation = self._handle_collision(operation, dry_run)
                if operation.skipped:
                    return operation
                if operation.error_message:
                    return operation
            
            # Perform the actual move
            if operation.renamed_to:
                final_target = operation.renamed_to
            else:
                final_target = target_path
            
            shutil.move(str(source_path), str(final_target))
            operation.success = True
            
            # Verify move was successful
            if not final_target.exists():
                operation.success = False
                operation.error_message = "Move completed but target file not found"
            elif source_path.exists():
                operation.success = False
                operation.error_message = "Source file still exists after move"
        
        except Exception as e:
            operation.success = False
            operation.error_message = str(e)
        
        return operation
    
    def _handle_collision(self, operation: MoveOperation, dry_run: bool) -> MoveOperation:
        """Handle file name collision based on strategy"""
        
        source_path = operation.source_path
        target_path = operation.target_path
        strategy = operation.strategy
        
        if strategy == MoveStrategy.SKIP:
            operation.skipped = True
            return operation
        
        elif strategy == MoveStrategy.RENAME:
            operation.renamed_to = self.find_available_name(target_path)
            return operation
        
        elif strategy == MoveStrategy.REPLACE_IF_SAME:
            if self.files_are_identical(source_path, target_path):
                # Files are identical, can safely "move" (delete source)
                if not dry_run:
                    source_path.unlink()
                operation.success = True
                return operation
            else:
                # Files are different, rename instead
                operation.renamed_to = self.find_available_name(target_path)
                return operation
        
        elif strategy == MoveStrategy.REPLACE_IF_NEWER:
            source_mtime = source_path.stat().st_mtime
            target_mtime = target_path.stat().st_mtime
            
            if source_mtime > target_mtime:
                # Source is newer, backup target and replace
                if not dry_run:
                    operation.backup_path = self.create_backup(target_path)
                return operation
            else:
                # Target is newer or same, rename source
                operation.renamed_to = self.find_available_name(target_path)
                return operation
        
        elif strategy == MoveStrategy.BACKUP_AND_REPLACE:
            if not dry_run:
                operation.backup_path = self.create_backup(target_path)
            return operation
        
        elif strategy == MoveStrategy.ASK_USER:
            # For CLI usage, fall back to rename strategy
            # Interactive mode would ask user here
            operation.renamed_to = self.find_available_name(target_path)
            return operation
        
        else:
            # Unknown strategy, default to rename
            operation.renamed_to = self.find_available_name(target_path)
            return operation
    
    def move_multiple_files(self, file_moves: List[Tuple[Path, Path]], 
                           strategy: MoveStrategy = MoveStrategy.ASK_USER,
                           dry_run: bool = False,
                           interaction_mode: str = "smart") -> MoveResult:
        """Move multiple files with batch processing"""
        
        session_id = f"move_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 1000}"
        operations = []
        backup_operations = []
        
        print(f"🚀 Starting {'dry run' if dry_run else 'live'} file move operation")
        print(f"📊 Moving {len(file_moves)} files with strategy: {strategy.value}")
        
        for i, (source, target) in enumerate(file_moves, 1):
            print(f"\n📄 [{i}/{len(file_moves)}] {source.name}")
            print(f"   → {target}")
            
            operation = self.move_single_file(source, target, strategy, dry_run)
            operations.append(operation)
            
            if operation.backup_path:
                backup_operations.append(operation.backup_path)
            
            # Show result
            if operation.success:
                if operation.renamed_to:
                    print(f"   ✅ Moved (renamed to: {operation.renamed_to.name})")
                elif operation.skipped:
                    print(f"   ⏭️  Skipped (target exists)")
                else:
                    print(f"   ✅ Moved successfully")
            else:
                print(f"   ❌ Failed: {operation.error_message}")
            
            # Save operation to database
            if not dry_run:
                self._save_move_operation(session_id, operation, interaction_mode)
        
        # Create result summary
        result = MoveResult(
            total_operations=len(operations),
            successful_moves=sum(1 for op in operations if op.success and not op.skipped),
            failed_moves=sum(1 for op in operations if not op.success),
            skipped_moves=sum(1 for op in operations if op.skipped),
            operations=operations,
            backup_operations=backup_operations
        )
        
        # Save session summary
        if not dry_run:
            self._save_move_session(session_id, result, interaction_mode, dry_run)
        
        # Show final summary
        print(f"\n📊 Move Operation Summary:")
        print(f"   Total files: {result.total_operations}")
        print(f"   ✅ Successful: {result.successful_moves}")
        print(f"   ❌ Failed: {result.failed_moves}")
        print(f"   ⏭️  Skipped: {result.skipped_moves}")
        
        if backup_operations:
            print(f"   💾 Backups created: {len(backup_operations)}")
        
        return result
    
    def _save_move_operation(self, session_id: str, operation: MoveOperation, 
                           interaction_mode: str):
        """Save move operation to database"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO file_moves
                (move_session_id, source_path, target_path, final_path, backup_path,
                 move_strategy, success, skipped, error_message, file_size,
                 source_checksum, move_date, interaction_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                str(operation.source_path),
                str(operation.target_path),
                str(operation.renamed_to or operation.target_path),
                str(operation.backup_path) if operation.backup_path else None,
                operation.strategy.value,
                operation.success,
                operation.skipped,
                operation.error_message,
                operation.source_path.stat().st_size if operation.source_path.exists() else 0,
                self.calculate_file_checksum(operation.source_path) if operation.source_path.exists() else "",
                datetime.now().isoformat(),
                interaction_mode
            ))
            conn.commit()
    
    def _save_move_session(self, session_id: str, result: MoveResult, 
                         interaction_mode: str, dry_run: bool):
        """Save move session summary to database"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO move_sessions
                (session_id, start_time, end_time, total_files, successful_moves,
                 failed_moves, skipped_moves, interaction_mode, dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                result.total_operations,
                result.successful_moves,
                result.failed_moves,
                result.skipped_moves,
                interaction_mode,
                dry_run
            ))
            conn.commit()
    
    def list_recent_moves(self, days: int = 7) -> List[Dict]:
        """List recent file move operations"""
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM file_moves
                WHERE move_date > ?
                ORDER BY move_date DESC
                LIMIT 100
            """, (cutoff_date,))
            
            columns = [desc[0] for desc in cursor.description]
            moves = []
            
            for row in cursor.fetchall():
                move = dict(zip(columns, row))
                moves.append(move)
            
            return moves
    
    def undo_recent_moves(self, session_id: str, confirm: bool = False) -> bool:
        """Attempt to undo moves from a specific session"""
        
        if not confirm:
            print("⚠️  Use confirm=True to actually undo moves. This cannot be undone!")
            return False
        
        print(f"🔄 Attempting to undo moves from session: {session_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT source_path, target_path, final_path, backup_path, success
                FROM file_moves
                WHERE move_session_id = ? AND success = 1
                ORDER BY move_date DESC
            """, (session_id,))
            
            moves_to_undo = cursor.fetchall()
        
        if not moves_to_undo:
            print("❌ No successful moves found in that session")
            return False
        
        undone_count = 0
        failed_count = 0
        
        for source, target, final, backup, success in moves_to_undo:
            try:
                final_path = Path(final)
                original_path = Path(source)
                
                if final_path.exists():
                    # Move file back to original location
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(final_path), str(original_path))
                    undone_count += 1
                    print(f"   ✅ Restored: {original_path.name}")
                else:
                    failed_count += 1
                    print(f"   ❌ File not found: {final_path}")
                
            except Exception as e:
                failed_count += 1
                print(f"   ❌ Failed to restore {Path(source).name}: {e}")
        
        print(f"\n📊 Undo Summary:")
        print(f"   ✅ Restored: {undone_count}")
        print(f"   ❌ Failed: {failed_count}")
        
        return undone_count > 0

def test_safe_file_mover():
    """Test the safe file moving system"""
    
    print("🧪 Testing Safe File Mover")
    print("=" * 50)
    
    mover = SafeFileMover()
    
    # Create test files in a temp directory
    test_dir = Path("/tmp/file_mover_test")
    test_dir.mkdir(exist_ok=True)
    
    # Create test files
    test_files = []
    for i in range(3):
        test_file = test_dir / f"test_file_{i}.txt"
        test_file.write_text(f"This is test file {i}\nContent for testing")
        test_files.append(test_file)
    
    # Create target directory
    target_dir = test_dir / "organized"
    target_dir.mkdir(exist_ok=True)
    
    # Test file moves
    moves = [
        (test_files[0], target_dir / "moved_file_1.txt"),
        (test_files[1], target_dir / "moved_file_2.txt"),
        (test_files[2], target_dir / "moved_file_3.txt")
    ]
    
    print(f"📝 Testing dry run...")
    result = mover.move_multiple_files(
        moves, 
        strategy=MoveStrategy.RENAME,
        dry_run=True,
        interaction_mode="smart"
    )
    
    print(f"\n📝 Testing actual moves...")
    result = mover.move_multiple_files(
        moves,
        strategy=MoveStrategy.RENAME, 
        dry_run=False,
        interaction_mode="smart"
    )
    
    # Test collision handling by trying to move again
    print(f"\n📝 Testing collision handling...")
    
    # Create another file with same name
    collision_file = test_dir / "collision_test.txt"
    collision_file.write_text("This will collide")
    
    collision_moves = [(collision_file, target_dir / "moved_file_1.txt")]
    
    result = mover.move_multiple_files(
        collision_moves,
        strategy=MoveStrategy.RENAME,
        dry_run=False,
        interaction_mode="smart"
    )
    
    # List recent moves
    print(f"\n📊 Recent moves:")
    recent = mover.list_recent_moves(1)
    for move in recent[:5]:
        print(f"   {Path(move['source_path']).name} → {Path(move['final_path']).name}")
    
    # Clean up
    shutil.rmtree(test_dir)
    print(f"\n✅ Test completed successfully!")

if __name__ == "__main__":
    test_safe_file_mover()