#!/usr/bin/env python3
import sys
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator
import os

def test_deduplication_logic():
    print("\n--- Testing BulletproofDeduplicator Logic ---")
    dedup = BulletproofDeduplicator()
    
    # Create mock files for testing
    test_dir = Path("test_dedup_zone")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Create two different duplicate groups
        (test_dir / "file1.txt").write_text("content A")
        (test_dir / "file1_copy.txt").write_text("content A")
        
        (test_dir / "file2.txt").write_text("content B")
        (test_dir / "file2_copy.txt").write_text("content B")
        
        print("   Running scan...")
        results = dedup.scan_directory(test_dir)
        
        # We expect 2 duplicate groups
        group_count = results.get("duplicate_groups", 0)
        print(f"   Duplicate groups found: {group_count}")
        
        if group_count == 2:
            print("✅ Deduplication logic successfully identified BOTH groups (Indicates fix for logic leak and NameError)")
        else:
            print(f"❌ Deduplication logic failed. Expected 2 groups, got {group_count}")
            
    finally:
        # Cleanup
        for f in test_dir.glob("*"): f.unlink()
        test_dir.rmdir()

if __name__ == "__main__":
    test_deduplication_logic()
