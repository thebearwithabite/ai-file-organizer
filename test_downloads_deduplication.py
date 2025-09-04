#!/usr/bin/env python3
"""
Test Deduplication on Downloads Folder First
Safe way to test the system before doing full system scan
"""

import sys
from pathlib import Path
from datetime import datetime

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from deduplication_system import BulletproofDeduplicator
from safe_deduplication import SafeDeduplicator

def test_downloads_deduplication():
    """Test deduplication specifically on Downloads folder"""
    
    print("🧪 Testing Deduplication on Downloads Folder")
    print("=" * 60)
    
    downloads_dir = Path.home() / "Downloads"
    if not downloads_dir.exists():
        print("❌ Downloads folder not found")
        return
    
    deduper = BulletproofDeduplicator()
    safe_deduper = SafeDeduplicator()
    
    # Find all files in Downloads
    files_to_hash = []
    for file_path in downloads_dir.rglob("*"):
        if (file_path.is_file() and 
            file_path.stat().st_size > 1024 and  # Skip tiny files
            not file_path.name.startswith('.')):  # Skip hidden files
            files_to_hash.append(file_path)
    
    print(f"📁 Found {len(files_to_hash)} files in Downloads to analyze")
    
    if len(files_to_hash) == 0:
        print("✅ Downloads folder is empty or has no suitable files")
        return
    
    # Hash files in batches
    print(f"\n🔍 Hashing files...")
    hashed_count = 0
    duplicates_found = 0
    
    for i, file_path in enumerate(files_to_hash, 1):
        try:
            print(f"[{i}/{len(files_to_hash)}] {file_path.name}")
            
            # Hash the file
            record = deduper.hash_file(file_path)
            hashed_count += 1
            
            # Check for immediate duplicates
            quick_duplicates = deduper.find_duplicates_by_quick_hash(record.quick_hash)
            if len(quick_duplicates) > 1:
                # Verify with secure hash
                for potential in quick_duplicates:
                    if (potential.file_path != str(file_path) and
                        potential.secure_hash == record.secure_hash):
                        duplicates_found += 1
                        print(f"   🔍 Duplicate found: matches {Path(potential.file_path).name}")
                        break
            
            # Progress update every 20 files
            if i % 20 == 0:
                print(f"   Progress: {i}/{len(files_to_hash)} files processed")
        
        except Exception as e:
            print(f"   ❌ Error hashing {file_path.name}: {e}")
    
    print(f"\n📊 Hashing Complete:")
    print(f"   Files hashed: {hashed_count}")
    print(f"   Duplicates found: {duplicates_found}")
    
    # Analyze duplicate groups
    print(f"\n🔍 Analyzing duplicate groups...")
    duplicate_groups = safe_deduper.analyze_duplicate_groups()
    
    # Filter to only Downloads duplicates
    downloads_groups = []
    for group in duplicate_groups:
        downloads_files = [f for f in group.files if downloads_dir in f.parents and f.exists()]
        if len(downloads_files) >= 2:  # At least 2 files in Downloads
            downloads_groups.append(group)
    
    if not downloads_groups:
        print("✅ No duplicate groups found in Downloads!")
        return
    
    print(f"📂 Found {len(downloads_groups)} duplicate groups in Downloads")
    
    # Show preview
    preview = safe_deduper.preview_deduplication(downloads_groups)
    
    print(f"\n🎯 DOWNLOADS DEDUPLICATION PREVIEW:")
    print(f"   Duplicate groups: {len(downloads_groups)}")
    print(f"   Safe deletions: {preview['safe_deletions']} files")
    print(f"   Space to free: {preview['safe_space_mb']:.1f} MB")
    
    # Show specific examples
    print(f"\n📂 Top duplicate groups in Downloads:")
    sorted_groups = sorted(downloads_groups, key=lambda g: g.total_size, reverse=True)[:5]
    
    for i, group in enumerate(sorted_groups, 1):
        downloads_files = [f for f in group.files if downloads_dir in f.parents and f.exists()]
        size_mb = group.total_size / (1024**2)
        
        print(f"\n   {i}. {len(downloads_files)} copies in Downloads:")
        print(f"      Original: {group.original_file.name}")
        print(f"      Size: {size_mb:.1f} MB | Safety: {group.safety_score:.1%}")
        
        for dup_file in downloads_files:
            if dup_file != group.original_file:
                print(f"      Would delete: {dup_file.name}")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Review the duplicates above")
    print(f"   2. Run: python safe_deduplication.py --dry-run")  
    print(f"   3. When confident: python safe_deduplication.py --execute")
    
    return {
        'files_analyzed': hashed_count,
        'duplicate_groups': len(downloads_groups),
        'safe_deletions': preview['safe_deletions'],
        'space_savings_mb': preview['safe_space_mb']
    }

if __name__ == "__main__":
    result = test_downloads_deduplication()
    if result:
        print(f"\n✅ Downloads analysis complete!")
        print(f"   Ready to proceed with safe deduplication")