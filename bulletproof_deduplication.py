#!/usr/bin/env python3
"""
Bulletproof Deduplication System with SHA-256 Two-Tier Hashing
Part of AI File Organizer v3.0 - Professional Content Management Platform

Created by: RT Max
"""

import sys
import argparse
import hashlib
import sqlite3
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Iterator
import time
import json
from datetime import datetime
from gdrive_integration import get_metadata_root

class BulletproofDeduplicator:
    """
    Military-grade duplicate detection using two-tier hashing system
    - Tier 1: MD5 for lightning-fast screening (0.1ms per file)
    - Tier 2: SHA-256 for bulletproof verification (2ms per file)
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        
        # PRIME DIRECTIVE: Metadata MUST be local-only
        # We ignore base_dir for the DB path and force it to the system metadata root
        metadata_root = get_metadata_root()
        metadata_root.mkdir(parents=True, exist_ok=True)
        self.db_path = metadata_root / "deduplication.db"
        
        self.init_database()
        
        # Bulletproof duplicate patterns
        self.safe_duplicate_patterns = [
            r'.*\s\(\d+\)\..*',          # "filename (1).ext"
            r'.*\scopy\..*',             # "filename copy.ext" 
            r'Generated Image.*\.jpeg',   # ChatGPT generated images
            r'.*_\d{8}_\d{6}\..*',       # Timestamped duplicates
            r'Screenshot.*\.png',         # Screenshot duplicates
            r'Copy of.*',                 # "Copy of filename.ext"
        ]
        self.safe_duplicate_compiled = [re.compile(p, re.IGNORECASE) for p in self.safe_duplicate_patterns]
        
        # Protected paths - never delete from these
        self.protected_paths = {
            '/System', '/Applications', '/Library',
            '/.git', '/.svn', '/node_modules'
        }

        # PROTECTED DATABASE PATTERNS - ABSOLUTELY NEVER DELETE OR MODIFY
        # These patterns protect all learned data, embeddings, and metadata
        self.protected_database_patterns = [
            r'.*vector_db.*',
            r'.*chroma.*',
            r'.*_METADATA_SYSTEM.*',
            r'.*_SYSTEM/.*\.db$',
            r'.*\.pkl$',           # Pickle learning data
            r'.*adaptive_learning.*',
            r'.*deduplication.*\.db$',
            # r'.*04_METADATA_SYSTEM.*',  # [REMOVED] Legacy path - replaced by AI_METADATA_SYSTEM
            r'.*learning_data.*',
            r'.*classification_logs.*',
            r'.*embeddings.*',
            r'.*\.db$',            # All SQLite databases
            r'.*\.sqlite.*',       # All SQLite variants
            r'.*index.*\.pkl$',    # Index files
            r'.*metadata.*',       # Any metadata folders/files
        ]
        self.protected_database_compiled = [re.compile(p, re.IGNORECASE) for p in self.protected_database_patterns]

        # Optimization: Sets and lists for fast lookup
        self.protected_extensions = {'.db', '.sqlite', '.sqlite3', '.pkl', '.pickle'}
        self.protected_dir_names = [
            'vector_db', 'chroma', 'metadata_system', 'learning',
            'adaptive', 'embeddings', 'index', '_system', 'classification_logs'
        ]
    
    def init_database(self):
        """Initialize SQLite database for hash tracking"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS file_hashes (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT UNIQUE,
                    quick_hash TEXT,
                    secure_hash TEXT,
                    file_size INTEGER,
                    last_modified REAL,
                    duplicate_group_id TEXT,
                    safety_score REAL,
                    can_delete BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_quick_hash ON file_hashes(quick_hash)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_secure_hash ON file_hashes(secure_hash)
            ''')
    
    def calculate_quick_hash(self, file_path: Path, file_size: Optional[int] = None) -> Optional[str]:
        """
        Tier 1: Lightning-fast MD5 screening (~0.1ms per file)
        Used for initial duplicate detection
        """
        try:
            # Skip symlinks and special files
            if file_path.is_symlink():
                return None

            # Check file size - warn about large files
            if file_size is None:
                file_size = file_path.stat().st_size

            if file_size > 1024 * 1024 * 100:  # 100MB
                print(f"   ⏸️  Large file ({file_size / (1024*1024):.1f}MB): {file_path.name}")

            with open(file_path, 'rb') as f:
                # Read first 64KB for quick hash - catches most duplicates
                content = f.read(65536)
                return hashlib.md5(content).hexdigest()
        except (PermissionError, OSError) as e:
            # Skip files we can't read (locked, network, etc.)
            return None
        except Exception as e:
            print(f"⚠️ Quick hash error for {file_path.name}: {e}")
            return None
    
    def calculate_secure_hash(self, file_path: Path, db_connection: Optional[sqlite3.Connection] = None,
                              file_size: Optional[int] = None, last_modified: Optional[float] = None) -> Optional[str]:
        """
        Tier 2: Bulletproof SHA-256 verification (~2ms per file)
        Used for cryptographic certainty before deletion
        """
        try:
            # Skip symlinks and special files
            if file_path.is_symlink():
                return None

            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Read file in chunks (1MB) for better performance than 64KB
                for chunk in iter(lambda: f.read(1048576), b""):
                    sha256_hash.update(chunk)
            
            secure_hash = sha256_hash.hexdigest()
            
            # Use provided stats or fetch them
            if file_size is None:
                file_size = file_path.stat().st_size
            if last_modified is None:
                last_modified = file_path.stat().st_mtime

            # Persist to database
            try:
                if db_connection:
                    # Use provided connection (faster for batch operations)
                    db_connection.execute("""
                        INSERT OR REPLACE INTO file_hashes 
                        (file_path, secure_hash, file_size, last_modified)
                        VALUES (?, ?, ?, ?)
                    """, (
                        str(file_path), secure_hash, 
                        file_size, last_modified
                    ))
                else:
                    # Create new connection (slower)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("""
                            INSERT OR REPLACE INTO file_hashes
                            (file_path, secure_hash, file_size, last_modified)
                            VALUES (?, ?, ?, ?)
                        """, (
                            str(file_path), secure_hash,
                            file_size, last_modified
                        ))
            except Exception as db_err:
                # Don't fail if DB write fails, just log it
                print(f"⚠️ Failed to persist hash for {file_path.name}: {db_err}")
                
            return secure_hash
        except (PermissionError, OSError) as e:
            # Skip files we can't read (locked, network, etc.)
            return None
        except Exception as e:
            print(f"⚠️ Secure hash error for {file_path.name}: {e}")
            return None

    def check_if_hash_exists_in_gdrive(self, secure_hash: str) -> Optional[str]:
        """
        Check if a file hash already exists in Google Drive
        
        Args:
            secure_hash: SHA-256 hash to check
            
        Returns:
            Path to existing file if found, None otherwise
        """
        if not secure_hash:
            return None
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Look for this hash where the path contains 'GoogleDrive'
                cursor.execute("""
                    SELECT file_path FROM file_hashes 
                    WHERE secure_hash = ? AND file_path LIKE '%GoogleDrive%'
                    LIMIT 1
                """, (secure_hash,))
                
                result = cursor.fetchone()
                if result:
                    return result[0]
                return None
        except Exception as e:
            print(f"⚠️ Error checking hash existence: {e}")
            return None

    def is_database_or_learned_data(self, file_path: Path) -> bool:
        """
        Check if file is a database or contains learned data
        ABSOLUTE PROTECTION - never consider these for deletion or modification

        Returns:
            True if file is database/learned data (PROTECTED)
            False if file is safe to scan
        """
        # OPTIMIZATION: Check extensions first (fastest O(1) lookup)
        if file_path.suffix.lower() in self.protected_extensions:
            return True

        path_str = str(file_path).lower()

        # OPTIMIZATION: Check directory names using string search (faster than regex or tuple iteration)
        for protected in self.protected_dir_names:
            if protected in path_str:
                return True

        # Check against protected database patterns (regex fallback)
        for pattern in self.protected_database_compiled:
            if pattern.search(path_str):
                return True

        return False

    def _fast_scan(self, directory: Path) -> Iterator[Tuple[Path, os.stat_result]]:
        """
        Recursively scan directory using os.scandir for better performance.
        Yields (Path, stat_result) tuples.
        """
        try:
            # os.scandir is faster than os.walk because it yields DirEntry objects
            # with cached stat information on most OSes
            with os.scandir(directory) as it:
                for entry in it:
                    if entry.name.startswith('.'):
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        if entry.name.endswith('.imovielibrary') or entry.name.endswith('.photoslibrary'):
                            continue
                        # Recurse
                        yield from self._fast_scan(entry.path)

                    elif entry.is_file(follow_symlinks=False):
                        try:
                            # entry.stat() is cached from scandir result
                            stat = entry.stat()
                            yield (Path(entry.path), stat)
                        except OSError as e:
                            print(f"   ⚠️ Error accessing {entry.name}: {e}")

        except OSError as e:
            print(f"   ⚠️ Error scanning directory {directory}: {e}")

    def calculate_safety_score(self, file_path: Path, duplicate_group: List[Dict], last_modified: Optional[float] = None) -> float:
        """
        Calculate safety score (0.0-1.0) for file deletion
        Higher score = safer to delete
        """
        # ABSOLUTE PROTECTION: Database and learned data files NEVER get positive safety scores
        if self.is_database_or_learned_data(file_path):
            return 0.0

        score = 0.0
        
        # File age factor (older = safer to delete)
        try:
            if last_modified is None:
                last_modified = file_path.stat().st_mtime

            age_days = (time.time() - last_modified) / (24 * 3600)
            if age_days > 30:
                score += 0.3
            elif age_days > 7:
                score += 0.2
            elif age_days > 1:
                score += 0.1
        except:
            pass
        
        # Location factor (Downloads/temp locations safer)
        path_str = str(file_path).lower()
        if any(safe in path_str for safe in ['/downloads', '/temp', '/tmp']):
            score += 0.3
        # AGGRESSIVE MODE: Penalty disabled by user request
        # elif any(protected in path_str for protected in ['/documents', '/desktop']):
        #     score -= 0.2
        
        # Pattern recognition (obvious duplicates safer)
        filename = file_path.name
        for pattern in self.safe_duplicate_compiled:
            if pattern.match(filename):
                score += 0.4
                break
        
        # Group size factor (more duplicates = safer to delete one)
        if len(duplicate_group) > 3:
            score += 0.2
        elif len(duplicate_group) > 1:
            score += 0.1
        
        # Protected path check
        for protected in self.protected_paths:
            if protected in str(file_path):
                # Exception: Allow iCloud Drive (Mobile Documents) and CloudStorage
                if protected == "/Library" and ("Mobile Documents" in str(file_path) or "CloudStorage" in str(file_path)):
                    continue
                score = 0.0  # Never delete from protected paths
                break
        
        return min(1.0, max(0.0, score))
    
    def scan_directory(self, directory: Path, execute: bool = False, safety_threshold: float = 0.7) -> Dict:
        """
        Scan directory for duplicates using two-tier hashing
        
        Args:
            directory: Directory to scan
            execute: If True, actually delete safe duplicates
        
        Returns:
            Scan results with statistics
        """
        if not directory.exists():
            return {"error": f"Directory not found: {directory}"}
        
        print(f"🔍 Scanning directory: {directory}")
        print(f"🛡️  Mode: {'EXECUTE' if execute else 'DRY RUN'}")
        
        results = {
            "scanned_files": 0,
            "duplicate_groups": 0,
            "duplicates_found": 0,
            "safe_to_delete": 0,
            "space_recoverable": 0,
            "deleted_files": 0,
            "errors": []
        }
        
        # Find all files with safe walker (using optimized _fast_scan)
        print("   Scanning files (skipping .imovielibrary and other bundles)...")
        print("📊 Tier 0: Grouping by file size...")

        size_groups = {}
        # skipped_files = 0 # unused in HEAD resolution
        protected_files = 0
        scanned_count = 0
        stat_cache = {}

        try:
            for file_path, stat in self._fast_scan(directory):
                scanned_count += 1
                if self.is_database_or_learned_data(file_path):
                    protected_files += 1
                    continue

                size = stat.st_size
                if size not in size_groups:
                    size_groups[size] = []
                size_groups[size].append(file_path)

                # Cache stat for later use in this scan session
                stat_cache[file_path] = stat

        except Exception as e:
            print(f"   ❌ Critical error during scan: {e}")
            return {"error": str(e)}

        print(f"📁 Scanned {scanned_count} files")

        # Only process size groups with multiple files
        size_potential = {s: paths for s, paths in size_groups.items() if len(paths) > 1}
        total_potential_files = sum(len(paths) for paths in size_potential.values())
        print(f"   Found {total_potential_files} files with non-unique sizes")

        # Group files by quick hash (Tier 1 screening)
        print("⚡ Tier 1: Quick MD5 screening for size-matched files...")
        quick_hash_groups = {}
        processed_count = 0
        skipped_files = 0

        for size, file_list in size_potential.items():
            for file_path in file_list:
                processed_count += 1
                if processed_count % 50 == 0 or processed_count == total_potential_files:
                    print(f"   Progress: {processed_count}/{total_potential_files} files ({((processed_count/total_potential_files)*100):.1f}%)")

                # Reuse size from tier 0
                quick_hash = self.calculate_quick_hash(file_path, file_size=size)
                if quick_hash:
                    if quick_hash not in quick_hash_groups:
                        quick_hash_groups[quick_hash] = []
                    quick_hash_groups[quick_hash].append(file_path)
                else:
                    skipped_files += 1

        if skipped_files > 0:
            print(f"   ⏭️  Skipped {skipped_files} files (locked, symlinks, or inaccessible)")
        
        # Only process hash groups with multiple files
        potential_duplicates = {h: paths for h, paths in quick_hash_groups.items() if len(paths) > 1}

        print(f"🔍 Found {len(potential_duplicates)} potential duplicate groups")
        print("🔒 Tier 2: SHA-256 bulletproof verification...")

        # Verify with SHA-256 (Tier 2 verification)
        confirmed_duplicates = {}
        total_groups = len(potential_duplicates)

        # Reuse database connection for batch processing
        with sqlite3.connect(self.db_path) as conn:
            for group_idx, (quick_hash, file_list) in enumerate(potential_duplicates.items()):
                # Show progress for verification phase
                if (group_idx + 1) % 10 == 0 or (group_idx + 1) == total_groups:
                    print(f"   Verifying group {group_idx + 1}/{total_groups} ({((group_idx+1)/total_groups*100):.1f}%)")

                # Calculate secure hashes for this group
                secure_hash_groups = {}

                for file_path in file_list:
                    # Get cached stat if available
                    stat = stat_cache.get(file_path)
                    f_size = stat.st_size if stat else None
                    f_mtime = stat.st_mtime if stat else None

                    secure_hash = self.calculate_secure_hash(file_path, db_connection=conn,
                                                           file_size=f_size, last_modified=f_mtime)
                    if secure_hash:
                        if secure_hash not in secure_hash_groups:
                            secure_hash_groups[secure_hash] = []

                        # Use cached stat or fetch if missing
                        if not stat:
                            try:
                                stat = file_path.stat()
                                f_size = stat.st_size
                                f_mtime = stat.st_mtime
                            except OSError:
                                continue

                        secure_hash_groups[secure_hash].append({
                            'path': file_path,
                            'size': f_size,
                            'mtime': f_mtime
                        })

            # Only groups with multiple files are true duplicates
            for secure_hash, duplicate_group in secure_hash_groups.items():
                if len(duplicate_group) > 1:
                    confirmed_duplicates[secure_hash] = duplicate_group
        
        if not confirmed_duplicates:
            print("✅ No confirmed duplicates found (passed SHA-256 verification)")
            return results
        
        results["duplicate_groups"] = len(confirmed_duplicates)
        
        print(f"🛡️  Confirmed {len(confirmed_duplicates)} duplicate groups with SHA-256")
        
        results["groups"] = []
        
        # Process each duplicate group
        for secure_hash, duplicate_group in confirmed_duplicates.items():
            results["duplicates_found"] += len(duplicate_group)
            
            print(f"\n🔍 Duplicate group ({len(duplicate_group)} files):")
            
            # Calculate safety scores for each file
            file_scores = []
            for file_info in duplicate_group:
                file_path = file_info['path']
                safety_score = self.calculate_safety_score(file_path, duplicate_group, last_modified=file_info.get('mtime'))
                
                # Get more file info for the group
                file_info_full = {
                    'path': str(file_path),
                    'name': file_path.name,
                    'size': file_info['size'],
                    'mtime': datetime.fromtimestamp(file_info['mtime']).isoformat() if hasattr(file_info, 'mtime') else time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(file_info.get('mtime', time.time()))),
                    'safety_score': safety_score
                }
                file_scores.append((file_path, safety_score, file_info['size'], file_info_full))
                print(f"   📄 {file_path.name} (safety: {safety_score:.2f})")
            
            # Sort by safety score (highest = safest to delete)
            file_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Add to results groups
            group_data = {
                "group_id": secure_hash,
                "total_size": sum(f[2] for f in file_scores),
                "files": [f[3] for f in file_scores]
            }
            results["groups"].append(group_data)
            
            # Keep the original (lowest safety score) and mark others for deletion
            files_to_keep = 1
            for i, (file_path, safety_score, file_size, _) in enumerate(file_scores):
                if i >= files_to_keep and safety_score > safety_threshold:  # Use configurable safety threshold
                    results["safe_to_delete"] += 1
                    results["space_recoverable"] += file_size
                    
                    print(f"   🗑️  Safe to delete: {file_path.name} (safety: {safety_score:.2f})")
                    
                    if execute:
                        try:
                            file_path.unlink()
                            results["deleted_files"] += 1
                            print(f"   ✅ Deleted: {file_path.name}")
                        except Exception as e:
                            error_msg = f"Failed to delete {file_path}: {e}"
                            results["errors"].append(error_msg)
                            print(f"   ❌ {error_msg}")
        
        # Print summary
        print(f"\n📊 DEDUPLICATION SUMMARY:")
        print(f"   Files scanned: {results['scanned_files']}")
        print(f"   Duplicate groups found: {results['duplicate_groups']}")
        print(f"   Total duplicates: {results['duplicates_found']}")
        print(f"   Safe to delete: {results['safe_to_delete']}")
        print(f"   Space recoverable: {results['space_recoverable'] / (1024*1024):.1f} MB")
        
        if execute:
            print(f"   Files deleted: {results['deleted_files']}")
            print(f"   Errors: {len(results['errors'])}")
        else:
            print(f"   🔍 DRY RUN - No files were deleted")
        
        return results

    def clean_local_duplicates_of_gdrive(self, gdrive_dirs: List[Path], local_dirs: List[Path], execute: bool = False) -> Dict:
        """
        Find files in local directories that already exist in Google Drive and delete local copies

        Args:
            gdrive_dirs: List of Google Drive directories to use as reference
            local_dirs: List of local directories to clean
            execute: If True, actually delete local duplicates

        Returns:
            Cleanup results with statistics
        """

        print("🔍 CROSS-DIRECTORY DUPLICATE CLEANUP")
        print(f"🛡️  Mode: {'EXECUTE' if execute else 'DRY RUN'}")
        print()

        results = {
            "gdrive_files_scanned": 0,
            "local_files_scanned": 0,
            "duplicates_found": 0,
            "space_recoverable": 0,
            "deleted_files": 0,
            "errors": []
        }

        # STEP 1: Build hash index of Google Drive files
        print("📁 STEP 1: Indexing Google Drive staging areas...")
        gdrive_hashes = {}  # secure_hash -> file_path

        # Optimization: Reuse database connection for batch processing
        with sqlite3.connect(self.db_path) as conn:
            for gdrive_dir in gdrive_dirs:
                if not gdrive_dir.exists():
                    print(f"   ⚠️  Skipping non-existent: {gdrive_dir}")
                    continue

                print(f"   📂 Scanning: {gdrive_dir.name}")

                for file_path in gdrive_dir.rglob('*'):
                    if not file_path.is_file():
                        continue

                    # Skip database/learned data
                    if self.is_database_or_learned_data(file_path):
                        continue

                    secure_hash = self.calculate_secure_hash(file_path, db_connection=conn)
                    if secure_hash:
                        gdrive_hashes[secure_hash] = file_path
                        results["gdrive_files_scanned"] += 1

                        if results["gdrive_files_scanned"] % 50 == 0:
                            print(f"      Progress: {results['gdrive_files_scanned']} files indexed")

            print(f"   ✅ Indexed {results['gdrive_files_scanned']} Google Drive files")
            print()

            # STEP 2: Scan local directories and compare
            print("💻 STEP 2: Scanning local directories for duplicates...")

            for local_dir in local_dirs:
                if not local_dir.exists():
                    print(f"   ⚠️  Skipping non-existent: {local_dir}")
                    continue

                print(f"   📂 Scanning: {local_dir}")

                for file_path in local_dir.rglob('*'):
                    if not file_path.is_file():
                        continue

                    # Skip database/learned data (ABSOLUTE PROTECTION)
                    if self.is_database_or_learned_data(file_path):
                        continue

                    # Skip files in protected paths
                    if any(protected in str(file_path) for protected in self.protected_paths):
                        continue

                    results["local_files_scanned"] += 1

                    if results["local_files_scanned"] % 50 == 0:
                        print(f"      Progress: {results['local_files_scanned']} local files scanned")

                    # Calculate hash and check if exists in Google Drive
                    secure_hash = self.calculate_secure_hash(file_path, db_connection=conn)

                    if secure_hash and secure_hash in gdrive_hashes:
                        # Found a duplicate!
                        gdrive_path = gdrive_hashes[secure_hash]
                        results["duplicates_found"] += 1

                        try:
                            file_size = file_path.stat().st_size
                            results["space_recoverable"] += file_size

                            print(f"   🔗 DUPLICATE FOUND:")
                            print(f"      Local:  {file_path}")
                            print(f"      GDrive: {gdrive_path}")
                            print(f"      Size:   {file_size / (1024*1024):.1f} MB")

                            if execute:
                                file_path.unlink()
                                results["deleted_files"] += 1
                                print(f"      ✅ Deleted local copy")
                            else:
                                print(f"      🔍 Would delete (dry-run)")

                            print()

                        except Exception as e:
                            error_msg = f"Failed to process {file_path}: {e}"
                            results["errors"].append(error_msg)
                            print(f"      ❌ {error_msg}")

        # STEP 3: Summary
        print("=" * 80)
        print("📊 CROSS-DIRECTORY CLEANUP SUMMARY:")
        print(f"   Google Drive files indexed: {results['gdrive_files_scanned']}")
        print(f"   Local files scanned: {results['local_files_scanned']}")
        print(f"   Duplicates found: {results['duplicates_found']}")
        print(f"   Space recoverable: {results['space_recoverable'] / (1024*1024):.1f} MB")

        if execute:
            print(f"   Files deleted: {results['deleted_files']}")
            print(f"   Errors: {len(results['errors'])}")
        else:
            print(f"   🔍 DRY RUN - No files were deleted")

        print("=" * 80)

        return results

def main():
    parser = argparse.ArgumentParser(description='Bulletproof Deduplication with SHA-256')
    parser.add_argument('--folder', required=True, help='Directory to scan for duplicates')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually delete duplicates (default is dry-run)')
    parser.add_argument('--safety-threshold', type=float, default=0.7,
                       help='Safety score threshold for deletion (0.0-1.0)')
    
    args = parser.parse_args()
    
    directory = Path(args.folder)
    deduplicator = BulletproofDeduplicator()
    
    print("🛡️  BULLETPROOF DEDUPLICATION SYSTEM")
    print("🔒 Two-Tier Hashing: MD5 (screening) + SHA-256 (verification)")
    print(f"⚖️  Safety threshold: {args.safety_threshold}")
    
    results = deduplicator.scan_directory(directory, args.execute, args.safety_threshold)
    
    if results.get("errors"):
        print("\n❌ ERRORS:")
        for error in results["errors"]:
            print(f"   {error}")
    
    print(f"\n{'✅ EXECUTION COMPLETE' if args.execute else '🔍 DRY RUN COMPLETE'}")

if __name__ == "__main__":
    main()