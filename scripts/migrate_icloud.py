#!/usr/bin/env python3
"""
iCloud Drive to Google Drive Migration Script
Part of AI File Organizer

This script moves files from iCloud Drive to Google Drive with:
1. Automated Deduplication
2. Intelligent Classification
3. Hierarchical Organization
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from automated_deduplication_service import AutomatedDeduplicationService
from unified_classifier import UnifiedClassificationService
from hierarchical_organizer import HierarchicalOrganizer
from gdrive_integration import get_ai_organizer_root

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('icloud_migration.log')
    ]
)
logger = logging.getLogger(__name__)

class iCloudMigrator:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.base_dir = get_ai_organizer_root()
        
        logger.info("Initializing services...")
        self.deduplicator = AutomatedDeduplicationService(str(self.base_dir))
        self.classifier = UnifiedClassificationService()
        self.organizer = HierarchicalOrganizer()
        
        self.stats = {
            "scanned": 0,
            "moved": 0,
            "duplicates": 0,
            "errors": 0,
            "bytes_moved": 0
        }

    def migrate(self, source_path: str):
        source = Path(source_path).expanduser()
        if not source.exists():
            logger.error(f"Source path does not exist: {source}")
            return

        # Pre-index Google Drive to ensure we have a baseline for duplicates
        self.pre_index_gdrive()

        logger.info(f"Starting migration from: {source}")
        logger.info(f"Target Root: {self.base_dir}")
        if self.dry_run:
            logger.info("DRY RUN MODE: No files will be moved")

        # Walk through source directory
        for file_path in source.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                self.process_file(file_path)

        self.print_summary()

    def pre_index_gdrive(self):
        """Index Google Drive files to ensure we detect duplicates"""
        logger.info("Indexing Google Drive to ensure duplicate detection...")
        
        # Scan the entire Google Drive root
        gdrive_root = self.base_dir
        
        # Exclude system/metadata folders
        excluded_dirs = {
            ".Trash",
            ".git",
            "04_METADATA_SYSTEM"  # Legacy/Invalid path
        }
        
        count = 0
        if gdrive_root.exists():
            logger.info(f"Scanning entire Google Drive root: {gdrive_root}")
            
            # Walk the entire drive
            for file_path in gdrive_root.rglob('*'):
                # Skip directories
                if not file_path.is_file():
                    continue
                    
                # Skip hidden files
                if file_path.name.startswith('.'):
                    continue
                
                # Check if file is in an excluded directory
                # We check parts relative to root to be safe
                try:
                    rel_path = file_path.relative_to(gdrive_root)
                    if any(part in excluded_dirs for part in rel_path.parts):
                        continue
                except ValueError:
                    # Should not happen if we are walking root, but safe fallback
                    continue

                # Calculate hash to populate DB
                # Access the underlying BulletproofDeduplicator
                # This will now write to the LOCAL metadata DB thanks to our fix
                self.deduplicator.deduplicator.calculate_secure_hash(file_path)
                count += 1
                if count % 100 == 0:
                    print(f"   Indexed {count} files...", end='\r')
                    
        print(f"   ✅ Indexed {count} files from Google Drive.")

    def process_file(self, file_path: Path):
        self.stats["scanned"] += 1
        try:
            # 1. Check for duplicates
            # We check against the entire AI Organizer root (Google Drive)
            logger.info(f"Checking {file_path.name}...")
            
            # Use check_for_duplicates_before_move to check against common locations and target
            # Since we don't know the specific target yet, we check generally
            # But the service requires a target directory. We'll use the base_dir as a proxy for now
            # or better, just calculate hash and check if it exists in the system
            
            # Using internal method for broader check
            file_hash = self.deduplicator._calculate_file_hash(file_path)
            duplicates = self.deduplicator._find_duplicates_in_common_locations(file_hash, file_path)
            
            # Filter out the file itself if it was found
            duplicates = [d for d in duplicates if d.absolute() != file_path.absolute()]
            
            if duplicates:
                logger.warning(f"Duplicate found: {file_path.name} exists at {duplicates[0]}")
                self.stats["duplicates"] += 1
                # Option: Move to duplicates folder? For now, we skip to be safe/clean
                # Or better, move to a "Duplicates" folder in GDrive so user can verify and delete source
                if not self.dry_run:
                    dup_dir = self.base_dir / "99_STAGING_EMERGENCY" / "iCloud_Duplicates"
                    dup_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dup_dir / file_path.name))
                return

            # 2. Classify
            classification = self.classifier.classify_file(file_path)
            
            # Handle result format (dict or object)
            if isinstance(classification, dict):
                category = classification.get('category', 'unknown')
                confidence = classification.get('confidence', 0.0)
                suggested_filename = classification.get('suggested_filename', file_path.name)
                project = classification.get('project')
                episode = classification.get('episode')
            else:
                category = getattr(classification, 'category', 'unknown')
                confidence = getattr(classification, 'confidence', 0.0)
                suggested_filename = getattr(classification, 'suggested_filename', file_path.name)
                project = getattr(classification, 'project', None)
                episode = getattr(classification, 'episode', None)

            # 3. Determine Destination
            if confidence < 0.7:
                logger.info(f"Low confidence ({confidence:.2f}) for {file_path.name}. Moving to Manual Review.")
                relative_path = Path("99_TEMP_PROCESSING/Manual_Review")
            else:
                relative_path, _ = self.organizer.build_hierarchical_path(
                    base_category=category,
                    file_path=file_path,
                    project_override=project,
                    episode_override=episode
                )
            
            target_path = self.base_dir / relative_path / suggested_filename
            
            # Handle filename collisions at target
            counter = 1
            while target_path.exists():
                stem = Path(suggested_filename).stem
                suffix = Path(suggested_filename).suffix
                target_path = target_path.parent / f"{stem}_{counter}{suffix}"
                counter += 1

            # 4. Move
            logger.info(f"Moving to: {target_path} (Category: {category}, Conf: {confidence:.2f})")
            
            if not self.dry_run:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(target_path))
                self.stats["moved"] += 1
                self.stats["bytes_moved"] += file_path.stat().st_size

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats["errors"] += 1

    def print_summary(self):
        logger.info("="*50)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*50)
        logger.info(f"Files Scanned: {self.stats['scanned']}")
        logger.info(f"Files Moved:   {self.stats['moved']}")
        logger.info(f"Duplicates:    {self.stats['duplicates']}")
        logger.info(f"Errors:        {self.stats['errors']}")
        logger.info(f"Data Moved:    {self.stats['bytes_moved'] / (1024*1024):.2f} MB")
        logger.info("="*50)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate iCloud Drive to Google Drive")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without moving files")
    parser.add_argument("--source", default="~/Library/Mobile Documents/com~apple~CloudDocs", help="Source directory")
    
    args = parser.parse_args()
    
    migrator = iCloudMigrator(dry_run=args.dry_run)
    migrator.migrate(args.source)
