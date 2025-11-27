#!/usr/bin/env python3
"""
System Health Check for AI File Organizer v3.1
Verifies the integrity of the Local-Only Architecture.
"""

import sys
import os
import sqlite3
import shutil
from pathlib import Path
import importlib.util

# Add project root to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

try:
    from gdrive_integration import get_metadata_root, get_ai_organizer_root
except ImportError:
    print("❌ Critical Error: Could not import gdrive_integration.py")
    sys.exit(1)

def check_path(path: Path, description: str, must_exist: bool = True, must_be_writable: bool = False) -> bool:
    """Check if a path exists and optionally if it is writable"""
    status = "✅"
    msg = f"{description} ({path})"
    
    if not path.exists():
        if must_exist:
            print(f"❌ Missing: {msg}")
            return False
        else:
            print(f"⚠️  Missing (Optional): {msg}")
            return True
            
    if must_be_writable:
        if not os.access(path, os.W_OK):
            print(f"❌ Not Writable: {msg}")
            return False
            
    print(f"{status} Found: {msg}")
    return True

def check_sqlite_db(db_path: Path) -> bool:
    """Check if SQLite database is accessible"""
    if not db_path.exists():
        print(f"⚠️  Database not found (will be created): {db_path.name}")
        return True
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        conn.close()
        print(f"✅ SQLite DB Healthy: {db_path.name}")
        return True
    except Exception as e:
        print(f"❌ SQLite DB Corrupt: {db_path.name} - {e}")
        return False

def check_chroma_db(db_path: Path) -> bool:
    """Check if ChromaDB is accessible"""
    if not db_path.exists():
        print(f"⚠️  Vector DB not found (will be created): {db_path.name}")
        return True
        
    try:
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        client.heartbeat()
        print(f"✅ ChromaDB Healthy: {db_path.name}")
        return True
    except Exception as e:
        print(f"❌ ChromaDB Error: {db_path.name} - {e}")
        return False

def main():
    print("🏥 AI File Organizer System Health Check")
    print("=" * 50)
    
    all_passed = True
    
    # 1. Check System Space
    print("\n1. Checking System Space (The Brain)...")
    metadata_root = get_metadata_root()
    if not check_path(metadata_root, "Metadata Root", must_be_writable=True):
        all_passed = False
    
    # Check Subdirectories
    dirs = ["databases", "vector_db", "content_cache"]
    for d in dirs:
        check_path(metadata_root / d, f"System Dir: {d}", must_exist=False)

    # 2. Check Databases
    print("\n2. Checking Databases...")
    if not check_sqlite_db(metadata_root / "metadata.db"):
        all_passed = False
    if not check_sqlite_db(metadata_root / "databases" / "content_index.db"):
        all_passed = False
    
    # Check Vector DB
    if not check_chroma_db(metadata_root / "vector_db"):
        all_passed = False

    # 3. Check Monitored Space
    print("\n3. Checking Monitored Space (The Body)...")
    organizer_root = get_ai_organizer_root()
    check_path(organizer_root, "Organizer Root")
    
    monitored_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Documents"
    ]
    
    for d in monitored_dirs:
        check_path(d, f"Monitored: {d.name}")

    # 4. Check Dependencies
    print("\n4. Checking Dependencies...")
    required_packages = ["chromadb", "watchdog", "fastapi", "uvicorn", "sqlite3"]
    for package in required_packages:
        if importlib.util.find_spec(package) is None and package != "sqlite3": # sqlite3 is stdlib
             print(f"❌ Missing Package: {package}")
             all_passed = False
        else:
             print(f"✅ Package Installed: {package}")

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ SYSTEM HEALTHY - Ready for Operation")
        sys.exit(0)
    else:
        print("❌ SYSTEM ISSUES DETECTED - Review errors above")
        sys.exit(1)

if __name__ == "__main__":
    main()
