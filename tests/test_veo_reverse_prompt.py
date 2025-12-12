#!/usr/bin/env python3
"""
Test Suite for VEO Reverse Prompt Generator
Phase 3a Implementation - AI File Organizer v3.1

This test suite validates all functionality of the VEO Prompt Generator:
1. Video file validation
2. Metadata extraction with ffprobe
3. Vision API integration
4. VEO JSON schema compliance
5. Database operations
6. File output generation

Created by: RT Max / Claude Code
Date: October 28, 2025
"""

import os
import sys
import json
import sqlite3
import unittest
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from veo_prompt_generator import VEOPromptGenerator, VEO_SCHEMA_TEMPLATE
from vision_analyzer import VisionAnalyzer

class TestVEOPromptGenerator(unittest.TestCase):
    """Test suite for VEO Prompt Generator"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_dir = Path(__file__).parent / "test_veo_output"
        cls.test_dir.mkdir(exist_ok=True)

        cls.test_db = cls.test_dir / "test_veo.db"

        # Find test videos in Downloads
        downloads_dir = Path.home() / "Downloads"
        cls.test_videos = list(downloads_dir.glob("*.mp4"))[:3]  # Get first 3 MP4 files

        if not cls.test_videos:
            print("⚠️  Warning: No test videos found in Downloads folder")

        # Initialize generator with test paths
        cls.generator = VEOPromptGenerator(
            base_dir=str(cls.test_dir),
            db_path=str(cls.test_db),
            output_dir=str(cls.test_dir / "veo_json")
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Keep test outputs for inspection
        print(f"\n📁 Test outputs saved in: {cls.test_dir}")

    def test_01_initialization(self):
        """Test 1: VEOPromptGenerator initialization"""
        print("\n" + "="*70)
        print("TEST 1: VEOPromptGenerator Initialization")
        print("="*70)

        self.assertIsNotNone(self.generator)
        self.assertTrue(self.generator.output_dir.exists())
        self.assertTrue(self.generator.db_path.exists())

        # Check database table creation
        conn = sqlite3.connect(self.generator.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='veo_prompts'")
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result, "veo_prompts table should exist")
        print("✅ Generator initialized successfully")
        print(f"   Output directory: {self.generator.output_dir}")
        print(f"   Database: {self.generator.db_path}")
        print(f"   Vision API enabled: {self.generator.vision_enabled}")

    def test_02_video_metadata_extraction(self):
        """Test 2: ffprobe metadata extraction"""
        print("\n" + "="*70)
        print("TEST 2: Video Metadata Extraction with ffprobe")
        print("="*70)

        if not self.test_videos:
            self.skipTest("No test videos available")

        test_video = self.test_videos[0]
        print(f"📹 Testing with: {test_video.name}")

        metadata = self.generator._extract_video_metadata(test_video)

        self.assertTrue(metadata.get('success'), "Metadata extraction should succeed")
        self.assertIn('duration', metadata)
        self.assertIn('width', metadata)
        self.assertIn('height', metadata)
        self.assertIn('aspect_ratio', metadata)
        self.assertIn('fps', metadata)

        print("✅ Metadata extracted successfully:")
        print(f"   Duration: {metadata['duration']:.2f}s")
        print(f"   Resolution: {metadata['width']}x{metadata['height']}")
        print(f"   Aspect Ratio: {metadata['aspect_ratio']}")
        print(f"   FPS: {metadata['fps']:.2f}")
        print(f"   Codec: {metadata['codec']}")
        print(f"   Has Audio: {metadata['has_audio']}")

    def test_03_veo_schema_validation(self):
        """Test 3: VEO 3.1 JSON schema structure"""
        print("\n" + "="*70)
        print("TEST 3: VEO 3.1 JSON Schema Validation")
        print("="*70)

        # Validate template structure
        self.assertIn('unit_type', VEO_SCHEMA_TEMPLATE)
        self.assertEqual(VEO_SCHEMA_TEMPLATE['unit_type'], 'shot')

        self.assertIn('veo_shot', VEO_SCHEMA_TEMPLATE)
        shot = VEO_SCHEMA_TEMPLATE['veo_shot']

        # Check required fields
        required_fields = ['shot_id', 'scene', 'character', 'camera', 'audio', 'flags']
        for field in required_fields:
            self.assertIn(field, shot, f"VEO shot should have '{field}' field")

        # Check scene structure
        scene_fields = ['context', 'visual_style', 'lighting', 'mood', 'aspect_ratio', 'duration_s']
        for field in scene_fields:
            self.assertIn(field, shot['scene'], f"Scene should have '{field}' field")

        # Check camera structure
        camera_fields = ['shot_call', 'movement', 'negatives']
        for field in camera_fields:
            self.assertIn(field, shot['camera'], f"Camera should have '{field}' field")

        # Check audio structure
        audio_fields = ['dialogue', 'delivery', 'ambience', 'sfx']
        for field in audio_fields:
            self.assertIn(field, shot['audio'], f"Audio should have '{field}' field")

        print("✅ VEO 3.1 schema structure validated:")
        print(f"   Required fields: {', '.join(required_fields)}")
        print(f"   Scene fields: {', '.join(scene_fields)}")
        print(f"   Camera fields: {', '.join(camera_fields)}")
        print(f"   Audio fields: {', '.join(audio_fields)}")

    def test_04_generate_veo_json_single_video(self):
        """Test 4: Generate VEO JSON from single video"""
        print("\n" + "="*70)
        print("TEST 4: Generate VEO JSON from Single Video")
        print("="*70)

        if not self.test_videos:
            self.skipTest("No test videos available")

        test_video = self.test_videos[0]
        print(f"📹 Processing: {test_video.name}")

        result = self.generator.generate_reverse_veo_json(str(test_video))

        self.assertTrue(result.get('success'), f"Generation should succeed: {result.get('error')}")
        self.assertIn('veo_json', result)
        self.assertIn('json_path', result)
        self.assertIn('confidence_score', result)

        veo_json = result['veo_json']

        # Validate structure
        self.assertEqual(veo_json['unit_type'], 'shot')
        self.assertIn('veo_shot', veo_json)
        self.assertGreater(len(veo_json['veo_shot']['shot_id']), 0)

        # Validate confidence score
        self.assertGreaterEqual(result['confidence_score'], 0.0)
        self.assertLessEqual(result['confidence_score'], 1.0)

        # Check JSON file was created
        json_path = Path(result['json_path'])
        self.assertTrue(json_path.exists(), "JSON file should be created")

        print("✅ VEO JSON generated successfully:")
        print(f"   JSON Path: {json_path}")
        print(f"   Shot ID: {veo_json['veo_shot']['shot_id']}")
        print(f"   Confidence: {result['confidence_score']:.2f}")
        print(f"   Scene Context: {veo_json['veo_shot']['scene']['context'][:100]}...")
        print(f"   Shot Type: {veo_json['veo_shot']['camera']['shot_call']}")
        print(f"   Camera Movement: {veo_json['veo_shot']['camera']['movement']}")
        print(f"   Lighting: {veo_json['veo_shot']['scene']['lighting']}")
        print(f"   Mood: {veo_json['veo_shot']['scene']['mood']}")

    def test_05_database_operations(self):
        """Test 5: Database storage and retrieval"""
        print("\n" + "="*70)
        print("TEST 5: Database Storage and Retrieval")
        print("="*70)

        if not self.test_videos:
            self.skipTest("No test videos available")

        # Generate VEO JSON (should save to database)
        test_video = self.test_videos[0]
        result = self.generator.generate_reverse_veo_json(str(test_video))

        self.assertTrue(result.get('success'))

        # Query database
        conn = sqlite3.connect(self.generator.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT file_path, shot_id, confidence_score, aspect_ratio,
                   duration_s, shot_type, camera_movement, lighting_type,
                   mood, scene_context
            FROM veo_prompts
            WHERE file_path = ?
        """, (str(test_video),))

        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row, "Database entry should exist")

        file_path, shot_id, confidence, aspect_ratio, duration, \
            shot_type, camera_movement, lighting, mood, scene_context = row

        print("✅ Database operations successful:")
        print(f"   File: {Path(file_path).name}")
        print(f"   Shot ID: {shot_id}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Aspect Ratio: {aspect_ratio}")
        print(f"   Duration: {duration}s")
        print(f"   Shot Type: {shot_type}")
        print(f"   Camera Movement: {camera_movement}")
        print(f"   Lighting: {lighting}")
        print(f"   Mood: {mood}")
        print(f"   Scene: {scene_context[:80]}...")

    def test_06_batch_processing(self):
        """Test 6: Process multiple videos"""
        print("\n" + "="*70)
        print("TEST 6: Batch Processing Multiple Videos")
        print("="*70)

        if len(self.test_videos) < 2:
            self.skipTest("Need at least 2 test videos")

        results = []
        for i, video in enumerate(self.test_videos[:3], 1):  # Process up to 3 videos
            print(f"\n📹 Processing video {i}/{min(3, len(self.test_videos))}: {video.name}")
            result = self.generator.generate_reverse_veo_json(str(video))
            results.append(result)

            if result.get('success'):
                print(f"   ✅ Success - Confidence: {result['confidence_score']:.2f}")
            else:
                print(f"   ❌ Failed: {result.get('error')}")

        # Check statistics
        stats = self.generator.get_statistics()

        print(f"\n✅ Batch processing complete:")
        print(f"   Videos Analyzed: {stats['videos_analyzed']}")
        print(f"   Prompts Generated: {stats['prompts_generated']}")
        print(f"   Success Rate: {sum(1 for r in results if r.get('success'))}/{len(results)}")

    def test_07_error_handling(self):
        """Test 7: Error handling for invalid inputs"""
        print("\n" + "="*70)
        print("TEST 7: Error Handling")
        print("="*70)

        # Test non-existent file
        result = self.generator.generate_reverse_veo_json("/nonexistent/file.mp4")
        self.assertFalse(result.get('success'))
        self.assertIn('error', result)
        print(f"✅ Non-existent file handled: {result['error']}")

        # Test unsupported format
        test_file = self.test_dir / "test.txt"
        test_file.touch()
        result = self.generator.generate_reverse_veo_json(str(test_file))
        self.assertFalse(result.get('success'))
        self.assertIn('error', result)
        print(f"✅ Unsupported format handled: {result['error']}")

        test_file.unlink()

    def test_08_vision_analyzer_integration(self):
        """Test 8: Vision Analyzer VEO method integration"""
        print("\n" + "="*70)
        print("TEST 8: Vision Analyzer Integration")
        print("="*70)

        vision_analyzer = self.generator.vision_analyzer

        self.assertIsNotNone(vision_analyzer)
        self.assertTrue(hasattr(vision_analyzer, 'analyze_for_veo_prompt'))

        print(f"✅ Vision Analyzer integration verified:")
        print(f"   API Initialized: {vision_analyzer.api_initialized}")
        print(f"   Has VEO method: {hasattr(vision_analyzer, 'analyze_for_veo_prompt')}")

        if self.test_videos and vision_analyzer.api_initialized:
            print(f"\n🎬 Testing VEO analysis on: {self.test_videos[0].name}")
            veo_analysis = vision_analyzer.analyze_for_veo_prompt(str(self.test_videos[0]))

            required_fields = ['shot_type', 'camera_movement', 'lighting', 'mood',
                             'scene_context', 'visual_style', 'audio_ambience',
                             'confidence_score']

            for field in required_fields:
                self.assertIn(field, veo_analysis, f"VEO analysis should have '{field}'")

            print(f"   ✅ VEO Analysis fields present:")
            print(f"      Shot Type: {veo_analysis['shot_type']}")
            print(f"      Camera Movement: {veo_analysis['camera_movement']}")
            print(f"      Lighting: {veo_analysis['lighting']}")
            print(f"      Mood: {veo_analysis['mood']}")
            print(f"      Confidence: {veo_analysis['confidence_score']:.2f}")


def run_comprehensive_tests():
    """Run all tests and generate report"""
    print("\n" + "="*70)
    print("VEO REVERSE PROMPT GENERATOR - COMPREHENSIVE TEST SUITE")
    print("Phase 3a Implementation - AI File Organizer v3.1")
    print("="*70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestVEOPromptGenerator)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
        print("\n🎯 Phase 3a VEO Reverse Prompt Builder (MVP) is operational!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit(run_comprehensive_tests())
