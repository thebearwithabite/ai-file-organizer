#!/usr/bin/env python3
"""
Google Drive CLI - Easy interface for AI File Organizer Google Drive integration
ADHD-friendly commands for cloud file management
"""

import sys
import argparse
from pathlib import Path
from gdrive_librarian import GoogleDriveLibrarian

def cmd_auth(args):
    """Authenticate with Google Drive"""
    print("🔐 Google Drive Authentication")
    print("=" * 50)
    
    librarian = GoogleDriveLibrarian()
    
    if args.credentials:
        success = librarian.authenticate(args.credentials)
    else:
        success = librarian.authenticate()
    
    if success:
        # Test the connection and show storage info
        info = librarian.get_storage_info()
        if info:
            print(f"\n💾 Your Google Drive Storage:")
            print(f"   Total: {info['total_gb']:.1f} GB")
            print(f"   Used: {info['used_gb']:.1f} GB ({info['usage_percent']:.1f}%)")
            print(f"   Available: {info['available_gb']:.1f} GB")
            
            # Show folders
            folders = librarian.get_drive_folders()
            print(f"\n📁 Available Folders ({len(folders)}):")
            for name, folder_id in sorted(folders.items()):
                print(f"   • {name}")
    else:
        print("\n❌ Authentication failed")
        print("\n📝 Setup Instructions:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Google Drive API")
        print("4. Create OAuth2 credentials (Desktop application)")
        print("5. Download the JSON file")
        print("6. Run: python gdrive_cli.py auth --credentials path/to/credentials.json")

def cmd_emergency(args):
    """Emergency space recovery from Downloads"""
    print("🚨 Emergency Space Recovery")
    print("=" * 50)
    
    librarian = GoogleDriveLibrarian()
    if not librarian.authenticate():
        return
    
    # Show current local space
    import shutil
    total, used, free = shutil.disk_usage("/")
    free_gb = free / (1024**3)
    print(f"💾 Local Storage: {free_gb:.1f} GB free")
    
    # Organize Downloads with focus on large files
    results = librarian.organize_downloads(dry_run=not args.live)
    
    if not args.live:
        print(f"\n⚡ Emergency Plan:")
        print(f"   Run with --live to actually upload {results['space_freed']:.1f} MB")
        print(f"   This would free {results['space_freed']/1024:.1f} GB of space")
    else:
        print(f"\n✅ Emergency complete! Freed {results['space_freed']/1024:.1f} GB")

def cmd_organize(args):
    """Organize files with AI classification"""
    print("🤖 AI File Organization")
    print("=" * 50)
    
    librarian = GoogleDriveLibrarian()
    if not librarian.authenticate():
        return
    
    if args.file:
        # Single file upload
        file_id = librarian.upload_file(args.file, args.folder)
        if file_id:
            print(f"✅ Successfully uploaded to Google Drive")
        else:
            print(f"❌ Upload failed")
    else:
        # Organize Downloads folder
        downloads_dir = args.directory or str(Path.home() / "Downloads")
        results = librarian.organize_downloads(downloads_dir, dry_run=not args.live)
        
        if not args.live:
            print(f"\n🔍 DRY RUN RESULTS:")
            print(f"   Would process: {results['processed']} files")
            print(f"   Would upload: {results['uploaded']} files") 
            print(f"   Would free: {results['space_freed']:.1f} MB")
            print(f"\n💡 Add --live to actually perform uploads")

def cmd_search(args):
    """Search Google Drive with AI understanding"""
    print(f"🔍 Searching Google Drive: '{args.query}'")
    print("=" * 50)
    
    librarian = GoogleDriveLibrarian()
    if not librarian.authenticate():
        return
    
    results = librarian.search_drive(args.query, args.folder)
    
    if not results:
        print("No files found")
        return
    
    total_size = 0
    for i, file in enumerate(results, 1):
        size_mb = file['size'] / (1024 * 1024)
        total_size += size_mb
        created = file['created'][:10] if file['created'] else 'Unknown'
        
        print(f"{i:2d}. 📄 {file['name']}")
        print(f"    💾 {size_mb:.1f} MB | 📅 {created}")
        if file['description']:
            print(f"    📝 {file['description']}")
        print()
    
    print(f"📊 Total: {len(results)} files, {total_size:.1f} MB")

def cmd_status(args):
    """Show system status and storage info"""
    print("📊 Google Drive AI Librarian Status")
    print("=" * 50)
    
    librarian = GoogleDriveLibrarian()
    if not librarian.authenticate():
        return
    
    # Google Drive storage
    info = librarian.get_storage_info()
    if info:
        print(f"☁️  Google Drive Storage:")
        print(f"   Total: {info['total_gb']:.1f} GB")
        print(f"   Used: {info['used_gb']:.1f} GB ({info['usage_percent']:.1f}%)")
        print(f"   Available: {info['available_gb']:.1f} GB")
    
    # Local storage
    import shutil
    total, used, free = shutil.disk_usage("/")
    free_gb = free / (1024**3)
    total_gb = total / (1024**3)
    used_percent = (used / total) * 100
    
    print(f"\n💻 Local Storage:")
    print(f"   Total: {total_gb:.1f} GB")
    print(f"   Free: {free_gb:.1f} GB")
    print(f"   Used: {used_percent:.1f}%")
    
    # Downloads folder size
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        import os
        total_size = 0
        file_count = 0
        large_files = 0
        
        for root, dirs, files in os.walk(downloads):
            for file in files:
                file_path = Path(root) / file
                try:
                    size = file_path.stat().st_size
                    total_size += size
                    file_count += 1
                    if size > 100 * 1024 * 1024:  # > 100MB
                        large_files += 1
                except:
                    pass
        
        downloads_gb = total_size / (1024**3)
        print(f"\n📁 Downloads Folder:")
        print(f"   Size: {downloads_gb:.1f} GB")
        print(f"   Files: {file_count}")
        print(f"   Large files (>100MB): {large_files}")
        
        if free_gb < 5.0:
            print(f"\n⚠️  LOW DISK SPACE WARNING!")
            print(f"   Consider running: python gdrive_cli.py emergency --live")

def cmd_folders(args):
    """List and manage Google Drive folders"""
    print("📁 Google Drive Folders")
    print("=" * 50)
    
    librarian = GoogleDriveLibrarian()
    if not librarian.authenticate():
        return
    
    folders = librarian.get_drive_folders()
    
    if not folders:
        print("No folders found")
        return
    
    print(f"Found {len(folders)} folders:\n")
    
    for name, folder_id in sorted(folders.items()):
        print(f"📂 {name}")
        print(f"   ID: {folder_id}")
        print()
    
    # Show mapping to AI categories
    print("🤖 AI Category Mapping:")
    category_map = {
        "Entertainment Industry": "entertainment_industry",
        "VOX": "creative_production, video", 
        "Reference Material": "business_operations, documents",
        "Music": "audio",
        "SFX": "effects"
    }
    
    for folder, categories in category_map.items():
        if folder in folders:
            print(f"   {folder} ← {categories}")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Google Drive AI Librarian - ADHD-friendly cloud file organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First-time setup
  python gdrive_cli.py auth --credentials credentials.json
  
  # Emergency space recovery (dry run)
  python gdrive_cli.py emergency
  
  # Actually upload large files to free space
  python gdrive_cli.py emergency --live
  
  # Organize Downloads folder
  python gdrive_cli.py organize --live
  
  # Upload specific file
  python gdrive_cli.py organize --file document.pdf --folder "Reference Material"
  
  # Search for files
  python gdrive_cli.py search --query "contract" 
  
  # Check storage status
  python gdrive_cli.py status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Auth command
    auth_parser = subparsers.add_parser('auth', help='Authenticate with Google Drive')
    auth_parser.add_argument('--credentials', help='Path to Google credentials JSON file')
    auth_parser.set_defaults(func=cmd_auth)
    
    # Emergency command  
    emergency_parser = subparsers.add_parser('emergency', help='Emergency space recovery from Downloads')
    emergency_parser.add_argument('--live', action='store_true', help='Actually upload files (not dry run)')
    emergency_parser.set_defaults(func=cmd_emergency)
    
    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize files with AI classification')
    organize_parser.add_argument('--file', help='Specific file to upload')
    organize_parser.add_argument('--folder', help='Target Google Drive folder')
    organize_parser.add_argument('--directory', help='Directory to organize (default: Downloads)')
    organize_parser.add_argument('--live', action='store_true', help='Actually upload files (not dry run)')
    organize_parser.set_defaults(func=cmd_organize)
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search Google Drive files')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--folder', help='Limit search to specific folder')
    search_parser.set_defaults(func=cmd_search)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show storage status and system info')
    status_parser.set_defaults(func=cmd_status)
    
    # Folders command
    folders_parser = subparsers.add_parser('folders', help='List Google Drive folders')
    folders_parser.set_defaults(func=cmd_folders)
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        try:
            args.func(args)
        except KeyboardInterrupt:
            print("\n\n👋 Operation cancelled")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if hasattr(args, 'debug') and args.debug:
                import traceback
                traceback.print_exc()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()