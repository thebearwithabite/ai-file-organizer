"""
Security Regression Tests - Path Traversal Prevention

Tests for CWE-22: Improper Limitation of a Pathname to a Restricted Directory
Verifies that sanitize_filename() and validate_path_within_base() prevent path traversal attacks.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from security_utils import sanitize_filename, validate_path_within_base, safe_join_path


class TestSanitizeFilename:
    """Test sanitize_filename() against various path traversal attacks"""

    def test_simple_filename(self):
        """Valid filenames should pass through unchanged"""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my_file-2024.txt") == "my_file-2024.txt"
        assert sanitize_filename("report.final.docx") == "report.final.docx"

    def test_path_traversal_unix_style(self):
        """Unix-style path traversal sequences should be stripped"""
        # Classic path traversal attempts
        assert sanitize_filename("../../../etc/passwd") == "etcpasswd"
        assert sanitize_filename("../../sensitive.txt") == "sensitive.txt"
        assert sanitize_filename("../file.pdf") == "file.pdf"

        # Multiple traversal attempts
        assert sanitize_filename("....//....//etc/passwd") == "etcpasswd"
        assert sanitize_filename("..\\..\\..\\etc\\passwd") == "etcpasswd"

    def test_path_traversal_windows_style(self):
        """Windows-style path traversal sequences should be stripped"""
        assert sanitize_filename("..\\..\\..\\Windows\\System32\\config\\sam") == "WindowsSystem32configsam"
        assert sanitize_filename("..\\sensitive.txt") == "sensitive.txt"
        assert sanitize_filename("C:\\Windows\\System32\\file.txt") == "CWindowsSystem32file.txt"

    def test_absolute_paths_blocked(self):
        """Absolute paths should be converted to just filename"""
        assert sanitize_filename("/etc/passwd") == "etcpasswd"
        assert sanitize_filename("/usr/bin/malicious.sh") == "usrbinmalicious.sh"
        assert sanitize_filename("C:\\Program Files\\app.exe") == "CProgram Filesapp.exe"

    def test_dangerous_characters_removed(self):
        """Special shell characters should be removed"""
        assert sanitize_filename("file;rm -rf /.txt") == "filerm -rf .txt"
        assert sanitize_filename("file`whoami`.txt") == "filewhoami.txt"
        assert sanitize_filename("file$USER.txt") == "fileUSER.txt"
        assert sanitize_filename("file|cat /etc/passwd.txt") == "filecat etcpasswd.txt"

    def test_null_bytes_removed(self):
        """Null bytes should be removed (could bypass extension checks)"""
        # Null byte injection attempts
        result = sanitize_filename("malicious.txt\x00.jpg")
        assert "\x00" not in result

    def test_empty_or_invalid_inputs(self):
        """Empty or invalid inputs should generate safe fallback"""
        assert sanitize_filename("") == "file_" + str(abs(hash("")))
        assert sanitize_filename("..") == "file_" + str(abs(hash("..")))
        assert sanitize_filename(".") == "file_" + str(abs(hash(".")))
        assert sanitize_filename("...") == "file_" + str(abs(hash("...")))

    def test_filename_length_limit(self):
        """Filenames exceeding 255 characters should be truncated"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".txt")  # Extension preserved

    def test_unicode_and_special_chars(self):
        """Unicode and special characters should be handled safely"""
        assert sanitize_filename("файл.txt") == ".txt"  # Cyrillic removed
        assert sanitize_filename("文件.pdf") == ".pdf"  # Chinese removed
        assert sanitize_filename("file™®©.txt") == "file.txt"

    def test_mixed_attack_vectors(self):
        """Combined attack vectors should all be neutralized"""
        assert sanitize_filename("../../../etc/passwd;rm -rf /") == "etcpasswdrm -rf "
        assert sanitize_filename("..\\..\\Windows\\System32\\config\\sam|cat") == "WindowsSystem32configsamcat"


class TestValidatePathWithinBase:
    """Test validate_path_within_base() path containment validation"""

    @pytest.fixture
    def temp_base_dir(self):
        """Create temporary base directory for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_valid_paths_within_base(self, temp_base_dir):
        """Paths legitimately within base should be allowed"""
        assert validate_path_within_base(temp_base_dir / "file.txt", temp_base_dir)
        assert validate_path_within_base(temp_base_dir / "subdir" / "file.txt", temp_base_dir)
        assert validate_path_within_base(temp_base_dir / "a" / "b" / "c" / "file.txt", temp_base_dir)

    def test_path_traversal_attempts_blocked(self, temp_base_dir):
        """Path traversal attempts should be blocked"""
        # Parent directory access
        assert not validate_path_within_base(temp_base_dir / ".." / "evil.txt", temp_base_dir)
        assert not validate_path_within_base(temp_base_dir / ".." / ".." / "etc" / "passwd", temp_base_dir)

        # Absolute paths outside base
        assert not validate_path_within_base(Path("/etc/passwd"), temp_base_dir)
        assert not validate_path_within_base(Path("/tmp/evil.txt"), temp_base_dir)

    def test_symlink_traversal_blocked(self, temp_base_dir):
        """Symlinks pointing outside base should be blocked"""
        # Create symlink pointing outside base (if not in restricted environment)
        try:
            symlink_path = temp_base_dir / "evil_link"
            target_path = Path("/etc/passwd")
            symlink_path.symlink_to(target_path)

            # Symlink should be blocked because it resolves outside base
            assert not validate_path_within_base(symlink_path, temp_base_dir)
        except (OSError, PermissionError):
            # Skip if symlinks not allowed in environment
            pytest.skip("Symlinks not supported in this environment")

    def test_relative_paths_resolved(self, temp_base_dir):
        """Relative paths should be resolved before validation"""
        # Relative path that stays within base
        assert validate_path_within_base("subdir/file.txt", temp_base_dir)

        # Relative path with .. that tries to escape
        assert not validate_path_within_base("../../etc/passwd", temp_base_dir)

    def test_nonexistent_paths_validated(self, temp_base_dir):
        """Nonexistent paths should still be validated (no existence requirement)"""
        # Path doesn't need to exist to be validated
        assert validate_path_within_base(temp_base_dir / "nonexistent" / "file.txt", temp_base_dir)

    def test_error_conditions_fail_secure(self):
        """Validation errors should fail securely (return False)"""
        # Invalid path types should return False
        assert not validate_path_within_base(None, Path("/tmp"))
        assert not validate_path_within_base("/some/path", None)


class TestSafeJoinPath:
    """Test safe_join_path() combined sanitization and validation"""

    @pytest.fixture
    def temp_base_dir(self):
        """Create temporary base directory for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_safe_paths_allowed(self, temp_base_dir):
        """Safe path combinations should succeed"""
        result = safe_join_path(temp_base_dir, "subdir", "file.txt")
        assert result == temp_base_dir / "subdir" / "file.txt"

    def test_path_traversal_raises_error(self, temp_base_dir):
        """Path traversal attempts should raise ValueError"""
        with pytest.raises(ValueError, match="outside base directory"):
            safe_join_path(temp_base_dir, "..", "..", "etc", "passwd")

    def test_parts_sanitized(self, temp_base_dir):
        """Each path component should be sanitized"""
        # Malicious filename in path
        result = safe_join_path(temp_base_dir, "safe_dir", "../evil.txt")
        assert result == temp_base_dir / "safe_dir" / "evil.txt"
        assert ".." not in str(result)


class TestIntegrationScenarios:
    """Integration tests simulating real attack scenarios"""

    @pytest.fixture
    def mock_upload_dir(self):
        """Simulate upload directory"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_file_upload_attack_scenario(self, mock_upload_dir):
        """Simulate malicious file upload with traversal filename"""
        # Attacker tries to upload with malicious filename
        malicious_filename = "../../../../etc/passwd"

        # Security layer sanitizes filename
        safe_filename = sanitize_filename(malicious_filename)
        upload_path = mock_upload_dir / safe_filename

        # Validate path is within upload directory
        assert validate_path_within_base(upload_path, mock_upload_dir)
        assert "etc" not in str(upload_path)
        assert "passwd" in str(upload_path)  # Filename preserved, path removed

    def test_config_path_attack_scenario(self, mock_upload_dir):
        """Simulate attack via user-configurable path"""
        # Attacker tries to configure malicious staging area
        malicious_config = "../../sensitive_data"

        # Validate staging area configuration
        staging_path = Path(malicious_config)
        is_safe = validate_path_within_base(staging_path, mock_upload_dir)

        # Malicious configuration should be rejected
        assert not is_safe

    def test_multi_vector_attack(self, mock_upload_dir):
        """Simulate attack combining multiple techniques"""
        # Attacker combines traversal + special chars + null byte
        attack_filename = "../../../etc/passwd\x00.jpg;rm -rf /"

        # Security layer should neutralize all vectors
        safe_filename = sanitize_filename(attack_filename)
        upload_path = mock_upload_dir / safe_filename

        # Verify all attack components neutralized
        assert ".." not in safe_filename
        assert "/" not in safe_filename
        assert "\x00" not in safe_filename
        assert ";" not in safe_filename
        assert validate_path_within_base(upload_path, mock_upload_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
