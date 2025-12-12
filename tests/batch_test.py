#!/usr/bin/env python3
"""
Small batch test of interactive file organization
Safe test with 3-5 files from staging area
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interactive_organizer import InteractiveOrganizer

def get_interesting_files():
    """Get a small selection of interesting files for testing"""
    staging_dir = Path("/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging")
    
    if not staging_dir.exists():
        return []
    
    all_files = [f for f in staging_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
    
    # Pick some interesting files for testing
    interesting_files = []
    
    # Look for different types of files
    for file_path in all_files:
        name_lower = file_path.name.lower()
        
        # Client Name related
        if 'Client' in name_lower or 'finn' in name_lower:
            interesting_files.append(file_path)
        
        # Management/business
        elif 'management' in name_lower or 'agreement' in name_lower:
            interesting_files.append(file_path)
        
        # Creative content
        elif 'island' in name_lower or 'script' in name_lower or 'creative' in name_lower:
            interesting_files.append(file_path)
        
        # AI/tech content
        elif 'ai' in name_lower or 'firebase' in name_lower:
            interesting_files.append(file_path)
        
        # Financial/commission
        elif 'commission' in name_lower or 'payment' in name_lower:
            interesting_files.append(file_path)
        
        if len(interesting_files) >= 5:
            break
    
    return interesting_files[:5]

def batch_test():
    """Run a small batch test with user interaction"""
    
    print("🧪 Small Batch Test - Interactive File Organization")
    print("=" * 60)
    print("This will test the questioning system with 3-5 of your actual files")
    print("We'll use DRY-RUN mode so no files are actually moved")
    
    # Get test files
    test_files = get_interesting_files()
    
    if not test_files:
        print("❌ No files found in staging area")
        return
    
    print(f"\n📁 Found {len(test_files)} interesting files to test:")
    for i, file_path in enumerate(test_files, 1):
        print(f"  {i}. {file_path.name}")
    
    print(f"\n🤔 The system will analyze each file and ask questions when confidence < 85%")
    print(f"This helps you see how the interactive system works!")
    
    input(f"\nPress Enter to start the test...")
    
    # Initialize organizer
    organizer = InteractiveOrganizer()
    
    # Process each file
    for i, file_path in enumerate(test_files, 1):
        print(f"\n{'='*60}")
        print(f"📄 File {i}/{len(test_files)}: {file_path.name}")
        print(f"{'='*60}")
        
        # Test organization (dry run)
        try:
            organizer.organize_specific_file(file_path, dry_run=True)
        except KeyboardInterrupt:
            print(f"\n⏭️  Skipping to next file...")
            continue
        except Exception as e:
            print(f"❌ Error with this file: {e}")
            continue
        
        if i < len(test_files):
            print(f"\n⏭️  Ready for next file...")
            input("Press Enter to continue (or Ctrl+C to stop)...")
    
    print(f"\n🎉 Batch Test Complete!")
    print(f"📊 Summary:")
    print(f"   Files tested: {len(test_files)}")
    print(f"   Mode: DRY-RUN (no files were actually moved)")
    
    print(f"\n💡 What you learned:")
    print(f"   • How the system asks clarifying questions")
    print(f"   • What confidence levels trigger questions")
    print(f"   • How your answers teach the system")
    
    print(f"\n🚀 Next Steps:")
    print(f"   • Run with --live to actually organize files")
    print(f"   • System will remember your preferences")
    print(f"   • Future classifications will be more confident")

if __name__ == "__main__":
    try:
        batch_test()
    except KeyboardInterrupt:
        print(f"\n\n👋 Test stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")