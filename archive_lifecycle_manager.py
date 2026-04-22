#!/usr/bin/env python3
"""
Archive Lifecycle Management System
Handles intelligent aging, archiving, and lifecycle management of files
Based on content analysis and time-based rules while maintaining ADHD-friendly organization
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil
import logging

from path_config import paths
from metadata_generator import MetadataGenerator
from content_extractor import ContentExtractor

# Configure logging
logger = logging.getLogger(__name__)

class ArchiveLifecycleManager:
    """
    Manages the complete lifecycle of files from active use to long-term archival
    Implements ADHD-friendly organization with intelligent automation
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else paths.get_path('documents')
        self.config_path = paths.get_path('organizer_base') / 'classification_rules.json'
        self.db_path = paths.get_path('organizer_base') / 'archive_lifecycle.db'
        
        # Initialize components
        self.metadata_generator = MetadataGenerator(str(self.base_dir))
        self.content_extractor = ContentExtractor(str(self.base_dir))
        
        # Load configuration
        self.config = self._load_configuration()
        self._init_database()
    
    def _load_configuration(self) -> Dict:
        """Load archive lifecycle configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def _init_database(self):
        """Initialize lifecycle tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_lifecycle (
                    file_path TEXT PRIMARY KEY,
                    content_category TEXT,
                    lifecycle_stage TEXT,  -- active, archive_candidate, archived, deep_storage
                    last_accessed REAL,
                    last_modified REAL,
                    archive_date REAL,
                    content_indicators TEXT,  -- JSON list of keywords found
                    retention_years INTEGER,
                    adhd_importance INTEGER,  -- 1-10 scale for ADHD-friendly prioritization
                    user_pinned BOOLEAN DEFAULT 0,  -- User manually marked important
                    archive_notes TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS archive_operations (
                    operation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT,
                    file_path TEXT,
                    source_location TEXT,
                    target_location TEXT,
                    operation_date REAL,
                    success BOOLEAN,
                    notes TEXT
                )
            """)
            
            conn.commit()
    
    def analyze_file_lifecycle_stage(self, file_path: Path) -> Dict:
        """
        Analyze a file to determine its appropriate lifecycle stage
        Returns classification with ADHD-friendly reasoning
        """
        
        try:
            # Get file metadata
            stat = file_path.stat()
            file_age_days = (time.time() - stat.st_mtime) / 86400
            
            # Extract and analyze content with fallback
            content = ""
            extraction_error = None
            
            try:
                extraction_result = self.content_extractor.extract_content(file_path)
                if extraction_result and extraction_result.get('success'):
                    content = extraction_result.get('text', '').lower()
                else:
                    extraction_error = extraction_result.get('error', 'Unknown extraction error') if extraction_result else 'No extraction result'
            except Exception as e:
                extraction_error = f"Content extractor failed: {e}"
            
            # Fallback: use filename for analysis if content extraction fails
            if not content:
                content = file_path.name.lower()
                
                # Only log warnings for unexpected extraction failures
                if extraction_error:
                    # Expected failures for image files, don't spam warnings
                    file_ext = file_path.suffix.lower()
                    if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg']:
                        logger.debug(f"Using filename analysis for image file: {file_path.name}")
                    elif file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.m4a']:
                        logger.debug(f"Using filename analysis for media file: {file_path.name}")
                    else:
                        logger.warning(f"Using filename fallback for {file_path.name}: {extraction_error}")
                else:
                    logger.debug(f"Using filename-based analysis for {file_path.name}")
            
            # Determine content category
            category_scores = {}
            content_indicators = []
            
            for category, rules in self.config.get('classification_rules', {}).items():
                score = 0
                found_keywords = []
                
                # Check keywords
                for keyword in rules.get('keywords', []):
                    if keyword.lower() in content:
                        weight = rules.get('confidence_weights', {}).get(keyword.lower(), 0.5)
                        score += weight
                        found_keywords.append(keyword)
                
                category_scores[category] = score
                if found_keywords:
                    content_indicators.extend(found_keywords)
            
            # Determine primary category
            primary_category = max(category_scores.items(), key=lambda x: x[1])[0] if category_scores else 'unknown'
            
            # Get lifecycle rules for this category
            lifecycle_rules = self.config.get('archive_lifecycle', {}).get(primary_category, {})
            
            # Determine lifecycle stage
            stage = self._determine_lifecycle_stage(
                content, file_age_days, lifecycle_rules, content_indicators
            )
            
            # Calculate ADHD importance score (1-10)
            adhd_importance = self._calculate_adhd_importance(
                content, content_indicators, file_age_days, primary_category
            )
            
            return {
                'primary_category': primary_category,
                'lifecycle_stage': stage,
                'file_age_days': file_age_days,
                'content_indicators': content_indicators,
                'adhd_importance': adhd_importance,
                'category_scores': category_scores,
                'reasoning': self._generate_adhd_friendly_reasoning(stage, adhd_importance, file_age_days, content_indicators),
                'recommended_action': self._get_recommended_action(stage, adhd_importance),
                'retention_years': lifecycle_rules.get('retention_years', 7)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing file lifecycle: {e}")
            return {'error': str(e)}
    
    def _determine_lifecycle_stage(self, content: str, file_age_days: float, 
                                  rules: Dict, indicators: List[str]) -> str:
        """Determine appropriate lifecycle stage for file"""
        
        # Check for explicit active/archive indicators
        active_keywords = rules.get('active_keywords', [])
        archive_keywords = rules.get('archive_keywords', [])
        age_threshold_months = rules.get('age_threshold_months', 12)
        
        # Check content for stage indicators
        has_active_indicators = any(keyword.lower() in content for keyword in active_keywords)
        has_archive_indicators = any(keyword.lower() in content for keyword in archive_keywords)
        
        # Age-based determination
        age_threshold_days = age_threshold_months * 30
        
        if has_active_indicators:
            return 'active'
        elif has_archive_indicators or file_age_days > age_threshold_days:
            if file_age_days > (age_threshold_days * 2):
                return 'deep_storage_candidate'
            else:
                return 'archive_candidate'
        else:
            return 'active'
    
    def _calculate_adhd_importance(self, content: str, indicators: List[str], 
                                  file_age_days: float, category: str) -> int:
        """
        Calculate ADHD-friendly importance score (1-10)
        Higher scores = more important to keep easily accessible
        """
        
        score = 5  # Base score
        
        # Category-based importance
        category_importance = {
            'entertainment_industry': 8,  # High - core business
            'financial_documents': 9,     # Critical - legal/tax requirements
            'creative_projects': 7,       # High - personal passion projects
            'development_projects': 6     # Medium-high - professional work
        }
        
        base_importance = category_importance.get(category, 5)
        
        # Recency bonus (ADHD: recent = more likely to need again)
        if file_age_days < 30:
            score += 2
        elif file_age_days < 90:
            score += 1
        elif file_age_days > 365:
            score -= 1
        
        # Content-specific indicators
        high_importance_terms = [
            'finn wolfhard', 'stranger things', 'contract', 'agreement',
            'tax', 'payment', 'invoice', 'papers that dream',
            'current', 'active', 'pending', 'urgent'
        ]
        
        importance_boost = sum(1 for term in high_importance_terms 
                             if term in content.lower())
        score += min(importance_boost, 3)  # Cap boost at 3 points
        
        # Frequency indicators (common ADHD patterns)
        if 'monthly' in content.lower() or 'weekly' in content.lower():
            score += 1
        
        if 'deadline' in content.lower() or 'due' in content.lower():
            score += 2
        
        # Personal connection boost (ADHD: emotional relevance = higher retention)
        personal_terms = ['ryan', 'personal', 'important', 'remember']
        if any(term in content.lower() for term in personal_terms):
            score += 1
        
        # Ensure score is within bounds
        return max(1, min(10, score))
    
    def _generate_adhd_friendly_reasoning(self, stage: str, importance: int, 
                                        age_days: float, indicators: List[str]) -> str:
        """Generate clear, ADHD-friendly explanation of classification"""
        
        reasoning = []
        
        # Clear stage explanation with visual context
        stage_explanations = {
            'active': f"🔴 KEEP ACTIVE: This file is current work that needs easy access",
            'archive_candidate': f"🟡 READY TO ARCHIVE: {int(age_days)} days old, completed work can be filed away",
            'deep_storage_candidate': f"🔵 DEEP STORAGE: {int(age_days)} days old, rarely needed, safe to store long-term",
        }
        
        reasoning.append(stage_explanations.get(stage, f"📋 Classification: {stage}"))
        
        # Clear importance explanation with reasoning
        if importance >= 8:
            reasoning.append(f"⭐ HIGH IMPORTANCE ({importance}/10): Contains critical business/legal content - keep accessible")
        elif importance >= 6:
            reasoning.append(f"📊 MEDIUM IMPORTANCE ({importance}/10): Useful reference material - archive but keep searchable")
        else:
            reasoning.append(f"📦 LOW IMPORTANCE ({importance}/10): Routine content - safe for long-term storage")
        
        # Key indicators with context
        if indicators:
            key_terms = indicators[:3]  # Limit to 3 for ADHD readability
            reasoning.append(f"🔍 Found key terms: {', '.join(key_terms)} (indicates content type)")
        
        # Clear time context
        if age_days < 7:
            reasoning.append("⚡ Very recent - definitely keep active")
        elif age_days < 30:
            reasoning.append("⏰ Recent file - likely still working on this")
        elif age_days < 365:
            reasoning.append("📆 Aging file - may be ready to archive")
        else:
            reasoning.append("📅 Old file - completed work, good candidate for archiving")
        
        return " • ".join(reasoning)
    
    def _get_recommended_action(self, stage: str, importance: int) -> str:
        """Get ADHD-friendly recommended action with clear next steps"""
        
        if stage == 'active':
            return "✅ KEEP ACTIVE: Leave in current active projects folder - you're likely still working on this"
        elif stage == 'archive_candidate':
            if importance >= 8:
                return "📁 ARCHIVE (High Priority): Move to archive but keep easily searchable - important reference material"
            elif importance >= 6:
                return "📦 ARCHIVE (Standard): Move to historical archive folder - completed work, good to file away"
            else:
                return "🗄️ ARCHIVE (Low Priority): Move to deep storage - routine content, rarely needed"
        elif stage == 'deep_storage_candidate':
            if importance >= 8:
                return "⚠️ REVIEW NEEDED: High importance but very old - consider if still relevant before deep storage"
            else:
                return "🗃️ DEEP STORAGE: Move to compressed long-term storage - very old, rarely accessed"
        else:
            return "❓ MANUAL REVIEW: Unclear classification - review manually to decide best location"
    
    def suggest_archive_actions(self, directory: Path = None, 
                               limit: int = 20) -> List[Dict]:
        """
        Generate ADHD-friendly archive suggestions
        Limited to manageable batches to avoid overwhelm
        """
        
        if directory is None:
            directory = self.base_dir
        
        suggestions = []
        processed_count = 0
        
        # Find files that might need archiving
        for file_path in directory.rglob("*"):
            if not file_path.is_file() or processed_count >= limit:
                break
            
            # Skip certain file types
            if file_path.suffix.lower() in {'.db', '.log', '.tmp', '.cache'}:
                continue
            
            # Analyze file
            analysis = self.analyze_file_lifecycle_stage(file_path)
            
            if 'error' not in analysis:
                stage = analysis['lifecycle_stage']
                
                # Only suggest files that need action
                if stage in ['archive_candidate', 'deep_storage_candidate']:
                    suggestions.append({
                        'file_path': str(file_path),
                        'file_name': file_path.name,
                        'current_location': str(file_path.parent),
                        'suggested_stage': stage,
                        'adhd_importance': analysis['adhd_importance'],
                        'reasoning': analysis['reasoning'],
                        'recommended_action': analysis['recommended_action'],
                        'age_days': int(analysis['file_age_days']),
                        'category': analysis['primary_category']
                    })
                
                processed_count += 1
        
        # Sort by ADHD importance (high importance first for user review)
        suggestions.sort(key=lambda x: x['adhd_importance'], reverse=True)
        
        return suggestions
    
    def execute_archive_action(self, file_path: str, target_stage: str, 
                              user_confirmed: bool = False) -> Dict:
        """
        Execute archive action with safety checks and ADHD-friendly feedback
        """
        
        source_path = Path(file_path)
        
        if not source_path.exists():
            return {'success': False, 'error': 'File not found'}
        
        try:
            # Determine target location
            analysis = self.analyze_file_lifecycle_stage(source_path)
            category = analysis['primary_category']
            
            # Get target folder from configuration
            folder_mappings = self.config.get('folder_mappings', {})
            
            if target_stage == 'archive_candidate':
                target_key = f"{category}_archive"
            else:
                target_key = f"{category}_active"
            
            target_base = folder_mappings.get(target_key, '02_ARCHIVE_HISTORICAL/')
            target_dir = self.base_dir / target_base
            
            # For archive, organize by year
            if 'archive' in target_stage:
                file_year = datetime.fromtimestamp(source_path.stat().st_mtime).year
                target_dir = target_dir / str(file_year)
            
            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / source_path.name
            
            # Handle file name conflicts
            if target_path.exists():
                counter = 1
                stem = source_path.stem
                suffix = source_path.suffix
                while target_path.exists():
                    target_path = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            
            # Execute move (with backup capability)
            backup_location = None
            if user_confirmed:
                # Create backup reference before moving
                backup_location = str(source_path)
                
                # Move file
                shutil.move(str(source_path), str(target_path))
                
                # Record operation
                self._record_archive_operation(
                    'move_to_archive', str(source_path), str(target_path), True
                )
                
                # Update lifecycle database
                self._update_file_lifecycle(str(target_path), target_stage, analysis)
            
            return {
                'success': True,
                'source_path': str(source_path),
                'target_path': str(target_path),
                'backup_location': backup_location,
                'operation': 'move' if user_confirmed else 'preview',
                'adhd_feedback': f"✅ Moved {source_path.name} to {target_dir.name}/" if user_confirmed else f"📋 Would move {source_path.name} to {target_dir.name}/"
            }
            
        except Exception as e:
            logger.error(f"Error executing archive action: {e}")
            return {'success': False, 'error': str(e)}
    
    def _record_archive_operation(self, operation_type: str, source: str, 
                                 target: str, success: bool, notes: str = None):
        """Record archive operation for audit trail"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO archive_operations 
                (operation_type, file_path, source_location, target_location, 
                 operation_date, success, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (operation_type, source, source, target, time.time(), success, notes))
            conn.commit()
    
    def _update_file_lifecycle(self, file_path: str, stage: str, analysis: Dict):
        """Update file lifecycle tracking"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO file_lifecycle 
                (file_path, content_category, lifecycle_stage, last_modified, 
                 archive_date, content_indicators, retention_years, adhd_importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_path,
                analysis['primary_category'],
                stage,
                time.time(),
                time.time() if 'archive' in stage else None,
                json.dumps(analysis['content_indicators']),
                analysis['retention_years'],
                analysis['adhd_importance']
            ))
            conn.commit()
    
    def get_archive_status(self) -> Dict:
        """Get comprehensive archive system status"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get lifecycle stage counts
                cursor = conn.execute("""
                    SELECT lifecycle_stage, COUNT(*) 
                    FROM file_lifecycle 
                    GROUP BY lifecycle_stage
                """)
                stage_counts = dict(cursor.fetchall())
                
                # Get recent operations
                cursor = conn.execute("""
                    SELECT operation_type, COUNT(*), AVG(success) 
                    FROM archive_operations 
                    WHERE operation_date > ? 
                    GROUP BY operation_type
                """, (time.time() - 86400,))  # Last 24 hours
                
                recent_operations = {row[0]: {'count': row[1], 'success_rate': row[2]} 
                                   for row in cursor.fetchall()}
                
                # Get ADHD importance distribution
                cursor = conn.execute("""
                    SELECT 
                        CASE 
                            WHEN adhd_importance >= 8 THEN 'high'
                            WHEN adhd_importance >= 6 THEN 'medium'
                            ELSE 'low'
                        END as importance_level,
                        COUNT(*)
                    FROM file_lifecycle 
                    GROUP BY importance_level
                """)
                importance_distribution = dict(cursor.fetchall())
            
            return {
                'lifecycle_stages': stage_counts,
                'recent_operations_24h': recent_operations,
                'importance_distribution': importance_distribution,
                'database_path': str(self.db_path),
                'total_tracked_files': sum(stage_counts.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting archive status: {e}")
            return {'error': str(e)}


def main():
    """Command line interface for archive lifecycle management"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Archive Lifecycle Manager")
    parser.add_argument('command', 
                       choices=['suggest', 'analyze', 'execute', 'status'],
                       help='Command to execute')
    parser.add_argument('--file', help='File path to analyze or execute action on')
    parser.add_argument('--directory', help='Directory to scan for suggestions')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of suggestions')
    parser.add_argument('--confirmed', action='store_true', help='Confirm execution of actions')
    
    args = parser.parse_args()
    
    manager = ArchiveLifecycleManager()
    
    if args.command == 'suggest':
        directory = Path(args.directory) if args.directory else None
        suggestions = manager.suggest_archive_actions(directory, args.limit)
        
        print(f"\n📋 Archive Suggestions ({len(suggestions)} files)")
        print("=" * 60)
        
        for i, suggestion in enumerate(suggestions[:10], 1):  # Limit display to 10 for ADHD readability
            print(f"\n{i}. 📄 {suggestion['file_name']}")
            print(f"   📅 Age: {suggestion['age_days']} days")
            print(f"   ⭐ Importance: {suggestion['adhd_importance']}/10")
            print(f"   💡 {suggestion['reasoning']}")
            print(f"   ➡️  {suggestion['recommended_action']}")
        
        if len(suggestions) > 10:
            print(f"\n... and {len(suggestions) - 10} more suggestions")
    
    elif args.command == 'analyze' and args.file:
        file_path = Path(args.file)
        analysis = manager.analyze_file_lifecycle_stage(file_path)
        
        if 'error' in analysis:
            print(f"❌ Error: {analysis['error']}")
        else:
            print(f"\n📊 File Analysis: {file_path.name}")
            print("=" * 50)
            print(f"📂 Category: {analysis['primary_category']}")
            print(f"🔄 Stage: {analysis['lifecycle_stage']}")
            print(f"⭐ ADHD Importance: {analysis['adhd_importance']}/10")
            print(f"📅 Age: {int(analysis['file_age_days'])} days")
            print(f"💡 Reasoning: {analysis['reasoning']}")
            print(f"➡️  Action: {analysis['recommended_action']}")
    
    elif args.command == 'status':
        status = manager.get_archive_status()
        
        if 'error' in status:
            print(f"❌ Error: {status['error']}")
        else:
            print("\n📊 Archive System Status")
            print("=" * 40)
            print(f"🗃️  Total Tracked Files: {status['total_tracked_files']}")
            print(f"📁 Database: {Path(status['database_path']).name}")
            
            print("\n📋 Lifecycle Stages:")
            for stage, count in status['lifecycle_stages'].items():
                print(f"   {stage}: {count}")
            
            print("\n⭐ Importance Distribution:")
            for level, count in status['importance_distribution'].items():
                print(f"   {level}: {count}")

if __name__ == "__main__":
    main()