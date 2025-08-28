#!/usr/bin/env python3
"""
Creative Idea Generation System for AI File Organizer
Analyzes content patterns and generates creative suggestions, plot ideas, and inspiration
Perfect for overcoming writer's block and discovering new creative directions
"""

import sys
import os
import sqlite3
import json
import re
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
from itertools import combinations

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from content_extractor import ContentExtractor
from creative_ai_partner import CreativeAIPartner

@dataclass
class CreativeIdea:
    """Represents a generated creative idea"""
    idea_type: str  # plot_twist, character_arc, theme_exploration, crossover, etc.
    title: str
    description: str
    inspiration_sources: List[str]  # Files that inspired this idea
    confidence: float
    genre_tags: List[str]
    character_suggestions: List[str]
    theme_connections: List[str]
    implementation_notes: str
    generated_date: datetime

@dataclass
class ContentPattern:
    """Represents a pattern found in creative content"""
    pattern_type: str  # theme, character_archetype, plot_structure, conflict_type
    pattern_name: str
    frequency: int
    related_files: List[str]
    variations: List[str]
    creative_potential: float

class CreativeIdeaGenerator:
    """
    Generates creative ideas and inspiration based on patterns in your existing content
    Designed to help with writer's block and creative development
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.ideas_dir = self.base_dir / "04_METADATA_SYSTEM" / "creative_ideas"
        self.ideas_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize content extractor and creative partner
        self.content_extractor = ContentExtractor(str(self.base_dir))
        self.creative_partner = CreativeAIPartner(str(self.base_dir))
        
        # Database for storing generated ideas
        self.db_path = self.ideas_dir / "creative_ideas.db"
        self._init_ideas_db()
        
        # Creative inspiration templates
        self.idea_templates = {
            'plot_twist': [
                "What if {character1} discovered that {character2} was actually {twist_element}?",
                "The {setting} that seemed safe turns out to be {danger_type}",
                "What if the {conflict} was actually caused by {unexpected_cause}?",
                "{character1} realizes that {their_goal} will destroy {what_they_love}",
                "The solution to {problem} creates an even bigger {new_problem}"
            ],
            
            'character_development': [
                "How would {character} change if they lost {important_thing}?",
                "What if {character1} had to teach {character2} about {theme}?",
                "Explore {character}'s backstory involving {theme} and {conflict_type}",
                "{character} must choose between {value1} and {value2}",
                "Show {character} learning {lesson} through {challenge_type}"
            ],
            
            'theme_exploration': [
                "Explore the intersection of {theme1} and {theme2} through {setting}",
                "What does {theme} look like in a world where {speculative_element}?",
                "How does {theme} manifest differently in {character1} vs {character2}?",
                "The cost of {theme} when taken to extremes",
                "Finding {theme} in unexpected places: {unlikely_setting}"
            ],
            
            'crossover_concepts': [
                "What if characters from {project1} met characters from {project2}?",
                "Combine the {element1} from {project1} with {element2} from {project2}",
                "How would {character1} handle the situation from {project2}?",
                "The themes of {project1} explored through the lens of {project2}",
                "{project1} set in the world of {project2}"
            ],
            
            'world_building': [
                "A society where {theme} is the central organizing principle",
                "What if {technology} was discovered in {historical_period}?",
                "A world where {character_trait} is illegal/mandatory",
                "The implications of {speculative_element} for {social_structure}",
                "Hidden {mysterious_element} underneath {familiar_setting}"
            ],
            
            'conflict_escalation': [
                "The {small_problem} spirals into {major_consequence}",
                "Personal {internal_conflict} becomes public {external_conflict}",
                "Allies become enemies over {philosophical_disagreement}",
                "The solution to {problem1} creates {problem2} with {character2}",
                "{character}'s strength becomes their weakness when {situation}"
            ]
        }
        
        # Genre-specific elements for idea generation
        self.genre_elements = {
            'sci_fi': {
                'technologies': ['AI consciousness', 'quantum computing', 'neural interfaces', 'time manipulation', 'genetic engineering'],
                'concepts': ['first contact', 'post-human evolution', 'digital consciousness', 'reality simulation', 'space colonization'],
                'conflicts': ['human vs AI', 'technology addiction', 'identity in digital age', 'playing god', 'unintended consequences']
            },
            
            'drama': {
                'relationships': ['family secrets', 'forbidden love', 'betrayal of trust', 'generational conflict', 'moral compromise'],
                'settings': ['small town', 'workplace', 'family gathering', 'crisis situation', 'milestone event'],
                'conflicts': ['duty vs desire', 'truth vs kindness', 'ambition vs ethics', 'past vs future', 'individual vs community']
            },
            
            'thriller': {
                'plot_devices': ['hidden identity', 'conspiracy', 'race against time', 'cat and mouse', 'double agent'],
                'dangers': ['stalker', 'corruption', 'blackmail', 'kidnapping', 'murder cover-up'],
                'revelations': ['trusted ally is enemy', 'victim is perpetrator', 'rescue is trap', 'escape route is blocked', 'help never coming']
            },
            
            'fantasy': {
                'magical_elements': ['prophecy', 'ancient curse', 'magical artifact', 'portal', 'transformation'],
                'conflicts': ['chosen one burden', 'power corruption', 'magic vs technology', 'old gods vs new', 'destiny vs free will'],
                'world_building': ['hidden magical world', 'magic has a price', 'dying magic', 'new magic discovered', 'magic is illegal']
            }
        }
        
        # Inspiration triggers for different creative needs
        self.inspiration_triggers = {
            'writers_block': [
                "Start with a character doing something completely unexpected",
                "Write the scene you're avoiding - what makes it difficult?",
                "What if your protagonist's greatest strength was actually their weakness?",
                "Begin with the ending and work backwards",
                "What would your character never, ever do? Make them do it."
            ],
            
            'character_development': [
                "Give your character a secret they're ashamed of",
                "What does your character want vs what do they need?",
                "How would your character react to their worst fear coming true?",
                "What lie does your character tell themselves?",
                "Who from your character's past haunts them?"
            ],
            
            'plot_development': [
                "What's the worst thing that could happen right now?",
                "How can you make your character's goal harder to achieve?",
                "What if the obvious solution doesn't work?",
                "Who has something to lose if your character succeeds?",
                "What price is your character unwilling to pay?"
            ],
            
            'theme_exploration': [
                "How does your theme show up in small, everyday moments?",
                "What's the dark side of your positive theme?",
                "How do different characters embody different aspects of your theme?",
                "What happens when your theme is taken to extremes?",
                "Where is your theme most unexpected or surprising?"
            ]
        }
    
    def _init_ideas_db(self):
        """Initialize SQLite database for creative ideas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS creative_ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idea_type TEXT,
                    title TEXT,
                    description TEXT,
                    inspiration_sources TEXT,  -- JSON array
                    confidence REAL,
                    genre_tags TEXT,  -- JSON array
                    character_suggestions TEXT,  -- JSON array
                    theme_connections TEXT,  -- JSON array
                    implementation_notes TEXT,
                    generated_date TEXT,
                    used BOOLEAN DEFAULT 0,
                    user_rating INTEGER,  -- 1-5 stars
                    notes TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT,
                    pattern_name TEXT,
                    frequency INTEGER,
                    related_files TEXT,  -- JSON array
                    variations TEXT,  -- JSON array
                    creative_potential REAL,
                    discovered_date TEXT,
                    last_seen TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inspiration_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date TEXT,
                    session_type TEXT,  -- brainstorm, writers_block, character_dev, etc.
                    ideas_generated INTEGER,
                    user_feedback TEXT,
                    most_helpful_idea_id INTEGER,
                    duration_minutes INTEGER
                )
            """)
            
            conn.commit()
    
    def analyze_creative_patterns(self) -> List[ContentPattern]:
        """Analyze existing creative content to identify patterns for idea generation"""
        
        print("🔍 Analyzing creative content patterns...")
        
        patterns = []
        
        # Get all analyzed creative files from creative partner
        with sqlite3.connect(self.creative_partner.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path, project_identified, characters_found, themes_detected, 
                       story_elements, character_development, plot_progression
                FROM file_analysis
                ORDER BY analyzed_date DESC
            """)
            
            creative_files = cursor.fetchall()
        
        if not creative_files:
            print("❌ No creative content analyzed yet")
            return patterns
        
        # Analyze character patterns
        character_patterns = self._analyze_character_patterns(creative_files)
        patterns.extend(character_patterns)
        
        # Analyze theme patterns  
        theme_patterns = self._analyze_theme_patterns(creative_files)
        patterns.extend(theme_patterns)
        
        # Analyze plot patterns
        plot_patterns = self._analyze_plot_patterns(creative_files)
        patterns.extend(plot_patterns)
        
        # Analyze project patterns
        project_patterns = self._analyze_project_patterns(creative_files)
        patterns.extend(project_patterns)
        
        # Save patterns to database
        self._save_patterns(patterns)
        
        print(f"✅ Discovered {len(patterns)} creative patterns")
        
        return patterns
    
    def _analyze_character_patterns(self, creative_files: List) -> List[ContentPattern]:
        """Analyze patterns in character usage and development"""
        
        patterns = []
        character_frequency = Counter()
        character_files = defaultdict(list)
        character_development_types = defaultdict(list)
        
        for file_data in creative_files:
            file_path, project, characters_json, themes_json, elements_json, dev_json, plot = file_data
            
            if characters_json:
                characters = json.loads(characters_json)
                for character in characters:
                    character_frequency[character] += 1
                    character_files[character].append(file_path)
            
            if dev_json:
                character_dev = json.loads(dev_json)
                for character, development in character_dev.items():
                    character_development_types[development].append(character)
        
        # Create patterns for frequently appearing characters
        for character, frequency in character_frequency.most_common(10):
            if frequency >= 2:  # Character appears in multiple files
                patterns.append(ContentPattern(
                    pattern_type="recurring_character",
                    pattern_name=character,
                    frequency=frequency,
                    related_files=character_files[character],
                    variations=[],
                    creative_potential=min(frequency * 0.2, 1.0)
                ))
        
        # Create patterns for character development types
        for dev_type, characters in character_development_types.items():
            if len(characters) >= 2:
                patterns.append(ContentPattern(
                    pattern_type="character_development",
                    pattern_name=dev_type,
                    frequency=len(characters),
                    related_files=[],
                    variations=characters,
                    creative_potential=0.7
                ))
        
        return patterns
    
    def _analyze_theme_patterns(self, creative_files: List) -> List[ContentPattern]:
        """Analyze thematic patterns across creative work"""
        
        patterns = []
        theme_frequency = Counter()
        theme_files = defaultdict(list)
        
        for file_data in creative_files:
            file_path, project, characters_json, themes_json, elements_json, dev_json, plot = file_data
            
            if themes_json:
                themes = json.loads(themes_json)
                for theme in themes:
                    theme_frequency[theme] += 1
                    theme_files[theme].append(file_path)
        
        # Create patterns for recurring themes
        for theme, frequency in theme_frequency.most_common(10):
            if frequency >= 2:
                patterns.append(ContentPattern(
                    pattern_type="recurring_theme",
                    pattern_name=theme,
                    frequency=frequency,
                    related_files=theme_files[theme],
                    variations=[],
                    creative_potential=min(frequency * 0.3, 1.0)
                ))
        
        return patterns
    
    def _analyze_plot_patterns(self, creative_files: List) -> List[ContentPattern]:
        """Analyze plot structure patterns"""
        
        patterns = []
        plot_types = Counter()
        
        for file_data in creative_files:
            file_path, project, characters_json, themes_json, elements_json, dev_json, plot = file_data
            
            if plot:
                plot_types[plot] += 1
        
        # Create patterns for plot structures
        for plot_type, frequency in plot_types.most_common():
            if frequency >= 2:
                patterns.append(ContentPattern(
                    pattern_type="plot_structure",
                    pattern_name=plot_type,
                    frequency=frequency,
                    related_files=[],
                    variations=[],
                    creative_potential=0.5
                ))
        
        return patterns
    
    def _analyze_project_patterns(self, creative_files: List) -> List[ContentPattern]:
        """Analyze patterns across different projects"""
        
        patterns = []
        project_frequency = Counter()
        project_files = defaultdict(list)
        
        for file_data in creative_files:
            file_path, project, characters_json, themes_json, elements_json, dev_json, plot = file_data
            
            if project:
                project_frequency[project] += 1
                project_files[project].append(file_path)
        
        # Create patterns for active projects
        for project, frequency in project_frequency.items():
            patterns.append(ContentPattern(
                pattern_type="active_project",
                pattern_name=project,
                frequency=frequency,
                related_files=project_files[project],
                variations=[],
                creative_potential=min(frequency * 0.1, 0.8)
            ))
        
        return patterns
    
    def _save_patterns(self, patterns: List[ContentPattern]):
        """Save discovered patterns to database"""
        
        with sqlite3.connect(self.db_path) as conn:
            for pattern in patterns:
                conn.execute("""
                    INSERT OR REPLACE INTO content_patterns
                    (pattern_type, pattern_name, frequency, related_files, variations,
                     creative_potential, discovered_date, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_type,
                    pattern.pattern_name,
                    pattern.frequency,
                    json.dumps(pattern.related_files),
                    json.dumps(pattern.variations),
                    pattern.creative_potential,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
    
    def generate_ideas(self, idea_type: str = "mixed", count: int = 5, 
                      focus_project: str = None) -> List[CreativeIdea]:
        """Generate creative ideas based on content patterns"""
        
        print(f"💡 Generating {count} {idea_type} ideas...")
        
        # First, analyze patterns if we haven't recently
        patterns = self.analyze_creative_patterns()
        
        ideas = []
        
        # Get available elements for idea generation
        characters = [p.pattern_name for p in patterns if p.pattern_type == "recurring_character"]
        themes = [p.pattern_name for p in patterns if p.pattern_type == "recurring_theme"]
        projects = [p.pattern_name for p in patterns if p.pattern_type == "active_project"]
        
        if focus_project:
            projects = [focus_project] if focus_project in projects else projects
        
        # Generate different types of ideas
        idea_types = [idea_type] if idea_type != "mixed" else list(self.idea_templates.keys())
        
        for _ in range(count):
            selected_type = random.choice(idea_types)
            
            try:
                idea = self._generate_single_idea(selected_type, characters, themes, projects, patterns)
                if idea:
                    ideas.append(idea)
            except Exception as e:
                print(f"⚠️  Error generating {selected_type} idea: {e}")
                continue
        
        # Save generated ideas
        self._save_ideas(ideas)
        
        print(f"✅ Generated {len(ideas)} creative ideas")
        
        return ideas
    
    def _generate_single_idea(self, idea_type: str, characters: List[str], 
                            themes: List[str], projects: List[str], 
                            patterns: List[ContentPattern]) -> Optional[CreativeIdea]:
        """Generate a single creative idea of specified type"""
        
        templates = self.idea_templates.get(idea_type, [])
        if not templates:
            return None
        
        template = random.choice(templates)
        
        # Fill in template variables
        variables = {
            'character': random.choice(characters) if characters else "the protagonist",
            'character1': random.choice(characters) if characters else "the protagonist", 
            'character2': random.choice(characters) if len(characters) > 1 else "the antagonist",
            'theme': random.choice(themes) if themes else "identity",
            'theme1': random.choice(themes) if themes else "power",
            'theme2': random.choice(themes) if len(themes) > 1 else "responsibility",
            'project1': random.choice(projects) if projects else "your current project",
            'project2': random.choice(projects) if len(projects) > 1 else "a past project",
            'conflict': random.choice(['internal struggle', 'external threat', 'moral dilemma', 'relationship conflict']),
            'setting': random.choice(['familiar place', 'new environment', 'hostile territory', 'safe haven']),
            'twist_element': random.choice(['the villain', 'an ally in disguise', 'from the future', 'their own family']),
            'challenge_type': random.choice(['physical test', 'emotional trial', 'moral choice', 'intellectual puzzle'])
        }
        
        # Generate the idea description
        try:
            description = template.format(**variables)
        except KeyError as e:
            # If template needs a variable we don't have, create a generic one
            missing_var = str(e).strip("'")
            variables[missing_var] = f"[{missing_var.replace('_', ' ')}]"
            description = template.format(**variables)
        
        # Generate implementation notes
        implementation_notes = self._generate_implementation_notes(idea_type, variables)
        
        # Create the creative idea
        idea = CreativeIdea(
            idea_type=idea_type,
            title=f"{idea_type.replace('_', ' ').title()} Concept",
            description=description,
            inspiration_sources=[p.pattern_name for p in patterns if p.creative_potential > 0.5],
            confidence=random.uniform(0.6, 0.9),
            genre_tags=self._determine_genre_tags(description, themes),
            character_suggestions=characters[:3],
            theme_connections=themes[:3],
            implementation_notes=implementation_notes,
            generated_date=datetime.now()
        )
        
        return idea
    
    def _generate_implementation_notes(self, idea_type: str, variables: Dict) -> str:
        """Generate practical implementation suggestions for the idea"""
        
        notes_templates = {
            'plot_twist': [
                f"Consider foreshadowing this through {variables.get('character1', 'character')} behavior",
                "Plant subtle clues 2-3 scenes before the revelation",
                "Make sure the twist feels inevitable in hindsight"
            ],
            'character_development': [
                f"Show {variables.get('character', 'character')} growth through actions, not exposition",
                "Create specific scenes that test this development",
                "Consider how other characters react to the change"
            ],
            'theme_exploration': [
                f"Explore {variables.get('theme', 'theme')} through multiple character perspectives",
                "Use symbolism and metaphor to reinforce the theme",
                "Avoid being preachy - let the theme emerge naturally"
            ]
        }
        
        suggestions = notes_templates.get(idea_type, ["Develop this idea through character actions and dialogue"])
        return "; ".join(suggestions)
    
    def _determine_genre_tags(self, description: str, themes: List[str]) -> List[str]:
        """Determine appropriate genre tags for an idea"""
        
        tags = []
        description_lower = description.lower()
        
        # Check for genre indicators
        if any(word in description_lower for word in ['future', 'technology', 'ai', 'space', 'robot']):
            tags.append('sci-fi')
        
        if any(word in description_lower for word in ['love', 'relationship', 'heart', 'emotion']):
            tags.append('drama')
        
        if any(word in description_lower for word in ['danger', 'threat', 'chase', 'escape', 'survival']):
            tags.append('thriller')
        
        if any(word in description_lower for word in ['magic', 'curse', 'prophecy', 'quest', 'ancient']):
            tags.append('fantasy')
        
        # Add theme-based tags
        if 'consciousness' in themes:
            tags.append('philosophical')
        
        if not tags:
            tags.append('general')
        
        return tags
    
    def _save_ideas(self, ideas: List[CreativeIdea]):
        """Save generated ideas to database"""
        
        with sqlite3.connect(self.db_path) as conn:
            for idea in ideas:
                conn.execute("""
                    INSERT INTO creative_ideas
                    (idea_type, title, description, inspiration_sources, confidence,
                     genre_tags, character_suggestions, theme_connections,
                     implementation_notes, generated_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    idea.idea_type,
                    idea.title,
                    idea.description,
                    json.dumps(idea.inspiration_sources),
                    idea.confidence,
                    json.dumps(idea.genre_tags),
                    json.dumps(idea.character_suggestions),
                    json.dumps(idea.theme_connections),
                    idea.implementation_notes,
                    idea.generated_date.isoformat()
                ))
            
            conn.commit()
    
    def get_inspiration_for_writers_block(self, context: str = "") -> List[str]:
        """Get specific inspiration prompts for overcoming writer's block"""
        
        prompts = []
        
        # Get context-specific prompts
        if context:
            context_lower = context.lower()
            
            if 'dialogue' in context_lower:
                prompts.extend([
                    "What's something this character would never say? Make them say it.",
                    "Have your character lie about something important.",
                    "What if this conversation happened in a completely different setting?"
                ])
            
            elif 'scene' in context_lower:
                prompts.extend([
                    "Start the scene later than you planned.",
                    "What's the subtext - what are characters really talking about?",
                    "Add an unexpected interruption to change the scene's direction."
                ])
            
            elif 'character' in context_lower:
                prompts.extend([
                    "Give your character a secret that changes everything.",
                    "What does your character want vs what do they need?",
                    "How would your character's enemy describe them?"
                ])
        
        # Add general writer's block breakers
        prompts.extend(random.sample(self.inspiration_triggers['writers_block'], 3))
        
        return prompts[:7]  # Return top 7 prompts
    
    def suggest_character_connections(self, character1: str, character2: str = None) -> List[str]:
        """Suggest interesting connections between characters"""
        
        suggestions = []
        
        if character2:
            # Specific character pair suggestions
            relationship_types = ['allies', 'enemies', 'family', 'romantic', 'mentor-student', 'rivals']
            
            for relationship in relationship_types:
                suggestions.append(f"What if {character1} and {character2} were {relationship}?")
                suggestions.append(f"How would {character1} react if {character2} betrayed them?")
                suggestions.append(f"What secret might {character1} and {character2} share?")
        else:
            # General character development suggestions
            suggestions.extend([
                f"What if {character1} had to sacrifice something important?",
                f"Give {character1} an impossible choice between two things they value.",
                f"How would {character1} change if they lost their greatest strength?",
                f"What does {character1} believe that isn't true?",
                f"Who from {character1}'s past could return to complicate things?"
            ])
        
        return suggestions[:5]
    
    def get_recent_ideas(self, limit: int = 10, idea_type: str = None) -> List[Dict]:
        """Get recently generated ideas"""
        
        with sqlite3.connect(self.db_path) as conn:
            if idea_type:
                cursor = conn.execute("""
                    SELECT * FROM creative_ideas 
                    WHERE idea_type = ?
                    ORDER BY generated_date DESC 
                    LIMIT ?
                """, (idea_type, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM creative_ideas 
                    ORDER BY generated_date DESC 
                    LIMIT ?
                """, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            ideas = []
            
            for row in cursor.fetchall():
                idea_dict = dict(zip(columns, row))
                # Parse JSON fields
                idea_dict['inspiration_sources'] = json.loads(idea_dict.get('inspiration_sources', '[]'))
                idea_dict['genre_tags'] = json.loads(idea_dict.get('genre_tags', '[]'))
                idea_dict['character_suggestions'] = json.loads(idea_dict.get('character_suggestions', '[]'))
                idea_dict['theme_connections'] = json.loads(idea_dict.get('theme_connections', '[]'))
                ideas.append(idea_dict)
            
            return ideas
    
    def rate_idea(self, idea_id: int, rating: int, notes: str = "") -> bool:
        """Rate an idea (1-5 stars) and add notes"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE creative_ideas 
                    SET user_rating = ?, notes = ?
                    WHERE id = ?
                """, (rating, notes, idea_id))
                conn.commit()
            
            return True
        except Exception as e:
            print(f"❌ Error rating idea: {e}")
            return False

def test_creative_idea_generator():
    """Test the creative idea generator system"""
    
    print("💡 Testing Creative Idea Generator")
    print("=" * 60)
    
    generator = CreativeIdeaGenerator()
    
    # Test pattern analysis
    print("🔍 Analyzing creative patterns...")
    patterns = generator.analyze_creative_patterns()
    
    print(f"📊 Pattern Analysis Results:")
    pattern_types = Counter([p.pattern_type for p in patterns])
    for pattern_type, count in pattern_types.items():
        print(f"   {pattern_type}: {count} patterns")
    
    # Test idea generation
    print(f"\n💫 Generating creative ideas...")
    
    idea_types = ['plot_twist', 'character_development', 'theme_exploration']
    
    for idea_type in idea_types:
        print(f"\n🎭 {idea_type.replace('_', ' ').title()} Ideas:")
        
        ideas = generator.generate_ideas(idea_type=idea_type, count=2)
        
        for i, idea in enumerate(ideas, 1):
            print(f"\n   {i}. {idea.title}")
            print(f"      💡 {idea.description}")
            print(f"      🎯 Confidence: {idea.confidence:.0%}")
            print(f"      🏷️  Tags: {', '.join(idea.genre_tags)}")
            
            if idea.character_suggestions:
                print(f"      👥 Characters: {', '.join(idea.character_suggestions)}")
            
            if idea.implementation_notes:
                print(f"      📝 Notes: {idea.implementation_notes}")
    
    # Test writer's block inspiration
    print(f"\n✍️  Writer's Block Inspiration:")
    inspiration = generator.get_inspiration_for_writers_block("dialogue scene")
    
    for i, prompt in enumerate(inspiration[:5], 1):
        print(f"   {i}. {prompt}")
    
    # Test character connections
    print(f"\n👥 Character Connection Ideas:")
    if patterns:
        character_patterns = [p for p in patterns if p.pattern_type == "recurring_character"]
        if len(character_patterns) >= 2:
            char1 = character_patterns[0].pattern_name
            char2 = character_patterns[1].pattern_name
            
            connections = generator.suggest_character_connections(char1, char2)
            for i, connection in enumerate(connections[:3], 1):
                print(f"   {i}. {connection}")
    
    # Show recent ideas
    print(f"\n📚 Recent Ideas:")
    recent_ideas = generator.get_recent_ideas(limit=3)
    
    for i, idea in enumerate(recent_ideas, 1):
        print(f"   {i}. {idea['title']}")
        print(f"      Type: {idea['idea_type']}")
        print(f"      Generated: {idea['generated_date'][:10]}")
    
    print(f"\n✅ Creative idea generator test completed!")

if __name__ == "__main__":
    test_creative_idea_generator()