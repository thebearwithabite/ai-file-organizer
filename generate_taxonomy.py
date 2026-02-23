import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.absolute()))

from gdrive_integration import get_ai_organizer_root, get_metadata_root
from taxonomy_service import TaxonomyService

def main():
    root = get_ai_organizer_root()
    if not root or not root.exists():
        print(f"Drive root not found at {root}")
        return

    metadata_root = get_metadata_root()
    config_dir = metadata_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Using metadata root: {metadata_root}")
    print(f"Using Google Drive root: {root}")

    svc = TaxonomyService(config_dir)

    # 46 Folders exactly? We'll let it discover all of them.
    # Exclude folders starting with '.' and some system folders
    exclude_prefixes = ('.', '_', '99_')
    
    added_count = 0
    for p in root.rglob('*'):
        if not p.is_dir():
            continue
            
        rel_path = p.relative_to(root)
        
        if any(part.startswith(exclude_prefixes) for part in rel_path.parts):
            continue
            
        cat_id = "f_" + "_".join(rel_path.parts).lower().replace(" ", "_").replace("-", "_")
        
        # Don't add if already exists under a different ID by fingerprint?
        # Let's just create a new dict and overwrite it all to guarantee a fresh accurate taxonomy.
        
        parent_path = str(rel_path.parent) if str(rel_path.parent) != "." else ""
        
        cat_data = {
            "id": cat_id,
            "display_name": p.name,
            "folder_name": p.name,
            "parent_path": parent_path,
            "path_fingerprint": str(rel_path),
            "locked": False,
            "confidence": 0.6,
            "keywords": [],
            "extensions": []
        }
        
        # Check if fingerprint already exists
        exists = False
        for ex_cat in svc.categories.values():
            if ex_cat.get("path_fingerprint") == str(rel_path):
                exists = True
                break
                
        if not exists:
            # Inject directly and save later to avoid ValueError
            svc.categories[cat_id] = cat_data
            added_count += 1

    svc._atomic_save()
    print(f"Added {added_count} new categories.")
    print(f"Taxonomy now has {len(svc.categories)} total categories.")
    print(f"Saved to {svc.taxonomy_path}")

if __name__ == '__main__':
    main()
