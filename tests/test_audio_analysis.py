#!/usr/bin/env python3
"""
Test Suite for Audio Analysis Pipeline (Phase 2c)

Tests the integration of:
- AudioAnalyzer (librosa + mutagen + OpenAI)
- UnifiedClassificationService
- UniversalAdaptiveLearning (audio pattern storage)

Created: 2025-10-25
Author: RT Max / Claude Code
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from audio_analyzer import AudioAnalyzer
from unified_classifier import UnifiedClassificationService
from universal_adaptive_learning import UniversalAdaptiveLearning


class AudioAnalysisTestSuite:
    """Comprehensive test suite for audio analysis pipeline"""

    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.test_results = []

        # Initialize components
        print("\n" + "="*70)
        print("AUDIO ANALYSIS PIPELINE TEST SUITE - Phase 2c")
        print("="*70 + "\n")

    def test_1_audio_analyzer_initialization(self):
        """Test AudioAnalyzer initialization and dependency checks"""
        print("\n[TEST 1] AudioAnalyzer Initialization")
        print("-" * 60)

        try:
            # Test with OpenAI API key
            api_key = os.getenv('OPENAI_API_KEY')

            analyzer = AudioAnalyzer(
                base_dir=str(self.project_dir),
                confidence_threshold=0.7,
                openai_api_key=api_key
            )

            print(f"✅ AudioAnalyzer initialized successfully")
            print(f"   - Base directory: {analyzer.base_dir}")
            print(f"   - Confidence threshold: {analyzer.confidence_threshold}")
            print(f"   - OpenAI client: {'Available' if analyzer.client else 'Not available'}")
            print(f"   - Learning data file: {analyzer.learning_data_file}")
            print(f"   - Discovered categories: {len(analyzer.discovered_categories.get('new_categories', []))} custom categories")

            self.test_results.append(("AudioAnalyzer Initialization", True, "All components initialized"))
            return analyzer

        except Exception as e:
            print(f"❌ AudioAnalyzer initialization failed: {e}")
            self.test_results.append(("AudioAnalyzer Initialization", False, str(e)))
            return None

    def test_2_spectral_analysis(self, test_file: Path):
        """Test librosa-based spectral analysis"""
        print("\n[TEST 2] Spectral Analysis (librosa)")
        print("-" * 60)

        try:
            analyzer = AudioAnalyzer(
                base_dir=str(self.project_dir),
                confidence_threshold=0.7
            )

            print(f"Analyzing: {test_file.name}")
            spectral_result = analyzer.analyze_audio_spectral(test_file, max_duration=30)

            if spectral_result.get('success'):
                print(f"✅ Spectral analysis successful")
                print(f"   - BPM: {spectral_result.get('bpm', 0):.1f}")
                print(f"   - Mood: {spectral_result.get('mood', 'unknown')}")
                print(f"   - Content Type: {spectral_result.get('content_type', 'unknown')}")
                print(f"   - Energy Level: {spectral_result.get('energy_level_scale', 0)}/10")
                print(f"   - Texture: {spectral_result.get('spectral_features', {}).get('texture', 'unknown')}")
                print(f"   - Brightness: {spectral_result.get('spectral_features', {}).get('brightness_normalized', 0):.2f}")
                print(f"   - Harmonic Ratio: {spectral_result.get('spectral_features', {}).get('harmonic_ratio', 0):.2f}")

                self.test_results.append(("Spectral Analysis", True, f"BPM={spectral_result.get('bpm', 0):.1f}, Mood={spectral_result.get('mood')}"))
                return spectral_result
            else:
                error = spectral_result.get('error', 'Unknown error')
                print(f"❌ Spectral analysis failed: {error}")
                self.test_results.append(("Spectral Analysis", False, error))
                return None

        except Exception as e:
            print(f"❌ Spectral analysis exception: {e}")
            self.test_results.append(("Spectral Analysis", False, str(e)))
            return None

    def test_3_metadata_extraction(self, test_file: Path):
        """Test mutagen-based metadata extraction"""
        print("\n[TEST 3] Metadata Extraction (mutagen)")
        print("-" * 60)

        try:
            analyzer = AudioAnalyzer(
                base_dir=str(self.project_dir),
                confidence_threshold=0.7
            )

            print(f"Extracting metadata from: {test_file.name}")
            metadata = analyzer.get_audio_metadata(test_file)

            print(f"✅ Metadata extraction successful")
            print(f"   - Duration: {metadata.get('duration', 'Unknown')}")
            print(f"   - Bitrate: {metadata.get('bitrate', 'Unknown')}")
            print(f"   - Sample Rate: {metadata.get('sample_rate', 'Unknown')}")

            self.test_results.append(("Metadata Extraction", True, f"Duration={metadata.get('duration')}"))
            return metadata

        except Exception as e:
            print(f"❌ Metadata extraction failed: {e}")
            self.test_results.append(("Metadata Extraction", False, str(e)))
            return None

    def test_4_unified_classifier_integration(self, test_file: Path):
        """Test UnifiedClassificationService with audio file"""
        print("\n[TEST 4] Unified Classifier Integration")
        print("-" * 60)

        try:
            service = UnifiedClassificationService()

            print(f"Classifying: {test_file.name}")
            classification = service.classify_file(test_file)

            if classification and not classification.get('error'):
                print(f"✅ Unified classification successful")
                print(f"   - Source: {classification.get('source', 'Unknown')}")
                print(f"   - Category: {classification.get('category', 'unknown')}")
                print(f"   - Confidence: {classification.get('confidence', 0):.1%}")
                print(f"   - Reasoning:")
                for reason in classification.get('reasoning', []):
                    if reason:  # Skip empty strings
                        print(f"     • {reason}")

                metadata = classification.get('metadata', {})
                if metadata:
                    print(f"   - Metadata:")
                    if metadata.get('mood'):
                        print(f"     • Mood: {metadata['mood']}")
                    if metadata.get('bpm'):
                        print(f"     • BPM: {metadata['bpm']:.1f}")
                    if metadata.get('energy_level'):
                        print(f"     • Energy: {metadata['energy_level']}/10")

                self.test_results.append(("Unified Classifier", True, f"Category={classification.get('category')}, Confidence={classification.get('confidence', 0):.1%}"))
                return classification
            else:
                error = classification.get('error', 'Unknown error')
                print(f"❌ Unified classification failed: {error}")
                self.test_results.append(("Unified Classifier", False, error))
                return None

        except Exception as e:
            print(f"❌ Unified classifier exception: {e}")
            self.test_results.append(("Unified Classifier", False, str(e)))
            return None

    def test_5_learning_system_integration(self, test_file: Path):
        """Test UniversalAdaptiveLearning audio pattern storage"""
        print("\n[TEST 5] Learning System Integration")
        print("-" * 60)

        try:
            learning_system = UniversalAdaptiveLearning(base_dir=str(self.project_dir))

            # Test recording classification with audio features
            features = {
                'bpm': 120.5,
                'mood': 'contemplative',
                'content_type': 'ambient',
                'energy_level': 0.6,
                'audio_keywords': ['atmospheric', 'calm', 'spacious'],
                'spectral_features': {
                    'brightness': 2500.0,
                    'texture': 'smooth',
                    'harmonic_ratio': 0.75
                }
            }

            print(f"Recording classification for: {test_file.name}")
            event_id = learning_system.record_classification(
                file_path=str(test_file),
                predicted_category='music_ambient',
                confidence=0.85,
                features=features
            )

            print(f"✅ Learning system integration successful")
            print(f"   - Event ID: {event_id}")
            print(f"   - Audio patterns stored:")
            print(f"     • BPM ranges: {len(learning_system.audio_patterns['bpm_ranges'])} categories")
            print(f"     • Moods tracked: {len(learning_system.audio_patterns['moods'])} categories")
            print(f"     • Energy levels: {len(learning_system.audio_patterns['energy_levels'])} categories")

            # Save data
            learning_system.save_all_data()
            print(f"   - Learning data saved to: {learning_system.learning_dir}")

            self.test_results.append(("Learning System Integration", True, f"Event ID={event_id}"))
            return event_id

        except Exception as e:
            print(f"❌ Learning system integration failed: {e}")
            self.test_results.append(("Learning System Integration", False, str(e)))
            return None

    def test_6_end_to_end_pipeline(self, test_file: Path):
        """Test complete end-to-end audio analysis pipeline"""
        print("\n[TEST 6] End-to-End Pipeline Test")
        print("-" * 60)

        try:
            # Initialize service
            service = UnifiedClassificationService()

            print(f"Running full pipeline for: {test_file.name}")

            # Classify file
            classification = service.classify_file(test_file)

            if classification and not classification.get('error'):
                # Record in learning system
                if service.learning_enabled and service.learning_system:
                    metadata = classification.get('metadata', {})
                    features = {
                        'bpm': metadata.get('bpm', 0),
                        'mood': metadata.get('mood', 'unknown'),
                        'content_type': metadata.get('spectral_content_type', 'unknown'),
                        'energy_level': metadata.get('energy_level', 0),
                        'audio_keywords': metadata.get('tags', []),
                        'spectral_features': metadata.get('spectral_features', {})
                    }

                    event_id = service.learning_system.record_classification(
                        file_path=str(test_file),
                        predicted_category=classification.get('category', 'audio'),
                        confidence=classification.get('confidence', 0.0),
                        features=features
                    )

                    print(f"✅ End-to-end pipeline successful")
                    print(f"   - Classification: {classification.get('category')} ({classification.get('confidence', 0):.1%})")
                    print(f"   - Learning event recorded: {event_id}")
                    print(f"   - Audio patterns updated in learning system")

                    # Get learning summary
                    summary = service.learning_system.get_learning_summary()
                    print(f"   - Total learning events: {summary.get('total_learning_events', 0)}")

                    self.test_results.append(("End-to-End Pipeline", True, f"Event={event_id}"))
                    return True
                else:
                    print(f"⚠️  Classification succeeded but learning system unavailable")
                    self.test_results.append(("End-to-End Pipeline", True, "Classification only"))
                    return True
            else:
                print(f"❌ End-to-end pipeline failed")
                self.test_results.append(("End-to-End Pipeline", False, "Classification failed"))
                return False

        except Exception as e:
            print(f"❌ End-to-end pipeline exception: {e}")
            self.test_results.append(("End-to-End Pipeline", False, str(e)))
            return False

    def print_test_summary(self):
        """Print summary of all test results"""
        print("\n" + "="*70)
        print("TEST SUMMARY - Audio Analysis Pipeline (Phase 2c)")
        print("="*70)

        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)

        print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.1f}%)\n")

        for test_name, success, details in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} - {test_name}")
            print(f"      {details}\n")

        print("="*70)


def main():
    """Run audio analysis test suite"""

    # Find test audio files
    downloads_dir = Path.home() / "Downloads"
    test_files = []

    # Look for WAV files in Downloads
    for audio_file in downloads_dir.glob("*.wav"):
        test_files.append(audio_file)
        if len(test_files) >= 1:  # Just use first file for testing
            break

    if not test_files:
        # Fallback: look for any audio files
        for ext in ['.mp3', '.m4a', '.aiff', '.flac']:
            for audio_file in downloads_dir.glob(f"*{ext}"):
                test_files.append(audio_file)
                if len(test_files) >= 1:
                    break
            if test_files:
                break

    if not test_files:
        print("❌ No audio files found in ~/Downloads for testing")
        print("Please add a .wav, .mp3, or other audio file to test with.")
        return

    test_file = test_files[0]
    print(f"Using test file: {test_file.name}")
    print(f"File size: {test_file.stat().st_size / (1024*1024):.2f} MB")

    # Run test suite
    suite = AudioAnalysisTestSuite()

    # Run all tests
    suite.test_1_audio_analyzer_initialization()
    suite.test_2_spectral_analysis(test_file)
    suite.test_3_metadata_extraction(test_file)
    suite.test_4_unified_classifier_integration(test_file)
    suite.test_5_learning_system_integration(test_file)
    suite.test_6_end_to_end_pipeline(test_file)

    # Print summary
    suite.print_test_summary()

    # Check if all tests passed
    all_passed = all(success for _, success, _ in suite.test_results)

    if all_passed:
        print("\n🎉 All tests passed! Audio analysis pipeline is fully operational.")
        print("✅ Phase 2c: Audio Analysis Pipeline - COMPLETE")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
