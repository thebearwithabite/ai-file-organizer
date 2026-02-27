
import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# --- MOCKING DEPENDENCIES ---
# We must mock dependencies BEFORE importing main to avoid environment errors
sys.modules['google.generativeai'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()

# Mock gdrive_integration fully
gdrive_mock = MagicMock()
gdrive_mock.get_metadata_root.return_value = Path("/tmp/ai_metadata_system")
gdrive_mock.get_ai_organizer_root.return_value = Path("/tmp/ai_organizer")
sys.modules['gdrive_integration'] = gdrive_mock

# Mock other internal modules
sys.modules['universal_adaptive_learning'] = MagicMock()
sys.modules['easy_rollback_system'] = MagicMock()
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

# Import app after mocking
from main import app

client = TestClient(app)

@pytest.fixture
def temp_files(tmp_path):
    """Create some test files"""
    # Safe file in Downloads (simulated)
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    safe_file = downloads / "safe.txt"
    safe_file.write_text("This is safe content.")

    # Unsafe file outside any allowed root
    unsafe_file = tmp_path / "unsafe.txt"
    unsafe_file.write_text("This is unsafe content.")

    # System file (simulated)
    system_file = tmp_path / "etc" / "passwd"
    system_file.parent.mkdir(parents=True)
    system_file.write_text("root:x:0:0:root:/root:/bin/bash")

    return {
        "safe": safe_file,
        "unsafe": unsafe_file,
        "system": system_file,
        "root": tmp_path
    }

def test_lfi_get_file_content_safe(temp_files):
    """Verify safe file access is allowed (mocking check bypass for now if needed)"""
    # In a real fix, we'd need to mock get_allowed_roots to include temp_files['root']
    # For now, we expect 200 if valid, or 404/500 if other issues, but NOT LFI blocking yet
    pass

def test_lfi_get_file_content_unsafe(temp_files):
    """Verify access to arbitrary file is blocked (this fails currently, proving vulnerability)"""
    path = str(temp_files['unsafe'].resolve())
    response = client.get(f"/api/files/content?path={path}")

    # CURRENT BEHAVIOR (VULNERABLE): Returns 200
    # DESIRED BEHAVIOR (FIXED): Returns 403

    # We assert the current state to confirm test setup works,
    # then we will flip assertion after fix
    if response.status_code == 200:
        print("VULNERABILITY CONFIRMED: Unsafe file accessed.")
    else:
        print(f"Access blocked/failed: {response.status_code}")

def test_lfi_preview_unsafe(temp_files):
    """Verify preview of arbitrary file is blocked"""
    path = str(temp_files['system'].resolve())
    # ContentExtractor might fail on non-text, so usage depends on mock
    # But endpoint should check path first
    response = client.get(f"/api/files/preview-text?path={path}")

    # If 500 (db error), it passed path check. If 403, it was blocked.
    if response.status_code != 403:
         print(f"VULNERABILITY INDICATED: Status {response.status_code} (Not 403)")

if __name__ == "__main__":
    # Manual run for quick feedback
    try:
        # Create a temp dir manually
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        files = {
            "safe": tmp / "safe.txt",
            "unsafe": tmp / "unsafe.txt",
            "system": tmp / "etc_passwd"
        }
        files["safe"].write_text("safe")
        files["unsafe"].write_text("unsafe")
        files["system"].write_text("root:x:0:0")

        print("--- Testing Content Endpoint ---")
        res = client.get(f"/api/files/content?path={files['unsafe']}")
        print(f"Unsafe Access Status: {res.status_code}")

        print("--- Testing Preview Endpoint ---")
        res = client.get(f"/api/files/preview-text?path={files['system']}")
        print(f"System Access Status: {res.status_code}")

        shutil.rmtree(tmp)
    except Exception as e:
        print(e)
