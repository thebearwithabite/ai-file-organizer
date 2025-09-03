#!/usr/bin/env python3
"""
Video Project Trainer for AI File Organizer
Learns which projects your video generations belong to based on patterns and user corrections
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

@dataclass
class ProjectPattern:
    """Represents a learned pattern for project classification"""
    project_name: str
    pattern_type: str  # 'filename', 'visual_content', 'metadata', 'location'
    pattern_value: str
    confidence: float
    evidence_count: int
    last_seen: datetime
    created_from: str  # 'user_correction', 'batch_analysis', 'auto_discovery'

@dataclass
class VideoProjectAssociation:
    """Association between a video and its project"""
    file_path: str
    project_name: str
    confidence: float
    reasoning: List[str]
    evidence_sources: List[str]
    user_confirmed: bool
    created_at: datetime

class VideoProjectTrainer:
    """
    Learns to automatically classify video generations into the correct projects
    based on visual content, filenames, metadata, and user corrections
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        
        # Project learning directory
        self.project_dir = self.base_dir / "04_METADATA_SYSTEM" / "project_learning"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for project learning
        self.db_path = self.project_dir / "video_project_learning.db"
        self._init_database()
        
        # Your known projects (User's actual creative work)
        self.known_projects = {
            # Entertainment Industry Work
            'stranger_things': {
                'aliases': ['stranger things', 'st', 'hawkins', 'netflix', 'finn wolfhard'],
                'visual_indicators': ['sci-fi', 'supernatural', 'retro', '80s aesthetic', 'dark atmosphere', 'finn'],
                'description': 'Stranger Things / Netflix / Client Name Wolfhard management content'
            },
            'demo_reels': {
                'aliases': ['demo reel', 'reel', 'acting demo', 'showreel', 'audition', 'finn'],
                'visual_indicators': ['acting performance', 'multiple scenes', 'professional lighting', 'character work'],
                'description': 'Acting demo reels and audition materials'
            },
            
            # Your Creative Content Projects
            'multimedia_series': {
                'aliases': ['multimedia series', 'this isnt real', 'multimedia', 'series', 'episode', 'content series'],
                'visual_indicators': ['series production', 'episode format', 'consistent branding', 'multimedia content', 'creative narrative'],
                'description': 'This Isnt Real multimedia series content'
            },
            'thebearwithabite': {
                'aliases': ['thebearwithabite', 'bear with a bite', 'bear cap', 'social media', 'tiktok', 'instagram'],
                'visual_indicators': ['45 year old man', 'bear cap', 'bear hat', 'middle-aged man', 'social media format', 'vertical video', 'selfie style'],
                'description': 'thebearwithabite social media content (45yo guys in bear caps)'
            },
            'papers_that_dream': {
                'aliases': ['papers that dream', 'ptd', 'podcast', 'ai consciousness', 'consciousness', 'ai discussion'],
                'visual_indicators': ['podcast setup', 'microphone', 'recording setup', 'ai themes', 'technology discussion', 'interview format'],
                'description': 'Papers That Dream podcast and AI consciousness content'
            },
            
            # Technical/Development Projects
            'github_projects': {
                'aliases': ['github', 'coding', 'programming', 'development', 'code demo', 'tutorial', 'tech demo'],
                'visual_indicators': ['code editor', 'terminal', 'programming', 'screen recording', 'code demonstration', 'github interface'],
                'description': 'GitHub projects and code demonstrations'
            },
            'ai_file_organizer': {
                'aliases': ['ai file organizer', 'file organizer', 'claude code', 'organization system', 'ai organizer'],
                'visual_indicators': ['file management', 'organization demo', 'ai system', 'file browser', 'automation demo'],
                'description': 'AI File Organizer system demonstrations and tutorials'
            },
            
            # Behind-the-Scenes & Production
            'behind_scenes': {
                'aliases': ['behind scenes', 'bts', 'making of', 'set', 'production', 'creation process'],
                'visual_indicators': ['film set', 'camera equipment', 'crew', 'production environment', 'creative process'],
                'description': 'Behind-the-scenes and production content'
            },
            'creative_experiments': {
                'aliases': ['experiment', 'test', 'creative test', 'prototype', 'concept', 'idea'],
                'visual_indicators': ['experimental', 'testing', 'prototype', 'rough cut', 'work in progress', 'concept development'],
                'description': 'Creative experiments and concept development'
            },
            
            # Business/Professional
            'business_content': {
                'aliases': ['business', 'professional', 'meeting', 'presentation', 'corporate', 'work'],
                'visual_indicators': ['business meeting', 'presentation', 'professional setting', 'office environment', 'corporate'],
                'description': 'Business and professional content'
            }
        }
        
        # Learning thresholds
        self.confidence_thresholds = {
            'auto_classify': 0.8,
            'suggest': 0.6,
            'uncertain': 0.4
        }
    
    def _init_database(self):
        """Initialize project learning database"""
        with sqlite3.connect(self.db_path) as conn:
            # Project patterns table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT,
                    pattern_type TEXT,
                    pattern_value TEXT,
                    confidence REAL,
                    evidence_count INTEGER,
                    last_seen TEXT,
                    created_from TEXT,
                    UNIQUE(project_name, pattern_type, pattern_value)
                )
            """)
            
            # Video project associations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_project_associations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    project_name TEXT,
                    confidence REAL,
                    reasoning TEXT,  -- JSON array
                    evidence_sources TEXT,  -- JSON array
                    user_confirmed BOOLEAN,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # User corrections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    original_project TEXT,
                    corrected_project TEXT,
                    correction_reason TEXT,
                    correction_timestamp TEXT
                )
            """)
            
            conn.commit()
    
    def learn_from_vision_analysis(self, file_path: Path, vision_result, current_classification: str = None):
        """Learn project patterns from vision analysis results"""
        
        if not vision_result.success:
            return
        
        # Extract potential project indicators
        indicators = self._extract_project_indicators(file_path, vision_result)
        
        # Find best matching project
        project_scores = self._score_project_matches(indicators)
        
        if project_scores:
            best_project, confidence = max(project_scores.items(), key=lambda x: x[1])
            
            # Only learn if confidence is reasonable
            if confidence >= self.confidence_thresholds['uncertain']:
                self._record_project_association(file_path, best_project, confidence, indicators)
                
                # Update patterns based on this example
                self._update_patterns_from_example(file_path, best_project, vision_result)
    
    def _extract_project_indicators(self, file_path: Path, vision_result) -> Dict[str, List[str]]:
        """Extract project indicators from file and vision analysis"""
        
        indicators = {
            'filename': [],
            'visual_content': [],
            'subjects': vision_result.subjects,
            'context': [vision_result.context] if vision_result.context else [],
            'suggested_tags': vision_result.suggested_tags,
            'location': [str(file_path.parent)]
        }
        
        # Filename indicators
        filename_lower = file_path.name.lower()
        for project, project_info in self.known_projects.items():
            for alias in project_info['aliases']:
                if alias.lower() in filename_lower:
                    indicators['filename'].append(alias)
        
        # Visual content indicators
        description_lower = vision_result.description.lower()
        for project, project_info in self.known_projects.items():
            for visual_indicator in project_info['visual_indicators']:
                if visual_indicator.lower() in description_lower:
                    indicators['visual_content'].append(visual_indicator)
        
        return indicators
    
    def _score_project_matches(self, indicators: Dict[str, List[str]]) -> Dict[str, float]:
        """Score how well indicators match each known project"""
        
        project_scores = defaultdict(float)
        
        for project_name, project_info in self.known_projects.items():
            score = 0.0
            
            # Filename matches (high weight)
            for filename_indicator in indicators['filename']:
                for alias in project_info['aliases']:
                    if alias.lower() in filename_indicator.lower():
                        score += 0.4
            
            # Visual content matches (high weight)
            for visual_indicator in indicators['visual_content']:
                for expected_visual in project_info['visual_indicators']:
                    if expected_visual.lower() in visual_indicator.lower():
                        score += 0.3
            
            # Subject matches (medium weight)
            for subject in indicators['subjects']:
                for alias in project_info['aliases']:
                    if alias.lower() in subject.lower():
                        score += 0.2
            
            # Context matches (medium weight)
            for context in indicators['context']:
                for alias in project_info['aliases']:
                    if alias.lower() in context.lower():
                        score += 0.2
                for visual_indicator in project_info['visual_indicators']:
                    if visual_indicator.lower() in context.lower():
                        score += 0.15
            
            # Tag matches (lower weight)
            for tag in indicators['suggested_tags']:
                for alias in project_info['aliases']:
                    if alias.lower() in tag.lower():
                        score += 0.1
            
            if score > 0:
                project_scores[project_name] = min(score, 1.0)
        
        return dict(project_scores)
    
    def _record_project_association(self, file_path: Path, project_name: str, confidence: float, indicators: Dict):
        """Record a video-project association"""
        
        reasoning = []
        evidence_sources = []
        
        # Build reasoning
        if indicators['filename']:
            reasoning.append(f"Filename contains: {', '.join(indicators['filename'])}")
            evidence_sources.append('filename')
        
        if indicators['visual_content']:
            reasoning.append(f"Visual content matches: {', '.join(indicators['visual_content'])}")
            evidence_sources.append('visual_analysis')
        
        if indicators['subjects']:
            reasoning.append(f"Detected subjects: {', '.join(indicators['subjects'][:3])}")
            evidence_sources.append('subject_detection')
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO video_project_associations
                (file_path, project_name, confidence, reasoning, evidence_sources, user_confirmed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(file_path), project_name, confidence,
                json.dumps(reasoning), json.dumps(evidence_sources),
                False, datetime.now().isoformat(), datetime.now().isoformat()
            ))
            conn.commit()
    
    def _update_patterns_from_example(self, file_path: Path, project_name: str, vision_result):
        """Update learned patterns based on a good example"""
        
        # Learn filename patterns
        filename_words = file_path.stem.lower().replace('_', ' ').replace('-', ' ').split()
        for word in filename_words:
            if len(word) > 3:  # Skip short words
                self._update_pattern(project_name, 'filename_word', word, 0.1, 'vision_analysis')
        
        # Learn visual content patterns
        if vision_result.content_type:
            self._update_pattern(project_name, 'content_type', vision_result.content_type, 0.2, 'vision_analysis')
        
        # Learn subject patterns
        for subject in vision_result.subjects[:3]:  # Top 3 subjects
            self._update_pattern(project_name, 'subject', subject.lower(), 0.15, 'vision_analysis')
        
        # Learn tag patterns
        for tag in vision_result.suggested_tags[:5]:  # Top 5 tags
            self._update_pattern(project_name, 'tag', tag.lower(), 0.1, 'vision_analysis')
    
    def _update_pattern(self, project_name: str, pattern_type: str, pattern_value: str, confidence: float, source: str):
        """Update a learned pattern"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if pattern exists
            cursor = conn.execute("""
                SELECT evidence_count, confidence FROM project_patterns
                WHERE project_name = ? AND pattern_type = ? AND pattern_value = ?
            """, (project_name, pattern_type, pattern_value))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                old_count, old_confidence = existing
                new_count = old_count + 1
                new_confidence = (old_confidence + confidence) / 2  # Average
                
                conn.execute("""
                    UPDATE project_patterns
                    SET evidence_count = ?, confidence = ?, last_seen = ?
                    WHERE project_name = ? AND pattern_type = ? AND pattern_value = ?
                """, (new_count, new_confidence, datetime.now().isoformat(),
                     project_name, pattern_type, pattern_value))
            else:
                # Create new pattern
                conn.execute("""
                    INSERT INTO project_patterns
                    (project_name, pattern_type, pattern_value, confidence, evidence_count, last_seen, created_from)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (project_name, pattern_type, pattern_value, confidence, 1,
                     datetime.now().isoformat(), source))
            
            conn.commit()
    
    def classify_video_project(self, file_path: Path, vision_result=None) -> Optional[VideoProjectAssociation]:
        """Classify which project a video belongs to"""
        
        # First check if we already have an association
        existing = self._get_existing_association(file_path)
        if existing and existing.user_confirmed:
            return existing
        
        # Use vision analysis if available
        if vision_result:
            indicators = self._extract_project_indicators(file_path, vision_result)
        else:
            # Use filename and location only
            indicators = {
                'filename': [],
                'visual_content': [],
                'subjects': [],
                'context': [],
                'suggested_tags': [],
                'location': [str(file_path.parent)]
            }
            
            # Extract from filename
            filename_lower = file_path.name.lower()
            for project, project_info in self.known_projects.items():
                for alias in project_info['aliases']:
                    if alias.lower() in filename_lower:
                        indicators['filename'].append(alias)
        
        # Score projects
        project_scores = self._score_project_matches(indicators)
        
        # Also check learned patterns
        learned_scores = self._score_against_learned_patterns(file_path, indicators)
        
        # Combine scores
        combined_scores = defaultdict(float)
        for project, score in project_scores.items():
            combined_scores[project] += score * 0.7  # Known patterns weight
        for project, score in learned_scores.items():
            combined_scores[project] += score * 0.3  # Learned patterns weight
        
        if not combined_scores:
            return None
        
        # Get best match
        best_project, confidence = max(combined_scores.items(), key=lambda x: x[1])
        
        if confidence < self.confidence_thresholds['uncertain']:
            return None
        
        # Build reasoning
        reasoning = []
        evidence_sources = []
        
        if indicators['filename']:
            reasoning.append(f"Filename indicators: {', '.join(indicators['filename'])}")
            evidence_sources.append('filename')
        
        if indicators['visual_content']:
            reasoning.append(f"Visual content: {', '.join(indicators['visual_content'])}")
            evidence_sources.append('vision')
        
        if learned_scores.get(best_project, 0) > 0:
            reasoning.append("Matches learned patterns from previous examples")
            evidence_sources.append('learned_patterns')
        
        return VideoProjectAssociation(
            file_path=str(file_path),
            project_name=best_project,
            confidence=confidence,
            reasoning=reasoning,
            evidence_sources=evidence_sources,
            user_confirmed=False,
            created_at=datetime.now()
        )
    
    def _get_existing_association(self, file_path: Path) -> Optional[VideoProjectAssociation]:
        """Get existing project association for file"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT project_name, confidence, reasoning, evidence_sources, user_confirmed, created_at
                FROM video_project_associations
                WHERE file_path = ?
            """, (str(file_path),))
            
            row = cursor.fetchone()
            if row:
                return VideoProjectAssociation(
                    file_path=str(file_path),
                    project_name=row[0],
                    confidence=row[1],
                    reasoning=json.loads(row[2]),
                    evidence_sources=json.loads(row[3]),
                    user_confirmed=bool(row[4]),
                    created_at=datetime.fromisoformat(row[5])
                )
        
        return None
    
    def _score_against_learned_patterns(self, file_path: Path, indicators: Dict) -> Dict[str, float]:
        """Score against previously learned patterns"""
        
        project_scores = defaultdict(float)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT project_name, pattern_type, pattern_value, confidence, evidence_count
                FROM project_patterns
                WHERE evidence_count >= 2  -- Only use patterns with multiple evidence
                ORDER BY evidence_count DESC
            """)
            
            for project_name, pattern_type, pattern_value, confidence, evidence_count in cursor.fetchall():
                # Check if this file matches the pattern
                matches = False
                
                if pattern_type == 'filename_word':
                    matches = pattern_value in file_path.name.lower()
                elif pattern_type == 'content_type' and 'visual_content' in indicators:
                    matches = pattern_value in ' '.join(indicators['visual_content']).lower()
                elif pattern_type == 'subject' and indicators['subjects']:
                    matches = any(pattern_value in subject.lower() for subject in indicators['subjects'])
                elif pattern_type == 'tag' and indicators['suggested_tags']:
                    matches = any(pattern_value in tag.lower() for tag in indicators['suggested_tags'])
                
                if matches:
                    # Weight by evidence count and confidence
                    weight = confidence * min(evidence_count / 5, 1.0)
                    project_scores[project_name] += weight * 0.2
        
        return dict(project_scores)
    
    def learn_from_user_correction(self, file_path: Path, original_project: str, corrected_project: str, reason: str = ""):
        """Learn from user correction"""
        
        # Record the correction
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO user_corrections
                (file_path, original_project, corrected_project, correction_reason, correction_timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (str(file_path), original_project, corrected_project, reason, datetime.now().isoformat()))
            
            # Update the association
            conn.execute("""
                INSERT OR REPLACE INTO video_project_associations
                (file_path, project_name, confidence, reasoning, evidence_sources, user_confirmed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 
                        COALESCE((SELECT created_at FROM video_project_associations WHERE file_path = ?), ?), ?)
            """, (
                str(file_path), corrected_project, 1.0,
                json.dumps([f"User correction: {reason}" if reason else "User confirmed"]),
                json.dumps(['user_correction']), True,
                str(file_path), datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
        
        # Learn new patterns from this correction if we have vision data
        print(f"✅ Learned from correction: {file_path.name} → {corrected_project}")
    
    def get_project_suggestions_for_video(self, file_path: Path, vision_result=None) -> List[Tuple[str, float, List[str]]]:
        """Get project suggestions for a video with confidence and reasoning"""
        
        association = self.classify_video_project(file_path, vision_result)
        
        if not association:
            return []
        
        # Get top suggestions (you could extend this to return multiple options)
        suggestions = [(association.project_name, association.confidence, association.reasoning)]
        
        # Add other reasonable matches
        if vision_result:
            indicators = self._extract_project_indicators(file_path, vision_result)
            all_scores = self._score_project_matches(indicators)
            
            for project, score in sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[1:3]:
                if score >= self.confidence_thresholds['uncertain']:
                    suggestions.append((project, score, [f"Alternative match based on {project} indicators"]))
        
        return suggestions


def test_video_project_trainer():
    """Test the video project trainer"""
    
    print("🎬 Testing Video Project Trainer")
    print("=" * 40)
    
    trainer = VideoProjectTrainer()
    
    # Find test video files
    test_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Desktop"
    ]
    
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
    test_videos = []
    
    for test_dir in test_dirs:
        if test_dir.exists():
            for ext in video_extensions:
                videos = list(test_dir.glob(f"*{ext}"))
                test_videos.extend(videos[:2])  # Max 2 videos per extension
                if len(test_videos) >= 3:
                    break
        if len(test_videos) >= 3:
            break
    
    if not test_videos:
        print("📝 No video files found for testing")
        return
    
    print(f"🎬 Testing with {len(test_videos)} videos:")
    
    for i, video_path in enumerate(test_videos, 1):
        print(f"\n[{i}] {video_path.name}")
        
        # Test classification
        association = trainer.classify_video_project(video_path)
        
        if association:
            print(f"    📂 Project: {association.project_name}")
            print(f"    🎯 Confidence: {association.confidence:.1%}")
            print(f"    💭 Reasoning: {association.reasoning[0] if association.reasoning else 'No specific reasoning'}")
        else:
            print(f"    ❓ No project match found")
        
        # Test suggestions
        suggestions = trainer.get_project_suggestions_for_video(video_path)
        if suggestions:
            print(f"    💡 Suggestions:")
            for proj, conf, reasons in suggestions:
                print(f"       • {proj} ({conf:.1%})")


if __name__ == '__main__':
    test_video_project_trainer()