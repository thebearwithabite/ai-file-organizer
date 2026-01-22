#!/usr/bin/env python3
"""
Test metadata generation with project files
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from metadata_generator import MetadataGenerator

def test_with_project_files():
    """Test metadata generation using the AI organizer project files"""
    
    print("🧪 Testing Metadata Generation with Project Files")
    print("=" * 60)
    
    generator = MetadataGenerator()
    
    # Use some of our project files for testing
    project_files = [
        project_dir / "README.md",
        project_dir / "CLAUDE.md", 
        project_dir / "interactive_classifier.py",
        project_dir / "file_naming_protocol.py"
    ]
    
    # Filter to existing files
    test_files = [f for f in project_files if f.exists()]
    
    if not test_files:
        print("❌ No test files found")
        return
    
    print(f"📁 Analyzing {len(test_files)} project files...")
    
    for file_path in test_files:
        print(f"\n📄 Analyzing: {file_path.name}")
        
        try:
            metadata = generator.analyze_file_comprehensive(file_path)
            
            # Show key results
            print(f"   📊 Category: {metadata.get('ai_category', 'Unknown')}")
            print(f"   🎯 Confidence: {metadata.get('confidence_score', 0)*100:.1f}%")
            print(f"   📝 Word count: {metadata.get('word_count', 0):,}")
            print(f"   📦 File size: {metadata.get('file_size', 0)/1024:.1f} KB")
            print(f"   🔖 Tags: {metadata.get('auto_tags', '[]')[:50]}...")
            
            # Save to database
            success = generator.save_file_metadata(metadata)
            print(f"   💾 Saved: {'✅' if success else '❌'}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Generate spreadsheet
    print(f"\n📊 Generating comprehensive spreadsheet...")
    
    try:
        output_path, df = generator.generate_comprehensive_spreadsheet()
        
        if output_path and df is not None:
            print(f"✅ Spreadsheet generated: {Path(output_path).name}")
            print(f"📈 Statistics:")
            print(f"   Total files in database: {len(df)}")
            print(f"   File types: {df['file_type'].nunique()}")
            print(f"   Categories: {df['ai_category'].nunique()}")
            print(f"   Average confidence: {df['confidence_score'].mean()*100:.1f}%")
            
            # Show sample data
            print(f"\n📋 Sample Data:")
            sample_cols = ['file_name', 'ai_category', 'confidence_percentage', 'word_count']
            available_cols = [col for col in sample_cols if col in df.columns]
            if available_cols:
                print(df[available_cols].head(3).to_string(index=False))
        else:
            print("❌ Failed to generate spreadsheet")
    
    except Exception as e:
        print(f"❌ Spreadsheet generation failed: {e}")

if __name__ == "__main__":
    test_with_project_files()