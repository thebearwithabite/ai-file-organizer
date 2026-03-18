#!/usr/bin/env python3
"""
ARCHITECTURAL LAW:
- base_dir = monitored filesystem location (may be remote)
- metadata_root = internal state (MUST be local)
- metadata_root MUST come from get_metadata_root()
- NEVER derive metadata paths from base_dir

Local LLM Librarian - Main CLI Interface
Complete file organization and search system with natural language queries
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from query_interface import LocalLibrarian
from staging_monitor import StagingMonitor
from content_extractor import ContentExtractor
from classification_engine import FileClassificationEngine
from gdrive_integration import get_ai_organizer_root

class LibrarianCLI:
    """
    Command-line interface for the Local LLM Librarian system
    Provides easy access to all system features
    """
    
    def __init__(self, base_dir: Optional[str] = None, mode: str = "mutating"):
        # Default to CONTENT_LIBRARY_MASTER if it exists, otherwise use Google Drive integration
        if base_dir:
            self.base_dir = Path(base_dir)
        elif (Path.home() / "CONTENT_LIBRARY_MASTER").exists():
            self.base_dir = Path.home() / "CONTENT_LIBRARY_MASTER"
        else:
            self.base_dir = get_ai_organizer_root()
        
        self.librarian = LocalLibrarian(str(self.base_dir))
        self.mode = mode # "mutating" or "read_only"
        print(f"📚 Local LLM Librarian initialized")
        print(f"🏠 Base directory: {self.base_dir}")
        print(f"⚙️ Operating mode: {self.mode}")
    
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
        """Run file organization on staging folders with deduplication"""
        print(f"\n🗂️ File Organization {'(Dry Run)' if dry_run else '(Live)'}")
        print("=" * 50)
        
        import shutil
        from automated_deduplication_service import AutomatedDeduplicationService
        from easy_rollback_system import EasyRollbackSystem

        staging_monitor = StagingMonitor(str(self.base_dir))
        classifier = FileClassificationEngine(str(self.base_dir))
        dedup_service = AutomatedDeduplicationService(str(self.base_dir))
        rollback = EasyRollbackSystem()
        
        # Get files ready for organization
        ready_files = staging_monitor.get_files_ready_for_organization()
        
        if not ready_files:
            print("✨ No files ready for organization yet!")
            print("💡 Files need to be in staging for 7+ days")
            return
        
        print(f"📁 Found {len(ready_files)} files ready for organization:\n")
        
        organized_count = 0
        skipped_count = 0
        duplicate_count = 0

        # Start rollback operation
        op_id = None
        if not dry_run:
            op_id = rollback.start_operation(
                "batch_organization",
                f"Organizing {len(ready_files)} files from staging",
                confidence=1.0
            )
        
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
                
                if recommendation == "auto_organize":
                    target_path = Path(classification.suggested_path)
                    target_dir = target_path.parent

                    # 1. Check for duplicates before moving
                    print(f"    🔍 Checking for duplicates...")
                    dup_check = dedup_service.check_for_duplicates_before_move(str(file_path), str(target_dir))

                    if dup_check["status"] == "duplicates_found":
                        print(f"    ⚠️  Duplicate found! ({len(dup_check['duplicate_paths'])} copies exist)")
                        duplicate_count += 1

                        if not dry_run:
                            # If it's a high-confidence duplicate, we can just remove the staging copy
                            if classification.confidence > 0.9:
                                print(f"    🗑️  High confidence duplicate - removing staging copy")
                                file_path.unlink()
                                staging_monitor.mark_file_organized(str(file_path), "DELETED_DUPLICATE")
                                continue
                            else:
                                print(f"    ⏭️  Skipping for manual review (duplicate exists)")
                                skipped_count += 1
                                continue

                    # 2. Perform the move
                    if not dry_run:
                        print(f"    ➡️  Moving to: {classification.suggested_path}")

                        # Ensure target directory exists
                        target_dir.mkdir(parents=True, exist_ok=True)

                        # Handle collision if destination filename already exists but isn't identical content
                        final_target = target_path
                        if final_target.exists():
                            suffix = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            final_target = target_dir / f"{target_path.stem}{suffix}{target_path.suffix}"
                            print(f"    ⚠️  Target exists, renaming to: {final_target.name}")

                        # Record for rollback
                        rollback.record_file_operation(op_id, str(file_path), str(final_target))

                        # Move file
                        shutil.move(str(file_path), str(final_target))

                        # Mark as organized in staging DB
                        staging_monitor.mark_file_organized(str(file_path), str(final_target))

                        organized_count += 1
                    else:
                        print(f"    👀 Would move to: {classification.suggested_path}")
                        organized_count += 1

                elif recommendation == "suggest_organization":
                    print(f"    💡 Suggested: {classification.suggested_path}")
                    skipped_count += 1
                else:
                    print(f"    ⚠️  Manual review needed")
                    skipped_count += 1
                
            except Exception as e:
                print(f"    ❌ Organization error: {e}")
            
            print()
        
        if not dry_run and op_id:
            rollback.complete_operation(op_id, success=True)

        if dry_run:
            print(f"🔍 Dry run complete:")
            print(f"    • {organized_count} files would be organized")
            print(f"    • {duplicate_count} duplicates identified")
            print(f"    • {skipped_count} files require review")
            print("\n💡 Use --live to actually move files")
        else:
            print(f"✅ Organization complete:")
            print(f"    • {organized_count} files moved")
            print(f"    • {duplicate_count} duplicates handled")
            print(f"    • {skipped_count} files skipped")
    
    def index(self, force: bool = False) -> None:
        """Index files for content search"""
        print(f"\n📚 Content Indexing {'(Force Refresh)' if force else '(Incremental)'}")
        print("=" * 50)
        
        extractor = ContentExtractor(str(self.base_dir))
        
        # Find files to index
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
  librarian search "Find Client Name contracts"
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