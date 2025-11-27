#!/usr/bin/env python3
"""
Enhanced Librarian CLI - Hybrid Search Interface
Integrates with your existing librarian.py to add semantic search capabilities
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from hybrid_librarian import HybridLibrarian
from librarian import LibrarianCLI
from gdrive_integration import get_ai_organizer_root

class EnhancedLibrarianCLI(LibrarianCLI):
    """
    Enhanced version of your librarian CLI with semantic search
    """
    
    def __init__(self, base_dir: str = None):
        # Use Google Drive integration as primary storage if no base_dir specified
        if base_dir is None:
            base_dir = str(get_ai_organizer_root())
        super().__init__(base_dir)
        self.hybrid_librarian = HybridLibrarian(str(self.base_dir))
        print(f"🧠 Enhanced Librarian initialized with semantic search")
    
    def search(self, query: str, limit: int = 10, verbose: bool = False, mode: str = "auto") -> None:
        """Enhanced search with semantic capabilities"""
        print(f"\n🔍 Enhanced Search: '{query}'")
        print(f"🎯 Search Mode: {mode}")
        print("-" * 50)
        
        results = self.hybrid_librarian.search(query, search_mode=mode, limit=limit)
        
        if not results:
            print("❌ No results found")
            print("\n💡 Try:")
            print("  • Different keywords")
            print("  • Semantic mode: --mode semantic")
            print("  • Index more content: enhanced_librarian index")
            return
        
        print(f"✅ Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            print(f"[{i}] 📄 {result.filename}")
            print(f"    📂 {Path(result.file_path).parent.name}/")
            print(f"    📊 Relevance: {result.relevance_score:.1f}%")
            if result.semantic_score > 0:
                print(f"    🧠 Semantic: {result.semantic_score:.1%}")
            print(f"    🏷️ Category: {result.file_category}")
            if result.tags:
                print(f"    🏷️ Tags: {', '.join(result.tags[:5])}")
            print(f"    📅 Modified: {result.last_modified.strftime('%Y-%m-%d %H:%M')}")
            print(f"    💾 Size: {self._format_size(result.file_size)}")
            
            if verbose:
                if result.content_summary:
                    print(f"    📝 Summary: {result.content_summary[:100]}...")
                if result.key_concepts:
                    print(f"    🧩 Concepts: {', '.join(result.key_concepts[:3])}")
                print(f"    🔍 Match: {result.matching_content[:100]}...")
                print(f"    💭 Reasoning: {', '.join(result.reasoning[:2])}")
                print(f"    📍 Full Path: {result.file_path}")
            
            print()
    
    def index_semantic(self, force: bool = False, target_folder: str = None) -> None:
        """Index files for semantic search"""
        print(f"\n🧠 Semantic Indexing {'(Force Refresh)' if force else '(New Files Only)'}")
        print("=" * 50)
        
        # Determine what to index
        if target_folder:
            index_locations = [Path(target_folder)]
        else:
            # Index key locations - local only
            from gdrive_integration import get_metadata_root
            index_locations = [
                self.base_dir / "00_ACTIVE_PROJECTS",
                self.base_dir / "01_UNIVERSAL_ASSETS",
                self.base_dir / "02_TEMPLATES_PRESETS",
                self.base_dir / "03_INSPIRATION_RESEARCH",
                get_metadata_root()  # Local metadata system only
            ]
        
        files_to_index = []
        for location in index_locations:
            if location.exists():
                print(f"📂 Scanning: {location}")
                for file_path in location.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in [
                        '.txt', '.md', '.pdf', '.docx', '.pages', '.ipynb', '.py', '.js', 
                        '.html', '.csv', '.json', '.gdoc'
                    ]:
                        files_to_index.append(file_path)
        
        print(f"📁 Found {len(files_to_index)} files to potentially index")
        
        indexed_count = 0
        success_count = 0
        skipped_count = 0
        
        for file_path in files_to_index[:50]:  # Limit for initial run
            print(f"⚡ Processing: {file_path.name}")
            
            try:
                # Check if already indexed (unless force)
                if not force:
                    # You could add logic here to check if file was already indexed
                    pass
                
                success = self.hybrid_librarian.index_file_for_semantic_search(file_path)
                indexed_count += 1
                
                if success:
                    success_count += 1
                    print(f"    ✅ Indexed for semantic search")
                else:
                    skipped_count += 1
                    print(f"    ⚠️ Skipped (too short or failed)")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        print(f"\n📊 Semantic Indexing Complete:")
        print(f"    Files processed: {indexed_count}")
        print(f"    Successfully indexed: {success_count}")
        print(f"    Skipped: {skipped_count}")
        print(f"    Success rate: {(success_count/indexed_count*100):.1f}%" if indexed_count > 0 else "N/A")
    
    def status(self) -> None:
        """Enhanced status with semantic search info"""
        super().status()  # Call original status
        
        # Add semantic search stats
        semantic_stats = self.hybrid_librarian.get_system_stats()
        
        print(f"\n🧠 Semantic Search Status:")
        print(f"    Available: {'✅' if semantic_stats['semantic_search_available'] else '❌'}")
        print(f"    Files indexed: {semantic_stats['files_indexed_semantically']:,}")
        if semantic_stats['embedding_model']:
            print(f"    Model: {semantic_stats['embedding_model']}")
    
    def smart_suggestions(self, partial: str) -> None:
        """Get enhanced search suggestions"""
        suggestions = self.hybrid_librarian.get_search_suggestions(partial)
        
        if suggestions:
            print(f"\n💡 Enhanced search suggestions for '{partial}':")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
        else:
            print(f"❌ No suggestions found for '{partial}'")

def main():
    """Enhanced CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Enhanced Local LLM Librarian with Semantic Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  enhanced_librarian search "Find files about consciousness" --mode semantic
  enhanced_librarian search "Client Name contracts" --mode fast
  enhanced_librarian search "AI research papers" --mode hybrid
  enhanced_librarian index --semantic
  enhanced_librarian status
        """
    )
    
    parser.add_argument('--base-dir', help='Base directory for file organization')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Enhanced search command
    search_parser = subparsers.add_parser('search', help='Enhanced search with semantic capabilities')
    search_parser.add_argument('query', help='Natural language search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum results')
    search_parser.add_argument('--verbose', action='store_true', help='Show detailed results')
    search_parser.add_argument('--mode', choices=['auto', 'fast', 'semantic', 'hybrid'], 
                              default='auto', help='Search mode')
    
    # Enhanced status command
    subparsers.add_parser('status', help='Show enhanced system status')
    
    # Semantic indexing command
    index_parser = subparsers.add_parser('index', help='Index files for semantic search')
    index_parser.add_argument('--force', action='store_true', help='Re-index all files')
    index_parser.add_argument('--folder', help='Specific folder to index')
    
    # Enhanced organize command (use original)
    organize_parser = subparsers.add_parser('organize', help='Organize files from staging')
    organize_parser.add_argument('--live', action='store_true', help='Actually move files')
    organize_parser.add_argument('--dry-run', action='store_true', help='Preview organization')
    
    # Enhanced suggest command
    suggest_parser = subparsers.add_parser('suggest', help='Get enhanced search suggestions')
    suggest_parser.add_argument('partial', help='Partial query for suggestions')
    
    args = parser.parse_args()
    
    # Initialize enhanced CLI
    try:
        cli = EnhancedLibrarianCLI(args.base_dir)
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'search':
            cli.search(args.query, args.limit, args.verbose, args.mode)
        elif args.command == 'status':
            cli.status()
        elif args.command == 'index':
            cli.index_semantic(args.force, args.folder)
        elif args.command == 'organize':
            cli.organize(dry_run=not args.live)
        elif args.command == 'suggest':
            cli.smart_suggestions(args.partial)
        else:
            print("🧠 Enhanced Local LLM Librarian")
            print("Use --help to see available commands")
            print("\nNew semantic search capabilities:")
            print("  python enhanced_librarian.py search 'AI consciousness' --mode semantic")
            print("  python enhanced_librarian.py index")
            print("  python enhanced_librarian.py status")
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()