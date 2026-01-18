
import unittest
import shutil
import tempfile
import hashlib
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator

class TestBulletproofDeduplicatorScan(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        self.dedup = BulletproofDeduplicator(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_file(self, path, content):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(content)

    def test_find_duplicates(self):
        content1 = b"unique content 1"
        content2 = b"duplicate content"
        content3 = b"unique content 2"

        self.create_file("file1.txt", content1)
        self.create_file("file2.txt", content2)
        self.create_file("subdir/file3.txt", content2) # Duplicate of file2
        self.create_file("subdir/file4.txt", content3)
        self.create_file("deep/nested/file5.txt", content2) # Another duplicate

        # Run scan
        results = self.dedup.scan_directory(self.root)

        self.assertEqual(results["scanned_files"], 5)
        self.assertEqual(results["duplicate_groups"], 1)
        self.assertEqual(results["duplicates_found"], 3)

        group = results["groups"][0]
        paths = [f['name'] for f in group['files']]
        self.assertIn("file2.txt", paths)
        self.assertIn("file3.txt", paths)
        self.assertIn("file5.txt", paths)
        self.assertNotIn("file1.txt", paths)

    def test_skip_hidden(self):
        self.create_file(".hidden.txt", b"content")
        self.create_file("normal.txt", b"content")

        results = self.dedup.scan_directory(self.root)
        self.assertEqual(results["scanned_files"], 1) # Only normal.txt

    def test_skip_bundles(self):
        self.create_file("Library.imovielibrary/config.plist", b"content")
        self.create_file("normal.txt", b"content")

        results = self.dedup.scan_directory(self.root)
        self.assertEqual(results["scanned_files"], 1)

if __name__ == '__main__':
    unittest.main()
