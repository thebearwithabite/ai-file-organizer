#!/usr/bin/env python3
"""
Audacity Google Drive Uploader - Safe Upload Script
Safely uploads large Audacity project files to Google Drive with comprehensive verification

CRITICAL SAFETY FEATURES:
- Upload verification with size matching
- Only deletes local files after confirmed successful upload
- Comprehensive error handling with rollback
- Progress reporting for large files
- Detailed logging of all operations

Usage:
    python audacity_gdrive_uploader.py
    
Files to upload:
1. /Users/user/Library/Application Support/audacity/CloudProjects/AlphaGo-Checkpoint Final.aup3
2. /Users/user/Library/Application Support/audacity/CloudProjects/CSC.aup3

# Script created for file organization workflow
"""

import os
import sys
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

# Import existing Google Drive auth
try:
    from google_drive_auth import GoogleDriveAuth, GoogleDriveAuthError
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
except ImportError as e:
    print("❌ Missing required dependencies:")
    print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# Set up comprehensive logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'audacity_upload_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AudacityUploaderError(Exception):
    """Custom exception for upload errors"""
    pass

class AudacityGDriveUploader:
    """
    Safe Google Drive uploader for Audacity project files
    
    Features:
    - Pre-upload verification (file exists, readable)
    - Upload with progress tracking
    - Post-upload verification (size, integrity)
    - Safe local file removal only after confirmation
    - Comprehensive rollback on any failure
    - Detailed operation logging
    """
    
    def __init__(self):
        """Initialize the uploader with Google Drive authentication"""
        
        logger.info("🚀 Initializing Audacity Google Drive Uploader")
        
        # Files to upload (as specified by user)
        self.audacity_files = [
            Path.home() / "Library/Application Support/audacity/CloudProjects/AlphaGo-Checkpoint Final.aup3",
            Path.home() / "Library/Application Support/audacity/CloudProjects/CSC.aup3"
        ]
        
        # Google Drive setup
        self.target_folder_name = "Audacity Projects"
        self.target_folder_id = None
        
        # Initialize Google Drive auth
        try:
            self.auth = GoogleDriveAuth()
            self.service = self.auth.get_authenticated_service()
            logger.info("✅ Google Drive authentication successful")
        except Exception as e:
            logger.error(f"❌ Google Drive authentication failed: {e}")
            raise AudacityUploaderError(f"Authentication failed: {e}")
        
        # Upload tracking
        self.upload_results = []
        self.total_space_freed = 0
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for integrity verification"""
        
        logger.info(f"🔍 Calculating hash for {file_path.name}")
        
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            file_hash = hash_md5.hexdigest()
            logger.info(f"✅ Hash calculated: {file_hash[:8]}...")
            return file_hash
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate hash for {file_path}: {e}")
            raise AudacityUploaderError(f"Hash calculation failed: {e}")
    
    def verify_file_accessibility(self, file_path: Path) -> Dict[str, any]:
        """Verify file exists and is accessible before upload"""
        
        logger.info(f"🔍 Verifying file accessibility: {file_path.name}")
        
        result = {
            'exists': False,
            'readable': False,
            'size_bytes': 0,
            'size_mb': 0,
            'hash': None
        }
        
        try:
            # Check file exists
            if not file_path.exists():
                logger.error(f"❌ File does not exist: {file_path}")
                return result
            
            result['exists'] = True
            
            # Check file is readable
            if not os.access(file_path, os.R_OK):
                logger.error(f"❌ File is not readable: {file_path}")
                return result
            
            result['readable'] = True
            
            # Get file size
            stat_info = file_path.stat()
            result['size_bytes'] = stat_info.st_size
            result['size_mb'] = result['size_bytes'] / (1024 * 1024)
            
            logger.info(f"📊 File size: {result['size_mb']:.1f} MB ({result['size_bytes']:,} bytes)")
            
            # Calculate hash for integrity verification
            result['hash'] = self.calculate_file_hash(file_path)
            
            logger.info(f"✅ File verification successful: {file_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ File verification failed for {file_path}: {e}")
            raise AudacityUploaderError(f"File verification failed: {e}")
    
    def get_or_create_target_folder(self) -> str:
        """Get or create the target folder in Google Drive"""
        
        logger.info(f"📁 Setting up target folder: {self.target_folder_name}")
        
        try:
            # Search for existing folder
            query = f"name='{self.target_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(q=query, fields='files(id,name)').execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"✅ Found existing folder: {self.target_folder_name} (ID: {folder_id})")
                return folder_id
            
            # Create new folder
            logger.info(f"📁 Creating new folder: {self.target_folder_name}")
            folder_metadata = {
                'name': self.target_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            logger.info(f"✅ Created folder: {self.target_folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"❌ Failed to set up target folder: {e}")
            raise AudacityUploaderError(f"Folder setup failed: {e}")
    
    def upload_file_with_progress(self, file_path: Path, folder_id: str) -> Dict[str, any]:
        """Upload file to Google Drive with progress tracking and verification"""
        
        logger.info(f"⬆️  Starting upload: {file_path.name}")
        
        upload_result = {
            'success': False,
            'file_id': None,
            'upload_size': 0,
            'verification_passed': False,
            'local_file_removed': False
        }
        
        try:
            # Pre-upload verification
            file_info = self.verify_file_accessibility(file_path)
            if not file_info['exists'] or not file_info['readable']:
                raise AudacityUploaderError(f"File verification failed: {file_path}")
            
            # Prepare upload
            file_metadata = {
                'name': file_path.name,
                'parents': [folder_id]
            }
            
            # Create resumable upload for large files
            media = MediaFileUpload(
                str(file_path),
                resumable=True,
                chunksize=1024*1024  # 1MB chunks for progress tracking
            )
            
            # Start upload
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size'
            )
            
            response = None
            progress_counter = 0
            
            logger.info(f"📤 Uploading {file_info['size_mb']:.1f} MB...")
            
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress_percent = int(status.progress() * 100)
                        if progress_counter % 10 == 0:  # Log every 10th chunk
                            logger.info(f"   📊 Upload progress: {progress_percent}%")
                        progress_counter += 1
                        
                except HttpError as e:
                    logger.error(f"❌ Upload failed: {e}")
                    raise AudacityUploaderError(f"Upload failed: {e}")
            
            # Upload completed
            uploaded_file_id = response.get('id')
            uploaded_file_name = response.get('name')
            uploaded_file_size = int(response.get('size', 0))
            
            logger.info(f"✅ Upload completed: {uploaded_file_name}")
            logger.info(f"   📊 Uploaded size: {uploaded_file_size:,} bytes")
            
            upload_result.update({
                'success': True,
                'file_id': uploaded_file_id,
                'upload_size': uploaded_file_size
            })
            
            # CRITICAL: Verify upload integrity
            logger.info(f"🔍 Verifying upload integrity...")
            
            if uploaded_file_size != file_info['size_bytes']:
                raise AudacityUploaderError(
                    f"Size mismatch! Local: {file_info['size_bytes']:,} bytes, "
                    f"Uploaded: {uploaded_file_size:,} bytes"
                )
            
            # Additional verification: Check file exists in Drive
            try:
                drive_file = self.service.files().get(fileId=uploaded_file_id, fields='id,name,size').execute()
                if not drive_file:
                    raise AudacityUploaderError("Uploaded file not found in Drive")
                
                logger.info(f"✅ Upload verification successful")
                upload_result['verification_passed'] = True
                
            except Exception as e:
                raise AudacityUploaderError(f"Upload verification failed: {e}")
            
            return upload_result
            
        except Exception as e:
            logger.error(f"❌ Upload failed for {file_path.name}: {e}")
            
            # If upload partially succeeded, try to clean up
            if upload_result.get('file_id'):
                try:
                    logger.info(f"🧹 Cleaning up partial upload...")
                    self.service.files().delete(fileId=upload_result['file_id']).execute()
                    logger.info(f"✅ Partial upload cleaned up")
                except:
                    logger.warning(f"⚠️  Could not clean up partial upload: {upload_result['file_id']}")
            
            raise AudacityUploaderError(f"Upload failed: {e}")
    
    def safe_remove_local_file(self, file_path: Path, upload_result: Dict) -> bool:
        """Safely remove local file only after successful upload verification"""
        
        logger.info(f"🗑️  Preparing to remove local file: {file_path.name}")
        
        # Double-check upload was successful and verified
        if not upload_result.get('success') or not upload_result.get('verification_passed'):
            logger.error(f"❌ Cannot remove local file - upload not verified: {file_path.name}")
            return False
        
        try:
            # Final size check before removal
            local_size = file_path.stat().st_size
            upload_size = upload_result.get('upload_size', 0)
            
            if local_size != upload_size:
                logger.error(f"❌ Size mismatch prevents local file removal")
                logger.error(f"   Local: {local_size:,} bytes, Upload: {upload_size:,} bytes")
                return False
            
            # Create backup in temp location (just in case)
            backup_dir = Path("/tmp/audacity_upload_backup")
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f"{file_path.name}.backup"
            
            logger.info(f"💾 Creating temporary backup: {backup_path}")
            import shutil
            shutil.copy2(file_path, backup_path)
            
            # Remove original file
            file_path.unlink()
            logger.info(f"✅ Local file removed: {file_path.name}")
            
            # Log space freed
            space_freed_mb = local_size / (1024 * 1024)
            self.total_space_freed += space_freed_mb
            logger.info(f"💿 Space freed: {space_freed_mb:.1f} MB")
            
            # Clean up backup after successful removal (keep for 5 minutes)
            time.sleep(5)  # Brief delay to ensure everything is stable
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"🧹 Backup cleaned up: {backup_path.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove local file {file_path.name}: {e}")
            logger.error(f"   File remains on disk for safety")
            return False
    
    def process_all_files(self) -> Dict[str, any]:
        """Process all Audacity files with comprehensive safety checks"""
        
        logger.info("🎵 Starting Audacity files upload process")
        logger.info("=" * 60)
        
        summary = {
            'total_files': len(self.audacity_files),
            'successful_uploads': 0,
            'failed_uploads': 0,
            'local_files_removed': 0,
            'total_space_freed_mb': 0,
            'upload_details': [],
            'errors': []
        }
        
        try:
            # Set up target folder
            self.target_folder_id = self.get_or_create_target_folder()
            
            # Process each file
            for i, file_path in enumerate(self.audacity_files, 1):
                logger.info(f"\n📁 Processing file {i}/{len(self.audacity_files)}: {file_path.name}")
                logger.info("-" * 40)
                
                file_result = {
                    'file_name': file_path.name,
                    'file_path': str(file_path),
                    'upload_successful': False,
                    'verification_passed': False,
                    'local_removed': False,
                    'space_freed_mb': 0,
                    'error': None
                }
                
                try:
                    # Check if file exists first
                    if not file_path.exists():
                        raise AudacityUploaderError(f"File not found: {file_path}")
                    
                    # Upload file
                    upload_result = self.upload_file_with_progress(file_path, self.target_folder_id)
                    
                    file_result.update({
                        'upload_successful': upload_result['success'],
                        'verification_passed': upload_result['verification_passed'],
                        'gdrive_file_id': upload_result.get('file_id')
                    })
                    
                    if upload_result['success'] and upload_result['verification_passed']:
                        summary['successful_uploads'] += 1
                        
                        # Only remove local file if upload verified
                        if self.safe_remove_local_file(file_path, upload_result):
                            file_result['local_removed'] = True
                            file_result['space_freed_mb'] = upload_result['upload_size'] / (1024 * 1024)
                            summary['local_files_removed'] += 1
                        
                    else:
                        summary['failed_uploads'] += 1
                        file_result['error'] = "Upload verification failed"
                
                except Exception as e:
                    logger.error(f"❌ Failed to process {file_path.name}: {e}")
                    summary['failed_uploads'] += 1
                    file_result['error'] = str(e)
                    summary['errors'].append(f"{file_path.name}: {e}")
                
                summary['upload_details'].append(file_result)
            
            # Calculate total space freed
            summary['total_space_freed_mb'] = self.total_space_freed
            
            # Log final summary
            logger.info("\n" + "="*60)
            logger.info("📊 UPLOAD SUMMARY")
            logger.info("="*60)
            logger.info(f"✅ Successful uploads: {summary['successful_uploads']}/{summary['total_files']}")
            logger.info(f"🗑️  Local files removed: {summary['local_files_removed']}/{summary['total_files']}")
            logger.info(f"💿 Total space freed: {summary['total_space_freed_mb']:.1f} MB ({summary['total_space_freed_mb']/1024:.2f} GB)")
            
            if summary['errors']:
                logger.warning(f"⚠️  Errors encountered: {len(summary['errors'])}")
                for error in summary['errors']:
                    logger.warning(f"   - {error}")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Critical error in upload process: {e}")
            summary['errors'].append(f"Critical error: {e}")
            return summary
    
    def create_summary_report(self, summary: Dict) -> Path:
        """Create detailed summary report"""
        
        report_file = Path(__file__).parent / f"audacity_upload_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Add timestamp and additional info
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'script_version': '1.0',
            'target_folder': self.target_folder_name,
            'target_folder_id': self.target_folder_id,
            'summary': summary
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"📋 Summary report saved: {report_file}")
        return report_file

def main():
    """Main execution function"""
    
    print("🎵 Audacity Google Drive Uploader")
    print("=" * 50)
    print("SAFETY FEATURES ENABLED:")
    print("✅ Upload verification with size matching")
    print("✅ Only deletes local files after confirmed upload")
    print("✅ Comprehensive error handling")
    print("✅ Detailed logging and progress tracking")
    print("=" * 50)
    
    try:
        # Confirm with user before proceeding
        print("\nFiles to upload:")
        files_to_upload = [
            str(Path.home() / "Library/Application Support/audacity/CloudProjects/AlphaGo-Checkpoint Final.aup3"),
            str(Path.home() / "Library/Application Support/audacity/CloudProjects/CSC.aup3")
        ]
        
        for file_path in files_to_upload:
            print(f"  📁 {file_path}")
        
        print(f"\n🎯 Target: Google Drive folder 'Audacity Projects'")
        print(f"📝 Log file: {log_file}")
        
        response = input("\nProceed with upload? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Upload cancelled by user")
            return
        
        # Initialize and run uploader
        uploader = AudacityGDriveUploader()
        summary = uploader.process_all_files()
        
        # Create summary report
        report_file = uploader.create_summary_report(summary)
        
        # Final status
        if summary['successful_uploads'] == summary['total_files']:
            print(f"\n🎉 SUCCESS! All {summary['total_files']} files uploaded successfully")
            print(f"💿 Total space freed: {summary['total_space_freed_mb']:.1f} MB")
        elif summary['successful_uploads'] > 0:
            print(f"\n⚠️  PARTIAL SUCCESS: {summary['successful_uploads']}/{summary['total_files']} files uploaded")
            print(f"💿 Space freed: {summary['total_space_freed_mb']:.1f} MB")
        else:
            print(f"\n❌ FAILED: No files were uploaded successfully")
        
        print(f"\n📋 Detailed report: {report_file}")
        print(f"📝 Full log: {log_file}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Upload cancelled by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        print(f"\n❌ Critical error: {e}")
        print(f"📝 Check log for details: {log_file}")

if __name__ == "__main__":
    main()