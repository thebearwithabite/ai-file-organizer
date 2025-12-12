
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from universal_adaptive_learning import UniversalAdaptiveLearning

def test_recent_activity():
    print("🧪 Testing Recent Activity...")
    
    # Initialize system
    learning_system = UniversalAdaptiveLearning()
    
    # Record a test event
    test_file = "/tmp/test_file.txt"
    event_id = learning_system.record_learning_event(
        event_type="test_event",
        file_path=test_file,
        original_prediction={"category": "test"},
        user_action={"action": "test_action"},
        confidence_before=0.5,
        context={"test": True}
    )
    print(f"✅ Recorded test event: {event_id}")
    
    # Get recent activity
    activities = learning_system.get_recent_activity(limit=10)
    print(f"📊 Retrieved {len(activities)} activities")
    
    # Verify
    found = False
    for activity in activities:
        if activity["id"] == event_id:
            found = True
            print(f"✅ Found event {event_id} in recent activity")
            print(f"   Type: {activity['type']}")
            print(f"   Timestamp: {activity['timestamp']}")
            break
            
    if not found:
        print("❌ Test event not found in recent activity")
        sys.exit(1)
        
    print("🎉 Recent Activity Test Passed!")

if __name__ == "__main__":
    test_recent_activity()
