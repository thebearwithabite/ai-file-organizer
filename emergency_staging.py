#!/usr/bin/env python3
"""
Emergency Storage Recovery - Safe Upload to Google Drive Staging
CRITICAL: This bypasses the full librarian system for emergency space clearing
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from gdrive_librarian import GoogleDriveLibrarian

class EmergencyStaging:
    def __init__(self):
        self.librarian = GoogleDriveLibrarian()
        self.staging_log = Path("emergency_staging.json")
        
    def safe_stage_file(self, file_path: str) -> bool:
        """Safely stage file: upload -> verify -> delete -> log"""
        
        local_file = Path(file_path)
        if not local_file.exists():
            print(f"❌ File not found: {file_path}")
            return False
            
        file_size_mb = local_file.stat().st_size / (1024 * 1024)
        print(f"\n📤 Staging: {local_file.name} ({file_size_mb:.1f}MB)")
        
        # 1. Upload to staging folder
        file_id = self.librarian.upload_file(str(local_file), gdrive_folder="99_STAGING_EMERGENCY")
        
        if not file_id:
            print(f"❌ Upload failed for {local_file.name}")
            return False
            
        # 2. Verify upload exists on Google Drive
        print(f"🔍 Verifying upload...")
        time.sleep(2)  # Brief delay for Google Drive sync
        
        # Check if file exists in Google Drive
        try:
            # Use the Google Drive API to verify file exists
            drive_service = self.librarian.drive_service
            file_info = drive_service.files().get(fileId=file_id).execute()
            
            if file_info and int(file_info.get('size', 0)) == local_file.stat().st_size:
                print(f"✅ Upload verified - sizes match")
                
                # 3. Log to emergency staging file
                self._log_staging_operation(local_file, file_id, file_size_mb)
                
                # 4. Delete local file
                local_file.unlink()
                print(f"🗑️  Deleted local file")
                print(f"💾 Freed {file_size_mb:.1f}MB")
                
                return True
            else:
                print(f"❌ Upload verification failed - size mismatch")
                return False
                
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False
            
    def _log_staging_operation(self, local_file: Path, gdrive_file_id: str, size_mb: float):
        """Log emergency staging operation for later processing"""
        
        # Load existing log
        staging_data = []
        if self.staging_log.exists():
            with open(self.staging_log, 'r') as f:
                staging_data = json.load(f)
        
        # Add this operation
        operation = {
            'timestamp': datetime.now().isoformat(),
            'original_path': str(local_file),
            'original_filename': local_file.name,
            'gdrive_file_id': gdrive_file_id,
            'size_mb': size_mb,
            'staging_folder': '99_STAGING_EMERGENCY',
            'status': 'staged_for_processing'
        }
        
        staging_data.append(operation)
        
        # Save updated log
        with open(self.staging_log, 'w') as f:
            json.dump(staging_data, f, indent=2)
            
    def stage_large_files(self, min_size_mb: float = 50):
        """Stage all large files for emergency space clearing"""
        
        print(f"🚨 Emergency Staging - Files >{min_size_mb}MB")
        print("=" * 50)
        
        # Directories to check
        check_dirs = [
            Path.home() / "Downloads",
            Path.home() / "Documents", 
            Path.home() / "Desktop"
        ]
        
        total_staged = 0
        total_freed = 0
        
        for check_dir in check_dirs:
            if not check_dir.exists():
                continue
                
            print(f"\n📁 Checking: {check_dir}")
            
            for file_path in check_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        
                        if size_mb >= min_size_mb:
                            if self.safe_stage_file(str(file_path)):
                                total_staged += 1
                                total_freed += size_mb
                                
                                # Check if we've freed enough space
                                if total_freed >= 5000:  # 5GB target for immediate relief
                                    print(f"\n🎯 Reached 5GB staging target")
                                    break
                                    
                    except Exception as e:
                        print(f"❌ Error processing {file_path.name}: {e}")
                        
        print(f"\n📊 Emergency Staging Summary:")
        print(f"   Files staged: {total_staged}")
        print(f"   Space freed: {total_freed:.1f}MB")
        print(f"   Log saved: {self.staging_log}")
        
if __name__ == "__main__":
    stager = EmergencyStaging()
    stager.stage_large_files(min_size_mb=50)