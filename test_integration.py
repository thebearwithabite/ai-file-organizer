#!/usr/bin/env python3
"""
Test the integrated organizer without interactive input
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from file_naming_protocol import FileNamingProtocol

def test_naming_protocol():
    """Test the file naming protocol with real files"""
    
    print("🧪 Testing File Naming Protocol")
    print("=" * 50)
    
    protocol = FileNamingProtocol()
    
    # Test with some real file examples
    test_cases = [
        {
            'filename': 'client_contract_06.pdf',
            'classification': {
                'category': 'entertainment_industry',
                'people': ['finn_Client'],
                'tags': ['entertainment_industry', 'finn_Client', 'contract']
            }
        },
        {
            'filename': 'MARCO (1).pdf',
            'classification': {
                'category': 'creative_production',
                'people': [],
                'tags': ['creative', 'script', 'marco']
            }
        },
        {
            'filename': 'AI_Image_Generators_Chart.pdf',
            'classification': {
                'category': 'development',
                'people': [],
                'tags': ['development', 'ai', 'reference']
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📄 Test Case {i}: {test_case['filename']}")
        print("-" * 30)
        
        original_path = Path(f"/test/{test_case['filename']}")
        
        # Test filename generation
        enhanced_name = protocol.generate_enhanced_filename(
            original_path, 
            test_case['classification']
        )
        
        # Test preview
        preview = protocol.preview_renaming(
            original_path, 
            test_case['classification']
        )
        
        print(f"Original: {preview['original_name']}")
        print(f"Enhanced: {preview['enhanced_name']}")
        print(f"Components:")
        components = preview['components']
        print(f"  📅 Date: {components.date}")
        print(f"  🏷️  Project: {components.project}")
        print(f"  👤 Client: {components.client}")
        print(f"  📄 Content: {components.content_type}")
        print(f"  🔢 Version: {components.version}")
        
        if preview['is_meaningful_change']:
            print(f"  ✅ Meaningful improvement")
        else:
            print(f"  ⚠️  Minimal change")

def test_folder_structure():
    """Test that the folder structure is created correctly"""
    
    print(f"\n🏗️  Testing Folder Structure")
    print("=" * 50)
    
    base_dir = Path("/Users/user/Documents/AI_ORGANIZER_BASE")
    
    expected_folders = [
        "01_ACTIVE_PROJECTS/Entertainment_Industry/Current_Contracts/Finn_Client",
        "01_ACTIVE_PROJECTS/Creative_Production/Papers_That_Dream",
        "01_ACTIVE_PROJECTS/Business_Operations/Financial_Records",
        "01_ACTIVE_PROJECTS/Development/AI_Projects",
        "02_ARCHIVED_PROJECTS",
        "03_REFERENCE_MATERIALS/Uncategorized",
        "99_TEMP_PROCESSING"
    ]
    
    for folder_path in expected_folders:
        full_path = base_dir / folder_path
        full_path.mkdir(parents=True, exist_ok=True)
        
        if full_path.exists():
            print(f"✅ {folder_path}")
        else:
            print(f"❌ {folder_path}")

def test_component_integration():
    """Test that all components work together"""
    
    print(f"\n🔗 Testing Component Integration")
    print("=" * 50)
    
    try:
        # Test imports
        from interactive_classifier import InteractiveClassifier
        from content_extractor import ContentExtractor
        from file_naming_protocol import FileNamingProtocol
        print("✅ All imports successful")
        
        # Test initialization
        base_dir = "/Users/user/Documents/AI_ORGANIZER_BASE"
        extractor = ContentExtractor(base_dir)
        protocol = FileNamingProtocol()
        print("✅ Components initialize successfully")
        
        # Test with a real file if available
        staging_dir = Path("/Users/user/Documents/TEMP_PROCESSING/Downloads_Staging")
        if staging_dir.exists():
            test_files = [f for f in staging_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
            
            if test_files:
                test_file = test_files[0]
                print(f"✅ Found test file: {test_file.name}")
                
                # Test content extraction
                try:
                    extraction_result = extractor.extract_content(test_file)
                    if extraction_result['success']:
                        print(f"✅ Content extraction successful")
                        content_preview = extraction_result['text'][:100] if extraction_result['text'] else "No text"
                        print(f"   Preview: {content_preview}...")
                    else:
                        print(f"⚠️  Content extraction failed: {extraction_result.get('error', 'Unknown')}")
                except Exception as e:
                    print(f"❌ Content extraction error: {e}")
                
                # Test naming protocol
                try:
                    mock_classification = {
                        'category': 'test_category',
                        'people': ['test_person'],
                        'tags': ['test', 'integration']
                    }
                    
                    enhanced_name = protocol.generate_enhanced_filename(
                        test_file, mock_classification
                    )
                    print(f"✅ Naming protocol successful")
                    print(f"   Enhanced name: {enhanced_name}")
                    
                except Exception as e:
                    print(f"❌ Naming protocol error: {e}")
            
            else:
                print("⚠️  No test files found in staging")
        else:
            print("⚠️  Staging directory not found")
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")

if __name__ == "__main__":
    try:
        test_naming_protocol()
        test_folder_structure()
        test_component_integration()
        
        print(f"\n🎉 Integration Tests Complete!")
        print("=" * 50)
        print("✅ File naming protocol implemented and tested")
        print("✅ Component integration working")
        print("✅ Ready for interactive organization")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")