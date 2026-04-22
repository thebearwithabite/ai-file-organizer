
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from adaptive_background_monitor import AdaptiveBackgroundMonitor

@pytest.fixture
def monitor_setup():
    # Create a temp directory structure
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)

    downloads_dir = base_path / "Downloads"
    downloads_dir.mkdir()

    desktop_dir = base_path / "Desktop"
    desktop_dir.mkdir()

    other_dir = base_path / "Documents"
    other_dir.mkdir()

    # Create files in Downloads
    for i in range(10):
        (downloads_dir / f"file_{i}.txt").touch()

    # Create directories in Downloads (should be ignored)
    for i in range(5):
        (downloads_dir / f"dir_{i}").mkdir()

    # Create files in Desktop
    for i in range(5):
        (desktop_dir / f"file_{i}.txt").touch()

    # Create files in Other (should be ignored)
    for i in range(3):
        (other_dir / f"file_{i}.txt").touch()

    monitor = AdaptiveBackgroundMonitor(base_dir=str(base_path))
    # Mock watch_directories to point to our temp dirs
    monitor.watch_directories = {
        "downloads": {"path": downloads_dir},
        "desktop": {"path": desktop_dir},
        "documents": {"path": other_dir}
    }

    yield monitor, downloads_dir, desktop_dir, other_dir

    # Cleanup
    shutil.rmtree(temp_dir)

def test_count_unorganized_files_correctness(monitor_setup):
    monitor, downloads_dir, desktop_dir, other_dir = monitor_setup

    # Expected: 10 in Downloads + 5 in Desktop = 15
    count = monitor._count_unorganized_files()
    assert count == 15, f"Expected 15 files, got {count}"

def test_count_ignores_directories(monitor_setup):
    monitor, downloads_dir, desktop_dir, other_dir = monitor_setup

    # Add more directories to Downloads
    (downloads_dir / "new_dir").mkdir()

    count = monitor._count_unorganized_files()
    assert count == 15, "Directories should be ignored"

def test_count_ignores_other_folders(monitor_setup):
    monitor, downloads_dir, desktop_dir, other_dir = monitor_setup

    # Add files to Documents (should be ignored by _count_unorganized_files logic)
    (other_dir / "new_file.txt").touch()

    count = monitor._count_unorganized_files()
    # Logic in _count_unorganized_files: if path.name.lower() in ['downloads', 'desktop']
    # So Documents should be skipped.
    assert count == 15, "Should only count files in Downloads or Desktop"
