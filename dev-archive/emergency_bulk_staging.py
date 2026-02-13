#!/usr/bin/env python3
"""
Emergency Bulk Staging Script - Clear 50GB Across Multiple Directories
Targets: Downloads, Desktop, CONTENT_LIBRARY_MASTER
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import json

class EmergencyBulkStaging:
    def __init__(self):
        self.log_file = Path("emergency_bulk_staging.log")
        self.target_dirs = [
            "/Users/user/Downloads",
            "/Users/user/Desktop", 
            "/Users/user/CONTENT_LIBRARY_MASTER"
        ]
        self.min_file_size_mb = 50  # Only files 50MB+
        self.total_freed = 0
        self.files_staged = 0
        
    def get_large_files(self, directory: str, min_size_mb: float = 50) -> list:
        """Find all large files in a directory"""
        large_files = []
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        if size_mb >= min_size_mb:
                            large_files.append((str(file_path), size_mb))
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            print(f"❌ Cannot access directory: {directory}")
            
        return sorted(large_files, key=lambda x: x[1], reverse=True)  # Sort by size desc
    
    def stage_file_safely(self, file_path: str, size_mb: float) -> bool:
        """Stage single file: upload -> verify -> delete -> log"""
        
        print(f"\n📤 Staging: {Path(file_path).name} ({size_mb:.1f}MB)")
        
        # Build gdrive_cli command
        cmd = [
            "python", "gdrive_cli.py", "organize",
            "--file", file_path,
            "--folder", "99_STAGING_EMERGENCY", 
            "--live"
        ]
        
        try:
            # 1. Upload to Google Drive
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode != 0:
                print(f"❌ Upload failed: {result.stderr}")
                return False
                
            # Check if upload was successful by looking for "Successfully uploaded" in output
            if "Successfully uploaded" in result.stdout:
                print(f"✅ Upload verified")
                
                # 2. Delete local file
                try:
                    os.remove(file_path)
                    print(f"🗑️  Deleted local file")
                    print(f"💾 Freed {size_mb:.1f}MB")
                    
                    # 3. Log the operation
                    self._log_operation(file_path, size_mb, "SUCCESS")
                    
                    self.total_freed += size_mb
                    self.files_staged += 1
                    
                    return True
                    
                except OSError as e:
                    print(f"❌ Could not delete local file: {e}")
                    self._log_operation(file_path, size_mb, f"UPLOAD_OK_DELETE_FAILED: {e}")
                    return False
                    
            else:
                print(f"❌ Upload verification failed")
                self._log_operation(file_path, size_mb, "UPLOAD_FAILED")
                return False
                
        except Exception as e:
            print(f"❌ Staging error: {e}")
            self._log_operation(file_path, size_mb, f"ERROR: {e}")
            return False
    
    def _log_operation(self, file_path: str, size_mb: float, status: str):
        """Log staging operation"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp},{Path(file_path).name},{size_mb:.1f}MB,{status}\n"
        
        with open(self.log_file, "a") as f:
            f.write(log_entry)
    
    def stage_all_directories(self, target_gb: float = 5.0):
        """Stage large files from all target directories"""
        
        print(f"🚨 EMERGENCY BULK STAGING")
        print(f"Target: {target_gb}GB to free immediately")
        print("=" * 60)
        
        target_mb = target_gb * 1024
        
        for directory in self.target_dirs:
            if not Path(directory).exists():
                print(f"⚠️  Directory not found: {directory}")
                continue
                
            print(f"\n📁 Processing: {directory}")
            print(f"🔍 Finding files >{self.min_file_size_mb}MB...")
            
            large_files = self.get_large_files(directory, self.min_file_size_mb)
            
            if not large_files:
                print(f"   No large files found")
                continue
                
            print(f"   Found {len(large_files)} large files")
            
            # Stage files until we hit target or run out
            for file_path, size_mb in large_files:
                if self.total_freed >= target_mb:
                    print(f"\n🎯 REACHED {target_gb}GB TARGET!")
                    break
                    
                # Skip files that might be in use or system files
                if any(skip in file_path.lower() for skip in ['.app/', '.cache', '.tmp', '.log']):
                    continue
                
                success = self.stage_file_safely(file_path, size_mb)
                
                # Brief pause to avoid overwhelming Google Drive API
                if success:
                    import time
                    time.sleep(1)
                    
            if self.total_freed >= target_mb:
                break
                
        print(f"\n📊 EMERGENCY STAGING COMPLETE")
        print("=" * 60)
        print(f"   Files staged: {self.files_staged}")
        print(f"   Total freed: {self.total_freed:.1f}MB ({self.total_freed/1024:.1f}GB)")
        print(f"   Log file: {self.log_file}")
        print(f"   Staging folder: 99_STAGING_EMERGENCY")

if __name__ == "__main__":
    # Check if we have the minimum required space to run safely
    try:
        import shutil
        free_space_gb = shutil.disk_usage("/").free / (1024**3)
        print(f"💾 Current free space: {free_space_gb:.1f}GB")
        
        if free_space_gb < 5:
            print(f"🚨 CRITICAL: Only {free_space_gb:.1f}GB free!")
            
    except Exception:
        pass
    
    stager = EmergencyBulkStaging()
    stager.stage_all_directories(target_gb=5.0)  # Target 5GB immediate relief