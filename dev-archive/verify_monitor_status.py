import sys
import time
from pathlib import Path

# Add project root to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from background_monitor import EnhancedBackgroundMonitor

def test_monitor_status():
    print("Initializing EnhancedBackgroundMonitor...")
    monitor = EnhancedBackgroundMonitor()
    
    # Start monitor briefly to set start_time (though it's set in __init__)
    monitor.running = True
    
    print("Getting status...")
    status = monitor.status()
    
    print(f"Status keys: {status.keys()}")
    
    required_keys = ['uptime_seconds', 'running', 'files_processed_24h']
    missing_keys = [key for key in required_keys if key not in status]
    
    if missing_keys:
        print(f"FAILED: Missing keys: {missing_keys}")
        sys.exit(1)
        
    if not isinstance(status['uptime_seconds'], int):
        print(f"FAILED: uptime_seconds is not an int: {type(status['uptime_seconds'])}")
        sys.exit(1)
        
    print(f"SUCCESS: Status contains all required keys. Uptime: {status['uptime_seconds']}s")

if __name__ == "__main__":
    test_monitor_status()
