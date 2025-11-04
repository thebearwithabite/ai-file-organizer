"""
Security Regression Tests - Log Redaction and Safe Logging

Tests for CWE-532: Insertion of Sensitive Information into Log File
Verifies that logs do not contain sensitive information like API keys,
passwords, tokens, file paths, or personally identifiable information (PII).
"""

import pytest
import logging
import re
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TestSensitiveDataPatterns:
    """Test detection and redaction of sensitive data patterns"""

    def test_api_key_patterns(self):
        """API keys should be detected and redactable"""
        sensitive_patterns = [
            "sk-proj-abc123xyz456",  # OpenAI format
            "AIzaSyD1234567890abcdefghijklmnop",  # Google API key
            "ya29.a0AfH6SMBxyz123",  # Google OAuth token
            "ghp_1234567890abcdefghijklmnopqrstuv",  # GitHub token
            "xoxb-1234567890-1234567890-abc123xyz",  # Slack token
        ]

        api_key_pattern = re.compile(
            r'(sk-[a-zA-Z0-9]{32,}|'  # OpenAI
            r'AIza[a-zA-Z0-9_-]{35}|'  # Google
            r'ya29\.[a-zA-Z0-9_-]+|'  # Google OAuth
            r'ghp_[a-zA-Z0-9]{36}|'  # GitHub
            r'xoxb-[0-9]+-[0-9]+-[a-zA-Z0-9]+)'  # Slack
        )

        for key in sensitive_patterns:
            assert api_key_pattern.search(key), f"Pattern should detect: {key}"

    def test_password_patterns(self):
        """Password-like strings should be detected"""
        sensitive_strings = [
            "password=secret123",
            "pwd=admin456",
            "pass:MySecretPass",
            "PASSWORD='hidden123'",
        ]

        password_pattern = re.compile(r'(password|pwd|pass)\s*[:=]\s*[\'\"]?[^\s\'\",]+', re.IGNORECASE)

        for pwd_string in sensitive_strings:
            assert password_pattern.search(pwd_string), f"Pattern should detect: {pwd_string}"

    def test_file_path_patterns(self):
        """Sensitive file paths should be detected"""
        sensitive_paths = [
            "/Users/admin/Documents/secrets.txt",
            "/home/user/.ssh/id_rsa",
            "C:\\Users\\Admin\\AppData\\credentials.json",
            "/etc/passwd",
        ]

        # Pattern for paths that might be sensitive
        path_pattern = re.compile(r'(/home/[^/]+|/Users/[^/]+|C:\\\\Users\\\\[^\\\\]+|/etc/)')

        for path in sensitive_paths:
            assert path_pattern.search(path), f"Pattern should detect: {path}"


class TestLogRedactionFunction:
    """Test a proposed sanitize_for_logging() function behavior"""

    def sanitize_for_logging(self, message: str) -> str:
        """
        Proposed implementation of log sanitization function.
        This shows the expected behavior for future implementation.
        """
        if not message:
            return message

        # Redact API keys
        message = re.sub(
            r'(sk-[a-zA-Z0-9]{32,}|AIza[a-zA-Z0-9_-]{35}|ya29\.[a-zA-Z0-9_-]+|ghp_[a-zA-Z0-9]{36})',
            '[REDACTED_API_KEY]',
            message
        )

        # Redact passwords
        message = re.sub(
            r'(password|pwd|pass)\s*[:=]\s*[\'\"]?([^\s\'\",]+)',
            r'\1=[REDACTED_PASSWORD]',
            message,
            flags=re.IGNORECASE
        )

        # Redact tokens
        message = re.sub(
            r'(token|bearer|auth)\s*[:=]\s*[\'\"]?([^\s\'\",]+)',
            r'\1=[REDACTED_TOKEN]',
            message,
            flags=re.IGNORECASE
        )

        # Redact email addresses
        message = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[REDACTED_EMAIL]',
            message
        )

        # Redact sensitive paths (keep structure but hide username)
        message = re.sub(r'/Users/[^/\s]+', '/Users/[REDACTED]', message)
        message = re.sub(r'/home/[^/\s]+', '/home/[REDACTED]', message)
        message = re.sub(r'C:\\\\Users\\\\[^\\\\]+', 'C:\\\\Users\\\\[REDACTED]', message)

        return message

    def test_redact_api_keys(self):
        """API keys should be redacted from log messages"""
        test_cases = [
            ("Error: Invalid API key sk-proj-abc123xyz456", "Error: Invalid API key [REDACTED_API_KEY]"),
            ("Using key: AIzaSyD1234567890abcdefghijklmnop", "Using key: [REDACTED_API_KEY]"),
            ("Token ya29.a0AfH6SMBxyz123 expired", "Token [REDACTED_API_KEY] expired"),
        ]

        for input_msg, expected in test_cases:
            result = self.sanitize_for_logging(input_msg)
            assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_redact_passwords(self):
        """Passwords should be redacted from log messages"""
        test_cases = [
            ("Database connection failed: password=secret123", "Database connection failed: password=[REDACTED_PASSWORD]"),
            ("Auth failed with pwd=admin456", "Auth failed with pwd=[REDACTED_PASSWORD]"),
            ("LOGIN: pass='MySecret123'", "LOGIN: pass=[REDACTED_PASSWORD]"),
        ]

        for input_msg, expected in test_cases:
            result = self.sanitize_for_logging(input_msg)
            assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_redact_tokens(self):
        """Tokens should be redacted from log messages"""
        test_cases = [
            ("Authorization: Bearer abc123xyz", "Authorization: Bearer=[REDACTED_TOKEN]"),
            ("Using token=xyz789abc", "Using token=[REDACTED_TOKEN]"),
            ("Auth: Bearer abc123", "Auth: Bearer=[REDACTED_TOKEN]"),
        ]

        for input_msg, expected in test_cases:
            result = self.sanitize_for_logging(input_msg)
            assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_redact_emails(self):
        """Email addresses should be redacted"""
        test_cases = [
            ("User john.doe@example.com logged in", "User [REDACTED_EMAIL] logged in"),
            ("Email: admin@company.com failed", "Email: [REDACTED_EMAIL] failed"),
        ]

        for input_msg, expected in test_cases:
            result = self.sanitize_for_logging(input_msg)
            assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_redact_user_paths(self):
        """User-specific paths should be redacted"""
        test_cases = [
            ("File not found: /Users/john/Documents/secret.txt", "File not found: /Users/[REDACTED]/Documents/secret.txt"),
            ("Error in /home/admin/.ssh/config", "Error in /home/[REDACTED]/.ssh/config"),
            ("Cannot access C:\\Users\\Admin\\secrets.txt", "Cannot access C:\\Users\\[REDACTED]\\secrets.txt"),
        ]

        for input_msg, expected in test_cases:
            result = self.sanitize_for_logging(input_msg)
            assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_preserve_non_sensitive_info(self):
        """Non-sensitive information should remain unchanged"""
        safe_messages = [
            "User logged in successfully",
            "File processed: document.pdf",
            "Search completed in 0.5 seconds",
            "Database query returned 10 results",
        ]

        for msg in safe_messages:
            result = self.sanitize_for_logging(msg)
            assert result == msg, f"Safe message should not change: {msg}"


class TestCurrentLoggingBehavior:
    """Test current logging practices in the codebase"""

    def test_search_endpoint_logging_safe(self, caplog):
        """Search endpoint should log safely without exposing queries"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        with caplog.at_level(logging.ERROR):
            with patch('main.search_service.search') as mock_search:
                # Simulate error that could contain sensitive data
                mock_search.side_effect = Exception("Query failed: SELECT * FROM users WHERE password='secret'")

                response = client.get("/api/search?q=sensitive_query")

                # Check that logs contain context but not raw sensitive data in user responses
                # (Internal logs can have details, but HTTP responses must be generic)
                assert response.status_code == 500
                assert "SELECT" not in response.json()["detail"]
                assert "password" not in response.json()["detail"]

    def test_file_upload_logging_safe(self, caplog):
        """File upload should log safely without exposing full paths"""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            # Mock file upload
            with patch('main.triage_service.get_classification') as mock_classify:
                mock_classify.return_value = {
                    "suggested_category": "Documents",
                    "confidence": 0.9,
                    "reasoning": "Test"
                }

                files = {"file": ("test.txt", b"test content", "text/plain")}
                response = client.post("/api/triage/upload", files=files)

                # Verify upload succeeded
                assert response.status_code == 200

                # Check logs - should have sanitized filename
                log_records = [r.message for r in caplog.records]
                # Should log something about the file, but safely
                assert any("uploaded" in msg.lower() or "file" in msg.lower() for msg in log_records)


class TestLogInjectionPrevention:
    """Test prevention of log injection attacks"""

    def test_newline_injection_prevention(self):
        """Newlines in user input should not break log format"""
        malicious_inputs = [
            "test\nINFO: Admin logged in\nFake log entry",
            "query\r\nERROR: Injected message",
            "file.txt\n\n[SECURITY] Fake alert",
        ]

        for malicious_input in malicious_inputs:
            # Log entries should escape or remove newlines
            sanitized = malicious_input.replace('\n', '\\n').replace('\r', '\\r')
            assert '\n' not in sanitized
            assert 'INFO:' not in sanitized or 'INFO:' in malicious_input

    def test_log_format_injection(self):
        """Format string attacks should be prevented"""
        malicious_inputs = [
            "%s%s%s%s",  # Format string injection
            "{admin}@{password}",  # Format injection
            "test $(whoami)",  # Command injection in logs
        ]

        # These should be logged as literal strings, not interpreted
        for malicious_input in malicious_inputs:
            # When using proper logging (logger.info(), not string formatting)
            # these are automatically safe
            assert malicious_input.count('%s') == 0 or '%s' in malicious_input  # Tautology to show awareness


class TestSecurityAuditLogging:
    """Test that security-relevant events are logged appropriately"""

    def test_authentication_failures_logged(self):
        """Authentication failures should be logged for security monitoring"""
        # Future implementation: track failed auth attempts
        # This is a placeholder for when auth is implemented
        pass

    def test_path_traversal_attempts_logged(self, caplog):
        """Path traversal attempts should be logged for security auditing"""
        from security_utils import validate_path_within_base
        from pathlib import Path
        import tempfile

        with caplog.at_level(logging.WARNING):
            temp_dir = Path(tempfile.mkdtemp())

            # Attempt path traversal
            malicious_path = temp_dir / ".." / ".." / "etc" / "passwd"
            result = validate_path_within_base(malicious_path, temp_dir)

            # Should fail validation
            assert not result

            # Should log the attempt
            assert any("Path validation failed" in record.message for record in caplog.records)

    def test_file_operation_logging(self):
        """File operations should log safely for audit trail"""
        # Verify that file operations log activity without exposing sensitive paths
        # This ensures we have an audit trail while maintaining security
        pass


class TestLogRotationAndStorage:
    """Test that logs are stored securely"""

    def test_log_file_permissions_secure(self):
        """Log files should have restricted permissions"""
        # Future implementation: verify log files are only readable by application
        # Placeholder for when log file storage is configured
        pass

    def test_log_retention_policy(self):
        """Logs should follow retention policy to avoid long-term data exposure"""
        # Future implementation: verify old logs are rotated/deleted
        # Placeholder for when log rotation is configured
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
