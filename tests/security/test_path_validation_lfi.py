import pytest
import sys
from pathlib import Path

# Add project root to sys.path if not present (handled by pytest usually but good for standalone)
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from security_utils import validate_path_is_safe
from path_config import paths

@pytest.fixture
def setup_safe_file():
    downloads_dir = paths.get_path('downloads')
    downloads_dir.mkdir(parents=True, exist_ok=True)
    valid_file = downloads_dir / "test_safe_file_lfi.txt"
    valid_file.touch()
    yield valid_file
    if valid_file.exists():
        valid_file.unlink()

@pytest.fixture
def setup_hidden_file():
    downloads_dir = paths.get_path('downloads')
    downloads_dir.mkdir(parents=True, exist_ok=True)
    hidden_file = downloads_dir / ".hidden_test_lfi"
    hidden_file.touch()
    yield hidden_file
    if hidden_file.exists():
        hidden_file.unlink()

def test_system_file_blocked():
    """Verify that system files like /etc/hosts are blocked."""
    # Use str for /etc/hosts to ensure string handling works
    assert not validate_path_is_safe("/etc/hosts")
    # Use Path object too
    assert not validate_path_is_safe(Path("/etc/hosts"))

def test_valid_file_allowed(setup_safe_file):
    """Verify that a valid file in Downloads is allowed."""
    assert validate_path_is_safe(setup_safe_file)
    assert validate_path_is_safe(str(setup_safe_file))

def test_hidden_file_blocked(setup_hidden_file):
    """Verify that a hidden file in Downloads is blocked."""
    assert not validate_path_is_safe(setup_hidden_file)

def test_safe_traversal_allowed(setup_safe_file):
    """Verify that '..' that stays inside safe root is allowed."""
    # downloads/subdir/../test_safe_file.txt
    safe_root = setup_safe_file.parent
    traversal_path = safe_root / "subdir" / ".." / setup_safe_file.name
    # Note: validate_path_is_safe resolves path, so non-existent intermediate dirs (subdir) might be an issue
    # depending on os.path.resolve behavior. But since we check validation, it should be fine.
    # Actually, validate_path_within_base resolves it.
    assert validate_path_is_safe(traversal_path)

def test_unsafe_traversal_blocked(setup_safe_file):
    """Verify that '..' that escapes safe root is blocked."""
    # downloads/../../../../etc/passwd
    safe_root = setup_safe_file.parent
    traversal_path = safe_root / ".." / ".." / ".." / ".." / "etc" / "passwd"
    assert not validate_path_is_safe(traversal_path)
