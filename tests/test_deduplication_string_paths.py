
import unittest
import hashlib
import tempfile
import os
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator

class TestBulletproofDeduplicatorStringPaths(unittest.TestCase):
    def setUp(self):
        self.deduplicator = BulletproofDeduplicator()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_calculate_quick_hash_string(self):
        """Verify quick hash works with string path."""
        content = b"x" * 65536
        expected_hash = hashlib.md5(content).hexdigest()

        file_path = self.test_dir / "quick_test.txt"
        with open(file_path, "wb") as f:
            f.write(content)

        # Pass as string
        calculated_hash = self.deduplicator.calculate_quick_hash(str(file_path))
        self.assertEqual(calculated_hash, expected_hash)

    def test_calculate_secure_hash_string(self):
        """Verify secure hash works with string path."""
        content = b"Secure content for SHA-256 test"
        expected_hash = hashlib.sha256(content).hexdigest()

        file_path = self.test_dir / "secure_test.txt"
        with open(file_path, "wb") as f:
            f.write(content)

        # Pass as string
        calculated_hash = self.deduplicator.calculate_secure_hash(str(file_path))
        self.assertEqual(calculated_hash, expected_hash)

    def test_symlink_string(self):
        """Verify symlink handling with string path."""
        target = self.test_dir / "target.txt"
        with open(target, "w") as f:
            f.write("target")

        link = self.test_dir / "link.txt"
        try:
            os.symlink(target, link)
        except OSError:
            # Skip if symlinks not supported (e.g. some Windows envs without admin)
            return

        # Pass as string
        result = self.deduplicator.calculate_quick_hash(str(link))
        self.assertIsNone(result)

        result = self.deduplicator.calculate_secure_hash(str(link))
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
