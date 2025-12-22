import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_system_status():
    print("Testing /api/system/status...")
    try:
        response = requests.get(f"{BASE_URL}/api/system/status")
        response.raise_for_status()
        data = response.json()
        
        orchestration = data.get("orchestration", {})
        print(f"Orchestration Status: {orchestration}")
        
        if "files_processed" in orchestration:
            print("✅ 'files_processed' found in orchestration info")
        else:
            print("❌ 'files_processed' MISSING in orchestration info")
            
        if orchestration.get("last_run"):
            print(f"✅ Last run: {orchestration['last_run']}")
        else:
            print("⚠️ No last run data found (might be normal if never run)")
            
    except Exception as e:
        print(f"❌ Error testing system status: {e}")

def test_learning_stats():
    print("\nTesting /api/settings/learning-stats...")
    try:
        response = requests.get(f"{BASE_URL}/api/settings/learning-stats")
        response.raise_for_status()
        data = response.json()
        
        print(f"Learning Stats: {data}")
        
        keys_to_check = ['image_events', 'video_events', 'audio_events', 'document_events', 'total_learning_events']
        all_passed = True
        for key in keys_to_check:
            if key in data:
                print(f"✅ '{key}' found: {data[key]}")
            else:
                print(f"❌ '{key}' MISSING")
                all_passed = False
        
        if all_passed:
            print("✅ All expected learning stat keys found")
            
    except Exception as e:
        print(f"❌ Error testing learning stats: {e}")

def test_rollback_operations():
    print("\nTesting /api/rollback/operations...")
    try:
        response = requests.get(f"{BASE_URL}/api/rollback/operations?days=7")
        response.raise_for_status()
        data = response.json()
        
        if "data" in data and "operations" in data["data"]:
            ops = data["data"]["operations"]
            print(f"✅ Found {len(ops)} operations in 'data.operations'")
            if len(ops) > 0:
                print(f"✅ First op ID: {ops[0].get('operation_id')}")
        else:
            print("❌ 'data.operations' path MISSING in response")
            
    except Exception as e:
        print(f"❌ Error testing rollback operations: {e}")

if __name__ == "__main__":
    test_system_status()
    test_learning_stats()
    test_rollback_operations()
