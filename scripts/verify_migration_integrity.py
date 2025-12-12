#!/usr/bin/env python3
"""
Migration Integrity Verification Script
Part of AI File Organizer

Purpose:
1. Scan 99_STAGING_EMERGENCY/iCloud_Duplicates for 0-byte files
2. Verify if a valid (non-zero byte) copy exists in the main Google Drive Library
3. Generate a report of "Safe to Delete" vs "At Risk" files
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

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
        logging.FileHandler('migration_verification.log')
    ]
)
logger = logging.getLogger(__name__)

class MigrationVerifier:
    def __init__(self):
        self.metadata_root = get_metadata_root()
        self.gdrive_root = get_ai_organizer_root()
        self.db_path = self.metadata_root / "deduplication.db"
        
        self.duplicates_dir = self.gdrive_root / "99_STAGING_EMERGENCY" / "iCloud_Duplicates"
        
        self.stats = {
            "scanned": 0,
            "zero_byte_files": 0,
            "safe_to_delete": 0,
            "at_risk": 0,
            "missing_from_db": 0
        }

    def verify(self):
        logger.info("Starting Migration Integrity Verification...")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Duplicates Dir: {self.duplicates_dir}")
        
        if not self.duplicates_dir.exists():
            logger.error(f"Duplicates directory not found: {self.duplicates_dir}")
            return

        # Connect to DB
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return

        report_lines = []
        report_lines.append("# Migration Integrity Report")
        report_lines.append(f"Date: {datetime.now().isoformat()}")
        report_lines.append("")
        report_lines.append("## At Risk Files (DO NOT DELETE)")
        report_lines.append("| Filename | Issue |")
        report_lines.append("|---|---|")

        # Scan for 0-byte files
        for file_path in self.duplicates_dir.rglob('*'):
            if not file_path.is_file():
                continue
                
            self.stats["scanned"] += 1
            
            # Check if 0-byte
            if file_path.stat().st_size == 0:
                self.stats["zero_byte_files"] += 1
                filename = file_path.name
                
                # Query DB for other copies of this file (by filename match since hash of 0-byte is useless)
                # We look for the file in the main library (not in duplicates folder)
                cursor.execute("""
                    SELECT file_path, secure_hash 
                    FROM file_hashes 
                    WHERE file_path LIKE ? AND file_path NOT LIKE ?
                """, (f"%/{filename}", "%/99_STAGING_EMERGENCY/%"))
                
                matches = cursor.fetchall()
                
                valid_copy_found = False
                valid_paths = []
                
                for path_str, file_hash in matches:
                    path = Path(path_str)
                    if path.exists() and path.stat().st_size > 0:
                        valid_copy_found = True
                        valid_paths.append(str(path))
                
                if valid_copy_found:
                    self.stats["safe_to_delete"] += 1
                    logger.info(f"✅ SAFE: {filename} -> Found valid copy at {valid_paths[0]}")
                else:
                    self.stats["at_risk"] += 1
                    issue = "No valid copy found in library" if not matches else "Library copy is also 0-bytes or missing"
                    logger.warning(f"❌ AT RISK: {filename} -> {issue}")
                    report_lines.append(f"| {filename} | {issue} |")
            
            if self.stats["scanned"] % 100 == 0:
                print(f"Scanned {self.stats['scanned']} files...", end='\r')

        conn.close()
        
        # Finish Report
        report_lines.append("")
        report_lines.append("## Summary")
        report_lines.append(f"- Total Scanned: {self.stats['scanned']}")
        report_lines.append(f"- Zero Byte Files: {self.stats['zero_byte_files']}")
        report_lines.append(f"- Safe to Delete: {self.stats['safe_to_delete']}")
        report_lines.append(f"- At Risk: {self.stats['at_risk']}")
        
        # Write Report
        report_path = project_root / "migration_integrity_report.md"
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_lines))
            
        logger.info("="*50)
        logger.info(f"Verification Complete. Report saved to {report_path}")
        logger.info(f"Safe to Delete: {self.stats['safe_to_delete']}")
        logger.info(f"At Risk: {self.stats['at_risk']}")

if __name__ == "__main__":
    verifier = MigrationVerifier()
    verifier.verify()
