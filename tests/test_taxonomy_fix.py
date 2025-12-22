import requests
import json
import time

BASE_URL = "http://localhost:8000/api/taxonomy"

def test_taxonomy_operations():
    print("🚀 Testing Taxonomy Operations...")
    test_id = f"test_cat_{int(time.time())}"
    
    # 1. Get initial taxonomy
    print("\n--- 1. Get Taxonomy ---")
    resp = requests.get(f"{BASE_URL}/")
    if resp.status_code != 200:
        print(f"❌ Failed to get taxonomy: {resp.status_code}")
        return
    categories = resp.json()
    print(f"✅ Loaded {len(categories)} categories")

    # 2. Create a new category
    print("\n--- 2. Create New Category ---")
    new_cat = {
        "id": test_id,
        "display_name": "Verification Category",
        "folder_name": f"Verif_{int(time.time())}",
        "parent_path": "99_TEMP_PROCESSING",
        "keywords": ["test_verification"],
        "confidence": 0.99
    }
    resp = requests.post(f"{BASE_URL}/create", json=new_cat)
    if resp.status_code == 200:
        print("✅ Category created successfully")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"❌ Failed to create category: {resp.status_code} - {resp.text}")
        return

    # 3. Verify it exists
    print("\n--- 3. Verify Category ---")
    resp = requests.get(f"{BASE_URL}/{test_id}")
    if resp.status_code == 200:
        print("✅ Category verified")
    else:
        print(f"❌ Category not found after creation")
        return

    # 4. Rename the category (Tests physical root fix)
    print("\n--- 4. Rename Category ---")
    rename_data = {"new_name": f"Renamed_{int(time.time())}"}
    resp = requests.post(f"{BASE_URL}/{test_id}/rename", json=rename_data)
    if resp.status_code == 200:
        print("✅ Category renamed successfully")
        print(json.dumps(resp.json(), indent=2))
    elif resp.status_code == 409:
         print(f"⚠️ Rename blocked (expected if folder exists): {resp.json()['detail']['reason']}")
    else:
        print(f"❌ Failed to rename category: {resp.status_code} - {resp.text}")

    # 5. Clean up (Optional, but let's leave it for manual check if needed, or delete)
    # The taxonomy service doesn't have a DELETE endpoint yet, but that's fine for now.
    
    print("\n🎉 Taxonomy operations test complete!")

if __name__ == "__main__":
    test_taxonomy_operations()
