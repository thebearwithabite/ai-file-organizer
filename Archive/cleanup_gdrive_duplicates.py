#!/usr/bin/env python3
"""
Cross-Directory Duplicate Cleanup
Finds local files that already exist in Google Drive staging and safely removes local copies

Usage:
    # DRY-RUN (safe, no deletions):
    python cleanup_gdrive_duplicates.py

    # EXECUTE (actually delete local duplicates):
    python cleanup_gdrive_duplicates.py --execute
"""

import sys
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bulletproof_deduplication import BulletproofDeduplicator

def main():
    parser = argparse.ArgumentParser(
        description='Clean local duplicates of files already in Google Drive'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete local duplicates (default is dry-run)'
    )

    args = parser.parse_args()

    # Google Drive staging directories (reference - never delete from these)
    gdrive_staging = [
        Path.home() / "Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive/99_STAGING_EMERGENCY",
        Path.home() / "Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive/99_TEMP_PROCESSING"
    ]

    # Local directories to clean (delete duplicates from these)
    local_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Documents"
    ]

    print("=" * 80)
    print("🧹 CROSS-DIRECTORY DUPLICATE CLEANUP")
    print("=" * 80)
    print()
    print("📁 Google Drive Reference Locations (NEVER DELETED):")
    for d in gdrive_staging:
        exists = "✅" if d.exists() else "❌"
        print(f"   {exists} {d}")
    print()
    print("💻 Local Directories to Clean:")
    for d in local_dirs:
        exists = "✅" if d.exists() else "❌"
        print(f"   {exists} {d}")
    print()

    if not args.execute:
        print("🔍 DRY-RUN MODE - No files will be deleted")
        print("   Add --execute flag to actually delete duplicates")
    else:
        print("⚠️  EXECUTE MODE - Local duplicates will be deleted!")
        response = input("\nType 'yes' to continue: ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return

    print()
    print("=" * 80)
    print()

    # Create deduplicator and run cleanup
    deduplicator = BulletproofDeduplicator()
    results = deduplicator.clean_local_duplicates_of_gdrive(
        gdrive_dirs=gdrive_staging,
        local_dirs=local_dirs,
        execute=args.execute
    )

    # Final summary
    print()
    if args.execute:
        print("✅ CLEANUP COMPLETE")
        print(f"   Deleted {results['deleted_files']} local duplicate files")
        print(f"   Freed {results['space_recoverable'] / (1024*1024):.1f} MB")
    else:
        print("🔍 DRY-RUN COMPLETE")
        print(f"   Found {results['duplicates_found']} local files that exist in Google Drive")
        print(f"   Could free {results['space_recoverable'] / (1024*1024):.1f} MB")
        print()
        print("   Run with --execute to actually delete these files")

    if results.get('errors'):
        print()
        print("⚠️  ERRORS:")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"   {error}")
        if len(results['errors']) > 10:
            print(f"   ... and {len(results['errors']) - 10} more errors")

if __name__ == "__main__":
    main()
