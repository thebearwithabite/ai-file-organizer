#!/usr/bin/env python3
"""
AI Librarian Staging Orchestrator
--------------------------------
Orchestrates the Deduplication and Staging workflow for Google Drive cleanup.

Workflow:
1.  Search: Find unclassified/loose files in Google Drive Root.
2.  Stage: Move them to `99_TEMP_PROCESSING/GDrive_Root_Staging`.
3.  Scan: Trigger Triage Service to analyze them.
4.  Review: Fetch files needing review.
5.  Action: (Interactive) User confirms classification or move.

Usage:
    python3 scripts/orchestrate_staging.py
"""

import os
import sys
import shutil
import requests
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gdrive_integration import get_ai_organizer_root

API_BASE = "http://localhost:8000/api"

def get_gdrive_root_files() -> List[Path]:
    """
    Find loose files in Google Drive Root (excluding organized folders).
    This mimics the 'Search' step but uses direct file system access for reliability
    before the files are indexed.
    """
    root = get_ai_organizer_root()
    if not root or not root.exists():
        print("❌ Google Drive Root not found.")
        return []

    print(f"🔍 Scanning Google Drive Root: {root}")
    
    # Folders to exclude (Core Library + Staging)
    exclude_dirs = {
        '01_ACTIVE_PROJECTS', 
        '02_MEDIA_ASSETS', 
        '03_REFERENCE_LIBRARY', 
        '04_METADATA_SYSTEM',
        '99_TEMP_PROCESSING', 
        '99_STAGING_EMERGENCY',
        '.trash'
    }

    loose_files = []
    
    # Scan ONLY the root level (depth=1 equivalent)
    # We don't want to dig into random folders yet, just clean the surface.
    try:
        for item in root.iterdir():
            if item.is_file():
                if not item.name.startswith('.'):
                    loose_files.append(item)
            elif item.is_dir():
                if item.name not in exclude_dirs and not item.name.startswith('.'):
                    # It's a loose folder - we might want to process its contents or move the whole folder
                    # For now, let's stick to files in root to be safe
                    pass
    except Exception as e:
        print(f"❌ Error scanning root: {e}")

    return loose_files

def stage_files(files: List[Path]) -> int:
    """
    Move files to 00_INBOX_STAGING.
    """
    root = get_ai_organizer_root()
    staging_dir = root / "00_INBOX_STAGING"
    staging_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚚 Staging {len(files)} files to: {staging_dir.name}")
    
    count = 0
    for file_path in files:
        try:
            dest_path = staging_dir / file_path.name
            
            # Handle duplicates in staging
            if dest_path.exists():
                stem = dest_path.stem
                suffix = dest_path.suffix
                dest_path = staging_dir / f"{stem}_{count}{suffix}"
            
            shutil.move(str(file_path), str(dest_path))
            print(f"   Moved: {file_path.name}")
            count += 1
        except Exception as e:
            print(f"   ❌ Failed to move {file_path.name}: {e}")
            
    return count

def trigger_triage_scan():
    """
    Call API to trigger triage scan.
    """
    print("🔄 Triggering Triage Scan...")
    try:
        response = requests.post(f"{API_BASE}/triage/trigger_scan")
        response.raise_for_status()
        result = response.json()
        print(f"✅ Scan Complete. Found {result.get('files_found', 0)} files for review.")
        return result
    except Exception as e:
        print(f"❌ API Error (Trigger Scan): {e}")
        return None

def get_files_to_review():
    """
    Call API to get files for review.
    """
    print("📥 Fetching files for review...")
    try:
        response = requests.get(f"{API_BASE}/triage/files_to_review")
        response.raise_for_status()
        result = response.json()
        return result.get('files', [])
    except Exception as e:
        print(f"❌ API Error (Get Files): {e}")
        return []

def classify_file(file_data: Dict[str, Any], confirmed_category: str):
    """
    Call API to classify/move file.
    """
    print(f"🚀 Classifying: {file_data['file_name']} -> {confirmed_category}")
    try:
        payload = {
            "file_path": file_data['file_path'],
            "confirmed_category": confirmed_category
        }
        response = requests.post(f"{API_BASE}/triage/classify", json=payload)
        response.raise_for_status()
        print("   ✅ Success!")
        return True
    except Exception as e:
        print(f"   ❌ API Error (Classify): {e}")
        return False

def interactive_review(files: List[Dict[str, Any]]):
    """
    Interactive CLI for reviewing files.
    """
    if not files:
        print("✅ No files to review.")
        return

    print(f"\n📋 Interactive Review ({len(files)} files)")
    print("="*60)

    for i, file_data in enumerate(files):
        print(f"\n[{i+1}/{len(files)}] File: {file_data['file_name']}")
        print(f"   Path: {file_data['file_path']}")
        
        classification = file_data.get('classification', {})
        suggested = classification.get('category', 'Unknown')
        confidence = classification.get('confidence', 0.0)
        
        print(f"   🤖 AI Suggestion: {suggested} ({confidence*100:.1f}%)")
        print(f"   Reasoning: {classification.get('reasoning', 'N/A')}")
        
        action = input("   Action [ (a)ccept / (s)kip / (m)anual / (q)uit ]: ").lower().strip()
        
        if action == 'q':
            break
        elif action == 'a':
            classify_file(file_data, suggested)
        elif action == 'm':
            manual_cat = input("   Enter category: ").strip()
            if manual_cat:
                classify_file(file_data, manual_cat)
        elif action == 's':
            print("   Skipped.")
        else:
            print("   Invalid action. Skipped.")

def main():
    print("🤖 AI Librarian Staging Orchestrator")
    print("====================================")
    
    # 1. Search / Identify
    loose_files = get_gdrive_root_files()
    
    if loose_files:
        print(f"\nFound {len(loose_files)} loose files in Root.")
        confirm = input("Move these files to Staging? (y/n): ").lower().strip()
        if confirm == 'y':
            # 2. Stage
            staged_count = stage_files(loose_files)
            print(f"✅ Staged {staged_count} files.")
        else:
            print("Skipping staging.")
    else:
        print("✅ Google Drive Root is clean (no loose files).")

    # 3. Scan
    trigger_triage_scan()
    
    # print("\n⏸️  PAUSED: Stopping before Triage Scan as requested.")
    # print("   Ready to discuss File Tree structure.")
    # return

    # 4. Review
    files_to_review = get_files_to_review()
    
    # Filter for files in GDrive_Root_Staging only?
    # For now, review everything found.

    # All Folders off of Gdrive Root (My Drive) with the excetion of: 
    # files placed in zz_Excuded

    # that are not: 
    # - in the Staging folder(s), or 
    # - in the index .database AND filed in the library
    #  should be indexed, renamed and added to the database then moved to their permanent location by the AI Librarian.
    # Stray structures created by previous versions of this tool need to be checked against the hashes of the files in the Library annd either deleted or added to index and then the moved to their permanent location.

    # Identified local folders that need to be deduped, indexed and moved are:
   # - /Users/user/projects
   # -'/Users/user/Library/Mobile Documents/com~apple~CloudDocs'

   # The AL Librarian (classification system) is an  intelligent  procative always-watching learning  with vision and hearing capabilities allowing it  to take the the most logical and meaningful 
   # in the maintence and evolution of a knowledgebase that will explicitly separate my work and creative projects from personal filesAI training data and system metadata.
    # 5. Interactive Action
    interactive_review(files_to_review)

if __name__ == "__main__":
    main()
