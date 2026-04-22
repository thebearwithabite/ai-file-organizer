import unittest
from pathlib import Path
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bulletproof_deduplication import BulletproofDeduplicator

class TestDeduplicationProtection(unittest.TestCase):
    def setUp(self):
        self.deduplicator = BulletproofDeduplicator()

    def test_protected_extensions(self):
        protected_files = [
            "data.db",
            "test.sqlite",
            "db.sqlite3",
            "model.pkl",
            "data.pickle"
        ]
        for f in protected_files:
            self.assertTrue(
                self.deduplicator.is_database_or_learned_data(Path(f"/tmp/{f}")),
                f"File {f} should be protected"
            )

    def test_protected_directories(self):
        protected_paths = [
            "/home/user/vector_db/index.json",
            "/home/user/chroma/data.bin",
            "/home/user/project/metadata_system/config.xml",
            "/home/user/adaptive_learning/state.json",
            "/home/user/embeddings/vectors.bin",
            "/home/user/_SYSTEM/config.db",
            "/home/user/learning_data/dataset.csv",
            "/home/user/classification_logs/log.txt"
        ]
        for p in protected_paths:
            self.assertTrue(
                self.deduplicator.is_database_or_learned_data(Path(p)),
                f"Path {p} should be protected"
            )

    def test_unprotected_files(self):
        unprotected_files = [
            "/home/user/Documents/report.docx",
            "/home/user/Downloads/image.jpg",
            "/home/user/project/main.py",
            "/home/user/video.mp4"
        ]
        for f in unprotected_files:
            self.assertFalse(
                self.deduplicator.is_database_or_learned_data(Path(f)),
                f"File {f} should NOT be protected"
            )

    def test_case_insensitivity(self):
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(Path("/home/user/VECTOR_DB/data.bin")),
            "Protection should be case insensitive"
        )
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(Path("/home/user/data.DB")),
            "Extension check should be case insensitive"
        )

if __name__ == '__main__':
    unittest.main()
