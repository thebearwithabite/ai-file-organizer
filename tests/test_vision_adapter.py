"""
Test Suite for Gemini Vision Adapter
Tests the bridge between vision_analyzer and universal_adaptive_learning
"""

import pytest
from gemini_vision_adapter import (
    GeminiVisionAdapter,
    LearningPromptInput,
    create_adapter_with_learning
)


class TestLearningPromptInput:
    """Test LearningPromptInput dataclass"""

    def test_create_prompt_input(self):
        """Test creating a LearningPromptInput instance"""
        prompt_input = LearningPromptInput(
            file_path="/test/image.jpg",
            predicted_category="screenshot",
            confidence=0.85,
            features={'visual_objects': ['button', 'window'], 'keywords': ['ui', 'design']},
            media_type="image",
            source="gemini_vision",
            timestamp="2025-11-03T10:00:00"
        )

        assert prompt_input.file_path == "/test/image.jpg"
        assert prompt_input.predicted_category == "screenshot"
        assert prompt_input.confidence == 0.85
        assert prompt_input.media_type == "image"

    def test_to_dict(self):
        """Test converting LearningPromptInput to dictionary"""
        prompt_input = LearningPromptInput(
            file_path="/test/image.jpg",
            predicted_category="photo",
            confidence=0.75,
            features={},
            media_type="image",
            source="gemini_vision",
            timestamp="2025-11-03T10:00:00"
        )

        data = prompt_input.to_dict()
        assert isinstance(data, dict)
        assert data['file_path'] == "/test/image.jpg"
        assert data['confidence'] == 0.75


class TestGeminiVisionAdapter:
    """Test GeminiVisionAdapter parsing and normalization"""

    def test_parse_static_output_success(self):
        """Test parsing successful vision analyzer output"""
        adapter = GeminiVisionAdapter()

        vision_output = {
            'success': True,
            'content_type': 'image',
            'description': "A screenshot of a web interface with buttons and forms",
            'objects_detected': ['button', 'form', 'text'],
            'scene_type': 'digital',
            'confidence_score': 0.85,
            'keywords': ['ui', 'interface', 'web', 'design'],
            'suggested_category': 'screenshot',
            'metadata': {'file_name': 'test.png'}
        }

        result = adapter.parse_static_output(vision_output, "/test/screenshot.png")

        assert isinstance(result, LearningPromptInput)
        assert result.predicted_category == "screenshot"
        assert result.confidence == 0.85
        assert result.media_type == "image"
        assert result.source == "gemini_vision"
        assert 'visual_objects' in result.features
        assert 'keywords' in result.features

    def test_parse_static_output_failure(self):
        """Test parsing failed vision analyzer output"""
        adapter = GeminiVisionAdapter()

        vision_output = {
            'success': False,
            'error': 'API quota exceeded',
            'content_type': 'image',
            'confidence_score': 0.0
        }

        result = adapter.parse_static_output(vision_output, "/test/image.jpg")

        assert isinstance(result, LearningPromptInput)
        assert result.confidence == 0.0
        assert result.source == "fallback"
        assert 'error' in result.features

    def test_parse_static_output_low_confidence(self):
        """Test that low confidence triggers fallback tags"""
        adapter = GeminiVisionAdapter()

        vision_output = {
            'success': True,
            'content_type': 'image',
            'description': "Unclear image",
            'objects_detected': [],
            'scene_type': 'unknown',
            'confidence_score': 0.3,  # Low confidence
            'keywords': [],
            'suggested_category': 'photo'
        }

        result = adapter.parse_static_output(vision_output, "/test/unclear.jpg")

        assert result.confidence == 0.3
        assert 'fallback_tags' in result.features
        assert len(result.features['fallback_tags']) > 0

    def test_parse_video_output(self):
        """Test parsing video/VEO output"""
        adapter = GeminiVisionAdapter()

        veo_output = {
            'suggested_category': 'video',
            'confidence_score': 0.9,
            'objects_detected': ['person', 'table', 'laptop'],
            'keywords': ['meeting', 'discussion', 'professional'],
            'description': "A professional meeting with people around a table",
            'shot_type': 'Medium Shot',
            'camera_movement': 'Static',
            'lighting': 'Natural',
            'mood': 'professional'
        }

        result = adapter.parse_video_output(veo_output, "/test/meeting.mp4")

        assert isinstance(result, LearningPromptInput)
        assert result.media_type == "video"
        assert result.source == "veo_prompt"
        assert result.confidence == 0.9
        assert result.features['shot_type'] == 'Medium Shot'
        assert result.features['camera_movement'] == 'Static'

    def test_fallback_tags(self):
        """Test fallback tag generation"""
        adapter = GeminiVisionAdapter()

        # Known category
        tags = adapter.fallback_tags('screenshot')
        assert 'ui' in tags
        assert 'interface' in tags

        # Unknown category
        tags = adapter.fallback_tags('unknown_category')
        assert 'visual' in tags
        assert 'unknown_category' in tags

    def test_generate_prompt_input_image(self):
        """Test universal prompt input generation for images"""
        adapter = GeminiVisionAdapter()

        analysis_result = {
            'success': True,
            'content_type': 'image',
            'description': "Test image",
            'objects_detected': ['test'],
            'scene_type': 'unknown',
            'confidence_score': 0.75,
            'keywords': ['test'],
            'suggested_category': 'photo'
        }

        result = adapter.generate_prompt_input(
            analysis_result=analysis_result,
            file_path="/test/image.jpg",
            media_type='image'
        )

        assert result.media_type == "image"
        assert result.predicted_category == "photo"

    def test_generate_prompt_input_video(self):
        """Test universal prompt input generation for videos"""
        adapter = GeminiVisionAdapter()

        analysis_result = {
            'suggested_category': 'video',
            'confidence_score': 0.8,
            'objects_detected': ['scene'],
            'keywords': ['video'],
            'description': "Test video",
            'shot_type': 'Wide Shot',
            'camera_movement': 'Pan',
            'lighting': 'Dramatic',
            'mood': 'tense'
        }

        result = adapter.generate_prompt_input(
            analysis_result=analysis_result,
            file_path="/test/video.mp4",
            media_type='video'
        )

        assert result.media_type == "video"
        assert result.source == "veo_prompt"


class TestAdapterIntegration:
    """Test integration with learning system (mocked)"""

    def test_emit_learning_signal_no_system(self):
        """Test that emit_learning_signal handles missing learning system"""
        adapter = GeminiVisionAdapter(learning_system=None)

        prompt_input = LearningPromptInput(
            file_path="/test/image.jpg",
            predicted_category="photo",
            confidence=0.75,
            features={},
            media_type="image",
            source="gemini_vision",
            timestamp="2025-11-03T10:00:00"
        )

        # Should return None when learning system not available
        event_id = adapter.emit_learning_signal(prompt_input)
        assert event_id is None

    def test_process_and_learn_without_system(self):
        """Test complete workflow without learning system"""
        adapter = GeminiVisionAdapter(learning_system=None)

        analysis_result = {
            'success': True,
            'content_type': 'image',
            'description': "Test",
            'objects_detected': [],
            'scene_type': 'unknown',
            'confidence_score': 0.75,
            'keywords': [],
            'suggested_category': 'photo'
        }

        result = adapter.process_and_learn(
            analysis_result=analysis_result,
            file_path="/test/image.jpg",
            media_type='image'
        )

        assert 'prompt_input' in result
        assert 'event_id' in result
        assert 'success' in result
        assert result['success'] is False  # Because learning system is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
