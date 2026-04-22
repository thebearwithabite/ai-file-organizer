#!/usr/bin/env python3
"""
Librarian Policy Engine
The "Business Logic" layer of the AI Librarian.

Responsible for:
1. Enforcing Wolfhard/Business Contracts (Folder Mappings)
2. Generating Standardized Filenames (Anti-Drift)
3. Determining Lifecycle Actions (Active vs Archive)
4. Returning IMMUTABLE PolicyDecision objects.

Does NOT handle:
- Physical File Operations (Moving/Deleting)
- Cloud API Calls (Google Drive)
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# V3 Integration
from unified_classifier import UnifiedClassificationService
from taxonomy_service import TaxonomyService, get_taxonomy_service
from gdrive_integration import get_metadata_root

# Standard Policy Config
STALE_THRESHOLD_DAYS = 7
UNSORTED_FOLDER_NAMES = ["Downloads", "Desktop", "staging"]

@dataclass(frozen=True)
class PolicyDecision:
    """
    Immutable decision object from the Policy Engine.
    "This is what SHOULD happen", not "This is what I did".
    """
    source_path: Path
    category_id: str
    target_path: Path      # Relative path (e.g. "01_ENTERTAINMENT/...")
    suggested_filename: str
    confidence: float
    rationale: List[str]
    action: str            # "upload", "organize", "archive", "review"
    metadata: Dict[str, Any] = field(default_factory=dict)

class LibrarianPolicyEngine:
    """
    The Brain that decides WHERE files go and WHAT they are named.
    Integrates V3 Taxonomy with Wolfhard/Business Business Rules.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        
        # Initialize Services
        self.classifier = UnifiedClassificationService()
        config_dir = get_metadata_root() / "config"
        self.taxonomy_service = get_taxonomy_service(config_dir)
        
        # --- BUSINESS RULES (Legacy "Wolfhard" Logic) ---
        # Maps "Logical Categories" -> "Physical Drive Paths"
        # This preserves the specific folder structure required by the user
        self.drive_folder_map = {
            # 01_ENTERTAINMENT_MANAGEMENT
            "entertainment_finn_active": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Client Name/2025_Active_Contracts",
            "entertainment_finn_remittances": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Client Name/Financial_Remittances", 
            "entertainment_finn_publicity": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Client Name/Publicity_Projects",
            "entertainment_finn_immigration": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Client NameImmigration_Visa",
            
            # 02_CREATIVE_PRODUCTIONS
            "creative_tptd_episodes": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Episode_Name",
            "creative_tptd_scripts": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Episode_Name/Scripts_Research", 
            "creative_tptd_audio": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Episode_Name/Audio_Assets",
            "creative_tptd_video": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Episode_Name/Video_Assets",

            # 03_BUSINESS_OPERATIONS
            "business_financial_current": "03_BUSINESS_OPERATIONS/Financial_Records/2025_Current",
            "business_tax_accounting": "03_BUSINESS_OPERATIONS/Financial_Records/Tax_Accounting",
            "business_legal_contracts": "03_BUSINESS_OPERATIONS/Legal_Contracts",
            
            # 04_DEVELOPMENT_PROJECTS
            "dev_ai_organizer": "04_DEVELOPMENT_PROJECTS/AI_File_Organizer",
            "dev_bear_threads": "04_DEVELOPMENT_PROJECTS/Bear_Threads",
            
            # 05_STAGING
            "staging_desktop": "05_STAGING_WORKFLOW/Desktop_Processing",
            "staging_uncertain": "05_STAGING_WORKFLOW/Uncertain_Classification",
            
            # 06_ARCHIVE
            "archive_2024": "06_ARCHIVE/2024_Projects"
        }
        
        logger.info("✅ Librarian Policy Engine Initialized")

    def evaluate_file(self, file_path: Path) -> PolicyDecision:
        """
        The Core Decision Loop.
        1. Classify (V3)
        2. Resolve Target (V3 + Business Rules)
        3. Standardize Name (Anti-Drift)
        4. Return Decision
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # --- 0. Age Protection (7-Day Rule) ---
        # If the file is in a dynamic area (Downloads/Desktop), 
        # only organize if it hasn't been touched in 7 days.
        is_stale = True
        parent_name = file_path.parent.name
        
        # Check if file is in an "unsorted" zone
        is_in_unsorted_zone = any(zone.lower() in str(file_path).lower() for zone in UNSORTED_FOLDER_NAMES)
        
        if is_in_unsorted_zone:
            stat = file_path.stat()
            # Check both modified and accessed
            last_activity = max(stat.st_mtime, stat.st_atime)
            age_days = (time.time() - last_activity) / (24 * 3600)
            
            if age_days < STALE_THRESHOLD_DAYS:
                is_stale = False
                logger.info(f"⏳ File '{file_path.name}' is too fresh ({age_days:.1f} days). Skipping auto-organization.")

        # 1. Unified Classification (V3)
        # Returns {category, confidence, predicted_path(deprecated), ...}
        # We primarily care about 'category' (ID) and 'suggested_filename' (from Vision)
        result = self.classifier.classify_file(file_path)
        
        category_id = result.get('category', 'unknown')
        confidence = result.get('confidence', 0.0)
        reasoning = result.get('reasoning', [])
        
        # 2. Path Resolution
        # Check Business Rules first (Specific Overrides)
        # E.g. if category is "receipts", but content is "Wolfhard", we might override.
        # For now, we rely on the Classifier outputting a correct Category ID.
        
        # Map Category ID -> Physical Path
        # First, check our hardcoded business map (Legacy compat)
        # Check if the classifier returned a specific logical key that matches our map
        target_str = self.drive_folder_map.get(category_id)
        
        if not target_str:
            # Fallback to Taxonomy Service (V3 Source of Truth)
            # This handles generic categories like "audio_sfx" -> "Projects/SFX"
            resolved_path = self.taxonomy_service.resolve_path(category_id)
            target_path = resolved_path
        else:
            target_path = Path(target_str)

        # 3. Smart Renaming (Anti-Drift)
        # Priority:
        # A. Vision Stub (from Classifier result)
        # B. Filename-derived Stub (Legacy Logic)
        
        final_filename = file_path.name # Default
        
        # Check for Vision/Classifier suggestion (Smart Renaming)
        suggested_name = result.get('suggested_filename')
        
        if suggested_name and suggested_name != file_path.name:
            # If Vision gave us a stub, we should formatting it
            # But unified_classifier usually returns a full filename if it can.
            # Let's trust it if confidence is high.
            final_filename = suggested_name
        else:
            # Fallback: Use Legacy Naming Logic (Standardized)
            final_filename = self._generate_standardized_filename(file_path, category_id, result)

        # 4. Determine Action
        action = "organize"
        
        # Guardrails
        if not is_stale:
            action = "ignore" 
            rationale = reasoning + [f"File is semi-active (last activity < {STALE_THRESHOLD_DAYS} days ago)"]
        elif confidence < 0.72: # Review Threshold
            action = "review"
            target_path = Path("05_STAGING_WORKFLOW/Uncertain_Classification")

        return PolicyDecision(
            source_path=file_path,
            category_id=category_id,
            target_path=target_path,
            suggested_filename=final_filename,
            confidence=confidence,
            rationale=rationale,
            action=action,
            metadata=result
        )

    def _generate_standardized_filename(self, file_path: Path, category: str, analysis: Dict) -> str:
        """
        Legacy Renaming Logic (Ported from recovered_gdrive_librarian)
        Generates consistent filenames based on content patterns.
        """
        original_name = file_path.stem.lower()
        extension = file_path.suffix
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Extract keywords/content from analysis
        # UnifiedClassifier puts keywords in 'keywords' or 'signals'
        keywords = analysis.get('keywords', [])
        if not keywords:
             # Try signals
             keywords = analysis.get('signals', {}).get('obvious', {}).get('keywords', [])
        
        content_text = " ".join(keywords).lower() if keywords else original_name

        # --- Wolfhard / Entertainment ---
        if "wolfhard" in content_text or "stranger things" in content_text:
            stub = "Document"
            if "contract" in content_text: stub = "Contract"
            elif "invoice" in content_text: stub = "Invoice"
            elif "schedule" in content_text: stub = "Schedule"
            return f"WOLFHARD, FINN - {stub} - {date_str}{extension}"

        # --- Papers That Dream (Creative) ---
        if "papers that dream" in content_text or "tptd" in content_text:
            return f"TPTD - Asset - {date_str}{extension}"

        # --- Financials ---
        if "receipt" in content_text or category.startswith("fin_"):
            # Try to find vendor? generic for now
            return f"Receipt - {date_str}{extension}"

        # --- Screenshots (Fallback if Vision didn't catch it) ---
        if "screenshot" in original_name:
            return f"Screenshot - {date_str}{extension}"

        # Default: Clean up original name
        clean_name = original_name.replace(" ", "_").replace("-", "_")
        # Truncate
        if len(clean_name) > 50:
            clean_name = clean_name[:50]
            
        return f"{category}_{clean_name}_{date_str}{extension}"