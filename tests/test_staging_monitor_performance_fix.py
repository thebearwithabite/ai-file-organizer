
import unittest
import sqlite3
import shutil
import tempfile
import json
from pathlib import Path
from datetime import datetime
import staging_monitor
from staging_monitor import StagingMonitor

class TestStagingMonitorEdgeCases(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.metadata_root = Path(self.test_dir)

        # Patch get_metadata_root
        self.original_get_metadata_root = staging_monitor.get_metadata_root
        staging_monitor.get_metadata_root = lambda: self.metadata_root

        self.monitor = StagingMonitor()

    def tearDown(self):
        staging_monitor.get_metadata_root = self.original_get_metadata_root
        shutil.rmtree(self.test_dir)

    def test_update_empty_results(self):
        """Test update with empty scan results"""
        scan_results = {"desktop": [], "downloads": []}
        try:
            self.monitor.update_tracking_database(scan_results)
        except Exception as e:
            self.fail(f"update_tracking_database raised exception on empty input: {e}")

    def test_update_new_files(self):
        """Test update with new files"""
        file_path = str(Path(self.test_dir) / "test.txt")
        Path(file_path).touch()

        scan_results = {
            "desktop": [{
                "path": file_path,
                "name": "test.txt",
                "size": 0,
                "modified": datetime.now(),
                "created": datetime.now(),
                "hash": "test_hash"
            }]
        }

        self.monitor.update_tracking_database(scan_results)

        with sqlite3.connect(self.monitor.db_path) as conn:
            cursor = conn.execute("SELECT file_path, file_hash FROM file_tracking")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], file_path)
            self.assertEqual(row[1], "test_hash")

    def test_update_existing_files(self):
        """Test update with existing files (modified)"""
        file_path = str(Path(self.test_dir) / "test.txt")
        Path(file_path).touch()

        # Insert initial record
        with sqlite3.connect(self.monitor.db_path) as conn:
            conn.execute("""
                INSERT INTO file_tracking
                (file_path, file_hash, first_seen, last_modified, size_bytes, folder_location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_path, "old_hash", datetime.now(), datetime.now(), 0, "desktop"))

        # Update with new hash
        scan_results = {
            "desktop": [{
                "path": file_path,
                "name": "test.txt",
                "size": 0,
                "modified": datetime.now(), # newer
                "created": datetime.now(),
                "hash": "new_hash"
            }]
        }

        self.monitor.update_tracking_database(scan_results)

        with sqlite3.connect(self.monitor.db_path) as conn:
            cursor = conn.execute("SELECT file_hash FROM file_tracking WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            self.assertEqual(row[0], "new_hash")

if __name__ == '__main__':
    unittest.main()
