import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from emergency_space_protection import EmergencySpaceProtection, SpaceEmergency
from bulletproof_deduplication import BulletproofDeduplicator

class TestEmergencySpaceProtectionIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/test_data_dedup")
        self.esp = EmergencySpaceProtection(base_dir=str(self.test_dir))

        # Ensure test files exist
        if not self.test_dir.exists():
            self.test_dir.mkdir(parents=True)

        (self.test_dir / "file1.txt").write_text("content")
        (self.test_dir / "file1_copy.txt").write_text("content")
        (self.test_dir / "file2.txt").write_text("content")
        (self.test_dir / "file3.txt").write_text("different")

    def tearDown(self):
        # Cleanup
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_cleanup_duplicate_files(self):
        # Mock SpaceEmergency
        emergency = MagicMock(spec=SpaceEmergency)
        emergency.affected_directories = [str(self.test_dir)]
        emergency.disk_path = str(self.test_dir)
        emergency.severity = "critical"

        # Mock the deduplicator instance directly on the esp object
        # The esp object is created in setUp, so patching the class afterwards doesn't affect it
        mock_deduplicator = MagicMock()
        mock_deduplicator.scan_directory.return_value = {
            "space_recoverable": 1024 * 1024 * 1024, # 1 GB
            "deleted_files": 10,
            "errors": []
        }

        # Swap the real deduplicator with the mock
        self.esp.deduplicator = mock_deduplicator

        freed_gb = self.esp._cleanup_duplicate_files(emergency)

        # Verify scan_directory called
        mock_deduplicator.scan_directory.assert_called_with(
            Path(self.test_dir),
            execute=True,
            safety_threshold=0.7 # Default for critical
        )

        # Verify return value
        self.assertEqual(freed_gb, 1.0)

    def test_cleanup_duplicate_files_emergency_severity(self):
        emergency = MagicMock(spec=SpaceEmergency)
        emergency.affected_directories = [str(self.test_dir)]
        emergency.disk_path = str(self.test_dir)
        emergency.severity = "emergency"

        # Mock the deduplicator instance directly
        mock_deduplicator = MagicMock()
        mock_deduplicator.scan_directory.return_value = {
            "space_recoverable": 0,
            "deleted_files": 0,
            "errors": []
        }

        self.esp.deduplicator = mock_deduplicator

        self.esp._cleanup_duplicate_files(emergency)

        # Verify scan_directory called with lower threshold
        mock_deduplicator.scan_directory.assert_called_with(
            Path(self.test_dir),
            execute=True,
            safety_threshold=0.5
        )

if __name__ == '__main__':
    unittest.main()
