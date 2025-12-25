#!/usr/bin/env python3
"""
Orchestrate Staging Workflow
Chains Drive Sync, Triage Scan, and Auto-Organization.
"""

import asyncio
import logging
import argparse
from pathlib import Path
import sys
import time
import json
import datetime as dt
from gdrive_integration import get_metadata_root
# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.services import SystemService, TriageService
from api.rollback_service import RollbackService
from universal_adaptive_learning import UniversalAdaptiveLearning

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Orchestrator")

def update_stats(processed, moved, skipped):
    try:
        stats_path = get_metadata_root() / "orchestration_stats.json"
        
        stats = {
            "last_run": dt.datetime.now().isoformat(),
            "files_processed": processed,
            "files_moved": moved,
            "files_skipped": skipped,
            "status": "running"
        }
        
        with open(stats_path, 'w') as f:
            json.dump(stats, f)
            
    except Exception as e:
        logger.error(f"Failed to sync stats: {e}")

def orchestrate(dry_run: bool = False, confidence_threshold: float = 0.80, scan_folder: str = None, recursive: bool = True):
    logger.info("🚀 Starting Staging Orchestration...")
    
    # 1. Initialize System Service (and Librarian)
    logger.info("Step 1: Initializing System Services...")
    try:
        librarian = SystemService.get_librarian()
        if not librarian:
            logger.error("Failed to initialize Librarian. Aborting.")
            return
    except Exception as e:
         logger.error(f"Error initializing services: {e}")
         return
        
    # 2. Drive Sync (if configured)
    logger.info("Step 2: Checking Google Drive Sync...")
    # In a real run, we might trigger a sync here
    # librarian.sync() 
    
    # 3. Determine Scan Targets
    logger.info("Step 3: Initializing Triage & Rollback Services...")
    rollback_service = RollbackService()
    triage_service = TriageService(rollback_service=rollback_service)
    
    scan_targets = []
    
    if scan_folder:
        custom_path = Path(scan_folder).resolve()
        if not custom_path.exists():
             logger.error(f"❌ Custom scan folder not found: {custom_path}")
             return
        logger.info(f"🎯 Targeted Scan: {custom_path}")
        scan_targets.append(custom_path)
    else:
        logger.info("📋 Scanning Default Staging Areas...")
        scan_targets = triage_service.staging_areas
    
    total_processed = 0
    total_moved = 0
    total_skipped = 0
    
    # Initial stats sync
    update_stats(0, 0, 0)
    
    for staging_area in scan_targets:
        if not staging_area.exists():
            continue
            
        logger.info(f"Scanning: {staging_area}")
        
        # Get all files
        if recursive:
            files = [f for f in staging_area.rglob('*') if f.is_file() and not f.name.startswith('.')]
        else:
            files = [f for f in staging_area.iterdir() if f.is_file() and not f.name.startswith('.')]
        
        for file_path in files:
            # Skip if file was already moved by another parallel process
            if not file_path.exists():
                continue

            # Skip sidecars (simple check: if it's a .json and there's a matching file or if it's in a .metadata folder)
            if file_path.suffix.lower() == '.json' and (file_path.parent / file_path.stem).exists():
                logger.info(f"Skipping potential sidecar: {file_path.name}")
                continue
            
            if '.metadata' in str(file_path):
                continue

            total_processed += 1
            
            # Update stats every file (or we could throttle)
            update_stats(total_processed, total_moved, total_skipped)
            
            try:
                # Double check existence before calling classifier (it might have been moved in the last few ms)
                if not file_path.exists():
                    continue
                    
                # Classify
                result = triage_service.classifier.classify_file(file_path)
                
                # Handle result format (dict or object)
                if isinstance(result, dict):
                    confidence = result.get('confidence', 0.0)
                    category = result.get('category', 'unknown')
                    reasoning = result.get('reasoning', [])
                else:
                    confidence = getattr(result, 'confidence', 0.0)
                    category = getattr(result, 'category', 'unknown')
                    reasoning = getattr(result, 'reasoning', [])
                
                logger.info(f"File: {file_path.name} | Category: {category} | Confidence: {confidence:.2f}")
                
                if confidence >= confidence_threshold:
                    if dry_run:
                        logger.info(f"  [DRY RUN] Would move to {category}")
                    else:
                        logger.info(f"  ✅ High confidence! Moving to {category}...")
                        move_result = triage_service.classify_file(
                            file_path=str(file_path),
                            confirmed_category=category
                        )
                        if move_result.get('status') == 'success':
                            total_moved += 1
                        else:
                            logger.error(f"  ❌ Failed to move: {move_result.get('message')}")
                else:
                    logger.info(f"  ⚠️ Low confidence. Leaving for manual review.")
                    total_skipped += 1
                    
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}")
                total_skipped += 1
                
    # Final stats sync
    try:
        stats_path = get_metadata_root() / "orchestration_stats.json"
        
        stats = {
            "last_run": dt.datetime.now().isoformat(),
            "files_processed": total_processed,
            "files_moved": total_moved,
            "files_skipped": total_skipped,
            "status": "completed"
        }
        
        with open(stats_path, 'w') as f:
            json.dump(stats, f)
    except:
        pass

    logger.info("-" * 50)
    logger.info(f"🏁 Orchestration Complete")
    logger.info(f"Total Files: {total_processed}")
    logger.info(f"Moved: {total_moved}")
    logger.info(f"Skipped (Needs Review): {total_skipped}")

    return {
        "files_processed": total_processed,
        "files_moved": total_moved,
        "files_skipped": total_skipped
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrate AI File Organization")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without moving files")
    parser.add_argument("--threshold", type=float, default=0.80, help="Confidence threshold for auto-move")
    parser.add_argument("--scan-folder", type=str, help="Specific folder to scan (overrides defaults)")
    parser.add_argument("--no-recursive", action="store_false", dest="recursive", help="Disable recursive scanning")
    
    args = parser.parse_args()
    
    orchestrate(
        dry_run=args.dry_run, 
        confidence_threshold=args.threshold,
        scan_folder=args.scan_folder,
        recursive=args.recursive
    )
