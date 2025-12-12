#!/usr/bin/env python3
"""
Safe Cleanup Script for 0-byte Duplicates
Part of AI File Organizer

Purpose:
1. Scan 99_STAGING_EMERGENCY/iCloud_Duplicates for 0-byte files
2. Verify valid copy exists in main library (Double Check)
3. DELETE the 0-byte file if safe
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from gdrive_integration import get_metadata_root, get_ai_organizer_root

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cleanup_duplicates.log')
    ]
)
logger = logging.getLogger(__name__)

class SafeCleanup:
    def __init__(self):
        self.metadata_root = get_metadata_root()
        self.gdrive_root = get_ai_organizer_root()
        self.db_path = self.metadata_root / "deduplication.db"
        self.duplicates_dir = self.gdrive_root / "99_STAGING_EMERGENCY" / "iCloud_Duplicates"
        
        self.stats = {
            "deleted": 0,
            "skipped": 0,
            "errors": 0
        }

    def cleanup(self):
        logger.info("Starting Safe Cleanup of 0-byte Duplicates...")
        
        if not self.duplicates_dir.exists():
            logger.error("Duplicates directory not found")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return

        for file_path in self.duplicates_dir.rglob('*'):
            if not file_path.is_file():
                continue
                
            # Only target 0-byte files
            if file_path.stat().st_size == 0:
                filename = file_path.name
                
                # Double check verification logic
                cursor.execute("""
                    SELECT file_path 
                    FROM file_hashes 
                    WHERE file_path LIKE ? AND file_path NOT LIKE ?
                """, (f"%/{filename}", "%/99_STAGING_EMERGENCY/%"))
                
                matches = cursor.fetchall()
                valid_copy_found = False
                
                for path_str, in matches:
                    path = Path(path_str)
                    if path.exists() and path.stat().st_size > 0:
                        valid_copy_found = True
                        break
                
                if valid_copy_found:
                    try:
                        file_path.unlink()
                        self.stats["deleted"] += 1
                        logger.info(f"🗑️ DELETED: {filename}")
                    except Exception as e:
                        self.stats["errors"] += 1
                        logger.error(f"Failed to delete {filename}: {e}")
                else:
                    self.stats["skipped"] += 1
                    logger.warning(f"⚠️ SKIPPED (At Risk): {filename}")

        conn.close()
        logger.info("="*50)
        logger.info(f"Cleanup Complete. Deleted: {self.stats['deleted']}, Skipped: {self.stats['skipped']}")

if __name__ == "__main__":
    cleaner = SafeCleanup()
    cleaner.cleanup()
