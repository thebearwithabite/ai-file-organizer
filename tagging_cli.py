#!/usr/bin/env python3
"""
Command Line Interface for Comprehensive Tagging System
Easy-to-use commands for tagging files and finding content by tags
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from tagging_system import ComprehensiveTaggingSystem

def tag_file(file_path: str, user_tags: str = "", show_suggestions: bool = False):
    """Tag a single file with auto-tagging and optional user tags"""
    
    print(f"🏷️  File Tagging")
    print("=" * 40)
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    tagger = ComprehensiveTaggingSystem()
    
    # Parse user tags
    user_tag_list = [tag.strip() for tag in user_tags.split(',') if tag.strip()] if user_tags else []
    
    print(f"📄 Tagging: {file_path.name}")
    if user_tag_list:
        print(f"👤 User tags: {', '.join(user_tag_list)}")
    
    try:
        # Tag the file
        tagged_file = tagger.tag_file(file_path, user_tag_list)
        
        print(f"\n🎯 Results:")
        print(f"   Auto tags: {len(tagged_file.auto_tags)}")
        print(f"   User tags: {len(tagged_file.user_tags)}")
        
        # Show top auto tags
        if tagged_file.auto_tags:
            print(f"\n🤖 Top Auto Tags:")
            
            # Sort by confidence
            auto_with_confidence = [(tag, tagged_file.confidence_scores.get(tag, 0)) 
                                   for tag in tagged_file.auto_tags]
            auto_with_confidence.sort(key=lambda x: x[1], reverse=True)
            
            for i, (tag, confidence) in enumerate(auto_with_confidence[:10], 1):
                source = tagged_file.tag_sources.get(tag, 'unknown')
                print(f"   {i:2d}. {tag} ({confidence:.0%}) - {source}")
        
        # Show user tags
        if tagged_file.user_tags:
            print(f"\n👤 User Tags:")
            for i, tag in enumerate(tagged_file.user_tags, 1):
                print(f"   {i:2d}. {tag}")
        
        # Save to database
        success = tagger.save_tagged_file(tagged_file)
        print(f"\n💾 Saved to database: {'✅' if success else '❌'}")
        
        # Show suggestions if requested
        if show_suggestions:
            print(f"\n💡 Tag Suggestions:")
            suggestions = tagger.suggest_tags(file_path)
            
            if suggestions:
                for i, suggestion in enumerate(suggestions[:5], 1):
                    print(f"   {i}. {suggestion.tag} ({suggestion.confidence:.0%}) - {suggestion.reasoning}")
            else:
                print("   No additional suggestions")
        
        return tagged_file
        
    except Exception as e:
        print(f"❌ Tagging failed: {e}")
        return None

def tag_directory(directory: str, recursive: bool = True, file_pattern: str = "*"):
    """Tag all files in a directory"""
    
    print(f"📁 Directory Tagging")
    print("=" * 50)
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    tagger = ComprehensiveTaggingSystem()
    
    print(f"📂 Directory: {dir_path}")
    print(f"🔍 Pattern: {file_pattern}")
    print(f"📊 Recursive: {recursive}")
    
    # Find files to tag
    if recursive:
        search_pattern = f"**/{file_pattern}"
    else:
        search_pattern = file_pattern
    
    files_to_tag = [f for f in dir_path.glob(search_pattern) 
                    if f.is_file() and not f.name.startswith('.')]
    
    # Filter to supported file types
    supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.rtf', '.py', '.js', '.html'}
    files_to_tag = [f for f in files_to_tag if f.suffix.lower() in supported_extensions]
    
    if not files_to_tag:
        print(f"❌ No supported files found")
        return
    
    print(f"\n🎯 Found {len(files_to_tag)} files to tag")
    
    successful = 0
    failed = 0
    
    for i, file_path in enumerate(files_to_tag, 1):
        print(f"\n📄 [{i}/{len(files_to_tag)}] {file_path.name}")
        
        try:
            tagged_file = tagger.tag_file(file_path)
            success = tagger.save_tagged_file(tagged_file)
            
            if success:
                successful += 1
                top_tags = sorted([(tag, tagged_file.confidence_scores.get(tag, 0)) 
                                 for tag in tagged_file.auto_tags], 
                                key=lambda x: x[1], reverse=True)[:3]
                
                print(f"   ✅ Tagged with {len(tagged_file.auto_tags)} auto tags")
                print(f"      Top: {', '.join([f'{tag}({conf:.0%})' for tag, conf in top_tags])}")
            else:
                failed += 1
                print(f"   ❌ Failed to save tags")
        
        except Exception as e:
            failed += 1
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    print(f"\n📊 Tagging Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")

def search_by_tags(tags: str, match_all: bool = False, limit: int = 20):
    """Search for files by tags"""
    
    print(f"🔍 Tag-Based File Search")
    print("=" * 50)
    
    tagger = ComprehensiveTaggingSystem()
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    if not tag_list:
        print("❌ No tags specified")
        return
    
    print(f"🏷️  Search tags: {', '.join(tag_list)}")
    print(f"📊 Match mode: {'ALL tags' if match_all else 'ANY tag'}")
    print(f"📈 Limit: {limit} results")
    
    # Search for files
    results = tagger.find_files_by_tags(tag_list, match_all=match_all, limit=limit)
    
    if not results:
        print(f"\n❌ No files found with specified tags")
        return
    
    print(f"\n🎯 Found {len(results)} matching files:")
    
    for i, result in enumerate(results, 1):
        file_path = Path(result['file_path'])
        matching_tags = result['matching_tags']
        all_tags = result['all_tags']
        
        print(f"\n📄 {i}. {file_path.name}")
        print(f"   📁 Path: {file_path.parent}")
        print(f"   🏷️  Matching: {', '.join(matching_tags)}")
        
        # Show other relevant tags
        other_tags = [tag for tag in all_tags if tag not in matching_tags][:5]
        if other_tags:
            print(f"   🔖 Other tags: {', '.join(other_tags)}")
        
        print(f"   📅 Tagged: {result['last_tagged'][:10]}")
    
    return results

def show_file_tags(file_path: str):
    """Show all tags for a specific file"""
    
    print(f"🔖 File Tag Details")
    print("=" * 40)
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    tagger = ComprehensiveTaggingSystem()
    file_tags = tagger.get_file_tags(file_path)
    
    if not file_tags:
        print(f"❌ No tags found for: {file_path.name}")
        print(f"💡 Run: tagging_cli.py tag '{file_path}' to tag this file")
        return
    
    print(f"📄 File: {file_path.name}")
    print(f"📅 Tagged: {file_tags['last_tagged'][:19].replace('T', ' ')}")
    
    # Show auto tags
    auto_tags = file_tags.get('auto_tags', [])
    if auto_tags:
        print(f"\n🤖 Auto Tags ({len(auto_tags)}):")
        
        # Sort by confidence
        confidence_scores = file_tags.get('confidence_scores', {})
        tag_sources = file_tags.get('tag_sources', {})
        
        auto_with_conf = [(tag, confidence_scores.get(tag, 0), tag_sources.get(tag, 'unknown')) 
                         for tag in auto_tags]
        auto_with_conf.sort(key=lambda x: x[1], reverse=True)
        
        for i, (tag, confidence, source) in enumerate(auto_with_conf, 1):
            print(f"   {i:2d}. {tag} ({confidence:.0%}) - {source}")
    
    # Show user tags
    user_tags = file_tags.get('user_tags', [])
    if user_tags:
        print(f"\n👤 User Tags ({len(user_tags)}):")
        for i, tag in enumerate(user_tags, 1):
            print(f"   {i:2d}. {tag}")
    
    if not auto_tags and not user_tags:
        print(f"❌ No tags found")

def show_statistics():
    """Show tagging system statistics"""
    
    print(f"📊 Tagging System Statistics")
    print("=" * 50)
    
    tagger = ComprehensiveTaggingSystem()
    stats = tagger.get_tag_statistics()
    
    print(f"📈 Overview:")
    print(f"   Total unique tags: {stats['total_tags']}")
    print(f"   Files tagged this week: {stats['recent_activity']['files_tagged_last_week']}")
    print(f"   Unique files with tags: {stats['recent_activity']['unique_files_tagged']}")
    
    # Most used tags
    if stats['most_used_tags']:
        print(f"\n🏆 Most Used Tags:")
        for i, tag_info in enumerate(stats['most_used_tags'][:10], 1):
            tag = tag_info['tag']
            usage = tag_info['usage_count']
            files = tag_info['file_count']
            confidence = tag_info['average_confidence']
            
            print(f"   {i:2d}. {tag}")
            print(f"       📊 {usage} uses across {files} files (avg confidence: {confidence:.0%})")
    
    # Category distribution
    if stats['category_distribution']:
        print(f"\n📂 Tag Categories:")
        for cat_info in stats['category_distribution']:
            category = cat_info['category']
            count = cat_info['count']
            usage = cat_info['total_usage']
            
            print(f"   {category}: {count} unique tags, {usage} total uses")

def suggest_tags_for_file(file_path: str, limit: int = 10):
    """Show tag suggestions for a file"""
    
    print(f"💡 Tag Suggestions")
    print("=" * 40)
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    tagger = ComprehensiveTaggingSystem()
    suggestions = tagger.suggest_tags(file_path)
    
    print(f"📄 File: {file_path.name}")
    
    if not suggestions:
        print(f"❌ No tag suggestions available")
        return
    
    print(f"\n💡 Suggested Tags (top {min(limit, len(suggestions))}):")
    
    for i, suggestion in enumerate(suggestions[:limit], 1):
        print(f"\n   {i:2d}. {suggestion.tag} ({suggestion.confidence:.0%})")
        print(f"       Source: {suggestion.source}")
        print(f"       Reason: {suggestion.reasoning}")
        
        if suggestion.similar_files:
            similar_names = [f.name for f in suggestion.similar_files[:2]]
            print(f"       Similar files: {', '.join(similar_names)}")

def main():
    """Command line interface for tagging system"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Comprehensive Tagging System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Tag single file
  tagging_cli.py tag document.pdf
  tagging_cli.py tag script.docx --user-tags "draft,client-work,important"
  
  # Tag directory
  tagging_cli.py directory /Users/user/Downloads
  tagging_cli.py directory /Users/user/Documents --pattern "*.pdf"
  
  # Search by tags
  tagging_cli.py search "project:,netflix"
  tagging_cli.py search "contract,client" --match-all
  
  # View file tags
  tagging_cli.py show document.pdf
  
  # Get suggestions
  tagging_cli.py suggest new_file.docx
  
  # View statistics
  tagging_cli.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Tag single file
    tag_parser = subparsers.add_parser('tag', help='Tag a single file')
    tag_parser.add_argument('file_path', help='Path to file to tag')
    tag_parser.add_argument('--user-tags', default='', help='Comma-separated user tags')
    tag_parser.add_argument('--suggestions', action='store_true', help='Show tag suggestions')
    
    # Tag directory
    dir_parser = subparsers.add_parser('directory', help='Tag all files in directory')
    dir_parser.add_argument('directory', help='Directory to process')
    dir_parser.add_argument('--pattern', default='*', help='File pattern to match (default: *)')
    dir_parser.add_argument('--no-recursive', action='store_true', help="Don't process subdirectories")
    
    # Search by tags
    search_parser = subparsers.add_parser('search', help='Search files by tags')
    search_parser.add_argument('tags', help='Comma-separated tags to search for')
    search_parser.add_argument('--match-all', action='store_true', help='File must have ALL specified tags')
    search_parser.add_argument('--limit', type=int, default=20, help='Maximum results (default: 20)')
    
    # Show file tags
    show_parser = subparsers.add_parser('show', help='Show tags for a specific file')
    show_parser.add_argument('file_path', help='Path to file')
    
    # Tag suggestions
    suggest_parser = subparsers.add_parser('suggest', help='Show tag suggestions for a file')
    suggest_parser.add_argument('file_path', help='Path to file')
    suggest_parser.add_argument('--limit', type=int, default=10, help='Number of suggestions (default: 10)')
    
    # Statistics
    subparsers.add_parser('stats', help='Show tagging system statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🏷️  AI File Organizer - Comprehensive Tagging")
    print("=" * 60)
    
    if args.command == 'tag':
        tag_file(args.file_path, args.user_tags, args.suggestions)
        
    elif args.command == 'directory':
        tag_directory(args.directory, not args.no_recursive, args.pattern)
        
    elif args.command == 'search':
        search_by_tags(args.tags, args.match_all, args.limit)
        
    elif args.command == 'show':
        show_file_tags(args.file_path)
        
    elif args.command == 'suggest':
        suggest_tags_for_file(args.file_path, args.limit)
        
    elif args.command == 'stats':
        show_statistics()

if __name__ == "__main__":
    main()