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
import sqlite3
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
from archive_lifecycle_manager import ArchiveLifecycleManager
from path_config import paths

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

class GoogleDriveLibrarian:
    """AI-powered Google Drive file organizer with ADHD-friendly features"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else paths.get_path('documents')
        
        # Use dynamic path configuration
        self.credentials_file = paths.get_path('organizer_base') / "gdrive_credentials.json"
        self.token_file = paths.get_path('organizer_base') / "gdrive_token.pickle"
        
        # Create required directories
        paths.create_required_directories(verbose=False)
        
        # Initialize Google Drive service
        self.service = None
        self.authenticated = False
        
        # Initialize local AI classifier and archive manager
        self.classifier = FileClassificationEngine(str(self.base_dir))
        self.archive_manager = ArchiveLifecycleManager(str(self.base_dir))
        
        # RYAN_THOMSON_MASTER_WORKSPACE - Enhanced structure based on comprehensive ecosystem analysis
        self.gdrive_folders = {
            # 01_ENTERTAINMENT_MANAGEMENT - Primary Revenue Stream (70%+ of business)
            "entertainment_finn_active": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/2025_Active_Contracts",
            "entertainment_finn_remittances": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/Financial_Remittances", 
            "entertainment_finn_publicity": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/Publicity_Projects",
            "entertainment_finn_immigration": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/Immigration_Visa",
            "entertainment_other_clients": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Other_Clients",
            "entertainment_business_ops": "01_ENTERTAINMENT_MANAGEMENT/Business_Operations/Refinery_Management",
            "entertainment_sag_resources": "01_ENTERTAINMENT_MANAGEMENT/Business_Operations/SAG_AFTRA_Resources",
            "entertainment_templates": "01_ENTERTAINMENT_MANAGEMENT/Business_Operations/Industry_Templates",
            
            # 02_CREATIVE_PRODUCTIONS - Papers That Dream & AI Narratives
            "creative_tptd_episodes": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Episodes",
            "creative_tptd_scripts": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Scripts_Research", 
            "creative_tptd_audio": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Audio_Assets",
            "creative_tptd_production": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Production_Materials",
            "creative_ai_narratives": "02_CREATIVE_PRODUCTIONS/AI_Research_Narratives",
            "creative_alphago": "02_CREATIVE_PRODUCTIONS/AI_Research_Narratives/AlphaGo",
            "creative_ilya_papers": "02_CREATIVE_PRODUCTIONS/AI_Research_Narratives/Ilyas_31_Papers",
            "creative_future_projects": "02_CREATIVE_PRODUCTIONS/AI_Research_Narratives/Future_Projects",
            "creative_video_assets": "02_CREATIVE_PRODUCTIONS/Video_Audio_Assets",
            
            # 03_BUSINESS_OPERATIONS - Financial & Legal Backbone
            "business_financial_current": "03_BUSINESS_OPERATIONS/Financial_Records/2025_Current",
            "business_tax_accounting": "03_BUSINESS_OPERATIONS/Financial_Records/Tax_Accounting",
            "business_banking": "03_BUSINESS_OPERATIONS/Financial_Records/Banking_Statements", 
            "business_legal_contracts": "03_BUSINESS_OPERATIONS/Legal_Contracts",
            "business_operational": "03_BUSINESS_OPERATIONS/Operational_Documents",
            
            # 04_DEVELOPMENT_PROJECTS - AI Innovation & Tools
            "dev_ai_organizer": "04_DEVELOPMENT_PROJECTS/AI_File_Organizer",
            "dev_reddit_ai": "04_DEVELOPMENT_PROJECTS/Reddit_Research_AI",
            "dev_bear_threads": "04_DEVELOPMENT_PROJECTS/Bear_Threads",
            "dev_model_realignment": "04_DEVELOPMENT_PROJECTS/Model_Realignment",
            "dev_agent_zero": "04_DEVELOPMENT_PROJECTS/Agent_Zero",
            "dev_other_tools": "04_DEVELOPMENT_PROJECTS/Other_Tools",
            
            # 05_STAGING_WORKFLOW - ADHD-Friendly Processing Areas
            "staging_desktop": "05_STAGING_WORKFLOW/Desktop_Processing",
            "staging_downloads": "05_STAGING_WORKFLOW/Downloads_Sorting",
            "staging_weekly_review": "05_STAGING_WORKFLOW/Weekly_Review",
            "staging_uncertain": "05_STAGING_WORKFLOW/Uncertain_Classification",
            
            # 06_ARCHIVE - Historical Projects by Year
            "archive_2024": "06_ARCHIVE/2024_Projects",
            "archive_2023": "06_ARCHIVE/2023_Projects", 
            "archive_historical": "06_ARCHIVE/Historical",
            
            # Default fallback mappings
            "business_active": "03_BUSINESS_OPERATIONS/Financial_Records/2025_Current",
            "business_archive": "06_ARCHIVE/2024_Projects",
            
            # Category Mappings for Intelligent Classification
            "entertainment_industry": "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/2025_Active_Contracts",
            "financial_documents": "03_BUSINESS_OPERATIONS/Financial_Records/2025_Current",
            "creative_projects": "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Episodes",
            "development_projects": "04_DEVELOPMENT_PROJECTS/AI_File_Organizer",
            "visual_media": "02_CREATIVE_PRODUCTIONS/Video_Audio_Assets",
            "reference_documents": "01_ENTERTAINMENT_MANAGEMENT/Business_Operations/Industry_Templates"
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
            
            # CRITICAL: Record rollback information for emergency recovery
            rollback_logged = self._log_rollback_info(
                original_path=str(local_file),
                original_name=local_file.name,
                new_name=file_name,
                gdrive_folder=gdrive_folder,
                gdrive_file_id=upload_file_id,
                category=category,
                confidence=confidence
            )
            
            if not rollback_logged:
                print(f"⚠️ WARNING: Rollback information not logged - emergency recovery may be difficult")
            
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
    
    def upload_with_archive_awareness(self, local_path: str, auto_delete: bool = False, 
                                     force_stage: str = None) -> Dict:
        """
        Upload file to Google Drive with intelligent archive lifecycle management
        ADHD-friendly with clear reasoning and safe defaults
        """
        
        local_file = Path(local_path)
        if not local_file.exists():
            return {'error': 'File not found', 'path': local_path}
        
        print(f"🧠 Analyzing file for archive-aware upload: {local_file.name}")
        
        try:
            # Analyze file lifecycle to determine optimal Google Drive location
            analysis = self.archive_manager.analyze_file_lifecycle_stage(local_file)
            
            if 'error' in analysis:
                return {'error': f"Analysis failed: {analysis['error']}", 'path': local_path}
            
            # Determine Google Drive folder based on analysis
            primary_category = analysis['primary_category']
            lifecycle_stage = analysis.get('lifecycle_stage', 'active')
            adhd_importance = analysis.get('adhd_importance', 5)
            
            # Override stage if user specified
            if force_stage:
                lifecycle_stage = force_stage
                print(f"🔧 User override: Forcing stage to '{force_stage}'")
            
            # Map to actual Google Drive folder names based on category
            if primary_category == "entertainment_industry":
                if lifecycle_stage == "archive_candidate":
                    gdrive_folder_name = "2024_Projects"
                else:
                    gdrive_folder_name = "2025_Active_Contracts"  # Finn's active contracts
            elif primary_category == "financial_documents":
                gdrive_folder_name = "2025_Current"  # Current financial records
            elif primary_category == "creative_projects":
                gdrive_folder_name = "Episodes"  # Papers That Dream episodes
            elif primary_category == "development_projects":
                gdrive_folder_name = "AI_File_Organizer"
            elif primary_category == "visual_media":
                gdrive_folder_name = "Video_Audio_Assets"
            elif primary_category == "reference_documents":
                gdrive_folder_name = "Industry_Templates"
            else:
                # Fallback to staging
                gdrive_folder_name = "Uncertain_Classification"
            
            gdrive_folder_path = gdrive_folder_name
            
            # Show ADHD-friendly analysis summary
            print(f"📊 Archive Analysis Summary:")
            print(f"   🏷️  Category: {primary_category}")
            print(f"   📋 Lifecycle Stage: {lifecycle_stage}")
            print(f"   ⭐ ADHD Importance: {adhd_importance}/10")
            print(f"   📁 Google Drive Folder: {gdrive_folder_path}")
            print(f"   💡 Reasoning: {analysis.get('reasoning', 'Analysis complete')}")
            print(f"   ➡️  Action: {analysis.get('recommended_action', 'Upload recommended')}")
            
            # Generate standardized filename
            standardized_name = self._generate_standardized_filename(
                local_file, primary_category, analysis
            )
            
            # Upload with determined folder and standardized name
            upload_result = self.upload_file(
                local_path=str(local_file),
                gdrive_folder=gdrive_folder_path,
                new_name=standardized_name,
                auto_delete=auto_delete
            )
            
            if upload_result:
                return {
                    'success': True,
                    'file_id': upload_result,
                    'local_path': str(local_file),
                    'gdrive_folder': gdrive_folder_path,
                    'analysis': {
                        'category': primary_category,
                        'stage': lifecycle_stage,
                        'importance': adhd_importance,
                        'reasoning': analysis.get('reasoning', ''),
                        'action': analysis.get('recommended_action', '')
                    },
                    'auto_deleted': auto_delete
                }
            else:
                return {
                    'success': False,
                    'error': 'Upload failed',
                    'local_path': str(local_file)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'local_path': str(local_file)
            }
    
    def bulk_archive_upload(self, source_directory: str, file_extensions: List[str] = None,
                           max_files: int = 20, auto_delete: bool = False, dry_run: bool = True) -> Dict:
        """
        ADHD-friendly bulk upload with archive awareness
        Processes files in manageable batches with clear progress feedback
        """
        
        source_path = Path(source_directory)
        if not source_path.exists():
            return {'error': f'Source directory not found: {source_directory}'}
        
        # Default file extensions if none provided
        if not file_extensions:
            file_extensions = ['.pdf', '.docx', '.doc', '.txt', '.pages', '.xlsx', '.pptx']
        
        print(f"🚀 Starting bulk archive upload from: {source_path}")
        print(f"📋 Extensions: {file_extensions}")
        print(f"🎯 Max files: {max_files} (ADHD-friendly batch size)")
        print(f"🔄 Mode: {'Preview' if dry_run else 'Live Upload'}")
        print(f"🗑️  Auto-delete: {'Yes' if auto_delete else 'No'}")
        
        # Find eligible files
        eligible_files = []
        for ext in file_extensions:
            for file_path in source_path.rglob(f"*{ext}"):
                if file_path.is_file() and len(eligible_files) < max_files:
                    eligible_files.append(file_path)
        
        if not eligible_files:
            return {
                'success': True,
                'message': 'No eligible files found',
                'files_processed': 0
            }
        
        print(f"📂 Found {len(eligible_files)} eligible files")
        
        # Process files with archive awareness
        results = {
            'success': True,
            'files_processed': 0,
            'files_uploaded': 0,
            'files_skipped': 0,
            'errors': 0,
            'uploads': [],
            'dry_run': dry_run
        }
        
        for i, file_path in enumerate(eligible_files, 1):
            try:
                print(f"\n📄 Processing {i}/{len(eligible_files)}: {file_path.name}")
                
                if dry_run:
                    # Preview mode - analyze but don't upload
                    analysis = self.archive_manager.analyze_file_lifecycle_stage(file_path)
                    if 'error' not in analysis:
                        primary_category = analysis['primary_category']
                        lifecycle_stage = analysis.get('lifecycle_stage', 'active')
                        adhd_importance = analysis.get('adhd_importance', 5)
                        
                        # Determine target folder
                        gdrive_folder_key = f"{primary_category}_{lifecycle_stage}"
                        if gdrive_folder_key not in self.gdrive_folders:
                            gdrive_folder_key = f"{primary_category}_active"
                            if gdrive_folder_key not in self.gdrive_folders:
                                gdrive_folder_key = "business_active"
                        
                        gdrive_folder_path = self.gdrive_folders[gdrive_folder_key]
                        
                        print(f"   📁 Would upload to: {gdrive_folder_path}")
                        print(f"   ⭐ Importance: {adhd_importance}/10")
                        print(f"   📋 Stage: {lifecycle_stage}")
                        
                        results['uploads'].append({
                            'file': str(file_path),
                            'target_folder': gdrive_folder_path,
                            'category': primary_category,
                            'stage': lifecycle_stage,
                            'importance': adhd_importance,
                            'preview': True
                        })
                        
                        results['files_processed'] += 1
                    else:
                        print(f"   ⚠️ Analysis failed: {analysis.get('error', 'Unknown error')}")
                        results['errors'] += 1
                
                else:
                    # Live mode - actually upload
                    upload_result = self.upload_with_archive_awareness(
                        str(file_path), 
                        auto_delete=auto_delete
                    )
                    
                    if upload_result.get('success'):
                        results['uploads'].append(upload_result)
                        results['files_uploaded'] += 1
                        print(f"   ✅ Uploaded successfully")
                    else:
                        print(f"   ❌ Upload failed: {upload_result.get('error', 'Unknown error')}")
                        results['errors'] += 1
                    
                    results['files_processed'] += 1
                
                # ADHD-friendly progress update
                if i % 5 == 0:
                    print(f"🔄 Progress: {i}/{len(eligible_files)} files processed")
                
            except Exception as e:
                print(f"   ❌ Processing error: {e}")
                results['errors'] += 1
        
        # Final summary
        print(f"\n📊 Bulk Upload Summary:")
        print(f"   📂 Files processed: {results['files_processed']}")
        if not dry_run:
            print(f"   ✅ Files uploaded: {results['files_uploaded']}")
        print(f"   ❌ Errors: {results['errors']}")
        print(f"   🎯 Success rate: {((results['files_processed'] - results['errors']) / max(results['files_processed'], 1)) * 100:.1f}%")
        
        return results
    
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
    
    def _generate_standardized_filename(self, file_path: Path, category: str, analysis: Dict) -> str:
        """Generate standardized filename based on User's professional naming conventions"""
        
        original_name = file_path.stem.lower()
        file_extension = file_path.suffix
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Detect key content indicators
        indicators = analysis.get('content_indicators', [])
        content_text = ' '.join(indicators).lower()
        
        try:
            if category == "entertainment_industry":
                # Finn Wolfhard files: "WOLFHARD, FINN - [Type] - [Date]"
                if any(term in content_text for term in ['finn wolfhard', 'wolfhard', 'stranger things']):
                    if 'contract' in content_text or 'agreement' in content_text:
                        return f"WOLFHARD, FINN - Contract - {current_date}{file_extension}"
                    elif 'publicity' in content_text or 'schedule' in content_text:
                        return f"WOLFHARD, FINN - Publicity Schedule - {current_date}{file_extension}"
                    elif 'remittance' in content_text or 'payment' in content_text:
                        return f"WOLFHARD, FINN - Payment Report - {current_date}{file_extension}"
                    else:
                        return f"WOLFHARD, FINN - Document - {current_date}{file_extension}"
                
                # Other entertainment files
                elif 'resume' in original_name:
                    # Extract name if possible
                    name_parts = original_name.split(' ')
                    if len(name_parts) >= 2:
                        last_name = name_parts[0].upper()
                        first_name = name_parts[1].title()
                        return f"{last_name}, {first_name} - Resume - {current_date}{file_extension}"
                
                return f"Entertainment - {current_date}{file_extension}"
            
            elif category == "creative_projects":
                # Papers That Dream: "TPTD - Episode [X] - [Title]"
                if 'papers that dream' in content_text or 'episode' in content_text:
                    # Try to extract episode number
                    import re
                    episode_match = re.search(r'episode\s*(\d+)', original_name)
                    if episode_match:
                        ep_num = episode_match.group(1).zfill(2)
                        # Try to extract title or use generic
                        if 'alphago' in original_name:
                            return f"TPTD - Episode {ep_num} - AlphaGo Story{file_extension}"
                        elif 'attention' in original_name:
                            return f"TPTD - Episode {ep_num} - Attention Mechanism{file_extension}"
                        else:
                            return f"TPTD - Episode {ep_num} - Draft{file_extension}"
                    else:
                        return f"TPTD - Episode Draft - {current_date}{file_extension}"
                
                # Audio/Cue sheets: "TPTD - Audio - [Type] - [Date]"
                elif 'cue sheet' in original_name or 'audio' in content_text:
                    return f"TPTD - Audio Assets - {current_date}{file_extension}"
                
                return f"Creative Project - {current_date}{file_extension}"
            
            elif category == "financial_documents":
                # Business docs: "[Company] - [Type] - [Date]"
                if 'refinery' in content_text or 'tax' in content_text:
                    if 'tax return' in content_text:
                        year = datetime.now().year
                        return f"Refinery Management LLC - Tax Return {year}{file_extension}"
                    elif 'payroll' in content_text:
                        return f"Refinery Management LLC - Payroll - {current_date}{file_extension}"
                    else:
                        return f"Refinery Management LLC - Financial - {current_date}{file_extension}"
                
                elif 'palantir' in original_name:
                    return f"Palantir - Business Update - {current_date}{file_extension}"
                
                return f"Financial Document - {current_date}{file_extension}"
            
            elif category == "development_projects":
                # Development: "[Project] - [Type] - [Date]"
                if 'package.json' in original_name or 'bear' in original_name or 'threads' in original_name:
                    return f"Bear Threads - Config - {current_date}{file_extension}"
                elif 'chatgpt' in original_name or 'monitoring' in original_name:
                    return f"Model Realignment - System Design - {current_date}{file_extension}"
                else:
                    return f"Development Project - {current_date}{file_extension}"
            
            elif category == "reference_documents":
                # Research papers: "[Topic] - Research Paper - [Date]"
                if 'alphago' in original_name or 'mastering' in original_name:
                    return f"AlphaGo - Research Paper - DeepMind{file_extension}"
                elif 'grok' in original_name:
                    return f"Grok - Documentation - {current_date}{file_extension}"
                elif any(term in original_name for term in ['2506.10943', 'arxiv', 'pdf']):
                    return f"Research Paper - {current_date}{file_extension}"
                else:
                    return f"Reference Material - {current_date}{file_extension}"
            
            elif category == "visual_media":
                # Media: "[Type] - [Description] - [Date]"
                if 'screenshot' in original_name or 'screencapture' in original_name:
                    if 'substack' in original_name:
                        return f"Screenshot - Substack Article - {current_date}{file_extension}"
                    else:
                        return f"Screenshot - {current_date}{file_extension}"
                elif 'framer' in original_name:
                    return f"Framer - Design Plan - {current_date}{file_extension}"
                else:
                    return f"Visual Asset - {current_date}{file_extension}"
            
            else:
                # Default standardization
                return f"Document - {current_date}{file_extension}"
                
        except Exception as e:
            # Fallback to safe default
            print(f"   ⚠️ Filename standardization error: {e}")
            return f"Document - {current_date}{file_extension}"
    
    def _log_rollback_info(self, original_path: str, original_name: str, new_name: str, 
                          gdrive_folder: str, gdrive_file_id: str, category: str, confidence: float) -> bool:
        """Log complete rollback information for emergency file recovery"""
        try:
            # Create rollback database if it doesn't exist
            rollback_db_path = paths.get_path('organizer_base') / 'file_rollback.db'
            
            with sqlite3.connect(rollback_db_path) as conn:
                # Create rollback table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_rollback (
                        rollback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation_timestamp TEXT,
                        original_path TEXT,
                        original_filename TEXT,
                        new_filename TEXT,
                        gdrive_folder TEXT,
                        gdrive_file_id TEXT,
                        category TEXT,
                        confidence REAL,
                        rollback_status TEXT DEFAULT 'active',
                        notes TEXT
                    )
                """)
                
                # Insert rollback record
                conn.execute("""
                    INSERT INTO file_rollback 
                    (operation_timestamp, original_path, original_filename, new_filename, 
                     gdrive_folder, gdrive_file_id, category, confidence, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    original_path,
                    original_name,
                    new_name,
                    gdrive_folder,
                    gdrive_file_id,
                    category,
                    confidence,
                    f"Auto-renamed: '{original_name}' → '{new_name}' | Folder: {gdrive_folder}"
                ))
                
                conn.commit()
                print(f"   📋 Rollback info logged: {rollback_db_path.name}")
                return True
                
        except Exception as e:
            print(f"   ❌ Rollback logging failed: {e}")
            return False
    
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
    
    def create_folder_structure(self) -> Dict:
        """Create the complete RYAN_THOMSON_MASTER_WORKSPACE folder structure in Google Drive"""
        if not self.authenticated:
            return {'error': 'Not authenticated with Google Drive'}
        
        try:
            print("🚀 Creating RYAN_THOMSON_MASTER_WORKSPACE structure...")
            created_folders = {}
            folder_hierarchy = {}
            
            # First, get all existing folders to avoid duplicates
            existing_folders = self.get_drive_folders()
            
            # Create the main workspace folder first
            workspace_name = "RYAN_THOMSON_MASTER_WORKSPACE"
            workspace_id = existing_folders.get(workspace_name)
            
            if not workspace_id:
                workspace_metadata = {'name': workspace_name, 'mimeType': 'application/vnd.google-apps.folder'}
                workspace_result = self.service.files().create(body=workspace_metadata, fields='id').execute()
                workspace_id = workspace_result['id']
                print(f"📁 Created main workspace: {workspace_name}")
            else:
                print(f"📁 Found existing workspace: {workspace_name}")
            
            folder_hierarchy['root'] = workspace_id
            
            # Define the complete folder structure
            folder_structure = [
                # 01_ENTERTAINMENT_MANAGEMENT
                "01_ENTERTAINMENT_MANAGEMENT",
                "01_ENTERTAINMENT_MANAGEMENT/Current_Clients",
                "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard",
                "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/2025_Active_Contracts",
                "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/Financial_Remittances",
                "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/Publicity_Projects", 
                "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Finn_Wolfhard/Immigration_Visa",
                "01_ENTERTAINMENT_MANAGEMENT/Current_Clients/Other_Clients",
                "01_ENTERTAINMENT_MANAGEMENT/Business_Operations",
                "01_ENTERTAINMENT_MANAGEMENT/Business_Operations/Refinery_Management",
                "01_ENTERTAINMENT_MANAGEMENT/Business_Operations/SAG_AFTRA_Resources",
                "01_ENTERTAINMENT_MANAGEMENT/Business_Operations/Industry_Templates",
                
                # 02_CREATIVE_PRODUCTIONS
                "02_CREATIVE_PRODUCTIONS",
                "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream",
                "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Episodes",
                "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Scripts_Research",
                "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Audio_Assets",
                "02_CREATIVE_PRODUCTIONS/The_Papers_That_Dream/Production_Materials",
                "02_CREATIVE_PRODUCTIONS/AI_Research_Narratives",
                "02_CREATIVE_PRODUCTIONS/AI_Research_Narratives/AlphaGo",
                "02_CREATIVE_PRODUCTIONS/AI_Research_Narratives/Ilyas_31_Papers",
                "02_CREATIVE_PRODUCTIONS/AI_Research_Narratives/Future_Projects",
                "02_CREATIVE_PRODUCTIONS/Video_Audio_Assets",
                
                # 03_BUSINESS_OPERATIONS
                "03_BUSINESS_OPERATIONS",
                "03_BUSINESS_OPERATIONS/Financial_Records",
                "03_BUSINESS_OPERATIONS/Financial_Records/2025_Current",
                "03_BUSINESS_OPERATIONS/Financial_Records/Tax_Accounting",
                "03_BUSINESS_OPERATIONS/Financial_Records/Banking_Statements",
                "03_BUSINESS_OPERATIONS/Legal_Contracts",
                "03_BUSINESS_OPERATIONS/Operational_Documents",
                
                # 04_DEVELOPMENT_PROJECTS
                "04_DEVELOPMENT_PROJECTS",
                "04_DEVELOPMENT_PROJECTS/AI_File_Organizer",
                "04_DEVELOPMENT_PROJECTS/Reddit_Research_AI",
                "04_DEVELOPMENT_PROJECTS/Bear_Threads",
                "04_DEVELOPMENT_PROJECTS/Model_Realignment",
                "04_DEVELOPMENT_PROJECTS/Agent_Zero",
                "04_DEVELOPMENT_PROJECTS/Other_Tools",
                
                # 05_STAGING_WORKFLOW
                "05_STAGING_WORKFLOW",
                "05_STAGING_WORKFLOW/Desktop_Processing",
                "05_STAGING_WORKFLOW/Downloads_Sorting",
                "05_STAGING_WORKFLOW/Weekly_Review",
                "05_STAGING_WORKFLOW/Uncertain_Classification",
                
                # 06_ARCHIVE
                "06_ARCHIVE",
                "06_ARCHIVE/2024_Projects",
                "06_ARCHIVE/2023_Projects",
                "06_ARCHIVE/Historical"
            ]
            
            # Create each folder in the hierarchy
            for folder_path in folder_structure:
                parts = folder_path.split('/')
                parent_id = workspace_id
                current_path = ""
                
                for part in parts:
                    current_path = f"{current_path}/{part}" if current_path else part
                    
                    # Check if this folder already exists
                    if current_path not in folder_hierarchy:
                        folder_metadata = {
                            'name': part,
                            'parents': [parent_id],
                            'mimeType': 'application/vnd.google-apps.folder'
                        }
                        
                        try:
                            result = self.service.files().create(body=folder_metadata, fields='id').execute()
                            folder_id = result['id']
                            folder_hierarchy[current_path] = folder_id
                            created_folders[current_path] = folder_id
                            print(f"  📁 Created: {current_path}")
                            
                        except HttpError as e:
                            # Folder might already exist
                            print(f"  ⚠️ Folder may already exist: {current_path} - {e}")
                            continue
                    
                    parent_id = folder_hierarchy.get(current_path, parent_id)
            
            # Update folder mappings with actual IDs for future use
            folder_id_mappings = {}
            for key, path in self.gdrive_folders.items():
                full_path = path
                if full_path in folder_hierarchy:
                    folder_id_mappings[key] = folder_hierarchy[full_path]
            
            print(f"\n✅ RYAN_THOMSON_MASTER_WORKSPACE structure created!")
            print(f"📊 Created {len(created_folders)} new folders")
            print(f"🏗️ Total structure: {len(folder_structure)} folders")
            
            return {
                'success': True,
                'workspace_id': workspace_id,
                'created_folders': len(created_folders),
                'total_folders': len(folder_structure),
                'folder_mappings': folder_id_mappings
            }
            
        except Exception as e:
            print(f"❌ Error creating folder structure: {e}")
            return {'error': str(e)}
    
    def get_rollback_history(self, limit: int = 50) -> List[Dict]:
        """Get recent file operations that can be rolled back"""
        try:
            rollback_db_path = paths.get_path('organizer_base') / 'file_rollback.db'
            
            if not rollback_db_path.exists():
                return []
            
            with sqlite3.connect(rollback_db_path) as conn:
                cursor = conn.execute("""
                    SELECT rollback_id, operation_timestamp, original_path, 
                           original_filename, new_filename, gdrive_folder, 
                           gdrive_file_id, category, rollback_status, notes
                    FROM file_rollback 
                    WHERE rollback_status = 'active'
                    ORDER BY operation_timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                return [dict(zip([col[0] for col in cursor.description], row)) 
                        for row in cursor.fetchall()]
                        
        except Exception as e:
            print(f"❌ Error getting rollback history: {e}")
            return []
    
    def execute_rollback(self, rollback_id: int, download_to_original_location: bool = False) -> Dict:
        """Execute emergency rollback of a file operation"""
        try:
            rollback_db_path = paths.get_path('organizer_base') / 'file_rollback.db'
            
            if not rollback_db_path.exists():
                return {'error': 'No rollback database found'}
            
            with sqlite3.connect(rollback_db_path) as conn:
                # Get rollback record
                cursor = conn.execute("""
                    SELECT * FROM file_rollback WHERE rollback_id = ? AND rollback_status = 'active'
                """, (rollback_id,))
                
                record = cursor.fetchone()
                if not record:
                    return {'error': f'Rollback record {rollback_id} not found or already processed'}
                
                # Extract record data
                columns = [col[0] for col in cursor.description]
                rollback_data = dict(zip(columns, record))
                
                gdrive_file_id = rollback_data['gdrive_file_id']
                original_path = rollback_data['original_path']
                original_filename = rollback_data['original_filename']
                
                print(f"🔄 Rolling back: {rollback_data['new_filename']} → {original_filename}")
                
                if download_to_original_location:
                    # Download file back to original location with original name
                    original_file_path = Path(original_path).parent / original_filename
                    
                    # Download from Google Drive
                    request = self.service.files().get_media(fileId=gdrive_file_id)
                    file_io = io.BytesIO()
                    downloader = MediaIoBaseDownload(file_io, request)
                    
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                    
                    # Write to original location
                    with open(original_file_path, 'wb') as f:
                        f.write(file_io.getvalue())
                    
                    print(f"✅ File restored to: {original_file_path}")
                
                # Rename file in Google Drive back to original name
                try:
                    self.service.files().update(
                        fileId=gdrive_file_id,
                        body={'name': original_filename}
                    ).execute()
                    print(f"✅ Google Drive file renamed back to: {original_filename}")
                except Exception as e:
                    print(f"⚠️ Could not rename in Google Drive: {e}")
                
                # Mark rollback as executed
                conn.execute("""
                    UPDATE file_rollback 
                    SET rollback_status = 'executed', 
                        notes = notes || ' | ROLLBACK EXECUTED: ' || ?
                    WHERE rollback_id = ?
                """, (datetime.now().isoformat(), rollback_id))
                
                conn.commit()
                
                return {
                    'success': True,
                    'rollback_id': rollback_id,
                    'original_filename': original_filename,
                    'restored_to_original_location': download_to_original_location
                }
                
        except Exception as e:
            return {'error': f'Rollback failed: {e}'}
    
    def export_rollback_database_to_csv(self, output_path: str = None) -> str:
        """Export complete rollback database to CSV for spreadsheet backup"""
        try:
            rollback_db_path = paths.get_path('organizer_base') / 'file_rollback.db'
            
            if not rollback_db_path.exists():
                return "No rollback database found"
            
            # Default output path
            if not output_path:
                output_path = str(paths.get_path('organizer_base') / f'rollback_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            
            with sqlite3.connect(rollback_db_path) as conn:
                cursor = conn.execute("""
                    SELECT rollback_id, operation_timestamp, original_path, 
                           original_filename, new_filename, gdrive_folder, 
                           gdrive_file_id, category, confidence, rollback_status, notes
                    FROM file_rollback 
                    ORDER BY operation_timestamp DESC
                """)
                
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow([
                        'Rollback_ID', 'Timestamp', 'Original_Path', 'Original_Filename',
                        'New_Filename', 'GDrive_Folder', 'GDrive_File_ID', 'Category',
                        'Confidence', 'Rollback_Status', 'Notes'
                    ])
                    
                    # Write data
                    writer.writerows(cursor.fetchall())
                
                return output_path
                
        except Exception as e:
            return f"CSV export failed: {e}"
    
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
    """Enhanced command line interface with archive awareness"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Drive AI Librarian with Archive Management')
    parser.add_argument('command', choices=[
        'auth', 'upload', 'archive-upload', 'bulk-upload', 'organize', 'search', 'info', 'create-folders', 'status',
        'rollback-history', 'rollback', 'export-rollback-csv'
    ], help='Command to execute')
    
    parser.add_argument('--file', help='Single file to upload')
    parser.add_argument('--directory', help='Directory for bulk operations')
    parser.add_argument('--folder', help='Google Drive folder name (for manual upload)')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--stage', choices=['active', 'archive_candidate', 'deep_storage_candidate'], 
                       help='Force specific lifecycle stage')
    parser.add_argument('--extensions', nargs='+', default=['.pdf', '.docx', '.doc', '.txt', '.pages'],
                       help='File extensions to process')
    parser.add_argument('--max-files', type=int, default=20, help='Maximum files to process (ADHD-friendly)')
    parser.add_argument('--auto-delete', action='store_true', help='Delete local file after successful upload')
    parser.add_argument('--live', action='store_true', help='Execute operations (not dry run)')
    parser.add_argument('--credentials', help='Path to Google credentials JSON file')
    parser.add_argument('--rollback-id', type=int, help='Rollback ID to execute')
    parser.add_argument('--download', action='store_true', help='Download file to original location during rollback')
    
    args = parser.parse_args()
    
    print("🚀 Google Drive AI Librarian - Archive Edition")
    print("=" * 50)
    
    librarian = GoogleDriveLibrarian()
    
    if args.command == 'auth':
        if librarian.authenticate(args.credentials):
            print("✅ Successfully authenticated with Google Drive")
        else:
            print("❌ Authentication failed")
    
    elif args.command == 'upload':
        if not args.file:
            print("❌ --file required for upload")
            return
        
        if not librarian.authenticate():
            print("❌ Authentication required")
            return
        
        result = librarian.upload_file(args.file, args.folder, auto_delete=args.auto_delete)
        if result:
            print(f"✅ Upload successful: {result}")
        else:
            print("❌ Upload failed")
    
    elif args.command == 'archive-upload':
        if not args.file:
            print("❌ --file required for archive-aware upload")
            return
        
        if not librarian.authenticate():
            print("❌ Authentication required")
            return
        
        result = librarian.upload_with_archive_awareness(
            args.file, 
            auto_delete=args.auto_delete,
            force_stage=args.stage
        )
        
        if result.get('success'):
            print(f"🎉 Archive-aware upload successful!")
            analysis = result.get('analysis', {})
            print(f"📁 Uploaded to: {result.get('gdrive_folder')}")
            print(f"🏷️  Category: {analysis.get('category')}")
            print(f"📋 Lifecycle Stage: {analysis.get('stage')}")
            print(f"⭐ Importance: {analysis.get('importance')}/10")
        else:
            print(f"❌ Archive upload failed: {result.get('error')}")
    
    elif args.command == 'bulk-upload':
        if not args.directory:
            print("❌ --directory required for bulk upload")
            return
        
        if not librarian.authenticate():
            print("❌ Authentication required")
            return
        
        result = librarian.bulk_archive_upload(
            args.directory,
            file_extensions=args.extensions,
            max_files=args.max_files,
            auto_delete=args.auto_delete,
            dry_run=not args.live
        )
        
        if result.get('success'):
            print(f"🎉 Bulk upload completed!")
            if not args.live:
                print(f"📋 Preview: {result.get('files_processed')} files analyzed")
            else:
                print(f"✅ Uploaded: {result.get('files_uploaded')} files")
        else:
            print(f"❌ Bulk upload failed: {result.get('error')}")
    
    elif args.command == 'organize':
        if not librarian.authenticate():
            print("❌ Authentication required")
            return
        
        result = librarian.organize_downloads(args.directory, dry_run=not args.live)
        print(f"📊 Organization complete")
    
    elif args.command == 'search':
        if not args.query:
            print("❌ --query required for search")
            return
        if librarian.authenticate():
            results = librarian.search_drive(args.query, args.folder)
            for file in results:
                print(f"📄 {file['name']} ({file['size']/1024/1024:.1f} MB)")
    
    elif args.command == 'create-folders':
        if not librarian.authenticate():
            print("❌ Authentication required")
            return
        
        librarian.create_folder_structure()
        print("✅ Enhanced folder structure created with archive organization")
    
    elif args.command == 'info':
        if librarian.authenticate():
            info = librarian.get_storage_info()
            if info:
                print(f"💾 Google Drive Storage:")
                print(f"   Total: {info['total_gb']:.1f} GB")
                print(f"   Used: {info['used_gb']:.1f} GB ({info['usage_percent']:.1f}%)")
                print(f"   Available: {info['available_gb']:.1f} GB")
    
    elif args.command == 'status':
        if librarian.authenticate():
            print("✅ Google Drive connection: Active")
            print("🗃️  Archive-aware upload: Available")
            print("📊 Lifecycle analysis: Enabled")
            print("🧠 ADHD-friendly batching: Enabled")
        else:
            print("❌ Google Drive connection: Failed")
    
    elif args.command == 'rollback-history':
        if not librarian.authenticate():
            print("❌ Authentication required")
            return
        
        history = librarian.get_rollback_history(limit=20)
        
        if history:
            print(f"📋 Rollback History ({len(history)} recent operations):")
            print("=" * 80)
            for record in history:
                print(f"ID: {record['rollback_id']} | {record['operation_timestamp'][:19]}")
                print(f"   Original: {record['original_filename']}")
                print(f"   Renamed:  {record['new_filename']}")
                print(f"   Folder:   {record['gdrive_folder']}")
                print(f"   GDrive ID: {record['gdrive_file_id']}")
                print()
        else:
            print("📋 No rollback history found")
    
    elif args.command == 'rollback':
        if not args.rollback_id:
            print("❌ --rollback-id required for rollback")
            return
            
        if not librarian.authenticate():
            print("❌ Authentication required") 
            return
        
        result = librarian.execute_rollback(args.rollback_id, args.download)
        
        if result.get('success'):
            print(f"✅ Rollback successful!")
            print(f"   File renamed back to: {result['original_filename']}")
            if result['restored_to_original_location']:
                print(f"   File downloaded to original location")
        else:
            print(f"❌ Rollback failed: {result.get('error')}")
    
    elif args.command == 'export-rollback-csv':
        csv_path = librarian.export_rollback_database_to_csv(args.file)
        
        if csv_path.endswith('.csv'):
            print(f"✅ Rollback database exported to CSV:")
            print(f"   📄 {csv_path}")
            print(f"   📊 Complete backup of all file operations")
            print(f"   🔄 Import into Excel/Sheets for analysis")
        else:
            print(f"❌ Export failed: {csv_path}")

if __name__ == "__main__":
    main()