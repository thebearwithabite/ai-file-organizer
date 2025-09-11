#!/usr/bin/env python3
"""
Google Drive Integration - Core Library
Fixes the fundamental architecture discrepancy by properly integrating
with the mounted Google Drive as the 2TB root storage system.

This should be used as the PRIMARY storage root, not local Documents folder.

Created by: RT Max
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class DriveStatus:
    """Google Drive status information"""
    is_mounted: bool
    drive_path: Optional[Path]
    total_space_gb: Optional[float]
    free_space_gb: Optional[float]
    emergency_staging_path: Optional[Path]
    is_online: bool

class GoogleDriveIntegration:
    """
    Google Drive Integration for AI File Organizer v3.0
    
    This class provides the core functionality to use Google Drive as the 
    PRIMARY storage root instead of local Documents folder.
    
    Key Features:
    - Automatic Google Drive detection and mounting
    - 2TB cloud storage as primary root
    - Emergency staging area (99_STAGING_EMERGENCY/)
    - Seamless integration with existing classification system
    - Fallback to local storage if Google Drive unavailable
    """
    
    def __init__(self):
        self.user_email = "user@example.com"
        self.base_drive_paths = [
            Path(f"/Users/{os.getenv('USER', 'user')}/Library/CloudStorage/GoogleDrive-{self.user_email}/My Drive"),
            Path(f"/Users/{os.getenv('USER', 'user')}/Library/CloudStorage/GoogleDrive-{self.user_email.replace('@', '-').replace('.', '-')}/My Drive"),
        ]
        
        # Fallback paths
        self.fallback_path = Path.home() / "Documents" / "AI_ORGANIZER_GDRIVE_FALLBACK"
        
        # Initialize drive connection
        self.drive_root = self._detect_google_drive()
        self.emergency_staging = self._setup_emergency_staging()
        
    def _detect_google_drive(self) -> Optional[Path]:
        """
        Detect mounted Google Drive path
        
        Returns:
            Path to Google Drive root, or None if not available
        """
        for path in self.base_drive_paths:
            if path.exists() and path.is_dir():
                print(f"✅ Google Drive detected: {path}")
                return path
        
        print(f"⚠️  Google Drive not detected at expected paths:")
        for path in self.base_drive_paths:
            print(f"   ❌ {path}")
        print(f"📁 Will use fallback: {self.fallback_path}")
        
        return None
    
    def _setup_emergency_staging(self) -> Path:
        """Setup emergency staging directory"""
        if self.drive_root:
            staging_path = self.drive_root / "99_STAGING_EMERGENCY"
            staging_path.mkdir(exist_ok=True)
            return staging_path
        else:
            staging_path = self.fallback_path / "99_STAGING_EMERGENCY"
            staging_path.mkdir(parents=True, exist_ok=True)
            return staging_path
    
    def get_ai_organizer_root(self) -> Path:
        """
        Get the PRIMARY root directory for AI File Organizer
        
        This should be used instead of Path.home() / "Documents"
        throughout the entire system.
        
        Returns:
            Path: Google Drive root or fallback path
        """
        if self.drive_root and self.drive_root.exists():
            return self.drive_root
        else:
            # Create fallback structure
            self.fallback_path.mkdir(parents=True, exist_ok=True)
            return self.fallback_path
    
    def get_status(self) -> DriveStatus:
        """Get current Google Drive status"""
        
        is_mounted = self.drive_root is not None and self.drive_root.exists()
        
        # Check if online by trying to access a file
        is_online = False
        total_space = None
        free_space = None
        
        if is_mounted:
            try:
                # Test access
                list(self.drive_root.iterdir())
                is_online = True
                
                # Get space info (approximate)
                statvfs = os.statvfs(str(self.drive_root))
                total_space = (statvfs.f_frsize * statvfs.f_blocks) / (1024**3)  # GB
                free_space = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)   # GB
                
            except (OSError, PermissionError):
                is_online = False
        
        return DriveStatus(
            is_mounted=is_mounted,
            drive_path=self.drive_root,
            total_space_gb=total_space,
            free_space_gb=free_space,
            emergency_staging_path=self.emergency_staging,
            is_online=is_online
        )
    
    def create_ai_organizer_structure(self) -> Dict[str, Path]:
        """
        Create the complete AI File Organizer directory structure
        in Google Drive (or fallback location)
        
        Returns:
            Dictionary mapping structure names to paths
        """
        root = self.get_ai_organizer_root()
        
        structure = {
            # Phase 1: Active Projects
            "active_projects": root / "01_ACTIVE_PROJECTS",
            "entertainment_industry": root / "01_ACTIVE_PROJECTS" / "Entertainment_Industry",
            "business_operations": root / "01_ACTIVE_PROJECTS" / "Business_Operations",
            "creative_projects": root / "01_ACTIVE_PROJECTS" / "Creative_Projects",
            
            # Phase 2: Media Assets
            "media_assets": root / "02_MEDIA_ASSETS",
            "visual_assets": root / "02_MEDIA_ASSETS" / "Visual_Assets",
            "audio_library": root / "02_MEDIA_ASSETS" / "Audio_Library",
            "video_content": root / "02_MEDIA_ASSETS" / "Video_Content",
            
            # Phase 3: Reference Library  
            "reference_library": root / "03_REFERENCE_LIBRARY",
            "research_papers": root / "03_REFERENCE_LIBRARY" / "Research_Papers",
            "industry_docs": root / "03_REFERENCE_LIBRARY" / "Industry_Documents",
            "templates": root / "03_REFERENCE_LIBRARY" / "Templates",
            
            # Phase 4: Metadata System
            "metadata_system": root / "04_METADATA_SYSTEM",
            "vector_db": root / "04_METADATA_SYSTEM" / "vector_db",
            "classification_logs": root / "04_METADATA_SYSTEM" / "classification_logs",
            "user_preferences": root / "04_METADATA_SYSTEM" / "user_preferences.json",
            
            # Phase 5: Processing Areas
            "temp_processing": root / "99_TEMP_PROCESSING",
            "manual_review": root / "99_TEMP_PROCESSING" / "Manual_Review",
            "staging_emergency": root / "99_STAGING_EMERGENCY",
        }
        
        # Create all directories
        for name, path in structure.items():
            if name != "user_preferences":  # Don't create the JSON file, just directory
                path.mkdir(parents=True, exist_ok=True)
                print(f"✅ Created: {name} -> {path}")
        
        # Create preferences file if it doesn't exist
        prefs_file = structure["user_preferences"]
        if not prefs_file.exists():
            prefs_file.parent.mkdir(parents=True, exist_ok=True)
            initial_prefs = {
                "created": str(datetime.now()),
                "version": "3.0",
                "google_drive_root": str(root),
                "category_preferences": {},
                "person_preferences": {},
                "project_preferences": {},
                "keyword_boosts": {},
                "decision_history": []
            }
            with open(prefs_file, 'w') as f:
                json.dump(initial_prefs, f, indent=2)
            print(f"✅ Created preferences: {prefs_file}")
        
        return structure
    
    def emergency_space_recovery(self, min_free_gb: float = 5.0) -> Dict[str, Any]:
        """
        Emergency space recovery when local storage is critically low
        
        Args:
            min_free_gb: Minimum free space threshold in GB
            
        Returns:
            Recovery statistics
        """
        
        # Check local storage
        home_path = Path.home()
        try:
            statvfs = os.statvfs(str(home_path))
            free_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
        except:
            free_gb = 0
        
        if free_gb >= min_free_gb:
            return {
                "recovery_needed": False,
                "current_free_gb": free_gb,
                "message": f"Local storage OK: {free_gb:.1f}GB free"
            }
        
        print(f"🚨 EMERGENCY SPACE RECOVERY TRIGGERED")
        print(f"   📊 Current free space: {free_gb:.1f}GB")
        print(f"   🎯 Target minimum: {min_free_gb}GB")
        
        recovery_stats = {
            "recovery_needed": True,
            "current_free_gb": free_gb,
            "files_moved": 0,
            "space_freed_gb": 0.0,
            "errors": []
        }
        
        # Move large files from common locations to Google Drive
        emergency_sources = [
            Path.home() / "Downloads",
            Path.home() / "Desktop", 
            Path.home() / "Documents"
        ]
        
        for source_dir in emergency_sources:
            if not source_dir.exists():
                continue
                
            print(f"🔍 Scanning: {source_dir}")
            
            try:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        # Check file size (move files > 50MB)
                        try:
                            file_size = file_path.stat().st_size
                            if file_size > 50 * 1024 * 1024:  # 50MB
                                target_path = self.emergency_staging / file_path.name
                                
                                # Handle name conflicts
                                counter = 1
                                original_target = target_path
                                while target_path.exists():
                                    stem = original_target.stem
                                    suffix = original_target.suffix
                                    target_path = self.emergency_staging / f"{stem}_{counter}{suffix}"
                                    counter += 1
                                
                                # Move file
                                shutil.move(str(file_path), str(target_path))
                                
                                space_freed = file_size / (1024**3)  # GB
                                recovery_stats["files_moved"] += 1
                                recovery_stats["space_freed_gb"] += space_freed
                                
                                print(f"   📦 Moved: {file_path.name} ({space_freed:.2f}GB)")
                                
                                # Check if we've freed enough space
                                if recovery_stats["space_freed_gb"] >= (min_free_gb - free_gb) * 1.2:
                                    break
                                    
                        except Exception as e:
                            recovery_stats["errors"].append(f"Error moving {file_path}: {e}")
                            
            except Exception as e:
                recovery_stats["errors"].append(f"Error scanning {source_dir}: {e}")
        
        return recovery_stats
    
    def get_path_for_category(self, category: str, subcategory: str = "") -> str:
        """
        Get the correct Google Drive path for a category/subcategory
        
        Args:
            category: Main category (e.g., "creative", "business", "visual")
            subcategory: Sub-category (e.g., "contracts", "podcasts")
            
        Returns:
            Relative path string for the category
        """
        
        # Map categories to Google Drive structure
        category_mapping = {
            "creative": "01_ACTIVE_PROJECTS/Creative_Projects",
            "entertainment": "01_ACTIVE_PROJECTS/Entertainment_Industry",
            "business": "01_ACTIVE_PROJECTS/Business_Operations",
            "visual": "02_MEDIA_ASSETS/Visual_Assets",
            "audio": "02_MEDIA_ASSETS/Audio_Library",
            "video": "02_MEDIA_ASSETS/Video_Content",
            "research": "03_REFERENCE_LIBRARY/Research_Papers",
            "templates": "03_REFERENCE_LIBRARY/Templates",
            "unknown": "99_TEMP_PROCESSING/Manual_Review"
        }
        
        base_path = category_mapping.get(category, "99_TEMP_PROCESSING/Manual_Review")
        
        if subcategory:
            return f"{base_path}/{subcategory.title().replace('_', ' ')}"
        
        return base_path

def get_ai_organizer_root() -> Path:
    """
    GLOBAL FUNCTION: Get AI File Organizer root directory
    
    This function should REPLACE all instances of:
    - Path.home() / "Documents"
    - "/Users/user/Documents"
    
    Returns:
        Path: Google Drive root or fallback location
    """
    gdrive = GoogleDriveIntegration()
    return gdrive.get_ai_organizer_root()

def main():
    """Test the Google Drive integration"""
    print("🔧 Google Drive Integration Test")
    
    gdrive = GoogleDriveIntegration()
    
    # Check status
    status = gdrive.get_status()
    print(f"\n📊 GOOGLE DRIVE STATUS:")
    print(f"   🔗 Mounted: {status.is_mounted}")
    print(f"   🌐 Online: {status.is_online}")
    if status.drive_path:
        print(f"   📁 Path: {status.drive_path}")
    if status.total_space_gb:
        print(f"   💾 Total Space: {status.total_space_gb:.1f}GB")
        print(f"   💿 Free Space: {status.free_space_gb:.1f}GB")
    print(f"   🚨 Emergency Staging: {status.emergency_staging_path}")
    
    # Get root
    root = gdrive.get_ai_organizer_root()
    print(f"\n🎯 AI ORGANIZER ROOT: {root}")
    
    # Create structure
    print(f"\n🏗️  CREATING DIRECTORY STRUCTURE...")
    structure = gdrive.create_ai_organizer_structure()
    
    print(f"\n✅ Google Drive Integration Ready!")
    print(f"🎯 Root: {root}")
    print(f"📁 Emergency Staging: {gdrive.emergency_staging}")

if __name__ == "__main__":
    main()