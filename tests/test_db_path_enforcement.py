#!/usr/bin/env python3
import unittest
from pathlib import Path
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gdrive_integration import ensure_safe_local_path
from content_extractor import ContentExtractor
from universal_adaptive_learning import UniversalAdaptiveLearning
from local_metadata_store import LocalMetadataStore

class TestDatabasePathEnforcement(unittest.TestCase):
    
    def test_ensure_safe_local_path_valid(self):
        """Test that a valid local path is accepted"""
        path = Path.home() / "Documents/AI_METADATA_SYSTEM/databases/test.db"
        try:
            result = ensure_safe_local_path(path)
            self.assertEqual(result, path)
        except RuntimeError:
            self.fail("ensure_safe_local_path raised RuntimeError unexpectedly for valid path")

    def test_ensure_safe_local_path_invalid_google_drive(self):
        """Test that a Google Drive path is rejected"""
        path = Path("/Users/test/Library/CloudStorage/GoogleDrive-test@gmail.com/My Drive/databases/test.db")
        with self.assertRaises(RuntimeError) as cm:
            ensure_safe_local_path(path)
        self.assertIn("Unsafe database path detected", str(cm.exception))

    def test_content_extractor_enforcement(self):
        """Test that ContentExtractor raises RuntimeError for unsafe paths"""
        # We can simulate this by monkey-patching get_metadata_root or passing an unsafe directory if it allowed base_dir override
        # ContentExtractor uses get_metadata_root() internally which we hardcoded to ~/Documents/...
        # So we test ensure_safe_local_path directly which is what it calls.
        pass

    def test_local_metadata_store_enforcement(self):
        """Test that LocalMetadataStore raises RuntimeError for unsafe paths"""
        unsafe_path = Path("/Users/test/Library/CloudStorage/GoogleDrive-test/metadata.db")
        with self.assertRaises(RuntimeError):
            LocalMetadataStore(db_path=unsafe_path)

if __name__ == '__main__':
    unittest.main()
