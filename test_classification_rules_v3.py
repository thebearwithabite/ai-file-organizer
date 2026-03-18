#!/usr/bin/env python3
"""
Test Classification Rules v3.0
Validates the enhanced classification system with real file patterns from User's ecosystem
Tests ADHD-friendly features and intelligent categorization
"""

import json
import tempfile
import time
import os
from pathlib import Path
from typing import Dict, List, Tuple

# Test imports
try:
    from classification_engine import FileClassificationEngine
    from path_config import paths
    print("✅ Classification engine components imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

class ClassificationRulesV3Tester:
    """Test suite for classification rules v3.0 with real file patterns"""

    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.setup_test_environment()

    def setup_test_environment(self):
        """Create isolated test environment with realistic test files"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="classification_test_"))
        print(f"🧪 Test environment: {self.temp_dir}")

        # Initialize classifier with test environment
        self.classifier = FileClassificationEngine(str(self.temp_dir))

        # Create realistic test files based on User's actual ecosystem
        self.create_realistic_test_files()

    def create_realistic_test_files(self):
        """Create test files based on actual patterns from User's file system"""

        # Real file patterns from User's ecosystem
        test_files = [
            # Entertainment Industry - Client Name Wolfhard specific
            {
                'name': 'Client Name_Wolfhard_Demo_Reel_2024.mov',
                'content': 'Client Name Wolfhard Demo Reel for 2024 submissions. Stranger Things footage. High priority casting material.',
                'category': 'entertainment_industry',
                'age_days': 15
            },
            {
                'name': 'Stranger_Things_Season_5_Contract.pdf',
                'content': 'SAG-AFTRA agreement for Client Name Wolfhard, Stranger Things Season 5. Netflix production. Current active contract.',
                'category': 'entertainment_industry',
                'age_days': 45
            },
            {
                'name': 'I-797_Approval_Notice_Client Name_2024.pdf',
                'content': 'USCIS Form I-797 Approval Notice for Client Name Wolfhard. O-1 Artist Visa extension approved.',
                'category': 'entertainment_industry',
                'age_days': 90
            },

            # Creative Projects - Papers That Dream
            {
                'name': 'Papers_That_Dream_Episode_23_Script.docx',
                'content': 'Papers That Dream podcast episode 23. AI consciousness and attention mechanisms. Research on LLMs.',
                'category': 'creative_projects',
                'age_days': 3
            },
            {
                'name': 'ElevenLabs_Client Name_Voice_Sample.mp3',
                'content': 'ElevenLabs voice synthesis sample. Client Name Wolfhard voice clone for creative projects.',
                'category': 'creative_projects',
                'age_days': 12
            },
            {
                'name': 'Papers_That_Dream_Audio_Episode_20.mp3',
                'content': 'Final audio for Papers That Dream episode 20. Published content. Ready for archive.',
                'category': 'creative_projects',
                'age_days': 180
            },

            # Financial Documents - Business Operations
            {
                'name': 'Refinery_Artist_Mgmt_LLC_Commission_Q3_2024.pdf',
                'content': 'Refinery Artist Management LLC commission report Q3 2024. Client Name Wolfhard residuals.',
                'category': 'financial_documents',
                'age_days': 30
            },
            {
                'name': 'Bank_Feed_September_2024_CAD.csv',
                'content': 'Canadian bank feed September 2024. Business account transactions. Refinery Management.',
                'category': 'financial_documents',
                'age_days': 20
            },
            {
                'name': 'Tax_Return_2023_Final.pdf',
                'content': 'Final tax return 2023. Filed and processed. Entertainment industry income.',
                'category': 'financial_documents',
                'age_days': 400
            },

            # Development Projects
            {
                'name': 'threads-downloader-v2.1.3.zip',
                'content': 'ThreadsExporter source code v2.1.3. React TypeScript project. Social media downloader.',
                'category': 'development_projects',
                'age_days': 60
            },
            {
                'name': 'package.json',
                'content': '{"name": "bear-threads-v3", "version": "1.0.0", "dependencies": {"react": "^18.0.0", "firebase": "^9.0.0"}}',
                'category': 'development_projects',
                'age_days': 10
            },

            # Visual Media
            {
                'name': 'ChatGPT_Generated_Image_UI_Mockup.png',
                'content': 'ChatGPT generated image for UI mockup. App interface design concept.',
                'category': 'visual_media',
                'age_days': 5
            },
            {
                'name': 'Screenshot_2024-09-01_Interface.png',
                'content': 'Screenshot of application interface. Development reference.',
                'category': 'visual_media',
                'age_days': 1
            }
        ]

        for file_info in test_files:
            # Create file
            file_path = self.temp_dir / file_info['name']

            with open(file_path, 'w') as f:
                f.write(file_info['content'])

            # Adjust age
            if file_info['age_days'] > 0:
                age_seconds = file_info['age_days'] * 24 * 3600
                old_time = time.time() - age_seconds
                os.utime(file_path, (old_time, old_time))

            print(f"📄 Created test file: {file_info['name']} ({file_info['age_days']} days old)")

    def test_keyword_classification(self):
        """Test keyword-based classification accuracy"""

        print("\n🧪 Testing Keyword Classification...")

        test_cases = [
            ('Client Name_Wolfhard_Demo_Reel_2024.mov', 'entertainment_industry'),
            ('Papers_That_Dream_Episode_23_Script.docx', 'creative_projects'),
            ('Refinery_Artist_Mgmt_LLC_Commission_Q3_2024.pdf', 'financial_documents'),
            ('threads-downloader-v2.1.3.zip', 'development_projects'),
            ('ChatGPT_Generated_Image_UI_Mockup.png', 'visual_media')
        ]

        correct_classifications = 0
        total_tests = len(test_cases)

        for filename, expected_category in test_cases:
            file_path = self.temp_dir / filename

            if file_path.exists():
                try:
                    result = self.classifier.classify_file(str(file_path))

                    if hasattr(result, 'primary_category'):
                        actual_category = result.primary_category
                    else:
                        actual_category = result.get('primary_category', 'unknown')

                    if actual_category == expected_category:
                        correct_classifications += 1
                        print(f"   ✅ {filename}: {actual_category} (correct)")
                    else:
                        print(f"   ❌ {filename}: Expected {expected_category}, got {actual_category}")

                except Exception as e:
                    print(f"   ❌ {filename}: Classification failed: {e}")
            else:
                print(f"   ❌ {filename}: File not found")

        accuracy = (correct_classifications / total_tests) * 100

        if accuracy >= 80:
            self.test_results.append(f"✅ Keyword classification: {accuracy:.1f}% accuracy (excellent)")
        elif accuracy >= 60:
            self.test_results.append(f"⚠️ Keyword classification: {accuracy:.1f}% accuracy (needs tuning)")
        else:
            self.test_results.append(f"❌ Keyword classification: {accuracy:.1f}% accuracy (needs work)")

    def test_finn_wolfhard_priority(self):
        """Test that Client Name Wolfhard files get highest priority classification"""

        print("\n🧪 Testing Client Name Wolfhard Priority Classification...")

        finn_files = [
            'Client Name_Wolfhard_Demo_Reel_2024.mov',
            'Stranger_Things_Season_5_Contract.pdf',
            'I-797_Approval_Notice_Client Name_2024.pdf'
        ]

        high_priority_count = 0

        for filename in finn_files:
            file_path = self.temp_dir / filename

            if file_path.exists():
                try:
                    result = self.classifier.classify_file(str(file_path))

                    # Check confidence score
                    confidence = getattr(result, 'confidence', result.get('confidence', 0))

                    if confidence >= 0.8:  # High confidence threshold
                        high_priority_count += 1
                        print(f"   ✅ {filename}: High priority ({confidence:.2f})")
                    else:
                        print(f"   ⚠️ {filename}: Lower priority ({confidence:.2f})")

                except Exception as e:
                    print(f"   ❌ {filename}: Classification failed: {e}")

        if high_priority_count >= 2:
            self.test_results.append(f"✅ Client Name priority: {high_priority_count}/3 files high priority")
        else:
            self.test_results.append(f"⚠️ Client Name priority: Only {high_priority_count}/3 files high priority")

    def test_adhd_friendly_features(self):
        """Test ADHD-friendly configuration settings"""

        print("\n🧪 Testing ADHD-Friendly Features...")

        # Load classification rules
        try:
            config_path = Path(__file__).parent / 'classification_rules.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Test ADHD settings
            adhd_settings = config.get('adhd_friendly_settings', {})

            # Check question limit
            max_questions = adhd_settings.get('max_questions_per_file', 10)
            if max_questions <= 2:
                self.test_results.append("✅ ADHD: Question limit appropriate (≤2)")
            else:
                self.test_results.append(f"⚠️ ADHD: Question limit high ({max_questions})")

            # Check visual context
            if adhd_settings.get('use_visual_context', False):
                self.test_results.append("✅ ADHD: Visual context enabled")
            else:
                self.test_results.append("⚠️ ADHD: Visual context disabled")

            # Check binary choices
            if adhd_settings.get('binary_choice_questions', False):
                self.test_results.append("✅ ADHD: Binary choice questions enabled")
            else:
                self.test_results.append("⚠️ ADHD: Binary choice questions disabled")

            # Check decision shortcuts
            shortcuts = adhd_settings.get('decision_shortcuts', {})
            if len(shortcuts) >= 5:
                self.test_results.append(f"✅ ADHD: Decision shortcuts available ({len(shortcuts)})")
            else:
                self.test_results.append(f"⚠️ ADHD: Limited decision shortcuts ({len(shortcuts)})")

        except Exception as e:
            self.test_results.append(f"❌ ADHD: Configuration test failed: {e}")

    def test_confidence_thresholds(self):
        """Test confidence threshold configuration for smart automation"""

        print("\n🧪 Testing Confidence Thresholds...")

        try:
            config_path = Path(__file__).parent / 'classification_rules.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            thresholds = config.get('confidence_thresholds', {})

            # Check threshold values
            auto_move = thresholds.get('auto_move', 0)
            suggest_move = thresholds.get('suggest_move', 0)
            manual_review = thresholds.get('manual_review', 0)

            if auto_move >= 0.85:
                self.test_results.append(f"✅ Confidence: Auto-move threshold appropriate ({auto_move})")
            else:
                self.test_results.append(f"⚠️ Confidence: Auto-move threshold low ({auto_move})")

            if suggest_move >= 0.65:
                self.test_results.append(f"✅ Confidence: Suggest-move threshold appropriate ({suggest_move})")
            else:
                self.test_results.append(f"⚠️ Confidence: Suggest-move threshold low ({suggest_move})")

            # Test logical ordering
            if auto_move > suggest_move > manual_review:
                self.test_results.append("✅ Confidence: Thresholds logically ordered")
            else:
                self.test_results.append("❌ Confidence: Threshold ordering incorrect")

        except Exception as e:
            self.test_results.append(f"❌ Confidence: Threshold test failed: {e}")

    def test_archive_lifecycle_rules(self):
        """Test archive lifecycle classification rules"""

        print("\n🧪 Testing Archive Lifecycle Rules...")

        try:
            config_path = Path(__file__).parent / 'classification_rules.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            archive_rules = config.get('archive_lifecycle', {})

            # Check entertainment industry rules
            entertainment = archive_rules.get('entertainment_industry', {})
            if entertainment.get('age_threshold_months', 0) == 12:
                self.test_results.append("✅ Archive: Entertainment threshold correct (12 months)")
            else:
                threshold = entertainment.get('age_threshold_months', 0)
                self.test_results.append(f"⚠️ Archive: Entertainment threshold unexpected ({threshold})")

            # Check creative projects rules
            creative = archive_rules.get('creative_projects', {})
            if creative.get('retention_years') == 'permanent':
                self.test_results.append("✅ Archive: Creative projects permanent retention")
            else:
                retention = creative.get('retention_years', 'unknown')
                self.test_results.append(f"⚠️ Archive: Creative retention not permanent ({retention})")

            # Check high priority patterns
            high_priority = entertainment.get('high_priority_patterns', [])
            finn_patterns = [p for p in high_priority if 'finn' in p.lower()]
            if finn_patterns:
                self.test_results.append("✅ Archive: Client Name patterns marked high priority")
            else:
                self.test_results.append("⚠️ Archive: Client Name patterns not found in high priority")

        except Exception as e:
            self.test_results.append(f"❌ Archive: Lifecycle rules test failed: {e}")

    def run_all_tests(self):
        """Run complete classification rules v3.0 test suite"""

        print("🚀 Starting Classification Rules v3.0 Tests")
        print("=" * 60)

        # Run all test categories
        self.test_keyword_classification()
        self.test_finn_wolfhard_priority()
        self.test_adhd_friendly_features()
        self.test_confidence_thresholds()
        self.test_archive_lifecycle_rules()

        # Generate summary report
        self.generate_test_report()

    def generate_test_report(self):
        """Generate comprehensive test report for classification rules v3.0"""

        print("\n" + "=" * 60)
        print("📊 CLASSIFICATION RULES v3.0 TEST RESULTS")
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
            print(f"\n🎉 CLASSIFICATION v3.0: EXCELLENT")
            print("   Enhanced classification rules are working perfectly!")
            print("   ADHD-friendly features are properly configured.")
            print("   User's file patterns are correctly recognized.")
        elif success_rate >= 60:
            print(f"\n✅ CLASSIFICATION v3.0: GOOD")
            print("   Classification working well, minor tuning recommended.")
            print("   Most ADHD features operational.")
        else:
            print(f"\n⚠️ CLASSIFICATION v3.0: NEEDS ATTENTION")
            print("   Several classification issues need resolution.")

        # Specific recommendations
        print(f"\n💡 SPECIFIC RECOMMENDATIONS:")

        if failed > 0:
            print("   🔧 Address failed tests for critical functionality")

        if warnings > 0:
            print("   📝 Review warnings to optimize classification accuracy")

        print("   🧪 Test with real files from User's ecosystem")
        print("   📊 Monitor classification patterns in production use")

        # Cleanup
        self.cleanup()

    def cleanup(self):
        """Clean up test environment"""

        if self.temp_dir and self.temp_dir.exists():
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                print(f"\n🧹 Classification test environment cleaned up")
            except Exception as e:
                print(f"\n⚠️ Could not clean up test environment: {e}")

def main():
    """Run classification rules v3.0 tests"""

    tester = ClassificationRulesV3Tester()

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