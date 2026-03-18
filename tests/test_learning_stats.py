"""
Test Suite for Learning Statistics API
Tests the GET /api/settings/learning-stats endpoint and underlying functionality
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys
import tempfile
import shutil
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from universal_adaptive_learning import UniversalAdaptiveLearning, LearningEvent

client = TestClient(app)


@pytest.fixture
def temp_learning_system(monkeypatch):
    """Create a temporary learning system for testing"""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    # Patch get_metadata_root to point to temp_dir
    def mock_get_metadata_root():
        return temp_path

    # We need to patch where it's imported in universal_adaptive_learning.py
    monkeypatch.setattr("universal_adaptive_learning.get_metadata_root", mock_get_metadata_root)

    learning_system = UniversalAdaptiveLearning(base_dir=temp_dir)
    yield learning_system
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestLearningStatsEndpoint:
    """Test the /api/settings/learning-stats API endpoint"""

    def test_endpoint_returns_correct_shape(self):
        """Test that the endpoint returns the expected JSON structure"""
        response = client.get("/api/settings/learning-stats")

        assert response.status_code == 200
        data = response.json()

        # Verify all required keys are present
        required_keys = [
            "total_learning_events",
            "image_events",
            "video_events",
            "audio_events",
            "document_events",
            "unique_categories_learned",
            "most_common_category",
            "top_confidence_average",
            "media_type_breakdown",
            "category_distribution"
        ]

        for key in required_keys:
            assert key in data, f"Missing key: {key}"

        # Verify data types
        assert isinstance(data["total_learning_events"], int)
        assert isinstance(data["image_events"], int)
        assert isinstance(data["video_events"], int)
        assert isinstance(data["audio_events"], int)
        assert isinstance(data["document_events"], int)
        assert isinstance(data["unique_categories_learned"], int)
        assert isinstance(data["top_confidence_average"], (int, float))
        assert isinstance(data["media_type_breakdown"], dict)
        assert isinstance(data["category_distribution"], dict)
        # most_common_category can be None or str
        assert data["most_common_category"] is None or isinstance(data["most_common_category"], str)

    def test_endpoint_with_empty_db(self):
        """Test that the endpoint handles empty learning system gracefully"""
        response = client.get("/api/settings/learning-stats")

        assert response.status_code == 200
        data = response.json()

        # With empty DB, should have zeros and empty structures
        assert data["total_learning_events"] >= 0
        assert data["image_events"] >= 0
        assert data["video_events"] >= 0
        assert data["audio_events"] >= 0
        assert data["document_events"] >= 0
        assert data["unique_categories_learned"] >= 0
        assert isinstance(data["media_type_breakdown"], dict)
        assert isinstance(data["category_distribution"], dict)


class TestLearningStatisticsMethod:
    """Test the get_learning_statistics() method directly"""

    def test_empty_learning_system(self, temp_learning_system):
        """Test statistics with no learning events"""
        stats = temp_learning_system.get_learning_statistics()

        assert stats["total_learning_events"] == 0
        assert stats["image_events"] == 0
        assert stats["video_events"] == 0
        assert stats["audio_events"] == 0
        assert stats["document_events"] == 0
        assert stats["unique_categories_learned"] == 0
        assert stats["most_common_category"] is None
        assert stats["top_confidence_average"] == 0.0
        assert stats["media_type_breakdown"] == {}
        assert stats["category_distribution"] == {}

    def test_only_image_events(self, temp_learning_system):
        """Test statistics with only image-origin events"""
        # Add image events
        for i in range(5):
            event = LearningEvent(
                event_id=f"evt_img_{i}",
                timestamp=datetime.now(),
                event_type="ai_classification",
                file_path=f"/test/image_{i}.jpg",
                original_prediction={
                    "category": "photo" if i < 3 else "screenshot",
                    "confidence": 0.8 + (i * 0.02)
                },
                user_action={"accepted": True, "category": "photo"},
                confidence_before=0.8 + (i * 0.02),
                confidence_after=0.9,
                context={"media_type": "image", "source": "gemini_vision"}
            )
            temp_learning_system.learning_events.append(event)

        # Save data to disk so get_learning_statistics() can reload it
        temp_learning_system.save_all_data(force=True)

        stats = temp_learning_system.get_learning_statistics()

        assert stats["total_learning_events"] == 5
        assert stats["image_events"] == 5
        assert stats["video_events"] == 0
        assert stats["audio_events"] == 0
        assert stats["document_events"] == 0
        assert stats["unique_categories_learned"] == 2  # photo and screenshot
        assert stats["most_common_category"] == "photo"
        assert stats["top_confidence_average"] > 0.0
        assert "image" in stats["media_type_breakdown"]
        assert stats["media_type_breakdown"]["image"] == 5

    def test_only_video_events(self, temp_learning_system):
        """Test statistics with only video-origin events"""
        # Add video events
        for i in range(3):
            event = LearningEvent(
                event_id=f"evt_vid_{i}",
                timestamp=datetime.now(),
                event_type="ai_classification",
                file_path=f"/test/video_{i}.mp4",
                original_prediction={
                    "category": "video",
                    "confidence": 0.85
                },
                user_action={"accepted": True, "category": "video"},
                confidence_before=0.85,
                confidence_after=0.9,
                context={"media_type": "video", "source": "veo_prompt"}
            )
            temp_learning_system.learning_events.append(event)

        # Save data to disk so get_learning_statistics() can reload it
        temp_learning_system.save_all_data(force=True)

        stats = temp_learning_system.get_learning_statistics()

        assert stats["total_learning_events"] == 3
        assert stats["image_events"] == 0
        assert stats["video_events"] == 3
        assert stats["audio_events"] == 0
        assert stats["unique_categories_learned"] == 1
        assert stats["most_common_category"] == "video"
        assert "video" in stats["media_type_breakdown"]
        assert stats["media_type_breakdown"]["video"] == 3

    def test_mixed_media_types(self, temp_learning_system):
        """Test statistics with mixed media types"""
        # Add mixed events
        media_types = ["image", "video", "audio", "document", "image", "video"]
        categories = ["photo", "video", "music", "pdf", "screenshot", "clip"]

        for i, (media_type, category) in enumerate(zip(media_types, categories)):
            event = LearningEvent(
                event_id=f"evt_mix_{i}",
                timestamp=datetime.now(),
                event_type="ai_classification",
                file_path=f"/test/file_{i}",
                original_prediction={"category": category, "confidence": 0.75 + (i * 0.03)},
                user_action={"accepted": True, "category": category},
                confidence_before=0.75 + (i * 0.03),
                confidence_after=0.9,
                context={"media_type": media_type, "source": "test"}
            )
            temp_learning_system.learning_events.append(event)

        # Save data to disk so get_learning_statistics() can reload it
        temp_learning_system.save_all_data(force=True)

        stats = temp_learning_system.get_learning_statistics()

        assert stats["total_learning_events"] == 6
        assert stats["image_events"] == 2
        assert stats["video_events"] == 2
        assert stats["audio_events"] == 1
        assert stats["document_events"] == 1
        assert stats["unique_categories_learned"] == 6
        assert stats["top_confidence_average"] > 0.0

    def test_malformed_events_handled_gracefully(self, temp_learning_system):
        """Test that malformed events don't crash statistics"""
        # Add events with missing context
        event_no_context = LearningEvent(
            event_id="evt_bad_1",
            timestamp=datetime.now(),
            event_type="ai_classification",
            file_path="/test/bad1.jpg",
            original_prediction={"category": "photo", "confidence": 0.8},
            user_action={"accepted": True},
            confidence_before=0.8,
            confidence_after=0.9,
            context=None  # Missing context
        )
        temp_learning_system.learning_events.append(event_no_context)

        # Add event with context but no media_type
        event_no_media_type = LearningEvent(
            event_id="evt_bad_2",
            timestamp=datetime.now(),
            event_type="ai_classification",
            file_path="/test/bad2.jpg",
            original_prediction={"category": "screenshot", "confidence": 0.75},
            user_action={"accepted": True},
            confidence_before=0.75,
            confidence_after=0.85,
            context={"source": "unknown"}  # No media_type
        )
        temp_learning_system.learning_events.append(event_no_media_type)

        # Add event with missing category
        event_no_category = LearningEvent(
            event_id="evt_bad_3",
            timestamp=datetime.now(),
            event_type="ai_classification",
            file_path="/test/bad3.jpg",
            original_prediction={"confidence": 0.9},  # No category
            user_action={"accepted": True},
            confidence_before=0.9,
            confidence_after=0.95,
            context={"media_type": "image"}
        )
        temp_learning_system.learning_events.append(event_no_category)

        # Save data to disk so get_learning_statistics() can reload it
        temp_learning_system.save_all_data(force=True)

        # Should not crash
        stats = temp_learning_system.get_learning_statistics()

        # Should still return valid structure
        assert isinstance(stats, dict)
        assert stats["total_learning_events"] == 3
        # Events with proper media_type should be counted
        assert stats["image_events"] == 1

    def test_confidence_average_calculation(self, temp_learning_system):
        """Test that top confidence average is calculated correctly"""
        # Add 15 events with known confidence values
        confidences = [0.95, 0.92, 0.90, 0.88, 0.85, 0.82, 0.80, 0.78, 0.75, 0.72, 0.70, 0.68, 0.65, 0.62, 0.60]

        for i, conf in enumerate(confidences):
            event = LearningEvent(
                event_id=f"evt_conf_{i}",
                timestamp=datetime.now(),
                event_type="ai_classification",
                file_path=f"/test/file_{i}.jpg",
                original_prediction={"category": "photo", "confidence": conf},
                user_action={"accepted": True, "category": "photo"},
                confidence_before=conf,
                confidence_after=0.9,
                context={"media_type": "image"}
            )
            temp_learning_system.learning_events.append(event)

        # Save data to disk so get_learning_statistics() can reload it
        temp_learning_system.save_all_data(force=True)

        stats = temp_learning_system.get_learning_statistics()

        # Top 10 should be: 0.95, 0.92, 0.90, 0.88, 0.85, 0.82, 0.80, 0.78, 0.75, 0.72
        expected_avg = sum(confidences[:10]) / 10
        assert abs(stats["top_confidence_average"] - expected_avg) < 0.01

    def test_category_distribution(self, temp_learning_system):
        """Test that category distribution is calculated correctly"""
        # Add events with different categories
        categories_list = ["photo"] * 5 + ["screenshot"] * 3 + ["video"] * 2 + ["document"] * 1

        for i, category in enumerate(categories_list):
            event = LearningEvent(
                event_id=f"evt_cat_{i}",
                timestamp=datetime.now(),
                event_type="ai_classification",
                file_path=f"/test/file_{i}",
                original_prediction={"category": category, "confidence": 0.8},
                user_action={"accepted": True, "category": category},
                confidence_before=0.8,
                confidence_after=0.9,
                context={"media_type": "image"}
            )
            temp_learning_system.learning_events.append(event)

        # Save data to disk so get_learning_statistics() can reload it
        temp_learning_system.save_all_data(force=True)

        stats = temp_learning_system.get_learning_statistics()

        assert stats["unique_categories_learned"] == 4
        assert stats["most_common_category"] == "photo"
        assert stats["category_distribution"]["photo"] == 5
        assert stats["category_distribution"]["screenshot"] == 3
        assert stats["category_distribution"]["video"] == 2
        assert stats["category_distribution"]["document"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
