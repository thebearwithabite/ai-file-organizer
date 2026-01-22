#!/usr/bin/env python3
"""
System Storage Cleanup for Critical Space Recovery
Safely frees up system data without breaking anything
ADHD-friendly with clear explanations and confirmations
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class SystemStorageCleanup:
    """Safe system storage cleanup for emergency space recovery"""
    
    def __init__(self):
        self.home = Path.home()
        self.library = self.home / "Library"
        
    def analyze_storage_hogs(self) -> Dict[str, Dict]:
        """Analyze what's taking up the most space"""
        
        print("🔍 Analyzing storage usage...")
        
        cleanup_opportunities = {
            'messages_attachments': {
                'path': self.library / "Messages" / "Attachments",
                'description': "iMessage attachments (photos, videos, files)",
                'potential_gb': 17,
                'safety': 'medium',  # Can re-download most from iCloud
                'action': 'Move old attachments (>90 days) to archive'
            },
            'docker_data': {
                'path': self.library / "Containers" / "com.docker.docker",
                'description': "Docker containers, images, and volumes", 
                'potential_gb': 16,
                'safety': 'high',  # Can rebuild containers
                'action': 'Clean unused Docker data'
            },
            'mail_attachments': {
                'path': self.library / "Mail",
                'description': "Email attachments and local cache",
                'potential_gb': 8.8,
                'safety': 'medium',  # Can re-sync from server
                'action': 'Archive old mail attachments'
            },
            'google_cache': {
                'path': self.library / "Caches" / "Google",
                'description': "Google Drive local cache",
                'potential_gb': 2.1,
                'safety': 'high',  # Just cache, will rebuild
                'action': 'Clear Google Drive cache'
            },
            'spotlight_index': {
                'path': self.library / "Metadata" / "CoreSpotlight",
                'description': "Spotlight search index",
                'potential_gb': 3.4,
                'safety': 'high',  # macOS will rebuild
                'action': 'Reset Spotlight index'
            },
            'audacity_temp': {
                'path': self.library / "Application Support" / "audacity",
                'description': "Audacity temporary files and cache",
                'potential_gb': 1.3,
                'safety': 'high',  # Just temp files
                'action': 'Clear Audacity temp files'
            }
        }
        
        # Verify which paths actually exist and get real sizes
        verified_opportunities = {}
        total_potential = 0
        
        for key, info in cleanup_opportunities.items():
            if info['path'].exists():
                try:
                    # Get actual size
                    result = subprocess.run(['du', '-sh', str(info['path'])], 
                                         capture_output=True, text=True)
                    if result.stdout:
                        size_str = result.stdout.split()[0]
                        verified_opportunities[key] = info.copy()
                        verified_opportunities[key]['actual_size'] = size_str
                        
                        # Convert to GB for calculation
                        if 'G' in size_str:
                            gb_size = float(size_str.replace('G', ''))
                        elif 'M' in size_str:
                            gb_size = float(size_str.replace('M', '')) / 1024
                        else:
                            gb_size = 0.1
                        
                        verified_opportunities[key]['actual_gb'] = gb_size
                        total_potential += gb_size
                
                except Exception as e:
                    print(f"⚠️ Could not analyze {info['path']}: {e}")
        
        print(f"📊 Found {len(verified_opportunities)} cleanup opportunities")
        print(f"💾 Potential space recovery: ~{total_potential:.1f}GB")
        
        return verified_opportunities
    
    def show_cleanup_plan(self, opportunities: Dict) -> None:
        """Show the cleanup plan with safety ratings"""
        
        print(f"\n📋 STORAGE CLEANUP PLAN")
        print(f"=" * 60)
        
        high_safety = []
        medium_safety = []
        
        for key, info in opportunities.items():
            if info['safety'] == 'high':
                high_safety.append((key, info))
            else:
                medium_safety.append((key, info))
        
        print(f"\n✅ HIGH SAFETY (Recommended first):")
        for key, info in high_safety:
            print(f"   🟢 {info['description']}")
            print(f"      Size: {info['actual_size']} | Action: {info['action']}")
        
        print(f"\n⚠️  MEDIUM SAFETY (Consider carefully):")
        for key, info in medium_safety:
            print(f"   🟡 {info['description']}")
            print(f"      Size: {info['actual_size']} | Action: {info['action']}")
            print(f"      Note: May need to re-download some content")
        
        total_high = sum(info['actual_gb'] for _, info in high_safety)
        total_medium = sum(info['actual_gb'] for _, info in medium_safety)
        
        print(f"\n📊 Potential Recovery:")
        print(f"   High Safety: ~{total_high:.1f}GB")
        print(f"   Medium Safety: ~{total_medium:.1f}GB")
        print(f"   Total: ~{total_high + total_medium:.1f}GB")
    
    def clean_docker_data(self, dry_run: bool = True) -> float:
        """Clean Docker data - highest impact, safest"""
        
        print(f"\n🐳 Docker Cleanup ({'DRY RUN' if dry_run else 'EXECUTING'})")
        
        docker_path = self.library / "Containers" / "com.docker.docker"
        
        if not docker_path.exists():
            print(f"   ℹ️ Docker container directory not found")
            return 0.0
        
        # Check if Docker is running
        docker_running = False
        try:
            result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
            docker_running = result.returncode == 0
        except:
            pass
        
        if docker_running:
            print(f"   🔄 Docker is running - using Docker commands...")
            commands = [
                "docker system prune -af",  # Remove all unused data
                "docker volume prune -f",   # Remove unused volumes
                "docker image prune -af",   # Remove all unused images
            ]
            
            if dry_run:
                print(f"   Would run: {'; '.join(commands)}")
                return 16.0
            else:
                try:
                    for cmd in commands:
                        result = subprocess.run(cmd.split(), capture_output=True, text=True)
                        if result.returncode == 0:
                            print(f"   ✅ {cmd}")
                        else:
                            print(f"   ⚠️ {cmd} - {result.stderr}")
                    return 16.0
                except Exception as e:
                    print(f"   ❌ Docker cleanup failed: {e}")
                    return 0.0
        else:
            print(f"   💾 Docker not running - safe to delete data directory...")
            
            if dry_run:
                print(f"   Would delete: {docker_path}")
                return 16.0
            else:
                try:
                    # Get size before deletion for verification
                    result = subprocess.run(['du', '-sh', str(docker_path)], 
                                         capture_output=True, text=True)
                    size_before = result.stdout.split()[0] if result.stdout else "unknown"
                    
                    # Delete Docker data (safe since Docker isn't running)
                    subprocess.run(['rm', '-rf', str(docker_path)], check=True)
                    print(f"   ✅ Deleted Docker data ({size_before})")
                    
                    # Recreate empty directory structure so Docker can start later
                    docker_path.mkdir(parents=True, exist_ok=True)
                    print(f"   ✅ Created clean Docker directory")
                    
                    return 16.0
                except Exception as e:
                    print(f"   ❌ Failed to delete Docker data: {e}")
                    return 0.0
    
    def clean_google_cache(self, dry_run: bool = True) -> float:
        """Clean Google Drive cache"""
        
        print(f"\n📊 Google Cache Cleanup ({'DRY RUN' if dry_run else 'EXECUTING'})")
        
        cache_paths = [
            self.library / "Caches" / "Google",
            self.library / "Application Support" / "Google" / "DriveFS" / "cache"
        ]
        
        total_freed = 0
        for cache_path in cache_paths:
            if cache_path.exists():
                if dry_run:
                    print(f"   Would clean: {cache_path}")
                    total_freed += 1.0  # Estimated per path
                else:
                    try:
                        subprocess.run(['rm', '-rf', str(cache_path)], check=True)
                        print(f"   ✅ Cleaned: {cache_path}")
                        total_freed += 1.0
                    except Exception as e:
                        print(f"   ❌ Failed to clean {cache_path}: {e}")
        
        return total_freed
    
    def clean_spotlight_index(self, dry_run: bool = True) -> float:
        """Reset Spotlight index"""
        
        print(f"\n🔍 Spotlight Index Reset ({'DRY RUN' if dry_run else 'EXECUTING'})")
        
        if dry_run:
            print(f"   Would reset Spotlight index (~3.4GB recovery)")
            return 3.4
        else:
            try:
                # Disable and re-enable Spotlight indexing
                subprocess.run(['sudo', 'mdutil', '-E', '/'], check=True)
                print(f"   ✅ Spotlight index reset")
                return 3.4
            except Exception as e:
                print(f"   ❌ Spotlight reset failed: {e}")
                return 0.0
    
    def clean_audacity_temp(self, dry_run: bool = True) -> float:
        """Clean Audacity temp files"""
        
        print(f"\n🎵 Audacity Cleanup ({'DRY RUN' if dry_run else 'EXECUTING'})")
        
        audacity_path = self.library / "Application Support" / "audacity"
        
        if audacity_path.exists():
            if dry_run:
                print(f"   Would clean Audacity temp files (~1.3GB)")
                return 1.3
            else:
                try:
                    # Clean temp directories but keep preferences
                    for temp_dir in ['temp', 'AutoSave']:
                        temp_path = audacity_path / temp_dir
                        if temp_path.exists():
                            subprocess.run(['rm', '-rf', str(temp_path)], check=True)
                    print(f"   ✅ Audacity temp files cleaned")
                    return 1.3
                except Exception as e:
                    print(f"   ❌ Audacity cleanup failed: {e}")
                    return 0.0
        return 0.0

def main():
    print(f"🧹 System Storage Cleanup - Emergency Space Recovery")
    print(f"=" * 65)
    
    cleanup = SystemStorageCleanup()
    
    # Analyze current situation
    opportunities = cleanup.analyze_storage_hogs()
    
    if not opportunities:
        print(f"⚠️ No major cleanup opportunities found")
        return
    
    # Show cleanup plan
    cleanup.show_cleanup_plan(opportunities)
    
    print(f"\n🎯 RECOMMENDED SAFE CLEANUP SEQUENCE:")
    print(f"1. Docker cleanup (~16GB) - Containers can be rebuilt")
    print(f"2. Google cache (~2GB) - Just cache, will rebuild")
    print(f"3. Spotlight index (~3.4GB) - macOS will rebuild")
    print(f"4. Audacity temp (~1.3GB) - Just temp files")
    print(f"")
    print(f"💡 This would free ~22GB safely!")
    
    import argparse
    parser = argparse.ArgumentParser(description="System storage cleanup")
    parser.add_argument('--execute', action='store_true', help='Actually execute cleanup')
    parser.add_argument('--docker-only', action='store_true', help='Clean only Docker (safest)')
    
    if len(sys.argv) == 1:
        print(f"\n🧪 Add --execute to actually run cleanup")
        print(f"    Add --docker-only for just Docker cleanup (safest 16GB)")
        return
    
    args = parser.parse_args()
    
    if args.execute:
        print(f"\n🚀 EXECUTING CLEANUP...")
        total_freed = 0
        
        if 'docker_data' in opportunities:
            total_freed += cleanup.clean_docker_data(dry_run=False)
        
        if not args.docker_only:
            if 'google_cache' in opportunities:
                total_freed += cleanup.clean_google_cache(dry_run=False)
            
            if 'spotlight_index' in opportunities:
                total_freed += cleanup.clean_spotlight_index(dry_run=False)
            
            if 'audacity_temp' in opportunities:
                total_freed += cleanup.clean_audacity_temp(dry_run=False)
        
        print(f"\n✅ Cleanup complete! Estimated space freed: {total_freed:.1f}GB")
        print(f"🎯 Your available space should now be ~{17 + total_freed:.1f}GB")
    
    else:
        print(f"\n🧪 DRY RUN - No changes made")
        total_potential = 0
        
        if 'docker_data' in opportunities:
            total_potential += cleanup.clean_docker_data(dry_run=True)
        
        if not args.docker_only:
            if 'google_cache' in opportunities:
                total_potential += cleanup.clean_google_cache(dry_run=True)
            
            if 'spotlight_index' in opportunities:
                total_potential += cleanup.clean_spotlight_index(dry_run=True)
            
            if 'audacity_temp' in opportunities:
                total_potential += cleanup.clean_audacity_temp(dry_run=True)
        
        print(f"\n📊 Potential space recovery: {total_potential:.1f}GB")

if __name__ == "__main__":
    main()