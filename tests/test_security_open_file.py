import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Ensure current directory is in python path
sys.path.append(os.getcwd())

from main import app

client = TestClient(app)

def test_open_file_secure_command():
    """
    Test that open-file endpoint uses secure arguments (preventing argument injection).
    """
    file_path = "safe_file.txt"

    # We mock main.Path so that when it's instantiated, it returns our mock object
    with patch("main.Path") as MockPath, \
         patch("main.subprocess.run") as mock_run:

        # Configure the mock path instance
        mock_path_instance = MockPath.return_value
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.__str__.return_value = file_path

        mock_run.return_value.returncode = 0

        response = client.post("/api/open-file", json={"path": file_path})

        # If the code fails (e.g. 500), assert will show it
        assert response.status_code == 200

        # Verify subprocess.run was called securely with '--'
        args, _ = mock_run.call_args
        command_list = args[0]

        # We expect ['open', '--', 'safe_file.txt']
        # If this fails, it means the code is still vulnerable
        assert command_list == ['open', '--', file_path]

def test_open_file_non_existent():
    """
    Test that open-file endpoint rejects non-existent files (preventing URL opening).
    """
    file_path = "missing_file.txt"

    with patch("main.Path") as MockPath, \
         patch("main.subprocess.run") as mock_run:

        mock_path_instance = MockPath.return_value
        mock_path_instance.exists.return_value = False

        response = client.post("/api/open-file", json={"path": file_path})

        # Secure code should return 404
        assert response.status_code == 404
        mock_run.assert_not_called()

def test_open_file_not_a_file():
    """
    Test that open-file endpoint rejects directories (or other non-files) to ensure we check is_file().
    """
    file_path = "/some/directory"

    with patch("main.Path") as MockPath, \
         patch("main.subprocess.run") as mock_run:

        mock_path_instance = MockPath.return_value
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = False # It is a directory

        response = client.post("/api/open-file", json={"path": file_path})

        # Secure code should return 404 (or 400, but 404 for "file not found" is fine)
        assert response.status_code == 404
        mock_run.assert_not_called()
