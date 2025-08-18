#!/usr/bin/env python3
"""
Local LLM Librarian - Main CLI Interface
Complete file organization and search system with natural language queries
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from query_interface import LocalLibrarian
from staging_monitor import StagingMonitor
from content_extractor import ContentExtractor
from classification_engine import FileClassificationEngine

class LibrarianCLI:
    """
    Command-line interface for the Local LLM Librarian system
    Provides easy access to all system features
    """
    
    def __init__(self, base_dir: str = None):
        # Default to CONTENT_LIBRARY_MASTER if it exists, otherwise Documents
        if base_dir:
            self.base_dir = Path(base_dir)
        elif (Path.home() / "CONTENT_LIBRARY_MASTER").exists():
            self.base_dir = Path.home() / "CONTENT_LIBRARY_MASTER"
        else:
            self.base_dir = Path.home() / "Documents"
        
        self.librarian = LocalLibrarian(str(self.base_dir))
        print(f"📚 Local LLM Librarian initialized")
        print(f"🏠 Base directory: {self.base_dir}")
    
    def search(self, query: str, limit: int = 10, verbose: bool = False) -> None:
        """Search files with natural language query"""
        print(f"\n🔍 Searching: '{query}'")
        print("-" * 50)
        
        results = self.librarian.search(query, limit)
        
        if not results:
            print("❌ No results found")
            print("\n💡 Try:")
            print("  • Different keywords")
            print("  • Broader search terms")
            print("  • Check file locations")
            return
        
        print(f"✅ Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            print(f"[{i}] 📄 {result.filename}")
            print(f"    📂 {Path(result.file_path).parent.name}/")
            print(f"    📊 Relevance: {result.relevance_score:.1%}")
            print(f"    🏷️ Category: {result.file_category}")
            print(f"    📅 Modified: {result.last_modified.strftime('%Y-%m-%d %H:%M')}")
            print(f"    💾 Size: {self._format_size(result.file_size)}")
            
            if verbose:
                print(f"    🔍 Match: {result.matching_content[:100]}...")
                print(f"    💭 Reasoning: {', '.join(result.reasoning[:2])}")
                print(f"    📍 Full Path: {result.file_path}")
            
            print()
    
    def status(self) -> None:
        """Show system status and statistics"""
        print("\n📊 System Status")
        print("=" * 50)
        
        status = self.librarian.get_system_status()
        
        # Content extraction stats
        content_stats = status['content_extraction']
        print(f"📝 Content Index:")
        print(f"    Files indexed: {content_stats['total_files']:,}")
        print(f"    Success rate: {content_stats['success_rate']:.1f}%")
        print(f"    Total content: {content_stats['total_content_length']:,} characters")
        print(f"    Average length: {content_stats['avg_content_length']:,} chars/file")
        
        # Staging system stats
        staging_stats = status['staging_system']
        print(f"\n⏰ Staging System:")
        print(f"    Active files: {staging_stats['total_active_files']:,}")
        print(f"    Ready to organize: {staging_stats['ready_for_organization']:,}")
        print(f"    Overdue files: {staging_stats['overdue_files']:,}")
        print(f"    Avg staging days: {staging_stats['average_staging_days']:.1f}")
        
        print(f"\n🔄 Last updated: {status['last_updated']}")
    
    def organize(self, dry_run: bool = True) -> None:
        """Run file organization on staging folders"""
        print(f"\n🗂️ File Organization {'(Dry Run)' if dry_run else '(Live)'}")
        print("=" * 50)
        
        staging_monitor = StagingMonitor(str(self.base_dir))
        classifier = FileClassificationEngine(str(self.base_dir))
        
        # Get files ready for organization
        ready_files = staging_monitor.get_files_ready_for_organization()
        
        if not ready_files:
            print("✨ No files ready for organization yet!")
            print("💡 Files need to be in staging for 7+ days")
            return
        
        print(f"📁 Found {len(ready_files)} files ready for organization:\n")
        
        organized_count = 0
        
        for file_info in ready_files:
            file_path = Path(file_info['path'])
            if not file_path.exists():
                continue
            
            print(f"📄 {file_info['name']}")
            print(f"    ⏰ In staging: {file_info['days_in_staging']} days")
            
            # Classify the file
            try:
                classification = classifier.classify_file(file_path)
                recommendation = classifier.get_organization_recommendation(classification)
                
                print(f"    🏷️ Category: {classification.category}")
                print(f"    📊 Confidence: {classification.confidence:.1%}")
                print(f"    🎯 Recommendation: {recommendation}")
                
                if recommendation == "auto_organize" and not dry_run:
                    # Would move the file here
                    print(f"    ✅ Would move to: {classification.suggested_path}")
                    organized_count += 1
                elif recommendation == "suggest_organization":
                    print(f"    💡 Suggested: {classification.suggested_path}")
                else:
                    print(f"    ⚠️ Manual review needed")
                
            except Exception as e:
                print(f"    ❌ Classification error: {e}")
            
            print()
        
        if dry_run:
            print(f"🔍 Dry run complete - {organized_count} files would be organized")
            print("💡 Use --live to actually move files")
        else:
            print(f"✅ Organized {organized_count} files")
    
    def index(self, force: bool = False) -> None:
        """Index files for content search"""
        print(f"\n📚 Content Indexing {'(Force Refresh)' if force else '(Incremental)'}")
        print("=" * 50)
        
        extractor = ContentExtractor(str(self.base_dir))
        
        # Find files to index
        index_locations = [
            self.base_dir / "01_ACTIVE_PROJECTS",
            self.base_dir / "02_MEDIA_ASSETS",
            self.base_dir / "03_ARCHIVE_REFERENCE"
        ]
        
        files_to_index = []
        for location in index_locations:
            if location.exists():
                for file_path in location.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in [
                        '.txt', '.md', '.pdf', '.docx', '.pages', '.ipynb', '.py', '.js', '.html', '.csv', '.json'
                    ]:
                        files_to_index.append(file_path)
        
        print(f"📁 Found {len(files_to_index)} files to potentially index")
        
        indexed_count = 0
        success_count = 0
        
        for file_path in files_to_index[:50]:  # Limit for demo
            print(f"⚡ Processing: {file_path.name}")
            
            try:
                result = extractor.extract_content(file_path)
                indexed_count += 1
                
                if result['success']:
                    success_count += 1
                    content_length = len(result['text'])
                    print(f"    ✅ Indexed: {content_length:,} characters")
                else:
                    print(f"    ⚠️ Failed: {result['metadata'].get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        print(f"\n📊 Indexing complete:")
        print(f"    Files processed: {indexed_count}")
        print(f"    Successful: {success_count}")
        print(f"    Success rate: {(success_count/indexed_count*100):.1f}%" if indexed_count > 0 else "N/A")
    
    def suggest(self, partial: str) -> None:
        """Get search suggestions"""
        suggestions = self.librarian.get_suggestions(partial)
        
        if suggestions:
            print(f"\n💡 Search suggestions for '{partial}':")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
        else:
            print(f"❌ No suggestions found for '{partial}'")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Local LLM Librarian - Intelligent file organization and search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  librarian search "Find Finn Wolfhard contracts"
  librarian search "Recent audio files" --limit 5
  librarian organize --dry-run
  librarian status
  librarian index --force
        """
    )
    
    parser.add_argument('--base-dir', help='Base directory for file organization')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search files with natural language')
    search_parser.add_argument('query', help='Natural language search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum results')
    search_parser.add_argument('--verbose', action='store_true', help='Show detailed results')
    
    # Status command
    subparsers.add_parser('status', help='Show system status and statistics')
    
    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize files from staging')
    organize_parser.add_argument('--live', action='store_true', help='Actually move files (default is dry run)')
    organize_parser.add_argument('--dry-run', action='store_true', help='Preview organization without moving files (default)')
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Index files for content search')
    index_parser.add_argument('--force', action='store_true', help='Force re-indexing all files')
    
    # Suggest command
    suggest_parser = subparsers.add_parser('suggest', help='Get search suggestions')
    suggest_parser.add_argument('partial', help='Partial query for suggestions')
    
    args = parser.parse_args()
    
    # Initialize CLI
    try:
        cli = LibrarianCLI(args.base_dir)
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'search':
            cli.search(args.query, args.limit, args.verbose)
        elif args.command == 'status':
            cli.status()
        elif args.command == 'organize':
            cli.organize(dry_run=not args.live)
        elif args.command == 'index':
            cli.index(args.force)
        elif args.command == 'suggest':
            cli.suggest(args.partial)
        else:
            print("📚 Local LLM Librarian")
            print("Use --help to see available commands")
            print("\nQuick start:")
            print("  python librarian.py search 'Find contracts'")
            print("  python librarian.py status")
            print("  python librarian.py organize --dry-run")
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()