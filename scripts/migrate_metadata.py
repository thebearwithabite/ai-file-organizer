#!/usr/bin/env python3
"""
Migrate Metadata Script
Moves configuration, databases, and artifacts from legacy locations to the new
compliant AI_METADATA_SYSTEM structure.
"""

import os
import shutil
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from gdrive_integration import get_metadata_root

def migrate_file(src: Path, dst: Path, copy: bool = False):
    """Move or copy a file if source exists and dest doesn't"""
    if not src.exists():
        return
    
    if dst.exists():
        print(f"⚠️  Destination already exists, skipping: {dst.name}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if copy:
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            print(f"✅ Copied {src.name} -> {dst}")
        else:
            shutil.move(src, dst)
            print(f"✅ Moved {src.name} -> {dst}")
    except Exception as e:
        print(f"❌ Failed to migrate {src.name}: {e}")

def main():
    print("🚀 Starting Metadata Migration...")
    
    metadata_root = get_metadata_root()
    print(f"📂 Target Root: {metadata_root}")
    
    # 1. Migrate Configuration (Token)
    legacy_config = Path.home() / ".ai_organizer_config"
    target_config = metadata_root / "config"
    
    migrate_file(
        legacy_config / "google_drive_token.json",
        target_config / "google_drive_token.json",
        copy=True # Copy to be safe, easier to rollback
    )
    
    migrate_file(
        legacy_config / "credentials.json",
        target_config / "credentials.json",
        copy=True
    )
    
    # 2. Migrate Databases
    target_db = metadata_root / "databases"
    
    # - Rollback DB
    migrate_file(
        legacy_config / "rollback.db",
        target_db / "rollback.db"
    )
    
    # - File Metadata DB (Rename might be needed? old was file_metadata.db, new local_metadata_store uses metadata.db?)
    # Let's just move it as is, and user can rename if needed, or we might need logic.
    # But local_metadata_store.py uses metadata.db by default.
    # If file_metadata.db is the real one, we should rename it.
    if (legacy_config / "file_metadata.db").exists() and not (target_db / "metadata.db").exists():
        try:
            shutil.copy2(legacy_config / "file_metadata.db", target_db / "metadata.db")
            print(f"✅ Copied file_metadata.db -> {target_db}/metadata.db (Renamed)")
        except Exception as e:
            print(f"❌ Failed to copy file_metadata.db: {e}")
            
    # - Adaptive Learning DB
    legacy_learning = Path.home() / ".ai_file_organizer" / "databases"
    migrate_file(
        legacy_learning / "adaptive_learning.db",
        target_db / "adaptive_learning.db"
    )
    
    # 3. Migrate ChromaDB (Vector Store)
    migrate_file(
        legacy_config / "chroma_db",
        metadata_root / "chroma_db"
    )

    print("\n✅ Migration Check Complete.")
    print(f"   Verify files in {metadata_root}")

if __name__ == "__main__":
    main()
