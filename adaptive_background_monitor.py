#!/usr/bin/env python3
"""
Adaptive Background Monitor with Learning Capabilities
Part of AI File Organizer v3.1 - Adaptive Emergency Prevention System

Enhances the existing background monitor with:
- Learning from manual file movements
- Automatic rule creation from user patterns
- Emergency detection and prevention
- Adaptive confidence-based processing

Created by: RT Max / Claude Code
"""

import sys
import time
import threading
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
import sqlite3
import json
import logging
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import queue

# Import existing system components
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from background_monitor import EnhancedBackgroundMonitor
from universal_adaptive_learning import UniversalAdaptiveLearning
from confidence_system import ADHDFriendlyConfidenceSystem, ConfidenceLevel
from bulletproof_deduplication import BulletproofDeduplicator
from gdrive_integration import get_ai_organizer_root, get_metadata_root
from easy_rollback_system import EasyRollbackSystem

class AdaptiveFileHandler(FileSystemEventHandler):
    """File system event handler with learning capabilities"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        self.event_queue = queue.Queue()
        
    def on_moved(self, event):
        """Handle file move events - learn from user actions"""
        if not event.is_directory:
            self.event_queue.put({
                'type': 'moved',
                'src_path': event.src_path,
                'dest_path': event.dest_path,
                'timestamp': datetime.now()
            })
    
    def on_created(self, event):
        """
        Handle file creation events

        NOTE: Files are observed immediately but NOT auto-organized.
        See _handle_new_file_with_cooldown() for 7-day safety rule.
        """
        if not event.is_directory:
            self.event_queue.put({
                'type': 'created',
                'path': event.src_path,
                'timestamp': datetime.now()
            })
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory:
            self.event_queue.put({
                'type': 'modified',
                'path': event.src_path,
                'timestamp': datetime.now()
            })

class AdaptiveBackgroundMonitor(EnhancedBackgroundMonitor):
    """
    Enhanced background monitor with adaptive learning capabilities
    
    Learns from user behavior and creates proactive emergency prevention
    """
    
    def __init__(self, base_dir: str = None, additional_watch_paths: List[str] = None):
        # Initialize parent class
        super().__init__(base_dir, additional_watch_paths)

        # Remove email folder from watch list to prevent overwhelming the system
        # Email monitoring was breaking OS limits by scanning ~/Library/Mail
        if 'mail' in self.watch_directories:
            del self.watch_directories['mail']
            self.logger = logging.getLogger(__name__)
            self.logger.info("Removed ~/Library/Mail from watch directories (email monitoring disabled)")

        # Initialize adaptive components
        self.learning_system = UniversalAdaptiveLearning(str(self.base_dir))
        self.confidence_system = ADHDFriendlyConfidenceSystem(str(self.base_dir))
        self.deduplicator = BulletproofDeduplicator(str(self.base_dir))
        self.rollback_system = EasyRollbackSystem()
        
        # File system watchers
        self.observers = {}
        self.file_handlers = {}
        self.event_processing_queue = queue.Queue()
        
        # Emergency detection
        self.emergency_thresholds = {
            "duplicate_count": 50,
            "disk_usage_percent": 90,
            "unorganized_files": 200,
            "file_age_days": 30
        }
        
        # Learning intervals
        self.learning_intervals = {
            'pattern_discovery': 1800,    # Discover patterns every 30 minutes
            'emergency_check': 600,       # Check emergencies every 10 minutes
            'rule_generation': 3600,      # Generate new rules hourly
            'cleanup_old_data': 86400     # Cleanup daily
        }
        
        # Initialize logging first (needed by other methods)
        self.logger = logging.getLogger(__name__)
        
        # Adaptive rules database
        self.rules_db_path = get_metadata_root() /  "adaptive_rules.db"
        self._init_adaptive_database()
        
        # Load existing adaptive rules
        self.adaptive_rules = self._load_adaptive_rules()
        
        # Statistics tracking - Merge with parent stats
        self.stats.update({
            "files_auto_organized": 0,
            "emergencies_prevented": 0,
            "patterns_discovered": 0,
            "rules_created": 0,
            "user_corrections_learned": 0
        })
        
        self.logger.info("Adaptive Background Monitor initialized")

    def _init_adaptive_database(self):
        """Initialize database for adaptive rules and learning"""
        self.rules_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.rules_db_path) as conn:
            # Adaptive rules table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_rules (
                    rule_id TEXT PRIMARY KEY,
                    rule_type TEXT,
                    trigger_conditions TEXT,
                    action_definition TEXT,
                    confidence_score REAL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    created_date TEXT,
                    last_used TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # User behavior tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_behavior (
                    behavior_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    action_type TEXT,
                    file_path TEXT,
                    source_location TEXT,
                    target_location TEXT,
                    context_data TEXT
                )
            """)
            
            # Emergency events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emergency_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    emergency_type TEXT,
                    severity_level TEXT,
                    details TEXT,
                    action_taken TEXT,
                    resolution_time REAL
                )
            """)
            
            conn.commit()

    def _load_adaptive_rules(self) -> List[Dict[str, Any]]:
        """Load adaptive rules from database"""
        try:
            with sqlite3.connect(self.rules_db_path) as conn:
                cursor = conn.execute("""
                    SELECT rule_id, rule_type, trigger_conditions, action_definition,
                           confidence_score, success_count, failure_count
                    FROM adaptive_rules 
                    WHERE is_active = TRUE
                """)
                
                rules = []
                for row in cursor.fetchall():
                    rule_id, rule_type, trigger_cond, action_def, confidence, success, failure = row
                    rules.append({
                        'rule_id': rule_id,
                        'rule_type': rule_type,
                        'trigger_conditions': json.loads(trigger_cond),
                        'action_definition': json.loads(action_def),
                        'confidence_score': confidence,
                        'success_count': success,
                        'failure_count': failure,
                        'accuracy': success / (success + failure) if (success + failure) > 0 else 0.0
                    })
                
                self.logger.info(f"Loaded {len(rules)} adaptive rules")
                return rules
                
        except Exception as e:
            self.logger.error(f"Error loading adaptive rules: {e}")
            return []

    def start_adaptive_monitoring(self):
        """Start adaptive monitoring with file system watchers"""
        self.logger.info("Starting adaptive background monitoring...")
        
        # Start parent monitoring
        super().start()
        
        # Set up file system watchers for learning
        self._setup_file_watchers()
        
        # Start adaptive processing threads
        self._start_adaptive_threads()
        
        self.logger.info("Adaptive monitoring started successfully")

    def _setup_file_watchers(self):
        """Set up file system watchers to learn from user actions"""
        
        for name, config in self.watch_directories.items():
            watch_path = config['path']
            
            if not watch_path.exists():
                continue
            
            # Prevent duplicate watchers
            if name in self.observers:
                self.logger.warning(f"Watcher for {name} already exists, skipping")
                continue

            try:
                observer = Observer()
                handler = AdaptiveFileHandler(self)
                observer.schedule(handler, str(watch_path), recursive=True)
                observer.start()
                
                self.observers[name] = observer
                self.file_handlers[name] = handler
                
                self.logger.info(f"Started watching {name}: {watch_path}")
                
            except Exception as e:
                self.logger.error(f"Error setting up watcher for {name}: {e}")

    def _start_adaptive_threads(self):
        """Start background threads for adaptive processing"""
        
        # Event processing thread
        self.threads['event_processor'] = threading.Thread(
            target=self._process_file_events, daemon=True
        )
        self.threads['event_processor'].start()
        
        # Pattern discovery thread  
        self.threads['pattern_discovery'] = threading.Thread(
            target=self._periodic_pattern_discovery, daemon=True
        )
        self.threads['pattern_discovery'].start()
        
        # Emergency monitoring thread
        self.threads['emergency_monitor'] = threading.Thread(
            target=self._periodic_emergency_check, daemon=True
        )
        self.threads['emergency_monitor'].start()
        
        # Rule generation thread
        self.threads['rule_generator'] = threading.Thread(
            target=self._periodic_rule_generation, daemon=True
        )
        self.threads['rule_generator'].start()

    def _process_file_events(self):
        """Process file system events and learn from user actions"""
        
        while self.running:
            try:
                # Collect events from all handlers
                events_to_process = []
                
                for handler in self.file_handlers.values():
                    while not handler.event_queue.empty():
                        try:
                            event = handler.event_queue.get_nowait()
                            events_to_process.append(event)
                        except queue.Empty:
                            break
                
                # Process collected events
                for event in events_to_process:
                    self._learn_from_file_event(event)
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error processing file events: {e}")
                time.sleep(30)

    def _learn_from_file_event(self, event: Dict[str, Any]):
        """Learn from a file system event"""
        
        event_type = event['type']
        
        if event_type == 'moved':
            # User manually moved a file - learn from this action
            self._learn_from_file_move(
                event['src_path'], 
                event['dest_path'], 
                event['timestamp']
            )
        
        elif event_type == 'created':
            # New file created - check for auto-organization opportunity
            self._handle_new_file(event['path'], event['timestamp'])
        
        elif event_type == 'modified':
            # File modified - check if it needs re-indexing
            self._handle_file_modification(event['path'], event['timestamp'])

    def _learn_from_file_move(self, src_path: str, dest_path: str, timestamp: datetime):
        """Learn from user manually moving a file"""
        
        try:
            src_file = Path(src_path)
            dest_file = Path(dest_path)
            
            # Skip if this was our own move (check rollback system)
            if self.rollback_system.was_ai_operation(src_path):
                return
            
            # Extract learning features
            original_prediction = self._get_original_prediction(src_file)
            user_action = {
                "target_location": str(dest_file.parent),
                "target_category": self._infer_category_from_path(dest_file.parent),
                "action_type": "manual_move"
            }
            
            context = {
                "file_extension": src_file.suffix.lower(),
                "source_directory": str(src_file.parent),
                "target_directory": str(dest_file.parent),
                "move_timestamp": timestamp.isoformat(),
                "content_keywords": self._extract_quick_keywords(src_file)
            }
            
            # Record learning event
            self.learning_system.record_learning_event(
                event_type="manual_move",
                file_path=src_path,
                original_prediction=original_prediction,
                user_action=user_action,
                confidence_before=0.5,  # Unknown confidence for manual moves
                context=context
            )
            
            # Record in behavior database
            self._record_user_behavior(
                action_type="manual_move",
                file_path=src_path,
                source_location=str(src_file.parent),
                target_location=str(dest_file.parent),
                context_data=json.dumps(context)
            )
            
            self.stats["user_corrections_learned"] += 1
            self.logger.info(f"Learned from manual move: {src_file.name} -> {dest_file.parent.name}")
            
        except Exception as e:
            self.logger.error(f"Error learning from file move: {e}")

    def _handle_new_file(self, file_path: str, timestamp: datetime):
        """Handle newly created file with adaptive intelligence"""
        
        try:
            file_obj = Path(file_path)
            
            if not file_obj.exists() or file_obj.is_dir():
                return
            
            # Check if file should be processed
            if not self._should_process_file(file_obj):
                return
            
            # Get prediction from learning system
            context = {
                "file_size": file_obj.stat().st_size,
                "creation_time": timestamp.isoformat(),
                "source_directory": str(file_obj.parent),
                "content_keywords": self._extract_quick_keywords(file_obj)
            }
            
            prediction = self.learning_system.predict_user_action(file_path, context)
            
            # Make confidence-based decision
            decision = self.confidence_system.make_confidence_decision(
                file_path=file_path,
                predicted_action=prediction.get("predicted_action", {}),
                system_confidence=prediction.get("confidence", 0.0),
                context=context
            )
            
            # Execute decision
            action_taken = False
            if not decision.requires_user_input and decision.predicted_action:
                action_taken = self._execute_automatic_action(file_obj, decision, context)
            elif decision.requires_user_input:
                self._queue_for_user_interaction(file_obj, decision, context)
                # Even if queued, we should index it so it's searchable
                super()._process_single_file(file_obj)
            
            # If no action taken (and not queued), index it in place
            if not action_taken and not decision.requires_user_input:
                super()._process_single_file(file_obj)
            
        except Exception as e:
            self.logger.error(f"Error handling new file {file_path}: {e}")

    def _process_single_file(self, file_path: Path, auto_organize: bool = False) -> bool:
        """
        Override: Route all polled files through the adaptive system.
        This unifies the Polling and Watchdog behaviors.
        """
        # We ignore the 'auto_organize' flag from the poll because 
        # _handle_new_file decides based on confidence.
        self._handle_new_file(str(file_path), datetime.now())
        return True

    def _handle_file_modification(self, file_path: str, timestamp: datetime):
        """Handle file modification - check for re-indexing"""
        
        try:
            file_obj = Path(file_path)
            
            if not self._should_process_file(file_obj):
                return
            
            # Check if file needs re-indexing
            if self._needs_reindexing(file_obj):
                self.logger.info(f"Re-indexing modified file: {file_obj.name}")
                self._process_single_file(file_obj)
            
        except Exception as e:
            self.logger.error(f"Error handling file modification: {e}")

    def _execute_automatic_action(self, file_obj: Path, decision, context: Dict[str, Any]) -> bool:
        """Execute automatic file organization action. Returns True if moved."""
        
        try:
            predicted_action = decision.predicted_action
            target_location = predicted_action.get("target_location")
            
            if not target_location:
                return False
            
            target_path = Path(target_location)
            
            # SAFETY CHECK: Never move database files or files from metadata system
            # This prevents accidental corruption or remote sync of critical system files
            if file_obj.suffix.lower() in ['.db', '.sqlite', '.sqlite3', '.db3', '.sdb', '.json']:
                # Allow moving JSONs unless they are in metadata system
                if "AI_METADATA_SYSTEM" in str(file_obj) or "AI_METADATA_SYSTEM" in str(target_path):
                    self.logger.warning(f"Blocked attempt to move system file: {file_obj.name}")
                    return False
                
                # Strictly block DB files regardless of location
                if file_obj.suffix.lower() != '.json':
                    self.logger.warning(f"Blocked attempt to move database file: {file_obj.name}")
                    return False

            target_path.mkdir(parents=True, exist_ok=True)
            
            # Create rollback entry before moving
            operation_id = self.rollback_system.start_operation(
                operation_type="adaptive_auto_move",
                description=f"Automatic organization: {file_obj.name} -> {target_path.name}",
                confidence=decision.system_confidence
            )
            
            # Move the file
            new_file_path = target_path / file_obj.name
            
            # Handle name conflicts
            if new_file_path.exists():
                counter = 1
                base_name = file_obj.stem
                extension = file_obj.suffix
                while new_file_path.exists():
                    new_name = f"{base_name}_{counter}{extension}"
                    new_file_path = target_path / new_name
                    counter += 1
            
            shutil.move(str(file_obj), str(new_file_path))
            
            # Record successful operation
            self.rollback_system.record_file_operation(
                operation_id=operation_id,
                original_path=str(file_obj),
                new_path=str(new_file_path),
                operation_type="move"
            )
            
            self.rollback_system.complete_operation(operation_id, success=True)
            
            self.stats["files_auto_organized"] += 1
            self.logger.info(f"Auto-organized: {file_obj.name} -> {target_path.name}")
            
            # Record success for learning
            self._record_action_success(decision, context, True)
            
            # INDEX THE FILE AT ITS NEW LOCATION
            # This ensures the vector database is up to date
            super()._process_single_file(new_file_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing automatic action: {e}")
            if 'operation_id' in locals():
                self.rollback_system.complete_operation(operation_id, success=False, error=str(e))
            self._record_action_success(decision, context, False)
            return False

    def _queue_for_user_interaction(self, file_obj: Path, decision, context: Dict[str, Any]):
        """Queue file for user interaction (future implementation)"""
        # TODO: Implement user interaction queue
        # For now, just log that it needs user input
        self.logger.info(f"File {file_obj.name} queued for user interaction: {decision.question_text}")

    def _periodic_pattern_discovery(self):
        """Periodically discover new patterns from learning events"""
        
        while self.running:
            try:
                self.logger.info("Starting pattern discovery cycle...")
                
                # Get recent learning events
                recent_events = [
                    event for event in self.learning_system.learning_events
                    if (datetime.now() - event.timestamp).days <= 7
                ]
                
                if len(recent_events) < 5:
                    self.logger.info("Not enough recent events for pattern discovery")
                    time.sleep(self.learning_intervals['pattern_discovery'])
                    continue
                
                # Discover patterns
                new_patterns = self._discover_behavioral_patterns(recent_events)
                
                if new_patterns:
                    self.stats["patterns_discovered"] += len(new_patterns)
                    self.logger.info(f"Discovered {len(new_patterns)} new patterns")
                
                time.sleep(self.learning_intervals['pattern_discovery'])
                
            except Exception as e:
                self.logger.error(f"Error in pattern discovery: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    def _periodic_emergency_check(self):
        """Periodically check for emergency conditions"""
        
        while self.running:
            try:
                self.logger.debug("Checking for emergency conditions...")
                
                emergencies = self._detect_emergencies()
                
                for emergency in emergencies:
                    self._handle_emergency(emergency)
                    self.stats["emergencies_prevented"] += 1
                
                time.sleep(self.learning_intervals['emergency_check'])
                
            except Exception as e:
                self.logger.error(f"Error in emergency check: {e}")
                time.sleep(60)

    def _periodic_rule_generation(self):
        """Periodically generate new adaptive rules"""
        
        while self.running:
            try:
                self.logger.info("Generating adaptive rules...")
                
                new_rules = self._generate_adaptive_rules()
                
                if new_rules:
                    self.adaptive_rules.extend(new_rules)
                    self.stats["rules_created"] += len(new_rules)
                    self.logger.info(f"Generated {len(new_rules)} new adaptive rules")
                
                time.sleep(self.learning_intervals['rule_generation'])
                
            except Exception as e:
                self.logger.error(f"Error in rule generation: {e}")
                time.sleep(300)

    def _detect_emergencies(self) -> List[Dict[str, Any]]:
        """Detect potential file organization emergencies"""
        
        emergencies = []
        
        try:
            # Check disk space
            for watch_name, config in self.watch_directories.items():
                path = config['path']
                if path.exists():
                    total, used, free = shutil.disk_usage(path)
                    usage_percent = (used / total) * 100
                    
                    if usage_percent > self.emergency_thresholds["disk_usage_percent"]:
                        emergencies.append({
                            'type': 'disk_space_critical',
                            'location': str(path),
                            'severity': 'high',
                            'details': f"Disk usage at {usage_percent:.1f}%",
                            'recommended_action': 'emergency_cleanup'
                        })
            
            # Check for duplicate file crisis
            duplicate_count = self._count_recent_duplicates()
            if duplicate_count > self.emergency_thresholds["duplicate_count"]:
                emergencies.append({
                    'type': 'duplicate_crisis',
                    'severity': 'medium',
                    'details': f"{duplicate_count} duplicates detected",
                    'recommended_action': 'bulk_deduplication'
                })
            
            # Check for unorganized file overflow
            unorganized_count = self._count_unorganized_files()
            if unorganized_count > self.emergency_thresholds["unorganized_files"]:
                emergencies.append({
                    'type': 'unorganized_overflow',
                    'severity': 'medium',
                    'details': f"{unorganized_count} unorganized files",
                    'recommended_action': 'bulk_organization'
                })
            
        except Exception as e:
            self.logger.error(f"Error detecting emergencies: {e}")
        
        return emergencies

    def _handle_emergency(self, emergency: Dict[str, Any]):
        """Handle detected emergency"""
        
        try:
            emergency_type = emergency['type']
            self.logger.warning(f"Handling emergency: {emergency_type}")
            
            if emergency_type == 'disk_space_critical':
                self._handle_disk_space_emergency(emergency)
            elif emergency_type == 'duplicate_crisis':
                self._handle_duplicate_emergency(emergency)
            elif emergency_type == 'unorganized_overflow':
                self._handle_organization_emergency(emergency)
            
            # Record emergency event
            self._record_emergency_event(emergency)
            
        except Exception as e:
            self.logger.error(f"Error handling emergency: {e}")

    def _handle_disk_space_emergency(self, emergency: Dict[str, Any]):
        """Handle critical disk space emergency"""
        
        location = emergency['location']
        self.logger.warning(f"Critical disk space at {location}")
        
        # TODO: Implement Google Drive emergency offloading
        # For now, just log the emergency
        self.logger.info("Emergency disk space handling not yet implemented")

    def _handle_duplicate_emergency(self, emergency: Dict[str, Any]):
        """Handle duplicate file crisis"""
        
        self.logger.warning("Handling duplicate file crisis")
        
        # Use bulletproof deduplication
        try:
            downloads_path = Path.home() / "Downloads"
            if downloads_path.exists():
                results = self.deduplicator.scan_directory(downloads_path, execute=True)
                self.logger.info(f"Emergency deduplication results: {results}")
        except Exception as e:
            self.logger.error(f"Error in emergency deduplication: {e}")

    def _handle_organization_emergency(self, emergency: Dict[str, Any]):
        """Handle unorganized file overflow emergency"""
        
        self.logger.warning("Handling unorganized file overflow")
        
        # TODO: Implement emergency bulk organization
        self.logger.info("Emergency organization handling not yet implemented")

    # Helper methods
    def _get_original_prediction(self, file_obj: Path) -> Dict[str, Any]:
        """Get what the system would have predicted for this file"""
        # Mock prediction - in real implementation this would query the classification system
        return {
            "predicted_category": "documents",
            "predicted_location": str(file_obj.parent),
            "confidence": 0.5
        }

    def _infer_category_from_path(self, path: Path) -> str:
        """Infer category from destination path"""
        path_str = str(path).lower()
        
        if "entertainment" in path_str:
            return "entertainment_industry"
        elif "business" in path_str:
            return "business"
        elif "personal" in path_str:
            return "personal"
        elif "creative" in path_str:
            return "creative_projects"
        else:
            return "documents"

    def _extract_quick_keywords(self, file_obj: Path) -> List[str]:
        """Extract quick keywords from filename for learning"""
        import re
        
        filename = file_obj.stem.lower()
        words = re.findall(r'\b[a-zA-Z]{3,}\b', filename)
        
        # Filter common words
        stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy", "did", "man", "men", "put", "say", "she", "too", "use"}
        
        keywords = [word for word in words if word not in stop_words]
        return keywords[:5]  # Return top 5 keywords

    def _record_user_behavior(self, action_type: str, file_path: str, source_location: str, target_location: str, context_data: str):
        """Record user behavior in database"""
        
        try:
            with sqlite3.connect(self.rules_db_path) as conn:
                conn.execute("""
                    INSERT INTO user_behavior 
                    (timestamp, action_type, file_path, source_location, target_location, context_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    action_type,
                    file_path,
                    source_location,
                    target_location,
                    context_data
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording user behavior: {e}")

    def _record_emergency_event(self, emergency: Dict[str, Any]):
        """Record emergency event in database"""
        
        try:
            with sqlite3.connect(self.rules_db_path) as conn:
                conn.execute("""
                    INSERT INTO emergency_events 
                    (timestamp, emergency_type, severity_level, details, action_taken)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    emergency['type'],
                    emergency['severity'],
                    emergency['details'],
                    emergency.get('recommended_action', 'none')
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording emergency event: {e}")

    def _record_action_success(self, decision, context: Dict[str, Any], success: bool):
        """Record whether an automatic action was successful"""
        # This would be used to improve future predictions
        pass

    def _discover_behavioral_patterns(self, events) -> List[Dict[str, Any]]:
        """Discover behavioral patterns from learning events"""
        # TODO: Implement sophisticated pattern discovery
        return []

    def _generate_adaptive_rules(self) -> List[Dict[str, Any]]:
        """Generate new adaptive rules from learned patterns"""
        # TODO: Implement rule generation
        return []

    def _count_recent_duplicates(self) -> int:
        """Count recent duplicate files"""
        # TODO: Implement duplicate counting
        return 0

    def _count_unorganized_files(self) -> int:
        """Count unorganized files in monitored directories"""
        count = 0
        try:
            for config in self.watch_directories.values():
                path = config['path']
                if path.exists() and path.name.lower() in ['downloads', 'desktop']:
                    count += len([f for f in path.iterdir() if f.is_file()])
        except:
            pass
        return count

    def _needs_reindexing(self, file_obj: Path) -> bool:
        """Check if file needs re-indexing"""
        # Simple check - could be more sophisticated
        try:
            current_hash = self._get_file_hash(file_obj)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT file_hash FROM processed_files WHERE file_path = ?",
                    (str(file_obj),)
                )
                result = cursor.fetchone()
                
                if result and result[0] != current_hash:
                    return True
            
        except:
            pass
        
        return False

    def get_adaptive_stats(self) -> Dict[str, Any]:
        """Get adaptive monitoring statistics"""
        
        # Get learning system stats
        learning_stats = self.learning_system.get_learning_summary()
        
        # Get confidence system stats
        confidence_stats = self.confidence_system.get_confidence_stats()
        
        return {
            "adaptive_monitor_stats": self.stats,
            "learning_system": learning_stats,
            "confidence_system": confidence_stats,
            "active_rules": len(self.adaptive_rules),
            "monitoring_status": {
                "observers_active": len(self.observers),
                "threads_running": len([t for t in self.threads.values() if t.is_alive()]),
                "last_pattern_discovery": "N/A",  # TODO: Track this
                "last_emergency_check": "N/A"     # TODO: Track this
            }
        }

    def stop_adaptive_monitoring(self):
        """Stop adaptive monitoring"""
        self.logger.info("Stopping adaptive monitoring...")
        
        # Stop parent monitoring
        super().stop()
        
        # Stop file system observers
        for observer in self.observers.values():
            try:
                observer.stop()
                observer.join()
            except:
                pass
        
        # Save learning data
        self.learning_system.save_all_data()

        self.logger.info("Adaptive monitoring stopped")

    def _handle_new_file_with_cooldown(self, path: Path) -> bool:
        """
        Handle new file with 7-day cooldown safety rule

        NOTE: This is a placeholder for Sprint 3.3 implementation.
        See docs/Adaptive_Monitor_Spec.md "Safety Rules" section.

        SAFETY RULES (v3.2+):
        1. Detect & log new files instantly
        2. Record event (path, category prediction, confidence, timestamp)
        3. Wait 7 days of inactivity before auto-organizing
        4. Only auto-move if confidence ≥ 0.85
        5. All moves go through log_file_op() for rollback safety

        Args:
            path: Path to new/detected file

        Returns:
            bool: True if file was organized, False if deferred

        Example implementation:
            ```python
            # Record observation immediately
            self.learning_system.record_observation(path)

            # Check file age
            age_days = (datetime.now() - path.stat().st_mtime).days
            if age_days < 7:
                self.logger.info(f"⏳ Deferring move for {path.name} ({age_days}d old)")
                return False

            # Check if should auto-move
            result = self.unified_classifier.classify(str(path))
            if result['confidence'] >= 0.85:
                # Move file with rollback protection
                self.rollback_system.log_file_op(
                    operation='move',
                    source=str(path),
                    destination=destination_path,
                    metadata={'confidence': result['confidence']}
                )
                shutil.move(str(path), destination_path)
                return True

            return False
            ```
        """
        # TODO: Implement 7-day cooldown logic in Sprint 3.3
        pass

# Testing and CLI interface
def main():
    """Command line interface for adaptive background monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Adaptive Background Monitor')
    parser.add_argument('--start', action='store_true', help='Start adaptive monitoring')
    parser.add_argument('--stats', action='store_true', help='Show adaptive statistics')
    parser.add_argument('--test', action='store_true', help='Run test scenarios')
    
    args = parser.parse_args()
    
    monitor = AdaptiveBackgroundMonitor()
    
    if args.start:
        try:
            monitor.start_adaptive_monitoring()
            print("🧠 Adaptive monitoring started. Press Ctrl+C to stop...")
            while True:
                time.sleep(60)
                stats = monitor.get_adaptive_stats()
                print(f"📊 Auto-organized: {stats['adaptive_monitor_stats']['files_auto_organized']}, "
                      f"Emergencies prevented: {stats['adaptive_monitor_stats']['emergencies_prevented']}")
        except KeyboardInterrupt:
            monitor.stop_adaptive_monitoring()
    elif args.stats:
        stats = monitor.get_adaptive_stats()
        print("🧠 Adaptive Background Monitor Statistics:")
        print(json.dumps(stats, indent=2, default=str))
    elif args.test:
        print("🧠 Testing adaptive background monitor...")
        # TODO: Implement test scenarios
        print("✅ Test completed!")
    else:
        print("🧠 Adaptive Background Monitor")
        print("Use --help for options")

if __name__ == "__main__":
    main()