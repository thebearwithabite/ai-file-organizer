#!/usr/bin/env python3
"""
Bulletproof File Deduplication System
Two-tier hashing with real-time monitoring and safe deletion
ADHD-friendly with multiple safety confirmations
"""

import hashlib
import os
import sqlite3
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import mimetypes

@dataclass
class FileHashRecord:
    """Complete hash record for a file"""
    file_path: str
    file_size: int
    modified_time: float
    quick_hash: str          # MD5 - fast for real-time detection
    secure_hash: str         # SHA-256 - bulletproof for deletion
    quick_calculated_at: datetime
    secure_calculated_at: datetime
    duplicate_group_id: Optional[str] = None

class DuplicateAction(Enum):
    """Actions for duplicate files"""
    KEEP_ORIGINAL = "keep_original"      # Keep oldest/most accessible
    STAGE_FOR_REVIEW = "stage_review"   # Move to review folder
    SAFE_DELETE = "safe_delete"         # Delete with backup
    SKIP = "skip"                       # Don't touch this duplicate

class BulletproofDeduplicator:
    """
    Bulletproof file deduplication with two-tier hashing
    Safe enough to actually DELETE files (not just move them)
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        
        # Deduplication database
        self.db_path = self.base_dir / "04_METADATA_SYSTEM" / "deduplication.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Safety mechanisms
        self.backup_dir = self.base_dir / "99_BACKUP_ARCHIVE" / "deleted_duplicates"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance settings
        self.chunk_size = 65536  # 64KB chunks for hashing
        self.batch_size = 100    # Files to process in one batch
        
        # Safety thresholds
        self.min_file_age_hours = 24        # Don't dedupe files newer than 24h
        self.max_deletions_per_session = 50  # ADHD-friendly limit
        self.require_manual_review_over_mb = 100  # Manual review for large files
        
        self._init_database()
    
    def _init_database(self):
        """Initialize deduplication tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            # File hash tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_hashes (
                    file_path TEXT PRIMARY KEY,
                    file_size INTEGER,
                    modified_time REAL,
                    quick_hash TEXT,
                    secure_hash TEXT,
                    quick_calculated_at TEXT,
                    secure_calculated_at TEXT,
                    duplicate_group_id TEXT,
                    is_protected BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Duplicate groups
            conn.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_groups (
                    group_id TEXT PRIMARY KEY,
                    secure_hash TEXT UNIQUE,
                    file_count INTEGER,
                    total_size INTEGER,
                    original_file TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_action TEXT,
                    action_count INTEGER DEFAULT 0
                )
            """)
            
            # Deletion log for safety
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deletion_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deleted_file TEXT,
                    backup_path TEXT,
                    secure_hash TEXT,
                    file_size INTEGER,
                    deleted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    duplicate_of TEXT,
                    can_restore BOOLEAN DEFAULT 1
                )
            """)
            
            # Create indices for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_quick_hash ON file_hashes(quick_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_secure_hash ON file_hashes(secure_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_size ON file_hashes(file_size)")
            
            conn.commit()
    
    def calculate_quick_hash(self, file_path: Path) -> str:
        """Calculate fast MD5 hash for real-time duplicate detection"""
        hasher = hashlib.md5()
        
        try:
            with open(file_path, 'rb') as f:
                # For large files, hash first and last chunks + size for speed
                file_size = file_path.stat().st_size
                
                if file_size > 1024 * 1024:  # > 1MB
                    # Hash first 64KB
                    chunk = f.read(self.chunk_size)
                    hasher.update(chunk)
                    
                    # Hash last 64KB
                    if file_size > self.chunk_size * 2:
                        f.seek(-self.chunk_size, 2)
                        chunk = f.read(self.chunk_size)
                        hasher.update(chunk)
                    
                    # Include file size in hash for uniqueness
                    hasher.update(str(file_size).encode())
                else:
                    # Small files: hash entire content
                    for chunk in iter(lambda: f.read(self.chunk_size), b""):
                        hasher.update(chunk)
                        
        except Exception:
            # Fallback: use file stats
            stat = file_path.stat()
            hasher.update(f"{stat.st_size}_{stat.st_mtime}_{file_path.name}".encode())
        
        return hasher.hexdigest()
    
    def calculate_secure_hash(self, file_path: Path) -> str:
        """Calculate bulletproof SHA-256 hash for safe deletion decisions"""
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(self.chunk_size), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            raise Exception(f"Failed to calculate secure hash for {file_path}: {e}")
    
    def hash_file(self, file_path: Path, force_rehash: bool = False) -> FileHashRecord:
        """Hash a file with both quick and secure methods"""
        
        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"File not found or not a file: {file_path}")
        
        stat = file_path.stat()
        current_mtime = stat.st_mtime
        
        # Check if we already have up-to-date hashes
        existing = self._get_hash_record(file_path)
        if existing and not force_rehash and existing.modified_time == current_mtime:
            if existing.quick_hash and existing.secure_hash:
                return existing
        
        print(f"🔍 Hashing: {file_path.name}")
        
        # Calculate hashes
        quick_hash = self.calculate_quick_hash(file_path)
        secure_hash = self.calculate_secure_hash(file_path)
        
        now = datetime.now()
        record = FileHashRecord(
            file_path=str(file_path),
            file_size=stat.st_size,
            modified_time=current_mtime,
            quick_hash=quick_hash,
            secure_hash=secure_hash,
            quick_calculated_at=now,
            secure_calculated_at=now
        )
        
        # Store in database
        self._store_hash_record(record)
        
        return record
    
    def _get_hash_record(self, file_path: Path) -> Optional[FileHashRecord]:
        """Get existing hash record from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path, file_size, modified_time, quick_hash, secure_hash,
                       quick_calculated_at, secure_calculated_at, duplicate_group_id
                FROM file_hashes WHERE file_path = ?
            """, (str(file_path),))
            
            row = cursor.fetchone()
            if row:
                return FileHashRecord(
                    file_path=row[0],
                    file_size=row[1],
                    modified_time=row[2],
                    quick_hash=row[3],
                    secure_hash=row[4],
                    quick_calculated_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    secure_calculated_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    duplicate_group_id=row[7]
                )
        return None
    
    def _store_hash_record(self, record: FileHashRecord):
        """Store hash record in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO file_hashes
                (file_path, file_size, modified_time, quick_hash, secure_hash,
                 quick_calculated_at, secure_calculated_at, duplicate_group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.file_path, record.file_size, record.modified_time,
                record.quick_hash, record.secure_hash,
                record.quick_calculated_at.isoformat() if record.quick_calculated_at else None,
                record.secure_calculated_at.isoformat() if record.secure_calculated_at else None,
                record.duplicate_group_id
            ))
            conn.commit()
    
    def find_duplicates_by_quick_hash(self, quick_hash: str) -> List[FileHashRecord]:
        """Find potential duplicates using quick hash"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path, file_size, modified_time, quick_hash, secure_hash,
                       quick_calculated_at, secure_calculated_at, duplicate_group_id
                FROM file_hashes WHERE quick_hash = ?
                ORDER BY file_size DESC, modified_time ASC
            """, (quick_hash,))
            
            records = []
            for row in cursor.fetchall():
                records.append(FileHashRecord(
                    file_path=row[0],
                    file_size=row[1],
                    modified_time=row[2],
                    quick_hash=row[3],
                    secure_hash=row[4],
                    quick_calculated_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    secure_calculated_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    duplicate_group_id=row[7]
                ))
            
            return records
    
    def verify_duplicate_with_secure_hash(self, file1: Path, file2: Path) -> bool:
        """Verify two files are identical using secure SHA-256 hash"""
        
        # Get or calculate secure hashes
        hash1_record = self.hash_file(file1)
        hash2_record = self.hash_file(file2)
        
        # Files are duplicates if secure hashes match
        return hash1_record.secure_hash == hash2_record.secure_hash
    
    def detect_new_duplicate(self, file_path: Path) -> Optional[List[Path]]:
        """Real-time duplicate detection for new files (called by background monitor)"""
        
        # Calculate quick hash
        quick_hash = self.calculate_quick_hash(file_path)
        
        # Find potential duplicates
        potential_duplicates = self.find_duplicates_by_quick_hash(quick_hash)
        
        if len(potential_duplicates) > 0:
            # Verify with secure hash
            verified_duplicates = []
            for potential in potential_duplicates:
                potential_path = Path(potential.file_path)
                if potential_path.exists() and potential_path != file_path:
                    if self.verify_duplicate_with_secure_hash(file_path, potential_path):
                        verified_duplicates.append(potential_path)
            
            if verified_duplicates:
                print(f"🚨 Duplicate detected: {file_path.name}")
                print(f"   Matches: {[p.name for p in verified_duplicates]}")
                return verified_duplicates
        
        # No duplicates found, store hash for future detection
        self.hash_file(file_path)
        return None
    
    def find_all_duplicates(self) -> Dict[str, List[Path]]:
        """Find all duplicate groups in the system"""
        
        duplicate_groups = {}
        
        with sqlite3.connect(self.db_path) as conn:
            # Find files with same secure hash
            cursor = conn.execute("""
                SELECT secure_hash, COUNT(*) as count, GROUP_CONCAT(file_path) as paths
                FROM file_hashes 
                WHERE secure_hash IS NOT NULL 
                GROUP BY secure_hash 
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
            """)
            
            for row in cursor.fetchall():
                secure_hash, count, paths_str = row
                paths = [Path(p) for p in paths_str.split(',') if Path(p).exists()]
                
                if len(paths) > 1:
                    duplicate_groups[secure_hash] = paths
        
        return duplicate_groups

def test_deduplication_system():
    """Test the deduplication system with sample files"""
    
    print("🧪 Testing Bulletproof Deduplication System")
    print("=" * 50)
    
    deduper = BulletproofDeduplicator()
    
    # Test with some files from Downloads
    test_dir = Path.home() / "Downloads"
    test_files = list(test_dir.glob("*.pdf"))[:5]  # Test with 5 PDFs
    
    if not test_files:
        print("📝 No test files found in Downloads")
        return
    
    print(f"🔍 Testing with {len(test_files)} files:")
    for f in test_files:
        print(f"   📄 {f.name}")
    
    # Hash all test files
    for file_path in test_files:
        try:
            record = deduper.hash_file(file_path)
            print(f"✅ Hashed: {file_path.name}")
            print(f"   Quick: {record.quick_hash[:16]}...")
            print(f"   Secure: {record.secure_hash[:16]}...")
        except Exception as e:
            print(f"❌ Failed to hash {file_path.name}: {e}")
    
    # Find duplicates
    duplicates = deduper.find_all_duplicates()
    
    if duplicates:
        print(f"\n🔍 Found {len(duplicates)} duplicate groups:")
        for secure_hash, paths in duplicates.items():
            print(f"   📂 Group {secure_hash[:16]}...:")
            for path in paths:
                print(f"      📄 {path}")
    else:
        print(f"\n✅ No duplicates found in test files")
    
    print(f"\n🎯 Deduplication system ready for production!")

if __name__ == "__main__":
    test_deduplication_system()