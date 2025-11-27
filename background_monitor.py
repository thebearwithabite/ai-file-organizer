#!/usr/bin/env python3
"""
Enhanced Background Monitor for AI File Organizer
Keeps vector database automatically up to date with multi-directory monitoring
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json
import logging
from typing import Dict, List, Set
import hashlib

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from vector_librarian import VectorLibrarian
from email_extractor import EmailExtractor
from content_extractor import ContentExtractor
from gdrive_integration import get_ai_organizer_root, get_metadata_root

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(Path(__file__).parent / 'logs' / 'monitor.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EnhancedBackgroundMonitor:
    """
    Comprehensive file monitoring and auto-indexing system
    Based on AudioAI organizer patterns but adapted for document management
    """
    
    def __init__(self, base_dir: str = None, additional_watch_paths: List[str] = None):
        self.base_dir = Path(base_dir) if base_dir else get_metadata_root()
        self.db_path = self.base_dir / "background_monitor.db"
        
        # Initialize components
        self.vector_librarian = VectorLibrarian()
        self.email_extractor = EmailExtractor()
        self.content_extractor = ContentExtractor(str(self.base_dir))
        
        # Monitoring configuration
        self.watch_directories = self._get_watch_directories()
        
        # Add additional paths
        if additional_watch_paths:
            for path_str in additional_watch_paths:
                path = Path(path_str).expanduser()
                if path.exists():
                    name = path.name.lower().replace(' ', '_')
                    self.watch_directories[name] = {
                        'path': path,
                        'priority': 'medium',
                        'auto_organize': False
                    }
                    logger.info(f"Added custom watch path: {path}")
        self.supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.pages', '.rtf'}
        self.email_extensions = {'.emlx'}
        
        # Update intervals (in seconds)
        self.intervals = {
            'real_time': 30,      # Check staging every 30 seconds
            'email_sync': 300,    # Check emails every 5 minutes
            'directory_scan': 3600,  # Full scan every hour
            'learning_update': 600,  # Update learning every 10 minutes
            'full_reindex': 86400    # Complete reindex daily
        }
        
        # Tracking
        self.processed_files = set()
        self.last_scan_times = {}
        self.running = False
        self.threads = {}
        
        # Initialize database
        self._init_database()
        self._load_processed_files()
    
    def _get_watch_directories(self) -> Dict[str, Dict]:
        """Get directories to monitor with different priorities"""
        return {
            # High priority - check frequently
            'staging': {
                'path': get_ai_organizer_root() / "TEMP_PROCESSING" / "Downloads_Staging",
                'priority': 'high',
                'auto_organize': True
            },
            'downloads': {
                'path': Path.home() / "Downloads",
                'priority': 'high',
                'auto_organize': False,  # Just index, don't move
                'wait_days': 7  # Wait 7 days before processing (ADHD-friendly)
            },
            'desktop': {
                'path': Path.home() / "Desktop",
                'priority': 'medium',
                'auto_organize': False,
                'wait_days': 7  # Wait 7 days before processing (ADHD-friendly)
            },
            
            # Medium priority - check hourly
            'documents': {
                'path': get_ai_organizer_root(),
                'priority': 'medium',
                'auto_organize': False
            },
            'icloud_documents': {
                'path': Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Documents",
                'priority': 'medium',
                'auto_organize': False
            },
            
            # Low priority - check daily
            'active_projects': {
                'path': self.base_dir / "01_ACTIVE_PROJECTS",
                'priority': 'low',
                'auto_organize': False
            },
            
            # Email monitoring
            'mail': {
                'path': Path.home() / "Library" / "Mail",
                'priority': 'email',
                'auto_organize': False
            }
        }
    
    def _init_database(self):
        """Initialize SQLite database for tracking"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT,
                    last_modified REAL,
                    last_indexed REAL,
                    file_size INTEGER,
                    content_type TEXT,
                    index_success BOOLEAN,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    directory_path TEXT,
                    scan_type TEXT,
                    start_time REAL,
                    end_time REAL,
                    files_found INTEGER,
                    files_processed INTEGER,
                    files_skipped INTEGER,
                    errors INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_updates (
                    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_time REAL,
                    update_type TEXT,
                    details TEXT,
                    success BOOLEAN
                )
            """)
            
            conn.commit()
    
    def _load_processed_files(self):
        """Load previously processed files from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT file_path FROM processed_files WHERE index_success = 1")
                self.processed_files = set(row[0] for row in cursor.fetchall())
            
            logger.info(f"Loaded {len(self.processed_files)} previously processed files")
            
        except Exception as e:
            logger.error(f"Error loading processed files: {e}")
            self.processed_files = set()
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash of file content for change detection"""
        try:
            with open(file_path, 'rb') as f:
                # Read first and last 1KB for efficiency
                start = f.read(1024)
                f.seek(-min(1024, file_path.stat().st_size), 2)
                end = f.read(1024)
                
            stat = file_path.stat()
            content = start + end + str(stat.st_size).encode() + str(stat.st_mtime).encode()
            return hashlib.md5(content).hexdigest()
            
        except Exception:
            # Fallback to simple stat-based hash
            stat = file_path.stat()
            return hashlib.md5(f"{stat.st_size}_{stat.st_mtime}".encode()).hexdigest()
    
    def _should_process_file(self, file_path: Path, directory_name: str = None) -> bool:
        """Determine if file needs processing"""
        
        if not file_path.exists() or file_path.is_dir():
            return False
        
        # Check extension
        if file_path.suffix.lower() not in (self.supported_extensions | self.email_extensions):
            return False
        
        # Skip hidden files and system files
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            return False
        
        # IMPORTANT: 7-day waiting period for Downloads and Desktop ONLY
        # Don't process files less than 7 days old to avoid interfering with active work
        # EXCEPTION: 99_STAGING_EMERGENCY bypasses this rule - files there are processed immediately
        if directory_name in ['downloads', 'desktop']:
            try:
                file_age_days = (time.time() - file_path.stat().st_mtime) / 86400  # Convert to days
                if file_age_days < 7:
                    return False  # Skip files newer than 7 days
            except:
                return False  # Skip if we can't determine age

        # Emergency staging folder: process immediately regardless of age
        # Files here were deliberately moved during emergencies and need immediate processing
        
        # Check if already processed and unchanged
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT file_hash, last_modified, index_success 
                    FROM processed_files 
                    WHERE file_path = ?
                """, (str(file_path),))
                
                result = cursor.fetchone()
                
                if result:
                    stored_hash, last_modified, was_successful = result
                    current_hash = self._get_file_hash(file_path)
                    
                    # If hash unchanged and was successful, skip
                    if stored_hash == current_hash and was_successful:
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking file status: {e}")
            return True  # Process if unsure
    
    def _record_file_processing(self, file_path: Path, success: bool, error_msg: str = None):
        """Record file processing results in database"""
        
        try:
            file_hash = self._get_file_hash(file_path)
            stat = file_path.stat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO processed_files 
                    (file_path, file_hash, last_modified, last_indexed, file_size, 
                     content_type, index_success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(file_path), file_hash, stat.st_mtime, time.time(),
                    stat.st_size, file_path.suffix, success, error_msg
                ))
                conn.commit()
            
            if success:
                self.processed_files.add(str(file_path))
                
        except Exception as e:
            logger.error(f"Error recording file processing: {e}")
    
    def _process_single_file(self, file_path: Path, auto_organize: bool = False) -> bool:
        """Process a single file for indexing"""
        
        try:
            logger.info(f"Processing: {file_path.name}")
            
            if file_path.suffix.lower() in self.email_extensions:
                # Process email
                email_result = self.email_extractor.extract_email_content(file_path)
                if email_result['success']:
                    # Index email content
                    success = self.vector_librarian.index_email(file_path, email_result)
                else:
                    logger.warning(f"Email extraction failed: {email_result.get('error')}")
                    success = False
            
            else:
                # Process document
                extraction_result = self.content_extractor.extract_content(file_path)
                
                if extraction_result['success']:
                    # Index document content
                    success = self.vector_librarian.index_document(
                        file_path, 
                        extraction_result['text']
                    )
                    
                    # Optionally organize the file
                    if auto_organize and success:
                        # TODO: Integrate with classification system
                        logger.info(f"Auto-organization enabled for {file_path.name}")
                        
                else:
                    logger.warning(f"Content extraction failed: {extraction_result.get('error')}")
                    success = False
            
            self._record_file_processing(file_path, success)
            return success
            
        except Exception as e:
            error_msg = f"Error processing {file_path.name}: {e}"
            logger.error(error_msg)
            self._record_file_processing(file_path, False, str(e))
            return False
    
    def _scan_directory(self, directory_info: Dict, scan_type: str = "regular") -> Dict:
        """Scan a directory for new or changed files"""
        
        directory_path = directory_info['path']
        priority = directory_info['priority']
        auto_organize = directory_info.get('auto_organize', False)
        
        scan_start = time.time()
        stats = {
            'files_found': 0,
            'files_processed': 0,
            'files_skipped': 0,
            'errors': 0
        }
        
        if not directory_path.exists():
            logger.warning(f"Directory not found: {directory_path}")
            return stats
        
        logger.info(f"Scanning {directory_path} ({priority} priority, {scan_type})")
        
        try:
            # Find relevant files
            files_to_check = []
            
            if priority == 'email':
                # Special handling for email directories
                for email_file in directory_path.rglob("*.emlx"):
                    if self._should_process_file(email_file, 'email'):
                        files_to_check.append(email_file)
            else:
                # Regular document scanning
                # Get directory name for 7-day rule checking
                dir_name = None
                for name, info in self.watch_directories.items():
                    if info['path'] == directory_path:
                        dir_name = name
                        break
                
                for ext in self.supported_extensions:
                    for file_path in directory_path.rglob(f"*{ext}"):
                        if self._should_process_file(file_path, dir_name):
                            files_to_check.append(file_path)
            
            stats['files_found'] = len(files_to_check)
            
            # Process files
            for file_path in files_to_check:
                if not self.running:
                    break
                
                try:
                    success = self._process_single_file(file_path, auto_organize)
                    if success:
                        stats['files_processed'] += 1
                    else:
                        stats['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    stats['errors'] += 1
            
            stats['files_skipped'] = stats['files_found'] - stats['files_processed'] - stats['errors']
            
            # Record scan history
            scan_end = time.time()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO scan_history 
                    (directory_path, scan_type, start_time, end_time, 
                     files_found, files_processed, files_skipped, errors)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(directory_path), scan_type, scan_start, scan_end,
                    stats['files_found'], stats['files_processed'], 
                    stats['files_skipped'], stats['errors']
                ))
                conn.commit()
            
            logger.info(f"Scan complete: {stats['files_processed']} processed, {stats['errors']} errors")
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory_path}: {e}")
            stats['errors'] += 1
        
        return stats
    
    def _real_time_monitor(self):
        """Monitor high-priority directories in real-time"""
        logger.info("Starting real-time monitoring")
        
        while self.running:
            try:
                # Check high-priority directories
                for name, dir_info in self.watch_directories.items():
                    if not self.running:
                        break
                        
                    if dir_info['priority'] == 'high':
                        stats = self._scan_directory(dir_info, "real-time")
                        if stats['files_processed'] > 0:
                            logger.info(f"Real-time: Processed {stats['files_processed']} files in {name}")
                
                time.sleep(self.intervals['real_time'])
                
            except Exception as e:
                logger.error(f"Error in real-time monitoring: {e}")
                time.sleep(self.intervals['real_time'])
    
    def _email_sync_monitor(self):
        """Monitor email directories for new messages"""
        logger.info("Starting email sync monitoring")
        
        while self.running:
            try:
                # Check email directories
                for name, dir_info in self.watch_directories.items():
                    if not self.running:
                        break
                        
                    if dir_info['priority'] == 'email':
                        stats = self._scan_directory(dir_info, "email-sync")
                        if stats['files_processed'] > 0:
                            logger.info(f"Email sync: Processed {stats['files_processed']} emails")
                
                time.sleep(self.intervals['email_sync'])
                
            except Exception as e:
                logger.error(f"Error in email sync: {e}")
                time.sleep(self.intervals['email_sync'])
    
    def _directory_scan_monitor(self):
        """Periodic full directory scans"""
        logger.info("Starting periodic directory scanning")
        
        while self.running:
            try:
                # Check medium priority directories
                for name, dir_info in self.watch_directories.items():
                    if not self.running:
                        break
                        
                    if dir_info['priority'] == 'medium':
                        stats = self._scan_directory(dir_info, "periodic")
                        if stats['files_processed'] > 0:
                            logger.info(f"Periodic scan: Processed {stats['files_processed']} files in {name}")
                
                time.sleep(self.intervals['directory_scan'])
                
            except Exception as e:
                logger.error(f"Error in periodic scanning: {e}")
                time.sleep(self.intervals['directory_scan'])
    
    def _learning_update_monitor(self):
        """Update learning patterns based on user interactions"""
        logger.info("Starting learning update monitoring")
        
        while self.running:
            try:
                # Check for learning updates needed
                # This would integrate with the classification system
                # to update vector database based on user corrections
                
                update_time = time.time()
                
                # Record learning update
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO learning_updates (update_time, update_type, details, success)
                        VALUES (?, ?, ?, ?)
                    """, (update_time, "periodic_check", "Learning patterns reviewed", True))
                    conn.commit()
                
                time.sleep(self.intervals['learning_update'])
                
            except Exception as e:
                logger.error(f"Error in learning updates: {e}")
                time.sleep(self.intervals['learning_update'])
    
    def _full_reindex_monitor(self):
        """Complete reindexing of all directories"""
        logger.info("Starting daily reindexing monitor")
        
        while self.running:
            try:
                logger.info("Starting full reindex...")
                
                # Full scan of all directories
                total_processed = 0
                for name, dir_info in self.watch_directories.items():
                    if not self.running:
                        break
                        
                    logger.info(f"Full reindex: {name}")
                    stats = self._scan_directory(dir_info, "full-reindex")
                    total_processed += stats['files_processed']
                
                logger.info(f"Full reindex complete: {total_processed} files processed")
                
                time.sleep(self.intervals['full_reindex'])
                
            except Exception as e:
                logger.error(f"Error in full reindex: {e}")
                time.sleep(self.intervals['full_reindex'])
    
    def start(self, threads_to_run: List[str] = None):
        """Start the background monitoring system"""
        
        if threads_to_run is None:
            threads_to_run = ['real_time', 'email_sync', 'directory_scan', 'learning_update', 'full_reindex']
        
        logger.info("Starting Enhanced Background Monitor")
        logger.info(f"Monitoring {len(self.watch_directories)} directories")
        logger.info(f"Database: {self.db_path}")
        
        self.running = True
        
        # Start monitoring threads
        thread_functions = {
            'real_time': self._real_time_monitor,
            'email_sync': self._email_sync_monitor,
            'directory_scan': self._directory_scan_monitor,
            'learning_update': self._learning_update_monitor,
            'full_reindex': self._full_reindex_monitor
        }
        
        for thread_name in threads_to_run:
            if thread_name in thread_functions:
                thread = threading.Thread(
                    target=thread_functions[thread_name],
                    name=f"Monitor-{thread_name}",
                    daemon=True
                )
                thread.start()
                self.threads[thread_name] = thread
                logger.info(f"Started {thread_name} monitoring thread")
        
        logger.info("All monitoring threads started")
    
    def stop(self):
        """Stop the background monitoring system"""
        logger.info("Stopping Enhanced Background Monitor")
        
        self.running = False
        
        # Wait for threads to finish
        for thread_name, thread in self.threads.items():
            logger.info(f"Stopping {thread_name} thread...")
            thread.join(timeout=5)
        
        logger.info("Background Monitor stopped")
    
    def status(self) -> Dict:
        """Get current status of the monitoring system"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get recent scan stats
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_scans,
                           SUM(files_processed) as total_processed,
                           SUM(errors) as total_errors,
                           MAX(end_time) as last_scan
                    FROM scan_history 
                    WHERE start_time > ?
                """, (time.time() - 86400,))  # Last 24 hours
                
                scan_stats = cursor.fetchone()
                
                # Get processed files count
                cursor = conn.execute("SELECT COUNT(*) FROM processed_files WHERE index_success = 1")
                processed_count = cursor.fetchone()[0]
                
                # Get error count
                cursor = conn.execute("SELECT COUNT(*) FROM processed_files WHERE index_success = 0")
                error_count = cursor.fetchone()[0]
            
            return {
                'running': self.running,
                'active_threads': len([t for t in self.threads.values() if t.is_alive()]),
                'watch_directories': len(self.watch_directories),
                'processed_files': processed_count,
                'error_files': error_count,
                'scans_24h': scan_stats[0] if scan_stats[0] else 0,
                'files_processed_24h': scan_stats[1] if scan_stats[1] else 0,
                'errors_24h': scan_stats[2] if scan_stats[2] else 0,
                'last_scan': datetime.fromtimestamp(scan_stats[3]) if scan_stats[3] else None
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {'error': str(e)}

def main():
    """Command line interface for the background monitor"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Background Monitor for AI File Organizer")
    parser.add_argument('command', choices=['start', 'stop', 'status', 'scan'], 
                       help='Command to execute')
    parser.add_argument('--threads', nargs='*', 
                       choices=['real_time', 'email_sync', 'directory_scan', 'learning_update', 'full_reindex'],
                       help='Specific threads to run')
    parser.add_argument('--directory', help='Specific directory to scan')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon process')
    
    args = parser.parse_args()
    
    monitor = EnhancedBackgroundMonitor()
    
    if args.command == 'start':
        try:
            monitor.start(args.threads)
            
            if args.daemon:
                logger.info("Running in daemon mode - press Ctrl+C to stop")
                while True:
                    time.sleep(1)
            else:
                logger.info("Monitor started - press Ctrl+C to stop")
                input("Press Enter to stop...\n")
                
        except KeyboardInterrupt:
            logger.info("Received stop signal")
        finally:
            monitor.stop()
    
    elif args.command == 'status':
        status = monitor.status()
        print("\n📊 Background Monitor Status")
        print("=" * 40)
        
        if 'error' in status:
            print(f"❌ Error: {status['error']}")
        else:
            print(f"🔄 Running: {'Yes' if status['running'] else 'No'}")
            print(f"🧵 Active Threads: {status['active_threads']}")
            print(f"📁 Watch Directories: {status['watch_directories']}")
            print(f"✅ Processed Files: {status['processed_files']}")
            print(f"❌ Error Files: {status['error_files']}")
            print(f"📈 Scans (24h): {status['scans_24h']}")
            print(f"📄 Files Processed (24h): {status['files_processed_24h']}")
            print(f"🔴 Errors (24h): {status['errors_24h']}")
            if status['last_scan']:
                print(f"🕐 Last Scan: {status['last_scan'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    elif args.command == 'scan':
        if args.directory:
            directory_path = Path(args.directory)
            if directory_path.exists():
                print(f"🔍 Scanning {directory_path}...")
                
                dir_info = {
                    'path': directory_path,
                    'priority': 'manual',
                    'auto_organize': False
                }
                
                stats = monitor._scan_directory(dir_info, "manual")
                
                print(f"✅ Scan complete:")
                print(f"   Files found: {stats['files_found']}")
                print(f"   Files processed: {stats['files_processed']}")
                print(f"   Files skipped: {stats['files_skipped']}")
                print(f"   Errors: {stats['errors']}")
            else:
                print(f"❌ Directory not found: {directory_path}")
        else:
            print("❌ --directory required for scan command")

if __name__ == "__main__":
    main()