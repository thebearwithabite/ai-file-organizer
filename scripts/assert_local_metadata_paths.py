#!/usr/bin/env python3
"""
Local Metadata Path Sanity Checker
Ensures no files are being written to Google Drive CloudStorage paths.

Usage:
    python scripts/assert_local_metadata_paths.py

Exit codes:
    0: All checks passed
    1: New files detected in CloudStorage (ERROR)
    2: Script error
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")

def format_size(size_bytes):
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"

def check_local_metadata():
    """Check local metadata system at ~/Documents/AI_METADATA_SYSTEM"""
    print_header("LOCAL METADATA SYSTEM CHECK")

    local_path = Path.home() / "Documents" / "AI_METADATA_SYSTEM"

    if not local_path.exists():
        print_error(f"Local metadata directory not found: {local_path}")
        return False

    print_success(f"Local metadata directory exists: {local_path}")

    # Check for database files
    db_files = list(local_path.glob("*.db"))
    print(f"\n  Database files ({len(db_files)}):")
    for db in sorted(db_files):
        size = db.stat().st_size
        mtime = datetime.fromtimestamp(db.stat().st_mtime)
        print(f"    • {db.name:40s} {format_size(size):>10s}  (modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")

    # Check vector DB
    vector_db_path = local_path / "vector_db"
    if vector_db_path.exists():
        vector_db_size = sum(f.stat().st_size for f in vector_db_path.rglob('*') if f.is_file())
        print_success(f"Vector database exists: {vector_db_path} ({format_size(vector_db_size)})")
    else:
        print_warning(f"Vector database not found: {vector_db_path}")

    # Check caches
    cache_dirs = ["content_cache", "vision_cache", "adaptive_learning"]
    print(f"\n  Cache directories:")
    for cache_name in cache_dirs:
        cache_path = local_path / cache_name
        if cache_path.exists():
            file_count = len(list(cache_path.rglob('*')))
            print(f"    • {cache_name:30s} ({file_count} items)")
        else:
            print(f"    • {cache_name:30s} (not found)")

    return True

def check_cloudStorage_paths():
    """Check for any metadata files in Google Drive CloudStorage paths"""
    print_header("GOOGLE DRIVE CLOUDSTORAGE CHECK")

    base_cloud_path = Path.home() / "Library" / "CloudStorage"

    if not base_cloud_path.exists():
        print_success("CloudStorage directory not found (Google Drive not mounted)")
        return True

    # Find Google Drive paths
    gdrive_paths = list(base_cloud_path.glob("GoogleDrive-*"))

    if not gdrive_paths:
        print_success("No Google Drive directories found in CloudStorage")
        return True

    print(f"Found {len(gdrive_paths)} Google Drive mount(s):")
    for gdrive_path in gdrive_paths:
        print(f"  • {gdrive_path.name}")

    # Check for 04_METADATA_SYSTEM directories
    metadata_dirs = []
    for gdrive_path in gdrive_paths:
        my_drive = gdrive_path / "My Drive"
        if my_drive.exists():
            # Find any 04_METADATA_SYSTEM directories
            for pattern in ["04_METADATA_SYSTEM*", "*04_METADATA_SYSTEM*"]:
                metadata_dirs.extend(my_drive.glob(pattern))

    if not metadata_dirs:
        print_success("No 04_METADATA_SYSTEM directories found in CloudStorage")
        return True

    print_warning(f"Found {len(metadata_dirs)} metadata directory/directories in CloudStorage:")

    # Check for recent file modifications (within last hour)
    now = datetime.now()
    cutoff_time = now - timedelta(hours=1)
    recent_files = []

    for metadata_dir in metadata_dirs:
        print(f"\n  📁 {metadata_dir}")

        if metadata_dir.is_dir():
            # Check all files in this directory
            for file_path in metadata_dir.rglob('*'):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    # Check if modified recently (within last hour)
                    if mtime > cutoff_time:
                        recent_files.append((file_path, mtime))
                        print_error(f"    RECENT: {file_path.name} (modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")

    if recent_files:
        print_error(f"\n⚠️  CRITICAL: {len(recent_files)} file(s) modified in CloudStorage within last hour!")
        print_error("    Files are still being written to Google Drive!")
        print_error("    The local-only refactor is incomplete.")
        return False
    else:
        print_success(f"\n✓ No recent file modifications detected (older than 1 hour)")
        print_warning("  These are archived fossils from before the local-only refactor")
        return True

def main():
    """Main sanity check"""
    print_header("AI FILE ORGANIZER - LOCAL METADATA PATH SANITY CHECK")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # Check local metadata
        local_ok = check_local_metadata()

        # Check CloudStorage
        cloud_ok = check_cloudStorage_paths()

        # Final verdict
        print_header("FINAL VERDICT")

        if local_ok and cloud_ok:
            print_success("All checks passed!")
            print_success("Local metadata system is operational")
            print_success("No recent CloudStorage writes detected")
            return 0
        else:
            print_error("Sanity check FAILED!")
            if not local_ok:
                print_error("  • Local metadata system issue")
            if not cloud_ok:
                print_error("  • CloudStorage write detected (local-only refactor incomplete)")
            return 1

    except Exception as e:
        print_error(f"Script error: {e}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())
