#!/usr/bin/env python3
"""
Surgical JSON Restoration
--------------------------
Finds files with .txt or .md extensions that contain valid JSON 
and renames them back to .json. This undoes any incorrect repairs.
"""

import os
import json
import shutil
from pathlib import Path

DRIVE_ROOT = Path("/Users/ryanthomson/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive")

def is_valid_json(file_path):
    """Check if a file contains valid JSON."""
    try:
        # Read a chunk first to avoid loading huge non-json files
        with open(file_path, 'r', errors='ignore') as f:
            first_char = f.read(1).strip()
            if first_char not in ('{', '['):
                return False
            
            # Go back and try to load full content
            f.seek(0)
            json.load(f)
            return True
    except:
        return False

def restore():
    print(f"🕵️ Scanning for mislabeled text files in {DRIVE_ROOT}...")
    
    restored_count = 0
    
    # Extensions to check
    EXTS = ('.txt', '.md')
    
    for root, dirs, files in os.walk(DRIVE_ROOT):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.lower().endswith(EXTS):
                file_path = Path(root) / file
                
                if is_valid_json(file_path):
                    # Check if it was originally a JSON (usually suggested by its name or content)
                    # For safety, we only rename if the resulting name doesn't exist.
                    new_path = file_path.with_suffix('.json')
                    
                    if new_path.exists():
                        print(f"⚠️  Conflict: {new_path.name} already exists. Skipping.")
                        continue
                        
                    print(f"✅ Found Actual JSON: {file_path.relative_to(DRIVE_ROOT)}")
                    shutil.move(str(file_path), str(new_path))
                    restored_count += 1

    print(f"\n--- Restoration Complete ---")
    print(f"Restored {restored_count} files back to .json.")

if __name__ == "__main__":
    restore()
