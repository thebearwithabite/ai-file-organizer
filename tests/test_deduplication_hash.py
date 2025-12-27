import unittest
import hashlib
import tempfile
import os
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator

class TestBulletproofDeduplicator(unittest.TestCase):
    def setUp(self):
        self.deduplicator = BulletproofDeduplicator()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_calculate_secure_hash_correctness(self):
        """Verify that calculate_secure_hash returns the correct SHA-256 hash."""
        content = b"Hello, World! This is a test for SHA-256."
        expected_hash = hashlib.sha256(content).hexdigest()

        file_path = self.test_dir / "test_file.txt"
        with open(file_path, "wb") as f:
            f.write(content)

        calculated_hash = self.deduplicator.calculate_secure_hash(file_path)
        self.assertEqual(calculated_hash, expected_hash)

    def test_calculate_secure_hash_large_file(self):
        """Verify hash for a file larger than the buffer size (64KB)."""
        # Create a file slightly larger than 64KB
        size = 65536 + 1024
        content = os.urandom(size)
        expected_hash = hashlib.sha256(content).hexdigest()

        file_path = self.test_dir / "large_test_file.bin"
        with open(file_path, "wb") as f:
            f.write(content)

        calculated_hash = self.deduplicator.calculate_secure_hash(file_path)
        self.assertEqual(calculated_hash, expected_hash)

    def test_calculate_secure_hash_empty_file(self):
        """Verify hash for an empty file."""
        content = b""
        expected_hash = hashlib.sha256(content).hexdigest()

        file_path = self.test_dir / "empty_file.bin"
        with open(file_path, "wb") as f:
            f.write(content)

        calculated_hash = self.deduplicator.calculate_secure_hash(file_path)
        self.assertEqual(calculated_hash, expected_hash)

if __name__ == '__main__':
    unittest.main()
