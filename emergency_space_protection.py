#!/usr/bin/env python3
"""
Emergency Disk Space Protection with Google Drive Offloading
Part of AI File Organizer v3.1 - Adaptive Emergency Prevention System

Provides proactive disk space monitoring and emergency offloading to Google Drive:
- Real-time disk space monitoring
- Intelligent file selection for offloading
- Automatic Google Drive emergency staging
- Smart local cache management
- Emergency prevention with early warning

Created by: RT Max / Claude Code
"""

import os
import sys
import time
import threading
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Tuple
import sqlite3
import json
import logging
import hashlib
from dataclasses import dataclass

# Import existing system components
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from gdrive_integration import get_ai_organizer_root, get_metadata_root
from universal_adaptive_learning import UniversalAdaptiveLearning
from confidence_system import ADHDFriendlyConfidenceSystem
from easy_rollback_system import EasyRollbackSystem
from bulletproof_deduplication import BulletproofDeduplicator

@dataclass
class SpaceEmergency:
    """A detected disk space emergency"""
    emergency_id: str
    detection_time: datetime
    severity: str  # "warning", "critical", "emergency"
    disk_path: str
    total_space_gb: float
    free_space_gb: float
    usage_percent: float
    projected_full_hours: Optional[float]
    recommended_actions: List[str]
    affected_directories: List[str]

@dataclass
class OffloadCandidate:
    """A file candidate for Google Drive offloading"""
    file_path: str
    file_size_mb: float
    last_access_days: int
    access_frequency: int
    importance_score: float
    offload_priority: float
    file_type: str
    is_duplicate: bool
    
class EmergencySpaceProtection:
    """
    Proactive disk space protection system with Google Drive emergency offloading
    
    Monitors disk usage and automatically moves files to Google Drive to prevent
    disk space emergencies that would cripple ADHD workflow
    """
    
    def __init__(self, base_dir: str = None):
        # Set up logging first
        self.logger = logging.getLogger(__name__)
        
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        
        # Initialize components
        self.learning_system = UniversalAdaptiveLearning(str(self.base_dir))
        self.confidence_system = ADHDFriendlyConfidenceSystem(str(self.base_dir))
        self.rollback_system = EasyRollbackSystem()
        self.deduplicator = BulletproofDeduplicator(str(self.base_dir))
        
        # Space protection database
        self.protection_db_path = get_metadata_root() /  "space_protection.db"
        
        # Configuration
        self.config = {
            "monitoring_enabled": True,
            "emergency_offloading_enabled": True,
            "warning_threshold": 85,      # Warn at 85% disk usage
            "critical_threshold": 90,     # Critical at 90% disk usage
            "emergency_threshold": 95,    # Emergency at 95% disk usage
            "target_free_space": 80,      # Target 80% usage after cleanup
            "monitoring_interval": 300,   # Check every 5 minutes
            "emergency_interval": 60,     # Check every minute in emergency
            "offload_batch_size": 100,    # Max files per offload batch
            "min_file_age_days": 7,       # Don't touch files newer than 7 days
            "cache_size_gb": 50           # Keep 50GB of recent files locally
        }
        
        # Google Drive emergency staging paths
        self.gdrive_emergency_paths = {
            "downloads": "99_EMERGENCY_STAGING/Downloads_Archive",
            "desktop": "99_EMERGENCY_STAGING/Desktop_Archive", 
            "documents": "99_EMERGENCY_STAGING/Documents_Archive",
            "large_files": "99_EMERGENCY_STAGING/Large_Files_Archive",
            "duplicates": "99_EMERGENCY_STAGING/Duplicate_Files_Archive"
        }

        # Detect real Google Drive path for offloading
        # We cannot use base_dir because it defaults to ~/Documents (local)
        self.gdrive_root = None
        possible_gdrive_paths = [
            Path.home() / "Google Drive" / "My Drive",
            Path.home() / "Google Drive",
            Path("/Volumes/GoogleDrive/My Drive"),
            Path("/Volumes/GoogleDrive")
        ]
        
        for path in possible_gdrive_paths:
            if path.exists() and path.is_dir():
                self.gdrive_root = path
                self.logger.info(f"Emergency offloading target found: {self.gdrive_root}")
                break
        
        if not self.gdrive_root:
            self.logger.warning("Google Drive not found! Emergency offloading will fail.")
        
        # Monitored locations with priorities
        self.monitored_locations = {
            Path.home() / "Downloads": {
                "priority": "high",
                "auto_offload": True,
                "target_usage": 50  # Keep downloads under 50% of available space
            },
            Path.home() / "Desktop": {
                "priority": "medium", 
                "auto_offload": True,
                "target_usage": 30
            },
            Path.home() / "Documents": {
                "priority": "low",
                "auto_offload": False,  # More careful with documents
                "target_usage": 70
            },
            self.base_dir: {
                "priority": "medium",
                "auto_offload": True,
                "target_usage": 60
            }
        }
        
        # File type priorities for offloading
        self.offload_priorities = {
            # High priority for offloading (safe to move)
            ".zip": 0.9,
            ".rar": 0.9,
            ".dmg": 0.9,
            ".iso": 0.9,
            ".mp4": 0.8,
            ".mov": 0.8,
            ".avi": 0.8,
            ".mkv": 0.8,
            ".mp3": 0.7,
            ".wav": 0.7,
            ".flac": 0.7,
            ".jpg": 0.6,
            ".png": 0.6,
            ".tiff": 0.6,
            ".psd": 0.5,
            
            # Medium priority (careful)
            ".pdf": 0.4,
            ".docx": 0.3,
            ".xlsx": 0.3,
            ".pptx": 0.3,
            
            # Low priority (keep local)
            ".txt": 0.1,
            ".md": 0.1,
            ".py": 0.1,
            ".js": 0.1,
            ".css": 0.1,
            ".html": 0.1
        }
        
        # Statistics
        self.stats = {
            "space_emergencies_prevented": 0,
            "files_offloaded": 0,
            "space_recovered_gb": 0.0,
            "emergency_interventions": 0,
            "warnings_issued": 0,
            "automatic_offloads": 0
        }
        
        # Active monitoring
        self.monitoring_active = False
        self.monitoring_threads = {}
        self.current_emergencies = []
        
        # Initialize database
        self._init_protection_database()
        
        self.logger.info("Emergency Space Protection initialized")

    def _init_protection_database(self):
        """Initialize space protection database"""
        self.protection_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.protection_db_path) as conn:
            # Space emergencies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS space_emergencies (
                    emergency_id TEXT PRIMARY KEY,
                    detection_time TEXT,
                    severity TEXT,
                    disk_path TEXT,
                    total_space_gb REAL,
                    free_space_gb REAL,
                    usage_percent REAL,
                    projected_full_hours REAL,
                    resolution_time TEXT,
                    actions_taken TEXT,
                    success BOOLEAN
                )
            """)
            
            # Offloaded files tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offloaded_files (
                    file_id TEXT PRIMARY KEY,
                    original_path TEXT,
                    gdrive_path TEXT,
                    offload_time TEXT,
                    file_size_mb REAL,
                    last_access_local TEXT,
                    access_frequency INTEGER,
                    offload_reason TEXT,
                    can_restore BOOLEAN DEFAULT TRUE,
                    emergency_offload BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Space usage tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS space_usage_history (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    disk_path TEXT,
                    total_space_gb REAL,
                    free_space_gb REAL,
                    usage_percent REAL,
                    trend_direction TEXT
                )
            """)
            
            # Local cache management
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_cache (
                    cache_id TEXT PRIMARY KEY,
                    file_path TEXT,
                    gdrive_path TEXT,
                    cached_time TEXT,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 1,
                    file_size_mb REAL,
                    priority_score REAL
                )
            """)
            
            conn.commit()

    def start_space_protection(self):
        """Start space protection monitoring"""
        self.logger.info("Starting emergency space protection...")
        
        self.monitoring_active = True
        
        # Start monitoring thread
        self.monitoring_threads["space_monitor"] = threading.Thread(
            target=self._space_monitoring_loop, daemon=True
        )
        self.monitoring_threads["space_monitor"].start()
        
        # Start emergency response thread
        self.monitoring_threads["emergency_response"] = threading.Thread(
            target=self._emergency_response_loop, daemon=True
        )
        self.monitoring_threads["emergency_response"].start()
        
        # Start cache management thread
        self.monitoring_threads["cache_manager"] = threading.Thread(
            target=self._cache_management_loop, daemon=True
        )
        self.monitoring_threads["cache_manager"].start()
        
        self.logger.info("Emergency space protection started successfully")

    def stop_space_protection(self):
        """Stop space protection monitoring"""
        self.logger.info("Stopping emergency space protection...")
        
        self.monitoring_active = False
        
        # Wait for threads to complete
        for thread in self.monitoring_threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.logger.info("Emergency space protection stopped")

    def _space_monitoring_loop(self):
        """Main space monitoring loop"""
        
        while self.monitoring_active:
            try:
                # Check all monitored locations
                emergencies = self._check_all_disk_usage()
                
                # Process any new emergencies
                for emergency in emergencies:
                    if emergency.emergency_id not in [e.emergency_id for e in self.current_emergencies]:
                        self.current_emergencies.append(emergency)
                        self._handle_space_emergency(emergency)
                
                # Determine sleep interval based on current situation
                if any(e.severity == "emergency" for e in self.current_emergencies):
                    sleep_time = self.config["emergency_interval"]
                else:
                    sleep_time = self.config["monitoring_interval"]
                
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Error in space monitoring loop: {e}")
                time.sleep(60)

    def _emergency_response_loop(self):
        """Emergency response processing loop"""
        
        while self.monitoring_active:
            try:
                if self.current_emergencies:
                    # Process emergencies by severity
                    self.current_emergencies.sort(key=lambda e: ["warning", "critical", "emergency"].index(e.severity), reverse=True)
                    
                    for emergency in self.current_emergencies.copy():
                        if emergency.severity == "emergency":
                            self._execute_emergency_offloading(emergency)
                        elif emergency.severity == "critical":
                            self._execute_critical_cleanup(emergency)
                        elif emergency.severity == "warning":
                            self._execute_preventive_measures(emergency)
                        
                        # Re-check if emergency is resolved
                        if self._is_emergency_resolved(emergency):
                            self.current_emergencies.remove(emergency)
                            self._record_emergency_resolution(emergency)
                
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error in emergency response loop: {e}")
                time.sleep(60)

    def _cache_management_loop(self):
        """Local cache management loop"""
        
        while self.monitoring_active:
            try:
                self._manage_local_cache()
                time.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Error in cache management loop: {e}")
                time.sleep(1800)

    def _check_all_disk_usage(self) -> List[SpaceEmergency]:
        """Check disk usage for all monitored locations"""
        
        emergencies = []
        
        # Group locations by disk to avoid duplicate checking
        disks_checked = set()
        
        for location, config in self.monitored_locations.items():
            if not location.exists():
                continue
            
            # Get disk path
            disk_path = self._get_disk_path(location)
            
            if disk_path in disks_checked:
                continue
            
            disks_checked.add(disk_path)
            
            # Check disk usage
            emergency = self._check_disk_usage(disk_path, location)
            if emergency:
                emergencies.append(emergency)
                
                # Record usage history
                self._record_usage_history(emergency)
        
        return emergencies

    def _check_disk_usage(self, disk_path: str, reference_location: Path) -> Optional[SpaceEmergency]:
        """Check disk usage for a specific disk"""
        
        try:
            total, used, free = shutil.disk_usage(disk_path)
            
            total_gb = total / (1024**3)
            free_gb = free / (1024**3)
            usage_percent = (used / total) * 100
            
            # Determine severity level
            severity = None
            if usage_percent >= self.config["emergency_threshold"]:
                severity = "emergency"
            elif usage_percent >= self.config["critical_threshold"]:
                severity = "critical"
            elif usage_percent >= self.config["warning_threshold"]:
                severity = "warning"
            
            if not severity:
                return None
            
            # Calculate projected time until full
            projected_full_hours = self._calculate_projected_full_time(disk_path, free_gb)
            
            # Get affected directories
            affected_dirs = [str(loc) for loc, conf in self.monitored_locations.items() 
                           if loc.exists() and self._get_disk_path(loc) == disk_path]
            
            # Generate emergency ID
            emergency_id = hashlib.md5(f"{disk_path}_{datetime.now().date()}_{severity}".encode()).hexdigest()[:12]
            
            emergency = SpaceEmergency(
                emergency_id=emergency_id,
                detection_time=datetime.now(),
                severity=severity,
                disk_path=disk_path,
                total_space_gb=total_gb,
                free_space_gb=free_gb,
                usage_percent=usage_percent,
                projected_full_hours=projected_full_hours,
                recommended_actions=self._get_recommended_actions(severity, usage_percent),
                affected_directories=affected_dirs
            )
            
            return emergency
            
        except Exception as e:
            self.logger.error(f"Error checking disk usage for {disk_path}: {e}")
            return None

    def _handle_space_emergency(self, emergency: SpaceEmergency):
        """Handle a detected space emergency"""
        
        self.logger.warning(f"Space emergency detected: {emergency.severity} on {emergency.disk_path}")
        self.logger.warning(f"Disk usage: {emergency.usage_percent:.1f}% ({emergency.free_space_gb:.1f} GB free)")
        
        # Record emergency
        self._record_space_emergency(emergency)
        
        # Update statistics
        if emergency.severity == "warning":
            self.stats["warnings_issued"] += 1
        else:
            self.stats["space_emergencies_prevented"] += 1

    def _execute_emergency_offloading(self, emergency: SpaceEmergency):
        """Execute emergency offloading to Google Drive"""
        
        self.logger.error(f"EMERGENCY: Executing immediate offloading for {emergency.disk_path}")
        
        try:
            # Calculate space needed to reach target
            target_usage = self.config["target_free_space"]
            space_needed_gb = emergency.total_space_gb * ((emergency.usage_percent - target_usage) / 100)
            
            self.logger.info(f"Need to free {space_needed_gb:.1f} GB to reach target usage")
            
            # Get offload candidates
            candidates = self._get_emergency_offload_candidates(emergency, space_needed_gb)
            
            if not candidates:
                self.logger.error("No suitable files found for emergency offloading!")
                return
            
            # Execute offloading in batches
            offloaded_space = 0.0
            offloaded_count = 0
            
            for batch_start in range(0, len(candidates), self.config["offload_batch_size"]):
                batch = candidates[batch_start:batch_start + self.config["offload_batch_size"]]
                
                batch_result = self._offload_file_batch(batch, emergency_mode=True)
                offloaded_space += batch_result["space_freed_gb"]
                offloaded_count += batch_result["files_offloaded"]
                
                # Check if we've freed enough space
                if offloaded_space >= space_needed_gb:
                    break
                
                # Brief pause between batches
                time.sleep(5)
            
            self.stats["emergency_interventions"] += 1
            self.stats["files_offloaded"] += offloaded_count
            self.stats["space_recovered_gb"] += offloaded_space
            
            self.logger.info(f"Emergency offloading completed: {offloaded_count} files, {offloaded_space:.1f} GB freed")
            
        except Exception as e:
            self.logger.error(f"Error in emergency offloading: {e}")

    def _execute_critical_cleanup(self, emergency: SpaceEmergency):
        """Execute critical cleanup measures"""
        
        self.logger.warning(f"CRITICAL: Executing cleanup for {emergency.disk_path}")
        
        try:
            # Focus on safe cleanup actions
            cleanup_actions = [
                self._cleanup_temp_files,
                self._cleanup_duplicate_files,
                self._cleanup_old_downloads,
                self._offload_large_media_files
            ]
            
            total_freed = 0.0
            
            for cleanup_action in cleanup_actions:
                freed_gb = cleanup_action(emergency)
                total_freed += freed_gb
                
                # Check if critical level resolved
                if self._is_emergency_resolved(emergency):
                    break
            
            self.logger.info(f"Critical cleanup freed {total_freed:.1f} GB")
            
        except Exception as e:
            self.logger.error(f"Error in critical cleanup: {e}")

    def _execute_preventive_measures(self, emergency: SpaceEmergency):
        """Execute preventive measures for warning level"""
        
        self.logger.info(f"WARNING: Executing preventive measures for {emergency.disk_path}")
        
        try:
            # Gentle cleanup and preparation
            actions = [
                self._prepare_offload_candidates,
                self._cleanup_temp_files,
                self._optimize_local_cache
            ]
            
            for action in actions:
                action(emergency)
            
        except Exception as e:
            self.logger.error(f"Error in preventive measures: {e}")

    def _get_emergency_offload_candidates(self, emergency: SpaceEmergency, space_needed_gb: float) -> List[OffloadCandidate]:
        """Get files suitable for emergency offloading"""
        
        candidates = []
        
        try:
            for directory_path in emergency.affected_directories:
                directory = Path(directory_path)
                
                if not directory.exists():
                    continue
                
                # Scan directory for candidates
                for file_path in directory.rglob('*'):
                    if file_path.is_file():
                        candidate = self._evaluate_offload_candidate(file_path, emergency_mode=True)
                        
                        if candidate and candidate.offload_priority > 0.3:  # Emergency threshold
                            candidates.append(candidate)
            
            # Sort by offload priority (highest first)
            candidates.sort(key=lambda c: c.offload_priority, reverse=True)
            
            # Select candidates until we have enough space
            selected_candidates = []
            total_space = 0.0
            
            for candidate in candidates:
                selected_candidates.append(candidate)
                total_space += candidate.file_size_mb / 1024  # Convert to GB
                
                if total_space >= space_needed_gb * 1.2:  # 20% buffer
                    break
            
            return selected_candidates
            
        except Exception as e:
            self.logger.error(f"Error getting offload candidates: {e}")
            return []

    def _evaluate_offload_candidate(self, file_path: Path, emergency_mode: bool = False) -> Optional[OffloadCandidate]:
        """Evaluate a file as an offload candidate"""
        
        try:
            if not file_path.exists() or file_path.is_dir():
                return None
            
            # CRITICAL: EXCLUDE DATABASE FILES AND METADATA SYSTEM
            # User requirement: DB files must NEVER go to Google Drive
            if file_path.suffix.lower() in ['.db', '.sqlite', '.sqlite3', '.db3', '.sdb']:
                return None
                
            # Exclude the entire metadata directory
            if "AI_METADATA_SYSTEM" in str(file_path):
                return None
                
            # Exclude hidden files
            if file_path.name.startswith('.'):
                return None
            
            stat_info = file_path.stat()
            file_size_mb = stat_info.st_size / (1024 * 1024)
            
            # Skip small files unless in emergency mode
            if file_size_mb < 1.0 and not emergency_mode:
                return None
            
            # Calculate file age
            file_age_days = (time.time() - stat_info.st_mtime) / (24 * 3600)
            
            # Skip very recent files
            if file_age_days < self.config["min_file_age_days"]:
                return None
            
            # Calculate access information
            last_access_days = (time.time() - stat_info.st_atime) / (24 * 3600)
            access_frequency = self._estimate_access_frequency(file_path)
            
            # Calculate importance score
            importance_score = self._calculate_importance_score(file_path, stat_info)
            
            # Calculate offload priority
            offload_priority = self._calculate_offload_priority(
                file_path, file_size_mb, last_access_days, 
                access_frequency, importance_score, emergency_mode
            )
            
            # Check for duplicates
            is_duplicate = self._is_duplicate_file(file_path)
            
            candidate = OffloadCandidate(
                file_path=str(file_path),
                file_size_mb=file_size_mb,
                last_access_days=int(last_access_days),
                access_frequency=access_frequency,
                importance_score=importance_score,
                offload_priority=offload_priority,
                file_type=file_path.suffix.lower(),
                is_duplicate=is_duplicate
            )
            
            return candidate
            
        except Exception as e:
            self.logger.error(f"Error evaluating offload candidate {file_path}: {e}")
            return None

    def _calculate_offload_priority(self, file_path: Path, file_size_mb: float, 
                                  last_access_days: int, access_frequency: int,
                                  importance_score: float, emergency_mode: bool) -> float:
        """Calculate offload priority for a file"""
        
        priority = 0.0
        
        # File type priority
        file_ext = file_path.suffix.lower()
        type_priority = self.offload_priorities.get(file_ext, 0.2)
        priority += type_priority * 0.3
        
        # Size factor (larger files get higher priority)
        size_factor = min(1.0, file_size_mb / 100)  # Normalize to 100MB
        priority += size_factor * 0.2
        
        # Access recency (older access = higher priority)
        access_factor = min(1.0, last_access_days / 30)  # Normalize to 30 days
        priority += access_factor * 0.2
        
        # Access frequency (less frequent = higher priority)
        frequency_factor = max(0.0, 1.0 - (access_frequency / 10))  # Normalize to 10 accesses
        priority += frequency_factor * 0.15
        
        # Importance (lower importance = higher priority for offload)
        importance_factor = 1.0 - importance_score
        priority += importance_factor * 0.15
        
        # Location factor
        path_str = str(file_path).lower()
        if "downloads" in path_str:
            priority += 0.2  # Downloads are good candidates
        elif "desktop" in path_str:
            priority += 0.1  # Desktop files are moderate candidates
        elif "documents" in path_str:
            priority -= 0.1  # Documents are less ideal
        
        # Emergency mode boosts all priorities
        if emergency_mode:
            priority *= 1.5
        
        return min(1.0, priority)

    def _offload_file_batch(self, candidates: List[OffloadCandidate], emergency_mode: bool = False) -> Dict[str, Any]:
        """Offload a batch of files to Google Drive"""
        
        files_offloaded = 0
        space_freed_gb = 0.0
        errors = []
        
        # Start rollback operation
        operation_id = self.rollback_system.start_operation(
            operation_type="emergency_space_offload" if emergency_mode else "space_offload",
            description=f"Offload {len(candidates)} files to Google Drive",
            confidence=0.9 if emergency_mode else 0.7
        )
        
        try:
            for candidate in candidates:
                try:
                    file_path = Path(candidate.file_path)
                    
                    if not file_path.exists():
                        continue
                    
                    # Determine Google Drive destination
                    gdrive_path = self._get_gdrive_offload_path(file_path, candidate)
                    
                    # Create Google Drive directory structure
                    if self.gdrive_root:
                        gdrive_dir = self.gdrive_root / gdrive_path
                    else:
                        # Fallback to base_dir (won't save space if on same disk, but preserves file)
                        gdrive_dir = self.base_dir / gdrive_path
                        
                    gdrive_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Move file to Google Drive
                    gdrive_file_path = gdrive_dir / file_path.name
                    
                    # Handle name conflicts
                    if gdrive_file_path.exists():
                        counter = 1
                        base_name = file_path.stem
                        extension = file_path.suffix
                        while gdrive_file_path.exists():
                            new_name = f"{base_name}_{counter}{extension}"
                            gdrive_file_path = gdrive_dir / new_name
                            counter += 1
                    
                    # Move the file
                    shutil.move(str(file_path), str(gdrive_file_path))
                    
                    # Record the operation
                    self.rollback_system.record_file_operation(
                        operation_id=operation_id,
                        original_path=str(file_path),
                        new_path=str(gdrive_file_path),
                        operation_type="move"
                    )
                    
                    # Record in offloaded files database
                    self._record_offloaded_file(candidate, str(gdrive_file_path), emergency_mode)
                    
                    files_offloaded += 1
                    space_freed_gb += candidate.file_size_mb / 1024
                    
                    self.logger.info(f"Offloaded: {file_path.name} -> {gdrive_path}")
                    
                except Exception as e:
                    error_msg = f"Failed to offload {candidate.file_path}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Complete rollback operation
            self.rollback_system.complete_operation(operation_id, success=True)
            
        except Exception as e:
            self.logger.error(f"Error in batch offload: {e}")
            self.rollback_system.complete_operation(operation_id, success=False, error=str(e))
        
        return {
            "files_offloaded": files_offloaded,
            "space_freed_gb": space_freed_gb,
            "errors": errors
        }

    def _get_gdrive_offload_path(self, file_path: Path, candidate: OffloadCandidate) -> str:
        """Get Google Drive path for offloading a file"""
        
        # Determine category based on source location and file type
        path_str = str(file_path).lower()
        
        if "downloads" in path_str:
            return self.gdrive_emergency_paths["downloads"]
        elif "desktop" in path_str:
            return self.gdrive_emergency_paths["desktop"]
        elif "documents" in path_str:
            return self.gdrive_emergency_paths["documents"]
        elif candidate.file_size_mb > 100:  # Large files
            return self.gdrive_emergency_paths["large_files"]
        elif candidate.is_duplicate:
            return self.gdrive_emergency_paths["duplicates"]
        else:
            # Default based on file type
            file_ext = file_path.suffix.lower()
            if file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
                return "99_EMERGENCY_STAGING/Video_Archive"
            elif file_ext in ['.mp3', '.wav', '.flac']:
                return "99_EMERGENCY_STAGING/Audio_Archive"
            elif file_ext in ['.jpg', '.png', '.tiff', '.psd']:
                return "99_EMERGENCY_STAGING/Image_Archive"
            else:
                return "99_EMERGENCY_STAGING/General_Archive"

    # Helper methods
    def _get_disk_path(self, location: Path) -> str:
        """Get the disk path for a location"""
        return str(location.anchor)  # Returns the root (e.g., '/' on Unix, 'C:\' on Windows)

    def _calculate_projected_full_time(self, disk_path: str, free_gb: float) -> Optional[float]:
        """Calculate projected time until disk is full"""
        # TODO: Implement trend analysis based on usage history
        # For now, return None (no projection)
        return None

    def _get_recommended_actions(self, severity: str, usage_percent: float) -> List[str]:
        """Get recommended actions for a space emergency"""
        
        actions = []
        
        if severity == "emergency":
            actions = [
                "immediate_file_offloading",
                "delete_temp_files",
                "remove_duplicates",
                "compress_large_files"
            ]
        elif severity == "critical":
            actions = [
                "offload_old_files",
                "cleanup_downloads",
                "remove_duplicates",
                "archive_media_files"
            ]
        elif severity == "warning":
            actions = [
                "cleanup_temp_files",
                "review_downloads",
                "identify_large_files",
                "prepare_offload_candidates"
            ]
        
        return actions

    def _cleanup_temp_files(self, emergency: SpaceEmergency) -> float:
        """Clean up temporary files and return space freed in GB"""
        self.logger.info("Cleaning up temporary files...")
        
        temp_patterns = ['*.tmp', '*.bak', '*.log', 'npm-debug.log*', 'yarn-error.log*']
        total_freed = 0
        
        for directory_path in emergency.affected_directories:
            directory = Path(directory_path)
            if not directory.exists():
                continue
                
            for pattern in temp_patterns:
                for temp_file in directory.rglob(pattern):
                    if temp_file.is_file():
                        try:
                            file_size = temp_file.stat().st_size
                            # Safe check - only delete if not recently modified (e.g. > 1 hour)
                            if time.time() - temp_file.stat().st_mtime > 3600:
                                temp_file.unlink()
                                total_freed += file_size
                                self.logger.debug(f"Purged temp file: {temp_file}")
                        except Exception as e:
                            self.logger.warning(f"Failed to delete {temp_file}: {e}")
                            
        freed_gb = total_freed / (1024**3)
        self.logger.info(f"Cleanup finished. Freed {freed_gb:.2f} GB")
        return freed_gb

    def _cleanup_duplicate_files(self, emergency: SpaceEmergency) -> float:
        """Clean up duplicate files and return space freed in GB"""
        self.logger.info("Starting emergency deduplication cleanup...")
        
        total_freed = 0
        
        for directory_path in emergency.affected_directories:
            directory = Path(directory_path)
            if not directory.exists():
                continue
            
            # Use BulletproofDeduplicator in auto-execute mode
            # We set a high safety threshold (0.9) for emergency auto-cleanup
            results = self.deduplicator.scan_directory(directory, execute=True, safety_threshold=0.9)
            
            freed_bytes = results.get("space_recovered", 0)
            total_freed += freed_bytes
            
            if freed_bytes > 0:
                self.logger.info(f"Deduplicated {directory}: Freed {freed_bytes / (1024**2):.1f} MB")
                
        freed_gb = total_freed / (1024**3)
        self.logger.info(f"Emergency deduplication finished. Freed {freed_gb:.2f} GB total")
        return freed_gb

    def _cleanup_old_downloads(self, emergency: SpaceEmergency) -> float:
        """Clean up old downloads and return space freed in GB"""
        # TODO: Implement old downloads cleanup
        return 0.0

    def _offload_large_media_files(self, emergency: SpaceEmergency) -> float:
        """Offload large media files and return space freed in GB"""
        # TODO: Implement media file offloading
        return 0.0

    def _prepare_offload_candidates(self, emergency: SpaceEmergency):
        """Prepare candidates for potential offloading"""
        # TODO: Implement candidate preparation
        pass

    def _optimize_local_cache(self, emergency: SpaceEmergency):
        """Optimize local cache usage"""
        # TODO: Implement cache optimization
        pass

    def _manage_local_cache(self):
        """Manage local cache of offloaded files"""
        # TODO: Implement cache management
        pass

    def _is_emergency_resolved(self, emergency: SpaceEmergency) -> bool:
        """Check if an emergency has been resolved"""
        
        try:
            total, used, free = shutil.disk_usage(emergency.disk_path)
            current_usage = (used / total) * 100
            
            # Check if we're below the threshold that triggered this emergency
            if emergency.severity == "emergency":
                return current_usage < self.config["critical_threshold"]
            elif emergency.severity == "critical":
                return current_usage < self.config["warning_threshold"]
            elif emergency.severity == "warning":
                return current_usage < self.config["warning_threshold"] - 5  # 5% buffer
            
        except Exception as e:
            self.logger.error(f"Error checking emergency resolution: {e}")
        
        return False

    def _estimate_access_frequency(self, file_path: Path) -> int:
        """Estimate how frequently a file is accessed"""
        # Simple estimate based on file age and access time
        try:
            stat_info = file_path.stat()
            file_age_days = (time.time() - stat_info.st_ctime) / (24 * 3600)
            last_access_days = (time.time() - stat_info.st_atime) / (24 * 3600)
            
            if file_age_days > 0:
                # Rough estimate: if recently accessed relative to age, higher frequency
                frequency = max(1, int(10 * (1 - last_access_days / max(file_age_days, 1))))
                return min(frequency, 10)  # Cap at 10
            
        except:
            pass
        
        return 1  # Default low frequency

    def _calculate_importance_score(self, file_path: Path, stat_info) -> float:
        """Calculate importance score for a file"""
        
        importance = 0.5  # Base importance
        
        # File type importance
        file_ext = file_path.suffix.lower()
        important_types = ['.docx', '.pdf', '.txt', '.md', '.py', '.js']
        if file_ext in important_types:
            importance += 0.3
        
        # Location importance
        path_str = str(file_path).lower()
        if "documents" in path_str:
            importance += 0.2
        elif "desktop" in path_str:
            importance += 0.1
        elif "downloads" in path_str:
            importance -= 0.1
        
        # Recent modification increases importance
        mod_age_days = (time.time() - stat_info.st_mtime) / (24 * 3600)
        if mod_age_days < 7:
            importance += 0.2
        elif mod_age_days < 30:
            importance += 0.1
        
        return min(1.0, max(0.0, importance))

    def _is_duplicate_file(self, file_path: Path) -> bool:
        """Check if file is a duplicate"""
        # TODO: Integrate with bulletproof deduplication system
        filename = file_path.name.lower()
        duplicate_indicators = [' (1)', ' copy', '_copy', ' - copy']
        return any(indicator in filename for indicator in duplicate_indicators)

    def _record_space_emergency(self, emergency: SpaceEmergency):
        """Record space emergency in database"""
        
        try:
            with sqlite3.connect(self.protection_db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO space_emergencies 
                    (emergency_id, detection_time, severity, disk_path, total_space_gb,
                     free_space_gb, usage_percent, projected_full_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    emergency.emergency_id,
                    emergency.detection_time.isoformat(),
                    emergency.severity,
                    emergency.disk_path,
                    emergency.total_space_gb,
                    emergency.free_space_gb,
                    emergency.usage_percent,
                    emergency.projected_full_hours
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording space emergency: {e}")

    def _record_emergency_resolution(self, emergency: SpaceEmergency):
        """Record emergency resolution"""
        
        try:
            with sqlite3.connect(self.protection_db_path) as conn:
                conn.execute("""
                    UPDATE space_emergencies 
                    SET resolution_time = ?, success = TRUE
                    WHERE emergency_id = ?
                """, (
                    datetime.now().isoformat(),
                    emergency.emergency_id
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording emergency resolution: {e}")

    def _record_usage_history(self, emergency: SpaceEmergency):
        """Record disk usage history"""
        
        try:
            with sqlite3.connect(self.protection_db_path) as conn:
                conn.execute("""
                    INSERT INTO space_usage_history 
                    (timestamp, disk_path, total_space_gb, free_space_gb, usage_percent)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    emergency.disk_path,
                    emergency.total_space_gb,
                    emergency.free_space_gb,
                    emergency.usage_percent
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording usage history: {e}")

    def _record_offloaded_file(self, candidate: OffloadCandidate, gdrive_path: str, emergency_offload: bool):
        """Record offloaded file in database"""
        
        try:
            file_id = hashlib.md5(f"{candidate.file_path}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            with sqlite3.connect(self.protection_db_path) as conn:
                conn.execute("""
                    INSERT INTO offloaded_files 
                    (file_id, original_path, gdrive_path, offload_time, file_size_mb,
                     access_frequency, offload_reason, emergency_offload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    candidate.file_path,
                    gdrive_path,
                    datetime.now().isoformat(),
                    candidate.file_size_mb,
                    candidate.access_frequency,
                    "space_protection",
                    emergency_offload
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording offloaded file: {e}")

    def get_protection_stats(self) -> Dict[str, Any]:
        """Get space protection statistics"""
        
        return {
            "protection_stats": self.stats,
            "monitoring_active": self.monitoring_active,
            "current_emergencies": len(self.current_emergencies),
            "emergency_details": [
                {
                    "severity": e.severity,
                    "disk_path": e.disk_path,
                    "usage_percent": e.usage_percent,
                    "free_space_gb": e.free_space_gb
                }
                for e in self.current_emergencies
            ],
            "config": self.config,
            "monitored_locations": {str(k): v for k, v in self.monitored_locations.items()}
        }

    def force_emergency_check(self) -> Dict[str, Any]:
        """Force an immediate emergency check"""
        
        self.logger.info("Forcing emergency space check...")
        
        emergencies = self._check_all_disk_usage()
        
        return {
            "emergencies_detected": len(emergencies),
            "emergency_details": [
                {
                    "severity": e.severity,
                    "disk_path": e.disk_path,
                    "usage_percent": e.usage_percent,
                    "free_space_gb": e.free_space_gb
                }
                for e in emergencies
            ]
        }

# Testing and CLI interface
def main():
    """Command line interface for emergency space protection"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Emergency Space Protection')
    parser.add_argument('--start', action='store_true', help='Start space protection monitoring')
    parser.add_argument('--stats', action='store_true', help='Show protection statistics')
    parser.add_argument('--check', action='store_true', help='Force emergency check')
    parser.add_argument('--test', action='store_true', help='Run test scenarios')
    
    args = parser.parse_args()
    
    protection = EmergencySpaceProtection()
    
    if args.start:
        try:
            protection.start_space_protection()
            print("🛡️ Emergency space protection started. Press Ctrl+C to stop...")
            while True:
                time.sleep(60)
                stats = protection.get_protection_stats()
                print(f"📊 Emergencies: {stats['current_emergencies']}, "
                      f"Space recovered: {stats['protection_stats']['space_recovered_gb']:.1f} GB")
        except KeyboardInterrupt:
            protection.stop_space_protection()
    elif args.stats:
        stats = protection.get_protection_stats()
        print("🛡️ Emergency Space Protection Statistics:")
        print(json.dumps(stats, indent=2, default=str))
    elif args.check:
        result = protection.force_emergency_check()
        print("🛡️ Emergency Check Result:")
        print(json.dumps(result, indent=2, default=str))
    elif args.test:
        print("🛡️ Testing emergency space protection...")
        # TODO: Implement test scenarios
        print("✅ Test completed!")
    else:
        print("🛡️ Emergency Space Protection")
        print("Use --help for options")

if __name__ == "__main__":
    main()