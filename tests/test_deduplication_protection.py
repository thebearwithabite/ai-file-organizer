
import unittest
import tempfile
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator

class TestDeduplicationProtection(unittest.TestCase):
    def setUp(self):
        self.deduplicator = BulletproofDeduplicator()
        # Mock patterns and dirs to ensure consistent testing even if defaults change
        # (Though we are testing the implementation logic, so we rely on what's in the class)
        # But we should verify against REAL defaults too.

    def test_protected_extensions(self):
        """Verify that specific extensions are protected."""
        protected = [
            Path("/path/to/db.sqlite"),
            Path("/path/to/data.db"),
            Path("/path/to/model.pkl"),
            Path("/path/to/cache.pickle"),
            Path("/path/to/thing.sqlite3"),
        ]

        for p in protected:
            self.assertTrue(self.deduplicator.is_database_or_learned_data(p), f"Should protect {p}")

        unprotected = [
            Path("/path/to/image.jpg"),
            Path("/path/to/doc.pdf"),
            Path("/path/to/script.py"),
        ]

        for p in unprotected:
            self.assertFalse(self.deduplicator.is_database_or_learned_data(p), f"Should NOT protect {p}")

    def test_protected_keywords_in_path(self):
        """Verify that paths containing protected keywords are protected."""
        protected = [
            Path("/path/to/vector_db/index.json"),
            Path("/path/to/my_chroma_db/data.bin"),
            Path("/Users/me/_METADATA_SYSTEM/config.json"),
            Path("/system/adaptive_learning/memory.json"),
            Path("/project/learning_data/dataset.csv"),
            Path("/logs/classification_logs/today.log"),
            Path("/model/embeddings/vec.npy"),
            Path("/data/metadata/info.json"),
            Path("/path/to/_system/internal.db"),
        ]

        for p in protected:
            self.assertTrue(self.deduplicator.is_database_or_learned_data(p), f"Should protect {p}")

    def test_mixed_case_handling(self):
        """Verify that protection is case-insensitive."""
        protected = [
            Path("/PATH/TO/VECTOR_DB/DATA.TXT"),
            Path("/path/to/MeTaDaTa/file.txt"),
            Path("/path/to/file.DB"),
        ]

        for p in protected:
            self.assertTrue(self.deduplicator.is_database_or_learned_data(p), f"Should protect {p}")

    def test_index_protection(self):
        """Verify index protection logic."""
        # Original logic: 'index' in any part of path protects it.
        # This is quite aggressive.
        protected = [
            Path("/path/to/index/file.txt"),
            Path("/path/to/index.html"),
        ]

        for p in protected:
            self.assertTrue(self.deduplicator.is_database_or_learned_data(p), f"Should protect {p}")

    def test_safe_files(self):
        """Verify that truly safe files are not protected."""
        safe = [
            Path("/Users/me/Downloads/receipt.pdf"),
            Path("/Users/me/Documents/resume.docx"),
            Path("/Users/me/Pictures/vacation.jpg"),
            Path("/Users/me/Music/song.mp3"),
        ]

        for p in safe:
            self.assertFalse(self.deduplicator.is_database_or_learned_data(p), f"Should NOT protect {p}")
