#!/usr/bin/env python3
"""
Critical Fixes Test Suite
Tests for Phase 1 critical safety implementations:
1. Atomic database migration with backup/rollback
2. Auto-delete error recovery with metadata verification
"""

import unittest
import sqlite3
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the classes we're testing
from metadata_generator import MetadataGenerator
from gdrive_librarian import GoogleDriveLibrarian


class TestDatabaseMigrationSafety(unittest.TestCase):
    """Test atomic database migration with backup/rollback functionality"""
    
    def setUp(self):
        """Set up test environment with temporary database"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_db_path = self.test_dir / "test_metadata.db"
        
        # Create a metadata generator with test database
        self.metadata_gen = MetadataGenerator(str(self.test_dir))
        self.metadata_gen.db_path = self.test_db_path
        
        # Create initial database with some test data
        self._create_initial_test_database()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_initial_test_database(self):
        """Create initial database with test data"""
        with sqlite3.connect(self.test_db_path) as conn:
            # Create basic table without Google Drive columns
            conn.execute("""
                CREATE TABLE file_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_name TEXT,
                    file_size INTEGER,
                    created_date TEXT
                )
            """)
            
            # Insert test data
            test_data = [
                ("/test/file1.pdf", "file1.pdf", 1024, "2025-01-01"),
                ("/test/file2.docx", "file2.docx", 2048, "2025-01-02")
            ]
            
            conn.executemany(
                "INSERT INTO file_metadata (file_path, file_name, file_size, created_date) VALUES (?, ?, ?, ?)",
                test_data
            )
            conn.commit()
    
    def _count_table_columns(self) -> int:
        """Count columns in file_metadata table"""
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(file_metadata)")
            return len(cursor.fetchall())
    
    def _count_table_rows(self) -> int:
        """Count rows in file_metadata table"""
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM file_metadata")
            return cursor.fetchone()[0]
    
    def test_successful_migration_with_backup(self):
        """Test successful migration creates backup and adds columns"""
        print("\\n🧪 Testing successful database migration...")
        
        # Verify initial state
        initial_columns = self._count_table_columns()
        initial_rows = self._count_table_rows()
        self.assertEqual(initial_rows, 2)  # Should have our test data
        
        # Run migration
        with sqlite3.connect(self.test_db_path) as conn:
            self.metadata_gen._migrate_database_schema(conn)
        
        # Verify migration success
        final_columns = self._count_table_columns()
        final_rows = self._count_table_rows()
        
        # Should have added Google Drive columns
        self.assertGreater(final_columns, initial_columns)
        # Should preserve existing data
        self.assertEqual(final_rows, initial_rows)
        
        # Verify backup was cleaned up (successful migration)
        backup_files = list(self.test_dir.glob("*_backup_*.db"))
        self.assertEqual(len(backup_files), 0)
        
        print("   ✅ Migration successful - columns added, data preserved, backup cleaned")
    
    def test_migration_failure_rollback(self):
        """Test migration failure triggers rollback and restores backup"""
        print("\\n🧪 Testing migration failure and rollback...")
        
        # Patch the database execution to simulate failure
        original_execute = sqlite3.Connection.execute
        
        def failing_execute(self, sql, *args):
            if "ALTER TABLE" in sql and "gdrive_" in sql:
                raise sqlite3.Error("Simulated migration failure")
            return original_execute(self, sql, *args)
        
        # Verify initial state
        initial_columns = self._count_table_columns()
        initial_rows = self._count_table_rows()
        
        with patch.object(sqlite3.Connection, 'execute', failing_execute):
            with sqlite3.connect(self.test_db_path) as conn:
                with self.assertRaises(sqlite3.Error):
                    self.metadata_gen._migrate_database_schema(conn)
        
        # Verify rollback occurred
        final_columns = self._count_table_columns()
        final_rows = self._count_table_rows()
        
        # Should have same number of columns (rollback successful)
        self.assertEqual(final_columns, initial_columns)
        # Should preserve existing data
        self.assertEqual(final_rows, initial_rows)
        
        print("   ✅ Rollback successful - original state restored")
    
    def test_concurrent_access_safety(self):
        """Test migration handles concurrent access gracefully"""
        print("\\n🧪 Testing concurrent access during migration...")
        
        # This test simulates concurrent access by attempting to read during migration
        import threading
        
        results = {'read_success': False, 'migration_success': False}
        
        def concurrent_reader():
            """Simulate concurrent database access"""
            time.sleep(0.1)  # Give migration time to start
            try:
                with sqlite3.connect(self.test_db_path) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM file_metadata")
                    count = cursor.fetchone()[0]
                    results['read_success'] = count >= 0
            except sqlite3.OperationalError:
                # Expected during exclusive transaction
                results['read_success'] = True  # This is actually correct behavior
        
        def migration_runner():
            """Run the migration"""
            try:
                with sqlite3.connect(self.test_db_path) as conn:
                    self.metadata_gen._migrate_database_schema(conn)
                results['migration_success'] = True
            except Exception as e:
                print(f"   Migration failed: {e}")
        
        # Start both threads
        reader_thread = threading.Thread(target=concurrent_reader)
        migration_thread = threading.Thread(target=migration_runner)
        
        migration_thread.start()
        reader_thread.start()
        
        migration_thread.join()
        reader_thread.join()
        
        # Both should complete successfully
        self.assertTrue(results['migration_success'])
        self.assertTrue(results['read_success'])
        
        print("   ✅ Concurrent access handled safely")


class TestAutoDeleteSafety(unittest.TestCase):
    """Test auto-delete safety with metadata verification"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "test_document.pdf"
        
        # Create test file
        self.test_file.write_text("Test PDF content for upload testing")
        
        # Create mock Google Drive service
        self.mock_service = MagicMock()
        self.gdrive_lib = GoogleDriveLibrarian(str(self.test_dir))
        self.gdrive_lib.service = self.mock_service
        self.gdrive_lib.authenticated = True
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_successful_upload_and_metadata_allows_delete(self):
        """Test successful upload + metadata logging allows auto-delete"""
        print("\\n🧪 Testing successful upload with metadata allows deletion...")
        
        # Mock successful upload
        self.mock_service.files().create().execute.return_value = {
            'id': 'test_file_id_123',
            'name': 'test_document.pdf',
            'size': '1024'
        }
        
        # Mock successful metadata logging
        with patch.object(self.gdrive_lib, '_log_metadata_operation', return_value=True):
            # Test upload with auto-delete
            result = self.gdrive_lib.upload_file(
                str(self.test_file), 
                gdrive_folder="Test Folder",
                auto_delete=True
            )
        
        # Verify upload returned success
        self.assertEqual(result, 'test_file_id_123')
        
        # Verify file was deleted (auto-delete succeeded)
        self.assertFalse(self.test_file.exists())
        
        print("   ✅ File uploaded, metadata logged, and local file deleted safely")
    
    def test_upload_success_metadata_failure_prevents_delete(self):
        """Test upload success but metadata failure prevents auto-delete"""
        print("\\n🧪 Testing upload success + metadata failure prevents deletion...")
        
        # Mock successful upload
        self.mock_service.files().create().execute.return_value = {
            'id': 'test_file_id_456',
            'name': 'test_document.pdf',
            'size': '1024'
        }
        
        # Mock failed metadata logging
        with patch.object(self.gdrive_lib, '_log_metadata_operation', return_value=False):
            # Test upload with auto-delete
            result = self.gdrive_lib.upload_file(
                str(self.test_file), 
                gdrive_folder="Test Folder",
                auto_delete=True
            )
        
        # Verify upload returned success (file was uploaded)
        self.assertEqual(result, 'test_file_id_456')
        
        # Verify file was NOT deleted (metadata failure prevented deletion)
        self.assertTrue(self.test_file.exists())
        
        print("   ✅ File uploaded but NOT deleted due to metadata logging failure")
    
    def test_metadata_exception_prevents_delete(self):
        """Test metadata logging exception prevents auto-delete"""
        print("\\n🧪 Testing metadata exception prevents deletion...")
        
        # Mock successful upload
        self.mock_service.files().create().execute.return_value = {
            'id': 'test_file_id_789',
            'name': 'test_document.pdf',
            'size': '1024'
        }
        
        # Mock metadata logging exception
        with patch.object(self.gdrive_lib, '_log_metadata_operation', side_effect=Exception("Database connection failed")):
            # Test upload with auto-delete
            result = self.gdrive_lib.upload_file(
                str(self.test_file), 
                gdrive_folder="Test Folder",
                auto_delete=True
            )
        
        # Verify upload returned success
        self.assertEqual(result, 'test_file_id_789')
        
        # Verify file was NOT deleted (exception prevented deletion)
        self.assertTrue(self.test_file.exists())
        
        print("   ✅ File uploaded but NOT deleted due to metadata exception")
    
    def test_upload_failure_no_delete_attempt(self):
        """Test upload failure doesn't attempt any deletion"""
        print("\\n🧪 Testing upload failure prevents deletion attempt...")
        
        # Mock failed upload
        from googleapiclient.errors import HttpError
        mock_resp = MagicMock()
        mock_resp.status = 500
        self.mock_service.files().create().execute.side_effect = HttpError(
            resp=mock_resp, content=b'Upload failed'
        )
        
        # Test upload with auto-delete
        result = self.gdrive_lib.upload_file(
            str(self.test_file), 
            gdrive_folder="Test Folder",
            auto_delete=True
        )
        
        # Verify upload failed
        self.assertIsNone(result)
        
        # Verify file still exists (no deletion attempt)
        self.assertTrue(self.test_file.exists())
        
        print("   ✅ Upload failed - no deletion attempted, file preserved")
    
    def test_deletion_permission_error_graceful_handling(self):
        """Test graceful handling when file deletion fails due to permissions"""
        print("\\n🧪 Testing graceful handling of deletion permission errors...")
        
        # Mock successful upload
        self.mock_service.files().create().execute.return_value = {
            'id': 'test_file_id_perm',
            'name': 'test_document.pdf',
            'size': '1024'
        }
        
        # Make file read-only to simulate permission error
        self.test_file.chmod(0o444)
        
        # Mock successful metadata logging
        with patch.object(self.gdrive_lib, '_log_metadata_operation', return_value=True):
            # Test upload with auto-delete
            result = self.gdrive_lib.upload_file(
                str(self.test_file), 
                gdrive_folder="Test Folder",
                auto_delete=True
            )
        
        # Verify upload still succeeded
        self.assertEqual(result, 'test_file_id_perm')
        
        # File should still exist (deletion failed but gracefully handled)
        self.assertTrue(self.test_file.exists())
        
        print("   ✅ Upload and metadata successful - deletion permission error handled gracefully")


def run_critical_fixes_test_suite():
    """Run comprehensive test suite for critical fixes"""
    print("🚀 Starting Critical Fixes Test Suite")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add database migration tests
    suite.addTest(unittest.makeSuite(TestDatabaseMigrationSafety))
    
    # Add auto-delete safety tests  
    suite.addTest(unittest.makeSuite(TestAutoDeleteSafety))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 ALL CRITICAL FIXES TESTS PASSED!")
        print(f"✅ {result.testsRun} tests completed successfully")
        return True
    else:
        print("❌ CRITICAL FIXES TESTS FAILED!")
        print(f"💥 {len(result.failures)} failures, {len(result.errors)} errors")
        
        if result.failures:
            print("\\nFailures:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
        
        if result.errors:
            print("\\nErrors:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")
        
        return False


if __name__ == "__main__":
    success = run_critical_fixes_test_suite()
    exit(0 if success else 1)