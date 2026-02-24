"""
Tests for validate_path_is_safe security fix.
"""
import pytest
import os
from pathlib import Path
from security_utils import validate_path_is_safe

class TestValidatePathIsSafe:

    @pytest.fixture
    def allowed_roots(self, tmp_path):
        """Create some allowed roots"""
        root1 = tmp_path / "root1"
        root1.mkdir()
        root2 = tmp_path / "root2"
        root2.mkdir()
        return [root1, root2]

    def test_valid_path(self, allowed_roots):
        """Test a valid path inside an allowed root"""
        root1 = allowed_roots[0]
        valid_file = root1 / "test.txt"
        valid_file.touch()

        assert validate_path_is_safe(valid_file, allowed_roots) is True
        assert validate_path_is_safe(str(valid_file), allowed_roots) is True

    def test_path_outside_allowed_roots(self, allowed_roots, tmp_path):
        """Test a path outside allowed roots"""
        outside_file = tmp_path / "outside.txt"
        outside_file.touch()

        assert validate_path_is_safe(outside_file, allowed_roots) is False

    def test_argument_injection(self, allowed_roots):
        """Test paths that look like arguments"""
        root1 = allowed_roots[0]

        # File named -flag inside allowed root
        bad_file = root1 / "-flag"
        bad_file.touch()

        # Even if it's inside allowed root, it should be rejected because of potential injection
        assert validate_path_is_safe(bad_file, allowed_roots) is False
        assert validate_path_is_safe("-flag", allowed_roots) is False

    def test_hidden_files(self, allowed_roots):
        """Test hidden files (starting with .)"""
        root1 = allowed_roots[0]
        hidden_file = root1 / ".hidden"
        hidden_file.touch()

        # Should be rejected by default
        assert validate_path_is_safe(hidden_file, allowed_roots) is False

        # Should be accepted if allow_hidden is True
        assert validate_path_is_safe(hidden_file, allowed_roots, allow_hidden=True) is True

    def test_hidden_directory(self, allowed_roots):
        """Test file inside hidden directory"""
        root1 = allowed_roots[0]
        hidden_dir = root1 / ".config"
        hidden_dir.mkdir()
        file_in_hidden = hidden_dir / "config.json"
        file_in_hidden.touch()

        assert validate_path_is_safe(file_in_hidden, allowed_roots) is False
        assert validate_path_is_safe(file_in_hidden, allowed_roots, allow_hidden=True) is True

    def test_path_traversal(self, allowed_roots):
        """Test path traversal attempts"""
        root1 = allowed_roots[0]
        # ../ outside.txt
        # resolving should detect it's outside
        traversal = root1 / ".." / "outside.txt"
        # Since resolving it makes it point to outside, and outside is not in allowed_roots
        assert validate_path_is_safe(traversal, allowed_roots) is False

    def test_absolute_system_path(self, allowed_roots):
        """Test trying to access /etc/passwd or similar"""
        # Assuming /etc/passwd exists on linux/mac
        # If running on windows, this test might need adjustment or be skipped
        if os.name == 'posix':
            assert validate_path_is_safe("/etc/passwd", allowed_roots) is False

    def test_relative_path_starting_with_dash(self, allowed_roots):
        """Test relative path starting with dash"""
        # e.g. "-a"
        assert validate_path_is_safe("-a", allowed_roots) is False
