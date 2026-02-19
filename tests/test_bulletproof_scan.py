import unittest
import tempfile
import os
import shutil
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator

class TestBulletproofScan(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir)
        self.deduplicator = BulletproofDeduplicator()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_scan_directory_correctness(self):
        """
        Verify that scan_directory correctly identifies duplicates
        and ignores unique files, ensuring the optimization doesn't break logic.
        """
        # 1. Unique File A (Size 100)
        file_a = self.base_dir / "unique_a.txt"
        with open(file_a, "wb") as f:
            f.write(os.urandom(100))

        # 2. Unique File B (Size 200)
        file_b = self.base_dir / "unique_b.txt"
        with open(file_b, "wb") as f:
            f.write(os.urandom(200))

        # 3. Duplicate Group C (Size 300, same content)
        content_c = os.urandom(300)
        file_c1 = self.base_dir / "dup_c1.txt"
        file_c2 = self.base_dir / "dup_c2.txt"
        with open(file_c1, "wb") as f:
            f.write(content_c)
        with open(file_c2, "wb") as f:
            f.write(content_c)

        # 4. Duplicate Group D (Size 400, same content)
        content_d = os.urandom(400)
        file_d1 = self.base_dir / "dup_d1.txt"
        file_d2 = self.base_dir / "dup_d2.txt"
        with open(file_d1, "wb") as f:
            f.write(content_d)
        with open(file_d2, "wb") as f:
            f.write(content_d)

        # 5. Size Collision (Size 400, different content)
        # Should be in same size group as D, but different hash
        content_e = os.urandom(400) # Different content
        file_e = self.base_dir / "collision_e.txt"
        with open(file_e, "wb") as f:
            f.write(content_e)

        # Run scan
        results = self.deduplicator.scan_directory(self.base_dir, execute=False)

        # Assertions
        # We expect 2 duplicate groups (C and D). E should not be a duplicate group.
        self.assertEqual(results["duplicate_groups"], 2, "Should find exactly 2 duplicate groups")

        # Verify total duplicates found (files marked as duplicates)
        # Group C has 2 files -> 2 duplicates found in list (or 1 extra copy depending on definition,
        # but results['duplicates_found'] usually counts all files in the group)
        # scan_directory implementation: results["duplicates_found"] += len(duplicate_group)
        # So C=2, D=2. Total = 4.
        self.assertEqual(results["duplicates_found"], 4)

        # Verify groups content
        groups = results["groups"]
        # We should have one group with size 300 and one with size 400
        sizes = sorted([g["total_size"] for g in groups])
        # total_size in group is sum of all files in group.
        # Group C: 300 * 2 = 600
        # Group D: 400 * 2 = 800
        self.assertEqual(sizes, [600, 800])

        # Verify file E is NOT in any group
        all_duplicate_paths = []
        for g in groups:
            for f in g["files"]:
                all_duplicate_paths.append(Path(f["path"]).name)

        self.assertIn("dup_c1.txt", all_duplicate_paths)
        self.assertIn("dup_c2.txt", all_duplicate_paths)
        self.assertIn("dup_d1.txt", all_duplicate_paths)
        self.assertIn("dup_d2.txt", all_duplicate_paths)
        self.assertNotIn("collision_e.txt", all_duplicate_paths)
        self.assertNotIn("unique_a.txt", all_duplicate_paths)

    def test_scan_directory_relative_path(self):
        """
        Verify scanning works with relative paths (regression test for cache key mismatch).
        """
        # Create a relative path test case
        # We need to change cwd to temp_dir to test relative paths
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)

            # Create duplicates in current directory
            with open("rel_dup_1.txt", "w") as f:
                f.write("duplicate content")
            with open("rel_dup_2.txt", "w") as f:
                f.write("duplicate content")

            # Scan current directory (".")
            results = self.deduplicator.scan_directory(Path("."), execute=False)

            # Should find 1 duplicate group
            self.assertEqual(results["duplicate_groups"], 1, "Should find duplicate group with relative path")
            self.assertEqual(results["duplicates_found"], 2)

        finally:
            os.chdir(original_cwd)

if __name__ == "__main__":
    unittest.main()
