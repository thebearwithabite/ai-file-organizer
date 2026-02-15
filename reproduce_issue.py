
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import app
except ImportError as e:
    print(f"Error importing app: {e}")
    sys.exit(1)

client = TestClient(app)

class TestOpenSecurity(unittest.TestCase):
    @patch("subprocess.run")
    def test_argument_injection_blocked(self, mock_run):
        # Payload starting with -
        payload = {"path": "-a Calculator"}

        response = client.post("/api/open-file", json=payload)

        print(f"Argument Injection Test: Status {response.status_code}, Detail: {response.json().get('detail')}")

        # Expect 400 Bad Request
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file path", response.json().get("detail", ""))

        # Verify subprocess.run was NOT called
        self.assertFalse(mock_run.called)

    @patch("subprocess.run")
    def test_nonexistent_file_blocked(self, mock_run):
        # Payload for non-existent file
        payload = {"path": "nonexistent_file_12345.txt"}

        response = client.post("/api/open-file", json=payload)

        print(f"Non-existent File Test: Status {response.status_code}, Detail: {response.json().get('detail')}")

        # Expect 404 Not Found
        self.assertEqual(response.status_code, 404)
        self.assertIn("File not found", response.json().get("detail", ""))

        # Verify subprocess.run was NOT called
        self.assertFalse(mock_run.called)

    @patch("subprocess.run")
    def test_valid_file_secure_execution(self, mock_run):
        # Create a dummy file to test with
        dummy_file = "test_safe.txt"
        with open(dummy_file, "w") as f:
            f.write("test")

        try:
            # Mock successful execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""

            payload = {"path": dummy_file}

            response = client.post("/api/open-file", json=payload)

            print(f"Valid File Test: Status {response.status_code}, Message: {response.json().get('message')}")

            # Expect 200 OK
            self.assertEqual(response.status_code, 200)

            # Verify subprocess.run was called with SAFE arguments
            self.assertTrue(mock_run.called)
            args, _ = mock_run.call_args
            command_list = args[0]
            print(f"Command executed: {command_list}")

            # Check for ['open', '--', dummy_file]
            expected_command = ['open', '--', dummy_file]
            self.assertEqual(command_list, expected_command)

        finally:
            if os.path.exists(dummy_file):
                os.remove(dummy_file)

if __name__ == "__main__":
    unittest.main()
