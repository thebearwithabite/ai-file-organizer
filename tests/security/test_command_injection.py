"""
Security Regression Tests - Command Injection Prevention

Tests for CWE-78: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')
Verifies that critical endpoints (like open-file) prevent command injection via argument injection.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Mock modules that might not be available or cause issues
sys.modules['api.services'] = MagicMock()
sys.modules['api.rollback_service'] = MagicMock()
sys.modules['api.veo_prompts_api'] = MagicMock()
sys.modules['security_utils'] = MagicMock()
sys.modules['gdrive_integration'] = MagicMock()
sys.modules['universal_adaptive_learning'] = MagicMock()
sys.modules['easy_rollback_system'] = MagicMock()
sys.modules['adaptive_background_monitor'] = MagicMock()
sys.modules['confidence_system'] = MagicMock()
sys.modules['automated_deduplication_service'] = MagicMock()
sys.modules['emergency_space_protection'] = MagicMock()
sys.modules['orchestrate_staging'] = MagicMock()
sys.modules['api.taxonomy_router'] = MagicMock()
sys.modules['api.identity_router'] = MagicMock()
sys.modules['api.veo_studio_api'] = MagicMock()
sys.modules['api.veo_brain_api'] = MagicMock()
sys.modules['pid_lock'] = MagicMock()

# Import app from main
from main import app

client = TestClient(app)

class TestOpenFileCommandInjection:
    """Test /api/open-file endpoint for command injection vulnerabilities"""

    def test_open_file_resolves_dashed_filename(self):
        """
        Verify that a filename starting with a dash (e.g. '-a Calculator')
        is resolved to an absolute path, preventing it from being interpreted
        as a command argument.
        """
        payload = "-a Calculator"

        # Create a temporary file to simulate existence (though resolution works regardless)
        with open(payload, 'w') as f:
            f.write("test")

        try:
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value.returncode = 0

                response = client.post("/api/open-file", json={"path": payload})

                # Verify successful response
                assert response.status_code == 200

                # Verify that the path passed to subprocess.run is the absolute path
                # and NOT the original payload starting with "-"
                expected_safe_path = str(Path(payload).resolve())

                # Check if subprocess.run was called with the SAFE resolved path
                mock_subprocess.assert_called_with(
                    ['open', expected_safe_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                # Ensure the path starts with / (or driver letter)
                assert expected_safe_path.startswith("/") or ":" in expected_safe_path
        finally:
            if os.path.exists(payload):
                os.remove(payload)

    def test_open_url_security(self):
        """Verify that valid URLs are still allowed and passed correctly"""
        payload = "https://google.com"

        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            response = client.post("/api/open-file", json={"path": payload})

            mock_subprocess.assert_called_with(
                ['open', payload],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert response.status_code == 200

    def test_invalid_dashed_path_rejection(self):
        """
        Verify that an invalid path starting with a dash is rejected
        if it cannot be resolved safely or fails validation.
        """
        payload = "-invalid-path-that-does-not-exist"

        # We expect a 400 error because the path likely won't exist, resolution might behave weirdly,
        # or the fallback check will catch it.
        # In our implementation:
        # 1. Path(payload).resolve() -> /abs/path/-invalid... (starts with /)
        # 2. exists() -> False -> warning logged
        # 3. safe_path does NOT start with -
        # 4. subprocess.run() called with absolute path

        # Wait, if we want to test REJECTION, we need to mock failure of resolution
        # or rely on the fallback check.

        with patch('pathlib.Path.resolve', side_effect=Exception("Resolution failed")):
            response = client.post("/api/open-file", json={"path": payload})

            assert response.status_code == 400
            assert "Invalid path" in response.json()['detail']

    def test_command_injection_via_semicolon(self):
        """
        Verify that shell metacharacters like semicolon are not executed
        because subprocess.run uses list arguments (shell=False).
        """
        payload = "file.txt; echo hacked"
        # We create file "file.txt"
        with open("file.txt", 'w') as f: f.write("test")

        try:
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value.returncode = 0
                response = client.post("/api/open-file", json={"path": payload})

                # subprocess.run should be called with resolved path of "file.txt; echo hacked"
                # which treats the whole string as a filename.
                expected = str(Path(payload).resolve())
                mock_subprocess.assert_called_with(
                    ['open', expected],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
        finally:
             if os.path.exists("file.txt"): os.remove("file.txt")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
