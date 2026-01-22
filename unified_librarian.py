"""
Unified Librarian (The Conductor)

This is the canonical entry point for all file organization, search, and storage operations.
It enforces the architectural law by composing:

1. LibrarianPolicyEngine (Brain): Decides WHAT to do
2. CloudLibrarian (Muscle): Handles storage I/O
3. HybridLibrarian (Eyes/Search): Handles semantic search (Read-Only)
4. UnifiedClassificationService (Intelligence): content understanding

Architecture:
    UnifiedLibrarian matches the Interface of the old GoogleDriveLibrarian but
    internally delegates to the focused components.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

from librarian_policy import LibrarianPolicyEngine
from gdrive_librarian import GoogleDriveLibrarian as CloudLibrarian
from hybrid_librarian import HybridLibrarian
from unified_classifier import UnifiedClassificationService
from gdrive_integration import get_ai_organizer_root

# Configure logging
logger = logging.getLogger(__name__)

class UnifiedLibrarian:
    """
    The Conductor.
    Orchestrates Policy, Storage, and Search.
    
    This class is the SINGLETON entry point for the API.
    """

    def __init__(self, config_dir: Path, cache_size_gb: float = 2.0, auto_sync: bool = False):
        logger.info(f"🎼 Initializing UnifiedLibrarian (The Conductor)...")
        
        self.config_dir = config_dir
        
        # 1. Cloud Storage (The Muscle)
        # We rename gdrive_librarian imports to CloudLibrarian conceptual model
        self.cloud = CloudLibrarian(
            config_dir=config_dir,
            cache_size_gb=cache_size_gb,
            auto_sync=auto_sync
        )
        
        # 2. Policy Engine (The Brain)
        # Responsible for naming, routing, and business rules
        self.policy = LibrarianPolicyEngine()
        
        # 3. Search Engine (The Eyes)
        # HybridLibrarian handles semantic + keyword search
        # We instantiate it with the AI Organizer Root
        self.search_engine = HybridLibrarian(base_dir=str(get_ai_organizer_root()))
        
        # 4. Intelligence
        self.classifier = UnifiedClassificationService()

        logger.info("✅ UnifiedLibrarian composition complete.")
        
    def initialize(self):
        """Pass-through initialization to components"""
        logger.info("🎼 Conductor initializing components...")
        self.cloud.initialize()
        # Search engine lazy loads, but we can warm it up if needed
        # self.search_engine._init_semantic_search() 
        logger.info("✅ UnifiedLibrarian fully initialized.")

    # --- Delegation Methods ---

    def search(self, query: str, limit: int = 10, **kwargs):
        """Delegate search to HybridLibrarian (Read-Only)"""
        return self.search_engine.search(query, limit=limit, **kwargs)

    def get_file(self, file_path: str):
        """Delegate file retrieval to CloudLibrarian"""
        return self.cloud.get_file(file_path)
    
    def sync(self):
        """Delegate sync to CloudLibrarian"""
        return self.cloud.sync()
        
    def get_status(self) -> Dict[str, Any]:
        """Aggregate status from components for verification"""
        from google_drive_auth import get_auth
        from taxonomy_service import get_taxonomy_service
        
        # Get cloud status (which contains auth info)
        cloud_status = {}
        if hasattr(self.cloud, 'get_system_status'):
            cloud_status = self.cloud.get_system_status()

        # Build unified status
        status = {
            "component": "UnifiedLibrarian",
            "librarian_class": self.__class__.__name__,
            "policy_engine_class": self.policy.__class__.__name__,
            "cloud_class": self.cloud.__class__.__name__,
            "search_class": self.search_engine.__class__.__name__,
            "classifier_class": self.classifier.__class__.__name__,
            "read_only_default": True, 
            "singleton_ids": {
                "auth": str(id(get_auth(self.config_dir))),
                "taxonomy": str(id(get_taxonomy_service(self.config_dir)))
            },
            "cloud": cloud_status, 
            "search": "active" if self.search_engine else "disabled"
        }
        
        # PROXY/MERGE KEY FIELDS FOR LEGACY COMPATIBILITY
        # api/services.py expects these at top level
        if 'authenticated' in cloud_status:
            status['authenticated'] = cloud_status['authenticated']
        if 'auth_info' in cloud_status:
            status['auth_info'] = cloud_status['auth_info']
        if 'drive_root' in cloud_status:
            status['drive_root'] = cloud_status['drive_root']
            
        return status

    # Alias for legacy compatibility (api/services.py calls this)
    get_system_status = get_status

    # --- Passthrough for Legacy Compatibility ---
    # Many parts of the system might still expect methods from GoogleDriveLibrarian.
    # We expose them here but implement them via the new components where possible.
    
    def get_database_stats(self):
        # Implementation via cloud or main DB
        pass

