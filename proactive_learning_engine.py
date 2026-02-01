#!/usr/bin/env python3
"""
Proactive Learning Engine for AI File Organizer
Automatically discovers patterns, creates new categories, and evolves folder structure
ADHD-friendly design with clear reasoning and manageable suggestions
"""

import sys
import os
import json
import sqlite3
from gdrive_integration import get_metadata_root
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
import re

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from learning_stats import LearningStatsTracker
from creative_idea_generator import CreativeIdeaGenerator
from custom_categories import CustomCategoryManager
from tagging_system import ComprehensiveTaggingSystem

@dataclass
class FolderSuggestion:
    """Represents a proactive folder structure suggestion"""
    folder_name: str
    folder_path: str
    confidence: float
    reasoning: List[str]
    supporting_files: List[str]
    pattern_evidence: Dict[str, Any]
    urgency: str  # 'high', 'medium', 'low'
    adhd_priority: int  # 1-10, higher = more important for ADHD workflow

@dataclass
class LearningInsight:
    """Represents a learning insight that could trigger changes"""
    insight_type: str  # 'frequent_correction', 'new_pattern', 'folder_overflow'
    description: str
    confidence: float
    suggested_action: str
    evidence: Dict[str, Any]
    file_count: int

class ProactiveLearningEngine:
    """
    Proactive learning system that automatically evolves the organization structure
    Based on pattern discovery, user corrections, and content analysis
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        
        # Initialize learning directory
        self.learning_dir = get_metadata_root() / "proactive_learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = self.learning_dir / "proactive_learning.db"
        self._init_database()
        
        # Initialize subsystems
        self.learning_tracker = LearningStatsTracker(str(self.base_dir))
        self.pattern_generator = CreativeIdeaGenerator(str(self.base_dir))
        self.category_manager = CustomCategoryManager(str(self.base_dir))
        self.tagging_system = ComprehensiveTaggingSystem(str(self.base_dir))
        
        # Proactive learning thresholds
        self.thresholds = {
            'min_corrections_for_rule_update': 3,
            'min_pattern_frequency_for_folder': 5,
            'min_files_in_temp_for_suggestion': 10,
            'confidence_threshold_for_auto_action': 0.85,
            'min_tag_frequency_for_category': 8
        }
        
        # ADHD-friendly settings
        self.adhd_settings = {
            'max_suggestions_per_session': 3,
            'prioritize_high_impact_changes': True,
            'require_explicit_confirmation': True,
            'batch_similar_suggestions': True
        }
    
    def _init_database(self):
        """Initialize proactive learning database"""
        with sqlite3.connect(self.db_path) as conn:
            # Folder suggestions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS folder_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_name TEXT,
                    folder_path TEXT,
                    confidence REAL,
                    reasoning TEXT,  -- JSON array
                    supporting_files TEXT,  -- JSON array
                    pattern_evidence TEXT,  -- JSON object
                    urgency TEXT,
                    adhd_priority INTEGER,
                    status TEXT,  -- 'pending', 'accepted', 'rejected', 'auto_implemented'
                    suggested_date TEXT,
                    reviewed_date TEXT,
                    implementation_date TEXT
                )
            """)
            
            # Learning insights table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insight_type TEXT,
                    description TEXT,
                    confidence REAL,
                    suggested_action TEXT,
                    evidence TEXT,  -- JSON object
                    file_count INTEGER,
                    status TEXT,
                    created_date TEXT,
                    processed_date TEXT
                )
            """)
            
            # Auto-implemented changes log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auto_changes_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    change_type TEXT,
                    change_description TEXT,
                    confidence REAL,
                    files_affected INTEGER,
                    before_state TEXT,  -- JSON
                    after_state TEXT,   -- JSON
                    implemented_date TEXT,
                    success BOOLEAN
                )
            """)
            
            conn.commit()
    
    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current system state to identify improvement opportunities"""
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'insights': [],
            'folder_suggestions': [],
            'auto_actions': []
        }
        
        print("🧠 Analyzing current system state for proactive improvements...")
        
        # 1. Analyze learning corrections
        correction_insights = self._analyze_correction_patterns()
        analysis['insights'].extend(correction_insights)
        
        # 2. Analyze discovered patterns
        pattern_insights = self._analyze_discovered_patterns()
        analysis['insights'].extend(pattern_insights)
        
        # 3. Analyze folder usage and overflow
        folder_insights = self._analyze_folder_usage()
        analysis['insights'].extend(folder_insights)
        
        # 4. Analyze tag patterns for new categories
        tag_insights = self._analyze_tag_patterns()
        analysis['insights'].extend(tag_insights)
        
        # 5. Generate folder suggestions based on insights
        folder_suggestions = self._generate_folder_suggestions(analysis['insights'])
        analysis['folder_suggestions'] = folder_suggestions
        
        # 6. Identify auto-implementable actions
        auto_actions = self._identify_auto_actions(analysis['insights'])
        analysis['auto_actions'] = auto_actions
        
        print(f"✅ Analysis complete: {len(analysis['insights'])} insights, {len(folder_suggestions)} folder suggestions, {len(auto_actions)} auto-actions")
        
        return analysis
    
    def _analyze_correction_patterns(self) -> List[LearningInsight]:
        """Analyze user corrections to identify systematic issues"""
        
        insights = []
        
        try:
            # Get correction data from learning tracker
            try:
                metrics = self.learning_tracker.get_classification_metrics(days=30)
            except AttributeError:
                metrics = None
            try:
                patterns = self.learning_tracker.get_correction_patterns(limit=50)
            except AttributeError:
                patterns = {'detailed_patterns': []}
            
            # Find frequent corrections (same from -> to pattern)
            correction_frequency = Counter()
            for pattern in patterns.get('detailed_patterns', []):
                key = f"{pattern['from']} → {pattern['to']}"
                correction_frequency[key] += 1
            
            # Identify corrections that should trigger rule updates
            for correction, frequency in correction_frequency.most_common(10):
                if frequency >= self.thresholds['min_corrections_for_rule_update']:
                    from_cat, to_cat = correction.split(' → ')
                    
                    insights.append(LearningInsight(
                        insight_type='frequent_correction',
                        description=f"Frequent correction: {from_cat} → {to_cat} ({frequency} times)",
                        confidence=min(frequency / self.thresholds['min_corrections_for_rule_update'], 1.0),
                        suggested_action=f"Update classification rules to prefer {to_cat} for patterns currently matching {from_cat}",
                        evidence={
                            'correction_pattern': correction,
                            'frequency': frequency,
                            'confidence_improvement_potential': 0.2
                        },
                        file_count=frequency
                    ))
            
            # Check for consistently low confidence categories
            if metrics and 'category_breakdown' in metrics:
                for category, stats in metrics['category_breakdown'].items():
                    if stats.get('accuracy', 1.0) < 0.7 and stats.get('count', 0) > 5:
                        insights.append(LearningInsight(
                            insight_type='low_accuracy_category',
                            description=f"Category '{category}' has low accuracy ({stats['accuracy']:.1%})",
                            confidence=1.0 - stats['accuracy'],
                            suggested_action=f"Review and enhance classification patterns for {category}",
                            evidence={
                                'category': category,
                                'accuracy': stats['accuracy'],
                                'sample_count': stats['count']
                            },
                            file_count=stats['count']
                        ))
        
        except Exception as e:
            print(f"⚠️ Error analyzing correction patterns: {e}")
        
        return insights
    
    def _analyze_discovered_patterns(self) -> List[LearningInsight]:
        """Analyze discovered content patterns for folder creation opportunities"""
        
        insights = []
        
        try:
            # Get discovered patterns from creative idea generator
            try:
                patterns = self.pattern_generator._analyze_content_patterns()
            except AttributeError:
                # Method name might be different, try alternative
                try:
                    patterns = []
                    # Alternative: get saved patterns from database
                    if hasattr(self.pattern_generator, 'get_content_patterns'):
                        patterns = self.pattern_generator.get_content_patterns()
                except:
                    patterns = []
            
            # Look for patterns that could become new folders
            for pattern in patterns:
                if (pattern.frequency >= self.thresholds['min_pattern_frequency_for_folder'] and
                    pattern.creative_potential >= 0.6):
                    
                    insights.append(LearningInsight(
                        insight_type='new_pattern',
                        description=f"Discovered recurring pattern: {pattern.pattern_name}",
                        confidence=pattern.creative_potential,
                        suggested_action=f"Create new folder category for {pattern.pattern_name}",
                        evidence={
                            'pattern_name': pattern.pattern_name,
                            'pattern_type': pattern.pattern_type,
                            'frequency': pattern.frequency,
                            'related_files': pattern.related_files,
                            'variations': pattern.variations
                        },
                        file_count=len(pattern.related_files)
                    ))
        
        except Exception as e:
            print(f"⚠️ Error analyzing discovered patterns: {e}")
        
        return insights
    
    def _analyze_folder_usage(self) -> List[LearningInsight]:
        """Analyze folder usage patterns to identify overflow or underuse"""
        
        insights = []
        
        try:
            # Check temp/processing folders for files that might need new categories
            temp_dirs = [
                self.base_dir / "99_TEMP_PROCESSING",
                Path.home() / "Downloads",
                Path.home() / "Desktop"
            ]
            
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    files = [f for f in temp_dir.iterdir() if f.is_file()]
                    
                    if len(files) >= self.thresholds['min_files_in_temp_for_suggestion']:
                        # Analyze file types in temp folder
                        file_analysis = self._analyze_temp_files(files)
                        
                        if file_analysis['dominant_patterns']:
                            insights.append(LearningInsight(
                                insight_type='folder_overflow',
                                description=f"{temp_dir.name} has {len(files)} files with patterns: {', '.join(file_analysis['dominant_patterns'][:3])}",
                                confidence=0.8,
                                suggested_action=f"Create specialized folders for patterns found in {temp_dir.name}",
                                evidence={
                                    'folder_path': str(temp_dir),
                                    'file_count': len(files),
                                    'patterns': file_analysis['dominant_patterns'],
                                    'file_types': file_analysis['file_types']
                                },
                                file_count=len(files)
                            ))
        
        except Exception as e:
            print(f"⚠️ Error analyzing folder usage: {e}")
        
        return insights
    
    def _analyze_tag_patterns(self) -> List[LearningInsight]:
        """Analyze tagging patterns to suggest new categories"""
        
        insights = []
        
        try:
            # Get tag statistics
            stats = self.tagging_system.get_tag_statistics()
            
            if stats and 'most_used_tags' in stats:
                # Look for frequently used tags that could become categories
                for tag_info in stats['most_used_tags']:
                    if (tag_info['usage_count'] >= self.thresholds['min_tag_frequency_for_category'] and
                        not tag_info['tag'].startswith(('person:', 'time:', 'version:'))):
                        
                        # Check if this tag pattern suggests a new folder category
                        category_suggestion = self._suggest_category_from_tag(tag_info['tag'])
                        
                        if category_suggestion:
                            insights.append(LearningInsight(
                                insight_type='tag_pattern',
                                description=f"Tag '{tag_info['tag']}' used {tag_info['usage_count']} times - suggests new category",
                                confidence=min(tag_info['usage_count'] / 20, 1.0),
                                suggested_action=f"Create category '{category_suggestion}' based on tag usage patterns",
                                evidence={
                                    'tag': tag_info['tag'],
                                    'usage_count': tag_info['usage_count'],
                                    'suggested_category': category_suggestion,
                                    'file_count': tag_info['file_count']
                                },
                                file_count=tag_info['file_count']
                            ))
        
        except Exception as e:
            print(f"⚠️ Error analyzing tag patterns: {e}")
        
        return insights
    
    def _analyze_temp_files(self, files: List[Path]) -> Dict[str, Any]:
        """Analyze files in temp directories to identify patterns"""
        
        analysis = {
            'file_types': Counter(),
            'naming_patterns': Counter(),
            'content_patterns': Counter(),
            'dominant_patterns': []
        }
        
        # Analyze file extensions
        for file in files:
            if file.is_file():
                analysis['file_types'][file.suffix.lower()] += 1
        
        # Analyze naming patterns
        for file in files:
            filename = file.name.lower()
            
            # Common naming patterns
            if 'contract' in filename or 'agreement' in filename:
                analysis['naming_patterns']['contracts'] += 1
            elif 'invoice' in filename or 'payment' in filename:
                analysis['naming_patterns']['financial'] += 1
            elif 'script' in filename or 'screenplay' in filename:
                analysis['naming_patterns']['scripts'] += 1
            elif 'demo' in filename or 'reel' in filename:
                analysis['naming_patterns']['demo_materials'] += 1
            elif 'episode' in filename or 'podcast' in filename:
                analysis['naming_patterns']['podcast_content'] += 1
        
        # Identify dominant patterns
        all_patterns = list(analysis['naming_patterns'].keys()) + [f"*{ext}" for ext in analysis['file_types'].keys()]
        pattern_counts = {**analysis['naming_patterns'], **{f"*{ext}": count for ext, count in analysis['file_types'].items()}}
        
        analysis['dominant_patterns'] = [pattern for pattern, count in 
                                       sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True) 
                                       if count >= 3][:5]
        
        return analysis
    
    def _suggest_category_from_tag(self, tag: str) -> Optional[str]:
        """Suggest a category name from a frequently used tag"""
        
        tag_to_category = {
            'tech:ai': 'AI_Research',
            'tech:alphago': 'AI_Game_Theory',
            'type:contract': 'Legal_Documents',
            'type:script': 'Screenplay_Drafts',
            'type:podcast': 'Audio_Content',
            'project:stranger_things': 'Netflix_Projects',
            'creative:music': 'Music_Production',
            'business:commission': 'Commission_Tracking'
        }
        
        # Direct mapping
        if tag in tag_to_category:
            return tag_to_category[tag]
        
        # Pattern-based suggestions
        if tag.startswith('project:'):
            project_name = tag.replace('project:', '').replace('_', ' ').title().replace(' ', '_')
            return f"{project_name}_Files"
        
        if tag.startswith('type:') and tag.count(':') == 1:
            content_type = tag.replace('type:', '').replace('_', ' ').title().replace(' ', '_')
            return f"{content_type}_Documents"
        
        if tag.startswith('tech:'):
            tech_area = tag.replace('tech:', '').replace('_', ' ').title().replace(' ', '_')
            return f"{tech_area}_Technology"
        
        return None
    
    def _generate_folder_suggestions(self, insights: List[LearningInsight]) -> List[FolderSuggestion]:
        """Generate concrete folder suggestions from insights"""
        
        suggestions = []
        
        # Group insights by type for better suggestions
        insights_by_type = defaultdict(list)
        for insight in insights:
            insights_by_type[insight.insight_type].append(insight)
        
        # Process new pattern insights
        for insight in insights_by_type['new_pattern']:
            evidence = insight.evidence
            folder_name = evidence['pattern_name'].replace(' ', '_').title()
            
            # Determine appropriate parent folder
            if 'business' in evidence['pattern_name'].lower():
                parent_folder = "01_ACTIVE_PROJECTS/Business_Operations"
            elif 'creative' in evidence['pattern_name'].lower():
                parent_folder = "01_ACTIVE_PROJECTS/Creative_Projects"
            elif 'entertainment' in evidence['pattern_name'].lower():
                parent_folder = "01_ACTIVE_PROJECTS/Entertainment_Industry"
            else:
                parent_folder = "01_ACTIVE_PROJECTS"
            
            folder_path = f"{parent_folder}/{folder_name}"
            
            suggestions.append(FolderSuggestion(
                folder_name=folder_name,
                folder_path=folder_path,
                confidence=insight.confidence,
                reasoning=[
                    f"Discovered recurring pattern: {evidence['pattern_name']}",
                    f"Found in {evidence['frequency']} different contexts",
                    f"Creative potential score: {evidence.get('creative_potential', 0):.1%}",
                    f"Related files: {len(evidence['related_files'])}"
                ],
                supporting_files=evidence['related_files'][:10],
                pattern_evidence=evidence,
                urgency='medium',
                adhd_priority=7 if insight.file_count > 10 else 5
            ))
        
        # Process tag pattern insights
        for insight in insights_by_type['tag_pattern']:
            evidence = insight.evidence
            category_name = evidence['suggested_category']
            
            # Smart folder path assignment
            if 'AI' in category_name or 'Tech' in category_name:
                parent_folder = "01_ACTIVE_PROJECTS/Development_Projects"
            elif 'Legal' in category_name or 'Contract' in category_name:
                parent_folder = "01_ACTIVE_PROJECTS/Entertainment_Industry/Current_Contracts"
            elif 'Audio' in category_name or 'Music' in category_name:
                parent_folder = "01_ACTIVE_PROJECTS/Creative_Projects"
            else:
                parent_folder = "01_ACTIVE_PROJECTS"
            
            folder_path = f"{parent_folder}/{category_name}"
            
            suggestions.append(FolderSuggestion(
                folder_name=category_name,
                folder_path=folder_path,
                confidence=insight.confidence,
                reasoning=[
                    f"Tag '{evidence['tag']}' used {evidence['usage_count']} times",
                    f"Applied to {evidence['file_count']} different files",
                    f"Suggests specialized category need",
                    f"Would improve organization efficiency"
                ],
                supporting_files=[f"Files with tag: {evidence['tag']}"],
                pattern_evidence=evidence,
                urgency='medium',
                adhd_priority=8 if evidence['usage_count'] > 15 else 6
            ))
        
        # Process folder overflow insights
        for insight in insights_by_type['folder_overflow']:
            evidence = insight.evidence
            patterns = evidence['patterns'][:3]  # Top 3 patterns
            
            for pattern in patterns:
                if pattern.startswith('*'):  # File extension pattern
                    ext = pattern[1:]
                    folder_name = f"Unsorted_{ext.upper()}_Files"
                    parent_folder = "99_TEMP_PROCESSING"
                else:  # Content pattern
                    folder_name = pattern.replace('_', ' ').title().replace(' ', '_')
                    parent_folder = "01_ACTIVE_PROJECTS"
                
                folder_path = f"{parent_folder}/{folder_name}"
                
                suggestions.append(FolderSuggestion(
                    folder_name=folder_name,
                    folder_path=folder_path,
                    confidence=0.8,
                    reasoning=[
                        f"Found {evidence['file_count']} files in {Path(evidence['folder_path']).name}",
                        f"Pattern '{pattern}' appears frequently",
                        f"Creating specialized folder would reduce clutter",
                        f"ADHD benefit: clearer mental model"
                    ],
                    supporting_files=[f"Files in {evidence['folder_path']}"],
                    pattern_evidence=evidence,
                    urgency='high' if evidence['file_count'] > 20 else 'medium',
                    adhd_priority=9 if evidence['file_count'] > 20 else 7
                ))
        
        # Sort suggestions by ADHD priority and confidence
        suggestions.sort(key=lambda x: (x.adhd_priority, x.confidence), reverse=True)
        
        # Limit to manageable number for ADHD-friendly workflow
        return suggestions[:self.adhd_settings['max_suggestions_per_session']]
    
    def _identify_auto_actions(self, insights: List[LearningInsight]) -> List[Dict[str, Any]]:
        """Identify actions that can be automatically implemented with high confidence"""
        
        auto_actions = []
        
        for insight in insights:
            if (insight.confidence >= self.thresholds['confidence_threshold_for_auto_action'] and
                insight.insight_type == 'frequent_correction'):
                
                evidence = insight.evidence
                correction = evidence['correction_pattern']
                
                auto_actions.append({
                    'action_type': 'update_classification_rule',
                    'description': f"Auto-update rule based on correction pattern: {correction}",
                    'confidence': insight.confidence,
                    'implementation': {
                        'rule_type': 'pattern_weight_adjustment',
                        'from_category': correction.split(' → ')[0],
                        'to_category': correction.split(' → ')[1],
                        'weight_adjustment': 0.2
                    },
                    'files_affected': insight.file_count,
                    'safety_level': 'safe'  # Won't break existing functionality
                })
        
        return auto_actions
    
    def implement_suggestions(self, suggestions: List[FolderSuggestion], 
                            interactive: bool = True) -> Dict[str, Any]:
        """Implement folder suggestions with ADHD-friendly workflow"""
        
        results = {
            'implemented': [],
            'skipped': [],
            'errors': []
        }
        
        if not suggestions:
            print("📝 No folder suggestions to implement")
            return results
        
        print(f"🚀 Implementing {len(suggestions)} folder suggestions...")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n📁 [{i}/{len(suggestions)}] Suggestion: {suggestion.folder_name}")
            print(f"   📍 Path: {suggestion.folder_path}")
            print(f"   🎯 Confidence: {suggestion.confidence:.1%}")
            print(f"   🧠 ADHD Priority: {suggestion.adhd_priority}/10")
            print("   💭 Reasoning:")
            for reason in suggestion.reasoning:
                print(f"      • {reason}")
            
            if interactive and self.adhd_settings['require_explicit_confirmation']:
                response = input(f"\n   ❓ Implement this suggestion? [y/N/s(kip all)]: ").lower().strip()
                
                if response == 's':
                    print("   ⏩ Skipping all remaining suggestions")
                    break
                elif response != 'y':
                    print("   ⏭️  Skipped")
                    results['skipped'].append(suggestion.folder_name)
                    continue
            
            # Implement the suggestion
            try:
                success = self._create_folder_structure(suggestion)
                
                if success:
                    print("   ✅ Folder structure created successfully")
                    results['implemented'].append(suggestion.folder_name)
                    
                    # Save to database
                    self._save_implemented_suggestion(suggestion, success=True)
                else:
                    print("   ❌ Failed to create folder structure")
                    results['errors'].append(suggestion.folder_name)
                    self._save_implemented_suggestion(suggestion, success=False)
                    
            except Exception as e:
                print(f"   💥 Error implementing suggestion: {e}")
                results['errors'].append(suggestion.folder_name)
                self._save_implemented_suggestion(suggestion, success=False, error=str(e))
        
        # Summary
        print(f"\n📊 Implementation Summary:")
        print(f"   ✅ Implemented: {len(results['implemented'])}")
        print(f"   ⏭️  Skipped: {len(results['skipped'])}")
        print(f"   ❌ Errors: {len(results['errors'])}")
        
        if results['implemented']:
            print(f"\n🎉 New folders created:")
            for folder in results['implemented']:
                print(f"   📁 {folder}")
        
        return results
    
    def _create_folder_structure(self, suggestion: FolderSuggestion) -> bool:
        """Create the actual folder structure for a suggestion"""
        
        try:
            # Create local folder structure
            full_path = self.base_dir / suggestion.folder_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Optionally create corresponding custom category
            category_name = suggestion.folder_name.lower().replace(' ', '_')
            
            # Extract keywords from reasoning and supporting files
            keywords = []
            for reason in suggestion.reasoning:
                if 'pattern' in reason.lower():
                    # Extract pattern keywords
                    words = re.findall(r'\b\w+\b', reason.lower())
                    keywords.extend([w for w in words if len(w) > 3 and w not in ['pattern', 'found', 'files', 'would']])
            
            # Create custom category if we have good keywords
            if keywords:
                try:
                    self.category_manager.create_custom_category(
                        category_name=category_name,
                        display_name=suggestion.folder_name,
                        description=f"Auto-generated category based on discovered patterns",
                        keywords=list(set(keywords[:10])),  # Top 10 unique keywords
                        parent_category=None
                    )
                except Exception as e:
                    print(f"   ⚠️ Created folder but couldn't create custom category: {e}")
            
            return True
            
        except Exception as e:
            print(f"   💥 Error creating folder structure: {e}")
            return False
    
    def _save_implemented_suggestion(self, suggestion: FolderSuggestion, success: bool, error: str = None):
        """Save implementation results to database"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO folder_suggestions
                (folder_name, folder_path, confidence, reasoning, supporting_files,
                 pattern_evidence, urgency, adhd_priority, status, suggested_date, implementation_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                suggestion.folder_name,
                suggestion.folder_path,
                suggestion.confidence,
                json.dumps(suggestion.reasoning),
                json.dumps(suggestion.supporting_files),
                json.dumps(suggestion.pattern_evidence),
                suggestion.urgency,
                suggestion.adhd_priority,
                'auto_implemented' if success else 'failed',
                datetime.now().isoformat(),
                datetime.now().isoformat() if success else None
            ))
            
            if error:
                conn.execute("""
                    INSERT INTO auto_changes_log
                    (change_type, change_description, confidence, files_affected,
                     before_state, after_state, implemented_date, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'folder_creation',
                    f"Failed to create {suggestion.folder_name}: {error}",
                    suggestion.confidence,
                    len(suggestion.supporting_files),
                    json.dumps({'status': 'no_folder'}),
                    json.dumps({'status': 'error', 'error': error}),
                    datetime.now().isoformat(),
                    False
                ))
            
            conn.commit()
    
    def run_proactive_analysis(self, interactive: bool = True) -> Dict[str, Any]:
        """Run complete proactive learning analysis and implementation"""
        
        print("🤖 AI File Organizer - Proactive Learning Mode")
        print("=" * 60)
        
        # Analyze current state
        analysis = self.analyze_current_state()
        
        # Display insights
        if analysis['insights']:
            print(f"\n🧠 Discovered {len(analysis['insights'])} learning insights:")
            for i, insight in enumerate(analysis['insights'], 1):
                print(f"   [{i}] {insight.description} (confidence: {insight.confidence:.1%})")
        
        # Display folder suggestions
        if analysis['folder_suggestions']:
            print(f"\n📁 Generated {len(analysis['folder_suggestions'])} folder suggestions:")
            for i, suggestion in enumerate(analysis['folder_suggestions'], 1):
                print(f"   [{i}] {suggestion.folder_name} (priority: {suggestion.adhd_priority}/10, {suggestion.urgency} urgency)")
        
        # Implement suggestions
        implementation_results = {}
        if analysis['folder_suggestions']:
            if interactive:
                response = input(f"\n❓ Implement folder suggestions? [Y/n]: ").lower().strip()
                if response != 'n':
                    implementation_results = self.implement_suggestions(analysis['folder_suggestions'], interactive=True)
                else:
                    print("📝 Suggestions saved for later review")
            else:
                # Auto-implement high confidence suggestions
                high_confidence = [s for s in analysis['folder_suggestions'] 
                                 if s.confidence >= self.thresholds['confidence_threshold_for_auto_action']]
                if high_confidence:
                    implementation_results = self.implement_suggestions(high_confidence, interactive=False)
        
        # Handle auto-actions
        if analysis['auto_actions']:
            print(f"\n⚡ Found {len(analysis['auto_actions'])} auto-implementable improvements")
            # TODO: Implement auto-actions (rule updates, etc.)
        
        return {
            'analysis': analysis,
            'implementation_results': implementation_results,
            'timestamp': datetime.now().isoformat()
        }


def main():
    """Run proactive learning engine"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI File Organizer - Proactive Learning Engine')
    parser.add_argument('--analyze', action='store_true', help='Run analysis only')
    parser.add_argument('--implement', action='store_true', help='Run analysis and implement suggestions')
    parser.add_argument('--non-interactive', action='store_true', help='Run without user prompts')
    parser.add_argument('--base-dir', help='Base directory for AI organizer')
    
    args = parser.parse_args()
    
    # Initialize engine
    engine = ProactiveLearningEngine(args.base_dir)
    
    if args.analyze:
        # Analysis only
        analysis = engine.analyze_current_state()
        print(f"\n📊 Analysis complete with {len(analysis['insights'])} insights and {len(analysis['folder_suggestions'])} suggestions")
    else:
        # Full proactive run
        interactive = not args.non_interactive
        results = engine.run_proactive_analysis(interactive=interactive)
        
        print("\n🎉 Proactive learning session complete!")
        if results['implementation_results']:
            impl = results['implementation_results']
            print(f"📁 Created {len(impl['implemented'])} new folders")


if __name__ == "__main__":
    main()