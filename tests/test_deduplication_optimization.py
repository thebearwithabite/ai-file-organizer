import unittest
import os
import shutil
import hashlib
from pathlib import Path
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bulletproof_deduplication import BulletproofDeduplicator

class TestDeduplicationOptimization(unittest.TestCase):
    def setUp(self):
        self.deduplicator = BulletproofDeduplicator()
        self.test_dir = Path("test_dedup_opt")
        self.test_dir.mkdir(exist_ok=True)
        self.test_file_path = self.test_dir / "test_file.txt"
        self.content = b"test content for hashing"
        with open(self.test_file_path, "wb") as f:
            f.write(self.content)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_calculate_quick_hash_string(self):
        path_str = str(self.test_file_path)
        quick_hash = self.deduplicator.calculate_quick_hash(path_str)
        expected_hash = hashlib.md5(self.content).hexdigest()
        self.assertEqual(quick_hash, expected_hash)

    def test_calculate_quick_hash_path(self):
        quick_hash = self.deduplicator.calculate_quick_hash(self.test_file_path)
        expected_hash = hashlib.md5(self.content).hexdigest()
        self.assertEqual(quick_hash, expected_hash)

    def test_calculate_quick_hash_direntry(self):
        with os.scandir(self.test_dir) as it:
            for entry in it:
                if entry.name == "test_file.txt":
                    quick_hash = self.deduplicator.calculate_quick_hash(entry)
                    expected_hash = hashlib.md5(self.content).hexdigest()
                    self.assertEqual(quick_hash, expected_hash)
                    break

    def test_calculate_secure_hash_string(self):
        path_str = str(self.test_file_path)
        secure_hash = self.deduplicator.calculate_secure_hash(path_str)
        expected_hash = hashlib.sha256(self.content).hexdigest()
        self.assertEqual(secure_hash, expected_hash)

    def test_calculate_secure_hash_path(self):
        secure_hash = self.deduplicator.calculate_secure_hash(self.test_file_path)
        expected_hash = hashlib.sha256(self.content).hexdigest()
        self.assertEqual(secure_hash, expected_hash)

    def test_scan_directory_integration(self):
        # Create duplicate file
        dup_path = self.test_dir / "dup_file.txt"
        with open(dup_path, "wb") as f:
            f.write(self.content)

        results = self.deduplicator.scan_directory(self.test_dir)

        self.assertEqual(results["duplicates_found"], 2)
        self.assertEqual(results["duplicate_groups"], 1)
        self.assertEqual(len(results["groups"]), 1)

        # Check if paths in groups are strings
        group = results["groups"][0]
        files = group["files"]
        for f in files:
            self.assertIsInstance(f['path'], str)

if __name__ == '__main__':
    unittest.main()
