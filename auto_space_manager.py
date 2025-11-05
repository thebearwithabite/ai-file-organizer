#!/usr/bin/env python3
"""
Automated Disk Space Manager
Monitors disk space and auto-moves large files to Google Drive when low
"""

import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
GDRIVE_STAGING = Path.home() / "Google Drive" / "My Drive" / "99_STAGING_EMERGENCY"
DOWNLOADS = Path.home() / "Downloads"
MIN_FREE_GB = 15  # Alert threshold
CRITICAL_FREE_GB = 10  # Auto-move threshold
LARGE_FILE_MB = 50  # Files over 50MB get auto-moved

def get_disk_space():
    """Get free disk space in GB"""
    result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    if len(lines) > 1:
        parts = lines[1].split()
        avail_gb = float(parts[3].replace('Gi', ''))
        return avail_gb
    return 0

def get_large_files(directory, min_size_mb=50):
    """Find files larger than min_size_mb"""
    large_files = []
    for file_path in Path(directory).glob('*'):
        if file_path.is_file():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb >= min_size_mb:
                large_files.append((file_path, size_mb))
    
    # Sort by size (largest first)
    large_files.sort(key=lambda x: x[1], reverse=True)
    return large_files

def move_to_gdrive(file_path, dest_dir):
    """Move file to Google Drive staging"""
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file_path.name
        
        print(f"📦 Moving: {file_path.name} ({file_path.stat().st_size / (1024*1024):.1f}MB)")
        shutil.move(str(file_path), str(dest_path))
        print(f"   → {dest_path}")
        return True
    except Exception as e:
        print(f"❌ Error moving {file_path.name}: {e}")
        return False

def main():
    free_gb = get_disk_space()
    print(f"\n💾 Current free space: {free_gb:.1f}GB")
    
    if free_gb < CRITICAL_FREE_GB:
        print(f"🚨 CRITICAL: Only {free_gb:.1f}GB free! Auto-moving large files...")
        large_files = get_large_files(DOWNLOADS, LARGE_FILE_MB)
        
        moved_count = 0
        freed_mb = 0
        
        for file_path, size_mb in large_files[:10]:  # Move up to 10 largest files
            if move_to_gdrive(file_path, GDRIVE_STAGING):
                moved_count += 1
                freed_mb += size_mb
                
                # Check if we've freed enough space
                current_free = get_disk_space()
                if current_free > MIN_FREE_GB:
                    print(f"✅ Space recovered! Now at {current_free:.1f}GB free")
                    break
        
        print(f"\n📊 Summary:")
        print(f"   Files moved: {moved_count}")
        print(f"   Space freed: {freed_mb:.1f}MB")
        
    elif free_gb < MIN_FREE_GB:
        print(f"⚠️  WARNING: Only {free_gb:.1f}GB free")
        print(f"   Large files in Downloads:")
        large_files = get_large_files(DOWNLOADS, LARGE_FILE_MB)
        for file_path, size_mb in large_files[:5]:
            print(f"   - {file_path.name} ({size_mb:.1f}MB)")
    else:
        print(f"✅ Disk space healthy: {free_gb:.1f}GB free")

if __name__ == "__main__":
    main()
