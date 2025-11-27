import sys
import os
from pathlib import Path
import logging

# Add project dir to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from background_monitor import EnhancedBackgroundMonitor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("background_monitor").setLevel(logging.DEBUG)

def force_scan():
    # Initialize monitor with Google Drive path
    gdrive_path = os.path.expanduser("~/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com")
    monitor = EnhancedBackgroundMonitor(additional_watch_paths=[gdrive_path])
    monitor.running = True # Manually set running to True for test
    
    # Find the Google Drive config
    gdrive_config = None
    for name, config in monitor.watch_directories.items():
        if "googledrive" in name:
            gdrive_config = config
            break
            
    if not gdrive_config:
        print("Error: Google Drive path not found in monitor configuration")
        return

    print(f"Forcing scan of: {gdrive_config['path']}")
    
    # Force scan
    stats = monitor._scan_directory(gdrive_config, "manual-force")
    print(f"Scan complete. Stats: {stats}")

if __name__ == "__main__":
    force_scan()
