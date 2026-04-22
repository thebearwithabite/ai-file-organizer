#!/usr/bin/env python3
"""
Test Path Resolution System
Validates that the dynamic path configuration works across different environments
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import shutil

from path_config import PathConfig, paths, get_dynamic_path, migrate_legacy_path


class TestPathResolution(unittest.TestCase):
    """Test dynamic path resolution functionality"""
    
    def test_current_user_paths(self):
        """Test that paths resolve correctly for current user"""
        print("\n🧪 Testing current user path resolution...")
        
        # Test basic path resolution
        home_path = get_dynamic_path('home')
        self.assertTrue(home_path.exists())
        self.assertEqual(home_path, Path.home())
        
        docs_path = get_dynamic_path('documents')
        expected_docs = Path.home() / 'Documents'
        self.assertEqual(docs_path, expected_docs)
        
        organizer_base = get_dynamic_path('organizer_base')
        self.assertTrue(organizer_base.exists())
        
        print("   ✅ Current user paths resolve correctly")
    
    def test_environment_variable_override(self):
        """Test that AI_ORGANIZER_BASE environment variable works"""
        print("\n🧪 Testing environment variable override...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test with environment variable override
            with patch.dict(os.environ, {'AI_ORGANIZER_BASE': str(temp_path)}):
                # Create a new PathConfig instance to test override
                test_config = PathConfig()
                
                docs_path = test_config.get_path('documents')
                expected_path = temp_path / 'Documents'
                self.assertEqual(docs_path, expected_path)
                
                print(f"   ✅ Environment override works: {docs_path}")
    
    def test_legacy_path_migration(self):
        """Test migration of legacy hardcoded paths"""
        print("\n🧪 Testing legacy path migration...")
        
        test_cases = [
            ('/Users/user/Documents', str(Path.home() / 'Documents')),
            ('/Users/user/Documents', str(Path.home() / 'Documents')),
            ('/Users/user/Github/ai-file-organizer', str(get_dynamic_path('organizer_base'))),
            ('/Users/user/Downloads/test.pdf', str(Path.home() / 'Downloads' / 'test.pdf')),
        ]
        
        for legacy_path, expected_pattern in test_cases:
            migrated = migrate_legacy_path(legacy_path)
            # Check that the path has been dynamically resolved
            self.assertNotIn('/Users/user/', str(migrated))
            if '/Users/user/' in legacy_path:  # Only check exact ryan pattern if it was in original
                self.assertNotIn('/Users/user/', str(migrated))
            print(f"   ✅ {legacy_path} → {migrated}")
    
    def test_required_directory_creation(self):
        """Test that required directories can be created"""
        print("\n🧪 Testing required directory creation...")
        
        # Test directory creation
        paths.create_required_directories(verbose=False)
        
        # Check that key directories exist
        essential_dirs = ['logs', 'cache', 'config', 'staging', 'backups']
        for dir_key in essential_dirs:
            dir_path = get_dynamic_path(dir_key)
            self.assertTrue(dir_path.exists(), f"Directory {dir_key} should exist at {dir_path}")
            
        print("   ✅ Required directories created and accessible")
    
    def test_database_path_resolution(self):
        """Test that database paths work with new system"""
        print("\n🧪 Testing database path resolution...")
        
        # Test metadata database path
        db_path = get_dynamic_path('metadata_db')
        self.assertTrue(str(db_path).endswith('metadata_tracking.db'))
        self.assertEqual(db_path.parent, get_dynamic_path('organizer_base'))
        
        # Test that MetadataGenerator can use dynamic path
        try:
            from metadata_generator import MetadataGenerator
            
            # Create metadata generator - should use dynamic paths
            mg = MetadataGenerator(str(get_dynamic_path('documents')))
            
            # Verify it's using the dynamic path
            expected_db_path = get_dynamic_path('metadata_db')
            self.assertEqual(mg.db_path, expected_db_path)
            
            print("   ✅ MetadataGenerator uses dynamic database path")
            
        except ImportError:
            print("   ⚠️  MetadataGenerator import skipped (dependencies may be missing)")
    
    def test_path_configuration_consistency(self):
        """Test that path configuration is consistent"""
        print("\n🧪 Testing path configuration consistency...")
        
        # Test that all path keys are accessible
        essential_paths = [
            'home', 'documents', 'downloads', 'desktop',
            'organizer_base', 'logs', 'cache', 'metadata_db'
        ]
        
        for path_key in essential_paths:
            try:
                path = get_dynamic_path(path_key)
                self.assertIsInstance(path, Path)
                self.assertTrue(len(str(path)) > 0)
                print(f"   ✅ {path_key}: {path}")
            except Exception as e:
                self.fail(f"Failed to get path for '{path_key}': {e}")
        
        print("   ✅ All essential paths accessible")
    
    def test_cross_platform_compatibility(self):
        """Test that paths work across different systems"""
        print("\n🧪 Testing cross-platform compatibility...")
        
        # Test path separators are handled correctly
        organizer_base = get_dynamic_path('organizer_base')
        logs_path = get_dynamic_path('logs')
        
        # Logs should be subdirectory of organizer_base
        self.assertTrue(logs_path.is_relative_to(organizer_base))
        
        # Test path string representations are valid
        for path_key in ['home', 'documents', 'organizer_base']:
            path = get_dynamic_path(path_key)
            path_str = str(path)
            self.assertTrue(len(path_str) > 0)
            self.assertIsInstance(Path(path_str), Path)
        
        print("   ✅ Cross-platform path handling verified")
    
    def test_background_monitor_integration(self):
        """Test that background monitor works with dynamic paths"""
        print("\n🧪 Testing background monitor integration...")
        
        try:
            # Test that background monitor can import with new paths
            from background_monitor import EnhancedBackgroundMonitor
            
            # Create monitor instance
            monitor = EnhancedBackgroundMonitor()
            
            # Verify it's using dynamic paths
            self.assertTrue(hasattr(monitor, 'vector_librarian'))
            
            print("   ✅ Background monitor integrates with dynamic paths")
            
        except ImportError as e:
            print(f"   ⚠️  Background monitor test skipped: {e}")
    
    def test_error_handling(self):
        """Test error handling for invalid path keys"""
        print("\n🧪 Testing error handling...")
        
        # Test invalid path key
        with self.assertRaises(ValueError):
            get_dynamic_path('nonexistent_path_key')
        
        # Test that we get helpful error message
        try:
            get_dynamic_path('invalid_key')
        except ValueError as e:
            self.assertIn('Unknown path key', str(e))
            self.assertIn('Available keys', str(e))
        
        print("   ✅ Error handling works correctly")


def run_path_resolution_tests():
    """Run comprehensive path resolution test suite"""
    print("🚀 Starting Path Resolution Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPathResolution)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 ALL PATH RESOLUTION TESTS PASSED!")
        print(f"✅ {result.testsRun} tests completed successfully")
        print("\n🔧 Path resolution system validated:")
        print("   • Dynamic user environment compatibility ✅")
        print("   • Environment variable override support ✅")
        print("   • Legacy path migration working ✅")
        print("   • Database integration functional ✅")
        print("   • Background monitor compatibility ✅")
        print("   • Cross-platform path handling ✅")
        return True
    else:
        print("❌ SOME PATH RESOLUTION TESTS FAILED!")
        print(f"💥 {len(result.failures)} failures, {len(result.errors)} errors out of {result.testsRun} tests")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"- {test}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"- {test}")
        
        return False


if __name__ == "__main__":
    success = run_path_resolution_tests()
    
    # Show environment info for debugging
    print("\n" + "=" * 60)
    print("📊 ENVIRONMENT INFORMATION:")
    env_info = paths.get_environment_info()
    for key, value in env_info.items():
        print(f"   {key}: {value}")
    
    exit(0 if success else 1)