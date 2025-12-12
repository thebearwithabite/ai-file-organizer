#!/usr/bin/env python3
"""
Integrated File Organizer with Naming Protocol
Combines classification, naming, and file movement into one seamless workflow
"""

import sys
from pathlib import Path
import shutil
import os
from datetime import datetime

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interactive_with_preview import PreviewClassifier
from file_naming_protocol import FileNamingProtocol
from gdrive_integration import get_ai_organizer_root, get_metadata_root

class IntegratedOrganizer:
    """Complete file organization with classification, naming, and movement"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        self.classifier = PreviewClassifier(str(self.base_dir))
        self.naming_protocol = FileNamingProtocol()
        
        # Ensure base directories exist
        self._ensure_base_structure()
    
    def _ensure_base_structure(self):
        """Create the basic folder structure if it doesn't exist"""
        base_folders = [
            "01_ACTIVE_PROJECTS",
            "02_ARCHIVED_PROJECTS",
            "03_REFERENCE_MATERIALS",
            # 04_METADATA_SYSTEM removed - now at ~/Documents/AI_METADATA_SYSTEM
            "99_TEMP_PROCESSING"
        ]
        
        for folder in base_folders:
            (self.base_dir / folder).mkdir(parents=True, exist_ok=True)
    
    def organize_file(self, file_path: Path, dry_run: bool = True, show_preview: bool = True) -> dict:
        """
        Complete file organization workflow:
        1. Show preview and classify interactively
        2. Generate enhanced filename
        3. Move to appropriate location
        """
        
        result = {
            'success': False,
            'original_path': str(file_path),
            'action_taken': 'none',
            'error': None
        }
        
        try:
            # Step 1: Interactive classification with preview
            if show_preview:
                classification_result, user_approved = self.classifier.classify_with_preview(file_path, dry_run)
            else:
                # Quick classification without preview
                classification_result = self.classifier.classify_with_questions(file_path)
                user_approved = True
            
            if not user_approved:
                result['action_taken'] = 'skipped_by_user'
                return result
            
            # Step 2: Generate enhanced filename
            extraction_result = None
            try:
                extraction_result = self.classifier.content_extractor.extract_content(file_path)
            except:
                pass
            
            classification_dict = {
                'category': classification_result.category,
                'people': classification_result.people,
                'tags': classification_result.tags
            }
            
            enhanced_filename = self.naming_protocol.generate_enhanced_filename(
                file_path, classification_dict, extraction_result
            )
            
            # Step 3: Determine target directory
            target_dir = self._get_target_directory(classification_result)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle filename collisions
            target_path = target_dir / enhanced_filename
            if target_path.exists():
                enhanced_filename = self.naming_protocol.handle_filename_collision(
                    target_path, enhanced_filename
                )
                target_path = target_dir / enhanced_filename
            
            # Step 4: Move the file (if not dry run)
            if dry_run:
                print(f"\n🔍 DRY RUN - Would move:")
                print(f"   From: {file_path}")
                print(f"   To:   {target_path}")
                result['action_taken'] = 'dry_run_preview'
                result['target_path'] = str(target_path)
            else:
                # Actually move the file
                shutil.move(str(file_path), str(target_path))
                print(f"\n✅ File moved successfully:")
                print(f"   From: {file_path}")
                print(f"   To:   {target_path}")
                result['action_taken'] = 'moved'
                result['target_path'] = str(target_path)
            
            result['success'] = True
            result['enhanced_filename'] = enhanced_filename
            result['classification'] = classification_dict
            result['confidence'] = classification_result.confidence
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Error organizing {file_path.name}: {e}")
        
        return result
    
    def _get_target_directory(self, classification_result) -> Path:
        """Determine the target directory based on classification"""
        
        category = classification_result.category.lower()
        
        # Map categories to folder structures
        if 'entertainment' in category:
            if any(person.lower().replace('_', ' ') in ['Client Name', 'finn'] 
                   for person in classification_result.people):
                return self.base_dir / "01_ACTIVE_PROJECTS" / "Entertainment_Industry" / "Current_Contracts" / "Client Name_Client"
            else:
                return self.base_dir / "01_ACTIVE_PROJECTS" / "Entertainment_Industry" / "Current_Contracts"
        
        elif 'creative' in category:
            if 'Creative Project' in ' '.join(classification_result.tags).lower():
                return self.base_dir / "01_ACTIVE_PROJECTS" / "Creative_Production" / "Papers_That_Dream"
            else:
                return self.base_dir / "01_ACTIVE_PROJECTS" / "Creative_Production"
        
        elif 'business' in category:
            if any(tag.lower() in ['financial', 'commission', 'invoice', 'tax'] 
                   for tag in classification_result.tags):
                return self.base_dir / "01_ACTIVE_PROJECTS" / "Business_Operations" / "Financial_Records"
            else:
                return self.base_dir / "01_ACTIVE_PROJECTS" / "Business_Operations"
        
        elif 'development' in category:
            return self.base_dir / "01_ACTIVE_PROJECTS" / "Development" / "AI_Projects"
        
        else:
            # Default to reference materials
            return self.base_dir / "03_REFERENCE_MATERIALS" / "Uncategorized"
    
    def batch_organize(self, file_paths: list, dry_run: bool = True, max_files: int = None) -> dict:
        """Organize multiple files with progress tracking"""
        
        print(f"\n🗂️  Batch Organization")
        print(f"{'='*60}")
        
        if max_files:
            file_paths = file_paths[:max_files]
        
        print(f"📁 Processing {len(file_paths)} files")
        print(f"🔧 Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
        
        results = {
            'total_files': len(file_paths),
            'successful': 0,
            'skipped': 0,
            'errors': 0,
            'file_results': []
        }
        
        for i, file_path in enumerate(file_paths, 1):
            print(f"\n📄 File {i}/{len(file_paths)}: {file_path.name}")
            print("-" * 50)
            
            try:
                file_result = self.organize_file(file_path, dry_run, show_preview=True)
                results['file_results'].append(file_result)
                
                if file_result['success']:
                    if file_result['action_taken'] in ['moved', 'dry_run_preview']:
                        results['successful'] += 1
                    else:
                        results['skipped'] += 1
                else:
                    results['errors'] += 1
                
                # Ask to continue (except for last file)
                if i < len(file_paths):
                    continue_choice = input(f"\nContinue to next file? (Y/n): ").strip().lower()
                    if continue_choice in ['n', 'no']:
                        print(f"⏹️  Stopping batch process")
                        break
                        
            except KeyboardInterrupt:
                print(f"\n⏹️  Batch process interrupted")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                results['errors'] += 1
                continue
        
        # Summary
        print(f"\n🎉 Batch Organization Complete!")
        print(f"   Total files: {results['total_files']}")
        print(f"   Successful: {results['successful']}")
        print(f"   Skipped: {results['skipped']}")
        print(f"   Errors: {results['errors']}")
        
        return results
    
    def quick_organize_folder(self, folder_path: Path, dry_run: bool = True, file_patterns: list = None) -> dict:
        """Quickly organize all files in a folder"""
        
        if not folder_path.exists():
            print(f"❌ Folder not found: {folder_path}")
            return {'success': False, 'error': 'Folder not found'}
        
        # Find files to organize
        files_to_process = []
        
        for file_path in folder_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                # Apply file patterns if specified
                if file_patterns:
                    if any(pattern.lower() in file_path.name.lower() for pattern in file_patterns):
                        files_to_process.append(file_path)
                else:
                    files_to_process.append(file_path)
        
        if not files_to_process:
            print(f"❌ No files found to organize in {folder_path}")
            return {'success': False, 'error': 'No files found'}
        
        print(f"\n📁 Quick Organize: {folder_path}")
        print(f"🔍 Found {len(files_to_process)} files to process")
        
        if file_patterns:
            print(f"🔍 Filtering for: {', '.join(file_patterns)}")
        
        return self.batch_organize(files_to_process, dry_run)

def main():
    """Command line interface for the integrated organizer"""
    
    print("🗂️  Integrated AI File Organizer")
    print("=" * 50)
    print("Combines classification, smart naming, and file organization")
    
    # Configuration
    organizer = IntegratedOrganizer()
    
    print(f"\n📍 Base directory: {organizer.base_dir}")
    
    # Quick test with Downloads staging
    staging_dir = get_ai_organizer_root() / "TEMP_PROCESSING" / "Downloads_Staging"
    
    if staging_dir.exists():
        print(f"\n📁 Found staging directory: {staging_dir}")
        
        # Find some test files
        test_files = []
        for file_path in staging_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                test_files.append(file_path)
            if len(test_files) >= 3:  # Limit for demo
                break
        
        if test_files:
            print(f"\n🧪 Demo files found:")
            for i, file_path in enumerate(test_files, 1):
                print(f"   {i}. {file_path.name}")
            
            print(f"\n⚙️  Options:")
            print(f"1. Organize single file (with preview)")
            print(f"2. Batch organize all files")
            print(f"3. Quick organize folder")
            
            choice = input(f"\nSelect option (1-3): ").strip()
            
            dry_run = True
            mode_choice = input(f"\nRun in DRY-RUN mode? (Y/n): ").strip().lower()
            if mode_choice in ['n', 'no']:
                dry_run = False
                print("⚠️  LIVE MODE - Files will be moved!")
            
            if choice == '1':
                # Single file demo
                file_path = test_files[0]
                print(f"\n📄 Organizing: {file_path.name}")
                result = organizer.organize_file(file_path, dry_run)
                print(f"\n📊 Result: {result}")
                
            elif choice == '2':
                # Batch demo
                results = organizer.batch_organize(test_files, dry_run)
                
            elif choice == '3':
                # Quick folder demo
                results = organizer.quick_organize_folder(staging_dir, dry_run, max_files=3)
            
            else:
                print("❌ Invalid choice")
        else:
            print("❌ No test files found in staging directory")
    else:
        print(f"❌ Staging directory not found: {staging_dir}")
        print("Create some test files there to try the organizer")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n👋 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")