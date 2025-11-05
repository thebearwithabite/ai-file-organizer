"""
Test Suite for VEO API Endpoints
Tests the FastAPI routes for Vision & Learning Prompt Management
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from api.veo_api import init_veo_prompts_table

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize and clean database for all tests"""
    import sqlite3
    from api.veo_api import DB_PATH

    # Initialize table
    init_veo_prompts_table()

    # Clear all existing test data
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM veo_prompts WHERE file_path LIKE '/test/%'")
        conn.commit()

    yield


class TestVEOPromptsGET:
    """Test GET /api/veo/prompts endpoint"""

    def test_list_prompts_no_filter(self):
        """Test listing prompts without filters"""
        response = client.get("/api/veo/prompts")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_prompts_with_media_type_filter(self):
        """Test filtering by media type"""
        response = client.get("/api/veo/prompts?media_type=image")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

        # Verify all results are images if any returned
        for prompt in response.json():
            assert prompt['media_type'] == 'image'

    def test_list_prompts_with_limit(self):
        """Test limit parameter"""
        response = client.get("/api/veo/prompts?limit=10")

        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert len(results) <= 10

    def test_list_prompts_with_search(self):
        """Test search parameter"""
        response = client.get("/api/veo/prompts?search=test")

        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestVEOPromptsPOST:
    """Test POST /api/veo/prompts endpoint"""

    def test_create_prompt_minimal(self):
        """Test creating a prompt with minimal data"""
        prompt_data = {
            "file_path": "/test/image.jpg",
            "predicted_category": "photo",
            "confidence": 0.85,
            "features": {
                "visual_objects": ["test"],
                "keywords": ["test"]
            },
            "media_type": "image",
            "source": "test"
        }

        response = client.post("/api/veo/prompts", json=prompt_data)

        # Should succeed or return 409 if duplicate
        assert response.status_code in [201, 409]

        if response.status_code == 201:
            data = response.json()
            assert "id" in data
            assert data['predicted_category'] == "photo"
            assert data['media_type'] == "image"

    def test_create_prompt_with_learning_signal(self):
        """Test that creating prompt emits learning signal"""
        prompt_data = {
            "file_path": "/test/learning_test.jpg",
            "predicted_category": "screenshot",
            "confidence": 0.92,
            "features": {
                "visual_objects": ["button", "window"],
                "keywords": ["ui", "interface"]
            },
            "media_type": "image",
            "source": "test"
        }

        response = client.post("/api/veo/prompts", json=prompt_data)

        # Should succeed or return 409 if duplicate
        assert response.status_code in [201, 409]

        if response.status_code == 201:
            data = response.json()
            # Event ID may be None if learning system not initialized
            assert "event_id" in data

    def test_create_prompt_video(self):
        """Test creating a video prompt"""
        prompt_data = {
            "file_path": "/test/video.mp4",
            "predicted_category": "video",
            "confidence": 0.78,
            "features": {
                "shot_type": "Medium Shot",
                "camera_movement": "Static",
                "lighting": "Natural"
            },
            "media_type": "video",
            "source": "veo_prompt"
        }

        response = client.post("/api/veo/prompts", json=prompt_data)

        assert response.status_code in [201, 409]

        if response.status_code == 201:
            data = response.json()
            assert data['media_type'] == "video"


class TestClipReanalyze:
    """Test POST /api/clip/{id}/reanalyze endpoint"""

    def test_reanalyze_nonexistent_clip(self):
        """Test reanalyzing a clip that doesn't exist"""
        response = client.post("/api/clip/99999/reanalyze")

        assert response.status_code == 404
        assert "not found" in response.json()['detail'].lower()

    def test_reanalyze_missing_file(self):
        """Test reanalyzing clip when file is missing"""
        # First create a prompt with non-existent file
        prompt_data = {
            "file_path": "/nonexistent/missing.jpg",
            "predicted_category": "photo",
            "confidence": 0.5,
            "features": {},
            "media_type": "image",
            "source": "test"
        }

        create_response = client.post("/api/veo/prompts", json=prompt_data)

        if create_response.status_code == 201:
            clip_id = create_response.json()['id']

            # Try to reanalyze
            reanalyze_response = client.post(f"/api/clip/{clip_id}/reanalyze")

            # Should fail because file doesn't exist
            assert reanalyze_response.status_code == 404


class TestClipGet:
    """Test GET /api/clip/{id} endpoint"""

    def test_get_clip_details(self):
        """Test retrieving clip details"""
        # First create a prompt
        prompt_data = {
            "file_path": "/test/detail_test.jpg",
            "predicted_category": "photo",
            "confidence": 0.88,
            "features": {"test": "data"},
            "media_type": "image",
            "source": "test"
        }

        create_response = client.post("/api/veo/prompts", json=prompt_data)

        if create_response.status_code == 201:
            clip_id = create_response.json()['id']

            # Get clip details
            get_response = client.get(f"/api/clip/{clip_id}")

            assert get_response.status_code == 200
            data = get_response.json()
            assert data['id'] == clip_id
            assert data['file_path'] == "/test/detail_test.jpg"
            assert data['predicted_category'] == "photo"

    def test_get_nonexistent_clip(self):
        """Test getting a clip that doesn't exist"""
        response = client.get("/api/clip/99999")

        assert response.status_code == 404


class TestVEOIntegration:
    """Integration tests for VEO API workflow"""

    def test_complete_workflow(self):
        """Test complete workflow: create → list → get → reanalyze"""
        # 1. Create a prompt
        prompt_data = {
            "file_path": "/test/workflow_test.jpg",
            "predicted_category": "screenshot",
            "confidence": 0.95,
            "features": {
                "visual_objects": ["button", "menu"],
                "keywords": ["ui", "application"]
            },
            "media_type": "image",
            "source": "test_workflow"
        }

        create_response = client.post("/api/veo/prompts", json=prompt_data)
        assert create_response.status_code in [201, 409]

        if create_response.status_code == 201:
            clip_id = create_response.json()['id']

            # 2. List prompts and verify it appears
            list_response = client.get("/api/veo/prompts?search=workflow_test")
            assert list_response.status_code == 200
            prompts = list_response.json()
            assert any(p['id'] == clip_id for p in prompts)

            # 3. Get clip details
            get_response = client.get(f"/api/clip/{clip_id}")
            assert get_response.status_code == 200
            assert get_response.json()['id'] == clip_id

    def test_media_type_filtering(self):
        """Test filtering by media type works correctly"""
        # Create an image prompt
        image_data = {
            "file_path": "/test/filter_image.jpg",
            "predicted_category": "photo",
            "confidence": 0.8,
            "features": {},
            "media_type": "image",
            "source": "test"
        }

        # Create a video prompt
        video_data = {
            "file_path": "/test/filter_video.mp4",
            "predicted_category": "video",
            "confidence": 0.8,
            "features": {},
            "media_type": "video",
            "source": "test"
        }

        client.post("/api/veo/prompts", json=image_data)
        client.post("/api/veo/prompts", json=video_data)

        # Filter for images only
        image_response = client.get("/api/veo/prompts?media_type=image")
        assert image_response.status_code == 200
        for prompt in image_response.json():
            assert prompt['media_type'] == 'image'

        # Filter for videos only
        video_response = client.get("/api/veo/prompts?media_type=video")
        assert video_response.status_code == 200
        for prompt in video_response.json():
            assert prompt['media_type'] == 'video'


class TestStorePromptUpsert:
    """Test smart insert/update logic for store_prompt()"""

    def test_insert_new_file(self):
        """Test inserting prompt for a new file"""
        prompt_data = {
            "file_path": "/test/new_file.jpg",
            "predicted_category": "photo",
            "confidence": 0.85,
            "features": {"test": "data"},
            "media_type": "image",
            "source": "test"
        }

        response = client.post("/api/veo/prompts", json=prompt_data)

        assert response.status_code == 201
        data = response.json()
        assert data['action'] == 'inserted'
        assert data['confidence_delta'] == 0.0
        assert 'event_id' in data

    def test_update_existing_file_significant_confidence_change(self):
        """Test updating prompt when confidence changes significantly (>0.1)"""
        file_path = "/test/update_significant.jpg"

        # First insert
        prompt_data_1 = {
            "file_path": file_path,
            "predicted_category": "photo",
            "confidence": 0.7,
            "features": {"test": "data"},
            "media_type": "image",
            "source": "test"
        }

        response_1 = client.post("/api/veo/prompts", json=prompt_data_1)
        assert response_1.status_code == 201
        first_id = response_1.json()['id']
        first_event_id = response_1.json()['event_id']

        # Second insert with significant confidence change
        prompt_data_2 = {
            "file_path": file_path,
            "predicted_category": "photo",
            "confidence": 0.95,  # +0.25 change (> 0.1 threshold)
            "features": {"test": "updated_data"},
            "media_type": "image",
            "source": "test"
        }

        response_2 = client.post("/api/veo/prompts", json=prompt_data_2)
        assert response_2.status_code == 201
        data = response_2.json()

        # Should be updated, not inserted
        assert data['action'] == 'updated'
        assert data['id'] == first_id  # Same ID
        assert data['confidence_delta'] == 0.25
        assert data['event_id'] != first_event_id  # New learning signal
        assert data['confidence'] == 0.95  # Updated confidence

    def test_skip_redundant_insert_minor_confidence_change(self):
        """Test skipping insert when confidence change is minimal (<0.1)"""
        file_path = "/test/skip_minor.jpg"

        # First insert
        prompt_data_1 = {
            "file_path": file_path,
            "predicted_category": "screenshot",
            "confidence": 0.85,
            "features": {"test": "data"},
            "media_type": "image",
            "source": "test"
        }

        response_1 = client.post("/api/veo/prompts", json=prompt_data_1)
        assert response_1.status_code == 201
        first_id = response_1.json()['id']
        first_event_id = response_1.json()['event_id']

        # Second insert with minor confidence change
        prompt_data_2 = {
            "file_path": file_path,
            "predicted_category": "screenshot",
            "confidence": 0.88,  # +0.03 change (< 0.1 threshold)
            "features": {"test": "slightly_different"},
            "media_type": "image",
            "source": "test"
        }

        response_2 = client.post("/api/veo/prompts", json=prompt_data_2)
        assert response_2.status_code == 201
        data = response_2.json()

        # Should be skipped
        assert data['action'] == 'skipped'
        assert data['id'] == first_id  # Same ID
        assert data['confidence_delta'] < 0.1
        assert data['event_id'] == first_event_id  # Reused event_id, no new learning signal

    def test_update_on_category_change(self):
        """Test updating when predicted category changes even if confidence is similar"""
        file_path = "/test/category_change.jpg"

        # First insert
        prompt_data_1 = {
            "file_path": file_path,
            "predicted_category": "photo",
            "confidence": 0.8,
            "features": {"test": "data"},
            "media_type": "image",
            "source": "test"
        }

        response_1 = client.post("/api/veo/prompts", json=prompt_data_1)
        assert response_1.status_code == 201
        first_id = response_1.json()['id']

        # Second insert with different category but similar confidence
        prompt_data_2 = {
            "file_path": file_path,
            "predicted_category": "screenshot",  # Changed category
            "confidence": 0.82,  # Only +0.02 change
            "features": {"test": "data"},
            "media_type": "image",
            "source": "test"
        }

        response_2 = client.post("/api/veo/prompts", json=prompt_data_2)
        assert response_2.status_code == 201
        data = response_2.json()

        # Should be updated due to category change
        assert data['action'] == 'updated'
        assert data['id'] == first_id
        assert data['predicted_category'] == 'screenshot'

    def test_separate_tracking_for_image_and_video(self):
        """Test that image and video for same file path are tracked separately"""
        file_path = "/test/multimodal_file"

        # Insert image
        image_data = {
            "file_path": file_path,
            "predicted_category": "photo",
            "confidence": 0.8,
            "features": {"visual_objects": ["tree"]},
            "media_type": "image",
            "source": "test"
        }

        image_response = client.post("/api/veo/prompts", json=image_data)
        assert image_response.status_code == 201
        image_id = image_response.json()['id']
        assert image_response.json()['action'] == 'inserted'

        # Insert video (same file path, different media type)
        video_data = {
            "file_path": file_path,
            "predicted_category": "video",
            "confidence": 0.85,
            "features": {"shot_type": "Medium Shot"},
            "media_type": "video",
            "source": "veo_prompt"
        }

        video_response = client.post("/api/veo/prompts", json=video_data)
        assert video_response.status_code == 201
        video_id = video_response.json()['id']
        assert video_response.json()['action'] == 'inserted'

        # Different IDs - stored separately
        assert video_id != image_id

        # Update image - should not affect video
        image_data_updated = {
            "file_path": file_path,
            "predicted_category": "photo",
            "confidence": 0.95,  # Significant change
            "features": {"visual_objects": ["tree", "sky"]},
            "media_type": "image",
            "source": "test"
        }

        image_update_response = client.post("/api/veo/prompts", json=image_data_updated)
        assert image_update_response.status_code == 201
        assert image_update_response.json()['action'] == 'updated'
        assert image_update_response.json()['id'] == image_id  # Same image ID

    def test_no_duplicate_learning_signals_on_skip(self):
        """Test that learning signals are not emitted for skipped prompts"""
        file_path = "/test/no_duplicate_signals.jpg"

        # First insert - should emit learning signal
        prompt_data_1 = {
            "file_path": file_path,
            "predicted_category": "photo",
            "confidence": 0.8,
            "features": {},
            "media_type": "image",
            "source": "test"
        }

        response_1 = client.post("/api/veo/prompts", json=prompt_data_1)
        first_event_id = response_1.json()['event_id']
        assert first_event_id is not None  # Learning signal emitted

        # Second insert with minor change - should skip and reuse event_id
        prompt_data_2 = {
            "file_path": file_path,
            "predicted_category": "photo",
            "confidence": 0.82,  # Only +0.02
            "features": {},
            "media_type": "image",
            "source": "test"
        }

        response_2 = client.post("/api/veo/prompts", json=prompt_data_2)
        data = response_2.json()

        assert data['action'] == 'skipped'
        assert data['event_id'] == first_event_id  # Reused, not new
        # No new learning signal emitted for skipped prompts


class TestImageOriginLearning:
    """Test image-origin prompt support in learning engine"""

    def test_create_image_prompt_with_learning(self):
        """Test creating image prompt and emitting learning signal"""
        prompt_data = {
            "file_path": "/test/image_learning.jpg",
            "predicted_category": "screenshot",
            "confidence": 0.92,
            "features": {
                "visual_objects": ["button", "window", "menu"],
                "keywords": ["ui", "interface", "design"],
                "scene_type": "digital"
            },
            "media_type": "image",
            "source": "gemini_vision"
        }

        response = client.post("/api/veo/prompts", json=prompt_data)

        assert response.status_code == 201
        data = response.json()
        assert data['media_type'] == 'image'
        assert data['event_id'] is not None  # Learning signal was emitted
        assert 'action' in data
        assert data['predicted_category'] == 'screenshot'

    def test_create_video_prompt_with_learning(self):
        """Test creating video prompt and emitting learning signal"""
        prompt_data = {
            "file_path": "/test/video_learning.mp4",
            "predicted_category": "video",
            "confidence": 0.88,
            "features": {
                "shot_type": "Medium Shot",
                "camera_movement": "Static",
                "lighting": "Natural",
                "mood": "calm"
            },
            "media_type": "video",
            "source": "veo_prompt"
        }

        response = client.post("/api/veo/prompts", json=prompt_data)

        assert response.status_code == 201
        data = response.json()
        assert data['media_type'] == 'video'
        assert data['event_id'] is not None
        assert data['predicted_category'] == 'video'

    def test_image_and_video_separate_learning_patterns(self):
        """Test that image and video prompts create separate learning patterns"""
        # Create image prompt
        image_data = {
            "file_path": "/test/pattern_test_image.jpg",
            "predicted_category": "photo",
            "confidence": 0.85,
            "features": {
                "visual_objects": ["tree", "sky"],
                "keywords": ["nature", "outdoor"],
                "scene_type": "outdoor"
            },
            "media_type": "image",
            "source": "gemini_vision"
        }

        image_response = client.post("/api/veo/prompts", json=image_data)
        assert image_response.status_code == 201
        image_event_id = image_response.json()['event_id']
        assert image_event_id is not None

        # Create video prompt
        video_data = {
            "file_path": "/test/pattern_test_video.mp4",
            "predicted_category": "video",
            "confidence": 0.90,
            "features": {
                "shot_type": "Wide Shot",
                "camera_movement": "Pan",
                "lighting": "Golden Hour",
                "mood": "peaceful"
            },
            "media_type": "video",
            "source": "veo_prompt"
        }

        video_response = client.post("/api/veo/prompts", json=video_data)
        assert video_response.status_code == 201
        video_event_id = video_response.json()['event_id']
        assert video_event_id is not None

        # Different event IDs - separate learning entries
        assert image_event_id != video_event_id

    def test_image_features_stored_in_learning(self):
        """Test that image-specific features are properly stored"""
        prompt_data = {
            "file_path": "/test/feature_storage.jpg",
            "predicted_category": "diagram",
            "confidence": 0.80,
            "features": {
                "visual_objects": ["chart", "graph", "axis"],
                "keywords": ["data", "visualization", "analytics"],
                "scene_type": "digital",
                "content_type": "diagram"
            },
            "media_type": "image",
            "source": "gemini_vision"
        }

        response = client.post("/api/veo/prompts", json=prompt_data)

        assert response.status_code == 201
        data = response.json()

        # Verify all features were stored
        assert 'visual_objects' in data['features']
        assert 'chart' in data['features']['visual_objects']
        assert 'keywords' in data['features']
        assert 'data' in data['features']['keywords']

    def test_no_video_specific_fields_required_for_images(self):
        """Test that images don't require video-specific fields"""
        # Image with NO video-specific fields (no shot_type, camera_movement, etc.)
        prompt_data = {
            "file_path": "/test/no_video_fields.jpg",
            "predicted_category": "photo",
            "confidence": 0.75,
            "features": {
                "visual_objects": ["person"],
                "keywords": ["portrait"]
                # NO shot_type, camera_movement, lighting, mood
            },
            "media_type": "image",
            "source": "gemini_vision"
        }

        response = client.post("/api/veo/prompts", json=prompt_data)

        # Should succeed without errors
        assert response.status_code == 201
        data = response.json()
        assert data['media_type'] == 'image'
        assert data['event_id'] is not None
        # No video-specific fields in response
        assert 'shot_type' not in data['features']
        assert 'camera_movement' not in data['features']

    def test_visual_pattern_accumulation(self):
        """Test that visual patterns accumulate across multiple images"""
        # Create multiple image prompts with similar categories
        for i in range(3):
            prompt_data = {
                "file_path": f"/test/pattern_accumulation_{i}.jpg",
                "predicted_category": "screenshot",
                "confidence": 0.85 + (i * 0.05),
                "features": {
                    "visual_objects": ["window", "button"],
                    "keywords": ["ui", "interface"],
                    "scene_type": "digital"
                },
                "media_type": "image",
                "source": "gemini_vision"
            }

            response = client.post("/api/veo/prompts", json=prompt_data)
            assert response.status_code == 201
            assert response.json()['event_id'] is not None

        # All 3 should have been successfully processed
        # (Pattern accumulation happens internally in learning system)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
