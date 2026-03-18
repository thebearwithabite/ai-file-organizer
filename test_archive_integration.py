#!/usr/bin/env python3
"""
Test Archive System Integration
Comprehensive testing of the enhanced archive organization system
Tests all components working together with ADHD-friendly validation
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json

# Add project to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Test imports (critical components only)
try:
    from path_config import paths, get_dynamic_path
    from archive_lifecycle_manager import ArchiveLifecycleManager
    from google_drive_migration import GoogleDriveMigrationAssistant
    from metadata_generator import MetadataGenerator
    from background_monitor import EnhancedBackgroundMonitor

    print("✅ Core components imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class ArchiveIntegrationTester:
    """
    Test suite for complete archive system integration
    Validates ADHD-friendly features and cross-component functionality
    """

    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.setup_test_environment()

    def setup_test_environment(self):
        """Create isolated test environment"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="archive_test_"))
        print(f"🧪 Test environment: {self.temp_dir}")

        # Create test directory structure
        test_dirs = [
            'test_documents',
            'test_downloads',
            'test_archive_source',
            'expected_output/01_ACTIVE_PROJECTS',
            'expected_output/02_ARCHIVE_HISTORICAL',
            'expected_output/03_REFERENCE_LIBRARY',
            'expected_output/04_TEMP_PROCESSING'
        ]

        for test_dir in test_dirs:
            (self.temp_dir / test_dir).mkdir(parents=True, exist_ok=True)

        # Create test files with different characteristics
        self.create_test_files()

    def create_test_files(self):
        """Create representative test files for different scenarios"""

        test_files = [
            # Entertainment industry files
            {
                'name': 'Client Name_Wolfhard_Contract_2024.pdf',
                'content': 'SAG-AFTRA Actor Agreement for Client Name Wolfhard. Stranger Things Season 5. Current active contract.',
                'age_days': 30,
                'category': 'entertainment_industry'
            },
            {
                'name': 'Stranger_Things_Contract_2022.pdf',
                'content': 'Completed agreement for Stranger Things Season 4. Final payment received. Contract executed.',
                'age_days': 450,
                'category': 'entertainment_industry'
            },

            # Financial documents
            {
                'name': 'Tax_Return_2024.pdf',
                'content': 'Annual tax return for 2024. Current year financial records. Outstanding refund.',
                'age_days': 60,
                'category': 'financial_documents'
            },
            {
                'name': 'Invoice_2022_Q3.pdf',
                'content': 'Quarterly invoice from 2022. Paid and completed. Historical financial record.',
                'age_days': 400,
                'category': 'financial_documents'
            },

            # Creative projects
            {
                'name': 'Papers_That_Dream_Episode_15.docx',
                'content': 'Draft script for Papers That Dream podcast episode 15. AI consciousness discussion. In progress.',
                'age_days': 5,
                'category': 'creative_projects'
            },
            {
                'name': 'Papers_That_Dream_Episode_10.docx',
                'content': 'Published episode 10 of Papers That Dream. Released and archived. Completed creative work.',
                'age_days': 200,
                'category': 'creative_projects'
            },

            # Reference materials
            {
                'name': 'Contract_Template_SAG.docx',
                'content': 'Standard SAG-AFTRA contract template. Reusable legal document template.',
                'age_days': 300,
                'category': 'reference'
            }
        ]

        for file_info in test_files:
            # Create file in test source directory
            file_path = self.temp_dir / 'test_archive_source' / file_info['name']

            with open(file_path, 'w') as f:
                f.write(file_info['content'])

            # Adjust file modification time to simulate age
            age_seconds = file_info['age_days'] * 24 * 3600
            old_time = time.time() - age_seconds
            os.utime(file_path, (old_time, old_time))

            print(f"📄 Created test file: {file_info['name']} ({file_info['age_days']} days old)")

    def test_path_configuration(self):
        """Test dynamic path configuration system"""

        print("\n🧪 Testing Path Configuration...")

        try:
            # Test environment variable override
            os.environ['AI_ORGANIZER_BASE'] = str(self.temp_dir)

            # Import path config with override
            from path_config import PathConfig
            test_config = PathConfig()

            # Verify paths resolve to test environment
            documents_path = test_config.get_path('documents')
            expected_path = self.temp_dir / 'Documents'

            if documents_path == expected_path:
                self.test_results.append("✅ Path configuration: Environment override works")
            else:
                self.test_results.append(f"❌ Path configuration: Expected {expected_path}, got {documents_path}")

            # Test directory creation
            created_count = test_config.create_required_directories(verbose=False)

            # Check if any directories were created or already exist
            logs_path = test_config.get_path('logs')
            if logs_path.exists() or created_count > 0:
                self.test_results.append("✅ Path configuration: Required directories created")
            else:
                self.test_results.append("❌ Path configuration: Required directories not created")

        except Exception as e:
            self.test_results.append(f"❌ Path configuration test failed: {e}")

    def test_archive_lifecycle_analysis(self):
        """Test archive lifecycle manager analysis"""

        print("\n🧪 Testing Archive Lifecycle Analysis...")

        try:
            # Initialize with test environment
            os.environ['AI_ORGANIZER_BASE'] = str(self.temp_dir)
            archive_manager = ArchiveLifecycleManager(str(self.temp_dir / 'test_archive_source'))

            # Test file analysis
            test_file = self.temp_dir / 'test_archive_source' / 'Client Name_Wolfhard_Contract_2024.pdf'
            analysis = archive_manager.analyze_file_lifecycle_stage(test_file)

            if 'error' not in analysis:
                self.test_results.append("✅ Archive analysis: File analysis completed")

                # Check ADHD importance scoring
                importance = analysis.get('adhd_importance', 0)
                if importance >= 7:  # Should be high for current Client Name contract
                    self.test_results.append(f"✅ Archive analysis: ADHD importance scoring works ({importance}/10)")
                else:
                    self.test_results.append(f"⚠️ Archive analysis: ADHD importance lower than expected ({importance}/10)")

                # Check lifecycle stage
                stage = analysis.get('lifecycle_stage', 'unknown')
                if stage == 'active':  # Current contract should be active
                    self.test_results.append("✅ Archive analysis: Lifecycle stage classification correct")
                else:
                    self.test_results.append(f"⚠️ Archive analysis: Expected 'active', got '{stage}'")

            else:
                self.test_results.append(f"❌ Archive analysis: {analysis['error']}")

            # Test archive suggestions
            suggestions = archive_manager.suggest_archive_actions(
                self.temp_dir / 'test_archive_source', limit=5
            )

            if suggestions:
                self.test_results.append(f"✅ Archive suggestions: Found {len(suggestions)} candidates")

                # Check for old files in suggestions
                old_file_found = any(s['age_days'] > 365 for s in suggestions)
                if old_file_found:
                    self.test_results.append("✅ Archive suggestions: Correctly identified old files")
                else:
                    self.test_results.append("⚠️ Archive suggestions: No old files identified")

            else:
                self.test_results.append("⚠️ Archive suggestions: No suggestions generated")

        except Exception as e:
            self.test_results.append(f"❌ Archive lifecycle test failed: {e}")

    def test_migration_assistant(self):
        """Test Google Drive migration assistant"""

        print("\n🧪 Testing Migration Assistant...")

        try:
            migration_assistant = GoogleDriveMigrationAssistant()

            # Test structure analysis
            analysis = migration_assistant.analyze_existing_structure(
                str(self.temp_dir / 'test_archive_source')
            )

            if 'error' not in analysis:
                self.test_results.append("✅ Migration: Structure analysis completed")

                total_files = analysis.get('total_files', 0)
                if total_files >= 5:  # We created 7 test files
                    self.test_results.append(f"✅ Migration: Found expected files ({total_files})")
                else:
                    self.test_results.append(f"⚠️ Migration: Expected more files, found {total_files}")

                # Check content categorization
                categories = analysis.get('content_categories', {})
                if categories.get('entertainment', 0) > 0:
                    self.test_results.append("✅ Migration: Content categorization works")
                else:
                    self.test_results.append("⚠️ Migration: Content categorization may need adjustment")

            else:
                self.test_results.append(f"❌ Migration: {analysis['error']}")

            # Test migration plan creation
            if 'error' not in analysis:
                plan = migration_assistant.create_migration_plan(analysis)

                if plan and 'phases' in plan:
                    self.test_results.append(f"✅ Migration: Plan created with {len(plan['phases'])} phases")

                    # Check ADHD-friendly batch sizes
                    max_batch = plan['adhd_guidelines']['max_files_per_session']
                    if max_batch <= 10:  # Should be manageable batch size
                        self.test_results.append(f"✅ Migration: ADHD-friendly batch size ({max_batch})")
                    else:
                        self.test_results.append(f"⚠️ Migration: Batch size may be too large ({max_batch})")

                else:
                    self.test_results.append("❌ Migration: Plan creation failed")

        except Exception as e:
            self.test_results.append(f"❌ Migration assistant test failed: {e}")

    def test_enhanced_search_integration(self):
        """Test enhanced search with archive context"""

        print("\n🧪 Testing Enhanced Search Integration...")

        try:
            # Test enhanced librarian availability

            # Test that the enhanced librarian file exists and has expected structure
            enhanced_lib_path = project_dir / 'enhanced_librarian.py'
            if enhanced_lib_path.exists():
                with open(enhanced_lib_path, 'r') as f:
                    content = f.read()

                # Check for key methods
                if 'def search(' in content:
                    self.test_results.append("✅ Enhanced search: Search method available")
                else:
                    self.test_results.append("⚠️ Enhanced search: Search method not found")

                if 'mode' in content and ('fast' in content or 'semantic' in content):
                    self.test_results.append("✅ Enhanced search: Multi-mode search support")
                else:
                    self.test_results.append("⚠️ Enhanced search: Search modes may be limited")

            else:
                self.test_results.append("❌ Enhanced search: Librarian file not found")

        except Exception as e:
            self.test_results.append(f"❌ Enhanced search test failed: {e}")

    def test_classification_rules_integration(self):
        """Test updated classification rules with archive lifecycle"""

        print("\n🧪 Testing Classification Rules Integration...")

        try:
            config_path = project_dir / 'classification_rules.json'

            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)

                # Check for archive lifecycle configuration
                if 'archive_lifecycle' in config:
                    self.test_results.append("✅ Classification: Archive lifecycle rules present")

                    # Check for ADHD-friendly settings
                    if 'adhd_friendly_settings' in config:
                        settings = config['adhd_friendly_settings']

                        max_questions = settings.get('max_questions_per_file', float('inf'))
                        if max_questions <= 3:
                            self.test_results.append("✅ Classification: ADHD-friendly question limit set")
                        else:
                            self.test_results.append("⚠️ Classification: Question limit may be too high")

                        if settings.get('use_visual_context', False):
                            self.test_results.append("✅ Classification: Visual context enabled")
                        else:
                            self.test_results.append("⚠️ Classification: Visual context disabled")

                    else:
                        self.test_results.append("⚠️ Classification: ADHD-friendly settings missing")

                    # Check enhanced folder mappings
                    folder_mappings = config.get('folder_mappings', {})
                    archive_mappings = [k for k in folder_mappings.keys() if 'archive' in k]

                    if archive_mappings:
                        self.test_results.append(f"✅ Classification: Archive folder mappings present ({len(archive_mappings)})")
                    else:
                        self.test_results.append("⚠️ Classification: Archive folder mappings missing")

                else:
                    self.test_results.append("❌ Classification: Archive lifecycle rules missing")

            else:
                self.test_results.append("❌ Classification: Rules file not found")

        except Exception as e:
            self.test_results.append(f"❌ Classification rules test failed: {e}")

    def test_applescript_files(self):
        """Test AppleScript UI files exist and have correct structure"""

        print("\n🧪 Testing AppleScript UI Integration...")

        try:
            # Check for enhanced AppleScript file
            applescript_path = project_dir / 'Enhanced_Archive_GUI.applescript'

            if applescript_path.exists():
                with open(applescript_path, 'r') as f:
                    content = f.read()

                # Check for visual context properties
                visual_indicators = ['SEARCH_ICON', 'ORGANIZE_ICON', 'ARCHIVE_ICON', 'ACTIVE_ICON', 'HISTORICAL_ICON']

                found_indicators = [indicator for indicator in visual_indicators if indicator in content]

                if len(found_indicators) >= 4:
                    self.test_results.append("✅ AppleScript: Visual context indicators present")
                else:
                    self.test_results.append(f"⚠️ AppleScript: Only {len(found_indicators)}/5 visual indicators found")

                # Check for archive management functions
                archive_functions = ['archiveManagement', 'migrationAssistant', 'formatArchiveResults']
                found_functions = [func for func in archive_functions if func in content]

                if len(found_functions) >= 2:
                    self.test_results.append("✅ AppleScript: Archive management functions present")
                else:
                    self.test_results.append(f"⚠️ AppleScript: Only {len(found_functions)}/3 archive functions found")

            else:
                self.test_results.append("❌ AppleScript: Enhanced Archive GUI file not found")

        except Exception as e:
            self.test_results.append(f"❌ AppleScript test failed: {e}")

    def test_adhd_friendly_features(self):
        """Test specific ADHD-friendly design features"""

        print("\n🧪 Testing ADHD-Friendly Features...")

        try:
            # Test batch size limitations
            migration_assistant = GoogleDriveMigrationAssistant()

            if migration_assistant.max_batch_size <= 10:
                self.test_results.append(f"✅ ADHD: Migration batch size appropriate ({migration_assistant.max_batch_size})")
            else:
                self.test_results.append(f"⚠️ ADHD: Migration batch size may be overwhelming ({migration_assistant.max_batch_size})")

            # Test pause between batches
            if migration_assistant.pause_between_batches >= 1:
                self.test_results.append(f"✅ ADHD: Pause between batches set ({migration_assistant.pause_between_batches}s)")
            else:
                self.test_results.append("⚠️ ADHD: No pause between batches")

            # Test archive manager importance scoring
            os.environ['AI_ORGANIZER_BASE'] = str(self.temp_dir)
            archive_manager = ArchiveLifecycleManager(str(self.temp_dir))

            # Test files should have varied importance scores
            test_file = self.temp_dir / 'test_archive_source' / 'Client Name_Wolfhard_Contract_2024.pdf'
            if test_file.exists():
                analysis = archive_manager.analyze_file_lifecycle_stage(test_file)

                if 'reasoning' in analysis and len(analysis['reasoning']) > 0:
                    self.test_results.append("✅ ADHD: Clear reasoning provided for decisions")
                else:
                    self.test_results.append("⚠️ ADHD: Decision reasoning may be unclear")

                if 'recommended_action' in analysis:
                    self.test_results.append("✅ ADHD: Clear action recommendations provided")
                else:
                    self.test_results.append("⚠️ ADHD: Action recommendations missing")

        except Exception as e:
            self.test_results.append(f"❌ ADHD features test failed: {e}")

    def run_all_tests(self):
        """Run complete test suite"""

        print("🚀 Starting Archive System Integration Tests")
        print("=" * 60)

        # Run all test categories
        self.test_path_configuration()
        self.test_archive_lifecycle_analysis()
        self.test_migration_assistant()
        self.test_enhanced_search_integration()
        self.test_classification_rules_integration()
        self.test_applescript_files()
        self.test_adhd_friendly_features()

        # Generate summary report
        self.generate_test_report()

    def generate_test_report(self):
        """Generate comprehensive test report"""

        print("\n" + "=" * 60)
        print("📊 ARCHIVE SYSTEM INTEGRATION TEST RESULTS")
        print("=" * 60)

        # Count results by status
        passed = sum(1 for result in self.test_results if result.startswith("✅"))
        warnings = sum(1 for result in self.test_results if result.startswith("⚠️"))
        failed = sum(1 for result in self.test_results if result.startswith("❌"))

        # Print summary
        print(f"📈 Test Summary:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ⚠️ Warnings: {warnings}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Total: {len(self.test_results)}")

        # Calculate success rate
        success_rate = (passed / len(self.test_results)) * 100 if self.test_results else 0

        print(f"\n🎯 Success Rate: {success_rate:.1f}%")

        # Print detailed results
        print(f"\n📋 Detailed Results:")
        for result in self.test_results:
            print(f"   {result}")

        # Overall assessment
        if success_rate >= 80:
            print(f"\n🎉 OVERALL ASSESSMENT: EXCELLENT")
            print("   The archive system integration is working well!")
            print("   ADHD-friendly features are properly implemented.")
        elif success_rate >= 60:
            print(f"\n✅ OVERALL ASSESSMENT: GOOD")
            print("   Most features working, some tuning recommended.")
            print("   Address warnings for optimal ADHD support.")
        else:
            print(f"\n⚠️ OVERALL ASSESSMENT: NEEDS WORK")
            print("   Several issues need attention before deployment.")
            print("   Focus on failed tests first.")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")

        if failed > 0:
            print("   🔧 Fix failed tests before using system")

        if warnings > 0:
            print("   📝 Review warnings to optimize ADHD-friendly features")

        print("   🧪 Run tests after making changes")
        print("   📊 Monitor system performance with real files")

        # Cleanup
        self.cleanup()

    def cleanup(self):
        """Clean up test environment"""

        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                print(f"\n🧹 Test environment cleaned up")
            except Exception as e:
                print(f"\n⚠️ Could not clean up test environment: {e}")

        # Reset environment variables
        if 'AI_ORGANIZER_BASE' in os.environ:
            del os.environ['AI_ORGANIZER_BASE']


def main():
    """Run archive integration tests"""

    tester = ArchiveIntegrationTester()

    try:
        tester.run_all_tests()
        return 0
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        tester.cleanup()
        return 1
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        tester.cleanup()
        return 1

if __name__ == "__main__":
    exit(main())