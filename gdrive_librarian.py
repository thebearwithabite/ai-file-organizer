#!/usr/bin/env python3
"""
Google Drive AI Librarian
Integrates your AI File Organizer with Google Drive for cloud storage and organization.
ADHD-friendly design with smart file management.
"""

import os
import json
import pickle
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

from classification_engine import FileClassificationEngine, ClassificationResult

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

class GoogleDriveLibrarian:
    """AI-powered Google Drive file organizer with ADHD-friendly features"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents"
        self.credentials_file = self.base_dir / "04_METADATA_SYSTEM" / "gdrive_credentials.json"
        self.token_file = self.base_dir / "04_METADATA_SYSTEM" / "gdrive_token.pickle"
        
        # Create metadata directory if it doesn't exist
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize Google Drive service
        self.service = None
        self.authenticated = False
        
        # Initialize local AI classifier
        self.classifier = FileClassificationEngine(str(self.base_dir))
        
        # Google Drive folder mapping
        self.gdrive_folders = {
            "entertainment": "Entertainment Industry",
            "creative": "VOX",
            "business": "Business Operations", 
            "reference": "Reference Material",
            "audio": "Music",
            "effects": "SFX"
        }
        
        print("🤖 Google Drive AI Librarian initialized")
        print(f"📁 Base directory: {self.base_dir}")
    
    def authenticate(self, credentials_path: str = None) -> bool:
        """Authenticate with Google Drive API"""
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path and not self.credentials_file.exists():
                    print("❌ Google Drive credentials not found!")
                    print("📝 Please download OAuth2 credentials from Google Cloud Console:")
                    print("   1. Go to https://console.cloud.google.com/")
                    print("   2. Enable Google Drive API") 
                    print("   3. Create OAuth2 credentials (Desktop application)")
                    print("   4. Download JSON file")
                    print(f"   5. Save as: {self.credentials_file}")
                    return False
                
                cred_file = credentials_path if credentials_path else str(self.credentials_file)
                flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
        self.authenticated = True
        print("✅ Google Drive authenticated successfully")
        return True
    
    def get_drive_folders(self) -> Dict[str, str]:
        """Get mapping of folder names to Google Drive folder IDs"""
        if not self.authenticated:
            return {}
        
        try:
            # Query for folders
            results = self.service.files().list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                pageSize=100,
                fields="nextPageToken, files(id, name, parents)"
            ).execute()
            
            folders = {}
            for item in results.get('files', []):
                folders[item['name']] = item['id']
            
            return folders
            
        except HttpError as error:
            print(f"❌ Error getting folders: {error}")
            return {}
    
    def upload_file(self, local_path: str, gdrive_folder: str = None, 
                   new_name: str = None, auto_delete: bool = False) -> Optional[str]:
        """Upload file to Google Drive with AI classification and optional auto-deletion"""
        if not self.authenticated:
            print("❌ Not authenticated with Google Drive")
            return None
        
        local_file = Path(local_path)
        if not local_file.exists():
            print(f"❌ File not found: {local_path}")
            return None
        
        # Store file size for logging before upload
        file_size_mb = local_file.stat().st_size / (1024 * 1024)
        
        try:
            # Quick classification for emergency upload
            print(f"🤔 Classifying: {local_file.name}")
            if local_file.suffix.lower() in ['.mp4', '.mov', '.avi']:
                gdrive_folder = gdrive_folder or "VOX"
                category = "video"
                confidence = 90.0
            elif local_file.suffix.lower() in ['.mp3', '.wav', '.aup3']:
                gdrive_folder = gdrive_folder or "VOX"
                category = "audio" 
                confidence = 90.0
            else:
                gdrive_folder = gdrive_folder or "Reference Material"
                category = "document"
                confidence = 70.0
            
            # Get folder ID
            folders = self.get_drive_folders()
            folder_id = folders.get(gdrive_folder)
            
            if not folder_id:
                print(f"❌ Folder '{gdrive_folder}' not found in Google Drive")
                return None
            
            # Prepare file metadata
            file_name = new_name if new_name else local_file.name
            file_metadata = {
                'name': file_name,
                'parents': [folder_id],
                'description': f"Uploaded by AI Librarian | Confidence: {confidence:.1f}% | Category: {category}"
            }
            
            # Upload file
            media = MediaFileUpload(str(local_file))
            file_result = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, createdTime'
            ).execute()
            
            print(f"✅ Uploaded: {file_name} → {gdrive_folder}")
            upload_file_id = file_result.get('id')
            print(f"   File ID: {upload_file_id}")
            print(f"   Size: {file_size_mb:.1f} MB")
            print(f"   Classification: {category} ({confidence:.1f}%)")
            
            # Critical: Only proceed with auto-delete if metadata logging succeeds
            metadata_logged = False
            if auto_delete:
                try:
                    # Attempt metadata logging with success verification
                    success = self._log_metadata_operation(local_file, gdrive_folder, category, confidence, file_size_mb)
                    if success:
                        metadata_logged = True
                        print(f"📊 Metadata logged successfully")
                    else:
                        print(f"❌ Metadata logging failed - database save unsuccessful")
                        print(f"⚠️  File uploaded but NOT deleted locally due to logging failure")
                        print(f"📄 Manual cleanup may be needed: {local_path}")
                        # Return successful upload ID but don't delete
                        return upload_file_id
                        
                except Exception as e:
                    print(f"❌ Metadata logging exception: {e}")
                    print(f"⚠️  File uploaded but NOT deleted locally due to logging failure")
                    print(f"📄 Manual cleanup may be needed: {local_path}")
                    # Return successful upload ID but don't delete
                    return upload_file_id
            
            # Safe auto-delete: Only if metadata logging succeeded OR auto_delete is False
            if auto_delete and metadata_logged:
                try:
                    local_file.unlink()
                    print(f"🗑️  Deleted local file: {local_file.name}")
                    print(f"💾 Freed {file_size_mb:.1f} MB of local space")
                    print(f"✅ Complete: Upload + Metadata + Cleanup successful")
                    
                except Exception as e:
                    print(f"❌ Could not delete local file: {e}")
                    print(f"⚠️  Manual deletion required: {local_path}")
                    print(f"✅ Note: File is uploaded and metadata logged correctly")
                    # File is uploaded and logged, just deletion failed - still return success
            
            return upload_file_id
            
        except HttpError as error:
            print(f"❌ Upload error: {error}")
            return None
    
    def organize_downloads(self, downloads_dir: str = None, dry_run: bool = True) -> Dict:
        """Organize Downloads folder with AI classification to Google Drive"""
        if not downloads_dir:
            downloads_dir = Path.home() / "Downloads"
        else:
            downloads_dir = Path(downloads_dir)
        
        if not downloads_dir.exists():
            print(f"❌ Downloads directory not found: {downloads_dir}")
            return {}
        
        print(f"📁 Organizing Downloads: {downloads_dir}")
        print(f"🔍 Mode: {'DRY RUN' if dry_run else 'LIVE UPLOAD'}")
        
        results = {
            "processed": 0,
            "uploaded": 0,
            "errors": 0,
            "space_freed": 0
        }
        
        # Get large files first (over 100MB)
        large_files = []
        for file_path in downloads_dir.iterdir():
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb > 100:  # Files over 100MB
                    large_files.append((file_path, size_mb))
        
        # Sort by size (largest first) for maximum space recovery
        large_files.sort(key=lambda x: x[1], reverse=True)
        
        print(f"🎯 Found {len(large_files)} large files (>100MB)")
        
        for file_path, size_mb in large_files:
            results["processed"] += 1
            print(f"\n📄 Processing: {file_path.name} ({size_mb:.1f} MB)")
            
            if dry_run:
                # Just classify, don't upload
                try:
                    # Quick classification based on file type and name for emergency
                    if file_path.suffix.lower() in ['.mp4', '.mov', '.avi']:
                        target_folder = "VOX"
                        category = "video"
                        confidence = 90.0
                    elif file_path.suffix.lower() in ['.mp3', '.wav', '.aup3']:
                        target_folder = "VOX" 
                        category = "audio"
                        confidence = 90.0
                    else:
                        target_folder = "Reference Material"
                        category = "document"
                        confidence = 70.0
                    
                    print(f"   🔍 Would upload to: {target_folder}")
                    print(f"   🎯 Classification: {category} ({confidence:.1f}%)")
                    print(f"   💾 Would free: {size_mb:.1f} MB")
                    
                    results["uploaded"] += 1  # Count as would-be uploaded
                    results["space_freed"] += size_mb
                    
                except Exception as e:
                    print(f"   ❌ Classification error: {e}")
                    results["errors"] += 1
            else:
                # Actually upload with auto-deletion enabled
                file_id = self.upload_file(str(file_path), auto_delete=True)
                if file_id:
                    results["uploaded"] += 1
                    results["space_freed"] += size_mb
                else:
                    results["errors"] += 1
        
        # Summary
        print(f"\n📊 Organization Complete:")
        print(f"   Files processed: {results['processed']}")
        print(f"   {'Would upload' if dry_run else 'Uploaded'}: {results['uploaded']}")
        print(f"   Errors: {results['errors']}")
        print(f"   {'Potential' if dry_run else 'Actual'} space freed: {results['space_freed']:.1f} MB")
        
        return results
    
    def search_drive(self, query: str, folder: str = None) -> List[Dict]:
        """Search Google Drive files with AI understanding"""
        if not self.authenticated:
            print("❌ Not authenticated with Google Drive")
            return []
        
        try:
            # Build search query
            search_query = f"fullText contains '{query}' and trashed=false"
            if folder:
                folders = self.get_drive_folders()
                folder_id = folders.get(folder)
                if folder_id:
                    search_query += f" and '{folder_id}' in parents"
            
            # Execute search
            results = self.service.files().list(
                q=search_query,
                pageSize=20,
                fields="nextPageToken, files(id, name, size, createdTime, parents, mimeType, description)"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append({
                    'id': item['id'],
                    'name': item['name'],
                    'size': int(item.get('size', 0)),
                    'created': item.get('createdTime'),
                    'type': item.get('mimeType'),
                    'description': item.get('description', '')
                })
            
            print(f"🔍 Found {len(files)} files matching '{query}'")
            return files
            
        except HttpError as error:
            print(f"❌ Search error: {error}")
            return []
    
    def _map_category_to_folder(self, category: str) -> str:
        """Map AI classification category to Google Drive folder"""
        mapping = {
            "entertainment_industry": "VOX",
            "creative_production": "VOX", 
            "business_operations": "Reference Material",
            "reference_material": "Reference Material",
            "audio": "Music",
            "video": "VOX",
            "document": "Reference Material"
        }
        
        return mapping.get(category, "Reference Material")
    
    def _log_metadata_operation(self, local_file: Path, gdrive_folder: str, category: str, confidence: float, size_mb: float) -> bool:
        """Log upload operation to metadata system for tracking with success verification"""
        try:
            # Import metadata generator
            from metadata_generator import MetadataGenerator
            
            # Create metadata entry for the upload operation
            metadata_gen = MetadataGenerator(str(self.base_dir))
            
            # Analyze the file before upload (if it still exists)
            if local_file.exists():
                metadata = metadata_gen.analyze_file_comprehensive(local_file)
                
                # Add Google Drive specific metadata
                metadata.update({
                    'gdrive_upload': True,
                    'gdrive_folder': gdrive_folder,
                    'gdrive_category': category,
                    'gdrive_confidence': confidence,
                    'upload_timestamp': datetime.now().isoformat(),
                    'organization_status': 'Uploaded_to_GDrive',
                    'space_freed_mb': size_mb
                })
                
                # Critical: Verify metadata was actually saved
                success = metadata_gen.save_file_metadata(metadata)
                if success:
                    print(f"   📊 Metadata logged and verified")
                    return True
                else:
                    print(f"   ❌ Metadata save to database failed")
                    return False
            else:
                print(f"   ⚠️  File no longer exists for metadata logging")
                return False
            
        except Exception as e:
            print(f"   ❌ Metadata logging exception: {e}")
            return False
    
    def get_storage_info(self) -> Dict:
        """Get Google Drive storage information"""
        if not self.authenticated:
            return {}
        
        try:
            about = self.service.about().get(fields="storageQuota").execute()
            quota = about.get('storageQuota', {})
            
            total_gb = int(quota.get('limit', 0)) / (1024**3)
            used_gb = int(quota.get('usage', 0)) / (1024**3)
            available_gb = total_gb - used_gb
            
            return {
                'total_gb': total_gb,
                'used_gb': used_gb,
                'available_gb': available_gb,
                'usage_percent': (used_gb / total_gb) * 100 if total_gb > 0 else 0
            }
            
        except HttpError as error:
            print(f"❌ Error getting storage info: {error}")
            return {}

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Google Drive AI Librarian")
    parser.add_argument('command', choices=['auth', 'upload', 'organize', 'search', 'info'])
    parser.add_argument('--file', help='File path to upload')
    parser.add_argument('--folder', help='Target Google Drive folder')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--downloads', help='Downloads directory to organize')
    parser.add_argument('--live', action='store_true', help='Actually perform operations (not dry run)')
    parser.add_argument('--credentials', help='Path to Google credentials JSON file')
    
    args = parser.parse_args()
    
    # Initialize librarian
    librarian = GoogleDriveLibrarian()
    
    if args.command == 'auth':
        librarian.authenticate(args.credentials)
    
    elif args.command == 'upload':
        if not args.file:
            print("❌ --file required for upload")
            return
        if librarian.authenticate():
            librarian.upload_file(args.file, args.folder)
    
    elif args.command == 'organize':
        if librarian.authenticate():
            librarian.organize_downloads(args.downloads, dry_run=not args.live)
    
    elif args.command == 'search':
        if not args.query:
            print("❌ --query required for search")
            return
        if librarian.authenticate():
            results = librarian.search_drive(args.query, args.folder)
            for file in results:
                print(f"📄 {file['name']} ({file['size']/1024/1024:.1f} MB)")
    
    elif args.command == 'info':
        if librarian.authenticate():
            info = librarian.get_storage_info()
            if info:
                print(f"💾 Google Drive Storage:")
                print(f"   Total: {info['total_gb']:.1f} GB")
                print(f"   Used: {info['used_gb']:.1f} GB ({info['usage_percent']:.1f}%)")
                print(f"   Available: {info['available_gb']:.1f} GB")

if __name__ == "__main__":
    main()