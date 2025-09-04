#!/usr/bin/env python3
"""
Google Drive Staging for Large Directories
Moves entire directories to Google Drive for testing and storage management
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import datetime
import subprocess

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def stage_directory_to_gdrive(source_dir: Path, staging_name: str = None) -> bool:
    """Stage an entire directory to Google Drive"""
    
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return False
    
    # Get directory size
    result = subprocess.run(['du', '-sh', str(source_dir)], capture_output=True, text=True)
    dir_size = result.stdout.split()[0] if result.stdout else "unknown"
    
    print(f"📦 Staging Directory to Google Drive")
    print(f"=" * 50)
    print(f"📁 Source: {source_dir}")
    print(f"💾 Size: {dir_size}")
    
    # Create staging name if not provided
    if not staging_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        staging_name = f"STAGED_{source_dir.name}_{timestamp}"
    
    print(f"🏷️ Staging name: {staging_name}")
    
    try:
        from gdrive_librarian import GoogleDriveAILibrarian
        
        # Initialize Google Drive connection
        librarian = GoogleDriveAILibrarian()
        
        # Create staging folder in Google Drive
        staging_folder_id = librarian.service.files().create(
            body={
                'name': staging_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
        ).execute().get('id')
        
        print(f"📂 Created staging folder: {staging_name}")
        
        # Count files to upload
        file_count = sum(1 for f in source_dir.rglob('*') if f.is_file())
        print(f"📄 Files to upload: {file_count}")
        
        # Upload directory structure
        uploaded_count = 0
        failed_count = 0
        
        def upload_recursive(local_path: Path, gdrive_parent_id: str):
            nonlocal uploaded_count, failed_count
            
            for item in local_path.iterdir():
                if item.is_file():
                    try:
                        # Upload file
                        media = librarian.MediaFileUpload(str(item), resumable=True)
                        file_metadata = {
                            'name': item.name,
                            'parents': [gdrive_parent_id]
                        }
                        
                        librarian.service.files().create(
                            body=file_metadata,
                            media_body=media
                        ).execute()
                        
                        uploaded_count += 1
                        if uploaded_count % 10 == 0:
                            print(f"   📤 Uploaded {uploaded_count}/{file_count} files...")
                        
                    except Exception as e:
                        failed_count += 1
                        print(f"   ❌ Failed to upload {item.name}: {e}")
                
                elif item.is_dir():
                    try:
                        # Create subdirectory
                        subfolder = librarian.service.files().create(
                            body={
                                'name': item.name,
                                'mimeType': 'application/vnd.google-apps.folder',
                                'parents': [gdrive_parent_id]
                            }
                        ).execute()
                        
                        # Recursively upload subdirectory
                        upload_recursive(item, subfolder.get('id'))
                        
                    except Exception as e:
                        print(f"   ❌ Failed to create folder {item.name}: {e}")
        
        # Start upload
        print(f"🚀 Starting upload...")
        upload_recursive(source_dir, staging_folder_id)
        
        print(f"\n📊 Upload Summary:")
        print(f"   ✅ Uploaded: {uploaded_count} files")
        print(f"   ❌ Failed: {failed_count} files")
        print(f"   📂 Google Drive folder: {staging_name}")
        
        if uploaded_count > 0:
            print(f"\n💡 Next steps:")
            print(f"   1. Verify files in Google Drive")
            print(f"   2. Test file accessibility")
            print(f"   3. Delete local directory to free {dir_size}")
            return True
        else:
            print(f"❌ No files were uploaded successfully")
            return False
            
    except ImportError:
        print(f"❌ Google Drive librarian not available")
        return False
    except Exception as e:
        print(f"❌ Staging failed: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Stage directories to Google Drive")
    parser.add_argument('directory', help='Directory to stage')
    parser.add_argument('--name', help='Staging folder name (optional)')
    parser.add_argument('--delete-after', action='store_true', 
                       help='Delete local directory after successful staging')
    
    args = parser.parse_args()
    
    source_dir = Path(args.directory).expanduser()
    
    print(f"🎯 Staging {source_dir} to Google Drive...")
    
    success = stage_directory_to_gdrive(source_dir, args.name)
    
    if success and args.delete_after:
        confirm = input(f"\n⚠️ Delete local directory {source_dir}? (yes/no): ")
        if confirm.lower() == 'yes':
            shutil.rmtree(source_dir)
            print(f"🗑️ Local directory deleted: {source_dir}")
        else:
            print(f"📁 Local directory preserved")

if __name__ == "__main__":
    main()