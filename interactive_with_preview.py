#!/usr/bin/env python3
"""
Interactive File Organization with Content Preview
Shows file content before asking classification questions
"""

import sys
from pathlib import Path
import os

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interactive_classifier import InteractiveClassifier
from content_extractor import ContentExtractor
from classification_engine import FileClassificationEngine
from file_naming_protocol import FileNamingProtocol

class PreviewClassifier(InteractiveClassifier):
    """Interactive classifier that shows content previews"""
    
    def __init__(self, base_dir: str = None):
        super().__init__(base_dir)
        self.content_extractor = ContentExtractor(str(self.base_dir))
        self.naming_protocol = FileNamingProtocol()
    
    def classify_with_preview(self, file_path: Path, dry_run: bool = True) -> tuple:
        """Classify file with content preview and interactive questions"""
        
        print(f"\n{'='*70}")
        print(f"📄 Analyzing: {file_path.name}")
        print(f"{'='*70}")
        
        # Show file details
        try:
            stat = file_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            from datetime import datetime
            modified = datetime.fromtimestamp(stat.st_mtime)
            
            print(f"📊 File Info:")
            print(f"   Size: {size_mb:.1f} MB")
            print(f"   Modified: {modified.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Type: {file_path.suffix}")
        except:
            pass
        
        # Extract and show content preview
        print(f"\n🔍 Content Preview:")
        print("-" * 50)
        
        content = ""
        try:
            extraction_result = self.content_extractor.extract_content(file_path)
            if extraction_result['success']:
                content = extraction_result['text']
                
                # Show a meaningful preview
                preview_text = content[:800] if content else "Could not extract text content"
                print(preview_text)
                
                if len(content) > 800:
                    print(f"\n... [Content continues for {len(content) - 800} more characters]")
            else:
                print(f"❌ Could not extract content: {extraction_result.get('error', 'Unknown error')}")
                # Try filename-based analysis
                print(f"📝 Will analyze based on filename: {file_path.name}")
        
        except Exception as e:
            print(f"❌ Error extracting content: {e}")
            print(f"📝 Will analyze based on filename: {file_path.name}")
        
        print("-" * 50)
        
        # Get initial classification
        initial_result = self.base_classifier.classify_file(file_path)
        
        print(f"\n🤖 Initial AI Analysis:")
        print(f"   Suggested Category: {initial_result.category}")
        print(f"   Confidence: {initial_result.confidence:.1f}%")
        print(f"   Detected People: {', '.join(initial_result.people) if initial_result.people else 'None'}")
        print(f"   Tags: {', '.join(initial_result.tags[:3]) if initial_result.tags else 'None'}")
        print(f"   Reasoning: {'; '.join(initial_result.reasoning[:2])}")
        
        # Ask user if they want to proceed with questions
        if initial_result.confidence >= 85:
            print(f"\n✅ High confidence classification!")
            print(f"   Would file to: {initial_result.suggested_path}")
            
            proceed = input(f"\nAccept this classification? (y/n): ").strip().lower()
            if proceed in ['y', 'yes', '']:
                return initial_result, True
            else:
                print(f"Proceeding with interactive questions...")
        
        print(f"\n🤔 Confidence too low ({initial_result.confidence:.1f}% < 85%) - asking questions...")
        
        # Now run interactive classification with the preview context
        result = self.classify_with_questions(file_path, content)
        
        # Generate enhanced filename using naming protocol
        extraction_result = {'text': content} if content else None
        classification_dict = {
            'category': result.category,
            'people': result.people,
            'tags': result.tags
        }
        
        enhanced_filename = self.naming_protocol.generate_enhanced_filename(
            file_path, classification_dict, extraction_result
        )
        
        # Preview the naming change
        naming_preview = self.naming_protocol.preview_renaming(
            file_path, classification_dict, extraction_result
        )
        
        # Show final decision
        print(f"\n✅ Final Classification:")
        print(f"   Category: {result.category}")
        print(f"   Confidence: {result.confidence:.1f}%")
        print(f"   Will file to: {result.suggested_path}")
        print(f"\n📝 File Naming:")
        print(f"   Current name: {naming_preview['original_name']}")
        print(f"   Enhanced name: {naming_preview['enhanced_name']}")
        
        components = naming_preview['components']
        print(f"   📅 Date: {components.date}")
        print(f"   🏷️  Project: {components.project}")
        print(f"   👤 Client: {components.client}")
        print(f"   📄 Content: {components.content_type}")
        print(f"   🔢 Version: {components.version}")
        
        if naming_preview['is_meaningful_change']:
            print(f"   ✅ Meaningful filename improvement")
        else:
            print(f"   ⚠️  Minimal filename change")
        
        if dry_run:
            print(f"   🔍 DRY RUN - No files moved")
        else:
            confirm = input(f"\nMove this file? (y/n): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print(f"   ⏭️  Skipped")
                return result, False
        
        return result, True
    
    def _ask_user_question(self, question):
        """Enhanced question asking with better formatting"""
        print(f"\n" + "="*60)
        print(f"❓ CLASSIFICATION QUESTION")
        print(f"="*60)
        print(f"Based on the content preview above:")
        print(f"\n{question.question_text}")
        print(f"\n💭 Why I'm asking: {question.reasoning}")
        
        print(f"\nOptions:")
        for i, option in enumerate(question.options, 1):
            print(f"  {i}. {option['label']}")
        
        while True:
            try:
                choice = input(f"\nYour choice (1-{len(question.options)}): ").strip()
                
                if not choice:
                    print("Please enter a number")
                    continue
                    
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(question.options):
                    selected = question.options[choice_num - 1]
                    print(f"✅ You chose: {selected['label']}")
                    break
                else:
                    print(f"Please enter a number between 1 and {len(question.options)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n⏭️  Using first option...")
                selected = question.options[0]
                break
        
        from datetime import datetime
        from interactive_classifier import UserResponse
        
        return UserResponse(
            selected_option=selected,
            timestamp=datetime.now(),
            question_id=f"{question.uncertainty_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

def run_interactive_batch():
    """Run interactive organization with previews"""
    
    print("🔍 Interactive File Organization with Previews")
    print("=" * 60)
    print("This will show you file contents before asking classification questions")
    
    # Get test files
    staging_dir = Path("/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging")
    
    if not staging_dir.exists():
        print("❌ Staging directory not found")
        return
    
    # Find interesting files
    test_files = []
    for file_path in staging_dir.iterdir():
        if file_path.is_file() and not file_path.name.startswith('.'):
            name_lower = file_path.name.lower()
            if any(keyword in name_lower for keyword in ['Client', 'finn', 'management', 'island', 'ai', 'commission']):
                test_files.append(file_path)
        if len(test_files) >= 5:
            break
    
    if not test_files:
        print("❌ No interesting files found for testing")
        return
    
    print(f"\n📁 Found {len(test_files)} files to organize:")
    for i, file_path in enumerate(test_files, 1):
        print(f"  {i}. {file_path.name}")
    
    print(f"\n💡 For each file, you'll see:")
    print(f"   • File info (size, date, type)")
    print(f"   • Content preview (first ~800 characters)")
    print(f"   • AI's initial analysis")
    print(f"   • Questions if confidence < 85%")
    
    dry_run = True
    mode_choice = input(f"\nRun in DRY-RUN mode (no files moved)? (Y/n): ").strip().lower()
    if mode_choice in ['n', 'no']:
        dry_run = False
        print("⚠️  LIVE MODE - Files will actually be moved!")
    else:
        print("🔍 DRY-RUN MODE - No files will be moved")
    
    input(f"\nPress Enter to start...")
    
    # Initialize classifier
    classifier = PreviewClassifier()
    
    # Process files
    processed = 0
    for i, file_path in enumerate(test_files, 1):
        try:
            print(f"\n🗂️  Processing file {i}/{len(test_files)}")
            
            result, success = classifier.classify_with_preview(file_path, dry_run)
            
            if success:
                processed += 1
            
            if i < len(test_files):
                next_choice = input(f"\nContinue to next file? (Y/n): ").strip().lower()
                if next_choice in ['n', 'no']:
                    break
                    
        except KeyboardInterrupt:
            print(f"\n⏭️  Stopping...")
            break
        except Exception as e:
            print(f"\n❌ Error processing {file_path.name}: {e}")
            continue
    
    print(f"\n🎉 Batch Processing Complete!")
    print(f"   Files processed: {processed}/{len(test_files)}")
    print(f"   Mode: {'LIVE' if not dry_run else 'DRY-RUN'}")
    
    # Show learning summary
    prefs = classifier.user_preferences
    if prefs.get("decision_history"):
        print(f"\n🧠 Learning Summary:")
        print(f"   Decisions made: {len(prefs['decision_history'])}")
        if prefs.get("person_preferences"):
            print(f"   Person preferences learned: {len(prefs['person_preferences'])}")
        if prefs.get("keyword_boosts"):
            print(f"   Keyword associations: {len(prefs['keyword_boosts'])}")

if __name__ == "__main__":
    try:
        run_interactive_batch()
    except KeyboardInterrupt:
        print(f"\n\n👋 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")