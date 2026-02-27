
import time
import sqlite3
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
import sys
import os

# Add repo root to path
sys.path.append(os.getcwd())

# Mock get_metadata_root to use temp dir
import gdrive_integration
original_get_metadata_root = gdrive_integration.get_metadata_root

temp_dir = tempfile.mkdtemp()
def mock_get_metadata_root():
    return Path(temp_dir)

gdrive_integration.get_metadata_root = mock_get_metadata_root

from staging_monitor import StagingMonitor

def benchmark():
    print(f"Setting up benchmark in {temp_dir}...")
    monitor = StagingMonitor()

    # Generate 10,000 dummy file records
    num_files = 10000
    scan_results = {
        "downloads": []
    }

    print(f"Generating {num_files} dummy file records...")
    for i in range(num_files):
        scan_results["downloads"].append({
            "path": f"/Users/dummy/Downloads/file_{i}.txt",
            "name": f"file_{i}.txt",
            "size": 1024,
            "modified": datetime.now(),
            "created": datetime.now(),
            "hash": "dummy_hash"
        })

    # Pre-populate DB with half of them to simulate updates + inserts
    print("Pre-populating database with 50% of files...")
    with sqlite3.connect(monitor.db_path) as conn:
        for i in range(0, num_files, 2):
            file_path = f"/Users/dummy/Downloads/file_{i}.txt"
            conn.execute("""
                INSERT INTO file_tracking
                (file_path, file_hash, first_seen, last_modified, size_bytes, folder_location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                file_path, "old_hash", datetime.now(), datetime.now(), 1024, "downloads"
            ))

    print("Running update_tracking_database...")
    start_time = time.time()
    monitor.update_tracking_database(scan_results)
    end_time = time.time()

    duration = end_time - start_time
    print(f"Processed {num_files} files in {duration:.4f} seconds")
    print(f"Rate: {num_files/duration:.2f} files/sec")

    # Cleanup
    shutil.rmtree(temp_dir)
    gdrive_integration.get_metadata_root = original_get_metadata_root

if __name__ == "__main__":
    benchmark()
