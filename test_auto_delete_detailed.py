#!/usr/bin/env python3
"""
Detailed Auto-Delete Safety Testing
Test specific scenarios for the auto-delete safety feature
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from gdrive_librarian import GoogleDriveLibrarian
from metadata_generator import MetadataGenerator

class AutoDeleteDetailedTester:
    """Detailed testing of auto-delete safety mechanisms"""
    
    def __init__(self):
        self.test_dir = None
        self.gdrive_lib = None
        self.test_results = []
    
    def setup_test_environment(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="auto_delete_detailed_"))
        self.gdrive_lib = GoogleDriveLibrarian(str(self.test_dir))
        
        # Create test file
        test_file = self.test_dir / "auto_delete_test.txt"
        test_file.write_text("Test content for auto-delete safety testing")
        
        return test_file
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   ℹ️  {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
    
    def test_metadata_logging_success_verification(self):
        """Test that metadata logging success is properly verified"""
        test_file = self.setup_test_environment()
        
        try:
            # Test successful metadata logging
            success = self.gdrive_lib._log_metadata_operation(
                test_file, "Test Folder", "document", 90.0, 1.0
            )
            
            if success:
                # Verify the metadata was actually saved
                metadata_gen = MetadataGenerator(str(self.test_dir))
                
                # Check database for the entry
                import sqlite3
                with sqlite3.connect(metadata_gen.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT gdrive_upload, gdrive_folder, gdrive_confidence, organization_status
                        FROM file_metadata WHERE file_path = ?
                    """, (str(test_file),))
                    result = cursor.fetchone()
                    
                    if result and result[0] == 1 and result[1] == "Test Folder" and result[2] == 90.0:
                        self.log_result("Metadata Logging Success Verification", True, 
                                       "Metadata logging returns True and database entry verified")
                    else:
                        self.log_result("Metadata Logging Success Verification", False, 
                                       f"Metadata logging returned True but database verification failed: {result}")
            else:
                self.log_result("Metadata Logging Success Verification", False, 
                               "Metadata logging returned False unexpectedly")
                
        except Exception as e:
            self.log_result("Metadata Logging Success Verification", False, f"Exception: {e}")
        
        finally:
            self.cleanup_test_environment()
    
    def test_metadata_logging_failure_detection(self):
        """Test that metadata logging failures are properly detected"""
        test_file = self.setup_test_environment()
        
        try:
            # Create a scenario where metadata logging should fail
            # Use an invalid path to cause the MetadataGenerator initialization to fail
            corrupted_lib = GoogleDriveLibrarian("/nonexistent/invalid/path")
            
            success = corrupted_lib._log_metadata_operation(
                test_file, "Test Folder", "document", 90.0, 1.0
            )
            
            if not success:
                self.log_result("Metadata Logging Failure Detection", True, 
                               "Metadata logging correctly returned False for invalid configuration")
            else:
                self.log_result("Metadata Logging Failure Detection", False, 
                               "Metadata logging should have failed but returned True")
                
        except Exception as e:
            self.log_result("Metadata Logging Failure Detection", True, 
                           f"Metadata logging correctly failed with exception: {type(e).__name__}")
        
        finally:
            self.cleanup_test_environment()
    
    def test_upload_logic_flow(self):
        """Test the upload logic flow for auto-delete safety"""
        test_file = self.setup_test_environment()
        
        # Mock the Google Drive service calls to simulate successful upload
        with patch.object(self.gdrive_lib, 'service') as mock_service:
            with patch.object(self.gdrive_lib, 'authenticated', True):
                with patch.object(self.gdrive_lib, 'get_drive_folders') as mock_get_folders:
                    
                    # Setup mocks
                    mock_get_folders.return_value = {"Test Folder": "folder_id_123"}
                    mock_create = MagicMock()
                    mock_create.execute.return_value = {
                        'id': 'uploaded_file_id_123',
                        'name': test_file.name,
                        'size': '100',
                        'createdTime': datetime.now().isoformat()
                    }
                    mock_service.files.return_value.create.return_value = mock_create
                    
                    # Test 1: Upload with auto_delete=True, metadata logging succeeds
                    print("\n🧪 Test Scenario 1: Upload success + Metadata success + Auto-delete enabled")
                    
                    # File should exist before upload
                    if not test_file.exists():
                        test_file.write_text("Test content restored")
                    
                    file_existed_before = test_file.exists()
                    
                    result = self.gdrive_lib.upload_file(str(test_file), 
                                                        gdrive_folder="Test Folder", 
                                                        auto_delete=True)
                    
                    file_exists_after = test_file.exists()
                    
                    if result and file_existed_before and not file_exists_after:
                        self.log_result("Auto-Delete Success Scenario", True, 
                                       "File uploaded and safely deleted after metadata logging success")
                    elif result and file_existed_before and file_exists_after:
                        self.log_result("Auto-Delete Success Scenario", False, 
                                       "File uploaded but not deleted (metadata logging may have failed)")
                    else:
                        self.log_result("Auto-Delete Success Scenario", False, 
                                       f"Upload failed or unexpected state: result={result}, before={file_existed_before}, after={file_exists_after}")
        
        self.cleanup_test_environment()
    
    def test_upload_without_auto_delete(self):
        """Test that files are preserved when auto_delete=False"""
        test_file = self.setup_test_environment()
        
        # Mock successful upload without auto-delete
        with patch.object(self.gdrive_lib, 'service') as mock_service:
            with patch.object(self.gdrive_lib, 'authenticated', True):
                with patch.object(self.gdrive_lib, 'get_drive_folders') as mock_get_folders:
                    
                    # Setup mocks
                    mock_get_folders.return_value = {"Test Folder": "folder_id_123"}
                    mock_create = MagicMock()
                    mock_create.execute.return_value = {
                        'id': 'uploaded_file_id_123',
                        'name': test_file.name,
                        'size': '100',
                        'createdTime': datetime.now().isoformat()
                    }
                    mock_service.files.return_value.create.return_value = mock_create
                    
                    file_existed_before = test_file.exists()
                    
                    result = self.gdrive_lib.upload_file(str(test_file), 
                                                        gdrive_folder="Test Folder", 
                                                        auto_delete=False)
                    
                    file_exists_after = test_file.exists()
                    
                    if result and file_existed_before and file_exists_after:
                        self.log_result("Auto-Delete Disabled Safety", True, 
                                       "File uploaded and preserved when auto_delete=False")
                    else:
                        self.log_result("Auto-Delete Disabled Safety", False, 
                                       f"Unexpected behavior: result={result}, before={file_existed_before}, after={file_exists_after}")
        
        self.cleanup_test_environment()
    
    def test_upload_failure_safety(self):
        """Test that files are preserved when upload fails"""
        test_file = self.setup_test_environment()
        
        # Test upload failure (no authentication)
        file_existed_before = test_file.exists()
        
        result = self.gdrive_lib.upload_file(str(test_file), auto_delete=True)
        
        file_exists_after = test_file.exists()
        
        if not result and file_existed_before and file_exists_after:
            self.log_result("Upload Failure Safety", True, 
                           "File preserved when upload fails (no authentication)")
        else:
            self.log_result("Upload Failure Safety", False, 
                           f"Unexpected behavior on upload failure: result={result}, before={file_existed_before}, after={file_exists_after}")
        
        self.cleanup_test_environment()
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def run_all_tests(self):
        """Run all auto-delete safety tests"""
        print("🛡️  DETAILED AUTO-DELETE SAFETY TESTING")
        print("=" * 60)
        
        self.test_metadata_logging_success_verification()
        self.test_metadata_logging_failure_detection()
        self.test_upload_logic_flow()
        self.test_upload_without_auto_delete()
        self.test_upload_failure_safety()
        
        # Summary
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        
        print(f"\n📊 DETAILED TEST SUMMARY")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed}")
        print(f"   Failed: {total - passed}")
        print(f"   Success Rate: {(passed/total*100):.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   • {result['test']}: {result['details']}")


def main():
    """Run detailed auto-delete safety tests"""
    tester = AutoDeleteDetailedTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()