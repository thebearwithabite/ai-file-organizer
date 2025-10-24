#!/usr/bin/env python3
"""
Automated Deduplication Service with Real-Time Prevention
Part of AI File Organizer v3.1 - Adaptive Emergency Prevention System

Integrates bulletproof deduplication into the automated workflow for:
- Real-time duplicate prevention during file operations
- Proactive duplicate detection and removal
- Emergency duplicate crisis prevention
- Learning-based duplicate pattern recognition

Created by: RT Max / Claude Code
"""

import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Tuple
import sqlite3
import json
import logging
import hashlib
import shutil
from dataclasses import dataclass

# Import existing system components
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from bulletproof_deduplication import BulletproofDeduplicator
from universal_adaptive_learning import UniversalAdaptiveLearning
from confidence_system import ADHDFriendlyConfidenceSystem
from gdrive_integration import get_ai_organizer_root
from easy_rollback_system import EasyRollbackSystem

@dataclass
class DuplicationThreat:
    """A detected duplication threat"""
    threat_id: str
    threat_type: str  # "immediate", "pattern", "overflow", "crisis"
    severity: str     # "low", "medium", "high", "critical"
    file_path: str
    duplicate_paths: List[str]
    threat_score: float
    recommended_action: str
    context: Dict[str, Any]

class AutomatedDeduplicationService:
    """
    Automated deduplication service that integrates with the file organization workflow
    
    Provides real-time duplicate prevention and proactive cleanup
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        
        # Initialize core components
        self.deduplicator = BulletproofDeduplicator(str(self.base_dir))
        self.learning_system = UniversalAdaptiveLearning(str(self.base_dir))
        self.confidence_system = ADHDFriendlyConfidenceSystem(str(self.base_dir))
        self.rollback_system = EasyRollbackSystem()
        
        # Service configuration
        self.service_db_path = self.base_dir / "04_METADATA_SYSTEM" / "deduplication_service.db"
        self.config = {
            "real_time_enabled": True,
            "proactive_scanning": True,
            "emergency_threshold": 50,        # Files before emergency
            "pattern_threshold": 0.8,         # Confidence for pattern detection
            "auto_cleanup_threshold": 0.9,    # Confidence for automatic cleanup
            "scan_intervals": {
                "real_time": 60,              # Check every minute for real-time threats
                "proactive": 3600,            # Proactive scan every hour
                "deep_scan": 86400,           # Deep scan daily
                "pattern_analysis": 1800      # Pattern analysis every 30 minutes
            }
        }
        
        # Threat detection patterns
        self.threat_patterns = {
            "download_duplicates": {
                "pattern": "multiple downloads of same file",
                "triggers": ["filename similarity", "size match", "time proximity"],
                "severity_multiplier": 1.5
            },
            "screenshot_spam": {
                "pattern": "excessive screenshot generation",
                "triggers": ["screenshot filename", "image format", "rapid creation"],
                "severity_multiplier": 2.0
            },
            "attachment_overflow": {
                "pattern": "repeated email attachment saves",
                "triggers": ["attachment filename pattern", "email source", "duplicate content"],
                "severity_multiplier": 1.3
            },
            "version_chaos": {
                "pattern": "multiple versions of same document",
                "triggers": ["version indicators", "timestamp proximity", "content similarity"],
                "severity_multiplier": 1.8
            }
        }
        
        # Statistics tracking
        self.stats = {
            "duplicates_prevented": 0,
            "threats_detected": 0,
            "emergency_interventions": 0,
            "automatic_cleanups": 0,
            "space_recovered_mb": 0.0,
            "patterns_learned": 0
        }
        
        # Active monitoring
        self.monitoring_active = False
        self.monitoring_threads = {}
        self.threat_queue = []
        
        # Initialize database
        self._init_service_database()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("Automated Deduplication Service initialized")

    def _init_service_database(self):
        """Initialize service database for tracking deduplication activities"""
        self.service_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.service_db_path) as conn:
            # Detected threats table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS detected_threats (
                    threat_id TEXT PRIMARY KEY,
                    detection_time TEXT,
                    threat_type TEXT,
                    severity TEXT,
                    file_path TEXT,
                    duplicate_paths TEXT,
                    threat_score REAL,
                    recommended_action TEXT,
                    action_taken TEXT,
                    resolution_time TEXT,
                    success BOOLEAN
                )
            """)
            
            # Deduplication operations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deduplication_operations (
                    operation_id TEXT PRIMARY KEY,
                    start_time TEXT,
                    operation_type TEXT,
                    target_directory TEXT,
                    files_scanned INTEGER,
                    duplicates_found INTEGER,
                    files_removed INTEGER,
                    space_recovered INTEGER,
                    confidence_level REAL,
                    automatic BOOLEAN,
                    success BOOLEAN,
                    error_message TEXT
                )
            """)
            
            # Duplicate patterns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT,
                    pattern_definition TEXT,
                    confidence REAL,
                    occurrences INTEGER,
                    last_seen TEXT,
                    effectiveness REAL
                )
            """)
            
            conn.commit()

    def start_automated_service(self):
        """Start the automated deduplication service"""
        self.logger.info("Starting automated deduplication service...")
        
        self.monitoring_active = True
        
        # Start monitoring threads
        if self.config["real_time_enabled"]:
            self.monitoring_threads["real_time"] = threading.Thread(
                target=self._real_time_monitoring, daemon=True
            )
            self.monitoring_threads["real_time"].start()
        
        if self.config["proactive_scanning"]:
            self.monitoring_threads["proactive"] = threading.Thread(
                target=self._proactive_scanning, daemon=True
            )
            self.monitoring_threads["proactive"].start()
        
        # Start pattern analysis thread
        self.monitoring_threads["pattern_analysis"] = threading.Thread(
            target=self._pattern_analysis, daemon=True
        )
        self.monitoring_threads["pattern_analysis"].start()
        
        # Start threat processing thread
        self.monitoring_threads["threat_processor"] = threading.Thread(
            target=self._process_threats, daemon=True
        )
        self.monitoring_threads["threat_processor"].start()
        
        self.logger.info("Automated deduplication service started successfully")

    def stop_automated_service(self):
        """Stop the automated deduplication service"""
        self.logger.info("Stopping automated deduplication service...")
        
        self.monitoring_active = False
        
        # Wait for threads to complete
        for thread in self.monitoring_threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.logger.info("Automated deduplication service stopped")

    def check_for_duplicates_before_move(self, file_path: str, target_directory: str) -> Dict[str, Any]:
        """
        Check for potential duplicates before moving a file
        
        Args:
            file_path: Source file path
            target_directory: Target directory for move
            
        Returns:
            Duplicate check result with recommendations
        """
        
        try:
            file_obj = Path(file_path)
            target_dir = Path(target_directory)
            
            if not file_obj.exists():
                return {"status": "error", "message": "Source file not found"}
            
            # Calculate file hash for comparison
            file_hash = self._calculate_file_hash(file_obj)
            
            # Check for duplicates in target directory
            target_duplicates = self._find_duplicates_in_directory(file_hash, target_dir)
            
            # Check for duplicates in common locations
            common_duplicates = self._find_duplicates_in_common_locations(file_hash, file_obj)
            
            # Combine all duplicates
            all_duplicates = target_duplicates + common_duplicates
            
            if not all_duplicates:
                return {
                    "status": "safe",
                    "duplicates_found": 0,
                    "recommendation": "proceed_with_move"
                }
            
            # Analyze duplicate threat
            threat = self._analyze_duplicate_threat(file_obj, all_duplicates)
            
            return {
                "status": "duplicates_found",
                "duplicates_found": len(all_duplicates),
                "duplicate_paths": [str(d) for d in all_duplicates],
                "threat_assessment": threat,
                "recommendation": self._get_duplicate_recommendation(threat)
            }
            
        except Exception as e:
            self.logger.error(f"Error checking for duplicates: {e}")
            return {"status": "error", "message": str(e)}

    def perform_pre_move_deduplication(self, file_path: str, target_directory: str) -> Dict[str, Any]:
        """
        Perform deduplication before moving a file to prevent duplicate creation
        
        Args:
            file_path: Source file path
            target_directory: Target directory
            
        Returns:
            Deduplication result
        """
        
        try:
            file_obj = Path(file_path)
            target_dir = Path(target_directory)
            
            # Check for duplicates
            duplicate_check = self.check_for_duplicates_before_move(file_path, target_directory)
            
            if duplicate_check["status"] != "duplicates_found":
                return duplicate_check
            
            duplicates = [Path(p) for p in duplicate_check["duplicate_paths"]]
            threat = duplicate_check["threat_assessment"]
            
            # Make confidence-based decision
            decision = self.confidence_system.make_confidence_decision(
                file_path=file_path,
                predicted_action={"action": "deduplicate", "keep_newest": True},
                system_confidence=threat["confidence"],
                context={"duplicates_found": len(duplicates), "threat_type": threat["type"]}
            )
            
            if decision.requires_user_input:
                return {
                    "status": "user_input_required",
                    "question": decision.question_text,
                    "options": decision.suggested_actions,
                    "duplicates": duplicate_check["duplicate_paths"]
                }
            
            # Perform automatic deduplication
            result = self._perform_automatic_deduplication(file_obj, duplicates, threat)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in pre-move deduplication: {e}")
            return {"status": "error", "message": str(e)}

    def _real_time_monitoring(self):
        """Real-time monitoring for immediate duplicate threats"""
        
        while self.monitoring_active:
            try:
                self.logger.debug("Real-time duplicate monitoring check...")
                
                # Monitor high-risk directories
                high_risk_dirs = [
                    Path.home() / "Downloads",
                    Path.home() / "Desktop",
                    self.base_dir / "99_STAGING_EMERGENCY"
                ]
                
                for directory in high_risk_dirs:
                    if directory.exists():
                        threats = self._scan_directory_for_threats(directory, "real_time")
                        self.threat_queue.extend(threats)
                
                time.sleep(self.config["scan_intervals"]["real_time"])
                
            except Exception as e:
                self.logger.error(f"Error in real-time monitoring: {e}")
                time.sleep(60)

    def _proactive_scanning(self):
        """Proactive scanning for potential duplicate problems"""
        
        while self.monitoring_active:
            try:
                self.logger.info("Starting proactive duplicate scan...")
                
                # Scan all monitored directories
                monitored_dirs = [
                    Path.home() / "Downloads",
                    Path.home() / "Desktop", 
                    Path.home() / "Documents",
                    self.base_dir / "01_ACTIVE_PROJECTS"
                ]
                
                for directory in monitored_dirs:
                    if directory.exists():
                        threats = self._scan_directory_for_threats(directory, "proactive")
                        self.threat_queue.extend(threats)
                
                # Trigger emergency intervention if needed
                if len(self.threat_queue) > self.config["emergency_threshold"]:
                    self._trigger_emergency_intervention()
                
                time.sleep(self.config["scan_intervals"]["proactive"])
                
            except Exception as e:
                self.logger.error(f"Error in proactive scanning: {e}")
                time.sleep(300)

    def _pattern_analysis(self):
        """Analyze patterns in duplicate creation for learning"""
        
        while self.monitoring_active:
            try:
                self.logger.info("Analyzing duplicate patterns...")
                
                # Get recent deduplication operations
                recent_operations = self._get_recent_operations(days=7)
                
                if len(recent_operations) >= 5:
                    patterns = self._discover_duplicate_patterns(recent_operations)
                    
                    if patterns:
                        self.stats["patterns_learned"] += len(patterns)
                        self._save_discovered_patterns(patterns)
                
                time.sleep(self.config["scan_intervals"]["pattern_analysis"])
                
            except Exception as e:
                self.logger.error(f"Error in pattern analysis: {e}")
                time.sleep(300)

    def _process_threats(self):
        """Process detected threats based on confidence and severity"""
        
        while self.monitoring_active:
            try:
                if not self.threat_queue:
                    time.sleep(10)
                    continue
                
                # Process threats in order of severity
                self.threat_queue.sort(key=lambda t: (t.severity, t.threat_score), reverse=True)
                
                while self.threat_queue:
                    threat = self.threat_queue.pop(0)
                    self._handle_threat(threat)
                    time.sleep(1)  # Brief pause between threat handling
                
            except Exception as e:
                self.logger.error(f"Error processing threats: {e}")
                time.sleep(30)

    def _scan_directory_for_threats(self, directory: Path, scan_type: str) -> List[DuplicationThreat]:
        """Scan directory for duplication threats"""
        
        threats = []
        
        try:
            if not directory.exists():
                return threats
            
            # Use bulletproof deduplicator to find duplicates
            scan_results = self.deduplicator.scan_directory(directory, execute=False)
            
            if scan_results.get("duplicate_groups", 0) == 0:
                return threats
            
            self.logger.info(f"Found {scan_results['duplicate_groups']} duplicate groups in {directory}")
            
            # Analyze each file for threats
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    threat = self._analyze_file_for_threats(file_path, scan_type)
                    if threat:
                        threats.append(threat)
            
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return threats

    def _analyze_file_for_threats(self, file_path: Path, scan_type: str) -> Optional[DuplicationThreat]:
        """Analyze a single file for duplication threats"""
        
        try:
            file_hash = self._calculate_file_hash(file_path)
            
            # Find duplicates across system
            duplicates = self._find_duplicates_in_common_locations(file_hash, file_path)
            
            if len(duplicates) < 2:  # Need at least 2 files to be duplicates
                return None
            
            # Calculate threat score
            threat_score = self._calculate_threat_score(file_path, duplicates)
            
            if threat_score < 0.3:  # Below threat threshold
                return None
            
            # Determine threat type and severity
            threat_type = self._determine_threat_type(file_path, duplicates)
            severity = self._determine_threat_severity(threat_score, len(duplicates))
            
            # Generate threat ID
            threat_id = hashlib.md5(f"{file_path}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            threat = DuplicationThreat(
                threat_id=threat_id,
                threat_type=threat_type,
                severity=severity,
                file_path=str(file_path),
                duplicate_paths=[str(d) for d in duplicates if d != file_path],
                threat_score=threat_score,
                recommended_action=self._get_recommended_action(threat_score, threat_type),
                context={
                    "scan_type": scan_type,
                    "file_size": file_path.stat().st_size,
                    "duplicate_count": len(duplicates),
                    "detection_time": datetime.now().isoformat()
                }
            )
            
            return threat
            
        except Exception as e:
            self.logger.error(f"Error analyzing file for threats: {e}")
            return None

    def _handle_threat(self, threat: DuplicationThreat):
        """Handle a detected duplication threat"""
        
        try:
            self.logger.info(f"Handling {threat.severity} threat: {threat.threat_type}")
            
            # Record threat detection
            self._record_threat_detection(threat)
            self.stats["threats_detected"] += 1
            
            # Make confidence-based decision
            decision = self.confidence_system.make_confidence_decision(
                file_path=threat.file_path,
                predicted_action={"action": threat.recommended_action},
                system_confidence=threat.threat_score,
                context={
                    "threat_type": threat.threat_type,
                    "duplicate_count": len(threat.duplicate_paths),
                    "severity": threat.severity
                }
            )
            
            if decision.requires_user_input:
                # Queue for user interaction (future implementation)
                self.logger.info(f"Threat {threat.threat_id} requires user input")
                return
            
            # Perform automatic action
            if threat.recommended_action == "remove_duplicates":
                self._execute_automatic_deduplication(threat)
            elif threat.recommended_action == "emergency_cleanup":
                self._execute_emergency_cleanup(threat)
            
        except Exception as e:
            self.logger.error(f"Error handling threat {threat.threat_id}: {e}")

    def _execute_automatic_deduplication(self, threat: DuplicationThreat):
        """Execute automatic deduplication for a threat"""
        
        try:
            file_path = Path(threat.file_path)
            duplicate_paths = [Path(p) for p in threat.duplicate_paths]
            
            # Start rollback operation
            operation_id = self.rollback_system.start_operation(
                operation_type="automatic_deduplication",
                description=f"Remove duplicates of {file_path.name}",
                confidence=threat.threat_score
            )
            
            files_removed = 0
            space_recovered = 0
            
            # Keep the newest file, remove others
            all_files = [file_path] + duplicate_paths
            all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            file_to_keep = all_files[0]
            files_to_remove = all_files[1:]
            
            for duplicate in files_to_remove:
                if duplicate.exists():
                    file_size = duplicate.stat().st_size
                    
                    # Record operation before deletion
                    self.rollback_system.record_file_operation(
                        operation_id=operation_id,
                        original_path=str(duplicate),
                        new_path="[DELETED]",
                        operation_type="delete"
                    )
                    
                    # Delete the duplicate
                    duplicate.unlink()
                    
                    files_removed += 1
                    space_recovered += file_size
                    
                    self.logger.info(f"Removed duplicate: {duplicate.name}")
            
            # Complete rollback operation
            self.rollback_system.complete_operation(operation_id, success=True)
            
            # Update statistics
            self.stats["automatic_cleanups"] += 1
            self.stats["space_recovered_mb"] += space_recovered / (1024 * 1024)
            
            # Record successful operation
            self._record_deduplication_operation(
                operation_type="automatic",
                target_directory=str(file_path.parent),
                files_removed=files_removed,
                space_recovered=space_recovered,
                confidence=threat.threat_score,
                success=True
            )
            
            self.logger.info(f"Automatic deduplication completed: {files_removed} files removed, "
                           f"{space_recovered/(1024*1024):.1f} MB recovered")
            
        except Exception as e:
            self.logger.error(f"Error in automatic deduplication: {e}")
            self.rollback_system.complete_operation(operation_id, success=False, error=str(e))

    def _execute_emergency_cleanup(self, threat: DuplicationThreat):
        """Execute emergency cleanup for critical threats"""
        
        try:
            self.logger.warning(f"Executing emergency cleanup for threat {threat.threat_id}")
            
            # Use bulletproof deduplicator for emergency cleanup
            target_dir = Path(threat.file_path).parent
            
            cleanup_results = self.deduplicator.scan_directory(target_dir, execute=True)
            
            self.stats["emergency_interventions"] += 1
            self.stats["space_recovered_mb"] += cleanup_results.get("space_recoverable", 0) / (1024 * 1024)
            
            self.logger.info(f"Emergency cleanup completed: {cleanup_results}")
            
        except Exception as e:
            self.logger.error(f"Error in emergency cleanup: {e}")

    # Helper methods
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        return self.deduplicator.calculate_secure_hash(file_path)

    def _find_duplicates_in_directory(self, file_hash: str, directory: Path) -> List[Path]:
        """Find duplicates of a file in a specific directory"""
        duplicates = []
        
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    if self._calculate_file_hash(file_path) == file_hash:
                        duplicates.append(file_path)
        except:
            pass
        
        return duplicates

    def _find_duplicates_in_common_locations(self, file_hash: str, original_file: Path) -> List[Path]:
        """Find duplicates in common locations"""
        duplicates = []
        
        # Common locations to check
        search_locations = [
            Path.home() / "Downloads",
            Path.home() / "Desktop",
            Path.home() / "Documents",
            original_file.parent
        ]
        
        for location in search_locations:
            if location.exists():
                location_duplicates = self._find_duplicates_in_directory(file_hash, location)
                duplicates.extend(location_duplicates)
        
        # Remove duplicates from list
        seen = set()
        unique_duplicates = []
        for dup in duplicates:
            if str(dup) not in seen:
                seen.add(str(dup))
                unique_duplicates.append(dup)
        
        return unique_duplicates

    def _analyze_duplicate_threat(self, file_obj: Path, duplicates: List[Path]) -> Dict[str, Any]:
        """Analyze the threat level of detected duplicates"""
        
        # Basic threat assessment
        threat_score = min(1.0, len(duplicates) / 10)  # Higher score for more duplicates
        
        # Check for pattern-based threats
        for pattern_name, pattern_config in self.threat_patterns.items():
            if self._matches_threat_pattern(file_obj, duplicates, pattern_config):
                threat_score *= pattern_config["severity_multiplier"]
                break
        
        threat_score = min(1.0, threat_score)  # Cap at 1.0
        
        return {
            "type": "duplicate_overflow",
            "confidence": threat_score,
            "risk_factors": [
                f"{len(duplicates)} duplicates found",
                f"File size: {file_obj.stat().st_size / (1024*1024):.1f} MB"
            ]
        }

    def _get_duplicate_recommendation(self, threat: Dict[str, Any]) -> str:
        """Get recommendation based on duplicate threat assessment"""
        
        if threat["confidence"] > 0.8:
            return "automatic_deduplication"
        elif threat["confidence"] > 0.6:
            return "suggest_deduplication"
        else:
            return "monitor_situation"

    def _perform_automatic_deduplication(self, file_obj: Path, duplicates: List[Path], threat: Dict[str, Any]) -> Dict[str, Any]:
        """Perform automatic deduplication"""
        
        try:
            # Keep the newest file
            all_files = [file_obj] + duplicates
            all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            file_to_keep = all_files[0]
            files_to_remove = all_files[1:]
            
            removed_count = 0
            space_recovered = 0
            
            for file_to_remove in files_to_remove:
                if file_to_remove.exists():
                    space_recovered += file_to_remove.stat().st_size
                    file_to_remove.unlink()
                    removed_count += 1
            
            return {
                "status": "success",
                "action": "automatic_deduplication",
                "files_removed": removed_count,
                "space_recovered_mb": space_recovered / (1024 * 1024),
                "file_kept": str(file_to_keep)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def _calculate_threat_score(self, file_path: Path, duplicates: List[Path]) -> float:
        """Calculate threat score for a file and its duplicates"""
        
        score = 0.0
        
        # Base score from number of duplicates
        score += min(0.5, len(duplicates) / 10)
        
        # File size factor (larger files are more threatening)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        score += min(0.2, file_size_mb / 100)
        
        # Location factor (downloads/desktop are higher risk)
        path_str = str(file_path).lower()
        if "downloads" in path_str or "desktop" in path_str:
            score += 0.2
        
        # Age factor (recent files are higher risk)
        age_hours = (time.time() - file_path.stat().st_mtime) / 3600
        if age_hours < 24:
            score += 0.1
        
        return min(1.0, score)

    def _determine_threat_type(self, file_path: Path, duplicates: List[Path]) -> str:
        """Determine the type of duplication threat"""
        
        # Check against known patterns
        for pattern_name, pattern_config in self.threat_patterns.items():
            if self._matches_threat_pattern(file_path, duplicates, pattern_config):
                return pattern_name
        
        return "general_duplication"

    def _determine_threat_severity(self, threat_score: float, duplicate_count: int) -> str:
        """Determine threat severity level"""
        
        if threat_score > 0.8 or duplicate_count > 10:
            return "critical"
        elif threat_score > 0.6 or duplicate_count > 5:
            return "high"
        elif threat_score > 0.4 or duplicate_count > 2:
            return "medium"
        else:
            return "low"

    def _get_recommended_action(self, threat_score: float, threat_type: str) -> str:
        """Get recommended action for a threat"""
        
        if threat_score > 0.8:
            return "remove_duplicates"
        elif threat_score > 0.6:
            return "suggest_cleanup"
        elif threat_type in ["screenshot_spam", "download_duplicates"]:
            return "pattern_intervention"
        else:
            return "monitor"

    def _matches_threat_pattern(self, file_path: Path, duplicates: List[Path], pattern_config: Dict[str, Any]) -> bool:
        """Check if files match a threat pattern"""
        
        # Simple pattern matching - could be more sophisticated
        filename = file_path.name.lower()
        
        if "screenshot" in pattern_config["pattern"]:
            return "screenshot" in filename or any(ext in filename for ext in [".png", ".jpg"])
        
        if "download" in pattern_config["pattern"]:
            return "downloads" in str(file_path).lower()
        
        return False

    def _trigger_emergency_intervention(self):
        """Trigger emergency intervention for duplicate crisis"""
        
        self.logger.warning("Triggering emergency duplicate intervention!")
        
        # Execute emergency cleanup on high-risk directories
        emergency_dirs = [
            Path.home() / "Downloads",
            Path.home() / "Desktop"
        ]
        
        for directory in emergency_dirs:
            if directory.exists():
                try:
                    results = self.deduplicator.scan_directory(directory, execute=True)
                    self.logger.info(f"Emergency cleanup in {directory}: {results}")
                except Exception as e:
                    self.logger.error(f"Emergency cleanup failed in {directory}: {e}")
        
        self.stats["emergency_interventions"] += 1
        
        # Clear threat queue after emergency intervention
        self.threat_queue.clear()

    def _get_recent_operations(self, days: int) -> List[Dict[str, Any]]:
        """Get recent deduplication operations"""
        # TODO: Implement database query for recent operations
        return []

    def _discover_duplicate_patterns(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Discover patterns in duplicate creation"""
        # TODO: Implement pattern discovery
        return []

    def _save_discovered_patterns(self, patterns: List[Dict[str, Any]]):
        """Save discovered patterns to database"""
        # TODO: Implement pattern saving
        pass

    def _record_threat_detection(self, threat: DuplicationThreat):
        """Record threat detection in database"""
        
        try:
            with sqlite3.connect(self.service_db_path) as conn:
                conn.execute("""
                    INSERT INTO detected_threats 
                    (threat_id, detection_time, threat_type, severity, file_path, 
                     duplicate_paths, threat_score, recommended_action)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    threat.threat_id,
                    datetime.now().isoformat(),
                    threat.threat_type,
                    threat.severity,
                    threat.file_path,
                    json.dumps(threat.duplicate_paths),
                    threat.threat_score,
                    threat.recommended_action
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording threat detection: {e}")

    def _record_deduplication_operation(self, operation_type: str, target_directory: str, 
                                      files_removed: int, space_recovered: int, 
                                      confidence: float, success: bool):
        """Record deduplication operation in database"""
        
        try:
            operation_id = hashlib.md5(f"{operation_type}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            with sqlite3.connect(self.service_db_path) as conn:
                conn.execute("""
                    INSERT INTO deduplication_operations 
                    (operation_id, start_time, operation_type, target_directory,
                     files_removed, space_recovered, confidence_level, automatic, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    operation_id,
                    datetime.now().isoformat(),
                    operation_type,
                    target_directory,
                    files_removed,
                    space_recovered,
                    confidence,
                    True,
                    success
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording deduplication operation: {e}")

    def get_service_stats(self) -> Dict[str, Any]:
        """Get deduplication service statistics"""
        
        return {
            "service_stats": self.stats,
            "active_threats": len(self.threat_queue),
            "monitoring_active": self.monitoring_active,
            "config": self.config,
            "threat_patterns": list(self.threat_patterns.keys())
        }

# Testing and CLI interface
def main():
    """Command line interface for automated deduplication service"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Deduplication Service')
    parser.add_argument('--start', action='store_true', help='Start automated service')
    parser.add_argument('--stats', action='store_true', help='Show service statistics')
    parser.add_argument('--check', help='Check file for duplicates before move')
    parser.add_argument('--target', help='Target directory for duplicate check')
    
    args = parser.parse_args()
    
    service = AutomatedDeduplicationService()
    
    if args.start:
        try:
            service.start_automated_service()
            print("🔍 Automated deduplication service started. Press Ctrl+C to stop...")
            while True:
                time.sleep(60)
                stats = service.get_service_stats()
                print(f"📊 Threats detected: {stats['service_stats']['threats_detected']}, "
                      f"Active threats: {stats['active_threats']}")
        except KeyboardInterrupt:
            service.stop_automated_service()
    elif args.stats:
        stats = service.get_service_stats()
        print("🔍 Automated Deduplication Service Statistics:")
        print(json.dumps(stats, indent=2, default=str))
    elif args.check and args.target:
        result = service.check_for_duplicates_before_move(args.check, args.target)
        print("🔍 Duplicate Check Result:")
        print(json.dumps(result, indent=2, default=str))
    else:
        print("🔍 Automated Deduplication Service")
        print("Use --help for options")

if __name__ == "__main__":
    main()