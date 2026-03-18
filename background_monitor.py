
import os
import time
import threading
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedBackgroundMonitor:
    """
    Base class for background monitoring.
    Recreated to support AdaptiveBackgroundMonitor.
    """

    def __init__(self, base_dir: str = None, additional_watch_paths: List[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.additional_watch_paths = additional_watch_paths or []
        self.running = False
        self.threads = {}
        self.watch_directories = {}
        
        # Statistics
        self.stats = {
            "processed_files": 0,
            "error_files": 0,
            "scans_24h": 0,
            "files_processed_24h": 0,
            "errors_24h": 0,
            "last_scan": None
        }
        
        # Track start time for uptime calculation
        self.start_time = None
        
        # Initialize watch directories
        self._init_watch_directories()

    def _init_watch_directories(self):
        """Initialize default watch directories"""
        # Add default paths
        defaults = {
            "downloads": {"path": Path.home() / "Downloads", "priority": "high"},
            "desktop": {"path": Path.home() / "Desktop", "priority": "medium"},
        }
        
        for name, info in defaults.items():
            if info["path"].exists():
                self.watch_directories[name] = info
                
        # Add additional paths
        for path_str in self.additional_watch_paths:
            path = Path(path_str).resolve()
            if path.exists():
                # Check if already watching this path (avoid duplicates)
                is_duplicate = False
                for existing_info in self.watch_directories.values():
                    if existing_info['path'].resolve() == path:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    self.watch_directories[f"custom_{path.name}"] = {"path": path, "priority": "custom"}

    def start(self, threads: List[str] = None):
        """Start monitoring threads"""
        if not self.running:
            self.start_time = time.time()
        self.running = True
        self.logger = logging.getLogger(__name__)
        self.logger.info("Starting EnhancedBackgroundMonitor...")
        
        if not threads:
            threads = ['directory_scan']
            
        if 'directory_scan' in threads:
            self.threads['directory_scan'] = threading.Thread(
                target=self._periodic_scan, daemon=True
            )
            self.threads['directory_scan'].start()
            
    def stop(self):
        """Stop monitoring"""
        self.running = False
        for name, thread in self.threads.items():
            if thread.is_alive():
                thread.join(timeout=1.0)
        self.logger.info("Monitor stopped")

    def status(self) -> Dict[str, Any]:
        """Get monitor status"""
        return {
            "running": self.running,
            "active_threads": list(self.threads.keys()),
            "watch_directories": {k: str(v['path']) for k, v in self.watch_directories.items()},
            "processed_files": self.stats["processed_files"],
            "error_files": self.stats["error_files"],
            "scans_24h": self.stats["scans_24h"],
            "files_processed_24h": self.stats["files_processed_24h"],
            "errors_24h": self.stats["errors_24h"],
            "last_scan": self.stats["last_scan"],
            "uptime_seconds": int(time.time() - self.start_time) if self.start_time and self.running else 0
        }

    def _periodic_scan(self):
        """Periodic directory scan loop"""
        while self.running:
            try:
                self.stats["scans_24h"] += 1
                self.stats["last_scan"] = datetime.now()
                
                for name, info in self.watch_directories.items():
                    self._scan_directory(info, info["priority"])
                    
                time.sleep(3600)  # Scan every hour
            except Exception as e:
                self.logger.error(f"Error in periodic scan: {e}")
                time.sleep(60)

    def _scan_directory(self, dir_info: Dict[str, Any], priority: str) -> Dict[str, int]:
        """Scan a single directory"""
        path = dir_info["path"]
        results = {"files_found": 0, "files_processed": 0, "files_skipped": 0, "errors": 0}
        
        if not path.exists():
            return results
            
        try:
            # Basic implementation - just counting files for now
            # AdaptiveBackgroundMonitor overrides this anyway
            for file_path in path.iterdir():
                if file_path.is_file():
                    results["files_found"] += 1
                    # self._process_single_file(file_path) # Logic handled by subclass
                    
        except Exception as e:
            self.logger.error(f"Error scanning {path}: {e}")
            results["errors"] += 1
            
        return results

    def _process_single_file(self, file_path: Path, auto_organize: bool = False) -> bool:
        """Process a single file - to be overridden"""
        return False

    def _should_process_file(self, file_path: Path, check_parent_marker: bool = True) -> bool:
        """
        Determine if a file should be processed.
        
        Args:
            file_path: Path to the file
            check_parent_marker: If True, checks parent directories for _NOAI/.noai
            
        Returns:
            bool: True if file should be processed, False otherwise
        """
        # Skip hidden files
        if file_path.name.startswith('.'):
            return False
            
        # Skip system files
        if file_path.name in ['.DS_Store', 'Thumbs.db']:
            return False
            
        # Skip temporary files
        if file_path.suffix in ['.tmp', '.crdownload', '.part']:
            return False
            
        # USER IGNORE LOGIC:
        # 1. Skip paths containing folder with "_NOAI" suffix (e.g. "Private_NOAI")
        # 2. Skip paths if a ".noai" marker file exists in the folder
        
        if check_parent_marker:
            for part in file_path.parts:
                if part.endswith('_NOAI'):
                    return False

            if (file_path.parent / ".noai").exists():
                return False
        else:
            # OPTIMIZATION: If parent checks were already done,
            # only check if the file name itself ends with _NOAI
            if file_path.name.endswith('_NOAI'):
                return False
            
        return True
