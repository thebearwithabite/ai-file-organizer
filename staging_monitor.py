#!/usr/bin/env python3
"""
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

class StagingMonitor:
    """
    Monitors Desktop/Downloads folders for 7-day staging workflow
    Non-intrusive file age tracking with gentle organization suggestions
    """
    
    def __init__(self, base_dir: str = None):
        # Default to current script directory for database files
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(__file__).parent
        
        self.db_path = self.base_dir / "staging_monitor.db"
        self.config_path = self.base_dir / "staging_config.json"
        
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
            "auto_organize_confidence": 0.8,
            "suggestion_confidence": 0.6
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
                        "hash": self._get_file_hash(file_path)
                    }
                    results[folder_name].append(file_info)
                except Exception as e:
                    print(f"Error scanning {file_path}: {e}")
        
        return results
    
    def update_tracking_database(self, scan_results: Dict[str, List[Dict]]):
        """Update database with current scan results"""
        current_time = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            for folder_name, files in scan_results.items():
                for file_info in files:
                    file_path = file_info["path"]
                    file_hash = file_info["hash"]
                    
                    # Check if file exists in tracking
                    cursor = conn.execute(
                        "SELECT file_hash, first_seen FROM file_tracking WHERE file_path = ?",
                        (file_path,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # File exists - check if modified
                        if existing[0] != file_hash:
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