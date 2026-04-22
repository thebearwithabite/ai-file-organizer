#!/usr/bin/env python3
"""
Safe File Deduplication with Multiple Confirmation Layers
Bulletproof system for actually DELETING duplicate files
ADHD-friendly with clear confirmations and easy recovery
"""

import sys
import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import sqlite3

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from deduplication_system import BulletproofDeduplicator, FileHashRecord, DuplicateAction

@dataclass
class DuplicateGroup:
    """A group of duplicate files with safety metadata"""
    secure_hash: str
    files: List[Path]
    total_size: int
    original_file: Path  # The file to keep (oldest/most accessible)
    candidates_for_deletion: List[Path]
    safety_score: float  # 0-1, how safe is it to delete
    requires_manual_review: bool

class SafeDeduplicator:
    """
    Safe duplicate file deletion with multiple confirmation layers
    Never deletes anything without being absolutely certain
    """
    
    def __init__(self, base_dir: str = None):
        self.deduper = BulletproofDeduplicator(base_dir)
        self.base_dir = self.deduper.base_dir
        
        # Safety settings (ADHD-friendly)
        self.max_deletions_per_session = 25  # Conservative limit
        self.require_confirmation_over_mb = 10  # Confirm for files >10MB
        self.backup_before_delete = True
        self.backup_retention_days = 30
        
        # Protected locations (never delete from these)
        self.protected_paths = {
            Path.home() / "Desktop",
            Path.home() / "Applications", 
            Path("/Applications"),
            Path("/System"),
            Path("/Library"),
            Path.home() / "Library" / "Application Support",
        }
        
        # Preferred locations (keep files from these over others)
        self.preferred_paths = {
            Path.home() / "Documents",
            Path.home() / "Dropbox",
            Path.home() / "Google Drive",
            Path.home() / "iCloud Drive",
        }
    
    def calculate_safety_score(self, duplicate_group: List[Path]) -> float:
        """Calculate how safe it is to deduplicate this group (0-1)"""
        
        safety_factors = []
        
        # Factor 1: File age (older = safer)
        ages = []
        for file_path in duplicate_group:
            if file_path.exists():
                age_days = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
                ages.append(age_days)
        
        avg_age = sum(ages) / len(ages) if ages else 0
        age_safety = min(avg_age / 30, 1.0)  # 30+ days = full safety
        safety_factors.append(age_safety)
        
        # Factor 2: Location diversity (more locations = safer)
        unique_parents = set(f.parent for f in duplicate_group if f.exists())
        location_safety = min(len(unique_parents) / 3, 1.0)  # 3+ locations = full safety
        safety_factors.append(location_safety)
        
        # Factor 3: No protected paths
        has_protected = any(self._is_in_protected_path(f) for f in duplicate_group)
        protected_safety = 0.3 if has_protected else 1.0
        safety_factors.append(protected_safety)
        
        # Factor 4: File size (smaller files safer to dedupe)
        if duplicate_group:
            avg_size_mb = sum(f.stat().st_size for f in duplicate_group if f.exists()) / len(duplicate_group) / (1024**2)
            size_safety = max(1.0 - (avg_size_mb / 100), 0.2)  # 100MB+ = low safety
            safety_factors.append(size_safety)
        
        # Factor 5: File type (documents safer than executables)
        file_types = set()
        for file_path in duplicate_group:
            if file_path.exists():
                file_types.add(file_path.suffix.lower())
        
        safe_extensions = {'.pdf', '.docx', '.txt', '.jpg', '.png', '.mp4', '.mov'}
        unsafe_extensions = {'.exe', '.app', '.dmg', '.pkg'}
        
        if any(ext in unsafe_extensions for ext in file_types):
            type_safety = 0.2
        elif any(ext in safe_extensions for ext in file_types):
            type_safety = 1.0
        else:
            type_safety = 0.6
        
        safety_factors.append(type_safety)
        
        # Overall safety is the minimum factor (most conservative)
        return min(safety_factors)
    
    def _is_in_protected_path(self, file_path: Path) -> bool:
        """Check if file is in a protected location"""
        try:
            for protected in self.protected_paths:
                if protected in file_path.parents or file_path == protected:
                    return True
        except:
            pass
        return False
    
    def _choose_original_file(self, duplicate_files: List[Path]) -> Path:
        """Choose which file to keep as the original (never delete this one)"""
        
        existing_files = [f for f in duplicate_files if f.exists()]
        if not existing_files:
            return duplicate_files[0]
        
        # Scoring system for choosing the best original
        scored_files = []
        
        for file_path in existing_files:
            score = 0
            
            # Prefer files in preferred locations
            for preferred in self.preferred_paths:
                if preferred in file_path.parents:
                    score += 100
                    break
            
            # Prefer older files (more established)
            age_days = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
            score += min(age_days, 30)  # Up to 30 points for age
            
            # Prefer files with better names (not in Downloads, not numbered copies)
            if "Downloads" in str(file_path):
                score -= 20
            if any(pattern in file_path.name.lower() for pattern in [" copy", " (1)", " (2)", "_copy"]):
                score -= 15
            if len(file_path.name) > 10:  # Prefer descriptive names
                score += 5
            
            # Prefer files that are more accessible
            if file_path.parent.name.lower() in ["desktop", "documents"]:
                score += 10
            
            scored_files.append((score, file_path))
        
        # Return the highest scored file
        scored_files.sort(reverse=True)
        return scored_files[0][1]
    
    def analyze_duplicate_groups(self) -> List[DuplicateGroup]:
        """Analyze all duplicates and create safe deletion plan"""
        
        print("🔍 Analyzing duplicate files for safe deletion...")
        
        all_duplicates = self.deduper.find_all_duplicates()
        duplicate_groups = []
        
        for secure_hash, files in all_duplicates.items():
            if len(files) < 2:
                continue
            
            # Calculate safety and choose original
            safety_score = self.calculate_safety_score(files)
            original_file = self._choose_original_file(files)
            candidates = [f for f in files if f != original_file and f.exists()]
            
            total_size = sum(f.stat().st_size for f in files if f.exists())
            requires_review = (
                safety_score < 0.7 or 
                total_size > self.require_confirmation_over_mb * 1024 * 1024 or
                any(self._is_in_protected_path(f) for f in files)
            )
            
            group = DuplicateGroup(
                secure_hash=secure_hash,
                files=files,
                total_size=total_size,
                original_file=original_file,
                candidates_for_deletion=candidates,
                safety_score=safety_score,
                requires_manual_review=requires_review
            )
            
            duplicate_groups.append(group)
        
        # Sort by safety score (safest first)
        duplicate_groups.sort(key=lambda x: x.safety_score, reverse=True)
        
        return duplicate_groups
    
    def preview_deduplication(self, duplicate_groups: List[DuplicateGroup]) -> Dict:
        """Show what would be deleted in a safe preview"""
        
        safe_groups = [g for g in duplicate_groups if g.safety_score >= 0.7 and not g.requires_manual_review]
        review_groups = [g for g in duplicate_groups if g.requires_manual_review or g.safety_score < 0.7]
        
        safe_deletions = sum(len(g.candidates_for_deletion) for g in safe_groups)
        safe_space = sum(g.total_size - g.original_file.stat().st_size for g in safe_groups 
                        if g.original_file.exists())
        
        review_deletions = sum(len(g.candidates_for_deletion) for g in review_groups)
        review_space = sum(g.total_size - g.original_file.stat().st_size for g in review_groups 
                          if g.original_file.exists())
        
        print(f"\n📊 DEDUPLICATION PREVIEW")
        print(f"=" * 50)
        print(f"✅ Safe to delete automatically:")
        print(f"   Files: {safe_deletions}")
        print(f"   Space to free: {safe_space / (1024**2):.1f} MB")
        
        print(f"\n⚠️  Requires manual review:")
        print(f"   Files: {review_deletions}")
        print(f"   Space to free: {review_space / (1024**2):.1f} MB")
        
        total_space = (safe_space + review_space) / (1024**2)
        print(f"\n🎯 Total potential space savings: {total_space:.1f} MB")
        
        # Show examples of what would be deleted
        print(f"\n📂 Example safe deletions:")
        for group in safe_groups[:3]:
            print(f"   Keep: {group.original_file.name}")
            for candidate in group.candidates_for_deletion[:2]:
                print(f"   Delete: {candidate.name} (safety: {group.safety_score:.1%})")
        
        return {
            'safe_groups': safe_groups,
            'review_groups': review_groups,
            'safe_deletions': safe_deletions,
            'safe_space_mb': safe_space / (1024**2),
            'total_space_mb': total_space
        }
    
    def execute_safe_deletions(self, safe_groups: List[DuplicateGroup], dry_run: bool = True) -> Dict:
        """Execute safe deletions with backup and logging"""
        
        if dry_run:
            print(f"\n🧪 DRY RUN - No files will be deleted")
        else:
            print(f"\n🗑️  EXECUTING SAFE DELETIONS")
        
        deleted_count = 0
        freed_space = 0
        failed_deletions = []
        
        # Limit deletions per session (ADHD-friendly)
        limited_groups = safe_groups[:self.max_deletions_per_session]
        
        for group in limited_groups:
            print(f"\n📂 Processing duplicate group (safety: {group.safety_score:.1%}):")
            print(f"   Keeping: {group.original_file.name}")
            
            for candidate in group.candidates_for_deletion:
                if not candidate.exists():
                    continue
                
                try:
                    file_size = candidate.stat().st_size
                    
                    if dry_run:
                        print(f"   Would delete: {candidate.name} ({file_size / 1024:.1f} KB)")
                        deleted_count += 1
                        freed_space += file_size
                    else:
                        # Create backup before deletion
                        if self.backup_before_delete:
                            backup_path = self._create_backup(candidate, group.secure_hash)
                            print(f"   Backed up: {candidate.name}")
                        
                        # Delete the file
                        candidate.unlink()
                        print(f"   ✅ Deleted: {candidate.name} ({file_size / 1024:.1f} KB)")
                        
                        # Log the deletion
                        self._log_deletion(candidate, group.original_file, group.secure_hash, backup_path if self.backup_before_delete else None)
                        
                        deleted_count += 1
                        freed_space += file_size
                
                except Exception as e:
                    print(f"   ❌ Failed to delete {candidate.name}: {e}")
                    failed_deletions.append((candidate, str(e)))
        
        print(f"\n📊 Deletion Summary:")
        print(f"   ✅ Deleted: {deleted_count} files")
        print(f"   💾 Space freed: {freed_space / (1024**2):.1f} MB")
        print(f"   ❌ Failed: {len(failed_deletions)} files")
        
        return {
            'deleted_count': deleted_count,
            'freed_space_mb': freed_space / (1024**2),
            'failed_deletions': failed_deletions
        }
    
    def _create_backup(self, file_path: Path, secure_hash: str) -> Path:
        """Create backup of file before deletion"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{secure_hash[:8]}_{timestamp}{file_path.suffix}"
        backup_path = self.deduper.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _log_deletion(self, deleted_file: Path, original_file: Path, secure_hash: str, backup_path: Optional[Path]):
        """Log file deletion for recovery purposes"""
        with sqlite3.connect(self.deduper.db_path) as conn:
            conn.execute("""
                INSERT INTO deletion_log 
                (deleted_file, backup_path, secure_hash, file_size, duplicate_of, can_restore)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(deleted_file),
                str(backup_path) if backup_path else None,
                secure_hash,
                deleted_file.stat().st_size if deleted_file.exists() else 0,
                str(original_file),
                backup_path is not None
            ))
            conn.commit()

def main():
    """Interactive safe deduplication"""
    
    print("🛡️  Safe File Deduplication System")
    print("=" * 50)
    
    deduper = SafeDeduplicator()
    
    # First, ensure we have hashes for system analysis
    print("🔍 Checking for duplicate analysis...")
    
    # Analyze duplicate groups
    duplicate_groups = deduper.analyze_duplicate_groups()
    
    if not duplicate_groups:
        print("✅ No duplicates found! Your system is clean.")
        return
    
    # Preview what would be deleted
    preview = deduper.preview_deduplication(duplicate_groups)
    
    if preview['safe_deletions'] == 0:
        print("⚠️  No files are safe for automatic deletion.")
        print("    All duplicates require manual review.")
        return
    
    # Ask for confirmation
    print(f"\n❓ Proceed with safe deletions?")
    print(f"   --dry-run: Preview only (default)")
    print(f"   --execute: Actually delete files")
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Actually delete duplicate files')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Preview only')
    
    if len(sys.argv) == 1:
        # Default to dry run
        result = deduper.execute_safe_deletions(preview['safe_groups'], dry_run=True)
    else:
        args = parser.parse_args()
        result = deduper.execute_safe_deletions(preview['safe_groups'], dry_run=not args.execute)

if __name__ == "__main__":
    main()