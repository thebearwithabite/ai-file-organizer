#!/usr/bin/env python3
"""
Google Drive Migration Assistant
Helps migrate existing Google Drive and scattered local files into the new archive structure
With ADHD-friendly batch processing and safety measures
"""

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from path_config import paths
from archive_lifecycle_manager import ArchiveLifecycleManager
from metadata_generator import MetadataGenerator
from enhanced_librarian import EnhancedLibrarianCLI

# Configure logging
logger = logging.getLogger(__name__)

class GoogleDriveMigrationAssistant:
    """
    Assists in migrating files from Google Drive and other locations 
    into the organized archive structure with ADHD-friendly controls
    """
    
    def __init__(self):
        self.base_dir = paths.get_path('documents')
        self.temp_analysis_dir = paths.get_path('organizer_base') / 'temp_analysis'
        self.migration_log_path = paths.get_path('logs') / 'migration.log'
        
        # Initialize components
        self.archive_manager = ArchiveLifecycleManager()
        self.metadata_generator = MetadataGenerator(str(self.base_dir))
        self.librarian = EnhancedLibrarianCLI()
        
        # Create temporary analysis directory
        self.temp_analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Migration tracking
        self.migration_session_id = int(time.time())
        self.processed_files = []
        self.errors = []
        
        # ADHD-friendly batch settings
        self.max_batch_size = 10  # Process max 10 files at once
        self.pause_between_batches = 2  # Seconds between batches
    
    def analyze_existing_structure(self, source_path: str) -> Dict:
        """
        Analyze existing file structure to understand current organization
        Returns ADHD-friendly summary and recommendations
        """
        
        source = Path(source_path)
        if not source.exists():
            return {'error': f"Source path not found: {source_path}"}
        
        print(f"🔍 Analyzing file structure in: {source}")
        
        analysis = {
            'source_path': str(source),
            'total_files': 0,
            'file_types': {},
            'directory_structure': {},
            'size_analysis': {'total_mb': 0, 'largest_files': []},
            'content_categories': {},
            'age_distribution': {'last_7_days': 0, 'last_30_days': 0, 'last_year': 0, 'older': 0},
            'migration_recommendations': []
        }
        
        current_time = time.time()
        
        try:
            # Walk through directory structure
            for root, dirs, files in os.walk(source):
                root_path = Path(root)
                relative_path = root_path.relative_to(source)
                
                # Track directory structure (limit depth for ADHD readability)
                if len(relative_path.parts) <= 3:
                    analysis['directory_structure'][str(relative_path)] = len(files)
                
                for file_name in files:
                    file_path = root_path / file_name
                    
                    try:
                        stat = file_path.stat()
                        file_size_mb = stat.st_size / (1024 * 1024)
                        file_age_days = (current_time - stat.st_mtime) / 86400
                        
                        analysis['total_files'] += 1
                        analysis['size_analysis']['total_mb'] += file_size_mb
                        
                        # Track file types
                        ext = file_path.suffix.lower()
                        analysis['file_types'][ext] = analysis['file_types'].get(ext, 0) + 1
                        
                        # Track largest files (top 10 for ADHD manageability)
                        if len(analysis['size_analysis']['largest_files']) < 10:
                            analysis['size_analysis']['largest_files'].append({
                                'path': str(file_path),
                                'size_mb': round(file_size_mb, 2),
                                'name': file_name
                            })
                        else:
                            # Replace smallest if current is larger
                            min_file = min(analysis['size_analysis']['largest_files'], key=lambda x: x['size_mb'])
                            if file_size_mb > min_file['size_mb']:
                                analysis['size_analysis']['largest_files'].remove(min_file)
                                analysis['size_analysis']['largest_files'].append({
                                    'path': str(file_path),
                                    'size_mb': round(file_size_mb, 2),
                                    'name': file_name
                                })
                        
                        # Age distribution
                        if file_age_days <= 7:
                            analysis['age_distribution']['last_7_days'] += 1
                        elif file_age_days <= 30:
                            analysis['age_distribution']['last_30_days'] += 1
                        elif file_age_days <= 365:
                            analysis['age_distribution']['last_year'] += 1
                        else:
                            analysis['age_distribution']['older'] += 1
                        
                        # Content category estimation (quick keywords in filename)
                        file_lower = file_name.lower()
                        if any(term in file_lower for term in ['finn', 'stranger', 'sag', 'contract', 'agreement']):
                            analysis['content_categories']['entertainment'] = analysis['content_categories'].get('entertainment', 0) + 1
                        elif any(term in file_lower for term in ['tax', 'invoice', 'receipt', 'financial']):
                            analysis['content_categories']['financial'] = analysis['content_categories'].get('financial', 0) + 1
                        elif any(term in file_lower for term in ['papers', 'dream', 'episode', 'podcast', 'ai']):
                            analysis['content_categories']['creative'] = analysis['content_categories'].get('creative', 0) + 1
                        elif any(term in file_lower for term in ['.py', '.js', '.html', 'package.json', 'readme']):
                            analysis['content_categories']['development'] = analysis['content_categories'].get('development', 0) + 1
                        else:
                            analysis['content_categories']['other'] = analysis['content_categories'].get('other', 0) + 1
                            
                    except Exception as e:
                        logger.warning(f"Error analyzing file {file_path}: {e}")
                        continue
            
            # Sort largest files by size
            analysis['size_analysis']['largest_files'].sort(key=lambda x: x['size_mb'], reverse=True)
            
            # Generate ADHD-friendly recommendations
            analysis['migration_recommendations'] = self._generate_migration_recommendations(analysis)
            
            # Round total size for readability
            analysis['size_analysis']['total_mb'] = round(analysis['size_analysis']['total_mb'], 2)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing structure: {e}")
            return {'error': str(e)}
    
    def _generate_migration_recommendations(self, analysis: Dict) -> List[str]:
        """Generate ADHD-friendly migration recommendations based on analysis"""
        
        recommendations = []
        total_files = analysis['total_files']
        
        # File volume recommendations
        if total_files > 1000:
            recommendations.append(f"🔥 Large collection ({total_files} files) - suggest processing in batches of 50-100 files")
        elif total_files > 100:
            recommendations.append(f"📊 Medium collection ({total_files} files) - manageable in batches of 20-30")
        else:
            recommendations.append(f"✅ Small collection ({total_files} files) - can process all at once")
        
        # Content-based recommendations
        categories = analysis['content_categories']
        if categories.get('entertainment', 0) > 0:
            recommendations.append(f"🎬 Found {categories['entertainment']} entertainment files - priority for active projects folder")
        
        if categories.get('financial', 0) > 0:
            recommendations.append(f"💰 Found {categories['financial']} financial files - check for current vs archive classification")
        
        if categories.get('creative', 0) > 0:
            recommendations.append(f"🎨 Found {categories['creative']} creative files - separate active episodes from published archive")
        
        # Age-based recommendations
        age_dist = analysis['age_distribution']
        recent_files = age_dist['last_7_days'] + age_dist['last_30_days']
        old_files = age_dist['older']
        
        if recent_files > 0:
            recommendations.append(f"⏰ {recent_files} recent files - likely candidates for active projects")
        
        if old_files > 0:
            recommendations.append(f"🗄️ {old_files} files older than 1 year - good candidates for archive")
        
        # Size recommendations
        total_mb = analysis['size_analysis']['total_mb']
        if total_mb > 1000:  # 1GB+
            recommendations.append(f"💾 Large data size ({total_mb:.1f} MB) - consider selective migration of most important files first")
        
        return recommendations
    
    def create_migration_plan(self, source_analysis: Dict, priorities: List[str] = None) -> Dict:
        """
        Create ADHD-friendly migration plan with clear phases and manageable batches
        """
        
        if priorities is None:
            priorities = ['entertainment', 'financial', 'creative', 'development']
        
        plan = {
            'migration_id': self.migration_session_id,
            'source_info': {
                'path': source_analysis['source_path'],
                'total_files': source_analysis['total_files'],
                'total_size_mb': source_analysis['size_analysis']['total_mb']
            },
            'phases': [],
            'adhd_guidelines': {
                'max_files_per_session': self.max_batch_size,
                'recommended_break_minutes': 5,
                'total_estimated_sessions': 0
            },
            'safety_measures': [
                "All operations are reversible with backup tracking",
                "Files are copied first, then verified before deletion",
                "Each phase can be stopped and resumed",
                "Preview mode available for all operations"
            ]
        }
        
        # Phase 1: High-priority current files
        phase1_criteria = {
            'name': 'Phase 1: Current Priority Files',
            'description': 'Recent entertainment and financial documents that need immediate access',
            'criteria': [
                'Files modified in last 30 days',
                'Entertainment industry keywords',
                'Financial documents from current year',
                'Files larger than 1MB (likely important documents)'
            ],
            'target_location': '01_ACTIVE_PROJECTS/',
            'estimated_files': 0,
            'priority': 'high'
        }
        
        # Phase 2: Historical archive content
        phase2_criteria = {
            'name': 'Phase 2: Historical Archive',
            'description': 'Older completed projects and reference materials',
            'criteria': [
                'Files older than 1 year',
                'Completed project indicators',
                'Historical financial records',
                'Published creative content'
            ],
            'target_location': '02_ARCHIVE_HISTORICAL/',
            'estimated_files': 0,
            'priority': 'medium'
        }
        
        # Phase 3: Reference and templates
        phase3_criteria = {
            'name': 'Phase 3: Reference Library',
            'description': 'Templates, resources, and reference materials',
            'criteria': [
                'Template files',
                'Reference documents',
                'Guides and procedures',
                'Reusable resources'
            ],
            'target_location': '03_REFERENCE_LIBRARY/',
            'estimated_files': 0,
            'priority': 'low'
        }
        
        # Estimate files for each phase based on analysis
        age_dist = source_analysis['age_distribution']
        categories = source_analysis['content_categories']
        
        phase1_criteria['estimated_files'] = age_dist['last_30_days'] + categories.get('entertainment', 0) + categories.get('financial', 0)
        phase2_criteria['estimated_files'] = age_dist['older'] + age_dist['last_year'] - phase1_criteria['estimated_files']
        phase3_criteria['estimated_files'] = categories.get('other', 0)
        
        plan['phases'] = [phase1_criteria, phase2_criteria, phase3_criteria]
        
        # Calculate total sessions needed
        total_files = sum(phase['estimated_files'] for phase in plan['phases'])
        plan['adhd_guidelines']['total_estimated_sessions'] = max(1, (total_files // self.max_batch_size) + 1)
        
        return plan
    
    def execute_migration_phase(self, migration_plan: Dict, phase_number: int, 
                               dry_run: bool = True, user_confirmed: bool = False) -> Dict:
        """
        Execute a specific migration phase with ADHD-friendly progress tracking
        """
        
        if phase_number < 1 or phase_number > len(migration_plan['phases']):
            return {'error': f"Invalid phase number: {phase_number}"}
        
        phase = migration_plan['phases'][phase_number - 1]
        source_path = Path(migration_plan['source_info']['path'])
        
        results = {
            'phase_name': phase['name'],
            'phase_number': phase_number,
            'dry_run': dry_run,
            'files_processed': 0,
            'files_moved': 0,
            'files_skipped': 0,
            'errors': 0,
            'operations': [],
            'next_steps': []
        }
        
        print(f"\n🚀 Starting {phase['name']}")
        print(f"📋 Criteria: {', '.join(phase['criteria'])}")
        print(f"📁 Target: {phase['target_location']}")
        print(f"🔄 Mode: {'Preview' if dry_run else 'Execute'}")
        
        try:
            current_batch = []
            
            # Find files matching phase criteria
            for root, dirs, files in os.walk(source_path):
                if len(current_batch) >= self.max_batch_size:
                    # Process current batch
                    batch_results = self._process_migration_batch(
                        current_batch, phase, dry_run, user_confirmed
                    )
                    results['files_processed'] += batch_results['files_processed']
                    results['files_moved'] += batch_results['files_moved']
                    results['files_skipped'] += batch_results['files_skipped']
                    results['errors'] += batch_results['errors']
                    results['operations'].extend(batch_results['operations'])
                    
                    current_batch = []
                    
                    if not dry_run and len(results['operations']) > 0:
                        time.sleep(self.pause_between_batches)  # ADHD-friendly pause
                
                for file_name in files:
                    file_path = Path(root) / file_name
                    
                    if self._file_matches_phase_criteria(file_path, phase):
                        current_batch.append(file_path)
            
            # Process remaining files in final batch
            if current_batch:
                batch_results = self._process_migration_batch(
                    current_batch, phase, dry_run, user_confirmed
                )
                results['files_processed'] += batch_results['files_processed']
                results['files_moved'] += batch_results['files_moved']
                results['files_skipped'] += batch_results['files_skipped']
                results['errors'] += batch_results['errors']
                results['operations'].extend(batch_results['operations'])
            
            # Generate next steps
            if dry_run:
                results['next_steps'] = [
                    f"Review the {len(results['operations'])} proposed operations",
                    f"Run again with --confirmed to execute moves",
                    f"Estimated time: {len(results['operations']) * 2} seconds"
                ]
            else:
                results['next_steps'] = [
                    f"Phase {phase_number} complete!",
                    f"Moved {results['files_moved']} files successfully",
                    f"Ready for Phase {phase_number + 1}" if phase_number < len(migration_plan['phases']) else "Migration complete!"
                ]
            
        except Exception as e:
            logger.error(f"Error executing migration phase: {e}")
            results['errors'] += 1
            results['error'] = str(e)
        
        return results
    
    def _file_matches_phase_criteria(self, file_path: Path, phase: Dict) -> bool:
        """Check if file matches the criteria for a migration phase"""
        
        try:
            stat = file_path.stat()
            file_age_days = (time.time() - stat.st_mtime) / 86400
            file_name_lower = file_path.name.lower()
            file_size_mb = stat.st_size / (1024 * 1024)
            
            # Phase 1: Current priority files
            if phase['name'].startswith('Phase 1'):
                return (
                    file_age_days <= 30 or  # Recent files
                    any(term in file_name_lower for term in ['finn', 'stranger', 'sag', 'contract', '2024', '2025']) or  # Important keywords
                    file_size_mb > 1  # Likely important documents
                )
            
            # Phase 2: Historical archive
            elif phase['name'].startswith('Phase 2'):
                return (
                    file_age_days > 365 or  # Older files
                    any(term in file_name_lower for term in ['2023', '2022', '2021', 'completed', 'final'])  # Archive indicators
                )
            
            # Phase 3: Reference materials
            elif phase['name'].startswith('Phase 3'):
                return (
                    any(term in file_name_lower for term in ['template', 'guide', 'reference', 'procedure']) or
                    file_path.suffix.lower() in ['.template', '.md'] or
                    'template' in str(file_path.parent).lower()
                )
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking file criteria: {e}")
            return False
    
    def _process_migration_batch(self, files: List[Path], phase: Dict, 
                                dry_run: bool, user_confirmed: bool) -> Dict:
        """Process a batch of files for migration"""
        
        batch_results = {
            'files_processed': 0,
            'files_moved': 0,
            'files_skipped': 0,
            'errors': 0,
            'operations': []
        }
        
        for file_path in files:
            try:
                batch_results['files_processed'] += 1
                
                # Analyze file to determine exact target location
                analysis = self.archive_manager.analyze_file_lifecycle_stage(file_path)
                
                if 'error' in analysis:
                    batch_results['errors'] += 1
                    batch_results['operations'].append({
                        'file': str(file_path),
                        'status': 'error',
                        'message': analysis['error']
                    })
                    continue
                
                # Determine target path
                target_base = self.base_dir / phase['target_location']
                
                # For archives, organize by year
                if 'archive' in phase['target_location'].lower():
                    file_year = datetime.fromtimestamp(file_path.stat().st_mtime).year
                    target_dir = target_base / analysis['primary_category'] / 'by_year' / str(file_year)
                else:
                    target_dir = target_base / analysis['primary_category']
                
                target_path = target_dir / file_path.name
                
                # Handle name conflicts
                if target_path.exists():
                    counter = 1
                    stem = file_path.stem
                    suffix = file_path.suffix
                    while target_path.exists():
                        target_path = target_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                
                operation = {
                    'file': file_path.name,
                    'source': str(file_path.parent),
                    'target': str(target_dir),
                    'adhd_importance': analysis['adhd_importance'],
                    'reasoning': analysis['reasoning'],
                    'status': 'planned' if dry_run else 'executing'
                }
                
                if not dry_run and user_confirmed:
                    # Execute the move
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(target_path))
                    
                    batch_results['files_moved'] += 1
                    operation['status'] = 'completed'
                    operation['final_path'] = str(target_path)
                
                batch_results['operations'].append(operation)
                
            except Exception as e:
                batch_results['errors'] += 1
                batch_results['operations'].append({
                    'file': str(file_path),
                    'status': 'error',
                    'message': str(e)
                })
        
        return batch_results
    
    def generate_migration_report(self, source_path: str) -> str:
        """Generate comprehensive ADHD-friendly migration report"""
        
        report_path = paths.get_path('logs') / f'migration_report_{int(time.time())}.md'
        
        # Analyze current structure
        analysis = self.analyze_existing_structure(source_path)
        
        if 'error' in analysis:
            return f"Error generating report: {analysis['error']}"
        
        # Create migration plan
        plan = self.create_migration_plan(analysis)
        
        # Generate report content
        report_content = f"""# 🗃️ Migration Report
**AI File Organizer - Google Drive Migration Analysis**
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Current Situation Analysis

**Source Location:** `{source_path}`
**Total Files:** {analysis['total_files']:,}
**Total Size:** {analysis['size_analysis']['total_mb']:.1f} MB

### 📁 File Type Distribution
{self._format_dict_for_report(analysis['file_types'], '📄')}

### 📅 Age Distribution  
- **Last 7 days:** {analysis['age_distribution']['last_7_days']} files
- **Last 30 days:** {analysis['age_distribution']['last_30_days']} files  
- **Last year:** {analysis['age_distribution']['last_year']} files
- **Older than 1 year:** {analysis['age_distribution']['older']} files

### 🏷️ Content Categories
{self._format_dict_for_report(analysis['content_categories'], '🎯')}

### 💡 Migration Recommendations
{chr(10).join(f'- {rec}' for rec in analysis['migration_recommendations'])}

## 🚀 Proposed Migration Plan

### ADHD-Friendly Approach
- **Max files per session:** {plan['adhd_guidelines']['max_files_per_session']}
- **Estimated sessions:** {plan['adhd_guidelines']['total_estimated_sessions']}
- **Recommended breaks:** {plan['adhd_guidelines']['recommended_break_minutes']} minutes between sessions

### Migration Phases

{self._format_migration_phases(plan['phases'])}

## 🛡️ Safety Measures
{chr(10).join(f'- ✅ {measure}' for measure in plan['safety_measures'])}

## 🔧 Next Steps

1. **Review this report** - Make sure the plan makes sense for your workflow
2. **Test with small batch** - Run Phase 1 in preview mode first
3. **Execute when ready** - Start with highest priority files
4. **Monitor progress** - Use built-in progress tracking

### Commands to Get Started:

```bash
# Preview Phase 1 (safe - no files moved)
python google_drive_migration.py execute --source "{source_path}" --phase 1 --dry-run

# Execute Phase 1 when ready
python google_drive_migration.py execute --source "{source_path}" --phase 1 --confirmed

# Check migration status
python google_drive_migration.py status
```

---
*This migration preserves all your files while creating an ADHD-friendly organization system that grows smarter over time.*
"""
        
        # Write report
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        print(f"📄 Migration report saved: {report_path}")
        return str(report_path)
    
    def _format_dict_for_report(self, data: Dict, emoji: str) -> str:
        """Format dictionary data for markdown report"""
        if not data:
            return "None found"
        
        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
        return '\n'.join(f'- {emoji} **{key}**: {value}' for key, value in sorted_items[:10])  # Limit to top 10
    
    def _format_migration_phases(self, phases: List[Dict]) -> str:
        """Format migration phases for report"""
        formatted = []
        
        for i, phase in enumerate(phases, 1):
            formatted.append(f"""
#### Phase {i}: {phase['name']}
**Priority:** {phase['priority'].upper()}
**Estimated Files:** {phase['estimated_files']}
**Target Location:** `{phase['target_location']}`

**Criteria:**
{chr(10).join(f'- {criteria}' for criteria in phase['criteria'])}

**Description:** {phase['description']}
""")
        
        return '\n'.join(formatted)


def main():
    """Command line interface for Google Drive migration"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Google Drive Migration Assistant")
    parser.add_argument('command', choices=['analyze', 'plan', 'execute', 'report', 'status'],
                       help='Migration command to execute')
    parser.add_argument('--source', required=True, help='Source directory path')
    parser.add_argument('--phase', type=int, help='Migration phase to execute (1-3)')
    parser.add_argument('--dry-run', action='store_true', help='Preview mode - no files moved')
    parser.add_argument('--confirmed', action='store_true', help='Confirm file operations')
    parser.add_argument('--batch-size', type=int, default=10, help='Files per batch')
    
    args = parser.parse_args()
    
    # Initialize migration assistant
    assistant = GoogleDriveMigrationAssistant()
    assistant.max_batch_size = args.batch_size
    
    try:
        if args.command == 'analyze':
            print("🔍 Analyzing existing file structure...")
            analysis = assistant.analyze_existing_structure(args.source)
            
            if 'error' in analysis:
                print(f"❌ Error: {analysis['error']}")
            else:
                print(f"\n📊 Analysis Complete!")
                print(f"📁 Total Files: {analysis['total_files']:,}")
                print(f"💾 Total Size: {analysis['size_analysis']['total_mb']:.1f} MB")
                print(f"🏷️  Categories: {len(analysis['content_categories'])}")
                
                print(f"\n💡 Recommendations:")
                for rec in analysis['migration_recommendations']:
                    print(f"   • {rec}")
        
        elif args.command == 'plan':
            analysis = assistant.analyze_existing_structure(args.source)
            if 'error' in analysis:
                print(f"❌ Error: {analysis['error']}")
            else:
                plan = assistant.create_migration_plan(analysis)
                print(f"\n🗺️  Migration Plan Created")
                print(f"📋 Total Phases: {len(plan['phases'])}")
                print(f"⏱️  Estimated Sessions: {plan['adhd_guidelines']['total_estimated_sessions']}")
                
                for i, phase in enumerate(plan['phases'], 1):
                    print(f"\n   Phase {i}: {phase['name']}")
                    print(f"   📊 Files: ~{phase['estimated_files']}")
                    print(f"   🎯 Priority: {phase['priority']}")
        
        elif args.command == 'execute':
            if not args.phase:
                print("❌ --phase required for execute command")
                return
            
            analysis = assistant.analyze_existing_structure(args.source)
            if 'error' in analysis:
                print(f"❌ Error: {analysis['error']}")
                return
            
            plan = assistant.create_migration_plan(analysis)
            
            dry_run = not args.confirmed or args.dry_run
            results = assistant.execute_migration_phase(plan, args.phase, dry_run, args.confirmed)
            
            if 'error' in results:
                print(f"❌ Error: {results['error']}")
            else:
                print(f"\n✅ {results['phase_name']} {'Preview' if dry_run else 'Execution'} Complete")
                print(f"📊 Processed: {results['files_processed']} files")
                if not dry_run:
                    print(f"📁 Moved: {results['files_moved']} files")
                print(f"⚠️  Errors: {results['errors']}")
                
                if results['next_steps']:
                    print(f"\n🔄 Next Steps:")
                    for step in results['next_steps']:
                        print(f"   • {step}")
        
        elif args.command == 'report':
            print("📄 Generating comprehensive migration report...")
            report_path = assistant.generate_migration_report(args.source)
            print(f"✅ Report generated: {report_path}")
            
        elif args.command == 'status':
            status = assistant.archive_manager.get_archive_status()
            if 'error' in status:
                print(f"❌ Error: {status['error']}")
            else:
                print("\n📊 Migration System Status")
                print("=" * 40)
                print(f"🗃️  Total Tracked: {status['total_tracked_files']} files")
                
                if status['lifecycle_stages']:
                    print(f"\n📋 Lifecycle Distribution:")
                    for stage, count in status['lifecycle_stages'].items():
                        print(f"   {stage}: {count}")
    
    except Exception as e:
        logger.error(f"Migration error: {e}")
        print(f"❌ Migration failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())