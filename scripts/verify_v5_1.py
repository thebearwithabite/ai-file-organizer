
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hierarchical_organizer import HierarchicalOrganizer
from unified_classifier import UnifiedClassificationService, save_metadata_sidecar
from taxonomy_service import TaxonomyService
from gdrive_integration import get_metadata_root

def test_audio_routing():
    print("\n--- Testing Audio Routing (V5.1) ---")
    # Setup Taxonomy
    config_dir = get_metadata_root() / "config"
    taxonomy = TaxonomyService(config_dir)
    organizer = HierarchicalOrganizer(taxonomy_service=taxonomy)
    
    # Test case: Voice recording that should match 'audio_vox'
    test_file = Path("conversation_with_ryan.mp3")
    category = "audio_vox"
    
    path, meta = organizer.build_hierarchical_path(category, test_file)
    print(f"File: {test_file.name}")
    print(f"Category: {category}")
    print(f"Target Path: {path}")
    
    # Verify it doesn't contain 'Unsorted'
    if "Unsorted" in path:
        print("❌ FAILED: 'Unsorted' found in path.")
        return False
    
    # Verify it maps to Projects (if project detected) or Manual_Review
    if not path.startswith("Projects") and not path.startswith("99_TEMP_PROCESSING/Manual_Review"):
        print(f"❌ FAILED: Unexpected root for {category}: {path}")
        return False
        
    print("✅ Audio routing verified.")
    return True

def test_sidecar_relocation():
    print("\n--- Testing Sidecar Relocation (V5.1) ---")
    
    # Setup a temp test file
    test_dir = project_root / "temp_test_v5_1"
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True)
    
    test_file = test_dir / "test_document.pdf"
    test_file.write_text("dummy content")
    
    dummy_classification = {
        "category": "tech_literature",
        "confidence": 0.95,
        "source": "Test"
    }
    
    # Save sidecar
    save_metadata_sidecar(test_file, dummy_classification)
    
    # Check for hidden folder
    metadata_dir = test_dir / ".metadata"
    expected_sidecar = metadata_dir / "test_document.pdf.json"
    
    print(f"Checking for sidecar at: {expected_sidecar}")
    if not expected_sidecar.exists():
        print("❌ FAILED: Sidecar not found in hidden .metadata folder.")
        # Check if it's in the old location
        old_sidecar = test_dir / "test_document.pdf.json"
        if old_sidecar.exists():
            print("❌ FAILED: Sidecar found in old non-hidden location.")
        return False
    
    import json
    with open(expected_sidecar, 'r') as f:
        data = json.load(f)
        if data['classification']['category'] != "tech_literature":
            print("❌ FAILED: Sidecar content mismatch.")
            return False
            
    print("✅ Sidecar relocation verified.")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    return True

if __name__ == "__main__":
    success = True
    if not test_audio_routing(): success = False
    if not test_sidecar_relocation(): success = False
    
    if success:
        print("\n🎉 V5.1 VERIFICATION PASSED.")
        sys.exit(0)
    else:
        print("\n💥 V5.1 VERIFICATION FAILED.")
        sys.exit(1)
