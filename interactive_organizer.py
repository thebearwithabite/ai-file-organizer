#!/usr/bin/env python3
"""
ARCHITECTURAL LAW:
- base_dir = monitored filesystem location (may be remote)
- metadata_root = internal state (MUST be local)
- metadata_root MUST come from get_metadata_root()
- NEVER derive metadata paths from base_dir

Interactive File Organizer
Integrates interactive classification with the existing staging system
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from staging_monitor import StagingMonitor
from staging_monitor import StagingMonitor
from unified_classifier import UnifiedClassificationService
from taxonomy_service import TaxonomyService
from gdrive_integration import get_metadata_root
from dataclasses import dataclass, field

from safe_file_recycling import SafeFileRecycling
from gdrive_integration import get_ai_organizer_root
from audio_ai_analyzer import AudioAIAnalyzer

@dataclass
class ClassificationResult:
    """
    Result of file classification compatible with InteractiveOrganizer.
    """
    category: str
    confidence: float
    reasoning: List[str]
    suggested_path: str
    tags: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    subcategory: str = "General"

class InteractiveOrganizer:
    """
    File organizer that asks questions for uncertain classifications
    Integrates with User's existing workflow
    """
    
    def __init__(self, base_dir: str = None):
        # Use Google Drive integration as primary storage root
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        
        # Initialize Core Services
        self.classifier_service = UnifiedClassificationService()
        self.taxonomy_service = TaxonomyService.get_instance(get_metadata_root() / "config")
        
        self.staging_monitor = StagingMonitor(str(self.base_dir))
        self.audio_analyzer = AudioAIAnalyzer(str(self.base_dir))
        self.recycling = SafeFileRecycling(str(self.base_dir))
        
        # ADHD-friendly safety mode (default on)
        self.use_recycling = True
        
        # Track organization session
        self.session_stats = {
            "files_processed": 0,
            "questions_asked": 0,
            "high_confidence": 0,
            "learned_preferences": 0,
            "files_recycled": 0,
            "files_organized": 0
        }
    
    def organize_staging_with_questions(self, dry_run: bool = True) -> Dict[str, int]:
        """
        Organize files from staging with interactive questions
        
        Args:
            dry_run: If True, show what would happen without moving files
            
        Returns:
            Statistics about the organization session
        """
        print("🗂️  Interactive File Organization")
        print("=" * 50)
        
        # Get files from staging areas
        staging_files = self._get_staging_files()
        
        if not staging_files:
            print("✅ No files in staging areas")
            return self.session_stats
        
        print(f"📁 Found {len(staging_files)} files to organize")
        
        for file_path in staging_files:
            self._organize_single_file(file_path, dry_run)
        
        print(f"\n📊 Organization Session Complete:")
        print(f"   Files processed: {self.session_stats['files_processed']}")
        print(f"   Questions asked: {self.session_stats['questions_asked']}")
        print(f"   High confidence: {self.session_stats['high_confidence']}")
        print(f"   Learning events: {self.session_stats['learned_preferences']}")
        
        if self.use_recycling and self.session_stats['files_recycled'] > 0:
            print(f"   ♻️  Files recycled safely: {self.session_stats['files_recycled']}")
            print(f"   💡 Complete organization: python safe_file_recycling.py --list")
        elif not self.use_recycling and self.session_stats['files_organized'] > 0:
            print(f"   ✅ Files moved directly: {self.session_stats['files_organized']}")
        
        return self.session_stats
    
    def organize_specific_file(self, file_path: Path, dry_run: bool = True) -> bool:
        """Organize a specific file with interactive classification"""
        print(f"\n🗂️  Organizing: {file_path.name}")
        return self._organize_single_file(file_path, dry_run)
    
    def _get_staging_files(self) -> List[Path]:
        """Get all files from staging areas"""
        staging_areas = [
            self.base_dir / "99_TEMP_PROCESSING" / "Downloads_Staging",
            self.base_dir / "99_TEMP_PROCESSING" / "Desktop_Staging",
            Path.home() / "Downloads",
            Path.home() / "Desktop"
        ]
        
        staging_files = []
        
        for area in staging_areas:
            if area.exists():
                for file_path in area.iterdir():
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        staging_files.append(file_path)
        
        return staging_files[:20]  # Limit to prevent overwhelming
    
    def _organize_single_file(self, file_path: Path, dry_run: bool) -> bool:
        """Organize a single file with interactive classification"""
        
        try:
            print(f"\n📄 Processing: {file_path.name}")
            
            # Extract content for better classification
            content = ""
            audio_analysis = None
            
            try:
                # Check if it's an audio file first
                audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.aiff'}
                if file_path.suffix.lower() in audio_extensions:
                    print(f"🎵 Detected audio file - running AudioAI analysis...")
                    try:
                        audio_analysis = self.audio_analyzer.analyze_audio_file(file_path)
                        self.audio_analyzer.save_analysis(audio_analysis)
                        
                        # Use audio analysis for classification context
                        content = f"Audio file: {audio_analysis.content_type}, {audio_analysis.duration_seconds:.1f}s"
                        if audio_analysis.transcription:
                            content += f" - {audio_analysis.transcription[:500]}"
                        
                        print(f"   🎯 Audio type: {audio_analysis.content_type}")
                        print(f"   ⏱️  Duration: {audio_analysis.duration_seconds:.1f}s")
                        if audio_analysis.creative_tags:
                            print(f"   🏷️  Tags: {', '.join(audio_analysis.creative_tags[:3])}")
                            
                    except Exception as e:
                        print(f"   ⚠️  Audio analysis failed: {e}")
                        print(f"   📄 Falling back to basic file classification...")
                
                # Text file content extraction
                elif file_path.suffix.lower() == '.txt':
                    content = file_path.read_text(encoding='utf-8', errors='ignore')[:2000]
                elif file_path.suffix.lower() == '.pdf':
                    # Use existing content extractor
                    from content_extractor import ContentExtractor
                    extractor = ContentExtractor(str(self.base_dir))
                    result = extractor.extract_content(file_path)
                    if result['success']:
                        content = result['text'][:2000]
            except:
                pass  # Use filename-based classification
            
            # Classify with Unified Service + Interaction
            print(f"🤔 Analyzing file...")
            classification = self._classify_and_interact(file_path, audio_analysis)
            
            # Enhanced classification for audio files
            if audio_analysis and audio_analysis.confidence_score > 0.7:
                # Use AudioAI analysis to improve classification
                if audio_analysis.content_type == 'interview':
                    classification.category = "Entertainment_Industry/Interviews"
                    classification.confidence = max(classification.confidence, 90)
                elif audio_analysis.content_type == 'voice_sample':
                    classification.category = "Entertainment_Industry/Voice_Samples"
                    classification.confidence = max(classification.confidence, 85)
                elif audio_analysis.content_type == 'scene_audio':
                    classification.category = "Entertainment_Industry/Scene_Work"
                    classification.confidence = max(classification.confidence, 85)
                elif audio_analysis.content_type == 'music':
                    classification.category = "Creative_Projects/Music"
                    classification.confidence = max(classification.confidence, 80)
                
                # Add audio-specific reasoning
                if audio_analysis.creative_tags:
                    classification.reasoning.extend([f"AudioAI: {tag}" for tag in audio_analysis.creative_tags[:2]])
                
                print(f"   🎵 AudioAI enhanced classification: {audio_analysis.content_type}")
            
            # Update session stats
            self.session_stats['files_processed'] += 1
            if classification.confidence >= 85:
                self.session_stats['high_confidence'] += 1
            
            # Generate destination path
            destination = self.base_dir / classification.suggested_path / file_path.name
            
            # Check for duplicates
            if destination.exists():
                print(f"⚠️  File already exists at destination")
                if self._handle_duplicate(file_path, destination, dry_run):
                    return True
                else:
                    return False
            
            # Show organization plan
            print(f"\n📋 Organization Plan:")
            print(f"   From: {file_path}")
            print(f"   To: {destination}")
            print(f"   Category: {classification.category}")
            print(f"   Confidence: {classification.confidence:.1f}%")
            print(f"   Reasoning: {', '.join(classification.reasoning[:2])}")
            
            if dry_run:
                print(f"   🔍 DRY RUN - Would move file")
                return True
            else:
                # Move file safely with recycling option
                if self.use_recycling:
                    # Move to recycling first for safety
                    recycled_path = self.recycling.recycle_file(
                        file_path, 
                        destination, 
                        operation_type="organize",
                        reason=f"Interactive organization: {classification.category} ({classification.confidence:.1f}%)"
                    )
                    
                    if recycled_path:
                        self.session_stats['files_recycled'] += 1
                        print(f"   ♻️  File recycled safely (can undo)")
                        print(f"   💡 Complete organization: python safe_file_recycling.py --complete {recycled_path.name}")
                        print(f"   ↩️  Or restore: python safe_file_recycling.py --restore {recycled_path.name}")
                    else:
                        print(f"   ❌ Failed to recycle file safely")
                        return False
                else:
                    # Direct move (old behavior)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    file_path.rename(destination)
                    print(f"   ✅ File moved directly")
                    self.session_stats['files_organized'] += 1
                
                # Index in semantic search system
                try:
                    from vector_librarian import VectorLibrarian
                    librarian = VectorLibrarian(str(self.base_dir))
                    if librarian.collection:
                        librarian.index_file_with_chunks(destination)
                        print(f"   🧠 Added to semantic search")
                except:
                    pass  # Non-critical
                
                return True
        
        except Exception as e:
            print(f"   ❌ Error organizing file: {e}")
            return False

    def _classify_and_interact(self, file_path: Path, audio_analysis=None) -> ClassificationResult:
        """
        Classify file, apply audio enhancements, and ask questions if confidence is low.
        """
        # 1. Get initial classification from Unified Service
        result_dict = self.classifier_service.classify_file(file_path)
        
        # Parse the result
        final = result_dict.get('final', {})
        category = final.get('category', 'unknown')
        confidence = final.get('confidence', 0.0) * 100 # Convert 0-1.0 to 0-100 scale
        
        trace = final.get('decision_trace', '')
        reasoning = [trace] if trace else []
        candidates = final.get('candidates', [])
        
        # Add candidate info to reasoning
        for cand in candidates:
            reasoning.append(f"Candidate ({cand.get('source')}): {cand.get('category')} ({cand.get('confidence', 0):.2f})")

        # Initial Result Construction
        result = ClassificationResult(
            category=category,
            confidence=confidence,
            reasoning=reasoning,
            suggested_path=str(self.taxonomy_service.resolve_path(category)),
            tags=[category]
        )

        # 2. Apply Audio Enhancements (Strategy: Boost Confidence BEFORE asking user)
        if audio_analysis and audio_analysis.confidence_score > 0.7:
             # Use AudioAI analysis to improve classification
            if audio_analysis.content_type == 'interview':
                result.category = "Entertainment_Industry/Interviews" # TODO: Update this to match new Taxonomy IDs if needed
                result.confidence = max(result.confidence, 90)
            elif audio_analysis.content_type == 'voice_sample':
                result.category = "audio_vox" # V3 Taxonomy ID
                result.confidence = max(result.confidence, 85)
            elif audio_analysis.content_type == 'scene_audio':
                result.category = "Entertainment_Industry/Scene_Work"
                result.confidence = max(result.confidence, 85)
            elif audio_analysis.content_type == 'music':
                result.category = "audio_music" # V3 Taxonomy ID
                result.confidence = max(result.confidence, 80)
            
            # Add audio-specific reasoning
            if audio_analysis.creative_tags:
                result.reasoning.extend([f"AudioAI: {tag}" for tag in audio_analysis.creative_tags[:2]])
            
            print(f"   🎵 AudioAI enhanced classification: {audio_analysis.content_type}")
            
            # Update path based on new category
            result.suggested_path = str(self.taxonomy_service.resolve_path(result.category))

        # 3. Interactive Questioning (Threshold: 65%)
        if result.confidence < 65:
            self._ask_user_questions(file_path, result, candidates)
            # Update path again in case user changed category
            result.suggested_path = str(self.taxonomy_service.resolve_path(result.category))
            
        return result

    def _ask_user_questions(self, file_path: Path, result: ClassificationResult, candidates: List[Dict]):
        """
        Ask user questions to resolve uncertainty.
        Modifies result in-place.
        """
        print(f"\n❓ Uncertainty detected for: {file_path.name} (Confidence: {result.confidence:.1f}%)")
        print(f"   Current best guess: {result.category}")
        
        # Identify options
        options = []
        seen_cats = set()
        
        # Add current best guess
        if result.category != "unknown":
            options.append(result.category)
            seen_cats.add(result.category)
        
        # Add other candidates from Unified Service
        for cand in candidates:
            cat = cand.get('category')
            if cat and cat != "unknown" and cat not in seen_cats:
                options.append(cat)
                seen_cats.add(cat)
                
        # Fill with standard categories from Taxonomy
        # We can get these from taxonomy service
        all_cats = list(self.taxonomy_service.get_all_categories().keys())
        # Sort by some logic or just take common ones? 
        # For now, let's use the ones that were hardcoded but as IDs
        standard_cats = ["audio_vox", "audio_sfx", "tech_literature", "biz_financials", "personal_photos"]
        
        for cat in standard_cats:
            if len(options) >= 5:
                break
            if cat not in seen_cats and cat in all_cats:
                options.append(cat)
                seen_cats.add(cat)
        
        print("   What is the primary category for this file?")
        for i, opt in enumerate(options, 1):
            print(f"   {i}. {opt}")
        print(f"   {len(options)+1}. [Custom Category ID]")
        print(f"   {len(options)+2}. [Skip / Keep Unknown]")
        
        try:
            choice = input(f"   Select (1-{len(options)+2}): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                
                # Preset option selected
                if 0 <= idx < len(options):
                    selected_cat = options[idx]
                    result.category = selected_cat
                    result.confidence = 100.0
                    result.reasoning.append(f"User selected: {selected_cat}")
                
                # Custom category
                elif idx == len(options):
                    custom = input("   Enter category ID: ").strip()
                    if custom:
                        # Verify it exists? Or allow creating new?
                        # For now, let's assume valid ID or string
                        result.category = custom
                        result.confidence = 100.0
                        result.reasoning.append(f"User defined: {custom}")
                
                # Skip
                elif idx == len(options) + 1:
                    print("   Skipping manual classification.")
                    
        except (KeyboardInterrupt, EOFError):
            print("\n   Skipping question (interrupted).")
            pass
    
    def _handle_duplicate(self, source: Path, destination: Path, dry_run: bool) -> bool:
        """Handle duplicate file detection"""
        
        # Check if files are actually identical
        try:
            if source.stat().st_size == destination.stat().st_size:
                # Same size - likely duplicate
                print(f"   🔍 Possible duplicate detected")
                
                if dry_run:
                    print(f"   🗑️  DRY RUN - Would delete duplicate")
                else:
                    # Ask user what to do
                    print(f"   Options:")
                    print(f"   1. Delete source (keep existing)")
                    print(f"   2. Keep both (rename source)")
                    print(f"   3. Skip this file")
                    
                    while True:
                        try:
                            choice = input(f"   Choose (1-3): ").strip()
                            if choice == "1":
                                source.unlink()
                                print(f"   🗑️  Duplicate deleted")
                                return True
                            elif choice == "2":
                                # Create unique name
                                counter = 1
                                base_name = destination.stem
                                extension = destination.suffix
                                while destination.exists():
                                    destination = destination.parent / f"{base_name}_{counter}{extension}"
                                    counter += 1
                                source.rename(destination)
                                print(f"   📁 Renamed and moved to {destination.name}")
                                return True
                            elif choice == "3":
                                print(f"   ⏭️  Skipped")
                                return False
                            else:
                                print(f"   Please enter 1, 2, or 3")
                        except (KeyboardInterrupt, EOFError):
                            print(f"   ⏭️  Skipped")
                            return False
            else:
                # Different sizes - rename and keep both
                counter = 1
                base_name = destination.stem
                extension = destination.suffix
                while destination.exists():
                    destination = destination.parent / f"{base_name}_{counter}{extension}"
                    counter += 1
                
                if dry_run:
                    print(f"   📁 DRY RUN - Would rename to {destination.name}")
                else:
                    source.rename(destination)
                    print(f"   📁 Renamed and moved to {destination.name}")
                
                return True
                
        except Exception as e:
            print(f"   ⚠️  Could not compare files: {e}")
            return False
    
    def quick_organize(self, folder_path: str, dry_run: bool = True) -> Dict[str, int]:
        """Quickly organize files in a specific folder"""
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"❌ Folder not found: {folder}")
            return {}
        
        print(f"🗂️  Quick organizing: {folder}")
        
        files = [f for f in folder.iterdir() if f.is_file() and not f.name.startswith('.')]
        
        for file_path in files[:10]:  # Limit for safety
            self._organize_single_file(file_path, dry_run)
        
        return self.session_stats
    
    def enable_direct_moves(self):
        """Disable recycling for direct file moves (less safe)"""
        self.use_recycling = False
        print("⚠️  Direct moves enabled - files will be moved immediately without recycling safety")
    
    def enable_recycling(self):
        """Enable recycling for safe file moves (default)"""
        self.use_recycling = True
        print("✅ Recycling enabled - files will be moved to recycling first for safety")

def main():
    """Command line interface for interactive organization"""
    parser = argparse.ArgumentParser(
        description="Interactive File Organizer with Confidence-Based Questioning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Organize staging areas with questions
  python interactive_organizer.py organize --live
  
  # Quick organize a specific folder
  python interactive_organizer.py quick /Users/user/Downloads --dry-run
  
  # Test with a single file
  python interactive_organizer.py file "/path/to/document.pdf" --live
        """
    )
    
    parser.add_argument('--base-dir', help='Base directory for file organization')
    parser.add_argument('--direct-moves', action='store_true', 
                       help='Move files directly without recycling (less safe)')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Organize staging areas
    organize_parser = subparsers.add_parser('organize', help='Organize files from staging areas')
    organize_parser.add_argument('--live', action='store_true', help='Actually move files (default is dry-run)')
    organize_parser.add_argument('--dry-run', action='store_true', help='Preview organization only')
    
    # Quick organize specific folder
    quick_parser = subparsers.add_parser('quick', help='Quickly organize a specific folder')
    quick_parser.add_argument('folder', help='Folder to organize')
    quick_parser.add_argument('--live', action='store_true', help='Actually move files')
    quick_parser.add_argument('--dry-run', action='store_true', help='Preview organization only')
    
    # Single file
    file_parser = subparsers.add_parser('file', help='Organize a single file')
    file_parser.add_argument('file_path', help='Path to file to organize')
    file_parser.add_argument('--live', action='store_true', help='Actually move file')
    file_parser.add_argument('--dry-run', action='store_true', help='Preview organization only')
    
    args = parser.parse_args()
    
    # Initialize organizer
    organizer = InteractiveOrganizer(args.base_dir)
    
    # Handle recycling mode
    if args.direct_moves:
        organizer.enable_direct_moves()
    
    # Execute command
    try:
        if args.command == 'organize':
            dry_run = not args.live if hasattr(args, 'live') else True
            organizer.organize_staging_with_questions(dry_run=dry_run)
        elif args.command == 'quick':
            dry_run = not args.live if hasattr(args, 'live') else True
            organizer.quick_organize(args.folder, dry_run=dry_run)
        elif args.command == 'file':
            dry_run = not args.live if hasattr(args, 'live') else True
            file_path = Path(args.file_path)
            organizer.organize_specific_file(file_path, dry_run=dry_run)
        else:
            print("🤔 Interactive File Organizer")
            print("Use --help to see available commands")
            print(f"Features:")
            print(f"  • Asks questions until 65% confident")
            print("  • Learns your preferences over time")
            print("  • ADHD-friendly decision making")
            print("  • Integrates with semantic search")
            
    except KeyboardInterrupt:
        print("\n\n👋 Organization stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()