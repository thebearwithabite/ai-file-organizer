#!/usr/bin/env python3
"""
System-Wide Deduplication Indexer
One-time command to hash all existing files for duplicate detection
ADHD-friendly with progress tracking and batch processing
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Set, List, Dict
import time

project_dir = Path(__file__).parent  
sys.path.insert(0, str(project_dir))

from deduplication_system import BulletproofDeduplicator
from safe_deduplication import SafeDeduplicator

class SystemDeduplicationIndexer:
    """
    Index entire system for duplicate detection
    Processes files in ADHD-friendly batches with clear progress
    """
    
    def __init__(self):
        self.deduper = BulletproofDeduplicator()
        self.safe_deduper = SafeDeduplicator()
        
        # ADHD-friendly batch settings
        self.batch_size = 50
        self.progress_report_interval = 100
        self.break_between_batches_seconds = 2
        
        # Skip these directories (too risky or too large)
        self.skip_directories = {
            "Library/Application Support",
            "Library/Caches", 
            "System",
            "Applications",
            "Library/Mail",  # Already handled by email extractor
            ".git",
            "node_modules",
            "__pycache__",
            ".DS_Store"
        }
        
        # Priority directories (index these first)
        self.priority_directories = [
            Path.home() / "Downloads",
            Path.home() / "Desktop", 
            Path.home() / "Documents",
            Path.home() / "Dropbox",
            Path.home() / "Google Drive",
            Path.home() / "iCloud Drive (Archive)",
        ]
        
        # File extensions to prioritize (likely to have duplicates)
        self.priority_extensions = {
            '.pdf', '.docx', '.doc', '.txt', '.pages',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.mp4', '.mov', '.avi', '.mkv', '.webm',
            '.zip', '.tar', '.gz', '.dmg', '.pkg',
            '.mp3', '.m4a', '.wav', '.flac'
        }
    
    def should_skip_directory(self, directory: Path) -> bool:
        """Check if directory should be skipped"""
        dir_str = str(directory)
        return any(skip_pattern in dir_str for skip_pattern in self.skip_directories)
    
    def find_all_files_to_index(self) -> List[Path]:
        """Find all files that should be indexed for deduplication"""
        
        print("🔍 Scanning system for files to index...")
        
        all_files = []
        
        # First, scan priority directories
        for priority_dir in self.priority_directories:
            if priority_dir.exists():
                print(f"📂 Scanning priority directory: {priority_dir}")
                
                for file_path in priority_dir.rglob("*"):
                    if (file_path.is_file() and 
                        not self.should_skip_directory(file_path.parent) and
                        file_path.stat().st_size > 0):  # Skip empty files
                        all_files.append(file_path)
        
        # Then scan home directory for any missed files
        print(f"📂 Scanning remaining home directory...")
        home = Path.home()
        
        for file_path in home.rglob("*"):
            if (file_path.is_file() and 
                not self.should_skip_directory(file_path.parent) and
                file_path.stat().st_size > 0 and
                file_path not in all_files):
                all_files.append(file_path)
        
        # Prioritize by extension and size
        priority_files = []
        other_files = []
        
        for file_path in all_files:
            if file_path.suffix.lower() in self.priority_extensions:
                priority_files.append(file_path)
            else:
                other_files.append(file_path)
        
        # Sort priority files by size (larger first - more likely duplicates)
        priority_files.sort(key=lambda f: f.stat().st_size, reverse=True)
        
        print(f"📊 Files to index:")
        print(f"   Priority files: {len(priority_files)}")
        print(f"   Other files: {len(other_files)}")
        print(f"   Total: {len(all_files)}")
        
        return priority_files + other_files
    
    def index_files_in_batches(self, files_to_index: List[Path], resume_from: int = 0):
        """Index files in ADHD-friendly batches with progress tracking"""
        
        total_files = len(files_to_index)
        processed = resume_from
        duplicates_found = 0
        
        print(f"\n🚀 Starting system-wide deduplication indexing")
        print(f"📊 Files to process: {total_files}")
        if resume_from > 0:
            print(f"📍 Resuming from file #{resume_from}")
        
        start_time = datetime.now()
        
        # Process in batches
        for i in range(resume_from, total_files, self.batch_size):
            batch = files_to_index[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_files + self.batch_size - 1) // self.batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} files)")
            print(f"🕐 Progress: {processed}/{total_files} ({processed/total_files*100:.1f}%)")
            
            batch_start = time.time()
            batch_duplicates = 0
            
            for j, file_path in enumerate(batch):
                try:
                    # Hash the file
                    record = self.deduper.hash_file(file_path)
                    
                    # Check for immediate duplicates using quick hash
                    quick_duplicates = self.deduper.find_duplicates_by_quick_hash(record.quick_hash)
                    
                    if len(quick_duplicates) > 1:
                        # Verify with secure hash
                        for duplicate_record in quick_duplicates:
                            if (duplicate_record.file_path != str(file_path) and
                                duplicate_record.secure_hash == record.secure_hash):
                                batch_duplicates += 1
                                duplicates_found += 1
                                print(f"   🔍 Duplicate found: {file_path.name}")
                                break
                    
                    processed += 1
                    
                    # Progress within batch
                    if (j + 1) % 10 == 0:
                        print(f"      [{j + 1}/{len(batch)}] {file_path.name}")
                
                except Exception as e:
                    print(f"   ❌ Failed to hash {file_path.name}: {e}")
                    processed += 1
            
            batch_time = time.time() - batch_start
            
            print(f"   ✅ Batch complete: {len(batch)} files in {batch_time:.1f}s")
            print(f"   🔍 Duplicates in batch: {batch_duplicates}")
            
            # ADHD-friendly progress report
            if processed % self.progress_report_interval == 0:
                elapsed = datetime.now() - start_time
                rate = processed / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
                eta_seconds = (total_files - processed) / rate if rate > 0 else 0
                eta = timedelta(seconds=int(eta_seconds))
                
                print(f"\n📊 PROGRESS REPORT:")
                print(f"   Processed: {processed}/{total_files} files")
                print(f"   Duplicates found: {duplicates_found}")
                print(f"   Processing rate: {rate:.1f} files/second")
                print(f"   Estimated time remaining: {eta}")
                print(f"   Elapsed time: {elapsed}")
            
            # Short break between batches (ADHD-friendly)
            if batch_num < total_batches:
                print(f"   ⏸️  Brief pause between batches...")
                time.sleep(self.break_between_batches_seconds)
        
        total_time = datetime.now() - start_time
        
        print(f"\n🎉 SYSTEM INDEXING COMPLETE!")
        print(f"=" * 50)
        print(f"📊 Final Statistics:")
        print(f"   Total files processed: {processed}")
        print(f"   Duplicates identified: {duplicates_found}")
        print(f"   Total time: {total_time}")
        print(f"   Average rate: {processed / total_time.total_seconds():.1f} files/second")
        
        return {
            'processed_files': processed,
            'duplicates_found': duplicates_found,
            'total_time': total_time
        }
    
    def run_full_system_analysis(self):
        """Run complete system analysis and show deduplication opportunities"""
        
        print("🔍 Running full system deduplication analysis...")
        
        # Find duplicates
        duplicate_groups = self.safe_deduper.analyze_duplicate_groups()
        
        if not duplicate_groups:
            print("✅ No duplicates found in indexed files!")
            return
        
        # Show preview
        preview = self.safe_deduper.preview_deduplication(duplicate_groups)
        
        print(f"\n🎯 DEDUPLICATION OPPORTUNITIES:")
        print(f"   Duplicate groups found: {len(duplicate_groups)}")
        print(f"   Safe automatic deletions: {preview['safe_deletions']} files")
        print(f"   Space that can be freed: {preview['safe_space_mb']:.1f} MB")
        
        # Show top duplicate groups
        print(f"\n📂 Top duplicate groups by size:")
        sorted_groups = sorted(duplicate_groups, key=lambda g: g.total_size, reverse=True)
        for i, group in enumerate(sorted_groups[:5], 1):
            size_mb = group.total_size / (1024**2)
            print(f"   {i}. {len(group.files)} copies of {group.original_file.name}")
            print(f"      Total size: {size_mb:.1f} MB | Safety: {group.safety_score:.1%}")
        
        print(f"\n💡 Next steps:")
        print(f"   python safe_deduplication.py --dry-run   # Preview safe deletions")
        print(f"   python safe_deduplication.py --execute   # Actually delete duplicates")

def main():
    """Main indexing command"""
    
    print("🗂️  System-Wide Deduplication Indexer")
    print("=" * 60)
    
    indexer = SystemDeduplicationIndexer()
    
    import argparse
    parser = argparse.ArgumentParser(description="Index entire system for deduplication")
    parser.add_argument('--index-only', action='store_true', 
                       help='Only index files, don\'t analyze duplicates')
    parser.add_argument('--analyze-only', action='store_true', 
                       help='Only analyze existing index for duplicates')
    parser.add_argument('--resume-from', type=int, default=0,
                       help='Resume indexing from specific file number')
    
    args = parser.parse_args()
    
    if args.analyze_only:
        indexer.run_full_system_analysis()
    elif args.index_only:
        files_to_index = indexer.find_all_files_to_index()
        indexer.index_files_in_batches(files_to_index, args.resume_from)
    else:
        # Full process: index then analyze
        files_to_index = indexer.find_all_files_to_index()
        indexer.index_files_in_batches(files_to_index, args.resume_from)
        indexer.run_full_system_analysis()

if __name__ == "__main__":
    main()