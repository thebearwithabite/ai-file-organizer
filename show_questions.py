#!/usr/bin/env python3
"""
Show what questions the system would ask for your files
Non-interactive demonstration
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interactive_classifier import InteractiveClassifier
from classification_engine import FileClassificationEngine

def show_classification_questions():
    """Show what questions would be asked for real files"""
    
    print("🤔 Interactive Classification Preview")
    print("=" * 50)
    print("This shows what questions the system would ask for your files")
    
    # Get some interesting files
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
    
    classifier = FileClassificationEngine()
    interactive_classifier = InteractiveClassifier()
    
    for i, file_path in enumerate(test_files, 1):
        print(f"\n{'='*60}")
        print(f"📄 File {i}: {file_path.name}")
        print(f"{'='*60}")
        
        # Get initial classification
        result = classifier.classify_file(file_path)
        
        print(f"📊 Initial Analysis:")
        print(f"   Category: {result.category}")
        print(f"   Confidence: {result.confidence:.1f}%")
        print(f"   People: {', '.join(result.people) if result.people else 'None'}")
        print(f"   Tags: {', '.join(result.tags[:3]) if result.tags else 'None'}")
        print(f"   Suggested Path: {result.suggested_path}")
        
        if result.confidence < 85:
            print(f"\n🤔 WOULD ASK QUESTIONS (confidence {result.confidence:.1f}% < 85%)")
            
            # Determine what type of question would be asked
            uncertainty_type = interactive_classifier._identify_uncertainty_type(result, "")
            
            if uncertainty_type == "category_conflict":
                print(f"   Question Type: Category Conflict")
                print(f"   📝 Would Ask: 'This file could be entertainment, business, or creative.'")
                print(f"                 'Which category fits best?'")
                
            elif uncertainty_type == "person_identification":
                print(f"   Question Type: Person Identification") 
                print(f"   📝 Would Ask: 'This mentions {', '.join(result.people)}.'")
                print(f"                 'Who is it primarily about?'")
                
            elif uncertainty_type == "business_vs_creative":
                print(f"   Question Type: Business vs Creative")
                print(f"   📝 Would Ask: 'This has both business and creative elements.'")
                print(f"                 'What's the primary focus?'")
                
            elif uncertainty_type == "entertainment_specific":
                print(f"   Question Type: Entertainment Industry Specific")
                print(f"   📝 Would Ask: 'This entertainment document should be filed under:'")
                print(f"                 'Active projects, business ops, or archive?'")
            
            # Show likely options
            if "Client" in file_path.name.lower() or "finn" in file_path.name.lower():
                print(f"   🎯 Likely Options:")
                print(f"      1. Entertainment Industry (current projects)")
                print(f"      2. Business Operations (payroll, contracts)")
                print(f"      3. Archive (past work)")
                
            elif "management" in file_path.name.lower() or "agreement" in file_path.name.lower():
                print(f"   🎯 Likely Options:")
                print(f"      1. Entertainment Industry (talent management)")
                print(f"      2. Business Operations (legal, contracts)")
                
            elif "island" in file_path.name.lower() or "creative" in file_path.name.lower():
                print(f"   🎯 Likely Options:")
                print(f"      1. Creative Projects (scripts, stories)")
                print(f"      2. Entertainment Industry (production)")
                
            elif "ai" in file_path.name.lower() or "firebase" in file_path.name.lower():
                print(f"   🎯 Likely Options:")
                print(f"      1. Development Projects (tech, coding)")
                print(f"      2. Creative Projects (AI content)")
                
            print(f"   ✨ After your answer: Confidence would jump to 85%+ ✅")
            
        else:
            print(f"\n✅ HIGH CONFIDENCE - No questions needed!")
            print(f"   Would file automatically: {result.suggested_path}")
    
    print(f"\n🧠 How the Learning Works:")
    print(f"   • Your first answers teach the system your preferences")
    print(f"   • 'Client Name + contract' → Your choice gets remembered")
    print(f"   • Next similar file → Higher initial confidence")
    print(f"   • After 5-10 decisions → Most files auto-organize")
    
    print(f"\n🎯 ADHD Benefits:")
    print(f"   • No overwhelming choices (max 3 options)")
    print(f"   • Clear, specific questions")
    print(f"   • System learns YOUR patterns")
    print(f"   • Reduces decision fatigue over time")

if __name__ == "__main__":
    show_classification_questions()