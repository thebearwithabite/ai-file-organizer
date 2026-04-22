#!/usr/bin/env python3
"""
Unified Librarian Orchestrator
The central integration point that composes Policy, Cloud, Search, and Classification.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from librarian_policy import LibrarianPolicyEngine, PolicyDecision
from gdrive_librarian import GoogleDriveLibrarian
from unified_classifier import UnifiedClassificationService
from gdrive_integration import get_metadata_root, get_ai_organizer_root

logger = logging.getLogger(__name__)

class UnifiedLibrarian:
    """
    High-level orchestrator for the AI File Organizer.
    Composes all lower-level services into a single point of entry.
    """
    
    _instance: Optional['UnifiedLibrarian'] = None

    @classmethod
    def get_instance(cls) -> 'UnifiedLibrarian':
        """Singleton access for the Unified Librarian"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize the orchestration layer"""
        logger.info("🎼 Initializing Unified Librarian Orchestrator...")
        
        self.metadata_root = get_metadata_root()
        self.config_dir = self.metadata_root / "config"
        
        # 1. Classification Brain
        self.classifier = UnifiedClassificationService()
        
        # 2. Policy Engine (Rules & Business Logic)
        self.policy = LibrarianPolicyEngine()
        
        # 3. Cloud & Search System
        self.cloud = GoogleDriveLibrarian(
            config_dir=self.config_dir,
            auto_sync=False # Managed by orchestration
        )
        
        logger.info("✅ Unified Librarian Ready")

    def decide_and_act(self, file_path: Path, dry_run: bool = True) -> Dict[str, Any]:
        """
        The core loop for a single file:
        1. Query Policy (which queries Classifier)
        2. Perform Cloud/Local actions based on Decision
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return {"status": "error", "message": f"File not found: {file_path}"}

        # Step 1: Get Decision from Policy Engine
        decision = self.policy.analyze_file(file_path)
        
        # Step 2: Execute based on decision action
        # (This will be fleshed out as we unify orchestrate_staging.py)
        
        return {
            "file": file_path.name,
            "decision": decision,
            "dry_run": dry_run
        }

    def get_status(self) -> Dict[str, Any]:
        """Unified status for the entire backend system"""
        return {
            "librarian": "online",
            "cloud": self.cloud.get_system_status(),
            "policy": "active",
            "classifier": "ready"
        }
