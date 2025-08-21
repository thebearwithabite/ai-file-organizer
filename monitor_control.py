#!/usr/bin/env python3
"""
Simple control script for the Enhanced Background Monitor
Provides easy commands to start, stop, and check status
"""

import sys
from pathlib import Path
import subprocess
import time

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from background_monitor import EnhancedBackgroundMonitor

def quick_start():
    """Start the monitor with recommended settings"""
    print("🚀 Starting Enhanced Background Monitor")
    print("=" * 50)
    
    monitor = EnhancedBackgroundMonitor()
    
    print("⚙️  Configuration:")
    print(f"   📍 Base directory: {monitor.base_dir}")
    print(f"   📁 Monitoring {len(monitor.watch_directories)} directories")
    print(f"   🔄 Update intervals: Real-time (30s), Email (5min), Directory scan (1hr)")
    
    try:
        # Start with recommended threads
        recommended_threads = ['real_time', 'email_sync', 'directory_scan']
        
        print(f"\n🔧 Starting threads: {', '.join(recommended_threads)}")
        monitor.start(recommended_threads)
        
        print("\n✅ Monitor started successfully!")
        print("\n📊 Status updates:")
        
        # Show periodic status updates
        status_count = 0
        while True:
            time.sleep(30)  # Check every 30 seconds
            status_count += 1
            
            if status_count % 10 == 0:  # Every 5 minutes, show detailed status
                status = monitor.status()
                if 'error' not in status:
                    print(f"\n⏰ Status Update ({time.strftime('%H:%M:%S')}):")
                    print(f"   📄 Files processed (24h): {status['files_processed_24h']}")
                    print(f"   🔴 Errors (24h): {status['errors_24h']}")
                    print(f"   📊 Total processed: {status['processed_files']}")
            else:
                # Just show a heartbeat
                print(".", end="", flush=True)
    
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Stopping monitor...")
        monitor.stop()
        print("✅ Monitor stopped")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        monitor.stop()

def quick_status():
    """Show current monitor status"""
    print("📊 Background Monitor Status")
    print("=" * 40)
    
    try:
        monitor = EnhancedBackgroundMonitor()
        status = monitor.status()
        
        if 'error' in status:
            print(f"❌ Error: {status['error']}")
            return
        
        print(f"🔄 Running: {'✅ Yes' if status['running'] else '❌ No'}")
        print(f"🧵 Active Threads: {status['active_threads']}")
        print(f"📁 Watch Directories: {status['watch_directories']}")
        print(f"✅ Processed Files: {status['processed_files']:,}")
        print(f"❌ Error Files: {status['error_files']}")
        
        print(f"\n📈 Last 24 Hours:")
        print(f"   Scans: {status['scans_24h']}")
        print(f"   Files processed: {status['files_processed_24h']}")
        print(f"   Errors: {status['errors_24h']}")
        
        if status['last_scan']:
            print(f"   Last scan: {status['last_scan'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show watch directories
        print(f"\n📁 Monitored Directories:")
        for name, dir_info in monitor.watch_directories.items():
            path = dir_info['path']
            priority = dir_info['priority']
            exists = "✅" if path.exists() else "❌"
            print(f"   {exists} {name}: {path} ({priority})")
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")

def quick_scan(directory_path: str = None):
    """Perform a quick scan of a directory"""
    
    if not directory_path:
        # Default to staging directory
        directory_path = "/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging"
    
    directory = Path(directory_path)
    
    print(f"🔍 Quick Scan: {directory}")
    print("=" * 50)
    
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    try:
        monitor = EnhancedBackgroundMonitor()
        
        # Create directory info
        dir_info = {
            'path': directory,
            'priority': 'manual',
            'auto_organize': False
        }
        
        print(f"📂 Scanning {directory}...")
        start_time = time.time()
        
        stats = monitor._scan_directory(dir_info, "manual")
        
        scan_time = time.time() - start_time
        
        print(f"\n✅ Scan Complete ({scan_time:.1f}s):")
        print(f"   📄 Files found: {stats['files_found']}")
        print(f"   ✅ Files processed: {stats['files_processed']}")
        print(f"   ⏭️  Files skipped: {stats['files_skipped']}")
        print(f"   ❌ Errors: {stats['errors']}")
        
        if stats['files_processed'] > 0:
            print(f"\n🎉 Successfully indexed {stats['files_processed']} files!")
        
    except Exception as e:
        print(f"❌ Scan failed: {e}")

def show_help():
    """Show help information"""
    print("🗂️  AI File Organizer - Background Monitor Control")
    print("=" * 60)
    print()
    print("📋 Available Commands:")
    print("   start    - Start the background monitor (recommended threads)")
    print("   status   - Show current monitor status")
    print("   scan     - Perform quick scan of staging directory")
    print("   scan <dir> - Perform quick scan of specific directory")
    print("   help     - Show this help message")
    print()
    print("💡 Examples:")
    print("   python monitor_control.py start")
    print("   python monitor_control.py status")
    print("   python monitor_control.py scan")
    print("   python monitor_control.py scan /Users/ryan/Downloads")
    print()
    print("🔄 The monitor automatically:")
    print("   • Watches staging directory every 30 seconds")
    print("   • Syncs emails every 5 minutes")
    print("   • Scans document directories every hour")
    print("   • ADHD-friendly: Waits 7 days before processing Downloads/Desktop")
    print("   • Keeps vector database up to date")
    print()
    print("⚠️  To stop: Press Ctrl+C when running 'start' command")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        quick_start()
    elif command == 'status':
        quick_status()
    elif command == 'scan':
        if len(sys.argv) > 2:
            quick_scan(sys.argv[2])
        else:
            quick_scan()
    elif command == 'help':
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python monitor_control.py help' for available commands")

if __name__ == "__main__":
    main()