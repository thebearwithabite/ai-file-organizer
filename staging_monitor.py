#!/usr/bin/env python3
"""
ARCHITECTURAL LAW:
- base_dir = monitored filesystem location (may be remote)
- metadata_root = internal state (MUST be local)
- metadata_root MUST come from get_metadata_root()
- NEVER derive metadata paths from base_dir

7-Day Staging Monitor System
Tracks file age in Desktop/Downloads for natural transition workflow
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

# Import centralized metadata root
from gdrive_integration import get_metadata_root

class StagingMonitor:
    """
    Monitors Desktop/Downloads folders for 7-day staging workflow
    Non-intrusive file age tracking with gentle organization suggestions
    """
    
    def __init__(self, base_dir: str = None):
        # base_dir is ONLY for the monitored area
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Default to checking Desktop/Downloads if no GDrive path provided
            self.base_dir = Path.home()
        
        # Internal state MUST be local (RULE ONE)
        metadata_root = get_metadata_root()
        db_dir = metadata_root / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_dir / "staging_monitor.db"
        self.config_path = metadata_root / "staging_config.json"
        
        # Monitored folders
        self.desktop_path = Path.home() / "Desktop"
        self.downloads_path = Path.home() / "Downloads"
        
        self._init_database()
        self._load_config()
    
    def _init_database(self):
        """Initialize SQLite database for file tracking"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_tracking (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT,
                    first_seen TIMESTAMP,
                    last_modified TIMESTAMP,
                    size_bytes INTEGER,
                    folder_location TEXT,
                    status TEXT DEFAULT 'active',
                    days_in_staging INTEGER DEFAULT 0,
                    suggested_category TEXT,
                    confidence_score REAL,
                    user_interaction TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS staging_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    event_type TEXT,
                    event_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def _load_config(self):
        """Load staging configuration"""
        default_config = {
            "staging_days": 7,
            "check_interval_hours": 24,
            "notification_time": "23:00",
            "excluded_extensions": [".tmp", ".cache", ".DS_Store"],
            "excluded_folders": ["node_modules", ".git", "__pycache__"],
            "auto_organize_confidence": 0.65,
            "suggestion_confidence": 0.50
        }
        
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = {**default_config, **json.load(f)}
        else:
            self.config = default_config
            self._save_config()
    
    def _save_config(self):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash for file change detection"""
        try:
            with open(file_path, 'rb') as f:
                # Read first 1KB for quick hash
                content = f.read(1024)
                return hashlib.md5(content).hexdigest()
        except:
            return ""
    
    def scan_staging_folders(self) -> Dict[str, List[Dict]]:
        """Scan Desktop and Downloads for files"""
        results = {"desktop": [], "downloads": []}
        
        for folder_name, folder_path in [("desktop", self.desktop_path), ("downloads", self.downloads_path)]:
            if not folder_path.exists():
                continue
                
            for file_path in folder_path.iterdir():
                if not file_path.is_file():
                    continue
                    
                # Skip excluded files
                if file_path.suffix.lower() in self.config["excluded_extensions"]:
                    continue
                    
                if any(excluded in file_path.name for excluded in self.config["excluded_folders"]):
                    continue
                
                try:
                    stat = file_path.stat()
                    file_info = {
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "created": datetime.fromtimestamp(stat.st_ctime),
                        "hash": None  # Lazy hashing: computed only if needed in update_tracking_database
                    }
                    results[folder_name].append(file_info)
                except Exception as e:
                    print(f"Error scanning {file_path}: {e}")
        
        return results
    
    def record_observation(self, file_path: Path, folder_location: str = "custom", db_connection: Optional[sqlite3.Connection] = None) -> bool:
        """
        Instantly record an observation of a file for age tracking.
        Returns True if newly discovered.
        """
        if not file_path.exists() or not file_path.is_file():
            return False
            
        current_time = datetime.now()
        # file_hash calculation deferred to _perform_record_observation if needed
        
        try:
            if db_connection:
                return self._perform_record_observation(db_connection, file_path, folder_location, current_time)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    return self._perform_record_observation(conn, file_path, folder_location, current_time)
        except Exception as e:
            print(f"Error recording observation for {file_path}: {e}")
            return False

    def _perform_record_observation(self, conn: sqlite3.Connection, file_path: Path, folder_location: str, current_time: datetime, file_hash: Optional[str] = None) -> bool:
        """Internal logic for record_observation to support connection reuse"""
        # Check if exists
        cursor = conn.execute(
            "SELECT file_hash, first_seen, status FROM file_tracking WHERE file_path = ?",
            (str(file_path),)
        )
        existing = cursor.fetchone()

        if existing:
            # Update status to active if it was removed/organized but reappeared
            if existing[2] != 'active':
                conn.execute(
                    "UPDATE file_tracking SET status = 'active', last_modified = ? WHERE file_path = ?",
                    (current_time, str(file_path))
                )
            return False
        else:
            # New discovery - NOW calculate hash if not provided
            if file_hash is None:
                file_hash = self._get_file_hash(file_path)

            conn.execute("""
                INSERT INTO file_tracking
                (file_path, file_hash, first_seen, last_modified, size_bytes, folder_location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(file_path), file_hash, current_time, current_time,
                file_path.stat().st_size, folder_location
            ))

            conn.execute("""
                INSERT INTO staging_events (file_path, event_type, event_data)
                VALUES (?, 'discovered', ?)
            """, (str(file_path), json.dumps({"folder": folder_location, "instant": True})))
            
            return True

    def get_file_age_days(self, file_path: str, db_connection: Optional[sqlite3.Connection] = None) -> Optional[int]:
        """Get the number of days a file has been known to the system"""
        try:
            if db_connection:
                return self._perform_get_file_age(db_connection, file_path)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    return self._perform_get_file_age(conn, file_path)
        except Exception as e:
            print(f"Error getting file age: {e}")
        return None

    def _perform_get_file_age(self, conn: sqlite3.Connection, file_path: str) -> Optional[int]:
        """Internal logic for get_file_age_days to support connection reuse"""
        cursor = conn.execute(
            "SELECT first_seen FROM file_tracking WHERE file_path = ?",
            (str(file_path),)
        )
        result = cursor.fetchone()
        if result:
            first_seen = datetime.fromisoformat(result[0])
            return (datetime.now() - first_seen).days
        return None
    
    def update_tracking_database(self, scan_results: Dict[str, List[Dict]]):
        """Update database with current scan results"""
        current_time = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            for folder_name, files in scan_results.items():
                for file_info in files:
                    file_path = file_info["path"]
                    file_hash = file_info.get("hash")
                    
                    # Check if file exists in tracking
                    cursor = conn.execute(
                        "SELECT file_hash, first_seen, size_bytes, last_modified FROM file_tracking WHERE file_path = ?",
                        (file_path,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        db_hash, db_first_seen, db_size, db_last_mod_str = existing

                        # Determine if we need to calculate hash
                        if file_hash is None:
                            # Parse DB timestamp (assuming ISO format)
                            try:
                                # Handle case where last_modified might be None or invalid
                                if db_last_mod_str:
                                    db_last_mod = datetime.fromisoformat(str(db_last_mod_str))
                                else:
                                    db_last_mod = datetime.min
                            except Exception:
                                db_last_mod = datetime.min

                            # Lazy Hashing Logic:
                            # If file on disk has NOT been modified since we last checked it (db_last_mod),
                            # AND the size is identical, we assume the content is unchanged.
                            # We use < because db_last_mod is the time we WROTE the record, so content MUST be older.
                            if file_info["modified"] < db_last_mod and file_info["size"] == db_size:
                                file_hash = db_hash # Optimized: reuse existing hash
                            else:
                                file_hash = self._get_file_hash(Path(file_path))

                        # File exists - check if modified
                        if db_hash != file_hash:
                            # File modified - update tracking
                            conn.execute("""
                                UPDATE file_tracking 
                                SET file_hash = ?, last_modified = ?, size_bytes = ?
                                WHERE file_path = ?
                            """, (file_hash, current_time, file_info["size"], file_path))
                            
                            # Log modification event
                            conn.execute("""
                                INSERT INTO staging_events (file_path, event_type, event_data)
                                VALUES (?, 'modified', ?)
                            """, (file_path, json.dumps({"new_size": file_info["size"]})))
                    else:
                        # New file - add to tracking
                        if file_hash is None:
                            file_hash = self._get_file_hash(Path(file_path))

                        conn.execute("""
                            INSERT INTO file_tracking 
                            (file_path, file_hash, first_seen, last_modified, size_bytes, folder_location)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            file_path, file_hash, current_time, current_time,
                            file_info["size"], folder_name
                        ))
                        
                        # Log new file event
                        conn.execute("""
                            INSERT INTO staging_events (file_path, event_type, event_data)
                            VALUES (?, 'discovered', ?)
                        """, (file_path, json.dumps({"folder": folder_name})))
    
    def get_files_ready_for_organization(self) -> List[Dict]:
        """Get files that have been in staging for 7+ days"""
        staging_cutoff = datetime.now() - timedelta(days=self.config["staging_days"])
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path, first_seen, folder_location, size_bytes,
                       CAST((julianday('now') - julianday(first_seen)) AS INTEGER) as days_in_staging
                FROM file_tracking 
                WHERE first_seen <= ? AND status = 'active'
                ORDER BY first_seen ASC
            """, (staging_cutoff,))
            
            ready_files = []
            for row in cursor.fetchall():
                file_path, first_seen, folder_location, size_bytes, days_in_staging = row
                
                # Verify file still exists
                if Path(file_path).exists():
                    ready_files.append({
                        "path": file_path,
                        "name": Path(file_path).name,
                        "first_seen": first_seen,
                        "folder": folder_location,
                        "size": size_bytes,
                        "days_in_staging": days_in_staging
                    })
                else:
                    # Mark as removed
                    conn.execute(
                        "UPDATE file_tracking SET status = 'removed' WHERE file_path = ?",
                        (file_path,)
                    )
        
        return ready_files
    
    def mark_file_organized(self, file_path: str, target_location: str = None):
        """Mark a file as organized (moved from staging)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE file_tracking SET status = 'organized' WHERE file_path = ?",
                (file_path,)
            )
            
            # Log organization event
            conn.execute("""
                INSERT INTO staging_events (file_path, event_type, event_data)
                VALUES (?, 'organized', ?)
            """, (file_path, json.dumps({"target": target_location})))
    
    def get_staging_stats(self) -> Dict:
        """Get current staging statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_active,
                    COUNT(CASE WHEN julianday('now') - julianday(first_seen) >= 7 THEN 1 END) as ready_for_org,
                    COUNT(CASE WHEN julianday('now') - julianday(first_seen) >= 14 THEN 1 END) as overdue,
                    AVG(julianday('now') - julianday(first_seen)) as avg_days_in_staging
                FROM file_tracking 
                WHERE status = 'active'
            """)
            
            stats = cursor.fetchone()
            
            return {
                "total_active_files": stats[0] or 0,
                "ready_for_organization": stats[1] or 0,
                "overdue_files": stats[2] or 0,
                "average_staging_days": round(stats[3] or 0, 1)
            }
    
    def generate_gentle_suggestion(self) -> Optional[str]:
        """Generate non-intrusive organization suggestion"""
        ready_files = self.get_files_ready_for_organization()
        
        if not ready_files:
            return None
        
        stats = self.get_staging_stats()
        
        suggestion = f"""
🗂️  Gentle File Organization Reminder

You have {stats['ready_for_organization']} files that have been in your staging areas for 7+ days.

Recent files ready for organization:
"""
        
        # Show up to 5 most recent files
        for file_info in ready_files[:5]:
            suggestion += f"  • {file_info['name']} ({file_info['days_in_staging']} days)\n"
        
        if len(ready_files) > 5:
            suggestion += f"  • ... and {len(ready_files) - 5} more\n"
        
        suggestion += f"""
💡 These files can be organized when you're ready - no rush!
   The system learns your preferences as you organize naturally.
"""
        
        return suggestion

def test_staging_monitor():
    """Test the staging monitor system"""
    print("🧪 Testing 7-Day Staging Monitor")
    print("-" * 40)
    
    # Initialize monitor
    monitor = StagingMonitor()
    
    # Scan folders
    print("📁 Scanning staging folders...")
    scan_results = monitor.scan_staging_folders()
    
    desktop_count = len(scan_results["desktop"])
    downloads_count = len(scan_results["downloads"])
    
    print(f"  Desktop: {desktop_count} files")
    print(f"  Downloads: {downloads_count} files")
    
    # Update database
    print("💾 Updating tracking database...")
    monitor.update_tracking_database(scan_results)
    
    # Get statistics
    stats = monitor.get_staging_stats()
    print(f"\n📊 Staging Statistics:")
    print(f"  Total active files: {stats['total_active_files']}")
    print(f"  Ready for organization: {stats['ready_for_organization']}")
    print(f"  Overdue files: {stats['overdue_files']}")
    print(f"  Average staging days: {stats['average_staging_days']}")
    
    # Generate suggestion
    suggestion = monitor.generate_gentle_suggestion()
    if suggestion:
        print("\n💡 Organization Suggestion:")
        print(suggestion)
    else:
        print("\n✨ No files ready for organization yet!")
    
    print("\n✅ Staging monitor test completed!")

if __name__ == "__main__":
    test_staging_monitor()