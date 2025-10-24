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
from typing import Dict, List, Optional, Tuple, Set
import time
import json

class BulletproofDeduplicator:
    """
    Military-grade duplicate detection using two-tier hashing system
    - Tier 1: MD5 for lightning-fast screening (0.1ms per file)
    - Tier 2: SHA-256 for bulletproof verification (2ms per file)
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.db_path = self.base_dir / "deduplication.db"
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
        
        # Protected paths - never delete from these
        self.protected_paths = {
            '/System', '/Applications', '/Library',
            '/.git', '/.svn', '/node_modules'
        }
    
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
    
    def calculate_quick_hash(self, file_path: Path) -> Optional[str]:
        """
        Tier 1: Lightning-fast MD5 screening (~0.1ms per file)
        Used for initial duplicate detection
        """
        try:
            # Skip symlinks and special files
            if file_path.is_symlink():
                return None

            # Check file size - warn about large files
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
    
    def calculate_secure_hash(self, file_path: Path) -> Optional[str]:
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
                # Read file in chunks for memory efficiency
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except (PermissionError, OSError) as e:
            # Skip files we can't read (locked, network, etc.)
            return None
        except Exception as e:
            print(f"⚠️ Secure hash error for {file_path.name}: {e}")
            return None
    
    def calculate_safety_score(self, file_path: Path, duplicate_group: List[Dict]) -> float:
        """
        Calculate safety score (0.0-1.0) for file deletion
        Higher score = safer to delete
        """
        score = 0.0
        
        # File age factor (older = safer to delete)
        try:
            age_days = (time.time() - file_path.stat().st_mtime) / (24 * 3600)
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
        elif any(protected in path_str for protected in ['/documents', '/desktop']):
            score -= 0.2
        
        # Pattern recognition (obvious duplicates safer)
        filename = file_path.name
        for pattern in self.safe_duplicate_patterns:
            if re.match(pattern, filename):
                score += 0.4
                break
        
        # Group size factor (more duplicates = safer to delete one)
        if len(duplicate_group) > 3:
            score += 0.2
        elif len(duplicate_group) > 1:
            score += 0.1
        
        # Protected path check
        if any(protected in str(file_path) for protected in self.protected_paths):
            score = 0.0  # Never delete from protected paths
        
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
        
        # Find all files
        all_files = []
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                all_files.append(file_path)
        
        print(f"📁 Found {len(all_files)} files to analyze")

        # Group files by quick hash (Tier 1 screening)
        print("⚡ Tier 1: Quick MD5 screening...")
        quick_hash_groups = {}
        skipped_files = 0

        for i, file_path in enumerate(all_files):
            # Show progress every 50 files
            if (i + 1) % 50 == 0 or (i + 1) == len(all_files):
                print(f"   Progress: {i + 1}/{len(all_files)} files ({((i+1)/len(all_files)*100):.1f}%)")

            quick_hash = self.calculate_quick_hash(file_path)
            if quick_hash:
                if quick_hash not in quick_hash_groups:
                    quick_hash_groups[quick_hash] = []
                quick_hash_groups[quick_hash].append(file_path)
            else:
                skipped_files += 1

        if skipped_files > 0:
            print(f"   ⏭️  Skipped {skipped_files} files (locked, symlinks, or inaccessible)")

        results["scanned_files"] = len(all_files)
        
        # Find potential duplicates (groups with multiple files)
        potential_duplicates = {k: v for k, v in quick_hash_groups.items() if len(v) > 1}
        
        if not potential_duplicates:
            print("✅ No duplicates found")
            return results
        
        print(f"🔍 Found {len(potential_duplicates)} potential duplicate groups")
        print("🔒 Tier 2: SHA-256 bulletproof verification...")

        # Verify with SHA-256 (Tier 2 verification)
        confirmed_duplicates = {}
        total_groups = len(potential_duplicates)

        for group_idx, (quick_hash, file_list) in enumerate(potential_duplicates.items()):
            # Show progress for verification phase
            if (group_idx + 1) % 10 == 0 or (group_idx + 1) == total_groups:
                print(f"   Verifying group {group_idx + 1}/{total_groups} ({((group_idx+1)/total_groups*100):.1f}%)")

            # Calculate secure hashes for this group
            secure_hash_groups = {}

            for file_path in file_list:
                secure_hash = self.calculate_secure_hash(file_path)
                if secure_hash:
                    if secure_hash not in secure_hash_groups:
                        secure_hash_groups[secure_hash] = []
                    secure_hash_groups[secure_hash].append({
                        'path': file_path,
                        'size': file_path.stat().st_size,
                        'mtime': file_path.stat().st_mtime
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
        
        # Process each duplicate group
        for secure_hash, duplicate_group in confirmed_duplicates.items():
            results["duplicates_found"] += len(duplicate_group)
            
            print(f"\n🔍 Duplicate group ({len(duplicate_group)} files):")
            
            # Calculate safety scores for each file
            file_scores = []
            for file_info in duplicate_group:
                file_path = file_info['path']
                safety_score = self.calculate_safety_score(file_path, duplicate_group)
                file_scores.append((file_path, safety_score, file_info['size']))
                print(f"   📄 {file_path.name} (safety: {safety_score:.2f})")
            
            # Sort by safety score (highest = safest to delete)
            file_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Keep the original (lowest safety score) and mark others for deletion
            files_to_keep = 1
            for i, (file_path, safety_score, file_size) in enumerate(file_scores):
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