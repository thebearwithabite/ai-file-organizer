#!/usr/bin/env python3
"""
Test interactive classification with a single real file
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interactive_classifier import InteractiveClassifier

def test_single_file():
    """Test with one of User's actual files"""
    
    # Test with a file from Downloads staging
    test_files = [
        "/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging/Client PAYROLL DOCS 2.pdf",
        "/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging/SAMPLE_AGREEMENT_2016.pdf",
        "/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging/client_contract_06.pdf",
        "/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging/AI_Image_Generators_Chart.pdf",
    ]
    
    classifier = InteractiveClassifier()
    
    for test_path in test_files:
        file_path = Path(test_path)
        if file_path.exists():
            print(f"✅ Found file to test: {file_path.name}")
            
            # Show what the system would ask about
            initial_result = classifier.base_classifier.classify_file(file_path)
            
            print(f"\n📊 Initial Analysis:")
            print(f"   Category: {initial_result.category}")
            print(f"   Confidence: {initial_result.confidence:.1f}%")
            print(f"   People: {', '.join(initial_result.people) if initial_result.people else 'None detected'}")
            print(f"   Tags: {', '.join(initial_result.tags) if initial_result.tags else 'None detected'}")
            print(f"   Reasoning: {'; '.join(initial_result.reasoning)}")
            
            if initial_result.confidence < 85:
                print(f"\n🤔 This would trigger questions because confidence is {initial_result.confidence:.1f}% < 85%")
                print(f"   The system would ask about:")
                
                # Show what types of questions would be asked
                if len(initial_result.people) > 1:
                    print(f"   • Who is this primarily about? ({', '.join(initial_result.people)})")
                
                if "contract" in file_path.name.lower() or "agreement" in file_path.name.lower():
                    print(f"   • Is this business operations or entertainment industry?")
                
                if "finn" in file_path.name.lower() or "Client" in file_path.name.lower():
                    print(f"   • Is this about current entertainment projects or business operations?")
            else:
                print(f"\n✅ High confidence - no questions needed!")
            
            print(f"   Suggested path: {initial_result.suggested_path}")
            
            return  # Test just the first file found
    
    print("❌ No test files found in staging area")

if __name__ == "__main__":
    test_single_file()