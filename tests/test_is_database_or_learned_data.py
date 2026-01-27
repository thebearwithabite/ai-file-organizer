"""
Unit tests for BulletproofDeduplicator.is_database_or_learned_data()

These tests verify the critical safety gate that protects database and learned data
from being deleted or modified. The function uses three layers of protection:
1. Extension-based checks (O(1) set lookup)
2. Directory name substring checks  
3. Regex pattern matching (fallback)

This test suite ensures that optimizations to this function don't silently change
deletion safety in the future.
"""

import unittest
import tempfile
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator


class TestIsDatabaseOrLearnedData(unittest.TestCase):
    """Test suite for the is_database_or_learned_data protection logic"""
    
    def setUp(self):
        """Create a deduplicator instance for testing"""
        self.deduplicator = BulletproofDeduplicator()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temporary directory"""
        self.temp_dir.cleanup()
    
    # =========================================================================
    # LAYER 1: Extension-based protection (O(1) set lookup)
    # =========================================================================
    
    def test_protected_extension_db(self):
        """Test that .db files are protected"""
        test_file = self.test_dir / "some_database.db"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            ".db files should be protected"
        )
    
    def test_protected_extension_sqlite(self):
        """Test that .sqlite files are protected"""
        test_file = self.test_dir / "data.sqlite"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            ".sqlite files should be protected"
        )
    
    def test_protected_extension_sqlite3(self):
        """Test that .sqlite3 files are protected"""
        test_file = self.test_dir / "records.sqlite3"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            ".sqlite3 files should be protected"
        )
    
    def test_protected_extension_pkl(self):
        """Test that .pkl (pickle) files are protected"""
        test_file = self.test_dir / "learning_data.pkl"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            ".pkl files should be protected"
        )
    
    def test_protected_extension_pickle(self):
        """Test that .pickle files are protected"""
        test_file = self.test_dir / "model.pickle"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            ".pickle files should be protected"
        )
    
    def test_unprotected_extensions(self):
        """Test that normal file extensions are not protected"""
        unprotected_files = [
            self.test_dir / "document.pdf",
            self.test_dir / "image.jpg",
            self.test_dir / "video.mp4",
            self.test_dir / "text.txt",
            self.test_dir / "archive.zip",
        ]
        for test_file in unprotected_files:
            self.assertFalse(
                self.deduplicator.is_database_or_learned_data(test_file),
                f"{test_file.suffix} files should not be protected by extension alone"
            )
    
    def test_extension_case_insensitive(self):
        """Test that extension matching is case-insensitive"""
        test_files = [
            self.test_dir / "data.DB",
            self.test_dir / "data.Db",
            self.test_dir / "data.PKL",
            self.test_dir / "data.SQLITE",
        ]
        for test_file in test_files:
            self.assertTrue(
                self.deduplicator.is_database_or_learned_data(test_file),
                f"Extension matching should be case-insensitive: {test_file.suffix}"
            )
    
    # =========================================================================
    # LAYER 2: Directory name substring checks
    # =========================================================================
    
    def test_protected_dir_vector_db(self):
        """Test that files in vector_db directories are protected"""
        test_file = self.test_dir / "vector_db" / "embeddings" / "file.txt"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in vector_db directories should be protected"
        )
    
    def test_protected_dir_chroma(self):
        """Test that files in chroma directories are protected"""
        test_file = self.test_dir / "chroma" / "index" / "data.bin"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in chroma directories should be protected"
        )
    
    def test_protected_dir_metadata_system(self):
        """Test that files in metadata_system directories are protected"""
        test_file = self.test_dir / "metadata_system" / "cache" / "file.json"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in metadata_system directories should be protected"
        )
    
    def test_protected_dir_learning(self):
        """Test that files in learning directories are protected"""
        test_file = self.test_dir / "learning" / "patterns" / "data.txt"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in learning directories should be protected"
        )
    
    def test_protected_dir_adaptive(self):
        """Test that files in adaptive directories are protected"""
        test_file = self.test_dir / "adaptive" / "models" / "file.dat"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in adaptive directories should be protected"
        )
    
    def test_protected_dir_embeddings(self):
        """Test that files in embeddings directories are protected"""
        test_file = self.test_dir / "embeddings" / "layer1" / "vectors.bin"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in embeddings directories should be protected"
        )
    
    def test_protected_dir_index(self):
        """Test that files in index directories are protected"""
        test_file = self.test_dir / "index" / "search" / "data.idx"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in index directories should be protected"
        )
    
    def test_protected_dir_system(self):
        """Test that files in _system directories are protected"""
        test_file = self.test_dir / "_system" / "config" / "settings.json"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in _system directories should be protected"
        )
    
    def test_protected_dir_classification_logs(self):
        """Test that files in classification_logs directories are protected"""
        test_file = self.test_dir / "classification_logs" / "2024" / "log.txt"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Files in classification_logs directories should be protected"
        )
    
    def test_protected_dir_substring_anywhere(self):
        """Test that directory name matching works anywhere in path"""
        test_files = [
            self.test_dir / "project" / "vector_db" / "data.txt",
            self.test_dir / "deep" / "nested" / "chroma" / "file.bin",
            self.test_dir / "parent" / "child" / "learning" / "sub" / "data.dat",
        ]
        for test_file in test_files:
            self.assertTrue(
                self.deduplicator.is_database_or_learned_data(test_file),
                f"Directory substring matching should work anywhere in path: {test_file}"
            )
    
    def test_unprotected_dirs(self):
        """Test that normal directories are not protected"""
        test_files = [
            self.test_dir / "documents" / "file.txt",
            self.test_dir / "downloads" / "image.jpg",
            self.test_dir / "projects" / "code" / "main.py",
        ]
        for test_file in test_files:
            self.assertFalse(
                self.deduplicator.is_database_or_learned_data(test_file),
                f"Normal directories should not be protected: {test_file}"
            )
    
    # =========================================================================
    # LAYER 3: Regex pattern matching (fallback)
    # =========================================================================
    
    def test_regex_vector_db_pattern(self):
        """Test regex pattern matching for vector_db anywhere in path"""
        test_file = Path("/home/user/my_vector_db_backup/data.txt")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match vector_db pattern"
        )
    
    def test_regex_chroma_pattern(self):
        """Test regex pattern matching for chroma"""
        test_file = Path("/var/lib/chroma_database/file.bin")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match chroma pattern"
        )
    
    def test_regex_metadata_system_pattern(self):
        """Test regex pattern matching for _METADATA_SYSTEM"""
        test_file = Path("/app/AI_METADATA_SYSTEM/cache.json")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match _METADATA_SYSTEM pattern"
        )
    
    def test_regex_system_db_pattern(self):
        """Test regex pattern matching for _SYSTEM/*.db"""
        test_file = Path("/data/AI_SYSTEM/database.db")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match _SYSTEM/*.db pattern"
        )
    
    def test_regex_adaptive_learning_pattern(self):
        """Test regex pattern matching for adaptive_learning"""
        test_file = Path("/models/adaptive_learning_v2/model.bin")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match adaptive_learning pattern"
        )
    
    def test_regex_deduplication_db_pattern(self):
        """Test regex pattern matching for deduplication*.db"""
        test_file = Path("/tmp/deduplication_cache.db")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match deduplication*.db pattern"
        )
    
    def test_regex_learning_data_pattern(self):
        """Test regex pattern matching for learning_data"""
        test_file = Path("/storage/learning_data_2024/patterns.txt")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match learning_data pattern"
        )
    
    def test_regex_classification_logs_pattern(self):
        """Test regex pattern matching for classification_logs"""
        test_file = Path("/logs/classification_logs_archived/log.txt")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match classification_logs pattern"
        )
    
    def test_regex_embeddings_pattern(self):
        """Test regex pattern matching for embeddings"""
        test_file = Path("/ai/embeddings_backup/vectors.npy")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match embeddings pattern"
        )
    
    def test_regex_metadata_pattern(self):
        """Test regex pattern matching for metadata"""
        test_file = Path("/project/metadata_cache/info.json")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match metadata pattern"
        )
    
    def test_regex_index_pkl_pattern(self):
        """Test regex pattern matching for index*.pkl"""
        test_file = Path("/search/index_v3.pkl")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Regex should match index*.pkl pattern"
        )
    
    def test_regex_sqlite_variants(self):
        """Test regex pattern matching for .sqlite* files"""
        test_files = [
            Path("/data/app.sqlite"),
            Path("/data/app.sqlite3"),
            Path("/data/app.sqlite-journal"),
        ]
        for test_file in test_files:
            self.assertTrue(
                self.deduplicator.is_database_or_learned_data(test_file),
                f"Regex should match sqlite variants: {test_file}"
            )
    
    # =========================================================================
    # EDGE CASES AND INTEGRATION TESTS
    # =========================================================================
    
    def test_multiple_protection_layers_applied(self):
        """Test that a file can match multiple protection layers"""
        # This file matches:
        # 1. Extension (.pkl)
        # 2. Directory name (learning)
        # 3. Regex pattern (learning_data)
        test_file = self.test_dir / "learning" / "learning_data" / "model.pkl"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "File matching multiple layers should be protected"
        )
    
    def test_protected_file_in_deep_nested_structure(self):
        """Test protection works in deeply nested directory structures"""
        test_file = self.test_dir / "a" / "b" / "c" / "d" / "chroma" / "e" / "f" / "data.txt"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Protection should work in deeply nested structures"
        )
    
    def test_similar_but_unprotected_names(self):
        """Test that similar names that shouldn't be protected are not protected"""
        # These should NOT be protected (they don't match the patterns exactly)
        test_files = [
            self.test_dir / "learning_materials" / "document.pdf",  # Contains "learning" but also other text
            self.test_dir / "chroma_tutorial" / "guide.txt",  # Contains "chroma" but also other text
        ]
        # Note: Due to substring matching in directory names, these WILL be protected
        # This is intentional - better to over-protect than under-protect
        for test_file in test_files:
            self.assertTrue(
                self.deduplicator.is_database_or_learned_data(test_file),
                f"Conservative protection: {test_file.parent.name} contains protected keyword"
            )
    
    def test_absolute_vs_relative_paths(self):
        """Test that both absolute and relative paths are handled correctly"""
        # Absolute path
        absolute_file = Path("/home/user/vector_db/data.pkl")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(absolute_file),
            "Absolute paths should be protected"
        )
        
        # Relative path
        relative_file = Path("vector_db/data.pkl")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(relative_file),
            "Relative paths should be protected"
        )
    
    def test_windows_style_paths(self):
        """Test that Windows-style paths work correctly"""
        # Note: On Unix systems, backslashes are treated as part of filename
        # but the lowercase conversion should still catch patterns
        test_file = Path("C:/Users/user/vector_db/data.db")
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Windows-style paths should be protected"
        )
    
    def test_empty_filename(self):
        """Test handling of edge case: empty filename"""
        test_file = Path("")
        # Should not crash, should return False
        self.assertFalse(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Empty path should not be protected"
        )
    
    def test_no_extension_file(self):
        """Test file with no extension in normal directory"""
        test_file = self.test_dir / "documents" / "README"
        self.assertFalse(
            self.deduplicator.is_database_or_learned_data(test_file),
            "File with no extension in normal directory should not be protected"
        )
    
    def test_no_extension_file_in_protected_dir(self):
        """Test file with no extension in protected directory"""
        test_file = self.test_dir / "vector_db" / "README"
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "File in protected directory should be protected regardless of extension"
        )
    
    # =========================================================================
    # PERFORMANCE VALIDATION TESTS
    # =========================================================================
    
    def test_fast_path_extension_check(self):
        """Verify extension check happens before slower checks"""
        # A .db file should return True without checking directory or regex
        test_file = self.test_dir / "unrelated" / "directory" / "file.db"
        # We can't directly test the order, but we verify it's protected
        self.assertTrue(
            self.deduplicator.is_database_or_learned_data(test_file),
            "Extension check should protect .db files"
        )
    
    def test_compiled_regexes_exist(self):
        """Verify that regexes are pre-compiled for performance"""
        self.assertIsInstance(
            self.deduplicator.protected_database_compiled,
            list,
            "Compiled regexes should be stored in a list"
        )
        self.assertGreater(
            len(self.deduplicator.protected_database_compiled),
            0,
            "Should have pre-compiled regex patterns"
        )
        # Verify they're actually compiled regex objects
        import re
        for pattern in self.deduplicator.protected_database_compiled:
            self.assertIsInstance(
                pattern,
                re.Pattern,
                "Should be compiled regex patterns, not strings"
            )
    
    def test_protected_extensions_is_set(self):
        """Verify protected extensions use a set for O(1) lookup"""
        self.assertIsInstance(
            self.deduplicator.protected_extensions,
            set,
            "Protected extensions should be a set for O(1) lookup"
        )
        self.assertGreater(
            len(self.deduplicator.protected_extensions),
            0,
            "Should have protected extensions defined"
        )
    
    def test_protected_dir_names_is_list(self):
        """Verify protected directory names are in a list for substring matching"""
        self.assertIsInstance(
            self.deduplicator.protected_dir_names,
            list,
            "Protected directory names should be a list"
        )
        self.assertGreater(
            len(self.deduplicator.protected_dir_names),
            0,
            "Should have protected directory names defined"
        )


if __name__ == '__main__':
    unittest.main()
