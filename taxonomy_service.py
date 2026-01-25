
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configure logger
logger = logging.getLogger(__name__)

class TaxonomyService:
    """
    V3 Category Management System.
    The Authoritative Source of Truth for Classification Taxonomy.
    """
    
    _instances: Dict[str, 'TaxonomyService'] = {}

    @classmethod
    def get_instance(cls, config_dir: Path) -> 'TaxonomyService':
        """Keyed singleton to ensure one instance per config directory"""
        key = str(Path(config_dir).absolute())
        if key not in cls._instances:
            cls._instances[key] = cls(config_dir)
        return cls._instances[key]

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.taxonomy_path = self.config_dir / "taxonomy.json"
        
        # In-memory cache
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.version = "3.0"
        
        self._load_taxonomy()

    def _load_taxonomy(self):
        """Load taxonomy from JSON or seed with defaults"""
        if not self.taxonomy_path.exists():
            logger.info("Taxonomy file not found. Seeding defaults.")
            self._seed_defaults()
            return

        try:
            with open(self.taxonomy_path, 'r') as f:
                data = json.load(f)
                self.categories = data.get("categories", {})
                self.version = data.get("version", "3.0")
            logger.info(f"Loaded {len(self.categories)} categories from taxonomy.")
        except Exception as e:
            logger.error(f"Failed to load taxonomy: {e}")
            # Fallback to empty if critical failure, or raise?
            # For robustness, we might want to backup and re-seed, but let's just log for now
            self.categories = {}

    def _atomic_save(self):
        """Atomic write to prevent corruption"""
        data = {
            "version": self.version,
            "categories": self.categories
        }
        
        # Ensure parent exists
        self.taxonomy_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write to temp file
            fd, tmp_path = tempfile.mkstemp(dir=self.config_dir, text=True)
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            os.replace(tmp_path, self.taxonomy_path)
            logger.debug("Taxonomy saved atomically.")
        except Exception as e:
            logger.error(f"Failed to save taxonomy atomically: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _seed_defaults(self):
        """Seed with Golden Hierarchy roots and categories"""
        defaults = {
            # --- PROJECTS ---
            # --- PROJECTS (Functional Categories) ---
            "audio_vox": {
                "id": "audio_vox",
                "display_name": "VOX",
                "folder_name": "VOX",
                "parent_path": "Projects",
                "path_fingerprint": "Projects/VOX",
                "locked": False,
                "keywords": ["recording", "voice", "dialogue", "vox"],
                "extensions": [".wav", ".mp3", ".aiff"],
                "confidence": 0.85
            },
            "audio_sfx": {
                "id": "audio_sfx",
                "display_name": "SFX",
                "folder_name": "SFX",
                "parent_path": "Projects",
                "path_fingerprint": "Projects/SFX",
                "locked": False,
                "keywords": ["sfx", "sound effect", "foley"],
                "extensions": [".wav", ".mp3", ".aiff"],
                "confidence": 0.85
            },
            "audio_music": {
                "id": "audio_music",
                "display_name": "Music",
                "folder_name": "Music",
                "parent_path": "Projects",
                "path_fingerprint": "Projects/Music",
                "locked": False,
                "keywords": ["theme", "music", "score", "loop"],
                "extensions": [".wav", ".mp3", ".aiff"],
                "confidence": 0.85
            },
            "creative_video": {
                "id": "creative_video",
                "display_name": "Video",
                "folder_name": "Video",
                "parent_path": "Projects",
                "path_fingerprint": "Projects/Video",
                "locked": False,
                "keywords": ["video", "footage", "clip", "render"],
                "extensions": [".mp4", ".mov", ".avi", ".mkv"],
                "confidence": 0.80
            },
            
            # --- TECHNOLOGY ---
            "tech_literature": {
                "id": "tech_literature",
                "display_name": "Literature",
                "folder_name": "Literature",
                "parent_path": "Technology",
                "path_fingerprint": "Technology/Literature",
                "locked": False,
                "aliases": ["Papers", "Books"],
                "keywords": ["journal", "paper", "research", "whitepaper"],
                "extensions": [".pdf"],
                "confidence": 0.70
            },
            "tech_reference": {
                "id": "tech_reference",
                "display_name": "Reference Materials",
                "folder_name": "Reference Materials",
                "parent_path": "Technology",
                "path_fingerprint": "Technology/Reference Materials",
                "locked": False,
                "aliases": ["Docs", "Manuals"],
                "keywords": ["manual", "documentation", "guide"],
                "extensions": [".md", ".txt"],
                "confidence": 0.60
            },

            # --- BUSINESS MANAGEMENT ---
            "biz_contracts": {
                "id": "biz_contracts",
                "display_name": "Contracts",
                "folder_name": "Contracts",
                "parent_path": "Business Management",
                "path_fingerprint": "Business Management/Contracts",
                "locked": False,
                "aliases": ["agreement", "NDA"],
                "keywords": ["contract", "agreement", "nda", "terms"],
                "extensions": [".pdf"],
                "confidence": 0.90
            },
            "biz_financials": {
                "id": "biz_financials",
                "display_name": "Financials",
                "folder_name": "Financials",
                "parent_path": "Business Management",
                "path_fingerprint": "Business Management/Financials",
                "locked": False,
                "aliases": ["Accounting", "Invoices"],
                "keywords": ["invoice", "receipt", "payment", "billing", "budget"],
                "extensions": [".xlsx", ".xls", ".csv", ".pdf"],
                "confidence": 0.85
            },

            # --- FINANCIALS (PERSONAL) ---
            "fin_taxes": {
                "id": "fin_taxes",
                "display_name": "Taxes",
                "folder_name": "Taxes",
                "parent_path": "Financials",
                "path_fingerprint": "Financials/Taxes",
                "locked": False,
                "aliases": ["IRS", "Tax_Returns"],
                "keywords": ["tax", "1099", "w2", "deduction"],
                "extensions": [".pdf"],
                "confidence": 0.95
            },
            "fin_receipts": {
                "id": "fin_receipts",
                "display_name": "Receipts & Memberships",
                "folder_name": "Receipts/Memberships/Etc.",
                "parent_path": "Financials",
                "path_fingerprint": "Financials/Receipts_Memberships",
                "locked": False,
                "aliases": [],
                "keywords": ["receipt", "subscription", "membership"],
                "extensions": [".pdf", ".jpg", ".png"],
                "confidence": 0.80
            },

            # --- PERSONAL ---
            "personal_identity": {
                "id": "personal_identity",
                "display_name": "Identity",
                "folder_name": "Identity",
                "parent_path": "Personal",
                "path_fingerprint": "Personal/Identity",
                "locked": False,
                "aliases": ["Passport", "ID"],
                "keywords": ["passport", "id card", "license", "birth certificate"],
                "extensions": [".pdf", ".jpg"],
                "confidence": 0.95
            },
            "personal_photos": {
                "id": "personal_photos",
                "display_name": "Photos",
                "folder_name": "Photos",
                "parent_path": "Personal",
                "path_fingerprint": "Personal/Photos",
                "locked": False,
                "keywords": ["birthday", "family", "vacation"],
                "extensions": [".jpg", ".png", ".heic"],
                "confidence": 0.70
            },
            "personal_documents": {
                "id": "personal_documents",
                "display_name": "Documents",
                "folder_name": "documents",
                "parent_path": "Personal",
                "path_fingerprint": "Personal/documents",
                "locked": False,
                "aliases": [],
                "keywords": [],
                "extensions": [".pdf", ".docx", ".pages"],
                "confidence": 0.50
            }
        }
        self.categories = defaults
        self._atomic_save()

    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        return self.categories.get(category_id)

    def get_all_categories(self) -> Dict[str, Dict[str, Any]]:
        return self.categories

    def resolve_path(self, category_id: str, project_root: str = "") -> Path:
        """Resolve physical path for a category"""
        cat = self.categories.get(category_id)
        if not cat:
            return Path("Unsorted")
        
        # V3 Path Construction
        # parent_path + folder_name
        parent = cat.get("parent_path", "")
        folder = cat.get("folder_name", "")
        
        # Safe combination
        full_path = Path(parent) / folder
        
        # Note: Caller is responsible for prepending Project Root (e.g. ~/Documents)
        # This function returns Relative Path structure from a root
        return full_path

    def update_category(self, category_id: str, updates: Dict[str, Any]):
        """Update metadata (keywords, aliases) without renaming folders"""
        if category_id not in self.categories:
            raise KeyError(f"Category {category_id} not found")
        
        # Block protected fields from this method
        blocked = ["id", "folder_name", "parent_path", "path_fingerprint"]
        clean_updates = {k: v for k, v in updates.items() if k not in blocked}
        
        self.categories[category_id].update(clean_updates)
        self._atomic_save()

    def add_category(self, category_data: Dict[str, Any]):
        """Add a new category to the taxonomy"""
        category_id = category_data.get("id")
        if not category_id:
            raise ValueError("Category ID is required")
        
        if category_id in self.categories:
            raise ValueError(f"Category {category_id} already exists")
        
        # Ensure required fields exist
        required_fields = ["display_name", "folder_name"]
        for field in required_fields:
            if field not in category_data:
                raise ValueError(f"Field {field} is required for new category")
        
        # Default fields
        new_cat = {
            "id": category_id,
            "display_name": category_data["display_name"],
            "folder_name": category_data["folder_name"],
            "parent_path": category_data.get("parent_path", ""),
            "locked": False,
            "aliases": category_data.get("aliases", []),
            "keywords": category_data.get("keywords", []),
            "extensions": category_data.get("extensions", []),
            "confidence": category_data.get("confidence", 0.5)
        }
        
        # Generate fingerprint
        parent = new_cat["parent_path"]
        folder = new_cat["folder_name"]
        new_cat["path_fingerprint"] = str(Path(parent) / folder) if parent else folder
        
        self.categories[category_id] = new_cat
        self._atomic_save()
        logger.info(f"Added new category: {category_id}")

    def rename_category(self, category_id: str, new_name: str, root_dir: Path) -> Dict[str, Any]:
        """
        Rename a Category -> Triggers Filesystem Rename.
        
        Args:
            category_id: ID of category to rename
            new_name: New folder name (display_name usually follows)
            root_dir: Absolute path to the physical root (e.g. ~/Documents)
            
        Returns:
            Dict with status and details
        """
        if category_id not in self.categories:
             return {"status": "error", "message": "Category not found"}

        cat = self.categories[category_id]
        
        # Check Locked
        if cat.get("locked", False):
             return {"status": "blocked", "reason": "category_locked"}

        old_folder = cat.get("folder_name")
        parent = cat.get("parent_path", "")
        
        if old_folder == new_name:
            return {"status": "skipped", "message": "Name unchanged"}

        # Calculate Paths
        old_rel_path = Path(parent) / old_folder
        new_rel_path = Path(parent) / new_name
        
        old_abs_path = root_dir / old_rel_path
        new_abs_path = root_dir / new_rel_path
        
        # SAFETY CHECK 1: Fingerprint Collision
        new_fingerprint = str(new_rel_path)
        for cid, data in self.categories.items():
            if cid != category_id and data.get("path_fingerprint") == new_fingerprint:
                return {
                    "status": "blocked", 
                    "reason": "fingerprint_collision",
                    "conflict_category_id": cid
                }

        # SAFETY CHECK 2: Target Exists & Non-Empty
        if new_abs_path.exists():
            if any(new_abs_path.iterdir()): # Check if not empty
                return {
                    "status": "blocked",
                    "reason": "target_exists_and_not_empty",
                    "path": str(new_abs_path)
                }
            # If empty, we can technically overwrite/merge, but safer to block or reuse?
            # User said "Refuse to act if Target folder already exists AND is non-empty"
            # So empty target is technically allowed, but we might just overwrite?
            # Let's assume we proceed if empty.

        # Perform Physical Rename
        try:
            if old_abs_path.exists():
                logger.info(f"Renaming physical folder: {old_abs_path} -> {new_abs_path}")
                new_abs_path.parent.mkdir(parents=True, exist_ok=True)
                old_abs_path.rename(new_abs_path)
            else:
                logger.warning(f"Physical folder missing: {old_abs_path}. Updating taxonomy only.")

            # Update Taxonomy
            cat["folder_name"] = new_name
            cat["display_name"] = new_name # Usually they sync
            cat["path_fingerprint"] = new_fingerprint
            
            self._atomic_save()
            return {"status": "success", "old_path": str(old_rel_path), "new_path": str(new_rel_path)}

        except Exception as e:
            logger.error(f"Rename failed: {e}")
            return {"status": "error", "message": str(e)}

    def handle_physical_rename(self, old_abs_path: Path, new_abs_path: Path, root_dir: Path):
        """
        Handle Filesystem Rename -> Update Taxonomy.
        Called by Background Monitor (after debounce).
        """
        # Convert to relative paths
        try:
            old_rel = old_abs_path.relative_to(root_dir)
            new_rel = new_abs_path.relative_to(root_dir)
        except ValueError:
            logger.debug("Rename outside root, ignoring.")
            return

        old_fingerprint = str(old_rel)
        
        # Find matching category
        target_cat_id = None
        for cid, data in self.categories.items():
            if data.get("path_fingerprint") == old_fingerprint:
                target_cat_id = cid
                break
        
        if not target_cat_id:
            logger.debug(f"No category found for path: {old_fingerprint}")
            return

        cat = self.categories[target_cat_id]
        if cat.get("locked", False):
            logger.warning(f"Physical rename detected for LOCKED category {target_cat_id}. Taxonomy Desync Risk!")
            # Ideally we'd move it back, but that's aggressive. For now, we log.
            return

        # Update Taxonomy
        new_name = new_rel.name
        # Check if parent changed?
        # If user moved "Visual_Assets/Screenshots" to "Audio/Screenshots", parent changed.
        # We need to update parent_path too.
        
        new_parent = str(new_rel.parent)
        if new_parent == ".": new_parent = "" # Root handling
        
        logger.info(f"Syncing Taxonomy to FS Rename: {target_cat_id} -> {new_name}")
        
        cat["folder_name"] = new_name
        cat["parent_path"] = new_parent
        cat["path_fingerprint"] = str(new_rel)
        cat["display_name"] = new_name # Update display name too
        
        self._atomic_save()
