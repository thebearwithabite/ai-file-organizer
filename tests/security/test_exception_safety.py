"""
Security Regression Tests - Exception Message Safety

Tests for CWE-209: Generation of Error Message Containing Sensitive Information
Verifies that HTTP endpoints return generic error messages without exposing
internal details, stack traces, or sensitive information.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main import app

# Create test client
client = TestClient(app)


class TestSearchEndpointExceptionSafety:
    """Test /api/search endpoint exception handling"""

    def test_search_generic_error_message(self):
        """Search endpoint should return generic error message on failure"""
        with patch('main.search_service.search') as mock_search:
            # Simulate internal error with sensitive information
            mock_search.side_effect = Exception("Database connection failed at 192.168.1.100:5432 with credentials admin:password123")

            response = client.get("/api/search?q=test")

            # Verify generic error message returned
            assert response.status_code == 500
            assert "An error occurred while performing the search" in response.json()["detail"]

            # Verify NO sensitive information exposed
            assert "192.168.1.100" not in response.json()["detail"]
            assert "5432" not in response.json()["detail"]
            assert "admin" not in response.json()["detail"]
            assert "password123" not in response.json()["detail"]
            assert "Database connection failed" not in response.json()["detail"]

    def test_search_no_stack_trace_exposure(self):
        """Search endpoint should not expose stack traces"""
        with patch('main.search_service.search') as mock_search:
            # Simulate error with stack trace
            mock_search.side_effect = ValueError("Invalid database query: SELECT * FROM users WHERE id='malicious'")

            response = client.get("/api/search?q=test")

            # Verify NO stack trace or SQL in response
            assert "ValueError" not in response.json()["detail"]
            assert "SELECT" not in response.json()["detail"]
            assert "FROM users" not in response.json()["detail"]
            assert "Traceback" not in response.json()["detail"]

    def test_search_logs_full_details_internally(self, caplog):
        """Search endpoint should log full error details internally"""
        with caplog.at_level(logging.ERROR):
            with patch('main.search_service.search') as mock_search:
                error_msg = "Internal error: API key abc123xyz expired"
                mock_search.side_effect = Exception(error_msg)

                response = client.get("/api/search?q=test")

                # Verify generic message to user
                assert "An error occurred while performing the search" in response.json()["detail"]

                # Verify full details logged internally
                assert any(error_msg in record.message for record in caplog.records)
                assert any("Search operation failed" in record.message for record in caplog.records)

    def test_search_multiple_error_types(self):
        """Search endpoint should handle different exception types safely"""
        error_types = [
            ValueError("Invalid input: /etc/passwd"),
            RuntimeError("System path: /usr/local/bin/secret"),
            KeyError("Missing API key: sk-abc123"),
            OSError("File not found: /home/user/.ssh/id_rsa"),
        ]

        for error in error_types:
            with patch('main.search_service.search') as mock_search:
                mock_search.side_effect = error

                response = client.get("/api/search?q=test")

                # All should return same generic message
                assert "An error occurred while performing the search" in response.json()["detail"]

                # None should expose error type or details
                assert type(error).__name__ not in response.json()["detail"]
                assert str(error) not in response.json()["detail"]


class TestTriageFilesEndpointExceptionSafety:
    """Test /api/triage/files_to_review endpoint exception handling"""

    def test_files_review_generic_error_message(self):
        """Files review endpoint should return generic error message"""
        with patch('main.triage_service.get_files_for_review') as mock_get_files:
            # Simulate error with internal path information
            mock_get_files.side_effect = Exception("Cannot access /Users/admin/Documents/secret_files/passwords.txt")

            response = client.get("/api/triage/files_to_review")

            # Verify generic message
            assert response.status_code == 500
            assert "An error occurred while retrieving files for review" in response.json()["detail"]

            # Verify NO path exposure
            assert "/Users/admin" not in response.json()["detail"]
            assert "secret_files" not in response.json()["detail"]
            assert "passwords.txt" not in response.json()["detail"]

    def test_files_review_no_username_exposure(self):
        """Files review endpoint should not expose usernames"""
        with patch('main.triage_service.get_files_for_review') as mock_get_files:
            mock_get_files.side_effect = PermissionError("User 'john_admin' does not have permission to access resource")

            response = client.get("/api/triage/files_to_review")

            # Verify NO username exposure
            assert "john_admin" not in response.json()["detail"]
            assert "PermissionError" not in response.json()["detail"]

    def test_files_review_logs_internal_details(self, caplog):
        """Files review endpoint should log internal details"""
        with caplog.at_level(logging.ERROR):
            with patch('main.triage_service.get_files_for_review') as mock_get_files:
                error_msg = "Database connection timeout: host=db.internal.company.com port=5432"
                mock_get_files.side_effect = Exception(error_msg)

                response = client.get("/api/triage/files_to_review")

                # Verify generic user message
                assert "An error occurred while retrieving files for review" in response.json()["detail"]

                # Verify full details logged
                assert any(error_msg in record.message for record in caplog.records)


class TestTriageScanEndpointExceptionSafety:
    """Test /api/triage/trigger_scan endpoint exception handling"""

    def test_trigger_scan_generic_error_message(self):
        """Trigger scan endpoint should return generic error message"""
        with patch('main.triage_service.trigger_scan') as mock_trigger:
            # Simulate error with API key
            mock_trigger.side_effect = Exception("Invalid OpenAI API key: sk-proj-abc123xyz456")

            response = client.post("/api/triage/trigger_scan")

            # Verify generic message
            assert response.status_code == 500
            assert "An error occurred while triggering the scan" in response.json()["detail"]

            # Verify NO API key exposure
            assert "sk-proj-" not in response.json()["detail"]
            assert "abc123xyz456" not in response.json()["detail"]
            assert "OpenAI" not in response.json()["detail"]

    def test_trigger_scan_no_environment_variable_exposure(self):
        """Trigger scan endpoint should not expose environment variables"""
        with patch('main.triage_service.trigger_scan') as mock_trigger:
            mock_trigger.side_effect = Exception("Environment variable GOOGLE_API_KEY not set. Expected format: AIza...")

            response = client.post("/api/triage/trigger_scan")

            # Verify NO environment variable names or values exposed
            assert "GOOGLE_API_KEY" not in response.json()["detail"]
            assert "AIza" not in response.json()["detail"]
            assert "Environment variable" not in response.json()["detail"]

    def test_trigger_scan_logs_internal_details(self, caplog):
        """Trigger scan endpoint should log internal details"""
        with caplog.at_level(logging.ERROR):
            with patch('main.triage_service.trigger_scan') as mock_trigger:
                error_msg = "ChromaDB connection failed: http://localhost:8001/api/v1/collections"
                mock_trigger.side_effect = Exception(error_msg)

                response = client.post("/api/triage/trigger_scan")

                # Verify generic user message
                assert "An error occurred while triggering the scan" in response.json()["detail"]

                # Verify full details logged internally
                assert any(error_msg in record.message for record in caplog.records)


class TestLibraryAPIExceptionSafety:
    """Test backend/library_api.py exception handling"""

    def test_manifest_endpoint_path_validation_errors(self):
        """Manifest endpoint should handle path validation safely"""
        # Import library API separately
        from backend.library_api import app as library_app
        library_client = TestClient(library_app)

        # Test with malicious project name
        response = library_client.get("/api/manifest/../../etc/passwd")

        # Should return 400 or 404, not expose internal paths
        assert response.status_code in [400, 404]

        if response.status_code == 400:
            # If validation fails, should be generic
            assert "Invalid project name" in response.json()["detail"]
            assert "/etc/passwd" not in response.json()["detail"]

    def test_manifest_endpoint_file_not_found(self):
        """Manifest endpoint should handle missing files safely"""
        from backend.library_api import app as library_app
        library_client = TestClient(library_app)

        response = library_client.get("/api/manifest/nonexistent_project")

        # Should return 404 without exposing file system structure
        assert response.status_code == 404
        assert "Manifest not found" in response.json()["detail"]

        # Should NOT expose actual path searched
        assert "05_VEO_PROMPTS" not in response.json()["detail"]
        assert ".json" not in response.json()["detail"]


class TestIntegrationExceptionSafety:
    """Integration tests for exception safety across multiple scenarios"""

    def test_multiple_endpoints_consistent_error_handling(self):
        """All endpoints should use consistent error handling pattern"""
        test_cases = [
            (lambda: client.get("/api/search?q=test"), "search_service.search"),
            (lambda: client.get("/api/triage/files_to_review"), "triage_service.get_files_for_review"),
            (lambda: client.post("/api/triage/trigger_scan"), "triage_service.trigger_scan"),
        ]

        for endpoint_call, patch_target in test_cases:
            with patch(f'main.{patch_target}') as mock_service:
                # Simulate error with sensitive data
                mock_service.side_effect = Exception("SENSITIVE: API_KEY=secret123, DB_PASSWORD=admin456")

                response = endpoint_call()

                # All should return 500
                assert response.status_code == 500

                # None should expose sensitive data
                assert "SENSITIVE" not in response.json()["detail"]
                assert "secret123" not in response.json()["detail"]
                assert "admin456" not in response.json()["detail"]
                assert "Exception" not in response.json()["detail"]

    def test_error_messages_are_user_friendly(self):
        """Error messages should be helpful, not just generic"""
        with patch('main.search_service.search') as mock_search:
            mock_search.side_effect = Exception("Internal error")

            response = client.get("/api/search?q=test")

            # Should be generic but still helpful
            error_message = response.json()["detail"]
            assert "error occurred" in error_message.lower()
            assert "try again" in error_message.lower() or "please" in error_message.lower()

    def test_no_exception_type_leakage(self):
        """Exception class names should not appear in responses"""
        exception_types = [
            ValueError, TypeError, KeyError, AttributeError,
            RuntimeError, OSError, PermissionError
        ]

        for exc_type in exception_types:
            with patch('main.search_service.search') as mock_search:
                mock_search.side_effect = exc_type("Sensitive internal error")

                response = client.get("/api/search?q=test")

                # Exception type name should NOT appear
                assert exc_type.__name__ not in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
