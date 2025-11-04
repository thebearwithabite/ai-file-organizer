#!/usr/bin/env python3
"""
Gemini Vision Adapter - Learning System Integration
Part of AI File Organizer v3.2 - Sprint 2.0

This module bridges Gemini Vision API outputs with the Universal Adaptive Learning system,
enabling the file organizer to learn from both static images and video analyses.

Key Functions:
- Parse Gemini Vision outputs into learning-compatible formats
- Generate normalized feature dictionaries for visual content
- Provide fallback tagging for low-confidence analyses
- Emit learning signals for continuous improvement

Created by: RT Max / Claude Code
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LearningPromptInput:
    """
    Normalized prompt data structure for learning system integration.

    This format is compatible with universal_adaptive_learning.record_classification()
    and provides a consistent interface regardless of whether the source is an image,
    video, or other media type.
    """
    file_path: str
    predicted_category: str
    confidence: float
    features: Dict[str, Any]
    media_type: str  # 'image', 'video', 'audio'
    source: str  # 'gemini_vision', 'veo_prompt', etc.
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class GeminiVisionAdapter:
    """
    Adapter class that normalizes Gemini Vision outputs for the learning system.

    This adapter handles:
    - Static image analysis (screenshots, photos, designs)
    - Video frame analysis (from VEO prompts)
    - Fallback tagging when confidence is low
    - Feature extraction for pattern recognition
    """

    # Confidence thresholds
    LOW_CONFIDENCE_THRESHOLD = 0.4
    MEDIUM_CONFIDENCE_THRESHOLD = 0.7

    # Fallback tags for common visual patterns
    FALLBACK_TAGS = {
        'screenshot': ['ui', 'interface', 'screen', 'digital', 'design'],
        'photo': ['image', 'picture', 'photograph', 'visual'],
        'document': ['text', 'pdf', 'paper', 'scan'],
        'diagram': ['chart', 'graph', 'visualization', 'technical'],
        'creative': ['artwork', 'design', 'illustration', 'artistic'],
        'headshot': ['portrait', 'person', 'face', 'professional'],
        'logo': ['brand', 'icon', 'graphic', 'identity']
    }

    def __init__(self, learning_system=None):
        """
        Initialize the adapter with optional learning system reference.

        Args:
            learning_system: Optional UniversalAdaptiveLearning instance for direct integration
        """
        self.learning_system = learning_system
        self.logger = logging.getLogger(__name__)

    def parse_static_output(self,
                          vision_output: Dict[str, Any],
                          file_path: str) -> LearningPromptInput:
        """
        Parse Gemini Vision static image output into normalized learning format.

        Args:
            vision_output: Output from vision_analyzer.analyze_image()
            file_path: Path to the analyzed file

        Returns:
            LearningPromptInput with normalized data

        Example vision_output structure:
            {
                'success': True,
                'content_type': 'image',
                'description': "...",
                'objects_detected': [...],
                'scene_type': 'indoor/outdoor/digital',
                'confidence_score': 0.85,
                'keywords': [...],
                'suggested_category': "screenshot",
                'metadata': {...}
            }
        """

        # Handle failure cases
        if not vision_output.get('success', False):
            return self._create_fallback_prompt_input(
                file_path=file_path,
                error=vision_output.get('error', 'Unknown error')
            )

        # Extract core fields
        predicted_category = vision_output.get('suggested_category', 'photo')
        confidence = vision_output.get('confidence_score', 0.5)
        description = vision_output.get('description', '')

        # Build features dictionary compatible with learning system
        features = {
            'visual_objects': vision_output.get('objects_detected', []),
            'keywords': vision_output.get('keywords', []),
            'scene_type': vision_output.get('scene_type', 'unknown'),
            'description': description,
            'text_content': vision_output.get('text_content', ''),
            'content_type': vision_output.get('content_type', 'image')
        }

        # Add metadata if available
        if 'metadata' in vision_output:
            features['metadata'] = vision_output['metadata']

        # Apply fallback tags if confidence is low
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            features['fallback_tags'] = self.fallback_tags(predicted_category)
            self.logger.warning(
                f"Low confidence ({confidence:.2f}) for {file_path}, "
                f"adding fallback tags: {features['fallback_tags']}"
            )

        return LearningPromptInput(
            file_path=file_path,
            predicted_category=predicted_category,
            confidence=confidence,
            features=features,
            media_type='image',
            source='gemini_vision',
            timestamp=datetime.now().isoformat()
        )

    def parse_video_output(self,
                          veo_output: Dict[str, Any],
                          file_path: str) -> LearningPromptInput:
        """
        Parse VEO (video) prompt output into normalized learning format.

        Args:
            veo_output: Output from veo_prompt_generator or vision_analyzer.analyze_video()
            file_path: Path to the analyzed video file

        Returns:
            LearningPromptInput with normalized data
        """

        # Extract VEO-specific fields
        predicted_category = veo_output.get('suggested_category', 'video')
        confidence = veo_output.get('confidence_score', 0.7)

        # Build features from VEO metadata
        features = {
            'visual_objects': veo_output.get('objects_detected', []),
            'keywords': veo_output.get('keywords', []),
            'description': veo_output.get('description', ''),
            'shot_type': veo_output.get('shot_type', ''),
            'camera_movement': veo_output.get('camera_movement', ''),
            'lighting_type': veo_output.get('lighting', ''),
            'mood': veo_output.get('mood', ''),
            'content_type': 'video'
        }

        return LearningPromptInput(
            file_path=file_path,
            predicted_category=predicted_category,
            confidence=confidence,
            features=features,
            media_type='video',
            source='veo_prompt',
            timestamp=datetime.now().isoformat()
        )

    def generate_prompt_input(self,
                            analysis_result: Dict[str, Any],
                            file_path: str,
                            media_type: str = 'image') -> LearningPromptInput:
        """
        Universal method to generate LearningPromptInput from any analysis result.

        Args:
            analysis_result: Output from any vision analyzer method
            file_path: Path to analyzed file
            media_type: 'image' or 'video'

        Returns:
            LearningPromptInput ready for learning system
        """
        if media_type == 'video':
            return self.parse_video_output(analysis_result, file_path)
        else:
            return self.parse_static_output(analysis_result, file_path)

    def fallback_tags(self, category: str) -> List[str]:
        """
        Generate fallback tags for a given category when confidence is low.

        Args:
            category: Predicted category name

        Returns:
            List of fallback tags to supplement analysis
        """
        # Return predefined tags if category is known
        if category in self.FALLBACK_TAGS:
            return self.FALLBACK_TAGS[category].copy()

        # Generate generic fallback tags
        return ['visual', 'media', 'file', category]

    def emit_learning_signal(self, prompt_input: LearningPromptInput) -> Optional[str]:
        """
        Emit learning signal to the adaptive learning system.

        Args:
            prompt_input: Normalized learning prompt data

        Returns:
            Event ID from learning system, or None if learning system not available
        """
        if not self.learning_system:
            self.logger.warning(
                "Learning system not initialized - signal not emitted. "
                "Initialize adapter with learning_system parameter."
            )
            return None

        try:
            # Record classification in learning system
            event_id = self.learning_system.record_classification(
                file_path=prompt_input.file_path,
                predicted_category=prompt_input.predicted_category,
                confidence=prompt_input.confidence,
                features=prompt_input.features
            )

            self.logger.info(
                f"Learning signal emitted: {prompt_input.media_type} analysis "
                f"for {Path(prompt_input.file_path).name} (event_id: {event_id})"
            )

            return event_id

        except Exception as e:
            self.logger.error(f"Failed to emit learning signal: {e}", exc_info=True)
            return None

    def process_and_learn(self,
                         analysis_result: Dict[str, Any],
                         file_path: str,
                         media_type: str = 'image') -> Dict[str, Any]:
        """
        Complete workflow: parse analysis, generate prompt input, emit learning signal.

        This is the main integration point for Vision Analyzer → Learning System flow.

        Args:
            analysis_result: Output from vision_analyzer
            file_path: Path to analyzed file
            media_type: 'image' or 'video'

        Returns:
            Dictionary with prompt_input and event_id
        """
        # Generate normalized prompt input
        prompt_input = self.generate_prompt_input(
            analysis_result=analysis_result,
            file_path=file_path,
            media_type=media_type
        )

        # Emit to learning system
        event_id = self.emit_learning_signal(prompt_input)

        return {
            'prompt_input': prompt_input.to_dict(),
            'event_id': event_id,
            'success': event_id is not None
        }

    def _create_fallback_prompt_input(self,
                                     file_path: str,
                                     error: str) -> LearningPromptInput:
        """
        Create fallback prompt input when vision analysis fails.

        Args:
            file_path: Path to file
            error: Error message from vision analyzer

        Returns:
            Minimal LearningPromptInput with fallback data
        """
        file_ext = Path(file_path).suffix.lower()

        # Infer category from file extension
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            category = 'photo'
        elif file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
            category = 'video'
        else:
            category = 'unknown'

        return LearningPromptInput(
            file_path=file_path,
            predicted_category=category,
            confidence=0.0,
            features={
                'error': error,
                'fallback_tags': self.fallback_tags(category),
                'file_extension': file_ext
            },
            media_type='image' if category != 'video' else 'video',
            source='fallback',
            timestamp=datetime.now().isoformat()
        )


# === Integration Helper Functions ===

def create_adapter_with_learning(base_dir: str = None) -> GeminiVisionAdapter:
    """
    Factory function to create adapter with learning system initialized.

    Args:
        base_dir: Base directory for learning system data

    Returns:
        GeminiVisionAdapter with learning system ready
    """
    from universal_adaptive_learning import UniversalAdaptiveLearning

    learning_system = UniversalAdaptiveLearning(base_dir=base_dir)
    adapter = GeminiVisionAdapter(learning_system=learning_system)

    logger.info("Gemini Vision Adapter initialized with learning system")
    return adapter


def analyze_and_learn(file_path: str,
                     vision_analyzer=None,
                     adapter=None) -> Dict[str, Any]:
    """
    Complete workflow: analyze image with Gemini Vision and record in learning system.

    Args:
        file_path: Path to image/video file
        vision_analyzer: Optional VisionAnalyzer instance (will create if None)
        adapter: Optional GeminiVisionAdapter instance (will create if None)

    Returns:
        Dict with analysis result, prompt_input, and event_id
    """
    from vision_analyzer import VisionAnalyzer

    # Initialize components if not provided
    if vision_analyzer is None:
        vision_analyzer = VisionAnalyzer()

    if adapter is None:
        adapter = create_adapter_with_learning()

    # Determine media type
    file_ext = Path(file_path).suffix.lower()
    if file_ext in VisionAnalyzer.VIDEO_EXTENSIONS:
        media_type = 'video'
        analysis_result = vision_analyzer.analyze_video(file_path)
    else:
        media_type = 'image'
        analysis_result = vision_analyzer.analyze_image(file_path)

    # Process and learn
    learning_result = adapter.process_and_learn(
        analysis_result=analysis_result,
        file_path=file_path,
        media_type=media_type
    )

    return {
        'analysis': analysis_result,
        'learning': learning_result,
        'media_type': media_type,
        'file_path': file_path
    }


# === CLI Test Harness ===

def main():
    """
    CLI test harness for validating Gemini Vision → Learning System integration.

    Usage:
        python gemini_vision_adapter.py /path/to/image.jpg
        python gemini_vision_adapter.py /path/to/video.mp4
    """
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python gemini_vision_adapter.py <file_path>")
        print("\nExample:")
        print("  python gemini_vision_adapter.py ~/Pictures/screenshot.png")
        print("  python gemini_vision_adapter.py ~/Videos/sample.mp4")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Gemini Vision Adapter - Test Harness")
    print(f"{'='*60}\n")
    print(f"Analyzing: {file_path}\n")

    # Run complete workflow
    result = analyze_and_learn(file_path)

    # Display results
    print(f"Media Type: {result['media_type']}")
    print(f"\nAnalysis Result:")
    print(f"  Success: {result['analysis'].get('success', False)}")
    print(f"  Category: {result['analysis'].get('suggested_category', 'N/A')}")
    print(f"  Confidence: {result['analysis'].get('confidence_score', 0.0):.2f}")
    print(f"  Description: {result['analysis'].get('description', 'N/A')[:100]}...")

    print(f"\nLearning System:")
    print(f"  Event ID: {result['learning'].get('event_id', 'N/A')}")
    print(f"  Success: {result['learning'].get('success', False)}")

    # Save detailed output to JSON
    output_file = Path(file_path).stem + "_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\nFull output saved to: {output_file}")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
