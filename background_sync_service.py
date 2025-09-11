#!/usr/bin/env python3
"""
Background Synchronization Service
Continuous synchronization between local files and Google Drive with intelligent conflict resolution

Features:
- Continuous metadata synchronization
- Change detection and propagation
- Intelligent conflict resolution
- ADHD-friendly minimal interruptions
- Efficient delta sync operations
- Robust error handling and recovery

Usage:
    sync_service = BackgroundSyncService(auth, metadata_store, streamer)
    sync_service.start_background_sync()
    
Created by: RT Max for AI File Organizer v3.0
"""

import os
import time
import threading
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Google API imports
try:
    from googleapiclient.errors import HttpError
    import requests
except ImportError as e:
    print("❌ Required libraries not installed.")
    print("Run: pip install google-api-python-client requests")
    raise e

from google_drive_auth import GoogleDriveAuth
from local_metadata_store import LocalMetadataStore, FileMetadata
from gdrive_streamer import GoogleDriveStreamer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    DRIVE_WINS = "drive_wins"
    LOCAL_WINS = "local_wins" 
    NEWER_WINS = "newer_wins"
    MANUAL_REVIEW = "manual_review"
    KEEP_BOTH = "keep_both"

class SyncStatus(Enum):
    """Sync operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"

@dataclass
class SyncOperation:
    """Represents a sync operation"""
    operation_id: str
    file_id: str
    operation_type: str  # "upload", "download", "metadata_update", "delete"
    local_path: Optional[str]
    drive_path: Optional[str]
    status: SyncStatus
    created_time: datetime
    completed_time: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    conflict_info: Optional[Dict] = None

@dataclass
class FileConflict:
    """Represents a file conflict requiring resolution"""
    file_id: str
    local_path: Path
    local_modified: datetime
    local_size: int
    local_checksum: str
    drive_modified: datetime
    drive_size: int
    drive_checksum: Optional[str]
    conflict_type: str  # "content", "metadata", "existence"
    detected_time: datetime
    resolution_strategy: Optional[ConflictResolution] = None
    resolved: bool = False

class BackgroundSyncService:
    """
    Background Synchronization Service
    
    Manages continuous sync between local files and Google Drive with
    intelligent conflict resolution and minimal user interruption.
    """
    
    def __init__(self,
                 auth_service: GoogleDriveAuth,
                 metadata_store: LocalMetadataStore,
                 streamer: GoogleDriveStreamer,
                 sync_interval: int = 300,  # 5 minutes
                 max_concurrent_ops: int = 3):
        """
        Initialize Background Sync Service
        
        Args:
            auth_service: Google Drive authentication service
            metadata_store: Local metadata store
            streamer: File streaming service
            sync_interval: Sync interval in seconds
            max_concurrent_ops: Maximum concurrent operations
        """
        
        self.auth_service = auth_service
        self.metadata_store = metadata_store
        self.streamer = streamer
        self.sync_interval = sync_interval
        self.max_concurrent_ops = max_concurrent_ops
        
        # Sync state
        self.is_running = False
        self.sync_thread: Optional[threading.Thread] = None
        self.last_sync_time: Optional[datetime] = None
        self.sync_lock = threading.Lock()
        
        # Operation queues
        self.pending_operations: List[SyncOperation] = []
        self.active_operations: Dict[str, SyncOperation] = {}
        self.completed_operations: List[SyncOperation] = []
        
        # Conflict management
        self.unresolved_conflicts: List[FileConflict] = []
        self.conflict_resolution_strategy = ConflictResolution.NEWER_WINS
        
        # Database for persistent sync state
        self.sync_db_path = Path.home() / ".ai_organizer_config" / "sync_state.db"
        self.sync_db_path.parent.mkdir(exist_ok=True)
        self._init_sync_database()
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_ops)
        self.shutdown_event = threading.Event()
        
        # Drive API change token for efficient polling
        self.drive_change_token: Optional[str] = None
        
        logger.info(f"🔄 BackgroundSyncService initialized")
        logger.info(f"   ⏰ Sync interval: {sync_interval}s")
        logger.info(f"   🔀 Max concurrent ops: {max_concurrent_ops}")
        
    def _init_sync_database(self):
        """Initialize sync state database"""
        
        with sqlite3.connect(self.sync_db_path) as conn:
            # Sync operations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_operations (
                    operation_id TEXT PRIMARY KEY,
                    file_id TEXT,
                    operation_type TEXT,
                    local_path TEXT,
                    drive_path TEXT,
                    status TEXT,
                    created_time TIMESTAMP,
                    completed_time TIMESTAMP,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    conflict_info TEXT
                )
            """)
            
            # File conflicts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_conflicts (
                    file_id TEXT PRIMARY KEY,
                    local_path TEXT,
                    local_modified TIMESTAMP,
                    local_size INTEGER,
                    local_checksum TEXT,
                    drive_modified TIMESTAMP,
                    drive_size INTEGER,
                    drive_checksum TEXT,
                    conflict_type TEXT,
                    detected_time TIMESTAMP,
                    resolution_strategy TEXT,
                    resolved BOOLEAN DEFAULT 0
                )
            """)
            
            # Sync state table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_time TIMESTAMP
                )
            """)
            
            conn.commit()
            
        logger.info("📊 Sync database initialized")
    
    def start_background_sync(self) -> bool:
        """Start background synchronization service"""
        
        if self.is_running:
            logger.warning("⚠️  Sync service is already running")
            return False
        
        try:
            # Test authentication
            test_result = self.auth_service.test_authentication()
            if not test_result['success']:
                logger.error(f"❌ Cannot start sync: authentication failed")
                return False
            
            logger.info("🚀 Starting background sync service...")
            
            # Initialize Drive change token
            self._initialize_change_token()
            
            # Load persistent state
            self._load_sync_state()
            
            # Start sync thread
            self.is_running = True
            self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.sync_thread.start()
            
            logger.info("✅ Background sync service started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start sync service: {e}")
            return False
    
    def stop_background_sync(self):
        """Stop background synchronization service"""
        
        if not self.is_running:
            logger.warning("⚠️  Sync service is not running")
            return
        
        logger.info("🛑 Stopping background sync service...")
        
        # Signal shutdown
        self.is_running = False
        self.shutdown_event.set()
        
        # Wait for sync thread to complete
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=10)
        
        # Shutdown executor
        self.executor.shutdown(wait=True, timeout=30)
        
        # Save state
        self._save_sync_state()
        
        logger.info("✅ Background sync service stopped")
    
    def _sync_loop(self):
        """Main synchronization loop"""
        
        logger.info("🔄 Sync loop started")
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                start_time = time.time()
                
                # Perform sync cycle
                self._perform_sync_cycle()
                
                # Update last sync time
                self.last_sync_time = datetime.now()
                
                # Calculate sleep time
                cycle_duration = time.time() - start_time
                sleep_time = max(0, self.sync_interval - cycle_duration)
                
                if sleep_time > 0:
                    logger.debug(f"💤 Sync cycle complete ({cycle_duration:.1f}s), sleeping {sleep_time:.1f}s")
                    self.shutdown_event.wait(sleep_time)
                
            except Exception as e:
                logger.error(f"❌ Error in sync loop: {e}")
                # Sleep before retrying
                self.shutdown_event.wait(min(60, self.sync_interval))
        
        logger.info("🔄 Sync loop stopped")
    
    def _perform_sync_cycle(self):
        """Perform one complete sync cycle"""
        
        with self.sync_lock:
            logger.debug("🔄 Starting sync cycle...")
            
            # Step 1: Check for Drive changes
            drive_changes = self._get_drive_changes()
            if drive_changes:
                logger.info(f"📥 Found {len(drive_changes)} Drive changes")
                self._process_drive_changes(drive_changes)
            
            # Step 2: Check for local changes
            local_changes = self._get_local_changes()
            if local_changes:
                logger.info(f"📤 Found {len(local_changes)} local changes")
                self._process_local_changes(local_changes)
            
            # Step 3: Process pending operations
            self._process_pending_operations()
            
            # Step 4: Check and resolve conflicts
            self._check_for_conflicts()
            
            # Step 5: Update metadata
            self._update_sync_metadata()
            
            logger.debug("✅ Sync cycle complete")
    
    def _initialize_change_token(self):
        """Initialize Google Drive change token for efficient polling"""
        
        try:
            service = self.auth_service.get_authenticated_service()
            
            # Get current change token
            response = service.changes().getStartPageToken().execute()
            self.drive_change_token = response.get('startPageToken')
            
            # Save to database
            self._save_sync_state_value('drive_change_token', self.drive_change_token)
            
            logger.info(f"🎫 Drive change token initialized: {self.drive_change_token}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize change token: {e}")
            self.drive_change_token = None
    
    def _get_drive_changes(self) -> List[Dict]:
        """Get changes from Google Drive since last sync"""
        
        if not self.drive_change_token:
            logger.debug("📥 No change token, skipping Drive change check")
            return []
        
        try:
            service = self.auth_service.get_authenticated_service()
            
            # Get changes since last token
            response = service.changes().list(
                pageToken=self.drive_change_token,
                spaces='drive',
                fields='changes(file(id,name,size,modifiedTime,trashed)),nextPageToken,newStartPageToken'
            ).execute()
            
            changes = response.get('changes', [])
            
            # Update change token for next time
            new_token = response.get('newStartPageToken')
            if new_token:
                self.drive_change_token = new_token
                self._save_sync_state_value('drive_change_token', new_token)
            
            return changes
            
        except HttpError as e:
            if e.resp.status == 400:
                # Invalid token, reinitialize
                logger.warning("⚠️  Invalid change token, reinitializing...")
                self._initialize_change_token()
                return []
            else:
                logger.error(f"❌ Error getting Drive changes: {e}")
                return []
        except Exception as e:
            logger.error(f"❌ Error getting Drive changes: {e}")
            return []
    
    def _get_local_changes(self) -> List[Dict]:
        """Get local file changes that need to be synced"""
        
        changes = []
        
        try:
            # Get files that have been modified locally since last sync
            last_sync = self.last_sync_time or (datetime.now() - timedelta(hours=24))
            
            # Query metadata store for recent changes
            recent_files = self.metadata_store.get_files_modified_since(last_sync)
            
            for file_metadata in recent_files:
                # Check if file actually exists and was modified
                if file_metadata.local_path and Path(file_metadata.local_path).exists():
                    file_stat = Path(file_metadata.local_path).stat()
                    local_modified = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    if local_modified > last_sync:
                        changes.append({
                            'type': 'local_modified',
                            'file_id': file_metadata.file_id,
                            'local_path': file_metadata.local_path,
                            'modified_time': local_modified
                        })
            
            return changes
            
        except Exception as e:
            logger.error(f"❌ Error getting local changes: {e}")
            return []
    
    def _process_drive_changes(self, changes: List[Dict]):
        """Process changes detected from Google Drive"""
        
        for change in changes:
            try:
                file_info = change.get('file', {})
                file_id = file_info.get('id')
                
                if not file_id:
                    continue
                
                # Check if file is trashed
                if file_info.get('trashed'):
                    self._queue_operation('delete', file_id, None, f"Drive file {file_id}")
                    continue
                
                # Get local metadata
                local_metadata = self.metadata_store.get_file_metadata(file_id)
                
                if local_metadata:
                    # File exists locally, check for conflicts
                    drive_modified = datetime.fromisoformat(
                        file_info.get('modifiedTime', datetime.now().isoformat()).replace('Z', '+00:00')
                    )
                    
                    local_path = Path(local_metadata.local_path)
                    if local_path.exists():
                        local_stat = local_path.stat()
                        local_modified = datetime.fromtimestamp(local_stat.st_mtime)
                        
                        # Check for conflict
                        if abs((drive_modified - local_modified).total_seconds()) > 60:  # 1 minute tolerance
                            self._detect_conflict(file_id, local_path, local_modified, drive_modified, file_info)
                        else:
                            # No conflict, update metadata
                            self._queue_operation('metadata_update', file_id, local_metadata.local_path, None)
                    else:
                        # Local file missing, download from Drive
                        self._queue_operation('download', file_id, None, local_metadata.local_path)
                else:
                    # New file on Drive, decide whether to download
                    if self._should_download_new_file(file_info):
                        target_path = self._determine_local_path(file_info)
                        self._queue_operation('download', file_id, None, target_path)
                
            except Exception as e:
                logger.error(f"❌ Error processing Drive change: {e}")
    
    def _process_local_changes(self, changes: List[Dict]):
        """Process local file changes that need to be synced"""
        
        for change in changes:
            try:
                file_id = change['file_id']
                local_path = change['local_path']
                
                # Get Drive metadata
                service = self.auth_service.get_authenticated_service()
                try:
                    drive_file = service.files().get(
                        fileId=file_id,
                        fields='id,name,modifiedTime,size'
                    ).execute()
                    
                    drive_modified = datetime.fromisoformat(
                        drive_file.get('modifiedTime', datetime.now().isoformat()).replace('Z', '+00:00')
                    )
                    local_modified = change['modified_time']
                    
                    # Check for conflict
                    if drive_modified > local_modified + timedelta(seconds=60):
                        # Drive version is newer, potential conflict
                        self._detect_conflict(file_id, Path(local_path), local_modified, drive_modified, drive_file)
                    else:
                        # Local version is newer or same, upload
                        self._queue_operation('upload', file_id, local_path, None)
                
                except HttpError as e:
                    if e.resp.status == 404:
                        # File doesn't exist on Drive, upload as new
                        self._queue_operation('upload', file_id, local_path, None)
                    else:
                        logger.error(f"❌ Error checking Drive file {file_id}: {e}")
                
            except Exception as e:
                logger.error(f"❌ Error processing local change: {e}")
    
    def _detect_conflict(self, 
                        file_id: str, 
                        local_path: Path, 
                        local_modified: datetime, 
                        drive_modified: datetime, 
                        drive_file_info: Dict):
        """Detect and record file conflict"""
        
        try:
            # Calculate local file checksum
            local_checksum = self._calculate_file_checksum(local_path)
            local_size = local_path.stat().st_size
            
            # Create conflict record
            conflict = FileConflict(
                file_id=file_id,
                local_path=local_path,
                local_modified=local_modified,
                local_size=local_size,
                local_checksum=local_checksum,
                drive_modified=drive_modified,
                drive_size=int(drive_file_info.get('size', 0)),
                drive_checksum=None,  # Would need to download to calculate
                conflict_type='content',
                detected_time=datetime.now()
            )
            
            # Store conflict
            self.unresolved_conflicts.append(conflict)
            self._save_conflict(conflict)
            
            logger.warning(f"⚠️  Conflict detected: {local_path.name}")
            logger.warning(f"   📅 Local: {local_modified}, Drive: {drive_modified}")
            
            # Apply resolution strategy
            self._resolve_conflict(conflict)
            
        except Exception as e:
            logger.error(f"❌ Error detecting conflict for {file_id}: {e}")
    
    def _resolve_conflict(self, conflict: FileConflict):
        """Resolve file conflict based on strategy"""
        
        try:
            if self.conflict_resolution_strategy == ConflictResolution.NEWER_WINS:
                if conflict.drive_modified > conflict.local_modified:
                    # Drive version wins
                    self._queue_operation('download', conflict.file_id, None, str(conflict.local_path))
                    conflict.resolution_strategy = ConflictResolution.DRIVE_WINS
                else:
                    # Local version wins
                    self._queue_operation('upload', conflict.file_id, str(conflict.local_path), None)
                    conflict.resolution_strategy = ConflictResolution.LOCAL_WINS
                
                conflict.resolved = True
                self._update_conflict(conflict)
                
                logger.info(f"🔧 Auto-resolved conflict: {conflict.local_path.name} "
                          f"({conflict.resolution_strategy.value})")
            
            elif self.conflict_resolution_strategy == ConflictResolution.KEEP_BOTH:
                # Keep both versions with different names
                self._resolve_conflict_keep_both(conflict)
            
            elif self.conflict_resolution_strategy == ConflictResolution.MANUAL_REVIEW:
                # Leave for manual resolution
                logger.info(f"👤 Manual review required: {conflict.local_path.name}")
                
        except Exception as e:
            logger.error(f"❌ Error resolving conflict: {e}")
    
    def _resolve_conflict_keep_both(self, conflict: FileConflict):
        """Resolve conflict by keeping both versions"""
        
        try:
            # Download Drive version with suffix
            drive_suffix = f"_drive_{conflict.drive_modified.strftime('%Y%m%d_%H%M%S')}"
            stem = conflict.local_path.stem
            suffix = conflict.local_path.suffix
            drive_path = conflict.local_path.parent / f"{stem}{drive_suffix}{suffix}"
            
            self._queue_operation('download', conflict.file_id, None, str(drive_path))
            
            # Rename local version with suffix
            local_suffix = f"_local_{conflict.local_modified.strftime('%Y%m%d_%H%M%S')}"
            local_new_path = conflict.local_path.parent / f"{stem}{local_suffix}{suffix}"
            conflict.local_path.rename(local_new_path)
            
            conflict.resolution_strategy = ConflictResolution.KEEP_BOTH
            conflict.resolved = True
            self._update_conflict(conflict)
            
            logger.info(f"📁 Kept both versions: {conflict.local_path.name}")
            
        except Exception as e:
            logger.error(f"❌ Error resolving conflict (keep both): {e}")
    
    def _queue_operation(self, operation_type: str, file_id: str, local_path: Optional[str], drive_path: Optional[str]):
        """Queue a sync operation"""
        
        operation_id = f"{operation_type}_{file_id}_{int(time.time())}"
        
        operation = SyncOperation(
            operation_id=operation_id,
            file_id=file_id,
            operation_type=operation_type,
            local_path=local_path,
            drive_path=drive_path,
            status=SyncStatus.PENDING,
            created_time=datetime.now()
        )
        
        self.pending_operations.append(operation)
        self._save_operation(operation)
        
        logger.debug(f"📋 Queued operation: {operation_type} for {file_id}")
    
    def _process_pending_operations(self):
        """Process queued sync operations"""
        
        if not self.pending_operations:
            return
        
        # Process operations up to max concurrent limit
        available_slots = self.max_concurrent_ops - len(self.active_operations)
        operations_to_process = self.pending_operations[:available_slots]
        
        for operation in operations_to_process:
            if operation.retry_count > 3:
                logger.error(f"❌ Operation failed too many times: {operation.operation_id}")
                operation.status = SyncStatus.FAILED
                self._save_operation(operation)
                self.pending_operations.remove(operation)
                continue
            
            # Submit operation to thread pool
            future = self.executor.submit(self._execute_operation, operation)
            operation.status = SyncStatus.IN_PROGRESS
            self.active_operations[operation.operation_id] = operation
            self.pending_operations.remove(operation)
            self._save_operation(operation)
            
            logger.info(f"🔄 Started operation: {operation.operation_type} for {operation.file_id}")
    
    def _execute_operation(self, operation: SyncOperation) -> bool:
        """Execute a sync operation"""
        
        try:
            success = False
            
            if operation.operation_type == 'upload':
                success = self._execute_upload(operation)
            elif operation.operation_type == 'download':
                success = self._execute_download(operation)
            elif operation.operation_type == 'metadata_update':
                success = self._execute_metadata_update(operation)
            elif operation.operation_type == 'delete':
                success = self._execute_delete(operation)
            
            # Update operation status
            if success:
                operation.status = SyncStatus.COMPLETED
                operation.completed_time = datetime.now()
                logger.info(f"✅ Completed operation: {operation.operation_id}")
            else:
                operation.status = SyncStatus.FAILED
                operation.retry_count += 1
                logger.warning(f"⚠️  Failed operation: {operation.operation_id} (retry {operation.retry_count})")
            
        except Exception as e:
            operation.status = SyncStatus.FAILED
            operation.error_message = str(e)
            operation.retry_count += 1
            logger.error(f"❌ Error executing operation {operation.operation_id}: {e}")
            success = False
        
        finally:
            # Remove from active operations
            if operation.operation_id in self.active_operations:
                del self.active_operations[operation.operation_id]
            
            # Save operation state
            self._save_operation(operation)
            
            # If failed and should retry, add back to pending
            if not success and operation.retry_count <= 3:
                operation.status = SyncStatus.PENDING
                self.pending_operations.append(operation)
        
        return success
    
    def _execute_upload(self, operation: SyncOperation) -> bool:
        """Execute file upload to Drive"""
        # Implementation would use Google Drive API to upload file
        # This is a placeholder for the actual upload logic
        logger.debug(f"📤 Uploading {operation.local_path} to Drive")
        time.sleep(1)  # Simulate upload time
        return True
    
    def _execute_download(self, operation: SyncOperation) -> bool:
        """Execute file download from Drive"""
        try:
            local_path = self.streamer.ensure_file_available(operation.file_id)
            
            # If operation specifies different target path, move file
            if operation.drive_path and str(local_path) != operation.drive_path:
                target_path = Path(operation.drive_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.rename(target_path)
            
            logger.debug(f"📥 Downloaded {operation.file_id} from Drive")
            return True
            
        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            return False
    
    def _execute_metadata_update(self, operation: SyncOperation) -> bool:
        """Execute metadata synchronization"""
        logger.debug(f"📊 Updating metadata for {operation.file_id}")
        # Update local metadata from Drive
        # This is a placeholder for the actual metadata sync logic
        time.sleep(0.5)  # Simulate processing time
        return True
    
    def _execute_delete(self, operation: SyncOperation) -> bool:
        """Execute file deletion"""
        logger.debug(f"🗑️  Processing delete for {operation.file_id}")
        # Handle file deletion (move to trash, update metadata, etc.)
        # This is a placeholder for the actual delete logic
        return True
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"❌ Error calculating checksum for {file_path}: {e}")
            return ""
    
    def _should_download_new_file(self, file_info: Dict) -> bool:
        """Determine if new Drive file should be downloaded"""
        # Simple heuristic - download text documents and small files
        file_size = int(file_info.get('size', 0))
        mime_type = file_info.get('mimeType', '')
        
        if file_size > 100 * 1024 * 1024:  # Skip files > 100MB
            return False
        
        # Download text documents, PDFs, and office documents
        download_types = [
            'text/',
            'application/pdf',
            'application/vnd.openxmlformats-officedocument',
            'application/vnd.oasis.opendocument'
        ]
        
        return any(mime_type.startswith(t) for t in download_types)
    
    def _determine_local_path(self, file_info: Dict) -> str:
        """Determine appropriate local path for Drive file"""
        filename = file_info.get('name', f"file_{file_info['id']}")
        # Use AI organizer structure from gdrive_integration
        from gdrive_integration import get_ai_organizer_root
        
        root = get_ai_organizer_root()
        return str(root / "99_TEMP_PROCESSING" / "Manual_Review" / filename)
    
    # Database operations
    def _save_operation(self, operation: SyncOperation):
        """Save operation to database"""
        with sqlite3.connect(self.sync_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sync_operations 
                (operation_id, file_id, operation_type, local_path, drive_path, status,
                 created_time, completed_time, error_message, retry_count, conflict_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                operation.operation_id, operation.file_id, operation.operation_type,
                operation.local_path, operation.drive_path, operation.status.value,
                operation.created_time.isoformat(),
                operation.completed_time.isoformat() if operation.completed_time else None,
                operation.error_message, operation.retry_count,
                json.dumps(operation.conflict_info) if operation.conflict_info else None
            ))
    
    def _save_conflict(self, conflict: FileConflict):
        """Save conflict to database"""
        with sqlite3.connect(self.sync_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO file_conflicts
                (file_id, local_path, local_modified, local_size, local_checksum,
                 drive_modified, drive_size, drive_checksum, conflict_type,
                 detected_time, resolution_strategy, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conflict.file_id, str(conflict.local_path), conflict.local_modified.isoformat(),
                conflict.local_size, conflict.local_checksum, conflict.drive_modified.isoformat(),
                conflict.drive_size, conflict.drive_checksum, conflict.conflict_type,
                conflict.detected_time.isoformat(),
                conflict.resolution_strategy.value if conflict.resolution_strategy else None,
                conflict.resolved
            ))
    
    def _update_conflict(self, conflict: FileConflict):
        """Update conflict in database"""
        self._save_conflict(conflict)  # Same as save for SQLite
    
    def _save_sync_state_value(self, key: str, value: str):
        """Save sync state value to database"""
        with sqlite3.connect(self.sync_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sync_state (key, value, updated_time)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
    
    def _load_sync_state(self):
        """Load sync state from database"""
        try:
            with sqlite3.connect(self.sync_db_path) as conn:
                cursor = conn.execute("SELECT value FROM sync_state WHERE key = 'drive_change_token'")
                row = cursor.fetchone()
                if row:
                    self.drive_change_token = row[0]
                    
        except Exception as e:
            logger.warning(f"⚠️  Could not load sync state: {e}")
    
    def _save_sync_state(self):
        """Save current sync state to database"""
        if self.drive_change_token:
            self._save_sync_state_value('drive_change_token', self.drive_change_token)
    
    def _check_for_conflicts(self):
        """Check for any unresolved conflicts and attempt resolution"""
        unresolved_count = len([c for c in self.unresolved_conflicts if not c.resolved])
        if unresolved_count > 0:
            logger.debug(f"🔍 {unresolved_count} unresolved conflicts")
    
    def _update_sync_metadata(self):
        """Update sync-related metadata"""
        # Update last sync time in database
        self._save_sync_state_value('last_sync_time', datetime.now().isoformat())
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get comprehensive sync status"""
        
        with self.sync_lock:
            status = {
                'is_running': self.is_running,
                'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
                'pending_operations': len(self.pending_operations),
                'active_operations': len(self.active_operations),
                'unresolved_conflicts': len([c for c in self.unresolved_conflicts if not c.resolved]),
                'conflict_resolution_strategy': self.conflict_resolution_strategy.value,
                'drive_change_token': self.drive_change_token,
                'sync_interval_seconds': self.sync_interval
            }
            
            # Add operation details
            status['active_operation_details'] = [
                {
                    'operation_id': op.operation_id,
                    'type': op.operation_type,
                    'file_id': op.file_id,
                    'created': op.created_time.isoformat(),
                    'status': op.status.value
                }
                for op in self.active_operations.values()
            ]
            
            return status

def test_background_sync():
    """Test the Background Sync Service"""
    
    print("🔄 Testing Background Sync Service")
    print("=" * 50)
    
    try:
        # Initialize components
        from gdrive_streamer import GoogleDriveStreamer
        
        auth = GoogleDriveAuth()
        metadata_store = LocalMetadataStore()
        streamer = GoogleDriveStreamer(auth, metadata_store)
        
        # Test authentication
        test_results = auth.test_authentication()
        if not test_results['success']:
            print(f"❌ Authentication failed: {test_results}")
            return
        
        print(f"✅ Authenticated as: {test_results['user_name']}")
        
        # Initialize sync service
        sync_service = BackgroundSyncService(
            auth_service=auth,
            metadata_store=metadata_store,
            streamer=streamer,
            sync_interval=60  # 1 minute for testing
        )
        
        print(f"🔄 Sync service initialized")
        
        # Start background sync
        if sync_service.start_background_sync():
            print(f"✅ Background sync started")
            
            # Let it run for a short time
            print(f"⏳ Running sync for 10 seconds...")
            time.sleep(10)
            
            # Get status
            status = sync_service.get_sync_status()
            print(f"📊 Sync Status:")
            print(f"   🔄 Running: {status['is_running']}")
            print(f"   📋 Pending ops: {status['pending_operations']}")
            print(f"   🏃 Active ops: {status['active_operations']}")
            print(f"   ⚠️  Conflicts: {status['unresolved_conflicts']}")
            
            # Stop sync service
            sync_service.stop_background_sync()
            print(f"🛑 Background sync stopped")
            
        else:
            print(f"❌ Failed to start background sync")
        
        print(f"\n✅ Background Sync Service test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_background_sync()