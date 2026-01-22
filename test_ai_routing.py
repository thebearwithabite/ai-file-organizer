#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from unified_classifier import UnifiedClassificationService

def test_routing():
    print("Testing AI Routing...")
    classifier = UnifiedClassificationService()
    test_file = Path("/Users/ryanthomson/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive/_Admin/99_TEMP_PROCESSING/Desktop/Passwords.pdf")
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return

    print(f"Classifying: {test_file.name}")
    result = classifier.classify_file(test_file)
    
    print("-" * 50)
    print(f"Source: {result.get('source')}")
    print(f"Category: {result.get('category')}")
    print(f"Confidence: {result.get('confidence')}")
    print(f"Reasoning: {result.get('reasoning')}")
    print("-" * 50)

if __name__ == "__main__":
    test_routing()
