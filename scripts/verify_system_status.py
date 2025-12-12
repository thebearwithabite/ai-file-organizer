#!/usr/bin/env python3
"""
Verify System Status Reporting
-----------------------------
Checks if the new unified get_status() in SystemService works correctly.
"""
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services import SystemService

def verify_status():
    print("🔍 Verifying System Service Status...")
    
    service = SystemService()
    
    # Inject a mock monitor for testing
    class MockMonitor:
        adaptive_rules = ["rule1", "rule2"]
        def status(self):
            return {
                "watch_directories": {"/tmp": True},
                "processed_files": 100,
                "errors_24h": 0,
                "last_scan": "2025-01-01T00:00:00"
            }
            
    SystemService.set_monitor(MockMonitor())
    
    # Update orchestration stats
    SystemService.update_orchestration_status({
        "last_run": "2025-01-01T12:00:00",
        "files_touched": 83
    })
    
    # Get status
    try:
        status = service.get_status()
        print(json.dumps(status, indent=2))
        
        # Verify structure
        assert "backend_status" in status
        assert "monitor" in status
        assert "orchestration" in status
        assert status["monitor"]["rules_loaded"] == 2
        assert status["orchestration"]["files_touched"] == 83
        
        print("✅ System Status Verification Passed!")
        return True
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        return False

if __name__ == "__main__":
    verify_status()
