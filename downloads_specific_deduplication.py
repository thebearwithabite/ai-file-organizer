#!/usr/bin/env python3
"""
Downloads-Specific Safe Deduplication
Tailored for the common duplicate patterns found in Downloads folders
More permissive safety settings for obvious duplicates
"""

import sys
from pathlib import Path
from datetime import datetime
import re

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from safe_deduplication import SafeDeduplicator, DuplicateGroup
from deduplication_system import BulletproofDeduplicator

class DownloadsDeduplicator(SafeDeduplicator):
    """
    Downloads-specific deduplication with adjusted safety settings
    More aggressive on obvious duplicates like numbered copies
    """
    
    def __init__(self, base_dir: str = None):
        super().__init__(base_dir)
        
        # More permissive settings for Downloads
        self.require_confirmation_over_mb = 50  # 50MB instead of 10MB
        
        # Downloads-specific patterns that are very safe to deduplicate
        self.safe_duplicate_patterns = [
            r'.*\s\(\d+\)\..*',          # "filename (1).ext", "filename (2).ext"  
            r'.*\s\(\d+\)\s\(\d+\)\..*', # "filename (1) (2).ext"
            r'.*_\d+\..*',               # "filename_1.ext", "filename_2.ext"
            r'.*\scopy\..*',             # "filename copy.ext"
            r'.*\scopy\s\(\d+\)\..*',    # "filename copy (1).ext"
            r'.*-\d+\..*',               # "filename-1.ext", "filename-2.ext"
            r'Generated Image.*\.jpeg',   # ChatGPT generated images
            r'ChatGPT Image.*\.png',     # ChatGPT images
            r'Flux_Dev.*\.jpg',          # AI generated images
            r'Default_.*\.jpg',          # More AI images
            r'ElevenLabs_.*\.mp3',       # AI generated audio
            r'.*_202\d{6}_.*',           # Files with timestamps
        ]
    
    def calculate_safety_score(self, duplicate_group):
        """Override safety calculation for Downloads-specific patterns"""
        
        base_safety = super().calculate_safety_score(duplicate_group)
        
        # Boost safety score for obvious duplicate patterns
        downloads_dir = Path.home() / "Downloads"
        
        for file_path in duplicate_group:
            if not file_path.exists():
                continue
                
            # Check if file is in Downloads
            if downloads_dir not in file_path.parents:
                continue
            
            filename = file_path.name
            
            # Very safe patterns get boosted safety
            for pattern in self.safe_duplicate_patterns:
                if re.match(pattern, filename, re.IGNORECASE):
                    base_safety = min(base_safety + 0.3, 1.0)  # Boost by 30%
                    break
            
            # Files in Downloads for more than 7 days are safer
            try:
                age_days = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
                if age_days > 7:
                    base_safety = min(base_safety + 0.2, 1.0)  # Boost by 20%
            except:
                pass
        
        return base_safety
    
    def analyze_downloads_duplicates(self):
        """Analyze specifically Downloads duplicates with detailed categorization"""
        
        print("🔍 Analyzing Downloads-specific duplicate patterns...")
        
        downloads_dir = Path.home() / "Downloads"
        all_duplicates = self.deduper.find_all_duplicates()
        
        # Filter to Downloads duplicates and categorize
        categories = {
            'ai_generated': [],      # AI generated content
            'numbered_copies': [],   # filename (1), filename (2) etc  
            'timestamps': [],        # Files with timestamps in name
            'exact_duplicates': [],  # Identical files with different names
            'other': []             # Other duplicates
        }
        
        downloads_groups = []
        
        for secure_hash, files in all_duplicates.items():
            # Only include groups where at least 2 files are in Downloads
            downloads_files = [f for f in files if f.exists() and downloads_dir in f.parents]
            
            if len(downloads_files) >= 2:
                # Categorize the duplicate group
                category = self._categorize_duplicate_group(downloads_files)
                
                safety_score = self.calculate_safety_score(downloads_files)
                original_file = self._choose_original_file(downloads_files)
                candidates = [f for f in downloads_files if f != original_file]
                
                total_size = sum(f.stat().st_size for f in downloads_files)
                
                group = DuplicateGroup(
                    secure_hash=secure_hash,
                    files=downloads_files,
                    total_size=total_size,
                    original_file=original_file,
                    candidates_for_deletion=candidates,
                    safety_score=safety_score,
                    requires_manual_review=safety_score < 0.6  # More permissive
                )
                
                categories[category].append(group)
                downloads_groups.append(group)
        
        return categories, downloads_groups
    
    def _categorize_duplicate_group(self, files):
        """Categorize a duplicate group by pattern"""
        
        filenames = [f.name for f in files]
        
        # Check for AI generated patterns
        ai_patterns = ['ChatGPT Image', 'Flux_Dev', 'Default_', 'ElevenLabs_', 'Generated Image']
        if any(any(pattern in name for pattern in ai_patterns) for name in filenames):
            return 'ai_generated'
        
        # Check for numbered copies
        numbered_patterns = [r'.*\s\(\d+\)\..*', r'.*\scopy.*', r'.*_\d+\..*']
        if any(any(re.match(pattern, name, re.IGNORECASE) for pattern in numbered_patterns) for name in filenames):
            return 'numbered_copies'
        
        # Check for timestamps
        if any('_202' in name or '202' in name for name in filenames):
            return 'timestamps'
        
        # Check if they have very similar names (likely exact duplicates with minor name differences)
        base_names = []
        for name in filenames:
            # Remove common suffixes like (1), _1, copy etc
            clean_name = re.sub(r'\s*\(\d+\)\s*', '', name)
            clean_name = re.sub(r'\s*copy\s*', '', clean_name, flags=re.IGNORECASE)
            clean_name = re.sub(r'_\d+', '', clean_name)
            base_names.append(clean_name)
        
        if len(set(base_names)) == 1:
            return 'exact_duplicates'
        
        return 'other'
    
    def show_downloads_analysis(self):
        """Show detailed analysis of Downloads duplicates"""
        
        categories, downloads_groups = self.analyze_downloads_duplicates()
        
        print(f"\n📊 DOWNLOADS DUPLICATE ANALYSIS")
        print(f"=" * 60)
        
        total_groups = sum(len(groups) for groups in categories.values())
        total_files = sum(sum(len(g.candidates_for_deletion) for g in groups) for groups in categories.values())
        total_space = sum(sum(g.total_size - g.original_file.stat().st_size for g in groups if g.original_file.exists()) for groups in categories.values())
        
        print(f"📂 Total duplicate groups in Downloads: {total_groups}")
        print(f"📄 Total duplicate files to delete: {total_files}")
        print(f"💾 Total space to free: {total_space / (1024**2):.1f} MB")
        
        for category, groups in categories.items():
            if not groups:
                continue
                
            category_files = sum(len(g.candidates_for_deletion) for g in groups)
            category_space = sum(g.total_size - g.original_file.stat().st_size for g in groups if g.original_file.exists())
            safe_groups = sum(1 for g in groups if not g.requires_manual_review)
            
            print(f"\n📂 {category.upper().replace('_', ' ')}:")
            print(f"   Groups: {len(groups)} | Files: {category_files} | Space: {category_space / (1024**2):.1f} MB")
            print(f"   Safe for auto-deletion: {safe_groups}/{len(groups)} groups")
            
            # Show examples
            for group in sorted(groups, key=lambda g: g.total_size, reverse=True)[:3]:
                print(f"      • Keep: {group.original_file.name}")
                print(f"        Delete: {len(group.candidates_for_deletion)} files")
                print(f"        Safety: {group.safety_score:.1%} | Size: {(group.total_size - group.original_file.stat().st_size) / 1024:.0f} KB")
        
        # Count safe vs review needed
        safe_groups = [g for g in downloads_groups if not g.requires_manual_review]
        review_groups = [g for g in downloads_groups if g.requires_manual_review]
        
        safe_files = sum(len(g.candidates_for_deletion) for g in safe_groups)
        safe_space = sum(g.total_size - g.original_file.stat().st_size for g in safe_groups if g.original_file.exists())
        
        print(f"\n🎯 RECOMMENDED ACTION:")
        print(f"   ✅ Safe to delete now: {safe_files} files ({safe_space / (1024**2):.1f} MB)")
        print(f"   ⚠️  Needs review: {len(review_groups)} groups")
        
        return safe_groups, review_groups

def main():
    """Analyze Downloads duplicates with permissive settings"""
    
    print("📁 Downloads-Specific Duplicate Analysis")
    print("=" * 60)
    
    deduper = DownloadsDeduplicator()
    safe_groups, review_groups = deduper.show_downloads_analysis()
    
    if safe_groups:
        print(f"\n❓ Proceed with safe Downloads cleanup?")
        print(f"   python downloads_specific_deduplication.py --execute")
        print(f"   (Will only delete files with high safety scores)")
    else:
        print(f"\n📝 All duplicates require manual review")
        print(f"   Consider running with --force-safe for more aggressive cleanup")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Execute safe deletions')
    
    if len(sys.argv) == 1:
        main()
    else:
        args = parser.parse_args()
        
        deduper = DownloadsDeduplicator()
        safe_groups, review_groups = deduper.show_downloads_analysis()
        
        if args.execute and safe_groups:
            result = deduper.execute_safe_deletions(safe_groups, dry_run=False)
            print(f"\n🎉 Cleanup complete!")
            print(f"   Files deleted: {result['deleted_count']}")
            print(f"   Space freed: {result['freed_space_mb']:.1f} MB")
        elif args.execute:
            print(f"❌ No safe deletions available")
        else:
            print(f"🧪 Use --execute to perform actual deletions")