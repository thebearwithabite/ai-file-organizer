
import pytest
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from adaptive_background_monitor import AdaptiveBackgroundMonitor
from universal_adaptive_learning import UniversalAdaptiveLearning
from confidence_system import ADHDFriendlyConfidenceSystem

class TestCooldownLogic:

    @pytest.fixture
    def monitor(self):
        """Fixture to create a monitor instance with mocks"""
        monitor = AdaptiveBackgroundMonitor(base_dir="/tmp/test_monitor")
        monitor.learning_system = MagicMock(spec=UniversalAdaptiveLearning)
        monitor.confidence_system = MagicMock(spec=ADHDFriendlyConfidenceSystem)
        monitor.rollback_system = MagicMock()

        # Mock staging monitor
        monitor.staging_monitor = MagicMock()
        monitor.staging_monitor.config = {"staging_days": 7}
        monitor.staging_monitor.record_observation.return_value = True

        # Mock logging to avoid clutter
        monitor.logger = MagicMock()

        # Mock extract keywords to avoid import errors or FS issues
        monitor._extract_quick_keywords = MagicMock(return_value=["test", "file"])

        return monitor

    @patch('adaptive_background_monitor.datetime')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    def test_new_file_deferred(self, mock_stat, mock_exists, mock_datetime, monitor):
        """Test that a file created less than 7 days ago is deferred"""

        # Setup mock file
        file_path = Path("/tmp/test_monitor/new_file.txt")
        mock_exists.return_value = True

        # Simulate "Now"
        now = datetime(2023, 10, 10, 12, 0, 0)
        mock_datetime.now.return_value = now
        mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp

        # Simulate file created 1 day ago
        file_mtime = (now - timedelta(days=1)).timestamp()
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_mtime = file_mtime
        mock_stat_obj.st_size = 1024
        mock_stat.return_value = mock_stat_obj

        # Mock staging age
        monitor.staging_monitor.get_file_age_days.return_value = 1

        # Mock prediction
        monitor.learning_system.predict_user_action.return_value = {
            "predicted_action": {"target_category": "documents"},
            "confidence": 0.9
        }

        # Execute
        result = monitor._handle_new_file_with_cooldown(file_path)

        # Verify
        assert result is False
        # monitor.learning_system.record_classification.assert_called_once() # No longer called in this path
        monitor.staging_monitor.record_observation.assert_called_once()
        monitor.confidence_system.make_confidence_decision.assert_not_called()

        # Check log message (optional but good for debugging)
        # monitor.logger.info.assert_any_call(f"⏳ Deferring move for new_file.txt (1d old)")

    @patch('adaptive_background_monitor.datetime')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    def test_old_file_processed(self, mock_stat, mock_exists, mock_datetime, monitor):
        """Test that a file created 8 days ago is processed"""

        # Setup mock file
        file_path = Path("/tmp/test_monitor/old_file.txt")
        mock_exists.return_value = True

        # Simulate "Now"
        now = datetime(2023, 10, 10, 12, 0, 0)
        mock_datetime.now.return_value = now
        mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp

        # Simulate file created 8 days ago
        file_mtime = (now - timedelta(days=8)).timestamp()
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_mtime = file_mtime
        mock_stat_obj.st_size = 1024
        mock_stat.return_value = mock_stat_obj

        # Mock staging age
        monitor.staging_monitor.get_file_age_days.return_value = 8

        # Mock prediction & Decision
        monitor.learning_system.predict_user_action.return_value = {
            "predicted_action": {"target_location": "/tmp/documents"},
            "confidence": 0.9
        }

        mock_decision = MagicMock()
        mock_decision.requires_user_input = False
        mock_decision.predicted_action = {"target_location": "/tmp/documents"}
        mock_decision.system_confidence = 0.9
        monitor.confidence_system.make_confidence_decision.return_value = mock_decision

        # Mock execution
        monitor._execute_automatic_action = MagicMock(return_value=True)

        # Execute
        result = monitor._handle_new_file_with_cooldown(file_path)

        # Verify
        assert result is True
        monitor.confidence_system.make_confidence_decision.assert_called_once()
        monitor._execute_automatic_action.assert_called_once()

    @patch('adaptive_background_monitor.datetime')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    def test_old_file_low_confidence_deferred(self, mock_stat, mock_exists, mock_datetime, monitor):
        """Test that a file created 8 days ago but low confidence is NOT moved"""

        # Setup mock file
        file_path = Path("/tmp/test_monitor/confusing_file.txt")
        mock_exists.return_value = True

        # Simulate "Now"
        now = datetime(2023, 10, 10, 12, 0, 0)
        mock_datetime.now.return_value = now
        mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp

        # Simulate file created 8 days ago
        file_mtime = (now - timedelta(days=8)).timestamp()
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_mtime = file_mtime
        mock_stat_obj.st_size = 1024
        mock_stat.return_value = mock_stat_obj

        # Mock staging age
        monitor.staging_monitor.get_file_age_days.return_value = 8

        # Mock prediction & Decision (Low Confidence)
        monitor.learning_system.predict_user_action.return_value = {
            "predicted_action": {},
            "confidence": 0.4
        }

        # Mock decision saying "Requires input" or just "No action"
        mock_decision = MagicMock()
        mock_decision.requires_user_input = False
        mock_decision.predicted_action = None # No action determined
        monitor.confidence_system.make_confidence_decision.return_value = mock_decision

        # Mock execution
        monitor._execute_automatic_action = MagicMock()
        monitor._process_single_file = MagicMock() # parent method mock is hard here, we mocked instance

        # Execute
        result = monitor._handle_new_file_with_cooldown(file_path)

        # Verify
        assert result is False
        monitor._execute_automatic_action.assert_not_called()
