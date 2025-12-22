import requests
import json

BASE_URL = "http://localhost:8000"

def test_triage_pending():
    print("Testing /api/triage/files_to_review...")
    try:
        response = requests.get(f"{BASE_URL}/api/triage/files_to_review")
        response.raise_for_status()
        data = response.json()
        print(f"✅ Success! Found {len(data)} files for triage.")
        if len(data) > 0:
            print(f"Sample file: {data[0].get('file_name')} - Category: {data[0].get('classification', {}).get('category')}")
    except Exception as e:
        print(f"❌ Error testing triage pending: {e}")

def test_triage_scan():
    print("\nTesting /api/triage/trigger_scan...")
    try:
        response = requests.post(f"{BASE_URL}/api/triage/trigger_scan")
        response.raise_for_status()
        data = response.json()
        files = data.get("files", [])
        print(f"✅ Success! Scanned and found {len(files)} files.")
    except Exception as e:
        print(f"❌ Error testing triage scan: {e}")

if __name__ == "__main__":
    test_triage_pending()
    test_triage_scan()
