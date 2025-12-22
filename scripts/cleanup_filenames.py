#!/usr/bin/env python3
"""
Cleanup Recursive Renaming Artifacts
Scans for files with pattern '_1_1_1...' and renames them back to original.
"""
from pathlib import Path
import re
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Cleanup")

# Path to clean
TARGET_DIR = Path("/Users/ryanthomson/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive/99_TEMP_PROCESSING/Manual_Review")

def cleanup_recursive_names(dry_run=True):
    logger.info(f"Scanning {TARGET_DIR}...")
    
    if not TARGET_DIR.exists():
        logger.error("Target directory not found!")
        return

    # Regex to catch the pattern: ends with multiple _1 sequences
    # e.g. name_1_1_1.ext
    # We look for (_\d+)+ before the suffix
    regex_pattern = re.compile(r'^(.*?)((?:_\d+){3,})(\.[^.]+)$')

    count = 0
    # Use rglob to scan recursively in subfolders
    for file_path in TARGET_DIR.rglob('*'):
        if not file_path.is_file():
            continue

        match = regex_pattern.match(file_path.name)
        if match:
            clean_name_base = match.group(1)
            suffix = match.group(3)
            # Remove any trailing _1 if it was part of the base but got caught? 
            # Actually group 1 is the prefix.
            
            # Construct clean name
            clean_name = f"{clean_name_base}{suffix}"
            new_path = TARGET_DIR / clean_name
            
            # Handle conflict if clean name already exists
            if new_path.exists():
                # If clean version exists, we might effectively have duplicates.
                # Logic: Compare sizes? Or just keep duplicate with proper counter?
                # For now, let's just log it.
                logger.warning(f"⚠️  Target exists: {clean_name} | Keeping: {file_path.name}")
                continue

            logger.info(f"Rename: {file_path.name} -> {clean_name}")
            
            if not dry_run:
                try:
                    file_path.rename(new_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to rename: {e}")
            else:
                count += 1
                
    logger.info(f"Found {count} files to clean.")
    if dry_run:
        logger.info("Run with dry_run=False to execute.")

if __name__ == "__main__":
    cleanup_recursive_names(dry_run=False)
