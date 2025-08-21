#!/usr/bin/env python3
"""
Demo of Interactive Classification System
Shows how the questioning system works with simulated responses
"""

import sys
from pathlib import Path

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interactive_classifier import InteractiveClassifier

class DemoClassifier(InteractiveClassifier):
    """Demo version that simulates user responses"""
    
    def __init__(self, base_dir: str = None):
        super().__init__(base_dir)
        
        # Simulated user preferences for demo
        self.demo_responses = {
            "Client Name": "Entertainment Industry",
            "business contract": "Business Operations",
            "creative script": "Creative Projects",
            "Client": "Entertainment Industry",
            "COMMISSIONS": "Business Operations",
            "Island": "Creative Projects",
            "MANAGEMENT AGREEMENT": "Entertainment Industry"
        }
    
    def _ask_user_question(self, question):
        """Simulate user response based on content"""
        print(f"\n❓ {question.question_text}")
        print(f"   Reason: {question.reasoning}")
        print("\nOptions:")
        
        for i, option in enumerate(question.options, 1):
            print(f"  {i}. {option['label']}")
        
        # Smart response based on question content
        response_choice = 1  # Default
        
        question_lower = question.question_text.lower()
        
        # Check for known patterns
        for keyword, preferred_category in self.demo_responses.items():
            if keyword.lower() in question_lower:
                # Find matching option
                for i, option in enumerate(question.options):
                    if preferred_category.lower() in option['label'].lower():
                        response_choice = i + 1
                        break
                break
        
        selected = question.options[response_choice - 1]
        
        print(f"\n🤖 Demo Response: {response_choice}. {selected['label']}")
        
        from datetime import datetime
        from interactive_classifier import UserResponse
        
        return UserResponse(
            selected_option=selected,
            timestamp=datetime.now(),
            question_id=f"{question.uncertainty_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

def demo_interactive_classification():
    """Demo the interactive classification with sample files"""
    print("🎬 Interactive Classification Demo")
    print("=" * 50)
    print("This shows how the system asks questions and learns preferences")
    
    classifier = DemoClassifier()
    
    # Test files from your Downloads staging
    demo_files = [
        "Client PAYROLL DOCS 2.pdf",
        "SAMPLE_AGREEMENT_2016.pdf", 
        "SAMPLE_COMMISSIONS - Jan 2021.pdf",
        "client_contract_06.pdf",
        "Island in Space Clean.pdf"
    ]
    
    for filename in demo_files:
        print(f"\n{'='*60}")
        print(f"🗂️  DEMO: Classifying {filename}")
        print(f"{'='*60}")
        
        # Create a fake file path for demo
        file_path = Path(f"/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging/{filename}")
        
        # Simulate content based on filename
        content = f"Document: {filename}\n"
        if "Client" in filename.lower():
            content += "Client Name actor agreement contract entertainment"
        if "commission" in filename.lower():
            content += "payment commission business financial management"
        if "island" in filename.lower():
            content += "creative story script artistic project"
        if "management" in filename.lower():
            content += "management agreement entertainment business contract"
        
        # Run classification
        result = classifier.classify_with_questions(file_path, content)
        
        print(f"\n✅ FINAL RESULT:")
        print(f"   📁 Category: {result.category}")
        print(f"   📂 Subcategory: {result.subcategory}")
        print(f"   🎯 Confidence: {result.confidence:.1f}%")
        print(f"   📍 Suggested Path: {result.suggested_path}")
        print(f"   👥 People: {', '.join(result.people) if result.people else 'None'}")
        print(f"   🏷️  Tags: {', '.join(result.tags) if result.tags else 'None'}")
        print(f"   💭 Reasoning: {'; '.join(result.reasoning)}")
    
    print(f"\n🧠 LEARNING SUMMARY:")
    print("The system learned these preferences:")
    prefs = classifier.user_preferences
    
    if prefs.get("person_preferences"):
        print(f"   👤 People: {prefs['person_preferences']}")
    
    if prefs.get("keyword_boosts"):
        print(f"   🔑 Keywords: {prefs['keyword_boosts']}")
    
    decisions = len(prefs.get("decision_history", []))
    print(f"   📊 Total decisions learned from: {decisions}")
    
    print(f"\n🎯 NEXT TIME:")
    print("   • Similar files will have higher initial confidence")
    print("   • Fewer questions needed as system learns your patterns")
    print("   • Faster organization with better accuracy")

if __name__ == "__main__":
    demo_interactive_classification()