
import unittest
import tempfile
import shutil
import re
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator

class TestDeduplicationProtection(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dedup = BulletproofDeduplicator(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_protected_extensions_blocked(self):
        """Test that files with protected extensions are blocked."""
        # Database files
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("test.db")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("test.sqlite")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("test.sqlite3")))

        # Pickle files
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("model.pkl")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("data.pickle")))

        # Case insensitivity
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("TEST.DB")))

        # Unprotected extensions
        self.assertFalse(self.dedup.is_database_or_learned_data(Path("test.txt")))
        self.assertFalse(self.dedup.is_database_or_learned_data(Path("image.jpg")))

    def test_protected_directory_names_blocked(self):
        """Test that files within protected directories are blocked."""
        # Protected directories
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("vector_db/index.json")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("chroma/data.bin")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("metadata_system/config.json")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("learning/model.pt")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("adaptive/rules.json")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("embeddings/cache.bin")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("index/lookup.dat")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("_system/internal.dat")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("classification_logs/log.txt")))

        # Nested paths
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("path/to/vector_db/file.txt")))

        # Case insensitive
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("VECTOR_DB/index.json")))

    def test_protected_regex_patterns_blocked(self):
        """Test that files matching protected regex patterns are blocked."""
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("_METADATA_SYSTEM/file.txt")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("adaptive_learning_v1.json")))
        self.assertTrue(self.dedup.is_database_or_learned_data(Path("deduplication.db")))

    def test_safe_duplicate_patterns(self):
        """Test that safe duplicate patterns match correctly (case sensitive)."""
        # Matches - The original patterns are case sensitive regexes.
        # "Generated Image" matches "Generated Image..." but not "generated image..."

        # Find the compiled pattern for Generated Image
        gen_img_pattern = next(p for p in self.dedup.safe_duplicate_compiled if "Generated Image" in p.pattern)

        self.assertTrue(gen_img_pattern.match("Generated Image 123.jpeg"))
        self.assertFalse(gen_img_pattern.match("generated image 123.jpeg")) # Should fail due to casing

if __name__ == '__main__':
    unittest.main()
