#!/usr/bin/env python3
"""
Universal Adaptive Learning System - Core Intelligence Foundation
Part of AI File Organizer v3.1 - Adaptive Emergency Prevention System

Inspired by Audio-AI-Organizer's AdaptiveAudioOrganizer class
Designed for ADHD-friendly proactive file management

Created by: RT Max / Claude Code
"""

import os
import sys
import json
import pickle
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import hashlib
import sqlite3
import logging

# Import existing system components
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from gdrive_integration import get_ai_organizer_root, get_metadata_root

@dataclass
class LearningEvent:
    """Record of a learning event for the adaptive system"""
    event_id: str
    timestamp: datetime
    event_type: str  # "user_correction", "manual_move", "preference_update", "pattern_discovery"
    file_path: str
    original_prediction: Dict[str, Any]
    user_action: Dict[str, Any]
    confidence_before: float
    confidence_after: float
    context: Dict[str, Any] = None

@dataclass
class AdaptivePattern:
    """A discovered pattern that can improve future predictions"""
    pattern_id: str
    pattern_type: str  # "filename", "content", "location", "time", "user_behavior"
    trigger_conditions: Dict[str, Any]
    predicted_action: Dict[str, Any]
    confidence: float
    frequency: int
    last_seen: datetime
    accuracy_rate: float = 0.0

@dataclass
class UserPreference:
    """A learned user preference"""
    preference_id: str
    preference_type: str  # "category", "location", "person", "project", "timing"
    conditions: Dict[str, Any]
    preferred_action: Dict[str, Any]
    strength: float  # 0.0-1.0, how strong this preference is
    frequency: int
    last_reinforced: datetime

class UniversalAdaptiveLearning:
    """
    Core adaptive learning system that learns from all user interactions
    and improves file organization predictions over time
    
    Designed for ADHD users - reduces cognitive load by learning patterns
    """
    
    def __init__(self, base_dir: str = None):
        # Set up logging FIRST (required by all _load_* methods)
        self.logger = logging.getLogger(__name__)

        # Use Google Drive integration as primary storage root
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()

        # Learning system files
        self.learning_dir = get_metadata_root() /  "adaptive_learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)

        # Persistent storage files
        self.learning_events_file = self.learning_dir / "learning_events.pkl"
        self.patterns_file = self.learning_dir / "discovered_patterns.pkl"
        self.preferences_file = self.learning_dir / "user_preferences.pkl"
        self.stats_file = self.learning_dir / "learning_stats.json"

        # Database for quick queries - use local storage for SQLite (cloud sync conflicts)
        local_db_dir = Path.home() / ".ai_file_organizer" / "databases"
        local_db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = local_db_dir / "adaptive_learning.db"

        # Load existing data
        self.learning_events: List[LearningEvent] = self._load_learning_events()
        self.patterns: Dict[str, AdaptivePattern] = self._load_patterns()
        self.user_preferences: Dict[str, UserPreference] = self._load_preferences()
        self.stats = self._load_stats()

        # Visual pattern storage for image/video learning
        self.visual_patterns_file = self.learning_dir / "visual_patterns.pkl"
        self.visual_patterns = self._load_visual_patterns()

        # Audio pattern storage for audio learning
        self.audio_patterns_file = self.learning_dir / "audio_patterns.pkl"
        self.audio_patterns = self._load_audio_patterns()
        
        # Learning configuration
        self.config = {
            "min_pattern_frequency": 3,  # Minimum occurrences to consider a pattern
            "pattern_confidence_threshold": 0.7,  # Minimum confidence to suggest pattern
            "preference_decay_days": 30,  # How quickly preferences fade without reinforcement
            "max_learning_events": 10000,  # Maximum events to keep in memory
            "confidence_boost_rates": {
                "user_correction": 0.3,
                "manual_move": 0.2,
                "pattern_match": 0.1,
                "preference_match": 0.15
            }
        }
        
        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for fast pattern and preference queries"""
        with sqlite3.connect(self.db_path) as conn:
            # Learning events table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    event_type TEXT,
                    file_path TEXT,
                    original_prediction TEXT,
                    user_action TEXT,
                    confidence_before REAL,
                    confidence_after REAL,
                    context TEXT
                )
            ''')
            
            # Patterns table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT,
                    trigger_conditions TEXT,
                    predicted_action TEXT,
                    confidence REAL,
                    frequency INTEGER,
                    last_seen TEXT,
                    accuracy_rate REAL
                )
            ''')
            
            # User preferences table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    preference_id TEXT PRIMARY KEY,
                    preference_type TEXT,
                    conditions TEXT,
                    preferred_action TEXT,
                    strength REAL,
                    frequency INTEGER,
                    last_reinforced TEXT
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_events_type ON learning_events(event_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_events_file ON learning_events(file_path)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_preferences_type ON user_preferences(preference_type)')

    def _load_learning_events(self) -> List[LearningEvent]:
        """Load learning events from pickle file"""
        if self.learning_events_file.exists():
            try:
                with open(self.learning_events_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load learning events: {e}")
        return []

    def _load_patterns(self) -> Dict[str, AdaptivePattern]:
        """Load discovered patterns from pickle file"""
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load patterns: {e}")
        return {}

    def _load_preferences(self) -> Dict[str, UserPreference]:
        """Load user preferences from pickle file"""
        if self.preferences_file.exists():
            try:
                with open(self.preferences_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load preferences: {e}")
        return {}

    def _load_stats(self) -> Dict:
        """Load learning statistics"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load stats: {e}")

        return {
            "total_learning_events": 0,
            "patterns_discovered": 0,
            "preferences_learned": 0,
            "accuracy_improvement": 0.0,
            "last_updated": datetime.now().isoformat(),
            "confidence_trends": [],
            "most_common_corrections": []
        }

    def _load_visual_patterns(self) -> Dict[str, Any]:
        """Load visual patterns from pickle file"""
        if self.visual_patterns_file.exists():
            try:
                with open(self.visual_patterns_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load visual patterns: {e}")

        # Initialize default visual pattern structure
        return {
            'objects_detected': defaultdict(list),
            'scene_types': defaultdict(list),
            'screenshot_contexts': defaultdict(list),
            'visual_keywords': defaultdict(list),
            'category_frequencies': defaultdict(int)
        }

    def _load_audio_patterns(self) -> Dict[str, Any]:
        """Load audio patterns from pickle file"""
        if self.audio_patterns_file.exists():
            try:
                with open(self.audio_patterns_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load audio patterns: {e}")

        # Initialize default audio pattern structure
        return {
            'bpm_ranges': defaultdict(list),  # BPM ranges by category
            'moods': defaultdict(list),  # Mood associations by category
            'content_types': defaultdict(list),  # music, SFX, voice, ambient
            'energy_levels': defaultdict(list),  # Energy level ranges by category
            'spectral_features': defaultdict(list),  # Spectral characteristics
            'audio_keywords': defaultdict(list),  # Keywords from audio analysis
            'category_frequencies': defaultdict(int)  # Category usage frequency
        }

    def save_all_data(self):
        """Save all learning data to persistent storage"""
        try:
            # Save pickle files
            with open(self.learning_events_file, 'wb') as f:
                pickle.dump(self.learning_events, f)
            
            with open(self.patterns_file, 'wb') as f:
                pickle.dump(self.patterns, f)
            
            with open(self.preferences_file, 'wb') as f:
                pickle.dump(self.user_preferences, f)
            
            # Update stats
            self.stats["last_updated"] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            
            # Sync to database
            self._sync_to_database()
            
        except Exception as e:
            self.logger.error(f"Error saving learning data: {e}")

    def _sync_to_database(self):
        """Sync in-memory data to SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            # Clear existing data
            conn.execute('DELETE FROM learning_events')
            conn.execute('DELETE FROM patterns')
            conn.execute('DELETE FROM user_preferences')
            
            # Insert learning events
            for event in self.learning_events[-1000:]:  # Keep last 1000 events in DB
                conn.execute('''
                    INSERT INTO learning_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.event_type,
                    event.file_path,
                    json.dumps(event.original_prediction),
                    json.dumps(event.user_action),
                    event.confidence_before,
                    event.confidence_after,
                    json.dumps(event.context) if event.context else None
                ))
            
            # Insert patterns
            for pattern in self.patterns.values():
                conn.execute('''
                    INSERT INTO patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pattern.pattern_id,
                    pattern.pattern_type,
                    json.dumps(pattern.trigger_conditions),
                    json.dumps(pattern.predicted_action),
                    pattern.confidence,
                    pattern.frequency,
                    pattern.last_seen.isoformat(),
                    pattern.accuracy_rate
                ))
            
            # Insert preferences
            for pref in self.user_preferences.values():
                conn.execute('''
                    INSERT INTO user_preferences VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pref.preference_id,
                    pref.preference_type,
                    json.dumps(pref.conditions),
                    json.dumps(pref.preferred_action),
                    pref.strength,
                    pref.frequency,
                    pref.last_reinforced.isoformat()
                ))

    def record_learning_event(self, 
                            event_type: str,
                            file_path: str,
                            original_prediction: Dict[str, Any],
                            user_action: Dict[str, Any],
                            confidence_before: float,
                            context: Dict[str, Any] = None) -> str:
        """
        Record a learning event for future pattern discovery
        
        Args:
            event_type: Type of learning event
            file_path: Path to the file involved
            original_prediction: What the system predicted
            user_action: What the user actually did
            confidence_before: Confidence before user action
            context: Additional context information
        
        Returns:
            Event ID
        """
        
        # Calculate confidence boost from this correction
        confidence_after = confidence_before + self.config["confidence_boost_rates"].get(event_type, 0.1)
        confidence_after = min(1.0, confidence_after)
        
        # Create learning event
        event_id = hashlib.md5(f"{file_path}_{datetime.now().isoformat()}_{event_type}".encode()).hexdigest()[:12]
        
        learning_event = LearningEvent(
            event_id=event_id,
            timestamp=datetime.now(),
            event_type=event_type,
            file_path=file_path,
            original_prediction=original_prediction,
            user_action=user_action,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            context=context or {}
        )
        
        # Add to learning events
        self.learning_events.append(learning_event)
        
        # Keep only recent events in memory
        if len(self.learning_events) > self.config["max_learning_events"]:
            self.learning_events = self.learning_events[-self.config["max_learning_events"]:]
        
        # Update stats
        self.stats["total_learning_events"] += 1
        
        # Trigger pattern discovery
        self._discover_patterns_from_event(learning_event)
        
        # Update preferences
        self._update_preferences_from_event(learning_event)

        # Save learning data to disk immediately to ensure persistence across instances
        self.save_all_data()

        self.logger.info(f"Recorded learning event: {event_type} for {Path(file_path).name}")

        return event_id

    def record_classification(self,
                            file_path: str,
                            predicted_category: str,
                            confidence: float,
                            features: Dict[str, Any],
                            media_type: str = 'unknown') -> str:
        """
        Record a classification event from multimodal sources (images, videos, audio, etc.)

        This method supports classification from:
        - Static images (media_type='image')
        - Video clips (media_type='video')
        - Audio files (media_type='audio')
        - Documents (media_type='document')

        Args:
            file_path: Path to the classified file
            predicted_category: Predicted category from classifier
            confidence: Confidence score (0.0-1.0)
            features: Dict of extracted features
            media_type: Type of media ('image', 'video', 'audio', 'document', etc.)

        Returns:
            Event ID for this classification
        """

        # Build original prediction dict
        original_prediction = {
            'category': predicted_category,
            'confidence': confidence,
            'media_type': media_type
        }

        # Build context with media_type and features
        context = {
            'media_type': media_type,
            'features': features,
            'source': features.get('source', 'unknown'),
            'file_extension': Path(file_path).suffix.lower()
        }

        # Update visual patterns for images/videos
        if media_type in ['image', 'video']:
            self._update_visual_patterns_from_classification(
                file_path=file_path,
                category=predicted_category,
                features=features
            )

        # Update audio patterns for audio files
        elif media_type == 'audio':
            self._update_audio_patterns_from_classification(
                file_path=file_path,
                category=predicted_category,
                features=features
            )

        # Record the classification as a learning event
        # Use 'ai_classification' as event_type to distinguish from user corrections
        event_id = self.record_learning_event(
            event_type='ai_classification',
            file_path=file_path,
            original_prediction=original_prediction,
            user_action={'accepted': True, 'category': predicted_category},
            confidence_before=confidence,
            context=context
        )

        self.logger.info(
            f"Recorded {media_type} classification: {predicted_category} "
            f"({confidence:.2f}) for {Path(file_path).name}"
        )

        return event_id

    def _store_visual_patterns(self,
                              category: str,
                              features: Dict[str, Any],
                              media_type: str,
                              confidence: float):
        """Store visual patterns from image/video analysis for future learning"""

        # Update visual pattern storage
        if 'visual_objects' in features:
            self.visual_patterns['objects_detected'][category].extend(features['visual_objects'])

        if 'scene_type' in features:
            self.visual_patterns['scene_types'][category].append(features['scene_type'])

        if 'keywords' in features:
            self.visual_patterns['visual_keywords'][category].extend(features['keywords'])

        # For screenshots, track UI context
        if category == 'screenshot' and 'content_type' in features:
            self.visual_patterns['screenshot_contexts'][category].append(features['content_type'])

        # Track category frequency
        self.visual_patterns['category_frequencies'][category] += 1

        # Save visual patterns periodically
        if sum(self.visual_patterns['category_frequencies'].values()) % 10 == 0:
            with open(self.visual_patterns_file, 'wb') as f:
                pickle.dump(self.visual_patterns, f)

    def _store_audio_patterns(self,
                             category: str,
                             features: Dict[str, Any],
                             confidence: float):
        """Store audio patterns from audio analysis for future learning"""

        # Update audio pattern storage
        if 'bpm' in features:
            self.audio_patterns['bpm_ranges'][category].append(features['bpm'])

        if 'mood' in features:
            self.audio_patterns['moods'][category].append(features['mood'])

        if 'content_type' in features:
            self.audio_patterns['content_types'][category].append(features['content_type'])

        if 'energy' in features:
            self.audio_patterns['energy_levels'][category].append(features['energy'])

        if 'keywords' in features:
            self.audio_patterns['audio_keywords'][category].extend(features['keywords'])

        # Track category frequency
        self.audio_patterns['category_frequencies'][category] += 1

        # Save audio patterns periodically
        if sum(self.audio_patterns['category_frequencies'].values()) % 10 == 0:
            with open(self.audio_patterns_file, 'wb') as f:
                pickle.dump(self.audio_patterns, f)

    def _discover_patterns_from_event(self, event: LearningEvent):
        """Discover new patterns from a learning event"""
        
        # Look for filename patterns
        self._discover_filename_patterns(event)
        
        # Look for content patterns
        self._discover_content_patterns(event)
        
        # Look for location patterns
        self._discover_location_patterns(event)
        
        # Look for timing patterns
        self._discover_timing_patterns(event)

    def _discover_filename_patterns(self, event: LearningEvent):
        """Discover patterns in filenames that predict user actions"""
        filename = Path(event.file_path).name.lower()
        
        # Extract filename features
        features = {
            "extension": Path(event.file_path).suffix.lower(),
            "contains_numbers": any(c.isdigit() for c in filename),
            "word_count": len(filename.split()),
            "contains_date": self._contains_date_pattern(filename),
            "keywords": self._extract_keywords(filename)
        }
        
        # Look for similar events with same filename features
        similar_events = []
        for past_event in self.learning_events[-100:]:  # Check last 100 events
            if past_event.event_id == event.event_id:
                continue
                
            past_filename = Path(past_event.file_path).name.lower()
            past_features = {
                "extension": Path(past_event.file_path).suffix.lower(),
                "contains_numbers": any(c.isdigit() for c in past_filename),
                "word_count": len(past_filename.split()),
                "contains_date": self._contains_date_pattern(past_filename),
                "keywords": self._extract_keywords(past_filename)
            }
            
            # Check for feature matches
            matches = sum(1 for k, v in features.items() if past_features.get(k) == v)
            if matches >= 3:  # At least 3 features match
                similar_events.append(past_event)
        
        # If we have enough similar events, create a pattern
        if len(similar_events) >= self.config["min_pattern_frequency"]:
            pattern_id = hashlib.md5(f"filename_{json.dumps(features, sort_keys=True)}".encode()).hexdigest()[:12]
            
            if pattern_id not in self.patterns:
                self.patterns[pattern_id] = AdaptivePattern(
                    pattern_id=pattern_id,
                    pattern_type="filename",
                    trigger_conditions=features,
                    predicted_action=event.user_action,
                    confidence=0.7,
                    frequency=1,
                    last_seen=datetime.now()
                )
                self.stats["patterns_discovered"] += 1
            else:
                # Update existing pattern
                pattern = self.patterns[pattern_id]
                pattern.frequency += 1
                pattern.last_seen = datetime.now()
                pattern.confidence = min(0.95, pattern.confidence + 0.05)

    def _discover_content_patterns(self, event: LearningEvent):
        """Discover patterns in file content that predict user actions"""
        if not event.context or "content_keywords" not in event.context:
            return
        
        content_keywords = event.context["content_keywords"]
        if not content_keywords:
            return
        
        # Look for keyword combinations that predict actions
        keyword_combos = []
        for i in range(len(content_keywords)):
            for j in range(i+1, min(i+3, len(content_keywords))):  # Max 2-word combinations
                keyword_combos.append(tuple(sorted([content_keywords[i], content_keywords[j]])))
        
        for combo in keyword_combos:
            # Check if this combination appears in other events
            similar_count = 0
            for past_event in self.learning_events[-50:]:
                if (past_event.context and 
                    "content_keywords" in past_event.context and
                    all(keyword in past_event.context["content_keywords"] for keyword in combo)):
                    similar_count += 1
            
            if similar_count >= self.config["min_pattern_frequency"]:
                pattern_id = hashlib.md5(f"content_{json.dumps(combo)}".encode()).hexdigest()[:12]
                
                if pattern_id not in self.patterns:
                    self.patterns[pattern_id] = AdaptivePattern(
                        pattern_id=pattern_id,
                        pattern_type="content",
                        trigger_conditions={"keyword_combination": combo},
                        predicted_action=event.user_action,
                        confidence=0.75,
                        frequency=1,
                        last_seen=datetime.now()
                    )

    def _discover_location_patterns(self, event: LearningEvent):
        """Discover patterns in file locations that predict user actions"""
        source_dir = str(Path(event.file_path).parent).lower()
        
        # Extract location features
        location_features = {
            "in_downloads": "downloads" in source_dir,
            "in_desktop": "desktop" in source_dir,
            "in_documents": "documents" in source_dir,
            "in_temp": any(temp in source_dir for temp in ["temp", "tmp", "staging"]),
            "depth": len(Path(event.file_path).parts)
        }
        
        # Similar logic to filename patterns
        similar_events = []
        for past_event in self.learning_events[-100:]:
            if past_event.event_id == event.event_id:
                continue
            
            past_dir = str(Path(past_event.file_path).parent).lower()
            past_features = {
                "in_downloads": "downloads" in past_dir,
                "in_desktop": "desktop" in past_dir,
                "in_documents": "documents" in past_dir,
                "in_temp": any(temp in past_dir for temp in ["temp", "tmp", "staging"]),
                "depth": len(Path(past_event.file_path).parts)
            }
            
            matches = sum(1 for k, v in location_features.items() if past_features.get(k) == v)
            if matches >= 3:
                similar_events.append(past_event)
        
        if len(similar_events) >= self.config["min_pattern_frequency"]:
            pattern_id = hashlib.md5(f"location_{json.dumps(location_features, sort_keys=True)}".encode()).hexdigest()[:12]
            
            if pattern_id not in self.patterns:
                self.patterns[pattern_id] = AdaptivePattern(
                    pattern_id=pattern_id,
                    pattern_type="location",
                    trigger_conditions=location_features,
                    predicted_action=event.user_action,
                    confidence=0.8,
                    frequency=1,
                    last_seen=datetime.now()
                )

    def _discover_timing_patterns(self, event: LearningEvent):
        """Discover timing patterns in user behavior"""
        current_time = event.timestamp
        time_features = {
            "hour": current_time.hour,
            "day_of_week": current_time.weekday(),
            "is_weekend": current_time.weekday() >= 5,
            "is_morning": 6 <= current_time.hour <= 12,
            "is_afternoon": 12 < current_time.hour <= 18,
            "is_evening": 18 < current_time.hour <= 23
        }
        
        # Look for similar timing patterns
        similar_timing_events = []
        for past_event in self.learning_events[-50:]:
            if abs((past_event.timestamp - current_time).total_seconds()) > 86400 * 7:  # Within a week
                continue
            
            past_features = {
                "hour": past_event.timestamp.hour,
                "day_of_week": past_event.timestamp.weekday(),
                "is_weekend": past_event.timestamp.weekday() >= 5,
                "is_morning": 6 <= past_event.timestamp.hour <= 12,
                "is_afternoon": 12 < past_event.timestamp.hour <= 18,
                "is_evening": 18 < past_event.timestamp.hour <= 23
            }
            
            matches = sum(1 for k, v in time_features.items() if past_features.get(k) == v)
            if matches >= 4:
                similar_timing_events.append(past_event)
        
        if len(similar_timing_events) >= self.config["min_pattern_frequency"]:
            pattern_id = hashlib.md5(f"timing_{json.dumps(time_features, sort_keys=True)}".encode()).hexdigest()[:12]
            
            if pattern_id not in self.patterns:
                self.patterns[pattern_id] = AdaptivePattern(
                    pattern_id=pattern_id,
                    pattern_type="timing",
                    trigger_conditions=time_features,
                    predicted_action=event.user_action,
                    confidence=0.65,
                    frequency=1,
                    last_seen=datetime.now()
                )

    def _update_preferences_from_event(self, event: LearningEvent):
        """Update user preferences based on learning event"""
        
        # Extract preference indicators from user action
        user_action = event.user_action
        
        if "target_category" in user_action:
            self._update_category_preference(event, user_action["target_category"])
        
        if "target_location" in user_action:
            self._update_location_preference(event, user_action["target_location"])
        
        if "associated_person" in user_action:
            self._update_person_preference(event, user_action["associated_person"])

    def _update_category_preference(self, event: LearningEvent, category: str):
        """Update user's category preferences"""
        # Extract conditions that led to this category choice
        conditions = {
            "file_extension": Path(event.file_path).suffix.lower(),
            "source_location": str(Path(event.file_path).parent),
        }
        
        if event.context and "content_keywords" in event.context:
            # Use top 3 keywords as conditions
            top_keywords = event.context["content_keywords"][:3]
            conditions["content_keywords"] = top_keywords
        
        pref_id = hashlib.md5(f"category_{category}_{json.dumps(conditions, sort_keys=True)}".encode()).hexdigest()[:12]
        
        if pref_id in self.user_preferences:
            pref = self.user_preferences[pref_id]
            pref.frequency += 1
            pref.strength = min(1.0, pref.strength + 0.1)
            pref.last_reinforced = datetime.now()
        else:
            self.user_preferences[pref_id] = UserPreference(
                preference_id=pref_id,
                preference_type="category",
                conditions=conditions,
                preferred_action={"category": category},
                strength=0.7,
                frequency=1,
                last_reinforced=datetime.now()
            )
            self.stats["preferences_learned"] += 1

    def _update_location_preference(self, event: LearningEvent, location: str):
        """Update user's location preferences"""
        conditions = {
            "file_type": Path(event.file_path).suffix.lower(),
            "original_location": str(Path(event.file_path).parent)
        }
        
        pref_id = hashlib.md5(f"location_{location}_{json.dumps(conditions, sort_keys=True)}".encode()).hexdigest()[:12]
        
        if pref_id in self.user_preferences:
            pref = self.user_preferences[pref_id]
            pref.frequency += 1
            pref.strength = min(1.0, pref.strength + 0.1)
            pref.last_reinforced = datetime.now()
        else:
            self.user_preferences[pref_id] = UserPreference(
                preference_id=pref_id,
                preference_type="location",
                conditions=conditions,
                preferred_action={"location": location},
                strength=0.7,
                frequency=1,
                last_reinforced=datetime.now()
            )

    def _update_person_preference(self, event: LearningEvent, person: str):
        """Update user's person-related preferences"""
        conditions = {
            "file_type": Path(event.file_path).suffix.lower()
        }
        
        if event.context and "content_keywords" in event.context:
            conditions["content_keywords"] = event.context["content_keywords"][:3]
        
        pref_id = hashlib.md5(f"person_{person}_{json.dumps(conditions, sort_keys=True)}".encode()).hexdigest()[:12]
        
        if pref_id in self.user_preferences:
            pref = self.user_preferences[pref_id]
            pref.frequency += 1
            pref.strength = min(1.0, pref.strength + 0.1)
            pref.last_reinforced = datetime.now()
        else:
            self.user_preferences[pref_id] = UserPreference(
                preference_id=pref_id,
                preference_type="person",
                conditions=conditions,
                preferred_action={"person": person},
                strength=0.7,
                frequency=1,
                last_reinforced=datetime.now()
            )

    def predict_user_action(self, file_path: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Predict what the user would want to do with this file based on learned patterns
        
        Args:
            file_path: Path to the file
            context: Additional context about the file
        
        Returns:
            Prediction with confidence score and reasoning
        """
        
        predictions = []
        confidence_sum = 0.0
        reasoning = []
        
        # Check filename patterns
        filename_prediction = self._predict_from_filename_patterns(file_path)
        if filename_prediction:
            predictions.append(filename_prediction)
            confidence_sum += filename_prediction["confidence"]
            reasoning.append(f"Filename pattern: {filename_prediction['reasoning']}")
        
        # Check content patterns
        if context and "content_keywords" in context:
            content_prediction = self._predict_from_content_patterns(context["content_keywords"])
            if content_prediction:
                predictions.append(content_prediction)
                confidence_sum += content_prediction["confidence"]
                reasoning.append(f"Content pattern: {content_prediction['reasoning']}")
        
        # Check location patterns
        location_prediction = self._predict_from_location_patterns(file_path)
        if location_prediction:
            predictions.append(location_prediction)
            confidence_sum += location_prediction["confidence"]
            reasoning.append(f"Location pattern: {location_prediction['reasoning']}")
        
        # Check timing patterns
        timing_prediction = self._predict_from_timing_patterns()
        if timing_prediction:
            predictions.append(timing_prediction)
            confidence_sum += timing_prediction["confidence"]
            reasoning.append(f"Timing pattern: {timing_prediction['reasoning']}")
        
        # Check user preferences
        preference_prediction = self._predict_from_preferences(file_path, context)
        if preference_prediction:
            predictions.append(preference_prediction)
            confidence_sum += preference_prediction["confidence"]
            reasoning.append(f"User preference: {preference_prediction['reasoning']}")
        
        if not predictions:
            return {
                "predicted_action": {},
                "confidence": 0.0,
                "reasoning": "No learned patterns match this file",
                "pattern_count": 0
            }
        
        # Combine predictions (weighted average)
        combined_action = {}
        total_weight = sum(p["confidence"] for p in predictions)
        
        for prediction in predictions:
            weight = prediction["confidence"] / total_weight if total_weight > 0 else 0
            for key, value in prediction["action"].items():
                if key not in combined_action:
                    combined_action[key] = {"value": value, "weight": weight}
                else:
                    # For conflicting values, keep the one with higher weight
                    if weight > combined_action[key]["weight"]:
                        combined_action[key] = {"value": value, "weight": weight}
        
        final_action = {k: v["value"] for k, v in combined_action.items()}
        average_confidence = confidence_sum / len(predictions) if predictions else 0.0
        
        return {
            "predicted_action": final_action,
            "confidence": min(0.95, average_confidence),  # Cap at 95%
            "reasoning": "; ".join(reasoning),
            "pattern_count": len(predictions),
            "supporting_patterns": [p["pattern_id"] for p in predictions if "pattern_id" in p]
        }

    def _predict_from_filename_patterns(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Predict action based on filename patterns"""
        filename = Path(file_path).name.lower()
        
        features = {
            "extension": Path(file_path).suffix.lower(),
            "contains_numbers": any(c.isdigit() for c in filename),
            "word_count": len(filename.split()),
            "contains_date": self._contains_date_pattern(filename),
            "keywords": self._extract_keywords(filename)
        }
        
        best_match = None
        best_score = 0
        
        for pattern in self.patterns.values():
            if pattern.pattern_type != "filename":
                continue
            
            score = 0
            for key, value in features.items():
                if key in pattern.trigger_conditions and pattern.trigger_conditions[key] == value:
                    score += 1
            
            match_ratio = score / len(pattern.trigger_conditions) if pattern.trigger_conditions else 0
            if match_ratio > 0.7 and match_ratio > best_score:
                best_match = pattern
                best_score = match_ratio
        
        if best_match:
            return {
                "action": best_match.predicted_action,
                "confidence": best_match.confidence * best_score,
                "reasoning": f"Filename matches pattern with {best_score:.1%} similarity",
                "pattern_id": best_match.pattern_id
            }
        
        return None

    def _predict_from_content_patterns(self, content_keywords: List[str]) -> Optional[Dict[str, Any]]:
        """Predict action based on content patterns"""
        if not content_keywords:
            return None
        
        # Generate keyword combinations
        keyword_combos = []
        for i in range(len(content_keywords)):
            for j in range(i+1, min(i+3, len(content_keywords))):
                keyword_combos.append(tuple(sorted([content_keywords[i], content_keywords[j]])))
        
        best_match = None
        best_score = 0
        
        for pattern in self.patterns.values():
            if pattern.pattern_type != "content":
                continue
            
            pattern_combo = pattern.trigger_conditions.get("keyword_combination")
            if pattern_combo and pattern_combo in keyword_combos:
                score = pattern.confidence * pattern.frequency / 10  # Weight by frequency
                if score > best_score:
                    best_match = pattern
                    best_score = score
        
        if best_match:
            return {
                "action": best_match.predicted_action,
                "confidence": min(0.9, best_match.confidence),
                "reasoning": f"Content keywords match learned pattern",
                "pattern_id": best_match.pattern_id
            }
        
        return None

    def _predict_from_location_patterns(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Predict action based on location patterns"""
        source_dir = str(Path(file_path).parent).lower()
        
        location_features = {
            "in_downloads": "downloads" in source_dir,
            "in_desktop": "desktop" in source_dir,
            "in_documents": "documents" in source_dir,
            "in_temp": any(temp in source_dir for temp in ["temp", "tmp", "staging"]),
            "depth": len(Path(file_path).parts)
        }
        
        best_match = None
        best_score = 0
        
        for pattern in self.patterns.values():
            if pattern.pattern_type != "location":
                continue
            
            score = 0
            for key, value in location_features.items():
                if key in pattern.trigger_conditions and pattern.trigger_conditions[key] == value:
                    score += 1
            
            match_ratio = score / len(pattern.trigger_conditions) if pattern.trigger_conditions else 0
            if match_ratio > 0.7 and match_ratio > best_score:
                best_match = pattern
                best_score = match_ratio
        
        if best_match:
            return {
                "action": best_match.predicted_action,
                "confidence": best_match.confidence * best_score,
                "reasoning": f"Location matches pattern with {best_score:.1%} similarity",
                "pattern_id": best_match.pattern_id
            }
        
        return None

    def _predict_from_timing_patterns(self) -> Optional[Dict[str, Any]]:
        """Predict action based on timing patterns"""
        current_time = datetime.now()
        time_features = {
            "hour": current_time.hour,
            "day_of_week": current_time.weekday(),
            "is_weekend": current_time.weekday() >= 5,
            "is_morning": 6 <= current_time.hour <= 12,
            "is_afternoon": 12 < current_time.hour <= 18,
            "is_evening": 18 < current_time.hour <= 23
        }
        
        best_match = None
        best_score = 0
        
        for pattern in self.patterns.values():
            if pattern.pattern_type != "timing":
                continue
            
            score = 0
            for key, value in time_features.items():
                if key in pattern.trigger_conditions and pattern.trigger_conditions[key] == value:
                    score += 1
            
            match_ratio = score / len(pattern.trigger_conditions) if pattern.trigger_conditions else 0
            if match_ratio > 0.8 and match_ratio > best_score:
                best_match = pattern
                best_score = match_ratio
        
        if best_match:
            return {
                "action": best_match.predicted_action,
                "confidence": best_match.confidence * best_score * 0.8,  # Lower weight for timing
                "reasoning": f"Time of day matches learned pattern",
                "pattern_id": best_match.pattern_id
            }
        
        return None

    def _predict_from_preferences(self, file_path: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Predict action based on user preferences"""
        file_features = {
            "file_extension": Path(file_path).suffix.lower(),
            "source_location": str(Path(file_path).parent)
        }
        
        if context and "content_keywords" in context:
            file_features["content_keywords"] = context["content_keywords"][:3]
        
        best_preference = None
        best_score = 0
        
        for pref in self.user_preferences.values():
            # Check if preference is still recent (not decayed)
            days_since_reinforced = (datetime.now() - pref.last_reinforced).days
            if days_since_reinforced > self.config["preference_decay_days"]:
                continue
            
            # Calculate match score
            score = 0
            total_conditions = len(pref.conditions)
            
            for key, value in pref.conditions.items():
                if key in file_features and file_features[key] == value:
                    score += 1
                elif key == "content_keywords" and "content_keywords" in file_features:
                    # Special handling for keyword lists
                    common_keywords = set(value) & set(file_features["content_keywords"])
                    if common_keywords:
                        score += len(common_keywords) / len(value)
            
            match_ratio = score / total_conditions if total_conditions > 0 else 0
            weighted_score = match_ratio * pref.strength * (pref.frequency / 10)
            
            if weighted_score > 0.5 and weighted_score > best_score:
                best_preference = pref
                best_score = weighted_score
        
        if best_preference:
            return {
                "action": best_preference.preferred_action,
                "confidence": min(0.85, best_preference.strength * best_score),
                "reasoning": f"User preference based on {best_preference.frequency} similar decisions",
                "preference_id": best_preference.preference_id
            }
        
        return None

    def _contains_date_pattern(self, text: str) -> bool:
        """Check if text contains date patterns"""
        import re
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'\d{8}',              # YYYYMMDD
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # Month names
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text.lower()):
                return True
        return False

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        import re

        # Remove file extension and common words
        text = re.sub(r'\.[^.]*$', '', text)  # Remove extension
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())  # Words with 3+ chars

        # Filter out common words
        stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy", "did", "man", "men", "put", "say", "she", "too", "use"}

        keywords = [word for word in words if word not in stop_words]
        return keywords[:10]  # Return top 10 keywords

    def _update_visual_patterns_from_classification(self,
                                                   file_path: str,
                                                   category: str,
                                                   features: Dict[str, Any]):
        """
        Update visual patterns from a classification event.
        Integrates with VisionAnalyzer patterns.

        Args:
            file_path: Path to the visual file
            category: Predicted category
            features: Feature dictionary from vision analysis
        """

        # Extract visual features
        visual_objects = features.get('visual_objects', [])
        keywords = features.get('keywords', [])
        scene_type = features.get('scene_type', 'unknown')

        # Update visual pattern storage
        if visual_objects:
            for obj in visual_objects:
                if obj not in self.visual_patterns['objects_detected'][category]:
                    self.visual_patterns['objects_detected'][category].append(obj)

        if keywords:
            for keyword in keywords:
                if keyword not in self.visual_patterns['visual_keywords'][category]:
                    self.visual_patterns['visual_keywords'][category].append(keyword)

        if scene_type != 'unknown':
            if category not in self.visual_patterns['scene_types'][scene_type]:
                self.visual_patterns['scene_types'][scene_type].append(category)

        # Update category frequency
        self.visual_patterns['category_frequencies'][category] += 1

        # Save visual patterns
        try:
            with open(self.visual_patterns_file, 'wb') as f:
                pickle.dump(self.visual_patterns, f)
        except Exception as e:
            self.logger.warning(f"Could not save visual patterns: {e}")

    def _update_audio_patterns_from_classification(self,
                                                   file_path: str,
                                                   category: str,
                                                   features: Dict[str, Any]):
        """
        Update audio patterns from a classification event.
        Integrates with AudioAnalyzer patterns.

        Args:
            file_path: Path to the audio file
            category: Predicted category
            features: Feature dictionary from audio analysis
        """

        # Extract audio features
        bpm = features.get('bpm', 0)
        mood = features.get('mood', 'unknown')
        content_type = features.get('content_type', 'unknown')
        energy_level = features.get('energy_level', 0.0)
        audio_keywords = features.get('audio_keywords', features.get('keywords', []))
        spectral_features = features.get('spectral_features', {})

        # Update BPM ranges by category
        if bpm > 0:
            self.audio_patterns['bpm_ranges'][category].append(bpm)

        # Update mood associations
        if mood != 'unknown':
            if mood not in self.audio_patterns['moods'][category]:
                self.audio_patterns['moods'][category].append(mood)

        # Update content type associations
        if content_type != 'unknown':
            if content_type not in self.audio_patterns['content_types'][category]:
                self.audio_patterns['content_types'][category].append(content_type)

        # Update energy levels
        if energy_level > 0:
            self.audio_patterns['energy_levels'][category].append(energy_level)

        # Update audio keywords
        if audio_keywords:
            for keyword in audio_keywords:
                if keyword not in self.audio_patterns['audio_keywords'][category]:
                    self.audio_patterns['audio_keywords'][category].append(keyword)

        # Update spectral feature patterns
        if spectral_features:
            self.audio_patterns['spectral_features'][category].append(spectral_features)

        # Update category frequency
        self.audio_patterns['category_frequencies'][category] += 1

        # Save audio patterns
        try:
            with open(self.audio_patterns_file, 'wb') as f:
                pickle.dump(self.audio_patterns, f)
        except Exception as e:
            self.logger.warning(f"Could not save audio patterns: {e}")

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of what the system has learned"""
        
        # Calculate recent accuracy
        recent_events = [e for e in self.learning_events if (datetime.now() - e.timestamp).days <= 7]
        accuracy_improvements = [e.confidence_after - e.confidence_before for e in recent_events]
        avg_improvement = sum(accuracy_improvements) / len(accuracy_improvements) if accuracy_improvements else 0.0
        
        # Get most common correction types
        correction_types = Counter(e.event_type for e in self.learning_events[-100:])
        
        # Get active patterns
        active_patterns = [p for p in self.patterns.values() if (datetime.now() - p.last_seen).days <= 30]
        
        # Get strong preferences
        strong_preferences = [p for p in self.user_preferences.values() if p.strength > 0.7]
        
        return {
            "total_learning_events": len(self.learning_events),
            "recent_events_7_days": len(recent_events),
            "patterns_discovered": len(self.patterns),
            "active_patterns": len(active_patterns),
            "preferences_learned": len(self.user_preferences),
            "strong_preferences": len(strong_preferences),
            "average_confidence_improvement": avg_improvement,
            "most_common_corrections": dict(correction_types.most_common(5)),
            "pattern_types": Counter(p.pattern_type for p in self.patterns.values()),
            "preference_types": Counter(p.preference_type for p in self.user_preferences.values()),
            "learning_rate": len(recent_events) / 7 if recent_events else 0,  # Events per day
            "data_freshness": {
                "newest_event": max([e.timestamp for e in self.learning_events]).isoformat() if self.learning_events else None,
                "oldest_event": min([e.timestamp for e in self.learning_events]).isoformat() if self.learning_events else None
            }
        }

    def get_learning_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for the learning system suitable for API exposure.

        Returns detailed statistics about learning events broken down by media type,
        categories, and confidence metrics.

        Returns:
            Dict with keys:
                - total_learning_events: Total number of events
                - image_events: Count of image-origin events
                - video_events: Count of video-origin events
                - audio_events: Count of audio-origin events
                - document_events: Count of document-origin events
                - unique_categories_learned: Number of unique categories
                - most_common_category: Most frequently seen category
                - top_confidence_average: Average confidence of top 10 events
                - media_type_breakdown: Dict mapping media_type to count
                - category_distribution: Dict mapping category to count (top 10)
        """

        # Reload learning events from disk to get latest data from all instances
        self.learning_events = self._load_learning_events()

        if not self.learning_events:
            return {
                "total_learning_events": 0,
                "image_events": 0,
                "video_events": 0,
                "audio_events": 0,
                "document_events": 0,
                "unique_categories_learned": 0,
                "most_common_category": None,
                "top_confidence_average": 0.0,
                "media_type_breakdown": {},
                "category_distribution": {}
            }

        # Count events by media_type
        media_type_counts = Counter()
        categories = Counter()
        confidences = []

        for event in self.learning_events:
            # Extract media_type from context (added in Sprint 2.0 Task 2.4)
            if event.context and 'media_type' in event.context:
                media_type = event.context['media_type']
                media_type_counts[media_type] += 1

            # Extract category from original_prediction
            if event.original_prediction and 'category' in event.original_prediction:
                category = event.original_prediction['category']
                categories[category] += 1

            # Collect confidence scores
            confidences.append(event.confidence_before)

        # Calculate top confidence average (top 10 events by confidence)
        top_confidences = sorted(confidences, reverse=True)[:10]
        top_confidence_avg = sum(top_confidences) / len(top_confidences) if top_confidences else 0.0

        # Get most common category
        most_common = categories.most_common(1)
        most_common_category = most_common[0][0] if most_common else None

        return {
            "total_learning_events": len(self.learning_events),
            "image_events": media_type_counts.get('image', 0),
            "video_events": media_type_counts.get('video', 0),
            "audio_events": media_type_counts.get('audio', 0),
            "document_events": media_type_counts.get('document', 0),
            "unique_categories_learned": len(categories),
            "most_common_category": most_common_category,
            "top_confidence_average": round(top_confidence_avg, 2),
            "media_type_breakdown": dict(media_type_counts),
            "category_distribution": dict(categories.most_common(10))
        }

    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old learning data to prevent memory bloat"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Clean old events
        original_count = len(self.learning_events)
        self.learning_events = [e for e in self.learning_events if e.timestamp > cutoff_date]
        events_removed = original_count - len(self.learning_events)
        
        # Clean old patterns (remove unused ones)
        active_cutoff = datetime.now() - timedelta(days=30)
        patterns_to_remove = [p_id for p_id, pattern in self.patterns.items() 
                            if pattern.last_seen < active_cutoff and pattern.frequency < 5]
        
        for p_id in patterns_to_remove:
            del self.patterns[p_id]
        
        # Clean weak preferences
        weak_prefs = [p_id for p_id, pref in self.user_preferences.items() 
                     if pref.strength < 0.3 and pref.frequency < 3]
        
        for p_id in weak_prefs:
            del self.user_preferences[p_id]
        
        self.logger.info(f"Cleanup removed {events_removed} old events, {len(patterns_to_remove)} inactive patterns, {len(weak_prefs)} weak preferences")
        
        return {
            "events_removed": events_removed,
            "patterns_removed": len(patterns_to_remove),
            "preferences_removed": len(weak_prefs)
        }

# Testing and verification functions
def test_adaptive_learning():
    """Test the adaptive learning system with sample data"""
    print("🧠 Testing Universal Adaptive Learning System...")
    
    # Initialize system
    learning_system = UniversalAdaptiveLearning()
    
    # Test learning event recording
    test_file = "/Users/user/Downloads/Client Name_TV Show_Contract_2024.pdf"
    original_prediction = {
        "category": "documents",
        "confidence": 0.6,
        "location": "/Users/user/Documents/General"
    }
    user_action = {
        "target_category": "entertainment_industry",
        "target_location": "/Users/user/GoogleDrive/AI_Organizer/01_ACTIVE_PROJECTS/Entertainment_Industry/Client Name",
        "associated_person": "Client Name"
    }
    context = {
        "content_keywords": ["contract", "exclusivity", "Client Name", "television", "representation"]
    }
    
    event_id = learning_system.record_learning_event(
        event_type="user_correction",
        file_path=test_file,
        original_prediction=original_prediction,
        user_action=user_action,
        confidence_before=0.6,
        context=context
    )
    
    print(f"✅ Recorded learning event: {event_id}")
    
    # Test prediction
    prediction = learning_system.predict_user_action(test_file, context)
    print(f"📊 Prediction result: {prediction}")
    
    # Test learning summary
    summary = learning_system.get_learning_summary()
    print(f"📈 Learning summary: {summary}")
    
    # Save data
    learning_system.save_all_data()
    print("💾 Saved learning data")
    
    print("🎯 Adaptive learning system test completed!")

if __name__ == "__main__":
    test_adaptive_learning()