#!/usr/bin/env python3
"""
Test Audacity Upload Setup
Verifies that everything is ready for the safe upload process

This script checks:
1. Google Drive authentication
2. File accessibility
3. Required permissions
4. Estimated upload time

Run this BEFORE running the main upload script.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

def test_imports():
    """Test that all required modules are available"""
    print("🔍 Testing imports...")
    
    try:
        from google_drive_auth import GoogleDriveAuth
        print("✅ google_drive_auth module available")
        
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
        print("✅ Google API client available")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return False

def test_google_drive_auth():
    """Test Google Drive authentication"""
    print("\n🔐 Testing Google Drive authentication...")
    
    try:
        from google_drive_auth import GoogleDriveAuth
        auth = GoogleDriveAuth()
        
        # Test authentication
        test_results = auth.test_authentication()
        
        if test_results['success']:
            print("✅ Google Drive authentication successful")
            print(f"   👤 User: {test_results['user_name']} ({test_results['user_email']})")
            print(f"   💾 Free storage: {test_results['free_storage_gb']:.1f} GB")
            return True, test_results
        else:
            print("❌ Google Drive authentication failed")
            print(f"   Error: {test_results.get('error', 'Unknown')}")
            return False, test_results
            
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False, {'error': str(e)}

def test_file_access():
    """Test access to Audacity files"""
    print("\n📁 Testing file access...")
    
    files_to_check = [
        Path("/Users/user/Library/Application Support/audacity/CloudProjects/AlphaGo-Checkpoint Final.aup3"),
        Path("/Users/user/Library/Application Support/audacity/CloudProjects/CSC.aup3")
    ]
    
    total_size_mb = 0
    accessible_files = 0
    
    for file_path in files_to_check:
        print(f"\n   📄 Checking: {file_path.name}")
        
        if not file_path.exists():
            print(f"   ❌ File not found: {file_path}")
            continue
        
        if not os.access(file_path, os.R_OK):
            print(f"   ❌ File not readable: {file_path}")
            continue
        
        try:
            stat_info = file_path.stat()
            size_mb = stat_info.st_size / (1024 * 1024)
            total_size_mb += size_mb
            accessible_files += 1
            
            print(f"   ✅ Size: {size_mb:.1f} MB ({stat_info.st_size:,} bytes)")
            print(f"   📅 Modified: {datetime.fromtimestamp(stat_info.st_mtime)}")
            
        except Exception as e:
            print(f"   ❌ Error reading file info: {e}")
    
    print(f"\n📊 Summary:")
    print(f"   📁 Accessible files: {accessible_files}/{len(files_to_check)}")
    print(f"   💾 Total size: {total_size_mb:.1f} MB ({total_size_mb/1024:.2f} GB)")
    
    return accessible_files == len(files_to_check), total_size_mb

def estimate_upload_time(size_mb, connection_speed_mbps=50):
    """Estimate upload time based on file size"""
    print(f"\n⏱️  Upload time estimation:")
    
    # Convert to bits and calculate
    size_bits = size_mb * 8 * 1024 * 1024
    upload_speed_bps = connection_speed_mbps * 1024 * 1024
    
    estimated_seconds = size_bits / upload_speed_bps
    
    hours = int(estimated_seconds // 3600)
    minutes = int((estimated_seconds % 3600) // 60)
    seconds = int(estimated_seconds % 60)
    
    print(f"   📊 File size: {size_mb:.1f} MB")
    print(f"   🌐 Assumed connection: {connection_speed_mbps} Mbps")
    
    if hours > 0:
        print(f"   ⏱️  Estimated time: {hours}h {minutes}m {seconds}s")
    elif minutes > 0:
        print(f"   ⏱️  Estimated time: {minutes}m {seconds}s")
    else:
        print(f"   ⏱️  Estimated time: {seconds}s")
    
    return estimated_seconds

def check_storage_space(drive_results, total_size_mb):
    """Check if there's enough storage space"""
    print(f"\n💾 Storage space check:")
    
    if not drive_results.get('success'):
        print("   ❌ Cannot check storage (authentication failed)")
        return False
    
    free_space_gb = drive_results.get('free_storage_gb', 0)
    needed_space_gb = total_size_mb / 1024
    
    print(f"   📊 Available space: {free_space_gb:.1f} GB")
    print(f"   📊 Required space: {needed_space_gb:.2f} GB")
    
    if free_space_gb > needed_space_gb:
        remaining_space = free_space_gb - needed_space_gb
        print(f"   ✅ Sufficient space (will have {remaining_space:.1f} GB remaining)")
        return True
    else:
        shortage = needed_space_gb - free_space_gb
        print(f"   ❌ Insufficient space (need {shortage:.2f} GB more)")
        return False

def main():
    """Run all setup tests"""
    print("🧪 Audacity Upload Setup Test")
    print("=" * 50)
    print("This will verify everything is ready for safe upload")
    print()
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Setup incomplete - fix imports first")
        return False
    
    # Test 2: Google Drive authentication
    auth_success, drive_results = test_google_drive_auth()
    if not auth_success:
        print("\n❌ Setup incomplete - fix Google Drive authentication first")
        return False
    
    # Test 3: File access
    files_accessible, total_size_mb = test_file_access()
    if not files_accessible:
        print("\n❌ Setup incomplete - cannot access all Audacity files")
        return False
    
    # Test 4: Storage space
    if not check_storage_space(drive_results, total_size_mb):
        print("\n❌ Setup incomplete - insufficient Google Drive storage")
        return False
    
    # Test 5: Upload time estimation
    estimate_upload_time(total_size_mb)
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎉 SETUP VERIFICATION COMPLETE")
    print("=" * 50)
    print("✅ All tests passed - ready for upload!")
    print(f"📁 Files to upload: 2 Audacity projects")
    print(f"💾 Total size: {total_size_mb:.1f} MB ({total_size_mb/1024:.2f} GB)")
    print(f"🎯 Target: Google Drive 'Audacity Projects' folder")
    print()
    print("Next steps:")
    print("1. Run: python audacity_gdrive_uploader.py")
    print("2. Confirm upload when prompted")
    print("3. Monitor progress in the logs")
    print()
    print("⚠️  Safety reminder: Files will only be deleted locally")
    print("   after successful upload verification!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)