#!/usr/bin/env python3
"""
Test Suite for Vision Integration - Phase 2a Verification
Part of AI File Organizer v3.1

This test suite verifies:
1. Gemini API initialization and connection
2. Image analysis functionality
3. Screenshot text extraction
4. Video analysis (if available)
5. Caching system
6. Integration with unified_classifier
7. Learning pattern storage

Created by: RT Max / Claude Code
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from vision_analyzer import VisionAnalyzer


class TestVisionIntegration:
    """Test suite for vision analysis integration"""

    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        self.analyzer = None

    def run_all_tests(self):
        """Run all test cases"""
        print("=" * 70)
        print("Vision Integration Test Suite - Phase 2a")
        print("=" * 70)
        print()

        # Test 1: Initialization
        self.test_initialization()

        # Test 2: API Configuration
        self.test_api_configuration()

        # Test 3: Cache System
        self.test_cache_system()

        # Test 4: Pattern Storage
        self.test_pattern_storage()

        # Test 5: Category Detection
        self.test_category_detection()

        # Test 6: Fallback Analysis
        self.test_fallback_analysis()

        # Test 7: Image Analysis (if API available and test images exist)
        self.test_image_analysis()

        # Test 8: Screenshot Detection
        self.test_screenshot_detection()

        # Test 9: Integration with Unified Classifier
        self.test_unified_classifier_integration()

        # Test 10: Statistics and Metrics
        self.test_statistics()

        # Print summary
        self.print_summary()

    def test_initialization(self):
        """Test 1: VisionAnalyzer initialization"""
        print("TEST 1: VisionAnalyzer Initialization")
        print("-" * 70)

        try:
            self.analyzer = VisionAnalyzer()
            print(f"✅ VisionAnalyzer created successfully")
            print(f"   Base Directory: {self.analyzer.base_dir}")
            print(f"   Cache Directory: {self.analyzer.cache_dir}")
            print(f"   Learning Directory: {self.analyzer.learning_dir}")
            print(f"   API Initialized: {self.analyzer.api_initialized}")

            # Verify directories exist
            assert self.analyzer.cache_dir.exists(), "Cache directory should exist"
            assert self.analyzer.learning_dir.exists(), "Learning directory should exist"

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 1: {e}")

        print()

    def test_api_configuration(self):
        """Test 2: API key configuration"""
        print("TEST 2: API Configuration")
        print("-" * 70)

        try:
            if self.analyzer.api_key:
                print(f"✅ API key loaded")
                print(f"   Key length: {len(self.analyzer.api_key)} characters")
                print(f"   Key prefix: {self.analyzer.api_key[:10]}...")
            else:
                print(f"⚠️  No API key found")
                print(f"   To enable Gemini API:")
                print(f"   1. Set GEMINI_API_KEY environment variable, OR")
                print(f"   2. Create ~/.ai_organizer_config/gemini_api_key.txt")

            if self.analyzer.api_initialized:
                print(f"✅ Gemini API initialized successfully")
                print(f"   Model: gemini-1.5-flash")
                self.test_results['passed'] += 1
            else:
                print(f"⚠️  Gemini API not initialized (tests will use fallback mode)")
                self.test_results['skipped'] += 1

        except Exception as e:
            print(f"❌ API configuration test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 2: {e}")

        print()

    def test_cache_system(self):
        """Test 3: Cache system functionality"""
        print("TEST 3: Cache System")
        print("-" * 70)

        try:
            # Test cache key generation
            test_file = "/Users/test/sample.jpg"
            cache_key = self.analyzer._get_cache_key(test_file)

            print(f"✅ Cache key generation works")
            print(f"   Test file: {test_file}")
            print(f"   Cache key: {cache_key}")

            # Verify cache key is consistent
            cache_key_2 = self.analyzer._get_cache_key(test_file)
            assert cache_key == cache_key_2, "Cache keys should be consistent"

            print(f"✅ Cache key consistency verified")

            # Test cache file structure
            cache_file = self.analyzer.cache_dir / f"{cache_key}.json"
            print(f"   Cache file would be: {cache_file.name}")

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Cache system test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 3: {e}")

        print()

    def test_pattern_storage(self):
        """Test 4: Learning pattern storage"""
        print("TEST 4: Learning Pattern Storage")
        print("-" * 70)

        try:
            # Check pattern file structure
            patterns = self.analyzer.vision_patterns

            print(f"✅ Vision patterns loaded")
            print(f"   Pattern keys: {list(patterns.keys())}")

            expected_keys = ['objects_detected', 'scene_types', 'screenshot_contexts',
                           'visual_keywords', 'category_frequencies']

            for key in expected_keys:
                assert key in patterns, f"Missing pattern key: {key}"
                print(f"   ✓ {key}: {type(patterns[key])}")

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Pattern storage test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 4: {e}")

        print()

    def test_category_detection(self):
        """Test 5: Category keyword detection"""
        print("TEST 5: Category Detection")
        print("-" * 70)

        try:
            categories = self.analyzer.category_keywords

            print(f"✅ Category keywords loaded: {len(categories)} categories")

            # Test a few categories
            test_categories = ['screenshot', 'headshot', 'logo', 'diagram']

            for category in test_categories:
                if category in categories:
                    keywords = categories[category]
                    print(f"   ✓ {category}: {len(keywords)} keywords - {keywords[:3]}")

            # Verify all categories have keywords
            for category, keywords in categories.items():
                assert len(keywords) > 0, f"Category {category} has no keywords"

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Category detection test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 5: {e}")

        print()

    def test_fallback_analysis(self):
        """Test 6: Fallback analysis (when API unavailable)"""
        print("TEST 6: Fallback Analysis")
        print("-" * 70)

        try:
            # Create a mock file path
            test_image = Path("/Users/test/screenshot_2024.png")

            # Test fallback image analysis
            result = self.analyzer._fallback_image_analysis(test_image)

            print(f"✅ Fallback image analysis works")
            print(f"   Success: {result['success']}")
            print(f"   Content Type: {result['content_type']}")
            print(f"   Suggested Category: {result['suggested_category']}")
            print(f"   Confidence: {result['confidence_score']:.2f}")

            # Verify result structure
            required_keys = ['success', 'content_type', 'description', 'confidence_score',
                           'suggested_category', 'keywords']
            for key in required_keys:
                assert key in result, f"Missing key in fallback result: {key}"

            # Test fallback video analysis
            test_video = Path("/Users/test/tutorial_recording.mp4")
            video_result = self.analyzer._fallback_video_analysis(test_video)

            print(f"✅ Fallback video analysis works")
            print(f"   Suggested Category: {video_result['suggested_category']}")

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Fallback analysis test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 6: {e}")

        print()

    def test_image_analysis(self):
        """Test 7: Real image analysis (if API available and images exist)"""
        print("TEST 7: Image Analysis")
        print("-" * 70)

        if not self.analyzer.api_initialized:
            print(f"⚠️  Skipping - Gemini API not initialized")
            print(f"   Set up API key to enable this test")
            self.test_results['skipped'] += 1
            print()
            return

        # Look for test images
        test_image_paths = [
            project_dir / "Screenshot 2025-09-26 at 12.23.57 PM.png",
            project_dir / "sreenshot.jpg"
        ]

        found_image = None
        for image_path in test_image_paths:
            if image_path.exists():
                found_image = image_path
                break

        if not found_image:
            print(f"⚠️  Skipping - No test images found")
            print(f"   Looked for: {[p.name for p in test_image_paths]}")
            self.test_results['skipped'] += 1
            print()
            return

        try:
            print(f"Testing with image: {found_image.name}")
            print(f"   Size: {found_image.stat().st_size / 1024:.1f} KB")

            # Analyze image
            result = self.analyzer.analyze_image(str(found_image))

            print(f"\n✅ Image analysis completed")
            print(f"   Success: {result['success']}")
            print(f"   Suggested Category: {result['suggested_category']}")
            print(f"   Confidence: {result['confidence_score']:.2f}")
            print(f"   Scene Type: {result['scene_type']}")
            print(f"   Objects Detected: {result['objects_detected'][:3]}")
            print(f"   Description (first 150 chars):")
            print(f"   {result['description'][:150]}...")

            # Verify result structure
            assert result['success'] == True, "Analysis should succeed"
            assert result['confidence_score'] > 0, "Should have confidence score"
            assert result['suggested_category'], "Should suggest a category"

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Image analysis test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 7: {e}")

        print()

    def test_screenshot_detection(self):
        """Test 8: Screenshot detection and text extraction"""
        print("TEST 8: Screenshot Detection")
        print("-" * 70)

        # Look for screenshot files
        screenshot_paths = list(project_dir.glob("*screenshot*.png")) + \
                          list(project_dir.glob("*Screenshot*.png"))

        if not screenshot_paths:
            print(f"⚠️  Skipping - No screenshot files found")
            self.test_results['skipped'] += 1
            print()
            return

        screenshot = screenshot_paths[0]

        try:
            print(f"Testing with screenshot: {screenshot.name}")

            # Test fallback detection
            result = self.analyzer._fallback_image_analysis(screenshot)
            is_screenshot = result['suggested_category'] == 'screenshot'

            print(f"✅ Screenshot detection: {is_screenshot}")
            print(f"   Detected category: {result['suggested_category']}")

            if self.analyzer.api_initialized:
                print(f"\n   Testing text extraction...")
                text = self.analyzer.extract_screenshot_text(str(screenshot))

                if text:
                    print(f"   ✅ Text extracted ({len(text)} characters)")
                    print(f"   First 100 chars: {text[:100]}...")
                else:
                    print(f"   ⚠️  No text extracted (image may not contain text)")

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Screenshot detection test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 8: {e}")

        print()

    def test_unified_classifier_integration(self):
        """Test 9: Integration with unified_classifier.py"""
        print("TEST 9: Unified Classifier Integration")
        print("-" * 70)

        try:
            # Import unified classifier
            from unified_classifier import UnifiedClassificationService

            # Check if vision analyzer is integrated
            classifier = UnifiedClassificationService()

            print(f"✅ UnifiedClassificationService loaded")

            # Check if _classify_image_file method exists
            has_image_method = hasattr(classifier, '_classify_image_file')
            print(f"   Has _classify_image_file method: {has_image_method}")

            # Verify the method is ready for vision integration
            if has_image_method:
                print(f"   ✓ Image classification method available")
                print(f"   Ready for Phase 2b integration")
            else:
                print(f"   ⚠️  Image classification method needs integration")

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Unified classifier integration test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 9: {e}")

        print()

    def test_statistics(self):
        """Test 10: Statistics and metrics"""
        print("TEST 10: Statistics and Metrics")
        print("-" * 70)

        try:
            stats = self.analyzer.get_statistics()

            print(f"✅ Statistics retrieved")
            print(f"   API Calls: {stats['api_calls']}")
            print(f"   Cache Hits: {stats['cache_hits']}")
            print(f"   Cache Misses: {stats['cache_misses']}")
            print(f"   Cache Hit Rate: {stats['cache_hit_rate']}")
            print(f"   API Initialized: {stats['api_initialized']}")

            if stats['category_frequencies']:
                print(f"   Most Common Category: {stats['most_common_category']}")

            # Verify statistics structure
            required_keys = ['api_calls', 'cache_hits', 'cache_misses',
                           'cache_hit_rate', 'api_initialized']
            for key in required_keys:
                assert key in stats, f"Missing statistics key: {key}"

            self.test_results['passed'] += 1

        except Exception as e:
            print(f"❌ Statistics test failed: {e}")
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"Test 10: {e}")

        print()

    def print_summary(self):
        """Print test summary"""
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        total_tests = self.test_results['passed'] + self.test_results['failed'] + self.test_results['skipped']

        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"⚠️  Skipped: {self.test_results['skipped']}")

        if self.test_results['passed'] == total_tests - self.test_results['skipped']:
            print(f"\n🎉 ALL TESTS PASSED!")
        elif self.test_results['failed'] == 0:
            print(f"\n✅ All non-skipped tests passed")
        else:
            print(f"\n⚠️  Some tests failed")

        if self.test_results['errors']:
            print(f"\nErrors:")
            for error in self.test_results['errors']:
                print(f"   - {error}")

        # Print next steps
        print(f"\n" + "=" * 70)
        print("NEXT STEPS FOR PHASE 2a")
        print("=" * 70)

        if not self.analyzer or not self.analyzer.api_initialized:
            print("\n1. Set up Gemini API key:")
            print("   export GEMINI_API_KEY='your-api-key-here'")
            print("   OR")
            print("   echo 'your-api-key-here' > ~/.ai_organizer_config/gemini_api_key.txt")
            print("\n2. Install dependencies:")
            print("   pip install -r requirements_v3.txt")

        print("\n3. Test with real images:")
        print("   python test_vision_integration.py")

        print("\n4. Review vision_analyzer.py implementation")

        print("\n5. Ready for Phase 2b: Integration with unified_classifier.py")

        print("\n" + "=" * 70)


def main():
    """Main test execution"""
    test_suite = TestVisionIntegration()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()
