#!/usr/bin/env python3
"""
ADHD-Friendly File Organizer - FIXED VERSION
Uses the improved classifier that actually works properly

Usage:
  python3 organize_adhd_friendly.py ~/Downloads --dry-run
  python3 organize_adhd_friendly.py ~/Downloads --live
  python3 organize_adhd_friendly.py single "Demo Reel.mov" --live

Created by: RT Max  
"""

import sys
import argparse
import signal
from pathlib import Path
from typing import List

# Import our fixed classifier
from interactive_classifier_fixed import ADHDFriendlyClassifier
from gdrive_integration import get_ai_organizer_root

class ADHDFriendlyOrganizer:
    """
    File organizer that actually works for ADHD brains:
    - No infinite loops
    - Obvious files auto-organize  
    - Easy escape with Ctrl+C
    - Clear progress indicators
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        self.classifier = ADHDFriendlyClassifier(str(self.base_dir))
        self.interrupted = False
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n\n🚪 Stopping organization... (Ctrl+C detected)")
        print(f"💡 Progress saved - you can resume anytime!")
        self.interrupted = True
        sys.exit(0)
    
    def organize_directory(self, directory: Path, dry_run: bool = True) -> None:
        """
        Organize all files in a directory
        
        Args:
            directory: Directory to organize
            dry_run: If True, shows what would happen without moving files
        """
        if not directory.exists():
            print(f"❌ Directory not found: {directory}")
            return
        
        # Find files to organize
        files_to_organize = []
        for file_path in directory.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                files_to_organize.append(file_path)
        
        if not files_to_organize:
            print(f"📁 No files found to organize in {directory}")
            return
        
        print(f"🗂️  ADHD-FRIENDLY FILE ORGANIZER")
        print(f"📁 Directory: {directory}")
        print(f"📄 Files found: {len(files_to_organize)}")
        print(f"🔍 Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
        print(f"💡 Press Ctrl+C anytime to stop")
        
        if dry_run:
            print(f"🛡️  DRY RUN - No files will be moved")
        else:
            print(f"⚡ LIVE MODE - Files will be moved")
        
        organized_count = 0
        skipped_count = 0
        
        # Process each file
        for i, file_path in enumerate(files_to_organize, 1):
            if self.interrupted:
                break
            
            print(f"\n📄 [{i}/{len(files_to_organize)}] Processing: {file_path.name}")
            
            try:
                # Classify the file
                result = self.classifier.classify_with_questions(file_path)
                
                if result.confidence >= 70.0:  # Good enough to organize
                    target_dir = self.base_dir / result.suggested_path
                    target_path = target_dir / file_path.name
                    
                    print(f"   📁 Target: {result.suggested_path}")
                    print(f"   📊 Confidence: {result.confidence:.1f}%")
                    
                    if not dry_run:
                        # Actually move the file
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Handle name conflicts
                        counter = 1
                        original_target = target_path
                        while target_path.exists():
                            stem = original_target.stem
                            suffix = original_target.suffix
                            target_path = target_dir / f"{stem}_{counter}{suffix}"
                            counter += 1
                        
                        file_path.rename(target_path)
                        print(f"   ✅ Moved to: {target_path}")
                    else:
                        print(f"   🔍 Would move to: {target_path}")
                    
                    organized_count += 1
                    
                else:
                    print(f"   ⚠️  Low confidence ({result.confidence:.1f}%) - skipping")
                    print(f"   💡 Consider manual review")
                    skipped_count += 1
                
            except KeyboardInterrupt:
                self._signal_handler(None, None)
            except Exception as e:
                print(f"   ❌ Error processing {file_path.name}: {e}")
                skipped_count += 1
        
        # Summary
        print(f"\n📊 ORGANIZATION SUMMARY:")
        print(f"   ✅ Organized: {organized_count}")
        print(f"   ⚠️  Skipped: {skipped_count}")
        print(f"   📁 Total: {len(files_to_organize)}")
        
        if dry_run:
            print(f"\n🔍 This was a DRY RUN - no files were moved")
            print(f"💡 Use --live to actually organize files")
        else:
            print(f"\n✅ Organization complete!")
    
    def organize_single_file(self, file_path: Path, dry_run: bool = True) -> None:
        """Organize a single file"""
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        
        print(f"🗂️  SINGLE FILE ORGANIZER")
        print(f"📄 File: {file_path.name}")
        print(f"🔍 Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
        
        try:
            result = self.classifier.classify_with_questions(file_path)
            
            target_dir = self.base_dir / result.suggested_path
            target_path = target_dir / file_path.name
            
            print(f"\n📊 CLASSIFICATION RESULT:")
            print(f"   📁 Category: {result.category}")
            print(f"   📂 Subcategory: {result.subcategory}")
            print(f"   📊 Confidence: {result.confidence:.1f}%")
            print(f"   📍 Target: {result.suggested_path}")
            
            if result.confidence >= 70.0:
                if not dry_run:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Handle name conflicts
                    counter = 1
                    original_target = target_path
                    while target_path.exists():
                        stem = original_target.stem
                        suffix = original_target.suffix
                        target_path = target_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    file_path.rename(target_path)
                    print(f"   ✅ Moved to: {target_path}")
                else:
                    print(f"   🔍 Would move to: {target_path}")
            else:
                print(f"   ⚠️  Confidence too low ({result.confidence:.1f}%) for auto-organization")
                print(f"   💡 Consider manual placement")
        
        except KeyboardInterrupt:
            print(f"\n👋 Cancelled by user")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    parser = argparse.ArgumentParser(description='ADHD-Friendly File Organizer - FIXED VERSION')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Directory organize command
    dir_parser = subparsers.add_parser('directory', help='Organize all files in a directory')
    dir_parser.add_argument('directory', help='Directory to organize')
    dir_parser.add_argument('--live', action='store_true', help='Actually move files (default is dry-run)')
    dir_parser.add_argument('--base-dir', help='Base directory for organization')
    
    # Single file command
    file_parser = subparsers.add_parser('single', help='Organize a single file')
    file_parser.add_argument('file', help='File to organize')
    file_parser.add_argument('--live', action='store_true', help='Actually move file (default is dry-run)')
    file_parser.add_argument('--base-dir', help='Base directory for organization')
    
    # Quick directory shortcut (default command)
    parser.add_argument('target', nargs='?', help='Directory or file to organize')
    parser.add_argument('--live', action='store_true', help='Actually move files (default is dry-run)')
    parser.add_argument('--base-dir', help='Base directory for organization')
    
    args = parser.parse_args()
    
    # Handle different command formats
    if args.command == 'directory':
        organizer = ADHDFriendlyOrganizer(args.base_dir)
        directory = Path(args.directory)
        organizer.organize_directory(directory, dry_run=not args.live)
    
    elif args.command == 'single':
        organizer = ADHDFriendlyOrganizer(args.base_dir) 
        file_path = Path(args.file)
        organizer.organize_single_file(file_path, dry_run=not args.live)
    
    elif args.target:
        # Quick shortcut mode
        organizer = ADHDFriendlyOrganizer(args.base_dir)
        target = Path(args.target)
        
        if target.is_dir():
            organizer.organize_directory(target, dry_run=not args.live)
        elif target.is_file():
            organizer.organize_single_file(target, dry_run=not args.live)
        else:
            print(f"❌ Target not found: {target}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()