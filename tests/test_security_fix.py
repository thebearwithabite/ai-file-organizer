import pytest
from pathlib import Path
from security_utils import validate_path_is_safe

def test_validate_path_is_safe_default_roots():
    """Test validation with default allowed roots (when allowed_roots=None)"""
    # Standard user paths should be allowed
    assert validate_path_is_safe(Path.home() / "Downloads/file.txt")
    assert validate_path_is_safe(Path.home() / "Desktop/file.txt")
    assert validate_path_is_safe(Path.home() / "Documents/file.txt")

    # Nested paths
    assert validate_path_is_safe(Path.home() / "Downloads/subdir/file.txt")

    # System paths should be denied
    assert not validate_path_is_safe(Path("/etc/passwd"))
    assert not validate_path_is_safe(Path("/usr/bin/python"))
    assert not validate_path_is_safe(Path.home() / ".ssh/id_rsa") # Hidden folder not in allow list

def test_validate_path_is_safe_custom_roots():
    """Test validation with custom allowed roots"""
    custom_roots = [Path("/tmp/allowed")]

    # Allowed
    assert validate_path_is_safe(Path("/tmp/allowed/file.txt"), custom_roots)

    # Denied
    assert not validate_path_is_safe(Path("/tmp/other/file.txt"), custom_roots)
    # Even Downloads should be denied if not in custom_roots
    assert not validate_path_is_safe(Path.home() / "Downloads/file.txt", custom_roots)

def test_path_traversal_attempts():
    """Test protection against path traversal"""
    allowed_roots = [Path("/home/user/allowed")]

    # Simple traversal
    assert not validate_path_is_safe(Path("/home/user/allowed/../secret.txt"), allowed_roots)

    # Check resolved path (assuming /home/user/allowed exists or resolving works logically)
    # Note: validate_path_within_base resolves paths. If paths don't exist, resolve() usually returns absolute path but doesn't follow symlinks if they don't exist.
    # But logical resolution removes '..'

    # Using strings
    assert not validate_path_is_safe("/home/user/allowed/../secret.txt", allowed_roots)

    # Valid traversal staying inside
    assert validate_path_is_safe("/home/user/allowed/subdir/../file.txt", allowed_roots)
