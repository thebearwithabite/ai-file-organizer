import unittest
import sqlite3
import os
from pathlib import Path
from metadata_generator import MetadataGenerator

class TestMetadataGeneratorSQLInjection(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("/tmp/test_metadata_gen")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.generator = MetadataGenerator(base_dir=str(self.test_dir))
        # Point the db to a test file
        self.generator.db_path = self.test_dir / "test_metadata.db"
        self.generator._init_tracking_db()

    def tearDown(self):
        if self.generator.db_path.exists():
            self.generator.db_path.unlink()

    def test_save_file_metadata_ignores_malicious_keys(self):
        # Insert a record with malicious keys
        malicious_metadata = {
            'file_name': 'test.txt',
            'file_path': '/tmp/test_metadata_gen/test.txt',
            'malicious_col) VALUES (1); DROP TABLE file_metadata; --': 'value'
        }

        # Save metadata
        result = self.generator.save_file_metadata(malicious_metadata)
        self.assertTrue(result)

        # Verify table still exists and data was inserted cleanly
        with sqlite3.connect(self.generator.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_metadata'")
            self.assertIsNotNone(cursor.fetchone())

            cursor = conn.execute("SELECT file_name FROM file_metadata WHERE file_name='test.txt'")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 'test.txt')

if __name__ == '__main__':
    unittest.main()
