#!/usr/bin/env python3
"""
Phase 2b Integration Test Suite
Tests integration of VisionAnalyzer with Classification and Learning Systems

This test suite validates:
1. VisionAnalyzer integration with UnifiedClassificationService
2. Visual pattern learning in UniversalAdaptiveLearning
3. End-to-end visual file classification workflow
4. Learning system pattern discovery from vision analysis

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

from unified_classifier import UnifiedClassificationService
from universal_adaptive_learning import UniversalAdaptiveLearning
from vision_analyzer import VisionAnalyzer


class Phase2bIntegrationTest:
    """Test suite for Phase 2b vision integration"""

    def __init__(self):
        self.test_results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }

    def run_all_tests(self):
        """Run all Phase 2b integration tests"""
        print("=" * 80)
        print("PHASE 2B INTEGRATION TEST SUITE")
        print("=" * 80)
        print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Test 1: Initialize systems
        self.test_system_initialization()

        # Test 2: VisionAnalyzer standalone
        self.test_vision_analyzer_standalone()

        # Test 3: UnifiedClassificationService with vision
        self.test_unified_classifier_vision()

        # Test 4: Learning system visual patterns
        self.test_learning_system_visual_patterns()

        # Test 5: End-to-end classification workflow
        self.test_end_to_end_classification()

        # Test 6: Pattern discovery from vision analysis
        self.test_pattern_discovery()

        # Print summary
        self.print_summary()

    def test_system_initialization(self):
        """Test 1: System initialization"""
        print("\n" + "=" * 80)
        print("TEST 1: System Initialization")
        print("=" * 80)

        try:
            # Initialize VisionAnalyzer
            print("\n1.1 Initializing VisionAnalyzer...")
            vision = VisionAnalyzer()
            assert vision is not None, "VisionAnalyzer initialization failed"

            if vision.api_initialized:
                print("   ✅ VisionAnalyzer initialized with Gemini API")
            else:
                print("   ⚠️  VisionAnalyzer initialized (fallback mode - no API key)")

            # Initialize UnifiedClassificationService
            print("\n1.2 Initializing UnifiedClassificationService...")
            classifier = UnifiedClassificationService()
            assert classifier is not None, "UnifiedClassificationService initialization failed"
            assert classifier.vision_analyzer is not None, "VisionAnalyzer not integrated"
            print("   ✅ UnifiedClassificationService initialized")
            print(f"   Vision enabled: {classifier.vision_enabled}")
            print(f"   Learning enabled: {classifier.learning_enabled}")

            # Initialize UniversalAdaptiveLearning
            print("\n1.3 Initializing UniversalAdaptiveLearning...")
            learning = UniversalAdaptiveLearning()
            assert learning is not None, "UniversalAdaptiveLearning initialization failed"
            assert hasattr(learning, 'visual_patterns'), "Visual patterns storage missing"
            assert hasattr(learning, 'record_classification'), "record_classification method missing"
            print("   ✅ UniversalAdaptiveLearning initialized")
            print(f"   Visual patterns file: {learning.visual_patterns_file}")

            self.record_test_result("System Initialization", True, "All systems initialized successfully")

        except Exception as e:
            self.record_test_result("System Initialization", False, str(e))

    def test_vision_analyzer_standalone(self):
        """Test 2: VisionAnalyzer standalone functionality"""
        print("\n" + "=" * 80)
        print("TEST 2: VisionAnalyzer Standalone")
        print("=" * 80)

        try:
            vision = VisionAnalyzer()

            # Test image file detection
            print("\n2.1 Testing image format detection...")
            test_formats = ['.jpg', '.png', '.gif', '.heic']
            for fmt in test_formats:
                assert fmt in vision.IMAGE_EXTENSIONS, f"{fmt} not in supported formats"
            print(f"   ✅ Supports {len(vision.IMAGE_EXTENSIONS)} image formats")

            # Test video file detection
            print("\n2.2 Testing video format detection...")
            test_formats = ['.mp4', '.mov', '.avi']
            for fmt in test_formats:
                assert fmt in vision.VIDEO_EXTENSIONS, f"{fmt} not in supported formats"
            print(f"   ✅ Supports {len(vision.VIDEO_EXTENSIONS)} video formats")

            # Test category keywords
            print("\n2.3 Testing category keyword mapping...")
            assert 'screenshot' in vision.category_keywords, "Screenshot category missing"
            assert 'headshot' in vision.category_keywords, "Headshot category missing"
            assert 'logo' in vision.category_keywords, "Logo category missing"
            print(f"   ✅ {len(vision.category_keywords)} visual categories defined")

            # Test statistics
            print("\n2.4 Testing statistics tracking...")
            stats = vision.get_statistics()
            assert 'api_calls' in stats, "API calls not tracked"
            assert 'cache_hits' in stats, "Cache hits not tracked"
            assert 'cache_hit_rate' in stats, "Cache hit rate not tracked"
            print(f"   ✅ Statistics tracking operational")
            print(f"   API initialized: {stats['api_initialized']}")

            self.record_test_result("VisionAnalyzer Standalone", True, "All standalone tests passed")

        except Exception as e:
            self.record_test_result("VisionAnalyzer Standalone", False, str(e))

    def test_unified_classifier_vision(self):
        """Test 3: UnifiedClassificationService vision integration"""
        print("\n" + "=" * 80)
        print("TEST 3: UnifiedClassificationService Vision Integration")
        print("=" * 80)

        try:
            classifier = UnifiedClassificationService()

            # Test file type detection
            print("\n3.1 Testing file type routing...")
            test_files = {
                'test.jpg': 'image',
                'test.png': 'image',
                'test.mp4': 'video',
                'test.mov': 'video',
                'test.pdf': 'text',
                'test.mp3': 'audio'
            }

            for filename, expected_type in test_files.items():
                file_path = Path('/tmp') / filename
                detected_type = classifier._get_file_type(file_path)
                assert detected_type == expected_type, f"{filename} misidentified as {detected_type}"

            print(f"   ✅ File type routing working correctly")

            # Test vision classifier methods exist
            print("\n3.2 Testing vision classification methods...")
            assert hasattr(classifier, '_classify_image_file'), "Image classifier missing"
            assert hasattr(classifier, '_classify_video_file'), "Video classifier missing"
            assert hasattr(classifier, '_fallback_classification'), "Fallback classifier missing"
            print("   ✅ All vision classification methods present")

            # Test fallback classification
            print("\n3.3 Testing fallback classification...")
            test_image = Path('/tmp/test_screenshot.png')
            fallback_result = classifier._fallback_classification(test_image, 'image')
            assert fallback_result is not None, "Fallback classification failed"
            assert 'category' in fallback_result, "Category missing from fallback"
            assert 'confidence' in fallback_result, "Confidence missing from fallback"
            assert fallback_result['metadata']['fallback_mode'] == True, "Fallback mode not set"
            print(f"   ✅ Fallback classification working")
            print(f"   Fallback confidence: {fallback_result['confidence']}")

            self.record_test_result("UnifiedClassificationService Vision", True, "Vision integration verified")

        except Exception as e:
            self.record_test_result("UnifiedClassificationService Vision", False, str(e))

    def test_learning_system_visual_patterns(self):
        """Test 4: Learning system visual pattern storage"""
        print("\n" + "=" * 80)
        print("TEST 4: Learning System Visual Patterns")
        print("=" * 80)

        try:
            learning = UniversalAdaptiveLearning()

            # Test visual patterns structure
            print("\n4.1 Testing visual patterns structure...")
            assert 'objects_detected' in learning.visual_patterns, "objects_detected missing"
            assert 'scene_types' in learning.visual_patterns, "scene_types missing"
            assert 'screenshot_contexts' in learning.visual_patterns, "screenshot_contexts missing"
            assert 'visual_keywords' in learning.visual_patterns, "visual_keywords missing"
            assert 'category_frequencies' in learning.visual_patterns, "category_frequencies missing"
            print("   ✅ Visual patterns structure complete")

            # Test record_classification method
            print("\n4.2 Testing record_classification method...")
            test_file = "/tmp/test_headshot.jpg"
            test_features = {
                'visual_objects': ['person', 'face', 'portrait'],
                'keywords': ['professional', 'headshot', 'portrait'],
                'scene_type': 'indoor'
            }

            event_id = learning.record_classification(
                file_path=test_file,
                predicted_category='headshot',
                confidence=0.85,
                features=test_features
            )

            assert event_id is not None, "Event ID not returned"
            assert len(learning.learning_events) > 0, "Learning event not recorded"
            print(f"   ✅ Classification recorded: {event_id}")

            # Verify visual patterns were updated
            print("\n4.3 Verifying visual pattern updates...")
            assert 'headshot' in learning.visual_patterns['category_frequencies'], "Category frequency not updated"
            assert learning.visual_patterns['category_frequencies']['headshot'] > 0, "Category count not incremented"
            print(f"   ✅ Visual patterns updated")
            print(f"   Headshot frequency: {learning.visual_patterns['category_frequencies']['headshot']}")

            # Test pattern saving
            print("\n4.4 Testing pattern persistence...")
            initial_count = len(learning.learning_events)
            learning.save_all_data()
            print(f"   ✅ Learning data saved ({initial_count} events)")

            self.record_test_result("Learning System Visual Patterns", True, "Visual pattern learning operational")

        except Exception as e:
            self.record_test_result("Learning System Visual Patterns", False, str(e))

    def test_end_to_end_classification(self):
        """Test 5: End-to-end classification workflow"""
        print("\n" + "=" * 80)
        print("TEST 5: End-to-End Classification Workflow")
        print("=" * 80)

        try:
            # Find a real test image if available
            test_image = self._find_test_image()

            if test_image:
                print(f"\n5.1 Testing with real image: {test_image.name}")
                classifier = UnifiedClassificationService()

                # Classify the image
                result = classifier.classify_file(test_image)

                assert result is not None, "Classification returned None"
                assert 'category' in result, "Category missing from result"
                assert 'confidence' in result, "Confidence missing from result"
                assert 'source' in result, "Source missing from result"

                print(f"   ✅ Classification successful")
                print(f"   Category: {result['category']}")
                print(f"   Confidence: {result['confidence']:.2f}")
                print(f"   Source: {result['source']}")

                # Verify learning system recorded it
                if classifier.learning_enabled:
                    print(f"\n5.2 Verifying learning system integration...")
                    learning = classifier.learning_system
                    summary = learning.get_learning_summary()
                    print(f"   ✅ Learning events: {summary['total_learning_events']}")

                self.record_test_result("End-to-End Classification", True, "Full workflow operational")
            else:
                print("   ⚠️  No test image found - skipping real classification test")
                self.record_test_result("End-to-End Classification", None, "No test image available")

        except Exception as e:
            self.record_test_result("End-to-End Classification", False, str(e))

    def test_pattern_discovery(self):
        """Test 6: Pattern discovery from vision analysis"""
        print("\n" + "=" * 80)
        print("TEST 6: Pattern Discovery from Vision Analysis")
        print("=" * 80)

        try:
            learning = UniversalAdaptiveLearning()

            # Simulate multiple classifications to trigger pattern discovery
            print("\n6.1 Simulating pattern discovery with multiple classifications...")

            test_cases = [
                {
                    'file': '/tmp/screenshot1.png',
                    'category': 'screenshot',
                    'confidence': 0.80,
                    'features': {
                        'visual_objects': ['interface', 'window', 'buttons'],
                        'keywords': ['screenshot', 'desktop', 'app'],
                        'scene_type': 'digital'
                    }
                },
                {
                    'file': '/tmp/screenshot2.png',
                    'category': 'screenshot',
                    'confidence': 0.85,
                    'features': {
                        'visual_objects': ['interface', 'menu', 'toolbar'],
                        'keywords': ['screenshot', 'application', 'ui'],
                        'scene_type': 'digital'
                    }
                },
                {
                    'file': '/tmp/screenshot3.png',
                    'category': 'screenshot',
                    'confidence': 0.82,
                    'features': {
                        'visual_objects': ['desktop', 'window', 'interface'],
                        'keywords': ['screenshot', 'screen', 'capture'],
                        'scene_type': 'digital'
                    }
                }
            ]

            for i, test_case in enumerate(test_cases, 1):
                learning.record_classification(
                    file_path=test_case['file'],
                    predicted_category=test_case['category'],
                    confidence=test_case['confidence'],
                    features=test_case['features']
                )
                print(f"   Classification {i}/3 recorded")

            print(f"   ✅ {len(test_cases)} classifications recorded")

            # Check pattern discovery
            print("\n6.2 Checking pattern discovery...")
            patterns_count = len(learning.patterns)
            print(f"   Patterns discovered: {patterns_count}")

            # Check visual pattern frequencies
            screenshot_freq = learning.visual_patterns['category_frequencies'].get('screenshot', 0)
            assert screenshot_freq >= 3, "Screenshot frequency not updated correctly"
            print(f"   ✅ Screenshot pattern frequency: {screenshot_freq}")

            # Check common objects
            if 'screenshot' in learning.visual_patterns['objects_detected']:
                objects = learning.visual_patterns['objects_detected']['screenshot']
                print(f"   Common objects for screenshots: {objects[:5]}")

            self.record_test_result("Pattern Discovery", True, "Pattern discovery from vision working")

        except Exception as e:
            self.record_test_result("Pattern Discovery", False, str(e))

    def _find_test_image(self) -> Path:
        """Find a test image file for real classification test"""
        # Check common locations for test images
        test_locations = [
            Path(__file__).parent / "Screenshot 2025-09-26 at 12.23.57 PM.png",
            Path(__file__).parent / "sreenshot.jpg",
            Path.home() / "Desktop",
            Path.home() / "Downloads"
        ]

        for location in test_locations:
            if location.is_file() and location.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                return location
            elif location.is_dir():
                # Search for image files
                for ext in ['.jpg', '.jpeg', '.png', '.gif']:
                    images = list(location.glob(f'*{ext}'))
                    if images:
                        return images[0]

        return None

    def record_test_result(self, test_name: str, passed: bool, message: str):
        """Record a test result"""
        self.test_results['total_tests'] += 1

        if passed is True:
            self.test_results['passed'] += 1
            status = "✅ PASSED"
        elif passed is False:
            self.test_results['failed'] += 1
            status = "❌ FAILED"
        else:
            self.test_results['skipped'] += 1
            status = "⚠️  SKIPPED"

        self.test_results['details'].append({
            'test': test_name,
            'status': status,
            'message': message
        })

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        for detail in self.test_results['details']:
            print(f"{detail['status']} {detail['test']}")
            print(f"         {detail['message']}")
            print()

        print("=" * 80)
        print(f"Total Tests: {self.test_results['total_tests']}")
        print(f"Passed:      {self.test_results['passed']} ✅")
        print(f"Failed:      {self.test_results['failed']} ❌")
        print(f"Skipped:     {self.test_results['skipped']} ⚠️")
        print("=" * 80)

        pass_rate = (self.test_results['passed'] / self.test_results['total_tests'] * 100) if self.test_results['total_tests'] > 0 else 0
        print(f"\nPass Rate: {pass_rate:.1f}%")

        if self.test_results['failed'] == 0:
            print("\n🎉 ALL TESTS PASSED! Phase 2b integration is complete.")
            return True
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
            return False


def main():
    """Main test execution"""
    tester = Phase2bIntegrationTest()
    success = tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
