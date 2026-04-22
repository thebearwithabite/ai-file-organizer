#!/usr/bin/env python3
"""
Command Line Interface for Multimedia Content Analysis
Easy-to-use commands for analyzing video, images, audio, and GIFs
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from multimedia_analyzer import MultimediaAnalyzer

def analyze_file(file_path: str, show_details: bool = True):
    """Analyze a single multimedia file"""
    
    print(f"🎬 Multimedia File Analysis")
    print("=" * 50)
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    analyzer = MultimediaAnalyzer()
    
    try:
        media_type = analyzer.get_media_type(file_path)
        if not media_type:
            print(f"❌ Unsupported file type: {file_path.suffix}")
            return
        
        print(f"📄 Analyzing: {file_path.name}")
        print(f"📁 Type: {media_type}")
        
        analysis = analyzer.analyze_file(file_path)
        
        if show_details:
            print(f"\n📊 Analysis Results:")
            print(f"   File Size: {analysis.file_size_mb:.1f} MB")
            print(f"   Content Type: {analysis.estimated_content_type}")
            print(f"   Confidence: {analysis.confidence_score:.1%}")
            
            if analysis.duration_seconds > 0:
                minutes = analysis.duration_seconds / 60
                print(f"   Duration: {minutes:.1f} minutes")
            
            if analysis.resolution:
                print(f"   Resolution: {analysis.resolution[0]}x{analysis.resolution[1]}")
            
            if analysis.codec:
                print(f"   Codec: {analysis.codec}")
            
            # Technical details
            if analysis.audio_characteristics:
                print(f"   Audio: {json.dumps(analysis.audio_characteristics, indent=6)}")
            
            if analysis.visual_characteristics:
                print(f"   Visual: {json.dumps(analysis.visual_characteristics, indent=6)}")
            
            print(f"   Suggested Category: {analysis.suggested_category}")
            print(f"   Tags: {', '.join(analysis.tags)}")
        
        # Save to database
        success = analyzer.save_analysis(analysis)
        print(f"\n💾 Saved to database: {'✅' if success else '❌'}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

def analyze_directory(directory: str, recursive: bool = True, filter_type: str = "all"):
    """Analyze all multimedia files in a directory"""
    
    print(f"📁 Directory Multimedia Analysis")
    print("=" * 60)
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    analyzer = MultimediaAnalyzer()
    
    # Filter by media type if specified
    if filter_type != "all":
        if filter_type not in analyzer.supported_types:
            print(f"❌ Invalid media type. Choose from: {list(analyzer.supported_types.keys())}")
            return
    
    print(f"📂 Analyzing: {dir_path}")
    print(f"🔍 Mode: {'Recursive' if recursive else 'Current directory only'}")
    print(f"🎯 Filter: {filter_type}")
    
    # Find files
    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"
    
    multimedia_files = []
    
    if filter_type == "all":
        # All media types
        for media_type, extensions in analyzer.supported_types.items():
            for ext in extensions:
                multimedia_files.extend(dir_path.glob(f"{pattern}{ext}"))
                multimedia_files.extend(dir_path.glob(f"{pattern}{ext.upper()}"))
    else:
        # Specific media type
        extensions = analyzer.supported_types[filter_type]
        for ext in extensions:
            multimedia_files.extend(dir_path.glob(f"{pattern}{ext}"))
            multimedia_files.extend(dir_path.glob(f"{pattern}{ext.upper()}"))
    
    multimedia_files = [f for f in multimedia_files if f.is_file()]
    
    if not multimedia_files:
        print(f"❌ No {filter_type} files found")
        return
    
    print(f"📊 Found {len(multimedia_files)} files to analyze\n")
    
    # Analyze files
    successful = 0
    failed = 0
    analyses = []
    
    for i, file_path in enumerate(multimedia_files, 1):
        print(f"📄 [{i}/{len(multimedia_files)}] {file_path.name}")
        
        try:
            analysis = analyzer.analyze_file(file_path)
            analyses.append(analysis)
            
            success = analyzer.save_analysis(analysis)
            if success:
                successful += 1
                print(f"   ✅ {analysis.media_type} - {analysis.estimated_content_type} ({analysis.confidence_score:.0%})")
                
                if analysis.duration_seconds > 0:
                    print(f"      ⏱️ {analysis.duration_seconds/60:.1f} min")
                
                if analysis.tags:
                    print(f"      🏷️ {', '.join(analysis.tags[:3])}")
            else:
                failed += 1
                print(f"   ❌ Analysis failed to save")
        
        except Exception as e:
            failed += 1
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    print(f"\n📊 Analysis Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    
    # Show content type breakdown
    if analyses:
        print(f"\n📈 Content Types Found:")
        content_types = {}
        for analysis in analyses:
            content_type = analysis.estimated_content_type or 'unknown'
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        for content_type, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {content_type}: {count} files")
    
    return analyses

def show_statistics():
    """Show multimedia analysis statistics"""
    
    print(f"📊 Multimedia Analysis Statistics")
    print("=" * 50)
    
    analyzer = MultimediaAnalyzer()
    results = analyzer.get_analysis_results(30)  # Last 30 days
    
    if not results:
        print("❌ No analysis results found")
        return
    
    print(f"📁 Total files analyzed: {len(results)}")
    
    # Media type breakdown
    media_types = {}
    content_types = {}
    categories = {}
    
    for result in results:
        # Media types
        media_type = result['media_type']
        media_types[media_type] = media_types.get(media_type, 0) + 1
        
        # Content types
        content_type = result['estimated_content_type'] or 'unknown'
        content_types[content_type] = content_types.get(content_type, 0) + 1
        
        # Categories
        category = result['suggested_category'] or 'uncategorized'
        categories[category] = categories.get(category, 0) + 1
    
    print(f"\n🎬 Media Types:")
    for media_type, count in sorted(media_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {media_type}: {count}")
    
    print(f"\n📝 Content Types:")
    for content_type, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {content_type}: {count}")
    
    print(f"\n📂 Suggested Categories:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"   {category}: {count}")
    
    # Confidence distribution
    high_conf = sum(1 for r in results if r['confidence_score'] >= 0.8)
    med_conf = sum(1 for r in results if 0.5 <= r['confidence_score'] < 0.8)
    low_conf = sum(1 for r in results if r['confidence_score'] < 0.5)
    
    print(f"\n🎯 Confidence Distribution:")
    print(f"   High (80%+): {high_conf}")
    print(f"   Medium (50-80%): {med_conf}")
    print(f"   Low (<50%): {low_conf}")
    
    # File sizes
    total_size = sum(r['file_size_mb'] for r in results if r['file_size_mb'])
    avg_size = total_size / len(results) if results else 0
    
    print(f"\n💾 File Sizes:")
    print(f"   Total: {total_size:.1f} MB")
    print(f"   Average: {avg_size:.1f} MB per file")

def show_supported_formats():
    """Show supported multimedia formats"""
    
    print(f"📋 Supported Multimedia Formats")
    print("=" * 50)
    
    analyzer = MultimediaAnalyzer()
    
    for media_type, extensions in analyzer.supported_types.items():
        print(f"\n🎬 {media_type.upper()}:")
        print(f"   {', '.join(extensions)}")
    
    print(f"\n💡 Analysis Features:")
    print(f"   • Content type detection (interview, scene, music, etc.)")
    print(f"   • Duration estimation for audio/video")
    print(f"   • Resolution estimation for images/video") 
    print(f"   • Quality assessment")
    print(f"   • Auto-tagging for organization")
    print(f"   • Project detection from filenames")

def main():
    """Command line interface for multimedia analysis"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Multimedia Content Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single file
  multimedia_cli.py file /path/to/video.mp4
  multimedia_cli.py file /path/to/photo.jpg --details
  
  # Analyze directory
  multimedia_cli.py directory /Users/user/Downloads
  multimedia_cli.py directory /Users/user/Movies --recursive --type video
  
  # View statistics and formats
  multimedia_cli.py stats
  multimedia_cli.py formats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Single file analysis
    file_parser = subparsers.add_parser('file', help='Analyze a single multimedia file')
    file_parser.add_argument('file_path', help='Path to multimedia file')
    file_parser.add_argument('--details', action='store_true', help='Show detailed analysis')
    
    # Directory analysis
    dir_parser = subparsers.add_parser('directory', help='Analyze all multimedia files in directory')
    dir_parser.add_argument('directory', help='Directory to analyze')
    dir_parser.add_argument('--recursive', action='store_true', help='Include subdirectories')
    dir_parser.add_argument('--type', choices=['all', 'image', 'video', 'audio'], default='all',
                           help='Filter by media type (default: all)')
    
    # Statistics
    subparsers.add_parser('stats', help='Show analysis statistics')
    
    # Supported formats
    subparsers.add_parser('formats', help='Show supported multimedia formats')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🎬 AI File Organizer - Multimedia Analysis")
    print("=" * 60)
    
    if args.command == 'file':
        analyze_file(args.file_path, args.details)
        
    elif args.command == 'directory':
        analyze_directory(args.directory, args.recursive, args.type)
        
    elif args.command == 'stats':
        show_statistics()
        
    elif args.command == 'formats':
        show_supported_formats()

if __name__ == "__main__":
    main()