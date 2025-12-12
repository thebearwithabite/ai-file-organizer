import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from api.services import SearchService, SystemService

def test_search_service():
    print("🧪 Testing SearchService...")
    try:
        service = SearchService()
        print("✅ SearchService initialized")
        
        # Test search
        results = service.search("test")
        print(f"✅ Search returned {len(results)} results")
        
        # Test indexed count
        count = service.get_indexed_count()
        print(f"✅ Indexed count: {count}")
        
    except Exception as e:
        print(f"❌ SearchService failed: {e}")
        import traceback
        traceback.print_exc()

def test_system_service():
    print("\n🧪 Testing SystemService...")
    try:
        service = SystemService()
        print("✅ SystemService initialized")
        
        # Test status
        status = service.get_status()
        print(f"✅ System status retrieved")
        print(f"   Auth Status: {status.get('authentication_status')}")
        print(f"   Drive User: {status.get('google_drive_user')}")
        
    except Exception as e:
        print(f"❌ SystemService failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search_service()
    test_system_service()
