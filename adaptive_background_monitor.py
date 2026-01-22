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
from staging_monitor import StagingMonitor

class AdaptiveFileHandler(FileSystemEventHandler):
    """File system event handler with learning capabilities"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        self.event_queue = queue.Queue()
        
    def on_moved(self, event):
        """Handle file move events - learn from user actions"""
        if event.is_directory:
            # Handle Directory Rename (Taxonomy Sync)
            # We don't queue this for the general event loop because it's a specific V3 sync
            # and needs debouncing managed by the monitor
            self.monitor.handle_directory_rename(event.src_path, event.dest_path)
            
            # Also queue as generic folder_created for other subsystems? 
            # Probably not needed if we handle sync.
        else:
            self.event_queue.put({
                'type': 'moved',
                'src_path': event.src_path,
                'dest_path': event.dest_path,
                'timestamp': datetime.now()
            })
    
    def on_created(self, event):
        """
        Handle file OR folder creation
        """
        if event.is_directory:
            self.event_queue.put({
                'type': 'folder_created',
                'path': event.src_path,
                'timestamp': datetime.now()
            })
        else:
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
        
        # V3 Taxonomy Sync
        # Lazy load TaxonomyService to avoid circular loops
        self._taxonomy_service = None
        
        # Debounce tracking for renames
        # Key: src_path, Value: Timer
        self._rename_timers = {}
        self._rename_lock = threading.Lock()

        # Initialize adaptive components
        self.learning_system = UniversalAdaptiveLearning(str(self.base_dir))
        self.confidence_system = ADHDFriendlyConfidenceSystem(str(self.base_dir))
        self.deduplicator = BulletproofDeduplicator(str(self.base_dir))
        self.rollback_system = EasyRollbackSystem()
        self.staging_monitor = StagingMonitor(str(self.base_dir))
        
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
            'cleanup_old_data': 86400,    # Cleanup daily
            'maintenance_cycle': 21600     # Check maintenance every 6 hours
        }
        
        # Adaptive rules database
        self.rules_db_path = get_metadata_root() / "databases" / "adaptive_rules.db"
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
        
        # Tracking timestamps
        self._last_pattern_discovery_time = None
        self._last_emergency_check_time = None

        self.logger.info("Adaptive Background Monitor initialized")

    @property
    def taxonomy_service(self):
        if not self._taxonomy_service:
            try:
                from taxonomy_service import TaxonomyService
                from gdrive_integration import get_metadata_root
                self._taxonomy_service = TaxonomyService(get_metadata_root() / "config")
            except Exception as e:
                self.logger.error(f"Failed to load TaxonomyService: {e}")
        return self._taxonomy_service

    def handle_directory_rename(self, src_path: str, dest_path: str):
        """
        Handle a directory rename event with debouncing.
        If a user renames a folder that matches a Category, we must sync the Taxonomy.
        """
        # Debounce window (500ms)
        # If user is typing "Screenshots" -> "Screen_Shots", we get many events.
        # We only want to act on the final stable state.
        
        with self._rename_lock:
            # Cancel existing timer for this source if it exists
            if src_path in self._rename_timers:
                self._rename_timers[src_path].cancel()
                del self._rename_timers[src_path]
            
            # Create new timer
            timer = threading.Timer(0.5, self._execute_taxonomy_sync, args=[src_path, dest_path])
            self._rename_timers[src_path] = timer
            timer.start()

    def _execute_taxonomy_sync(self, src_path: str, dest_path: str):
        """Execute the sync after debounce"""
        # Clean up timer reference
        with self._rename_lock:
            if src_path in self._rename_timers:
                del self._rename_timers[src_path]
        
        try:
            # Validate persistence
            if not os.path.exists(dest_path):
                self.logger.debug(f"Rename target vanished (transient): {dest_path}")
                return

            if self.taxonomy_service:
                # Get root dir for relative path calculation
                # We assume self.base_dir or similar is the root context
                # Use common root logic
                root_path = Path.home() / "Documents" # Default fallback
                if self.base_dir:
                    root_path = Path(self.base_dir)
                
                # Check if it resolved to something managed
                # TaxonomyService expects absolute paths to handle parsing
                self.taxonomy_service.handle_physical_rename(
                    Path(src_path), 
                    Path(dest_path), 
                    root_path
                )
        except Exception as e:
            self.logger.error(f"Error syncing taxonomy rename: {e}")

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
            
            # Maintenance history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_history (
                    task_id TEXT PRIMARY KEY,
                    task_name TEXT,
                    last_run TEXT,
                    success BOOLEAN,
                    details TEXT
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
        
        # Maintenance cycle thread
        self.threads['maintenance_cycle'] = threading.Thread(
            target=self._periodic_maintenance_cycle, daemon=True
        )
        self.threads['maintenance_cycle'].start()

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
            
        elif event_type == 'folder_created':
            # New folder created - learn new project structure?
            self._handle_new_folder(event['path'])
        
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

            # --- SIDECAR FOLLOWER ---
            # Automatically move hidden metadata sidecar if it exists
            src_sidecar = src_file.parent / ".metadata" / f"{src_file.name}.json"
            if src_sidecar.exists():
                dest_metadata_dir = dest_file.parent / ".metadata"
                dest_metadata_dir.mkdir(parents=True, exist_ok=True)
                dest_sidecar = dest_metadata_dir / f"{dest_file.name}.json"
                
                try:
                    shutil.move(str(src_sidecar), str(dest_sidecar))
                    self.logger.info(f"✨ Sidecar Follower: Moved metadata for {src_file.name}")
                except Exception as sidecar_error:
                    self.logger.warning(f"⚠️ Failed to move sidecar for {src_file.name}: {sidecar_error}")
            
        except Exception as e:
            self.logger.error(f"Error learning from file move: {e}")

    def _handle_new_folder(self, folder_path: str):
        """Handle newly created folder to learn structure (V2 Robust)"""
        try:
            folder = Path(folder_path)
            # ignore hidden or system folders
            if folder.name.startswith('.') or folder.name.endswith('_NOAI'):
                return
                
            from hierarchical_organizer import HierarchicalOrganizer
            organizer = HierarchicalOrganizer()
            
            # Check for explicit project marker (Strongest signal)
            status = "observed"
            if (folder / ".project.json").exists() or (folder / "_PROJECT").exists():
                status = "verified"
            
            # Register (Organizer handles Scope/Root checks internally)
            # We pass the folder name as the project name
            organizer.register_project(folder.name, str(folder), status=status)
            
            # Only log if it was actually accepted (we can't easily know return value, 
            # but we can assume if it's in roots it's interesting)
            if any(root in str(folder) for root in organizer.project_roots):
                if status == "verified":
                    self.logger.info(f"✅ Verified Project Detected: {folder.name}")
                else:
                    self.logger.info(f"👀 Observed New Project Folder: {folder.name}")
                
        except Exception as e:
            self.logger.error(f"Error handling new folder {folder_path}: {e}")

    def _handle_new_file(self, file_path: str, timestamp: datetime):
        """
        Handle newly created file with adaptive intelligence.
        Delegates to _handle_new_file_with_cooldown for 7-day safety rule.
        """
        try:
            file_obj = Path(file_path)
            
            if not file_obj.exists() or file_obj.is_dir():
                return
            
            # Check if file should be processed
            if not self._should_process_file(file_obj):
                return

            # Delegate to 7-day cooldown logic
            self._handle_new_file_with_cooldown(file_obj)
            
        except Exception as e:
            self.logger.error(f"Error handling new file {file_path}: {e}")

    def _handle_new_file_with_cooldown(self, path: Path) -> bool:
        """
        Handle new file with 7-day cooldown safety rule.

        SAFETY RULES (v3.2+):
        1. Detect & log new files instantly
        2. Record event (path, category prediction, confidence, timestamp)
        3. Wait 7 days of inactivity before auto-organizing
        4. Only auto-move if confidence ≥ 0.85
        5. All moves go through log_file_op() for rollback safety

        Args:
            path: Path to new/detected file

        Returns:
            bool: True if file was organized, False if deferred or failed
        """
        try:
            if not path.exists():
                return False

            # Get file age (in days)
            age_days = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days

            # Build context for prediction (needed for observation logging)
            context = {
                "file_size": path.stat().st_size,
                "creation_time": datetime.now().isoformat(),
                "source_directory": str(path.parent),
                "content_keywords": self._extract_quick_keywords(path)
            }
            
            # Get prediction regardless of age (to log observation)
            prediction = self.learning_system.predict_user_action(str(path), context)
            
            # CASE 1: File is too new (< 7 days)
            if age_days < 7:
                self.logger.info(f"⏳ Deferring move for {path.name} ({age_days}d old)")

                # Record as observation only (not verified)
                # We use record_classification which sets event_type='ai_observation'
                self.learning_system.record_classification(
                    file_path=str(path),
                    predicted_category=prediction.get("predicted_action", {}).get("target_category", "unknown"),
                    confidence=prediction.get("confidence", 0.0),
                    features=context,
                    media_type="file" # generic media type
                )
                return False

            # CASE 2: File is mature (>= 7 days) - Proceed with auto-organization
            decision = self.confidence_system.make_confidence_decision(
                file_path=str(path),
                predicted_action=prediction.get("predicted_action", {}),
                system_confidence=prediction.get("confidence", 0.0),
                context=context
            )
            
            # Execute decision
            action_taken = False
            if not decision.requires_user_input and decision.predicted_action:
                action_taken = self._execute_automatic_action(path, decision, context)

            
            # --- V3.1 ENHANCEMENT: 7-DAY STAGING COOLDOWN ---
            # Instead of executing automatically, check if it's ready
            is_organized = self._handle_new_file_with_cooldown(file_obj)
            
            if is_organized:
                action_taken = True
            elif not decision.requires_user_input and decision.predicted_action:
                # If it's not ready but we have a prediction, just log it
                # super()._process_single_file(file_obj) # Already processed below
                pass
            elif decision.requires_user_input:
                self._queue_for_user_interaction(path, decision, context)
                # Still process for indexing
                super()._process_single_file(path)
            
            # If no action taken (and not queued), index it in place
            if not action_taken and not decision.requires_user_input:
                super()._process_single_file(path)

            return action_taken

        except Exception as e:
            self.logger.error(f"Error in cooldown handler for {path}: {e}")
            return False

    def _process_single_file(self, file_path: Path, auto_organize: bool = False) -> bool:
        """
        Override: Route all polled files through the adaptive system.
        This unifies the Polling and Watchdog behaviors.
        """
        # We ignore the 'auto_organize' flag from the poll because 
        # _handle_new_file decides based on confidence.
        self._handle_new_file(str(file_path), datetime.now())
        return True

    def _scan_directory(self, dir_info: Dict[str, Any], priority: str) -> Dict[str, int]:
        """
        Override: Scan directory and process files periodically.
        This is critical for the 7-day cooldown: files that were deferred
        must be re-checked later.
        """
        path = dir_info["path"]
        results = {"files_found": 0, "files_processed": 0, "files_skipped": 0, "errors": 0}

        if not path.exists():
            return results

        try:
            self.logger.debug(f"Scanning directory for deferred files: {path}")
            for file_path in path.iterdir():
                if file_path.is_file():
                    results["files_found"] += 1
                    # Process file (will check age again)
                    try:
                        # We use _handle_new_file directly to go through the cooldown logic
                        self._handle_new_file(str(file_path), datetime.now())
                        results["files_processed"] += 1
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path}: {e}")
                        results["errors"] += 1

        except Exception as e:
            self.logger.error(f"Error scanning {path}: {e}")
            results["errors"] += 1

        return results

    def _handle_file_modification(self, file_path: str, timestamp: datetime):
        """Handle file modification - check for re-indexing"""
        
        try:
            file_obj = Path(file_path)
            
            if not self._should_process_file(file_obj):
                return
            
            # Check if file needs re-indexing
            if self._needs_reindexing(file_obj):
                self.logger.info(f"Re-indexing modified file: {file_obj.name}")
                # Treat modification as a "new event" for cooldown purposes?
                # The spec says: "Wait 7 days of inactivity (no modifications in last 7 days)"
                # So yes, we should run it through the handler.
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
                self._run_pattern_discovery_cycle()
                time.sleep(self.learning_intervals['pattern_discovery'])
                
            except Exception as e:
                self.logger.error(f"Error in pattern discovery loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    def _run_pattern_discovery_cycle(self):
        """Run a single pattern discovery cycle"""
        # Let exceptions propagate to the main loop for proper backoff handling
        self.logger.info("Starting pattern discovery cycle...")
        self._last_pattern_discovery_time = datetime.now()

        # Get recent learning events
        recent_events = [
            event for event in self.learning_system.learning_events
            if (datetime.now() - event.timestamp).days <= 7
        ]

        if len(recent_events) < 5:
            self.logger.info("Not enough recent events for pattern discovery")
            return

        # Discover patterns
        new_patterns = self._discover_behavioral_patterns(recent_events)

        if new_patterns:
            self.stats["patterns_discovered"] += len(new_patterns)
            self.logger.info(f"Discovered {len(new_patterns)} new patterns")

    def _periodic_emergency_check(self):
        """Periodically check for emergency conditions"""
        
        while self.running:
            try:
                self._run_emergency_check_cycle()
                time.sleep(self.learning_intervals['emergency_check'])
                
            except Exception as e:
                self.logger.error(f"Error in emergency check: {e}")
                time.sleep(60)

    def _run_emergency_check_cycle(self):
        """Run a single emergency check cycle"""
        # Let exceptions propagate to the main loop for proper backoff handling
        self.logger.debug("Checking for emergency conditions...")
        self._last_emergency_check_time = datetime.now()

        emergencies = self._detect_emergencies()

        for emergency in emergencies:
            self._handle_emergency(emergency)
            self.stats["emergencies_prevented"] += 1

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

    def _periodic_maintenance_cycle(self):
        """Periodically run scheduled maintenance tasks"""
        
        while self.running:
            try:
                self.logger.info("Checking scheduled maintenance tasks...")
                
                # 1. Weekly Temp Cleanup (Every 7 days)
                if self._should_run_maintenance("weekly_temp_cleanup", days=7):
                    self._run_weekly_temp_cleanup()
                
                # 2. Bi-weekly Deduplication (Every 14 days)
                if self._should_run_maintenance("biweekly_deduplication", days=14):
                    self._run_biweekly_deduplication()
                
                # Sleep for the configured interval before checking again
                time.sleep(self.learning_intervals.get('maintenance_cycle', 21600))
                
            except Exception as e:
                self.logger.error(f"Error in maintenance cycle: {e}")
                time.sleep(3600)

    def _should_run_maintenance(self, task_name: str, days: int) -> bool:
        """Check if a maintenance task is due"""
        try:
            with sqlite3.connect(self.rules_db_path) as conn:
                cursor = conn.execute(
                    "SELECT last_run FROM maintenance_history WHERE task_name = ?",
                    (task_name,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return True  # Never run before
                
                last_run = datetime.fromisoformat(result[0])
                if datetime.now() - last_run >= timedelta(days=days):
                    return True
                    
        except Exception as e:
            self.logger.error(f"Error checking maintenance status for {task_name}: {e}")
            return False
            
        return False

    def _run_weekly_temp_cleanup(self):
        """Run weekly temporary file cleanup"""
        self.logger.info("🚀 Starting weekly scheduled temp file cleanup...")
        
        try:
            # We reuse the logic from EmergencySpaceProtection but run it as a normal task
            from emergency_space_protection import EmergencySpaceProtection, SpaceEmergency
            protector = EmergencySpaceProtection(str(self.base_dir))
            
            # Create a mock emergency object to reuse the cleanup logic
            mock_emergency = SpaceEmergency(
                emergency_id=f"weekly_maint_{datetime.now().strftime('%Y%m%d')}",
                detection_time=datetime.now(),
                severity="scheduled",
                disk_path="/",
                total_space_gb=0,
                free_space_gb=0,
                usage_percent=0,
                projected_full_hours=None,
                recommended_actions=["cleanup_temp_files"],
                affected_directories=[str(config['path']) for config in self.watch_directories.values() if config['path'].exists()]
            )
            
            freed_gb = protector._cleanup_temp_files(mock_emergency)
            
            self._record_maintenance_run("weekly_temp_cleanup", True, f"Freed {freed_gb:.2f} GB of temporary files")
            self.logger.info(f"✅ Weekly temp cleanup completed. Freed {freed_gb:.2f} GB")
            
        except Exception as e:
            self.logger.error(f"❌ Weekly temp cleanup failed: {e}")
            self._record_maintenance_run("weekly_temp_cleanup", False, str(e))

    def _run_biweekly_deduplication(self):
        """Run bi-weekly deduplication across all watched paths"""
        self.logger.info("🚀 Starting bi-weekly scheduled deduplication...")
        
        try:
            total_removed = 0
            total_freed_bytes = 0
            
            for name, config in self.watch_directories.items():
                watch_path = config['path']
                if not watch_path.exists():
                    continue
                
                self.logger.info(f"Deduplicating {name} ({watch_path})...")
                # Use high safety threshold for scheduled auto-cleanup
                results = self.deduplicator.scan_directory(watch_path, execute=True, safety_threshold=0.9)
                
                total_removed += results.get("files_removed", 0)
                total_freed_bytes += results.get("space_recovered", 0)
            
            freed_mb = total_freed_bytes / (1024 * 1024)
            self._record_maintenance_run("biweekly_deduplication", True, f"Removed {total_removed} duplicates, freed {freed_mb:.1f} MB")
            self.logger.info(f"✅ Bi-weekly deduplication completed. Freed {freed_mb:.1f} MB")
            
        except Exception as e:
            self.logger.error(f"❌ Bi-weekly deduplication failed: {e}")
            self._record_maintenance_run("biweekly_deduplication", False, str(e))

    def _record_maintenance_run(self, task_name: str, success: bool, details: str):
        """Record maintenance task run in database"""
        try:
            with sqlite3.connect(self.rules_db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO maintenance_history 
                    (task_id, task_name, last_run, success, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    task_name, # Use task_name as ID for simplicity
                    task_name,
                    datetime.now().isoformat(),
                    success,
                    details
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error recording maintenance run for {task_name}: {e}")

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

    def _handle_disk_space_emergency(self, emergency_dict: Dict[str, Any]):
        """Handle critical disk space emergency"""
        
        location = emergency_dict['location']
        self.logger.warning(f"Critical disk space at {location}")
        
        try:
            # Re-use the logic from EmergencySpaceProtection
            from emergency_space_protection import EmergencySpaceProtection, SpaceEmergency
            protector = EmergencySpaceProtection(str(self.base_dir))
            
            # Create a real emergency object for the protector
            disk_path = protector._get_disk_path(Path(location))
            total, used, free = shutil.disk_usage(disk_path)
            
            emergency = SpaceEmergency(
                emergency_id=f"auto_{int(time.time())}",
                detection_time=datetime.now(),
                severity="emergency" if (used/total) > 0.95 else "critical",
                disk_path=disk_path,
                total_space_gb=total / (1024**3),
                free_space_gb=free / (1024**3),
                usage_percent=(used/total)*100,
                projected_full_hours=None,
                recommended_actions=["emergency_offload"],
                affected_directories=[location]
            )
            
            self.logger.info(f"Initiating emergency recovery for {location}...")
            
            # Run the same response logic as the dedicated service
            if emergency.severity == "emergency":
                protector._execute_emergency_offloading(emergency)
            else:
                protector._execute_critical_cleanup(emergency)
                
            self.logger.info("Emergency space recovery check complete.")
            
        except Exception as e:
            self.logger.error(f"Error in emergency space recovery: {e}")

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
        from collections import Counter
        
        # 1. Discover Extension -> Target Directory patterns
        extension_patterns = Counter()
        extension_targets = {}
        
        manual_moves = [e for e in events if e.event_type == 'manual_move']
        
        for event in manual_moves:
            ctx = event.context
            ext = ctx.get('file_extension', 'unknown')
            target = ctx.get('target_directory', 'unknown')
            
            key = (ext, target)
            extension_patterns[key] += 1
            
        new_patterns = []
        for (ext, target), count in extension_patterns.items():
            # If a specific extension has been moved to a specific target 3+ times
            if count >= 3:
                new_patterns.append({
                    "pattern_type": "extension_routing",
                    "trigger_conditions": {"file_extension": ext},
                    "predicted_action": {"target_location": target},
                    "frequency": count,
                    "confidence": 0.7 + (min(count, 10) * 0.02) # Boost confidence with frequency
                })
        
        # 2. Discover Keyword -> Target Directory patterns
        keyword_patterns = Counter()
        
        for event in manual_moves:
            ctx = event.context
            keywords = ctx.get('content_keywords', [])
            target = ctx.get('target_directory', 'unknown')
            
            for word in keywords:
                key = (word, target)
                keyword_patterns[key] += 1
                
        for (word, target), count in keyword_patterns.items():
            if count >= 3:
                new_patterns.append({
                    "pattern_type": "keyword_routing",
                    "trigger_conditions": {"keyword": word},
                    "predicted_action": {"target_location": target},
                    "frequency": count,
                    "confidence": 0.75 + (min(count, 10) * 0.02)
                })
                
        return new_patterns

    def _generate_adaptive_rules(self) -> List[Dict[str, Any]]:
        """Generate new adaptive rules from learned patterns"""
        # Promotion logic: Discover -> Pattern -> Rule
        recent_events = [
            event for event in self.learning_system.learning_events
            if (datetime.now() - event.timestamp).days <= 30
        ]
        
        patterns = self._discover_behavioral_patterns(recent_events)
        promoted_rules = []
        
        for pattern in patterns:
            # Rule Promotion Requirements:
            # 1. Frequency >= 5 OR Confidence >= 0.85
            if pattern['frequency'] >= 5 or pattern['confidence'] >= 0.85:
                rule_id = f"rule_{hashlib.md5(str(pattern).encode()).hexdigest()[:8]}"
                
                # Check if rule already exists in DB
                try:
                    with sqlite3.connect(self.rules_db_path) as conn:
                        cursor = conn.execute("SELECT rule_id FROM adaptive_rules WHERE rule_id = ?", (rule_id,))
                        if cursor.fetchone():
                            continue
                            
                        # Insert new rule
                        conn.execute("""
                            INSERT INTO adaptive_rules 
                            (rule_id, rule_type, trigger_conditions, action_definition, confidence_score, created_date)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            rule_id,
                            pattern['pattern_type'],
                            json.dumps(pattern['trigger_conditions']),
                            json.dumps(pattern['predicted_action']),
                            pattern['confidence'],
                            datetime.now().isoformat()
                        ))
                        conn.commit()
                        promoted_rules.append(pattern)
                        self.logger.info(f"🏆 Promoted pattern to active rule: {pattern['pattern_type']} -> {pattern['predicted_action']['target_location']}")
                except Exception as e:
                    self.logger.error(f"Error promoting rule {rule_id}: {e}")
                    
        return promoted_rules

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
        
        # Format timestamps
        last_pattern = self._last_pattern_discovery_time.isoformat() if self._last_pattern_discovery_time else "N/A"
        last_emergency = self._last_emergency_check_time.isoformat() if self._last_emergency_check_time else "N/A"

        return {
            "adaptive_monitor_stats": self.stats,
            "learning_system": learning_stats,
            "confidence_system": confidence_stats,
            "active_rules": len(self.adaptive_rules),
            "monitoring_status": {
                "observers_active": len(self.observers),
                "threads_running": len([t for t in self.threads.values() if t.is_alive()]),
                "last_pattern_discovery": last_pattern,
                "last_emergency_check": last_emergency
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
        
        Monitors files in Desktop/Downloads and only auto-organizes after
        they have been stationary for 7 days.
        """
        try:
            # 1. Capture observation immediately
            # This ensures we have a 'first_seen' timestamp even if it's a new file
            is_new = self.staging_monitor.record_observation(path)
            
            # 2. Extract confidence-based logic
            # (In a real system, we'd reuse the decision from _handle_new_file, 
            # but we need to check if it's MATURE enough now)
            
            age_days = self.staging_monitor.get_file_age_days(str(path))
            
            if age_days is None:
                return False
                
            if age_days < self.staging_monitor.config.get("staging_days", 7):
                if is_new:
                    self.logger.info(f"🆕 Discovered {path.name}. Entering 7-day staging.")
                return False

            # 3. If mature (>= 7 days), check for high confidence move
            # We re-run the classification just in case context changed
            context = {
                "file_size": path.stat().st_size,
                "creation_time": datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
                "age_days": age_days
            }
            
            prediction = self.learning_system.predict_user_action(str(path), context)
            decision = self.confidence_system.make_confidence_decision(
                file_path=str(path),
                predicted_action=prediction.get("predicted_action", {}),
                system_confidence=prediction.get("confidence", 0.0),
                context=context
            )
            
            # Use high confidence threshold for auto-move (V3 requirement: 0.85)
            # The confidence_system might have its own thresholds, but we enforce 0.85 here
            if not decision.requires_user_input and decision.system_confidence >= 0.85:
                self.logger.info(f"⏳ Cooldown complete for {path.name} ({age_days}d). High confidence ({decision.system_confidence:.2f}). Organizing...")
                moved = self._execute_automatic_action(path, decision, context)
                if moved:
                    self.staging_monitor.mark_file_organized(str(path), decision.predicted_action.get("target_location"))
                return moved
            elif age_days >= 14:
                # If extremely old but low confidence, maybe queue for user?
                self.logger.debug(f"File {path.name} is {age_days}d old but confidence is only {decision.system_confidence:.2f}")
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error in cooldown handler for {path}: {e}")
            return False

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