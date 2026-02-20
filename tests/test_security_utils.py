
import pytest
from pathlib import Path
from security_utils import validate_path_is_safe, get_allowed_roots, sanitize_filename, validate_path_within_base
from path_config import paths

def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("safe.txt") == "safe.txt"
    assert sanitize_filename("/absolute/path") == "path"

def test_get_allowed_roots():
    roots = get_allowed_roots()
    assert isinstance(roots, list)
    assert len(roots) > 0
    # verify at least one common path
    assert any("Downloads" in str(r) for r in roots)

def test_validate_path_is_safe():
    # Setup allowed paths
    allowed_root = paths.get_path('downloads')

    # Valid path in Downloads
    valid_path = allowed_root / "safe_file.txt"
    assert validate_path_is_safe(valid_path, allow_non_existent=True)

    # Invalid path (absolute)
    invalid_path = Path("/etc/passwd")
    assert not validate_path_is_safe(invalid_path, allow_non_existent=True)

    # Hidden file
    hidden_file = allowed_root / ".hidden"
    assert not validate_path_is_safe(hidden_file, allow_non_existent=True)

def test_validate_path_within_base():
    base = Path("/tmp")
    assert validate_path_within_base(base / "file.txt", base)
    assert not validate_path_within_base(Path("/etc/passwd"), base)
