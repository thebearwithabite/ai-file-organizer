#!/usr/bin/env python3
"""
Computer Vision CLI for AI File Organizer
Test and use the Gemini 2.5 Flash vision analysis system
"""

import sys
import argparse
from pathlib import Path

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from vision_content_extractor import GeminiVisionExtractor
from content_extractor import ContentExtractor

def analyze_file(file_path: str, context: str = 'general'):
    """Analyze a single file with computer vision"""
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"👁️ Analyzing: {file_path.name}")
    print("-" * 50)
    
    # Try vision analysis first
    vision_extractor = GeminiVisionExtractor()
    
    if vision_extractor.can_process_file(file_path):
        result = vision_extractor.analyze_visual_content(file_path, context)
        
        print(f"✅ Vision Analysis: {'Success' if result.success else 'Failed'}")
        
        if result.success:
            print(f"📋 Content Type: {result.content_type}")
            print(f"🎯 Confidence: {result.confidence:.1%}")
            print(f"📂 Suggested Category: {result.suggested_category}")
            
            if result.subjects:
                print(f"👥 Subjects: {', '.join(result.subjects)}")
            
            if result.context:
                print(f"🌍 Context: {result.context}")
            
            if result.text_content:
                print(f"📝 Text Found: {result.text_content[:200]}{'...' if len(result.text_content) > 200 else ''}")
            
            if result.suggested_tags:
                print(f"🏷️ Tags: {', '.join(result.suggested_tags)}")
            
            print(f"\n💭 Reasoning:")
            for reason in result.reasoning:
                print(f"   • {reason}")
            
            print(f"\n📄 Full Description:")
            print(f"   {result.description}")
        else:
            print(f"❌ Error: {result.description}")
    else:
        print("❓ File type not supported for vision analysis")
        
        # Try regular content extraction
        content_extractor = ContentExtractor()
        content_result = content_extractor.extract_content(file_path)
        
        if content_result.get('success'):
            text = content_result.get('text', '')
            print(f"📝 Text Content: {text[:300]}{'...' if len(text) > 300 else ''}")
        else:
            print(f"❌ Content extraction failed: {content_result.get('metadata', {}).get('error', 'Unknown error')}")

def analyze_directory(dir_path: str, context: str = 'general', limit: int = 10):
    """Analyze all supported files in a directory"""
    
    dir_path = Path(dir_path)
    
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"❌ Directory not found: {dir_path}")
        return
    
    print(f"📁 Analyzing directory: {dir_path}")
    print("=" * 60)
    
    vision_extractor = GeminiVisionExtractor()
    
    # Find all supported files
    supported_files = []
    for file_path in dir_path.iterdir():
        if file_path.is_file() and vision_extractor.can_process_file(file_path):
            supported_files.append(file_path)
    
    if not supported_files:
        print("📝 No vision-compatible files found")
        return
    
    # Limit files for testing
    if len(supported_files) > limit:
        supported_files = supported_files[:limit]
        print(f"📊 Analyzing first {limit} files (out of {len(list(dir_path.iterdir()))} total)")
    
    # Batch analyze
    results = vision_extractor.batch_analyze_files(supported_files, context)
    
    # Summary
    successful = sum(1 for r in results if r.success)
    print(f"\n📊 Summary: {successful}/{len(results)} files analyzed successfully")
    
    # Show interesting results
    print(f"\n🎯 Most Confident Results:")
    confident_results = [(f, r) for f, r in zip(supported_files, results) if r.success and r.confidence > 0.7]
    confident_results.sort(key=lambda x: x[1].confidence, reverse=True)
    
    for i, (file_path, result) in enumerate(confident_results[:5], 1):
        print(f"   [{i}] {file_path.name}")
        print(f"       📋 {result.content_type} ({result.confidence:.1%})")
        print(f"       🏷️  {', '.join(result.suggested_tags[:3])}")

def test_vision_system():
    """Test the vision system with available files"""
    
    print("🧪 Testing Computer Vision System")
    print("=" * 40)
    
    # Test directories
    test_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Desktop", 
        Path("/Users/user/Desktop")
    ]
    
    for test_dir in test_dirs:
        if test_dir.exists():
            print(f"\n📁 Testing directory: {test_dir.name}")
            analyze_directory(str(test_dir), context='general', limit=3)
            break
    else:
        print("❌ No test directories found")

def setup_api_key():
    """Guide user through API key setup"""
    
    print("🔑 Computer Vision API Key Setup")
    print("=" * 35)
    print()
    print("To use computer vision features, you need a Google API key:")
    print()
    print("1. Go to: https://makersuite.google.com/app/apikey")
    print("2. Create a new API key")
    print("3. Set it in your environment:")
    print()
    print("   export GOOGLE_API_KEY='your-api-key-here'")
    print("   # or")
    print("   export GEMINI_API_KEY='your-api-key-here'")
    print()
    print("4. Install the required library:")
    print("   pip install google-generativeai")
    print()
    print("💰 Pricing: ~$0.005 per minute of video, ~$0.50 per 100 images")
    print("🚀 Includes: Gemini 2.5 Flash with image + video analysis")

def main():
    """Main CLI interface"""
    
    parser = argparse.ArgumentParser(
        description='AI File Organizer - Computer Vision CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vision_cli.py analyze screenshot.png
  vision_cli.py analyze video.mp4 --context entertainment
  vision_cli.py directory ~/Downloads --limit 5
  vision_cli.py test
  vision_cli.py setup
  
Context Options:
  general       - General image/video analysis
  entertainment - Entertainment industry focus (Client Name Wolfhard, etc.)
  creative      - Creative projects (Papers That Dream, AI content)
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze single file
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a single file')
    analyze_parser.add_argument('file', help='Path to image or video file')
    analyze_parser.add_argument('--context', choices=['general', 'entertainment', 'creative'], 
                               default='general', help='Analysis context')
    
    # Analyze directory
    directory_parser = subparsers.add_parser('directory', help='Analyze files in directory')
    directory_parser.add_argument('path', help='Path to directory')
    directory_parser.add_argument('--context', choices=['general', 'entertainment', 'creative'], 
                                 default='general', help='Analysis context')
    directory_parser.add_argument('--limit', type=int, default=10, help='Max files to analyze')
    
    # Test system
    test_parser = subparsers.add_parser('test', help='Test vision system with sample files')
    
    # Setup guide
    setup_parser = subparsers.add_parser('setup', help='Show API key setup instructions')
    
    args = parser.parse_args()
    
    # Default to setup if no command
    if not args.command:
        setup_api_key()
        return
    
    try:
        if args.command == 'analyze':
            analyze_file(args.file, args.context)
        elif args.command == 'directory':
            analyze_directory(args.path, args.context, args.limit)
        elif args.command == 'test':
            test_vision_system()
        elif args.command == 'setup':
            setup_api_key()
            
    except KeyboardInterrupt:
        print(f"\n👋 Vision analysis cancelled by user")
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()