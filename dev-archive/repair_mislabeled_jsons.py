#!/usr/bin/env python3
"""
Repair Mislabeled JSON Files
---------------------------
Scans the Google Drive root for .json files that were incorrectly renamed 
by the AI (e.g. Docx files renamed to JSON). Uses the system 'file' utility
to detect true MIME types and suggests/performs renames.
"""

import os
import subprocess
import shutil
from pathlib import Path

# Mapping of MIME types to correct extensions
MIME_TO_EXT = {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/msword': '.doc',
    'text/plain': '.txt',
    'text/markdown': '.md',
    'text/html': '.html',
    'application/pdf': '.pdf',
    'application/zip': '.zip',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'video/mp4': '.mp4',
    'video/quicktime': '.mov',
}

DRIVE_ROOT = Path("/Users/ryanthomson/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive")

def get_actual_mime(file_path):
    """Use system 'file' command to get mime type with brief retry."""
    import time
    for attempt in range(2):
        try:
            result = subprocess.run(['file', '--mime-type', '-b', str(file_path)], 
                                   capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except:
            if attempt < 1:
                time.sleep(0.5)
                continue
            return None

def repair(dry_run=True):
    print(f"🔍 Scanning {DRIVE_ROOT} for mislabeled JSON files...")
    if dry_run:
        print("🚀 DRY RUN MODE: No files will be changed.")
    
    mislabeled_count = 0
    
    for root, dirs, files in os.walk(DRIVE_ROOT):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.lower().endswith('.json'):
                file_path = Path(root) / file
                
                # Check actual type
                mime = get_actual_mime(file_path)
                
                # If it's NOT a json file but is named .json
                if mime and mime != 'application/json':
                    # Special case: don't flag text/plain if it's actually valid JSON content
                    # (sometimes JSON is detected as text/plain by 'file')
                    if mime == 'text/plain':
                        try:
                            import json
                            with open(file_path, 'r') as f:
                                json.load(f)
                            continue # It's valid JSON
                        except:
                            pass # Not JSON content
                    
                    correct_ext = MIME_TO_EXT.get(mime)
                    if correct_ext:
                        mislabeled_count += 1
                        new_name = file_path.stem + correct_ext
                        new_path = file_path.parent / new_name
                        
                        print(f"[!] Mismatch: {file_path.relative_to(DRIVE_ROOT)}")
                        print(f"    Detected: {mime}")
                        print(f"    Suggested: {new_name}")
                        
                        if not dry_run:
                            try:
                                # Ensure we don't overwrite
                                if new_path.exists():
                                    print(f"    ⚠️  Skipping: Destination already exists: {new_name}")
                                else:
                                    shutil.move(str(file_path), str(new_path))
                                    print(f"    ✅ Renamed to {new_name}")
                            except Exception as e:
                                print(f"    ❌ Error renaming: {e}")

    print(f"\n--- Scan Complete ---")
    print(f"Found {mislabeled_count} mislabeled files.")

if __name__ == "__main__":
    import sys
    is_dry_run = "--fix" not in sys.argv
    repair(dry_run=is_dry_run)
    
    if is_dry_run:
        print("\nTo apply fixes, run: python3 repair_mislabeled_jsons.py --fix")
