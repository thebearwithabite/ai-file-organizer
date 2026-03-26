#!/usr/bin/env python3
"""
Migrate legacy patterns from adaptive_learning.db into adaptive_rules.db
"""

import sqlite3
import os
from pathlib import Path

def migrate_legacy_rules():
    base_dir = Path.home() / "AI_METADATA_SYSTEM" / "databases"
    learning_db = base_dir / "adaptive_learning.db"
    rules_db = base_dir / "adaptive_rules.db"

    if not learning_db.exists():
        print(f"❌ Legacy database not found: {learning_db}")
        return
        
    if not rules_db.exists():
        print(f"❌ New rules database not found: {rules_db}")
        return

    print("🔄 Connecting to databases...")
    try:
        with sqlite3.connect(rules_db) as rules_conn:
            # We use an ATTACH approach within python 
            rules_conn.execute(f"ATTACH DATABASE '{learning_db}' AS old_db")
            
            print(f"📦 Migrating legacy patterns from {learning_db.name} -> {rules_db.name}...")
            
            cursor = rules_conn.execute("""
                INSERT OR IGNORE INTO adaptive_rules (
                    rule_id, rule_type, trigger_conditions, action_definition, 
                    confidence_score, success_count, failure_count, 
                    created_date, last_used, is_active
                )
                SELECT 
                    pattern_id,
                    pattern_type,
                    trigger_conditions,
                    predicted_action,
                    confidence,
                    CAST(frequency * accuracy_rate AS INTEGER),
                    CAST(frequency * (1 - accuracy_rate) AS INTEGER),
                    last_seen,
                    last_seen,
                    1
                FROM old_db.patterns;
            """)
            rules_conn.commit()
            
            # Check how many were inserted
            count_cursor = rules_conn.execute("SELECT count(*) FROM adaptive_rules")
            count = count_cursor.fetchone()[0]
            
            print(f"✅ Migration successful! The new adaptive_rules.db now contains {count} active rules.")
            
    except sqlite3.OperationalError as e:
        if "readonly database" in str(e).lower() or "locked" in str(e).lower():
            print("\n❌ ERROR: Database is locked or readonly.")
            print("   Please STOP the running Uvicorn/FastAPI backend server first, then try again!")
        else:
            print(f"\n❌ SQLite Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    migrate_legacy_rules()
