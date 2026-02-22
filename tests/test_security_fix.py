import sys
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock dependencies BEFORE importing main
sys.modules['google'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google_drive_auth'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.http'] = MagicMock()

# Mock gdrive_integration and its exports
mock_gdrive = MagicMock()
mock_gdrive.get_metadata_root = lambda: Path("/tmp/metadata")
mock_gdrive.get_ai_organizer_root = lambda: Path("/tmp/ai_organizer")
sys.modules['gdrive_integration'] = mock_gdrive

# Also mock other services
sys.modules['universal_adaptive_learning'] = MagicMock()
sys.modules['adaptive_background_monitor'] = MagicMock()
sys.modules['confidence_system'] = MagicMock()
sys.modules['automated_deduplication_service'] = MagicMock()
sys.modules['emergency_space_protection'] = MagicMock()
sys.modules['orchestrate_staging'] = MagicMock()
sys.modules['api.services'] = MagicMock()
sys.modules['api.rollback_service'] = MagicMock()
sys.modules['api.veo_prompts_api'] = MagicMock()
sys.modules['api.veo_studio_api'] = MagicMock()
sys.modules['api.veo_brain_api'] = MagicMock()
sys.modules['api.taxonomy_router'] = MagicMock()
sys.modules['api.identity_router'] = MagicMock()
sys.modules['pid_lock'] = MagicMock()
sys.modules['content_extractor'] = MagicMock()

# Import security_utils and path_config to ensure they are real
import security_utils
from security_utils import validate_path_is_safe
from path_config import paths

# Import main (the endpoint logic)
import main
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_validate_path_is_safe_logic():
    """Test the core validation logic against system paths"""
    home = Path.home()
    docs = home / "Documents"
    downloads = home / "Downloads"

    # Safe paths
    assert validate_path_is_safe(docs / "file.txt") is True, "Documents/file.txt should be safe"
    assert validate_path_is_safe(downloads / "sub/image.png") is True, "Downloads/sub/image.png should be safe"

    # Unsafe paths
    assert validate_path_is_safe(Path("/etc/passwd")) is False, "/etc/passwd should be unsafe"
    assert validate_path_is_safe(Path("/")) is False, "Root should be unsafe"

    # Traversal attack strings (resolved)
    # Note: If /etc/passwd exists, resolve() will make it absolute /etc/passwd
    # which is not in Documents/Downloads
    traversal = docs / "../../etc/passwd"
    assert validate_path_is_safe(traversal) is False, "Path traversal should be blocked"

@pytest.mark.asyncio
async def test_get_file_content_security():
    """Test that get_file_content endpoint enforces security"""
    mock_request = MagicMock()

    # 1. Test blocked path
    unsafe_path = "/etc/passwd"

    # Verify it raises 403
    with pytest.raises(HTTPException) as excinfo:
        await main.get_file_content(mock_request, path=unsafe_path)

    assert excinfo.value.status_code == 403
    assert "Access denied" in str(excinfo.value.detail)

    # 2. Test safe path
    # We construct a path that matches 'downloads' in path_config
    safe_path = str(paths.get_path('downloads') / "test_safe.txt")

    # Mock existence checks so we don't need actual file
    with patch('pathlib.Path.exists', return_value=True):
        with patch('main.range_requests_response') as mock_response:
            mock_response.return_value = "STREAM_RESPONSE"

            response = await main.get_file_content(mock_request, path=safe_path)
            assert response == "STREAM_RESPONSE"

@pytest.mark.asyncio
async def test_open_file_security():
    """Test that open_file endpoint enforces security"""
    mock_request = MagicMock()
    mock_request.path = "/etc/passwd"

    with pytest.raises(HTTPException) as excinfo:
        await main.open_file(mock_request)

    assert excinfo.value.status_code == 403
    assert "Access denied" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_preview_security():
    """Test that get_file_preview_text enforces security"""
    unsafe_path = "/etc/passwd"

    with pytest.raises(HTTPException) as excinfo:
        await main.get_file_preview_text(path=unsafe_path)

    assert excinfo.value.status_code == 403
    assert "Access denied" in str(excinfo.value.detail)
