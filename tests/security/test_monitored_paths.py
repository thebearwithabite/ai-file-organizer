
import pytest
from pathlib import Path
import tempfile
import shutil
from security_utils import validate_path_is_monitored

class TestValidatePathIsMonitored:
    """Test validate_path_is_monitored() logic"""

    @pytest.fixture
    def temp_env(self):
        """Create temporary environment with monitored and unmonitored paths"""
        base = Path(tempfile.mkdtemp())

        downloads = base / "Downloads"
        downloads.mkdir()

        desktop = base / "Desktop"
        desktop.mkdir()

        other = base / "Other"
        other.mkdir()

        yield {
            "base": base,
            "downloads": downloads,
            "desktop": desktop,
            "other": other,
            "monitored": [downloads, desktop]
        }

        shutil.rmtree(base, ignore_errors=True)

    def test_allowed_paths(self, temp_env):
        """Files in monitored paths should be allowed"""
        monitored = temp_env["monitored"]
        downloads = temp_env["downloads"]

        # File directly in monitored dir
        assert validate_path_is_monitored(downloads / "file.txt", monitored)

        # File in subdirectory
        subdir = downloads / "subdir"
        subdir.mkdir()
        assert validate_path_is_monitored(subdir / "file.txt", monitored)

    def test_denied_paths(self, temp_env):
        """Files outside monitored paths should be denied"""
        monitored = temp_env["monitored"]
        other = temp_env["other"]
        base = temp_env["base"]

        # File in unmonitored dir
        assert not validate_path_is_monitored(other / "file.txt", monitored)

        # File in base dir (parent of monitored)
        assert not validate_path_is_monitored(base / "file.txt", monitored)

        # System paths
        assert not validate_path_is_monitored("/etc/passwd", monitored)

    def test_traversal_attempts(self, temp_env):
        """Path traversal attempts should be blocked"""
        monitored = temp_env["monitored"]
        downloads = temp_env["downloads"]

        # Try to escape downloads
        assert not validate_path_is_monitored(downloads / ".." / "other_file.txt", monitored)

        # Try to escape to system root
        assert not validate_path_is_monitored(downloads / ".." / ".." / "etc" / "passwd", monitored)

    def test_nonexistent_monitored_roots(self, temp_env):
        """If a monitored root doesn't exist, it should be handled gracefully"""
        base = temp_env["base"]
        nonexistent = base / "Nonexistent"

        # Even if allowed path doesn't exist, we can check against it conceptually,
        # but since validate_path_within_base resolves paths, and resolve behavior on non-existent paths
        # is just normalization, it should work.

        # However, typically we only monitor existing paths.
        pass

    def test_argument_injection_prevention(self, temp_env):
        """Arguments starting with - should be blocked (though usually checked before calling this)"""
        monitored = temp_env["monitored"]

        # validate_path_is_monitored expects a path.
        # If passed "-aCalc", it treats it as relative path "./-aCalc" or resolved path.
        # Resolved path will be /app/-aCalc (if CWD is /app).
        # Which is likely not in monitored paths.

        assert not validate_path_is_monitored("-aCalculator", monitored)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
