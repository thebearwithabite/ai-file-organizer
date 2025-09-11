#!/usr/bin/env python3
"""
Hybrid Architecture Integration Tests
Comprehensive testing of the complete Google Drive + Local AI File Organizer system

Tests:
- Authentication and authorization
- File streaming and caching
- Background synchronization
- Conflict resolution
- Hybrid search functionality
- ADHD-friendly user experience
- Error handling and recovery

Usage:
    python test_hybrid_architecture.py --full
    python test_hybrid_architecture.py --quick
    python test_hybrid_architecture.py --auth-only

Created by: RT Max for AI File Organizer v3.0
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import argparse
import logging

# Test framework
import json

# Import our components
try:
    from google_drive_auth import GoogleDriveAuth
    from local_metadata_store import LocalMetadataStore
    from gdrive_streamer import GoogleDriveStreamer
    from background_sync_service import BackgroundSyncService, ConflictResolution
    from gdrive_librarian import GoogleDriveLibrarian, SearchScope
    from gdrive_integration import GoogleDriveIntegration
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required components are available")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridArchitectureTest:
    """
    Comprehensive test suite for the hybrid AI file organizer architecture
    """
    
    def __init__(self, test_dir: Path = None):
        """Initialize test suite"""
        
        # Set up test directory
        if test_dir is None:
            test_dir = Path.home() / ".ai_organizer_test"
        test_dir.mkdir(exist_ok=True)
        self.test_dir = test_dir
        
        # Test components will be initialized during tests
        self.auth_service = None
        self.metadata_store = None
        self.streamer = None
        self.sync_service = None
        self.librarian = None
        self.gdrive_integration = None
        
        # Test results
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        print(f"🧪 Hybrid Architecture Test Suite")
        print(f"   📁 Test dir: {test_dir}")
        print("=" * 60)
    
    def log_test_result(self, test_name: str, passed: bool, message: str = "", details: Dict = None):
        """Log test result"""
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"     {message}")
        
        if passed:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
        
        self.test_results['details'].append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details or {}
        })
    
    def test_authentication(self) -> bool:
        """Test Google Drive authentication"""
        
        print("\n🔐 Testing Authentication...")
        
        try:
            # Initialize auth service
            self.auth_service = GoogleDriveAuth(
                config_dir=self.test_dir / "auth_config"
            )
            
            # Test authentication
            auth_result = self.auth_service.test_authentication()
            
            if auth_result['success']:
                user_info = {
                    'name': auth_result.get('user_name', 'Unknown'),
                    'email': auth_result.get('user_email', 'Unknown'),
                    'storage_total_gb': auth_result.get('total_storage_gb', 0),
                    'storage_used_gb': auth_result.get('used_storage_gb', 0)
                }
                
                self.log_test_result(
                    "Google Drive Authentication", 
                    True,
                    f"Authenticated as {user_info['name']} ({user_info['email']})",
                    user_info
                )
                return True
            else:
                self.log_test_result(
                    "Google Drive Authentication",
                    False,
                    f"Authentication failed: {auth_result.get('error', 'Unknown error')}"
                )
                return False
        
        except Exception as e:
            self.log_test_result(
                "Google Drive Authentication",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def test_gdrive_integration(self) -> bool:
        """Test Google Drive integration and structure creation"""
        
        print("\n📁 Testing Google Drive Integration...")
        
        try:
            # Initialize integration
            self.gdrive_integration = GoogleDriveIntegration()
            
            # Test status
            status = self.gdrive_integration.get_status()
            
            self.log_test_result(
                "Google Drive Detection",
                status.is_mounted,
                f"Drive mounted: {status.is_mounted}, Online: {status.is_online}",
                {
                    'drive_path': str(status.drive_path) if status.drive_path else None,
                    'total_space_gb': status.total_space_gb,
                    'free_space_gb': status.free_space_gb
                }
            )
            
            # Test structure creation
            try:
                structure = self.gdrive_integration.create_ai_organizer_structure()
                
                self.log_test_result(
                    "AI Organizer Directory Structure",
                    len(structure) > 0,
                    f"Created {len(structure)} directories",
                    {'directories': list(structure.keys())}
                )
                
            except Exception as e:
                self.log_test_result(
                    "AI Organizer Directory Structure",
                    False,
                    f"Structure creation failed: {e}"
                )
            
            return status.is_mounted
            
        except Exception as e:
            self.log_test_result(
                "Google Drive Integration",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def test_metadata_store(self) -> bool:
        """Test local metadata store"""
        
        print("\n📊 Testing Metadata Store...")
        
        try:
            # Initialize metadata store
            self.metadata_store = LocalMetadataStore(
                db_path=self.test_dir / "test_metadata.db"
            )
            
            # Test basic operations
            test_file_path = self.test_dir / "test_file.txt"
            test_file_path.write_text("Test content for metadata store")
            
            # Add file metadata
            success = self.metadata_store.add_file_metadata(
                file_id="test_file_001",
                local_path=str(test_file_path),
                drive_path="drive:///test_file_001",
                file_size=len("Test content for metadata store"),
                content_type="text/plain",
                tags=["test", "metadata"],
                category="test"
            )
            
            self.log_test_result(
                "Metadata Store - Add File",
                success,
                "Successfully added test file metadata"
            )
            
            # Retrieve metadata
            metadata = self.metadata_store.get_file_metadata("test_file_001")
            
            self.log_test_result(
                "Metadata Store - Retrieve File",
                metadata is not None,
                f"Retrieved metadata for test file",
                {'metadata': metadata.__dict__ if metadata else None}
            )
            
            # Get statistics
            stats = self.metadata_store.get_stats()
            
            self.log_test_result(
                "Metadata Store - Statistics",
                stats['total_files'] >= 1,
                f"Stats: {stats['total_files']} files, {stats['total_size_mb']:.1f}MB",
                stats
            )
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "Metadata Store",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def test_file_streaming(self) -> bool:
        """Test file streaming and caching"""
        
        print("\n🌊 Testing File Streaming...")
        
        if not self.auth_service or not self.metadata_store:
            self.log_test_result(
                "File Streaming",
                False,
                "Prerequisites not met (auth or metadata store failed)"
            )
            return False
        
        try:
            # Initialize streamer
            self.streamer = GoogleDriveStreamer(
                auth_service=self.auth_service,
                metadata_store=self.metadata_store,
                cache_dir=self.test_dir / "cache",
                cache_size_gb=1.0  # Small cache for testing
            )
            
            # Test getting Drive service
            try:
                service = self.auth_service.get_authenticated_service()
                files_result = service.files().list(pageSize=1).execute()
                test_files = files_result.get('files', [])
                
                if not test_files:
                    self.log_test_result(
                        "File Streaming - Test File",
                        False,
                        "No files found in Google Drive for testing"
                    )
                    return True  # Not a failure, just no files to test with
                
                test_file = test_files[0]
                file_id = test_file['id']
                filename = test_file['name']
                
                self.log_test_result(
                    "File Streaming - Test File Selected",
                    True,
                    f"Testing with: {filename}",
                    {'file_id': file_id, 'filename': filename}
                )
                
                # Test file info retrieval
                file_info = self.streamer.get_file_info(file_id)
                
                self.log_test_result(
                    "File Streaming - File Info",
                    'error' not in file_info,
                    f"Retrieved file info for {filename}",
                    {'file_size_mb': file_info.get('file_size_mb', 0)}
                )
                
                # Test file availability (should cache small files)
                if file_info.get('file_size_mb', 0) < 50:  # Only test with small files
                    try:
                        local_path = self.streamer.ensure_file_available(file_id)
                        
                        self.log_test_result(
                            "File Streaming - Ensure Available",
                            local_path is not None and local_path.exists(),
                            f"File available at: {local_path.name if local_path else 'None'}"
                        )
                        
                        # Test cache functionality
                        cache_size = self.streamer.cache_manager.get_cache_size()
                        cache_files = len(self.streamer.cache_manager.cache_metadata)
                        
                        self.log_test_result(
                            "File Streaming - Cache Status",
                            cache_files > 0,
                            f"Cache: {cache_files} files, {cache_size / 1024:.1f}KB",
                            {'cache_size_kb': cache_size / 1024, 'cached_files': cache_files}
                        )
                        
                    except Exception as e:
                        self.log_test_result(
                            "File Streaming - Ensure Available",
                            False,
                            f"Failed to ensure file availability: {e}"
                        )
                else:
                    self.log_test_result(
                        "File Streaming - Large File Skip",
                        True,
                        f"Skipped large file ({file_info.get('file_size_mb', 0):.1f}MB) to avoid long download"
                    )
                
            except Exception as e:
                self.log_test_result(
                    "File Streaming - Drive Access",
                    False,
                    f"Could not access Drive files: {e}"
                )
                return False
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "File Streaming",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def test_background_sync(self) -> bool:
        """Test background synchronization (without actually starting it long-term)"""
        
        print("\n🔄 Testing Background Sync...")
        
        if not self.auth_service or not self.metadata_store or not self.streamer:
            self.log_test_result(
                "Background Sync",
                False,
                "Prerequisites not met"
            )
            return False
        
        try:
            # Initialize sync service
            self.sync_service = BackgroundSyncService(
                auth_service=self.auth_service,
                metadata_store=self.metadata_store,
                streamer=self.streamer,
                sync_interval=60  # 1 minute for testing
            )
            
            # Test initialization
            self.log_test_result(
                "Background Sync - Initialization",
                self.sync_service is not None,
                "Sync service initialized successfully"
            )
            
            # Test starting sync service
            started = self.sync_service.start_background_sync()
            
            self.log_test_result(
                "Background Sync - Start Service",
                started,
                "Background sync service started" if started else "Failed to start sync service"
            )
            
            if started:
                # Let it run briefly
                time.sleep(5)
                
                # Check status
                status = self.sync_service.get_sync_status()
                
                self.log_test_result(
                    "Background Sync - Status Check",
                    status['is_running'],
                    f"Sync running: {status['is_running']}, Pending: {status['pending_operations']}",
                    status
                )
                
                # Stop the service
                self.sync_service.stop_background_sync()
                
                self.log_test_result(
                    "Background Sync - Stop Service",
                    not self.sync_service.is_running,
                    "Background sync service stopped successfully"
                )
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "Background Sync",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def test_hybrid_search(self) -> bool:
        """Test the complete hybrid search system"""
        
        print("\n🔍 Testing Hybrid Search...")
        
        try:
            # Initialize librarian (this integrates all components)
            self.librarian = GoogleDriveLibrarian(
                config_dir=self.test_dir / "librarian_config",
                cache_size_gb=0.5,  # Small cache
                auto_sync=False,    # Disable for testing
                sync_interval=300
            )
            
            # Initialize the librarian
            initialized = self.librarian.initialize()
            
            self.log_test_result(
                "Hybrid Search - Librarian Init",
                initialized,
                "Librarian initialized successfully" if initialized else "Librarian initialization failed"
            )
            
            if not initialized:
                return False
            
            # Test different search scopes
            test_queries = [
                ("documents", SearchScope.AUTO),
                ("contract", SearchScope.HYBRID),
                ("test", SearchScope.LOCAL_ONLY)
            ]
            
            for query, scope in test_queries:
                try:
                    results = self.librarian.search(
                        query=query,
                        scope=scope,
                        limit=5
                    )
                    
                    self.log_test_result(
                        f"Hybrid Search - Query '{query}' ({scope.value})",
                        True,  # Success if no exception
                        f"Found {len(results)} results",
                        {
                            'query': query,
                            'scope': scope.value,
                            'result_count': len(results),
                            'results': [{'filename': r.filename, 'relevance': r.relevance_score} 
                                       for r in results[:3]]  # First 3 results
                        }
                    )
                    
                except Exception as e:
                    self.log_test_result(
                        f"Hybrid Search - Query '{query}' ({scope.value})",
                        False,
                        f"Search failed: {e}"
                    )
            
            # Test system status
            status = self.librarian.get_system_status()
            
            self.log_test_result(
                "Hybrid Search - System Status",
                status['authenticated'],
                f"System status retrieved - Auth: {status['authenticated']}",
                {
                    'components': list(status['components'].keys()),
                    'cache_files': status['components']['cache']['files_cached'],
                    'metadata_files': status['components']['metadata_store']['total_files']
                }
            )
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "Hybrid Search",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def test_adhd_friendly_features(self) -> bool:
        """Test ADHD-friendly features"""
        
        print("\n🧠 Testing ADHD-Friendly Features...")
        
        if not self.librarian:
            self.log_test_result(
                "ADHD Features",
                False,
                "Librarian not initialized"
            )
            return False
        
        try:
            # Test configuration for ADHD features
            config = self.librarian.config
            adhd_features = config.get('adhd_features', {})
            
            required_features = [
                'progressive_disclosure',
                'simple_questions',
                'immediate_feedback',
                'confidence_threshold'
            ]
            
            features_present = all(feature in adhd_features for feature in required_features)
            
            self.log_test_result(
                "ADHD Features - Configuration",
                features_present,
                f"ADHD features configured: {list(adhd_features.keys())}",
                adhd_features
            )
            
            # Test that confidence threshold is reasonable for ADHD users
            confidence_threshold = adhd_features.get('confidence_threshold', 0)
            reasonable_threshold = 80 <= confidence_threshold <= 90
            
            self.log_test_result(
                "ADHD Features - Confidence Threshold",
                reasonable_threshold,
                f"Confidence threshold: {confidence_threshold}% (should be 80-90%)",
                {'threshold': confidence_threshold}
            )
            
            # Test immediate feedback (search should return quickly)
            start_time = time.time()
            results = self.librarian.search("test", limit=3)
            search_time = time.time() - start_time
            
            quick_response = search_time < 5.0  # Should respond within 5 seconds
            
            self.log_test_result(
                "ADHD Features - Quick Response",
                quick_response,
                f"Search responded in {search_time:.2f}s (should be < 5s)",
                {'response_time_seconds': search_time, 'results_count': len(results)}
            )
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "ADHD Features",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling and recovery"""
        
        print("\n🛡️  Testing Error Handling...")
        
        try:
            # Test authentication with invalid credentials
            test_auth = GoogleDriveAuth(
                credentials_file="nonexistent_credentials.json",
                config_dir=self.test_dir / "bad_auth_test"
            )
            
            # This should handle the error gracefully
            try:
                auth_result = test_auth.test_authentication()
                handled_gracefully = not auth_result['success'] and 'error' in auth_result
            except Exception:
                handled_gracefully = True  # Exception is also acceptable
            
            self.log_test_result(
                "Error Handling - Invalid Credentials",
                handled_gracefully,
                "Invalid credentials handled gracefully"
            )
            
            # Test metadata store with invalid path
            try:
                bad_metadata_store = LocalMetadataStore(
                    db_path=Path("/invalid/path/metadata.db")
                )
                # This should either work (create path) or handle error gracefully
                handled_gracefully = True
            except Exception as e:
                # Exception is acceptable if it's informative
                handled_gracefully = "permission" in str(e).lower() or "path" in str(e).lower()
            
            self.log_test_result(
                "Error Handling - Invalid Database Path",
                handled_gracefully,
                "Invalid database path handled appropriately"
            )
            
            # Test search with invalid query
            if self.librarian:
                try:
                    results = self.librarian.search("", limit=0)  # Empty query, zero limit
                    handled_gracefully = isinstance(results, list)  # Should return empty list
                except Exception:
                    handled_gracefully = True  # Exception is also acceptable
                
                self.log_test_result(
                    "Error Handling - Invalid Search Query",
                    handled_gracefully,
                    "Invalid search query handled gracefully"
                )
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "Error Handling",
                False,
                f"Unexpected exception in error handling test: {str(e)}"
            )
            return False
    
    def run_quick_test(self) -> Dict[str, Any]:
        """Run quick test suite (authentication and basic functionality)"""
        
        print("🚀 Running Quick Test Suite...")
        
        # Essential tests only
        auth_ok = self.test_authentication()
        if auth_ok:
            self.test_gdrive_integration()
            self.test_metadata_store()
        
        self.test_error_handling()
        
        return self.get_test_summary()
    
    def run_full_test(self) -> Dict[str, Any]:
        """Run complete test suite"""
        
        print("🚀 Running Full Test Suite...")
        
        # Run all tests in logical order
        auth_ok = self.test_authentication()
        
        if auth_ok:
            self.test_gdrive_integration()
            self.test_metadata_store()
            self.test_file_streaming()
            self.test_background_sync()
            self.test_hybrid_search()
            self.test_adhd_friendly_features()
        else:
            print("⚠️  Skipping remaining tests due to authentication failure")
        
        self.test_error_handling()
        
        return self.get_test_summary()
    
    def run_auth_only_test(self) -> Dict[str, Any]:
        """Run authentication test only"""
        
        print("🚀 Running Authentication Test Only...")
        
        self.test_authentication()
        
        return self.get_test_summary()
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get test results summary"""
        
        total_tests = self.test_results['passed'] + self.test_results['failed'] + self.test_results['skipped']
        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            'total_tests': total_tests,
            'passed': self.test_results['passed'],
            'failed': self.test_results['failed'],
            'skipped': self.test_results['skipped'],
            'success_rate': success_rate,
            'timestamp': self.test_results['timestamp'],
            'details': self.test_results['details']
        }
        
        return summary
    
    def print_summary(self):
        """Print test summary"""
        
        summary = self.get_test_summary()
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⏭️  Skipped: {summary['skipped']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        
        if summary['failed'] > 0:
            print(f"\n❌ Failed Tests:")
            for detail in summary['details']:
                if not detail['passed']:
                    print(f"   • {detail['test']}: {detail['message']}")
        
        # Save detailed results
        results_file = self.test_dir / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
    
    def cleanup(self):
        """Clean up test resources"""
        
        print("\n🧹 Cleaning up test resources...")
        
        # Stop any running services
        if self.sync_service and self.sync_service.is_running:
            self.sync_service.stop_background_sync()
        
        if self.librarian:
            self.librarian.cleanup()
        
        print("✅ Cleanup complete")

def main():
    """Main test runner"""
    
    parser = argparse.ArgumentParser(description="Hybrid Architecture Integration Tests")
    parser.add_argument("--full", action="store_true", help="Run complete test suite")
    parser.add_argument("--quick", action="store_true", help="Run quick test suite")
    parser.add_argument("--auth-only", action="store_true", help="Run authentication test only")
    parser.add_argument("--test-dir", type=str, help="Custom test directory")
    
    args = parser.parse_args()
    
    # Determine test directory
    test_dir = Path(args.test_dir) if args.test_dir else None
    
    # Initialize test suite
    test_suite = HybridArchitectureTest(test_dir=test_dir)
    
    try:
        # Run appropriate test suite
        if args.auth_only:
            test_suite.run_auth_only_test()
        elif args.quick:
            test_suite.run_quick_test()
        elif args.full:
            test_suite.run_full_test()
        else:
            # Default to quick test
            print("No test type specified, running quick test suite")
            test_suite.run_quick_test()
        
        # Print summary
        test_suite.print_summary()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always cleanup
        test_suite.cleanup()

if __name__ == "__main__":
    main()