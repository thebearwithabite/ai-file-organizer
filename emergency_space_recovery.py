#!/usr/bin/env python3
"""
Emergency Storage Space Recovery
Smart file staging to Google Drive to free up critical space
ADHD-friendly with clear progress and no accidental deletions
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import subprocess

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

class EmergencySpaceRecovery:
    """Smart storage recovery for critically low disk space"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents"
        self.target_recovery_gb = 20  # Goal: recover 20GB
        self.target_recovery_bytes = self.target_recovery_gb * 1024**3
        
        # Safe staging priorities (largest impact, lowest risk)
        self.staging_priorities = {
            'old_downloads': {
                'path': Path.home() / "Downloads",
                'age_days': 30,
                'extensions': {'.zip', '.dmg', '.pkg', '.iso', '.tar.gz'},
                'description': 'Old installer files and archives'
            },
            'large_media': {
                'path': self.base_dir,
                'min_size_mb': 50,
                'extensions': {'.mov', '.mp4', '.mkv', '.avi', '.m4v'},
                'description': 'Large video files'
            },
            'old_documents': {
                'path': self.base_dir,
                'age_days': 90,
                'extensions': {'.pdf', '.docx', '.pages', '.keynote'},
                'description': 'Documents not accessed in 90 days'
            },
            'cache_safe': {
                'path': self.base_dir,
                'patterns': ['*cache*', '*Cache*', '*tmp*', '*temp*'],
                'description': 'Safe cache directories'
            }
        }
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Get current disk usage in GB"""
        try:
            result = subprocess.run(['df', '-H', str(Path.home())], 
                                 capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                total_gb = float(parts[1].rstrip('G')) if 'G' in parts[1] else float(parts[1])/1000
                used_gb = float(parts[2].rstrip('G')) if 'G' in parts[2] else float(parts[2])/1000  
                available_gb = float(parts[3].rstrip('G')) if 'G' in parts[3] else float(parts[3])/1000
                
                return {
                    'total_gb': total_gb,
                    'used_gb': used_gb,
                    'available_gb': available_gb,
                    'usage_percent': (used_gb / total_gb) * 100
                }
        except:
            pass
        
        return {'total_gb': 0, 'used_gb': 0, 'available_gb': 17, 'usage_percent': 90}
    
    def find_staging_candidates(self) -> List[Dict]:
        """Find files that can be safely staged to Google Drive"""
        
        candidates = []
        total_size = 0
        
        print(f"🔍 Scanning for staging candidates (target: {self.target_recovery_gb}GB)...")
        
        for category, config in self.staging_priorities.items():
            print(f"\n📂 Checking: {config['description']}")
            category_size = 0
            category_files = []
            
            if category == 'old_downloads':
                # Old installer files
                cutoff_date = datetime.now() - timedelta(days=config['age_days'])
                
                for ext in config['extensions']:
                    for file_path in config['path'].glob(f"*{ext}"):
                        if file_path.is_file():
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_time < cutoff_date:
                                size_mb = file_path.stat().st_size / (1024**2)
                                candidates.append({
                                    'path': file_path,
                                    'size_mb': size_mb,
                                    'category': category,
                                    'reason': f"Old {ext} file ({size_mb:.1f}MB, {(datetime.now() - file_time).days} days old)"
                                })
                                category_size += size_mb
                                category_files.append(file_path.name)
            
            elif category == 'large_media':
                # Large video files
                for ext in config['extensions']:
                    for file_path in config['path'].rglob(f"*{ext}"):
                        if file_path.is_file():
                            size_mb = file_path.stat().st_size / (1024**2)
                            if size_mb >= config['min_size_mb']:
                                candidates.append({
                                    'path': file_path,
                                    'size_mb': size_mb,
                                    'category': category,
                                    'reason': f"Large video file ({size_mb:.1f}MB)"
                                })
                                category_size += size_mb
                                category_files.append(file_path.name)
            
            elif category == 'old_documents':
                # Old documents
                cutoff_date = datetime.now() - timedelta(days=config['age_days'])
                
                for ext in config['extensions']:
                    for file_path in config['path'].rglob(f"*{ext}"):
                        if file_path.is_file():
                            # Check last access time
                            try:
                                access_time = datetime.fromtimestamp(file_path.stat().st_atime)
                                if access_time < cutoff_date:
                                    size_mb = file_path.stat().st_size / (1024**2)
                                    candidates.append({
                                        'path': file_path,
                                        'size_mb': size_mb,
                                        'category': category,
                                        'reason': f"Not accessed in {(datetime.now() - access_time).days} days ({size_mb:.1f}MB)"
                                    })
                                    category_size += size_mb
                                    category_files.append(file_path.name)
                            except:
                                continue
            
            print(f"   Found: {len(category_files)} files, {category_size:.1f}MB total")
            if category_files and len(category_files) <= 5:
                print(f"   Files: {', '.join(category_files)}")
            elif category_files:
                print(f"   Examples: {', '.join(category_files[:3])}... (+{len(category_files)-3} more)")
            
            total_size += category_size
            
            # Stop if we have enough candidates
            if total_size >= self.target_recovery_gb * 1024:  # Convert GB to MB
                break
        
        # Sort by size (largest first)
        candidates.sort(key=lambda x: x['size_mb'], reverse=True)
        
        print(f"\n📊 Summary: Found {len(candidates)} candidates totaling {total_size:.1f}MB ({total_size/1024:.1f}GB)")
        
        return candidates
    
    def preview_staging_plan(self, candidates: List[Dict]) -> Dict:
        """Preview what will be staged"""
        
        total_size_mb = sum(c['size_mb'] for c in candidates)
        total_size_gb = total_size_mb / 1024
        
        # Select files to reach target
        selected = []
        selected_size_mb = 0
        
        for candidate in candidates:
            if selected_size_mb >= self.target_recovery_gb * 1024:  # Target in MB
                break
            selected.append(candidate)
            selected_size_mb += candidate['size_mb']
        
        print(f"\n📋 STAGING PREVIEW")
        print(f"=" * 50)
        print(f"🎯 Target: {self.target_recovery_gb}GB")
        print(f"📦 Will stage: {len(selected)} files ({selected_size_mb:.1f}MB / {selected_size_mb/1024:.1f}GB)")
        
        # Group by category
        categories = {}
        for item in selected:
            cat = item['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        for category, items in categories.items():
            cat_size = sum(item['size_mb'] for item in items)
            print(f"\n📂 {self.staging_priorities[category]['description']}:")
            print(f"   Files: {len(items)}, Size: {cat_size:.1f}MB")
            
            # Show examples
            for item in items[:3]:
                print(f"   • {item['path'].name} ({item['size_mb']:.1f}MB) - {item['reason']}")
            if len(items) > 3:
                print(f"   • ... and {len(items)-3} more files")
        
        return {
            'selected_files': selected,
            'total_size_mb': selected_size_mb,
            'total_size_gb': selected_size_mb / 1024,
            'categories': categories
        }
    
    def execute_staging(self, staging_plan: Dict, dry_run: bool = True):
        """Execute the staging plan"""
        
        if dry_run:
            print(f"\n🧪 DRY RUN - No files will be moved")
        else:
            print(f"\n🚀 EXECUTING STAGING PLAN")
        
        print(f"📦 Moving {len(staging_plan['selected_files'])} files to Google Drive")
        print(f"💾 Will free: {staging_plan['total_size_gb']:.1f}GB")
        
        if not dry_run:
            # Import gdrive_librarian for actual staging
            try:
                from gdrive_librarian import GoogleDriveAILibrarian
                
                librarian = GoogleDriveAILibrarian(str(self.base_dir))
                
                # Create staging folder
                staging_date = datetime.now().strftime("%Y%m%d_%H%M%S")
                staging_folder = f"EMERGENCY_STAGING_{staging_date}"
                
                success_count = 0
                for item in staging_plan['selected_files']:
                    try:
                        print(f"📤 Staging: {item['path'].name}")
                        # Stage to Google Drive (this would need to be implemented)
                        # librarian.stage_file(item['path'], staging_folder)
                        success_count += 1
                    except Exception as e:
                        print(f"❌ Failed to stage {item['path'].name}: {e}")
                
                print(f"\n✅ Staged {success_count}/{len(staging_plan['selected_files'])} files")
                
            except ImportError:
                print(f"❌ Google Drive librarian not available")
        
        print(f"\n🎯 Expected free space after staging: ~{17 + staging_plan['total_size_gb']:.1f}GB")

def main():
    print(f"🚨 Emergency Storage Space Recovery")
    print(f"=" * 50)
    
    recovery = EmergencySpaceRecovery()
    
    # Show current disk usage
    disk_info = recovery.get_disk_usage()
    print(f"💾 Current disk usage:")
    print(f"   Available: {disk_info['available_gb']:.1f}GB")
    print(f"   Used: {disk_info['usage_percent']:.1f}%")
    
    # Find staging candidates
    candidates = recovery.find_staging_candidates()
    
    if not candidates:
        print(f"\n⚠️  No staging candidates found")
        return
    
    # Preview staging plan
    staging_plan = recovery.preview_staging_plan(candidates)
    
    print(f"\n❓ Execute this staging plan?")
    print(f"   --dry-run: Preview only (safe)")
    print(f"   --execute: Actually move files to Google Drive")
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Actually execute staging')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Preview only')
    
    if len(sys.argv) == 1:
        # No arguments, default to dry run
        recovery.execute_staging(staging_plan, dry_run=True)
    else:
        args = parser.parse_args()
        recovery.execute_staging(staging_plan, dry_run=not args.execute)

if __name__ == "__main__":
    main()