#!/usr/bin/env python3
"""
Emergency Restore Script
Automates the recovery of core AI File Organizer databases from the legacy backup.
"""

import os
import shutil
from pathlib import Path

BACKUP_ROOT = Path("/Users/ryanthomson/Documents/Documents - MacBook Air (4)/AI_METADATA_SYSTEM")
LIVE_ROOT = Path("/Users/ryanthomson/AI_METADATA_SYSTEM")

CRITICAL_DBS = [
    "adaptive_learning.db",
    "metadata.db",
    "adaptive_rules.db",
    "content_index.db"
]

def restore():
    print("🚀 Starting Emergency Restore...")
    
    # 1. Ensure directories exist
    (LIVE_ROOT / "databases").mkdir(parents=True, exist_ok=True)
    
    # 2. Copy databases
    for db in CRITICAL_DBS:
        src = BACKUP_ROOT / "databases" / db
        dst = LIVE_ROOT / "databases" / db
        
        if src.exists():
            print(f"📦 Restoring {db}...")
            shutil.copy2(src, dst)
        else:
            print(f"⚠️  Backup not found for {db}")

    print("✅ Restore complete. Please restart the AI File Organizer server.")

if __name__ == "__main__":
    restore()
