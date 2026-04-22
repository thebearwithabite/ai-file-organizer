#!/usr/bin/env python3
"""
Command Line Interface for Batch Processing
Easy-to-use commands for processing large collections of files
"""

import sys
import argparse
from pathlib import Path
import time

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from batch_processor import BatchProcessor, BatchJob
from interaction_modes import InteractionMode

class ProgressPrinter:
    """Simple progress printer for CLI"""
    
    def __init__(self):
        self.last_update = 0
    
    def __call__(self, progress):
        current_time = time.time()
        
        # Only update every 5 seconds to avoid spam
        if current_time - self.last_update > 5:
            percent = (progress.processed / progress.total_files * 100) if progress.total_files > 0 else 0
            
            print(f"\n📈 Progress Update:")
            print(f"   {progress.processed}/{progress.total_files} files ({percent:.1f}%)")
            print(f"   ✅ Success: {progress.successful}  ❌ Failed: {progress.failed}  ⏭️ Skipped: {progress.skipped}")
            
            if progress.files_per_minute > 0:
                print(f"   ⚡ Speed: {progress.files_per_minute:.1f} files/min")
            
            if progress.estimated_completion:
                eta = progress.estimated_completion.strftime("%H:%M:%S")
                print(f"   🕐 ETA: {eta}")
            
            if progress.current_file:
                print(f"   📄 Current: {progress.current_file}")
                
            self.last_update = current_time

def process_directory(directory: str, mode: str = "smart", dry_run: bool = True, 
                     max_workers: int = 1, recursive: bool = True):
    """Process all files in a directory"""
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    print(f"📁 Batch Processing Directory: {dir_path}")
    print("=" * 60)
    
    # Find files to process
    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"
    
    all_files = list(dir_path.glob(pattern))
    files_to_process = [f for f in all_files 
                       if f.is_file() 
                       and not f.name.startswith('.') 
                       and f.suffix.lower() in ['.pdf', '.docx', '.doc', '.txt', '.md', '.rtf']]
    
    if not files_to_process:
        print("❌ No supported files found to process")
        return
    
    print(f"🔍 Found {len(files_to_process)} files to process")
    
    # Create batch processor
    processor = BatchProcessor()
    
    # Add progress callback
    progress_printer = ProgressPrinter()
    processor.add_progress_callback(progress_printer)
    
    # Convert mode string to enum
    mode_map = {
        'smart': InteractionMode.SMART,
        'minimal': InteractionMode.MINIMAL,
        'always': InteractionMode.ALWAYS,
        'never': InteractionMode.NEVER
    }
    interaction_mode = mode_map.get(mode.lower(), InteractionMode.SMART)
    
    # Create and run batch job
    job_name = f"Directory: {dir_path.name}"
    job = processor.create_batch_job(job_name, files_to_process, interaction_mode, dry_run)
    
    print(f"\n🚀 Starting batch processing...")
    print(f"   Mode: {interaction_mode.value}")
    print(f"   Dry run: {dry_run}")
    print(f"   Workers: {max_workers}")
    
    # Run the job
    try:
        summary = processor.run_batch_job(job, max_workers)
        
        print(f"\n🎉 Batch processing complete!")
        return summary
        
    except KeyboardInterrupt:
        print(f"\n⏸️  Batch processing interrupted")
        return None

def process_file_list(file_list_path: str, mode: str = "smart", dry_run: bool = True):
    """Process files from a text file list"""
    
    file_list = Path(file_list_path)
    if not file_list.exists():
        print(f"❌ File list not found: {file_list_path}")
        return
    
    # Read file list
    try:
        with open(file_list, 'r') as f:
            file_paths = [Path(line.strip()) for line in f if line.strip()]
        
        # Filter to existing files
        existing_files = [f for f in file_paths if f.exists()]
        
        print(f"📋 Processing {len(existing_files)} files from list")
        print(f"   (Found {len(existing_files)}/{len(file_paths)} files)")
        
        if not existing_files:
            print("❌ No existing files found")
            return
        
        # Create batch processor
        processor = BatchProcessor()
        progress_printer = ProgressPrinter()
        processor.add_progress_callback(progress_printer)
        
        # Convert mode
        mode_map = {
            'smart': InteractionMode.SMART,
            'minimal': InteractionMode.MINIMAL,
            'always': InteractionMode.ALWAYS,
            'never': InteractionMode.NEVER
        }
        interaction_mode = mode_map.get(mode.lower(), InteractionMode.SMART)
        
        # Create and run job
        job_name = f"File List: {file_list.name}"
        job = processor.create_batch_job(job_name, existing_files, interaction_mode, dry_run)
        
        summary = processor.run_batch_job(job)
        return summary
        
    except Exception as e:
        print(f"❌ Error processing file list: {e}")
        return None

def list_jobs():
    """List all batch jobs"""
    
    print("📊 Batch Processing Jobs")
    print("=" * 50)
    
    processor = BatchProcessor()
    jobs = processor.list_jobs()
    
    if not jobs:
        print("❌ No batch jobs found")
        return
    
    print(f"Found {len(jobs)} jobs:")
    print()
    
    for job in jobs:
        status_icon = {
            'completed': '✅',
            'running': '🔄', 
            'paused': '⏸️',
            'failed': '❌',
            'pending': '⏳'
        }.get(job['status'], '❓')
        
        print(f"{status_icon} {job['job_id']}")
        print(f"   Name: {job['name']}")
        print(f"   Status: {job['status']}")
        print(f"   Files: {job['file_count']} ({job['successful_files']} successful, {job['failed_files']} failed)")
        print(f"   Mode: {job['mode']} ({'DRY RUN' if job['dry_run'] else 'LIVE'})")
        print(f"   Created: {job['created_at'][:19].replace('T', ' ')}")
        print()

def show_batch_help():
    """Show helpful examples and tips"""
    
    print("""
🚀 AI File Organizer - Batch Processing Examples

📁 PROCESS DIRECTORY:
   python batch_cli.py directory /Users/user/Downloads
   python batch_cli.py directory /Users/user/Documents --mode never --live
   python batch_cli.py directory /Users/user/Desktop --no-recursive

📋 PROCESS FILE LIST:
   python batch_cli.py filelist files_to_process.txt --mode minimal
   
📊 MANAGE JOBS:
   python batch_cli.py jobs                    # List all jobs
   python batch_cli.py help                    # Show this help

⚙️  MODES:
   smart    - Ask when uncertain (70% threshold) - RECOMMENDED
   minimal  - Only ask for very uncertain files (40% threshold)  
   always   - Ask about every file (100% threshold)
   never    - Fully automatic, no questions (0% threshold)

💡 TIPS:
   • Start with --dry-run to see what would happen
   • Use 'never' mode for bulk imports from trusted sources
   • Use 'smart' mode for daily file organization  
   • Use 'always' mode for critical documents
   • Larger --workers only helps in 'never' mode (parallel processing)

🔧 PERFORMANCE:
   • Interactive modes (smart/always): ~10-50 files/hour
   • Automatic mode (never): ~100-500 files/hour
   • Processing speed depends on file sizes and AI analysis time
    """)

def main():
    """Command line interface for batch processing"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Batch Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Directory processing command
    dir_parser = subparsers.add_parser('directory', help='Process all files in a directory')
    dir_parser.add_argument('directory', help='Directory to process')
    dir_parser.add_argument('--mode', choices=['smart', 'minimal', 'always', 'never'], 
                           default='smart', help='Interaction mode (default: smart)')
    dir_parser.add_argument('--live', action='store_true', 
                           help='Actually move files (default is dry-run)')
    dir_parser.add_argument('--workers', type=int, default=1, 
                           help='Number of parallel workers (only for never mode)')
    dir_parser.add_argument('--no-recursive', action='store_true', 
                           help='Don\'t process subdirectories')
    
    # File list processing command
    list_parser = subparsers.add_parser('filelist', help='Process files from a text file list')
    list_parser.add_argument('file_list', help='Text file containing list of file paths')
    list_parser.add_argument('--mode', choices=['smart', 'minimal', 'always', 'never'], 
                            default='smart', help='Interaction mode (default: smart)')
    list_parser.add_argument('--live', action='store_true', 
                            help='Actually move files (default is dry-run)')
    
    # Jobs management command
    subparsers.add_parser('jobs', help='List all batch processing jobs')
    
    # Help command
    subparsers.add_parser('help', help='Show detailed help and examples')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🚀 AI File Organizer - Batch Processing CLI")
    print("=" * 60)
    
    if args.command == 'directory':
        process_directory(
            args.directory,
            args.mode,
            not args.live,  # dry_run is opposite of live
            args.workers,
            not args.no_recursive
        )
        
    elif args.command == 'filelist':
        process_file_list(args.file_list, args.mode, not args.live)
        
    elif args.command == 'jobs':
        list_jobs()
        
    elif args.command == 'help':
        show_batch_help()

if __name__ == "__main__":
    main()