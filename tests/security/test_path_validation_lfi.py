import pytest
from pathlib import Path
from main import validate_path_is_safe

def test_validate_path_is_safe_allows_safe_paths(monkeypatch):
    """Test that safe paths within allowed roots are permitted."""
    import main
    safe_root = Path.home() / "Downloads"
    # Mock get_allowed_roots to only return our safe_root
    monkeypatch.setattr(main, 'get_allowed_roots', lambda: [safe_root])

    # Test file inside the root
    safe_file = safe_root / "safe_file.txt"
    assert validate_path_is_safe(safe_file) == True

def test_validate_path_is_safe_blocks_traversal(monkeypatch):
    """Test that path traversal attempts are blocked."""
    import main
    safe_root = Path.home() / "Downloads"
    monkeypatch.setattr(main, 'get_allowed_roots', lambda: [safe_root])

    # Test path traversing out
    unsafe_file = safe_root / ".." / "Desktop" / "unsafe_file.txt"
    assert validate_path_is_safe(unsafe_file) == False

def test_validate_path_is_safe_blocks_argument_injection(monkeypatch):
    """Test that files starting with hyphens are blocked to prevent argument injection."""
    import main
    safe_root = Path.home() / "Downloads"
    monkeypatch.setattr(main, 'get_allowed_roots', lambda: [safe_root])

    # Test argument injection
    unsafe_file = safe_root / "-rf"
    assert validate_path_is_safe(unsafe_file) == False

def test_validate_path_is_safe_blocks_absolute_paths_outside_roots(monkeypatch):
    """Test that absolute paths outside of the allowed roots are blocked."""
    import main
    safe_root = Path.home() / "Downloads"
    monkeypatch.setattr(main, 'get_allowed_roots', lambda: [safe_root])

    # Test absolute path to /etc/passwd
    unsafe_file = Path("/etc/passwd")
    assert validate_path_is_safe(unsafe_file) == False
