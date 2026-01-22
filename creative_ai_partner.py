#!/usr/bin/env python3
"""
Creative AI Partner System for AI File Organizer
Character recognition, story analysis, and creative continuity tracking
Designed for entertainment industry professionals working with scripts and creative content
"""

import sys
import os
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
import hashlib

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from content_extractor import ContentExtractor

@dataclass
class Character:
    """Represents a character from creative content"""
    name: str
    aliases: List[str]
    first_appearance: str  # File where first mentioned
    description: str
    personality_traits: List[str]
    relationships: Dict[str, str]  # character_name -> relationship_type
    story_arcs: List[str]
    mentioned_in_files: List[str]
    character_type: str  # protagonist, antagonist, supporting, etc.
    
@dataclass
class StoryElement:
    """Represents a story element (theme, plot point, location, etc.)"""
    element_id: str
    element_type: str  # theme, location, plot_point, conflict, etc.
    name: str
    description: str
    first_mentioned: str
    recurring: bool
    related_characters: List[str]
    mentioned_in_files: List[str]
    importance_score: float

@dataclass
class CreativeProject:
    """Represents a creative project with all its elements"""
    project_name: str
    project_type: str  # script, novel, treatment, etc.
    genre: str
    characters: List[Character]
    story_elements: List[StoryElement]
    themes: List[str]
    timeline: List[Dict]  # chronological events
    file_versions: List[str]
    last_analyzed: datetime

@dataclass
class StoryAnalysis:
    """Analysis results for a creative document"""
    file_path: Path
    project_identified: Optional[str]
    characters_found: List[str]
    new_characters: List[str]
    story_elements: List[str]
    themes_detected: List[str]
    continuity_issues: List[str]
    character_development: Dict[str, str]
    plot_progression: str
    analysis_confidence: float

class CreativeAIPartner:
    """
    AI Partner for creative professionals working with scripts, treatments, and stories
    Tracks characters, story continuity, and creative development across projects
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.creative_dir = self.base_dir / "04_METADATA_SYSTEM" / "creative_ai_partner"
        self.creative_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize content extractor
        self.content_extractor = ContentExtractor(str(self.base_dir))
        
        # Database for creative content analysis
        self.db_path = self.creative_dir / "creative_analysis.db"
        self._init_creative_db()
        
        # Character recognition patterns (more selective)
        self.character_patterns = {
            # Script format character names (usually ALL CAPS)
            'script_characters': [
                r'^([A-Z][A-Z\s]{2,20}):',   # CHARACTER: dialogue format only
                r'\n([A-Z][A-Z\s]{3,15})\n\s*[\(\[]',  # Character name before stage direction
            ],
            
            # Narrative character mentions (very selective)
            'narrative_characters': [
                r'\b([A-Z][a-z]{3,12})\s+said\b',  # "Character said"
                r'\b([A-Z][a-z]{3,12})\s+replied\b',  # "Character replied" 
                r'\b([A-Z][a-z]{3,12})\s+whispered\b',  # "Character whispered"
                r'\b([A-Z][a-z]{3,12})\s+shouted\b',  # "Character shouted"
                r'\b([A-Z][a-z]{3,12})\s+laughed\b',  # "Character laughed"
                r'"[^"]*,"\s+([A-Z][a-z]{3,12})\s+said',  # "dialogue," Character said
            ],
            
            # Known character names from your projects (high confidence)
            'known_characters': [
                r'\b(Eleven|Mike|Will|Dustin|Lucas|Max|Nancy|Steve|Jonathan|Hopper|Joyce)\b',  # Stranger Things
                r'\b(Alex|Maya|Torres|Chen|User|Client|Client Name)\b',  # Your creative characters  
                r'\b(The Protagonist|The Antagonist|The Mentor|The Hero|The Villain)\b',  # Archetypal references
            ]
        }
        
        # Story element patterns
        self.story_patterns = {
            'locations': [
                r'\b(INT\.|EXT\.)\s+([A-Z\s-]+)\s*-',  # Script locations
                r'\bthe ([a-z]+(?:\s+[a-z]+)*)\s+where\b',  # "the place where"
                r'\bin ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # "in LocationName"
                r'\bat ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # "at LocationName"
            ],
            
            'themes': [
                r'\b(love|betrayal|revenge|redemption|sacrifice|loyalty|friendship|family)\b',
                r'\b(coming.of.age|good.vs.evil|man.vs.nature|identity|power|corruption)\b',
                r'\b(consciousness|artificial intelligence|humanity|technology|progress)\b',
            ],
            
            'plot_devices': [
                r'\b(flashback|montage|voice.over|dream sequence|plot twist)\b',
                r'\b(cliffhanger|red herring|macguffin|deus ex machina)\b',
                r'\b(exposition|rising action|climax|falling action|resolution)\b',
            ],
            
            'emotional_beats': [
                r'\b(dramatic|emotional|tense|suspenseful|romantic|comedic|tragic)\b',
                r'\b(heartbreaking|inspiring|shocking|surprising|touching|powerful)\b',
                r'\b(intense|intimate|explosive|quiet|subtle|raw|vulnerable)\b',
            ]
        }
        
        # Project identification patterns
        self.project_patterns = {
            'stranger_things': [
                r'\bstranger\s+things\b',
                r'\bhawkins\b',
                r'\bupside.down\b',
                r'\bmind.flayer\b',
                r'\bdemogorgon\b'
            ],
            'creative_project_podcast': [
                r'\bcreative\s+project\b',
                r'\bpodcast\b',
                r'\bconsciousness\b',
                r'\bartificial\s+intelligence\b',
                r'\bai\s+consciousness\b'
            ],
            'papers_that_dream': [
                r'\bpapers\s+that\s+dream\b',
                r'\bscreenplay\b',
                r'\bfeature\s+film\b',
                r'\bmovie\s+script\b'
            ]
        }
        
        # Character relationship indicators
        self.relationship_patterns = {
            'romantic': [r'\bloves?\b', r'\bromance\b', r'\bkiss\b', r'\bdate\b', r'\bmarry\b'],
            'family': [r'\bfather\b', r'\bmother\b', r'\bbrother\b', r'\bsister\b', r'\bson\b', r'\bdaughter\b'],
            'friendship': [r'\bfriend\b', r'\bbuddy\b', r'\bpal\b', r'\bcompanion\b'],
            'conflict': [r'\benemy\b', r'\brival\b', r'\bopponent\b', r'\bfight\b', r'\bconflict\b'],
            'professional': [r'\bboss\b', r'\bcoworker\b', r'\bclient\b', r'\bmanager\b', r'\bcolleague\b']
        }
    
    def _init_creative_db(self):
        """Initialize SQLite database for creative content analysis"""
        with sqlite3.connect(self.db_path) as conn:
            # Characters table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    aliases TEXT,  -- JSON array
                    first_appearance TEXT,
                    description TEXT,
                    personality_traits TEXT,  -- JSON array
                    relationships TEXT,  -- JSON object
                    story_arcs TEXT,  -- JSON array
                    mentioned_in_files TEXT,  -- JSON array
                    character_type TEXT,
                    created_date TEXT,
                    last_updated TEXT
                )
            """)
            
            # Story elements table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS story_elements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    element_id TEXT UNIQUE,
                    element_type TEXT,
                    name TEXT,
                    description TEXT,
                    first_mentioned TEXT,
                    recurring BOOLEAN,
                    related_characters TEXT,  -- JSON array
                    mentioned_in_files TEXT,  -- JSON array
                    importance_score REAL,
                    created_date TEXT,
                    last_updated TEXT
                )
            """)
            
            # Creative projects table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS creative_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT UNIQUE,
                    project_type TEXT,
                    genre TEXT,
                    characters TEXT,  -- JSON array of character names
                    story_elements TEXT,  -- JSON array of element IDs
                    themes TEXT,  -- JSON array
                    timeline TEXT,  -- JSON array of events
                    file_versions TEXT,  -- JSON array of file paths
                    created_date TEXT,
                    last_analyzed TEXT
                )
            """)
            
            # File analysis results table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_name TEXT,
                    file_hash TEXT,
                    project_identified TEXT,
                    characters_found TEXT,  -- JSON array
                    new_characters TEXT,  -- JSON array
                    story_elements TEXT,  -- JSON array
                    themes_detected TEXT,  -- JSON array
                    continuity_issues TEXT,  -- JSON array
                    character_development TEXT,  -- JSON object
                    plot_progression TEXT,
                    analysis_confidence REAL,
                    analyzed_date TEXT
                )
            """)
            
            conn.commit()
    
    def analyze_creative_content(self, file_path: Path) -> StoryAnalysis:
        """Analyze a creative document for characters, story elements, and continuity"""
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Extract content
        content_result = self.content_extractor.extract_content(file_path)
        content = content_result.get('text', '') if content_result.get('success') else ''
        
        if not content:
            raise ValueError(f"Could not extract content from {file_path}")
        
        print(f"🎭 Analyzing creative content: {file_path.name}")
        
        # Initialize analysis
        analysis = StoryAnalysis(
            file_path=file_path,
            project_identified=None,
            characters_found=[],
            new_characters=[],
            story_elements=[],
            themes_detected=[],
            continuity_issues=[],
            character_development={},
            plot_progression="",
            analysis_confidence=0.0
        )
        
        # Identify project
        analysis.project_identified = self._identify_project(content, file_path)
        
        # Extract characters
        characters_found = self._extract_characters(content)
        analysis.characters_found = list(characters_found.keys())
        
        # Check for new characters
        existing_characters = self._get_existing_characters()
        analysis.new_characters = [char for char in analysis.characters_found 
                                 if char.lower() not in [c.lower() for c in existing_characters]]
        
        # Extract story elements
        analysis.story_elements = self._extract_story_elements(content)
        
        # Detect themes
        analysis.themes_detected = self._detect_themes(content)
        
        # Analyze character development
        analysis.character_development = self._analyze_character_development(content, characters_found)
        
        # Assess plot progression
        analysis.plot_progression = self._assess_plot_progression(content)
        
        # Check continuity (compare with existing project data)
        if analysis.project_identified:
            analysis.continuity_issues = self._check_continuity(content, analysis.project_identified)
        
        # Calculate confidence
        analysis.analysis_confidence = self._calculate_analysis_confidence(analysis)
        
        return analysis
    
    def _identify_project(self, content: str, file_path: Path) -> Optional[str]:
        """Identify which creative project this content belongs to"""
        
        content_lower = content.lower()
        filename_lower = file_path.name.lower()
        
        project_scores = {}
        
        # Check against project patterns
        for project_name, patterns in self.project_patterns.items():
            score = 0
            
            # Content analysis
            for pattern in patterns:
                content_matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
                score += content_matches * 2
            
            # Filename analysis
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    score += 3
            
            if score > 0:
                project_scores[project_name] = score
        
        # Return project with highest score if above threshold
        if project_scores:
            best_project = max(project_scores, key=project_scores.get)
            if project_scores[best_project] >= 3:  # Minimum confidence threshold
                return best_project
        
        return None
    
    def _extract_characters(self, content: str) -> Dict[str, Dict]:
        """Extract character names and basic information from content"""
        
        characters = {}
        lines = content.split('\n')
        
        # Check each pattern category
        for category, patterns in self.character_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                
                for match in matches:
                    if isinstance(match, tuple):
                        # Handle patterns with multiple groups
                        character_name = ' '.join(match).strip()
                    else:
                        character_name = match.strip()
                    
                    # Clean up the character name
                    character_name = re.sub(r'[^\w\s]', '', character_name)
                    character_name = ' '.join(character_name.split())
                    
                    # Skip if too short, too long, or common words
                    if (len(character_name) < 3 or 
                        len(character_name) > 25 or
                        character_name.lower() in ['said', 'replied', 'thought', 'the', 'and', 'int', 'ext', 'this', 'that', 'with', 'from']):
                        continue
                    
                    # Skip if it's all uppercase and likely a direction (like "FADE IN")
                    if character_name.isupper() and len(character_name.split()) > 2:
                        continue
                    
                    # Skip common technical/business terms that aren't characters
                    non_character_terms = [
                        'accuracy', 'targets', 'tests', 'audio', 'files', 'project', 'system', 
                        'organization', 'documents', 'folder', 'storage', 'components', 
                        'testing', 'protocol', 'philosophy', 'core', 'based', 'analysis',
                        'metadata', 'content', 'search', 'database', 'vector', 'processing',
                        'classification', 'confidence', 'extraction', 'generation'
                    ]
                    
                    if any(term in character_name.lower() for term in non_character_terms):
                        continue
                    
                    if character_name not in characters:
                        characters[character_name] = {
                            'detection_method': category,
                            'mentions': 1,
                            'context_lines': []
                        }
                    else:
                        characters[character_name]['mentions'] += 1
                    
                    # Add context for the character
                    for i, line in enumerate(lines):
                        if character_name in line:
                            start_idx = max(0, i-1)
                            end_idx = min(len(lines), i+2)
                            context = ' '.join(lines[start_idx:end_idx]).strip()
                            if context and len(context) < 200:
                                characters[character_name]['context_lines'].append(context)
        
        # Filter out characters with very low mentions unless they're known characters
        filtered_characters = {}
        for char_name, char_info in characters.items():
            if char_info['mentions'] >= 2 or char_info['detection_method'] == 'known_characters':
                filtered_characters[char_name] = char_info
        
        return filtered_characters
    
    def _extract_story_elements(self, content: str) -> List[str]:
        """Extract story elements like locations, themes, plot devices"""
        
        elements = []
        content_lower = content.lower()
        
        for element_type, patterns in self.story_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                
                for match in matches:
                    if isinstance(match, tuple):
                        element = ' '.join(match).strip()
                    else:
                        element = match.strip()
                    
                    # Clean up element
                    element = re.sub(r'[^\w\s-]', '', element)
                    element = ' '.join(element.split())
                    
                    if len(element) > 2 and element not in elements:
                        elements.append(f"{element_type}:{element}")
        
        return elements
    
    def _detect_themes(self, content: str) -> List[str]:
        """Detect thematic elements in the content"""
        
        themes = []
        content_lower = content.lower()
        
        # Check for explicit theme mentions
        theme_patterns = self.story_patterns.get('themes', [])
        
        for pattern in theme_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            themes.extend(matches)
        
        # Analyze content for implicit themes
        if 'family' in content_lower and 'loss' in content_lower:
            themes.append('family_loss')
        
        if 'power' in content_lower and 'corrupt' in content_lower:
            themes.append('corruption_of_power')
        
        if 'artificial' in content_lower and 'human' in content_lower:
            themes.append('ai_vs_humanity')
        
        if 'memory' in content_lower and 'past' in content_lower:
            themes.append('memory_and_identity')
        
        return list(set(themes))  # Remove duplicates
    
    def _analyze_character_development(self, content: str, characters: Dict) -> Dict[str, str]:
        """Analyze character development and arcs"""
        
        development = {}
        
        for character_name in characters.keys():
            # Look for character development indicators near character mentions
            char_pattern = re.escape(character_name)
            
            # Find sentences containing the character
            sentences = re.split(r'[.!?]+', content)
            char_sentences = [s for s in sentences if re.search(char_pattern, s, re.IGNORECASE)]
            
            if char_sentences:
                # Analyze emotional journey
                emotional_words = {
                    'growth': ['learns', 'realizes', 'discovers', 'grows', 'changes', 'becomes'],
                    'conflict': ['struggles', 'fights', 'opposes', 'conflicts', 'battles'],
                    'triumph': ['wins', 'succeeds', 'achieves', 'conquers', 'overcomes'],
                    'loss': ['loses', 'fails', 'grieves', 'mourns', 'suffers']
                }
                
                char_emotions = []
                for sentence in char_sentences:
                    sentence_lower = sentence.lower()
                    for emotion, words in emotional_words.items():
                        if any(word in sentence_lower for word in words):
                            char_emotions.append(emotion)
                
                if char_emotions:
                    development[character_name] = ' -> '.join(char_emotions)
                else:
                    development[character_name] = 'static_character'
        
        return development
    
    def _assess_plot_progression(self, content: str) -> str:
        """Assess plot structure and progression"""
        
        content_lower = content.lower()
        
        # Look for structural indicators
        structure_indicators = {
            'setup': ['introduces', 'establishes', 'begins', 'opens', 'starts'],
            'inciting_incident': ['when', 'suddenly', 'then', 'until', 'but'],
            'rising_action': ['conflict', 'tension', 'builds', 'escalates', 'develops'],
            'climax': ['confrontation', 'peak', 'crucial', 'decisive', 'critical'],
            'resolution': ['resolves', 'concludes', 'ends', 'finally', 'ultimately']
        }
        
        plot_elements = []
        
        for element, indicators in structure_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                plot_elements.append(element)
        
        if len(plot_elements) >= 3:
            return f"structured_narrative: {' -> '.join(plot_elements)}"
        elif len(plot_elements) >= 1:
            return f"partial_structure: {', '.join(plot_elements)}"
        else:
            return "unstructured_or_fragment"
    
    def _check_continuity(self, content: str, project_name: str) -> List[str]:
        """Check for continuity issues within a project"""
        
        issues = []
        
        # Get existing project data
        existing_project = self._get_project_data(project_name)
        if not existing_project:
            return issues
        
        # Check character consistency
        existing_characters = existing_project.get('characters', [])
        content_characters = self._extract_characters(content)
        
        for char_name in content_characters.keys():
            # Check for similar character names (possible typos)
            for existing_char in existing_characters:
                similarity = self._calculate_name_similarity(char_name, existing_char)
                if 0.7 < similarity < 1.0:  # Similar but not identical
                    issues.append(f"possible_character_name_inconsistency: '{char_name}' vs '{existing_char}'")
        
        # Check theme consistency
        existing_themes = existing_project.get('themes', [])
        content_themes = self._detect_themes(content)
        
        # Flag if introducing completely new themes
        new_themes = [theme for theme in content_themes if theme not in existing_themes]
        if new_themes and len(existing_themes) > 0:
            issues.append(f"new_themes_introduced: {', '.join(new_themes)}")
        
        return issues
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two character names"""
        
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Simple similarity based on common characters
        if name1_lower == name2_lower:
            return 1.0
        
        # Check for substring matches
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return 0.8
        
        # Count common characters
        common_chars = len(set(name1_lower) & set(name2_lower))
        total_chars = len(set(name1_lower) | set(name2_lower))
        
        return common_chars / total_chars if total_chars > 0 else 0.0
    
    def _calculate_analysis_confidence(self, analysis: StoryAnalysis) -> float:
        """Calculate confidence score for the analysis"""
        
        confidence = 0.0
        
        # Project identification confidence
        if analysis.project_identified:
            confidence += 0.3
        
        # Character detection confidence
        if analysis.characters_found:
            confidence += min(len(analysis.characters_found) * 0.1, 0.3)
        
        # Story elements confidence
        if analysis.story_elements:
            confidence += min(len(analysis.story_elements) * 0.05, 0.2)
        
        # Theme detection confidence
        if analysis.themes_detected:
            confidence += min(len(analysis.themes_detected) * 0.05, 0.1)
        
        # Plot progression confidence
        if 'structured' in analysis.plot_progression:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _get_existing_characters(self) -> List[str]:
        """Get list of existing characters from database"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM characters")
            return [row[0] for row in cursor.fetchall()]
    
    def _get_project_data(self, project_name: str) -> Optional[Dict]:
        """Get existing project data from database"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT project_type, genre, characters, themes, timeline
                FROM creative_projects 
                WHERE project_name = ?
            """, (project_name,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'project_type': row[0],
                    'genre': row[1],
                    'characters': json.loads(row[2]) if row[2] else [],
                    'themes': json.loads(row[3]) if row[3] else [],
                    'timeline': json.loads(row[4]) if row[4] else []
                }
        
        return None
    
    def save_analysis(self, analysis: StoryAnalysis) -> bool:
        """Save creative analysis results to database"""
        
        try:
            file_hash = self._calculate_file_hash(analysis.file_path)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO file_analysis
                    (file_path, file_name, file_hash, project_identified, characters_found,
                     new_characters, story_elements, themes_detected, continuity_issues,
                     character_development, plot_progression, analysis_confidence, analyzed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(analysis.file_path),
                    analysis.file_path.name,
                    file_hash,
                    analysis.project_identified,
                    json.dumps(analysis.characters_found),
                    json.dumps(analysis.new_characters),
                    json.dumps(analysis.story_elements),
                    json.dumps(analysis.themes_detected),
                    json.dumps(analysis.continuity_issues),
                    json.dumps(analysis.character_development),
                    analysis.plot_progression,
                    analysis.analysis_confidence,
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Update character and project databases
            self._update_character_database(analysis)
            self._update_project_database(analysis)
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving creative analysis: {e}")
            return False
    
    def _update_character_database(self, analysis: StoryAnalysis):
        """Update character database with new information"""
        
        for character_name in analysis.characters_found:
            with sqlite3.connect(self.db_path) as conn:
                # Check if character exists
                cursor = conn.execute("SELECT name FROM characters WHERE name = ?", (character_name,))
                
                if cursor.fetchone():
                    # Update existing character
                    conn.execute("""
                        UPDATE characters 
                        SET mentioned_in_files = json_insert(
                            COALESCE(mentioned_in_files, '[]'), '$[#]', ?
                        ),
                        last_updated = ?
                        WHERE name = ?
                    """, (str(analysis.file_path), datetime.now().isoformat(), character_name))
                else:
                    # Create new character
                    conn.execute("""
                        INSERT INTO characters
                        (name, first_appearance, mentioned_in_files, created_date, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        character_name,
                        str(analysis.file_path),
                        json.dumps([str(analysis.file_path)]),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
    
    def _update_project_database(self, analysis: StoryAnalysis):
        """Update project database with new information"""
        
        if not analysis.project_identified:
            return
        
        project_name = analysis.project_identified
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if project exists
            cursor = conn.execute("SELECT project_name FROM creative_projects WHERE project_name = ?", (project_name,))
            
            if cursor.fetchone():
                # Update existing project
                conn.execute("""
                    UPDATE creative_projects 
                    SET file_versions = json_insert(
                        COALESCE(file_versions, '[]'), '$[#]', ?
                    ),
                    last_analyzed = ?
                    WHERE project_name = ?
                """, (str(analysis.file_path), datetime.now().isoformat(), project_name))
            else:
                # Create new project
                conn.execute("""
                    INSERT INTO creative_projects
                    (project_name, project_type, characters, themes, file_versions, 
                     created_date, last_analyzed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_name,
                    'script' if 'script' in str(analysis.file_path).lower() else 'creative_writing',
                    json.dumps(analysis.characters_found),
                    json.dumps(analysis.themes_detected),
                    json.dumps([str(analysis.file_path)]),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash for change detection"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return ""
    
    def get_project_overview(self, project_name: str) -> Optional[Dict]:
        """Get comprehensive overview of a creative project"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Get project data
            cursor = conn.execute("""
                SELECT * FROM creative_projects WHERE project_name = ?
            """, (project_name,))
            
            project_row = cursor.fetchone()
            if not project_row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            project_data = dict(zip(columns, project_row))
            
            # Get associated characters
            characters = []
            character_names = json.loads(project_data.get('characters', '[]'))
            
            for char_name in character_names:
                char_cursor = conn.execute("""
                    SELECT * FROM characters WHERE name = ?
                """, (char_name,))
                
                char_row = char_cursor.fetchone()
                if char_row:
                    char_columns = [desc[0] for desc in char_cursor.description]
                    char_data = dict(zip(char_columns, char_row))
                    characters.append(char_data)
            
            # Get file analyses
            analysis_cursor = conn.execute("""
                SELECT * FROM file_analysis WHERE project_identified = ?
                ORDER BY analyzed_date DESC
            """, (project_name,))
            
            analysis_columns = [desc[0] for desc in analysis_cursor.description]
            analyses = []
            
            for analysis_row in analysis_cursor.fetchall():
                analysis_data = dict(zip(analysis_columns, analysis_row))
                analyses.append(analysis_data)
            
            return {
                'project_info': project_data,
                'characters': characters,
                'file_analyses': analyses,
                'total_files': len(analyses),
                'total_characters': len(characters)
            }
    
    def find_character_appearances(self, character_name: str) -> List[Dict]:
        """Find all files where a character appears"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path, file_name, characters_found, analyzed_date, project_identified
                FROM file_analysis
                WHERE json_extract(characters_found, '$') LIKE ?
                ORDER BY analyzed_date DESC
            """, (f'%{character_name}%',))
            
            columns = [desc[0] for desc in cursor.description]
            appearances = []
            
            for row in cursor.fetchall():
                appearance = dict(zip(columns, row))
                # Parse characters_found to check exact match
                characters = json.loads(appearance['characters_found'])
                if character_name in characters:
                    appearances.append(appearance)
            
            return appearances
    
    def _get_db_connection(self):
        """Get database connection for CLI usage"""
        import sqlite3
        return sqlite3.connect(self.db_path)

def test_creative_ai_partner():
    """Test the creative AI partner system"""
    
    print("🎭 Testing Creative AI Partner System")
    print("=" * 60)
    
    partner = CreativeAIPartner()
    
    # Find test files (look for creative content)
    test_dirs = [
        Path("/Users/user/Github/ai-file-organizer"),
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Documents"
    ]
    
    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            # Look for creative content files
            creative_files = []
            for pattern in ['*.md', '*.txt', '*.pdf', '*.docx']:
                creative_files.extend(test_dir.glob(pattern))
            
            # Filter for likely creative content
            for file in creative_files:
                filename_lower = file.name.lower()
                if any(keyword in filename_lower for keyword in 
                      ['script', 'story', 'character', 'treatment', 'creative', 'draft']):
                    test_files.append(file)
                    if len(test_files) >= 2:
                        break
            
            # Also add any .md files as they might contain creative content
            if len(test_files) < 2:
                md_files = [f for f in test_dir.glob("*.md") if f.is_file()]
                test_files.extend(md_files[:2])
            
            if len(test_files) >= 2:
                break
    
    if not test_files:
        print("❌ No creative content files found for testing")
        print("💡 Try placing some script or story files in Downloads or Desktop")
        return
    
    print(f"📚 Testing with {len(test_files)} files")
    
    for i, test_file in enumerate(test_files, 1):
        print(f"\n🎬 [{i}] Analyzing: {test_file.name}")
        
        try:
            analysis = partner.analyze_creative_content(test_file)
            
            print(f"   🎯 Project: {analysis.project_identified or 'Unknown'}")
            print(f"   👥 Characters: {len(analysis.characters_found)}")
            
            if analysis.characters_found:
                char_list = ', '.join(analysis.characters_found[:5])
                if len(analysis.characters_found) > 5:
                    char_list += f" ... and {len(analysis.characters_found) - 5} more"
                print(f"      Names: {char_list}")
            
            if analysis.new_characters:
                print(f"   ✨ New characters: {', '.join(analysis.new_characters[:3])}")
            
            if analysis.themes_detected:
                print(f"   🎨 Themes: {', '.join(analysis.themes_detected[:3])}")
            
            if analysis.story_elements:
                print(f"   🏛️  Story elements: {len(analysis.story_elements)}")
            
            print(f"   📊 Plot: {analysis.plot_progression}")
            print(f"   🎯 Confidence: {analysis.analysis_confidence:.1%}")
            
            if analysis.continuity_issues:
                print(f"   ⚠️  Continuity issues: {len(analysis.continuity_issues)}")
            
            # Save analysis
            success = partner.save_analysis(analysis)
            print(f"   💾 Saved: {'✅' if success else '❌'}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
    
    # Test project overview if we found any projects
    print(f"\n📋 Testing project overviews:")
    
    with sqlite3.connect(partner.db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT project_identified FROM file_analysis WHERE project_identified IS NOT NULL")
        projects = [row[0] for row in cursor.fetchall()]
    
    for project_name in projects[:2]:  # Test up to 2 projects
        print(f"\n🎬 Project: {project_name}")
        overview = partner.get_project_overview(project_name)
        
        if overview:
            print(f"   📁 Files: {overview['total_files']}")
            print(f"   👥 Characters: {overview['total_characters']}")
            
            if overview['characters']:
                char_names = [char['name'] for char in overview['characters'][:3]]
                print(f"      Main characters: {', '.join(char_names)}")
    
    print(f"\n✅ Creative AI Partner test completed!")

if __name__ == "__main__":
    test_creative_ai_partner()