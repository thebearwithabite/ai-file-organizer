
import sys
import os
import shutil
import logging
from pathlib import Path
import json

# Setup paths
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TaxonomyCheck")

def test_taxonomy_service():
    print("\n--- Testing Taxonomy Service ---")
    from taxonomy_service import TaxonomyService
    
    # Use a temp config dir
    config_dir = Path("./temp_test_config")
    if config_dir.exists(): shutil.rmtree(config_dir)
    config_dir.mkdir()
    
    service = TaxonomyService(config_dir)
    
    # 1. Check Seeding
    cats = service.get_all_categories()
    print(f"Categories loaded: {len(cats)}")
    if "visual_assets_screenshots" not in cats:
        print("❌ Failed: Default categories not seeded.")
        return False
    print("✅ Seeding successful.")
    
    # 2. Check Resolve Path
    path = service.resolve_path("visual_assets_screenshots")
    print(f"Resolved path for screenshots: {path}")
    if str(path) != "Visual_Assets/Screenshots":
        print(f"❌ Failed: Unexpected path resolution: {path}")
        return False
    print("✅ Path Resolution successful.")
    
    # 3. Check Rename Logic (Dry Run / Mock FS)
    # We create a dummy folder structure locally
    root = config_dir / "fs_root"
    root.mkdir()
    (root / "Visual_Assets" / "Screenshots").mkdir(parents=True)
    
    print("Testing Rename Category...")
    res = service.rename_category("visual_assets_screenshots", "Snaps", root)
    print(f"Rename Result: {res}")
    
    if res["status"] != "success":
        print(f"❌ Rename Failed: {res}")
        return False
        
    expected_path = root / "Visual_Assets" / "Snaps"
    if not expected_path.exists():
         print("❌ Physical Rename failed (folder missing)")
         return False
    print("✅ Physical Rename verified.")
    
    # Check JSON update
    cat = service.get_category("visual_assets_screenshots")
    if cat["folder_name"] != "Snaps":
        print("❌ JSON Update failed")
        return False
    print("✅ JSON Taxonomy Update verified.")
    
    # Cleanup
    shutil.rmtree(config_dir)
    return True

def test_classifier_integration():
    print("\n--- Testing Classifier Integration ---")
    # We need to mock get_metadata_root or ensure it points somewhere safe
    # unify_classifier lazy loads, so we can init it
    try:
        from unified_classifier import UnifiedClassificationService
        print("Init Classifier...")
        ucs = UnifiedClassificationService()
        
        # We can't easily test internal state without mocking dependencies heavily due to GDrive Integration imports
        # But if it imported without error, that's a good sign.
        # Let's check if it has 'taxonomy_service' attribute
        if hasattr(ucs, 'taxonomy_service'):
            print("✅ Classifier has taxonomy_service attached.")
        else:
            print("❌ Classifier missing taxonomy_service.")
            return False
            
        # Test Obvious Pattern
        # We mock a path
        test_path = Path("screenshot_2025.png")
        res = ucs._check_obvious_classification(test_path)
        print(f"Obvious Pattern Check result: {res}")
        
        if res and res['category'] == 'visual_assets_screenshots':
             print("✅ Obvious Pattern matching works via Taxonomy.")
        else:
             print("❌ Obvious Pattern matching failed.")
             return False

    except Exception as e:
        print(f"❌ Classifier Test Failed: {e}")
        return False
    return True

if __name__ == "__main__":
    success = True
    if not test_taxonomy_service(): success = False
    if not test_classifier_integration(): success = False
    
    if success:
        print("\n🎉 ALL TESTS PASSED.")
        sys.exit(0)
    else:
        print("\n💥 SOME TESTS FAILED.")
        sys.exit(1)
