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

        # We need to mock BulletproofDeduplicator inside the method or rely on actual behavior.
        # Since I want to verify integration, I will rely on actual behavior but I need to make sure
        # scan_directory uses a low safety threshold for tests because file ages are 0.

        # In _cleanup_duplicate_files:
        # safety_threshold = 0.7 (or 0.5 for emergency)

        # My test files are new, so safety score will be low (probably < 0.2).
        # To make them deletable, I need to mock BulletproofDeduplicator to return a high safety score
        # OR mock the scan_directory method.

        # Let's mock scan_directory to verify it is called correctly.
        with patch('emergency_space_protection.BulletproofDeduplicator') as MockDeduplicator:
            instance = MockDeduplicator.return_value
            instance.scan_directory.return_value = {
                "space_recoverable": 1024 * 1024 * 1024, # 1 GB
                "deleted_files": 10,
                "errors": []
            }

            freed_gb = self.esp._cleanup_duplicate_files(emergency)

            # Verify initialization
            MockDeduplicator.assert_called_with(str(self.esp.base_dir))

            # Verify scan_directory called
            instance.scan_directory.assert_called_with(
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

        with patch('emergency_space_protection.BulletproofDeduplicator') as MockDeduplicator:
            instance = MockDeduplicator.return_value
            instance.scan_directory.return_value = {
                "space_recoverable": 0,
                "deleted_files": 0,
                "errors": []
            }

            self.esp._cleanup_duplicate_files(emergency)

            # Verify scan_directory called with lower threshold
            instance.scan_directory.assert_called_with(
                Path(self.test_dir),
                execute=True,
                safety_threshold=0.5
            )

if __name__ == '__main__':
    unittest.main()
