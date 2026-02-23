
import sys
import os
import pytest
from unittest.mock import MagicMock
from pathlib import Path
import tempfile

# MOCKING DEPENDENCIES BEFORE IMPORTING MAIN
# This is crucial because main.py imports many modules that might not work in the test environment

# Mock google libraries
sys.modules["google"] = MagicMock()
sys.modules["google.oauth2"] = MagicMock()
sys.modules["googleapiclient"] = MagicMock()
sys.modules["googleapiclient.discovery"] = MagicMock()
sys.modules["googleapiclient.http"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()

# Mock internal services that might have side effects
sys.modules["gdrive_integration"] = MagicMock()
sys.modules["universal_adaptive_learning"] = MagicMock()
sys.modules["api.services"] = MagicMock()
sys.modules["api.rollback_service"] = MagicMock()
sys.modules["api.veo_prompts_api"] = MagicMock()
sys.modules["api.veo_studio_api"] = MagicMock()
sys.modules["api.veo_brain_api"] = MagicMock()
sys.modules["api.taxonomy_router"] = MagicMock()
sys.modules["api.identity_router"] = MagicMock()
sys.modules["easy_rollback_system"] = MagicMock()
sys.modules["adaptive_background_monitor"] = MagicMock()
sys.modules["confidence_system"] = MagicMock()
sys.modules["automated_deduplication_service"] = MagicMock()
sys.modules["emergency_space_protection"] = MagicMock()
sys.modules["orchestrate_staging"] = MagicMock()
sys.modules["content_extractor"] = MagicMock()

# We want REAL security_utils to test the fix later, but for now we might mock it if needed
# Actually, main.py imports specific functions. If we want to test the fix, we need main.py to import the REAL functions.
# So we should NOT mock security_utils if possible.
# But we need path_config to work.

# Setup mock for gdrive_integration used in main.py
sys.modules["gdrive_integration"].get_metadata_root = MagicMock(return_value=Path("/tmp/metadata"))
sys.modules["gdrive_integration"].get_ai_organizer_root = MagicMock(return_value=Path("/tmp/organizer"))

# Now try to import app
# We need to be in the root directory for imports to work nicely or set PYTHONPATH
sys.path.append(os.getcwd())

try:
    from main import app
    from fastapi.testclient import TestClient
except ImportError as e:
    pytest.fail(f"Failed to import app: {e}")

client = TestClient(app)

def test_lfi_prevention_content():
    """
    Test that we CANNOT access arbitrary files outside allowed roots.
    """
    # Create a sensitive file outside expected paths (e.g. in /tmp, but clearly not in Downloads/Desktop)
    # We use a temp file which usually goes to /tmp or /var/tmp
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as f:
        f.write("SECRET_DATA_CONTENT")
        sensitive_path = f.name

    try:
        # Try to access it via API
        response = client.get(f"/api/files/content?path={sensitive_path}")

        # Should now return 403 Forbidden
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    finally:
        if os.path.exists(sensitive_path):
            os.unlink(sensitive_path)

def test_lfi_prevention_preview():
    """
    Test LFI prevention in preview-text endpoint
    """
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as f:
        f.write("SECRET_DATA_PREVIEW")
        sensitive_path = f.name

    # Mock content_extractor in main.py context
    # main.py does: from content_extractor import ContentExtractor
    # We already mocked sys.modules["content_extractor"]
    # Configure the mock to return our data
    mock_extractor = sys.modules["content_extractor"].ContentExtractor.return_value
    mock_extractor.extract_content.return_value = {"text": "SECRET_DATA_PREVIEW"}

    try:
        response = client.get(f"/api/files/preview-text?path={sensitive_path}")

        # Should now return 403 Forbidden
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    finally:
        if os.path.exists(sensitive_path):
            os.unlink(sensitive_path)

def test_lfi_prevention_open_file():
    """
    Test LFI prevention in open-file endpoint
    """
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as f:
        f.write("SECRET_DATA_OPEN")
        sensitive_path = f.name

    try:
        response = client.post("/api/open-file", json={"path": sensitive_path})

        # Should now return 403 Forbidden
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    finally:
        if os.path.exists(sensitive_path):
            os.unlink(sensitive_path)
