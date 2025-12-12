#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "file_rollback.db"

with sqlite3.connect(db_path) as conn:
    cursor = conn.execute("SELECT * FROM file_rollback ORDER BY operation_timestamp DESC")
    
    print("Debug: Raw database rows")
    for i, row in enumerate(cursor.fetchall()):
        print(f"Row {i}: length={len(row)}")
        for j, col in enumerate(row):
            print(f"  [{j}] = {repr(col)}")
        print()