"""
AudioAnalyzer - Refactored from AdaptiveAudioOrganizer
A self-contained audio analysis and classification module for intelligent file organization.

This module provides core audio analysis functionality extracted from the AI-Audio-Organizer
with all external dependencies removed for integration with the unified classification system.
"""

import os
import json
import pickle
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

try:
    import mutagen
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("Warning: mutagen not available. Audio metadata extraction will be limited.")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available. AI classification will be disabled.")

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("Warning: librosa not available. Spectral analysis will be disabled.")

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    print("Information: faster-whisper not available. Local transcription disabled.")


class AudioAnalyzer:
    """
    Self-contained audio analysis and classification system.
    
    Provides intelligent audio file analysis with adaptive learning capabilities,
    extracting semantic information from audio files and generating appropriate
    classifications and folder structures.
    """
    
    def __init__(self, 
                 base_dir: str,
                 confidence_threshold: float = 0.7,
                 openai_api_key: Optional[str] = None,
                 learning_data_path: Optional[str] = None,
                 categories_data_path: Optional[str] = None):
        """
        Initialize the AudioAnalyzer with necessary parameters.
        
        Args:
            base_dir: Base directory for file operations
            confidence_threshold: Minimum confidence for classifications (0.0-1.0)
            openai_api_key: Optional OpenAI API key for AI classification
            learning_data_path: Path to learning data file (optional)
            categories_data_path: Path to discovered categories file (optional)
        """
        self.base_dir = Path(base_dir)
        self.confidence_threshold = confidence_threshold
        
        # OpenAI client setup
        self.client = None
        if openai_api_key and OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=openai_api_key)
        
        # Local Whisper initialization
        self.local_whisper = None
        self.use_local_whisper = FASTER_WHISPER_AVAILABLE
        
        # Learning system files
        from gdrive_integration import get_metadata_root
        metadata_dir = get_metadata_root()
        self.learning_data_file = Path(learning_data_path) if learning_data_path else metadata_dir / "learning_data.pkl"
        self.discovered_categories_file = Path(categories_data_path) if categories_data_path else metadata_dir / "discovered_categories.json"
        
        # Load existing learning data
        self.learning_data = self.load_learning_data()
        self.discovered_categories = self.load_discovered_categories()
        
        # Base categories from Golden Taxonomy V3
        self.base_categories = {
            "audio_vox": ["contemplative", "melancholic", "mysterious", "dramatic_punctuation"],
            "audio_sfx": ["subtle_background", "narrative_support", "dramatic_punctuation"],
            "audio_music": ["contemplative", "tension_building", "wonder_discovery", "melancholic", "mysterious"],
        }
        
        # Dynamic folder mapping that grows over time
        self.folder_map = self.build_dynamic_folder_map()
        self.audio_extensions = {'.mp3', '.wav', '.aiff', '.m4a', '.flac', '.ogg', '.wma'}
    
    def load_learning_data(self) -> Dict[str, Any]:
        """Load historical classification data"""
        if self.learning_data_file.exists():
            try:
                with open(self.learning_data_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load learning data: {e}")
        
        return {
            'classifications': [],
            'user_corrections': [],
            'patterns': defaultdict(list),
            'filename_patterns': defaultdict(list)
        }
    
    def save_learning_data(self) -> None:
        """Save learning data for future use"""
        try:
            self.learning_data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.learning_data_file, 'wb') as f:
                pickle.dump(self.learning_data, f)
        except Exception as e:
            print(f"Warning: Could not save learning data: {e}")
    
    def load_discovered_categories(self) -> Dict[str, Any]:
        """Load dynamically discovered categories"""
        if self.discovered_categories_file.exists():
            try:
                with open(self.discovered_categories_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load discovered categories: {e}")
        
        return {
            'new_moods': [],
            'new_categories': [],
            'new_themes': [],
            'frequency_counts': defaultdict(int)
        }
    
    def save_discovered_categories(self) -> None:
        """Save discovered categories"""
        try:
            self.discovered_categories_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.discovered_categories_file, 'w') as f:
                json.dump(self.discovered_categories, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save discovered categories: {e}")
    
    def build_dynamic_folder_map(self) -> Dict[str, str]:
        """Build folder mapping that includes discovered categories"""
        base_map = {
            "music_ambient_contemplative": "01_UNIVERSAL_ASSETS/MUSIC_LIBRARY/by_mood/contemplative/",
            "music_ambient_tension_building": "01_UNIVERSAL_ASSETS/MUSIC_LIBRARY/by_mood/tension_building/",
            "music_ambient_wonder_discovery": "01_UNIVERSAL_ASSETS/MUSIC_LIBRARY/by_mood/wonder_discovery/",
            "music_ambient_melancholic": "01_UNIVERSAL_ASSETS/MUSIC_LIBRARY/by_mood/melancholic/",
            "music_ambient_mysterious": "01_UNIVERSAL_ASSETS/MUSIC_LIBRARY/by_mood/mysterious/",
            "sfx_consciousness_subtle_background": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/consciousness/thought_processing/",
            "sfx_consciousness_narrative_support": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/consciousness/awakening_emergence/",
            "sfx_consciousness_dramatic_punctuation": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/consciousness/memory_formation/",
            "sfx_human_subtle_background": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/human_elements/breathing_heartbeat/",
            "sfx_human_narrative_support": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/human_elements/emotional_responses/",
            "sfx_human_dramatic_punctuation": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/human_elements/environmental_human/",
            "sfx_environmental_subtle_background": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/abstract_conceptual/time_space/",
            "sfx_environmental_narrative_support": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/abstract_conceptual/transformation/",
            "sfx_environmental_dramatic_punctuation": "01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/abstract_conceptual/connection_bridging/",
            "voice_element_contemplative": "01_UNIVERSAL_ASSETS/VOICE_ELEMENTS/narrator_banks/",
            "voice_element_melancholic": "01_UNIVERSAL_ASSETS/VOICE_ELEMENTS/processed_vocals/",
            "voice_element_mysterious": "01_UNIVERSAL_ASSETS/VOICE_ELEMENTS/vocal_textures/",
            "voice_element_dramatic_punctuation": "01_UNIVERSAL_ASSETS/VOICE_ELEMENTS/character_voices/",
            "default": "01_UNIVERSAL_ASSETS/UNSORTED/"
        }
        
        # Add discovered categories
        for category in self.discovered_categories.get('new_categories', []):
            for mood in self.discovered_categories.get('new_moods', []):
                key = f"{category}_{mood}"
                if key not in base_map:
                    # Create new folder path based on category type
                    if category.startswith('music_'):
                        base_map[key] = f"01_UNIVERSAL_ASSETS/MUSIC_LIBRARY/by_mood/{mood}/"
                    elif category.startswith('sfx_'):
                        sfx_type = category.replace('sfx_', '')
                        base_map[key] = f"01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/{sfx_type}/{mood}/"
                    elif category.startswith('voice_'):
                        base_map[key] = f"01_UNIVERSAL_ASSETS/VOICE_ELEMENTS/{mood}/"
                    else:
                        base_map[key] = f"01_UNIVERSAL_ASSETS/EXPERIMENTAL/{category}/{mood}/"
        
        return base_map
    
    def get_audio_metadata(self, file_path: Path) -> Dict[str, str]:
        """Extract audio metadata using mutagen"""
        if not MUTAGEN_AVAILABLE:
            return {'duration': 'Unknown', 'bitrate': 'Unknown', 'sample_rate': 'Unknown'}

        try:
            audio_file = mutagen.File(file_path)
            if audio_file is not None:
                duration = audio_file.info.length
                return {
                    'duration': f"{int(duration // 60)}:{int(duration % 60):02d}",
                    'duration_seconds': duration,
                    'bitrate': getattr(audio_file.info, 'bitrate', 'Unknown'),
                    'sample_rate': getattr(audio_file.info, 'sample_rate', 'Unknown')
                }
        except Exception as e:
            print(f"Could not read metadata for {file_path}: {e}")

        return {'duration': 'Unknown', 'duration_seconds': 0, 'bitrate': 'Unknown', 'sample_rate': 'Unknown'}

    def analyze_audio_spectral(self, file_path: Path, max_duration: int = 120) -> Dict[str, Any]:
        """
        Perform spectral analysis on audio file using librosa

        Args:
            file_path: Path to audio file
            max_duration: Maximum duration to analyze in seconds (default 120s/2mins per user request)

        Returns:
            Dictionary with spectral features including BPM, energy, brightness, etc.
        """
        if not LIBROSA_AVAILABLE:
            return {
                'success': False,
                'error': 'librosa not available',
                'bpm': 0,
                'energy_level': 0.0,
                'spectral_features': {}
            }

        try:
            # Smart sampling: Analyze the middle of the track for better representation
            total_duration = librosa.get_duration(path=str(file_path))
            
            offset = 0.0
            if total_duration > max_duration:
                # Start from the middle (minus half duration to center it)
                offset = (total_duration - max_duration) / 2
                print(f"🎵 Analyzying {max_duration}s slice from {offset:.1f}s (Total: {total_duration:.1f}s)")
            
            # Load audio file from calculated offset
            y, sr = librosa.load(str(file_path), offset=offset, duration=max_duration, sr=None)

            # Detect BPM (tempo)
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(tempo)

            # Calculate spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]

            # Calculate RMS energy
            rms = librosa.feature.rms(y=y)[0]

            # Separate harmonic and percussive components
            y_harmonic, y_percussive = librosa.effects.hpss(y)

            # Calculate harmonic/percussive ratio
            harmonic_energy = np.sum(y_harmonic ** 2)
            percussive_energy = np.sum(y_percussive ** 2)
            total_energy = harmonic_energy + percussive_energy
            harmonic_ratio = harmonic_energy / total_energy if total_energy > 0 else 0

            # Determine brightness (high frequency content)
            brightness = float(np.mean(spectral_centroids))
            brightness_normalized = min(1.0, brightness / 4000.0)  # Normalize to 0-1

            # Determine texture based on spectral features
            texture = self._determine_texture(
                spectral_bandwidth=np.mean(spectral_bandwidth),
                zero_crossing_rate=np.mean(zero_crossing_rate),
                harmonic_ratio=harmonic_ratio
            )

            # Calculate energy level (0.0 to 1.0)
            energy_level = float(np.mean(rms))
            energy_level_normalized = min(1.0, energy_level * 10)  # Normalize

            # Calculate energy level as 0-10 scale
            energy_level_scale = int(energy_level_normalized * 10)

            # Determine mood based on spectral features
            mood = self._determine_mood_from_spectral(
                bpm=bpm,
                energy_level=energy_level_normalized,
                brightness=brightness_normalized,
                harmonic_ratio=harmonic_ratio
            )

            # Determine content type (music vs SFX vs voice)
            content_type = self._determine_content_type(
                harmonic_ratio=harmonic_ratio,
                zero_crossing_rate=np.mean(zero_crossing_rate),
                spectral_centroid=brightness
            )

            return {
                'success': True,
                'bpm': bpm,
                'energy_level': energy_level_normalized,
                'energy_level_scale': energy_level_scale,
                'mood': mood,
                'content_type': content_type,
                'spectral_features': {
                    'brightness': brightness,
                    'brightness_normalized': brightness_normalized,
                    'texture': texture,
                    'harmonic_ratio': harmonic_ratio,
                    'spectral_centroid_mean': float(np.mean(spectral_centroids)),
                    'spectral_rolloff_mean': float(np.mean(spectral_rolloff)),
                    'spectral_bandwidth_mean': float(np.mean(spectral_bandwidth)),
                    'zero_crossing_rate_mean': float(np.mean(zero_crossing_rate)),
                    'rms_energy_mean': float(np.mean(rms))
                },
                'analysis_duration': max_duration
            }

        except Exception as e:
            print(f"Spectral analysis failed for {file_path.name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'bpm': 0,
                'energy_level': 0.0,
                'spectral_features': {}
            }

    def _determine_texture(self, spectral_bandwidth: float, zero_crossing_rate: float, harmonic_ratio: float) -> str:
        """Determine audio texture based on spectral features"""
        if harmonic_ratio > 0.7:
            if spectral_bandwidth < 1000:
                return 'smooth'
            else:
                return 'rich'
        elif harmonic_ratio < 0.3:
            if zero_crossing_rate > 0.1:
                return 'rough'
            else:
                return 'percussive'
        else:
            return 'mixed'

    def _determine_mood_from_spectral(self, bpm: float, energy_level: float, brightness: float, harmonic_ratio: float) -> str:
        """Determine mood based on spectral analysis"""
        # High energy, fast tempo
        if energy_level > 0.7 and bpm > 140:
            return 'energetic'

        # High energy, moderate tempo
        elif energy_level > 0.6 and bpm > 100:
            return 'uplifting'

        # Low energy, slow tempo, dark
        elif energy_level < 0.4 and bpm < 90 and brightness < 0.4:
            return 'contemplative'

        # Low energy, slow tempo, bright
        elif energy_level < 0.4 and bpm < 90 and brightness > 0.5:
            return 'calm'

        # Moderate energy, dissonant (low harmonic ratio)
        elif harmonic_ratio < 0.4 and energy_level > 0.5:
            return 'tense'

        # Low harmonic, slow
        elif harmonic_ratio < 0.5 and bpm < 100:
            return 'mysterious'

        # Moderate tempo, moderate energy
        elif 90 <= bpm <= 130 and 0.4 <= energy_level <= 0.6:
            return 'melancholic'

        else:
            return 'ambient'

    def _determine_content_type(self, harmonic_ratio: float, zero_crossing_rate: float, spectral_centroid: float) -> str:
        """Determine content type (music, SFX, voice, ambient) based on spectral features"""
        # Voice typically has specific harmonic characteristics
        if 0.5 < harmonic_ratio < 0.8 and 1500 < spectral_centroid < 3500:
            return 'voice'

        # Music typically has high harmonic content
        elif harmonic_ratio > 0.6:
            return 'music'

        # SFX typically has high zero-crossing rate and low harmonic ratio
        elif zero_crossing_rate > 0.15 or harmonic_ratio < 0.3:
            return 'sfx'

        # Ambient/atmospheric
        else:
            return 'ambient'
    
    def analyze_filename_patterns(self, filename: str) -> List[str]:
        """Extract patterns from filename that might indicate content type"""
        patterns = []
        filename_lower = filename.lower()
        
        # Common audio descriptors
        descriptors = {
            'ambient': ['ambient', 'atmosphere', 'atmos', 'background', 'bg'],
            'percussion': ['drum', 'beat', 'perc', 'rhythm', 'kick', 'snare'],
            'vocal': ['vocal', 'voice', 'speech', 'talk', 'narr', 'dialogue'],
            'nature': ['nature', 'wind', 'rain', 'water', 'forest', 'bird'],
            'mechanical': ['mech', 'robot', 'machine', 'tech', 'digital', 'synth'],
            'emotional': ['sad', 'happy', 'dark', 'bright', 'calm', 'tense'],
            'temporal': ['intro', 'outro', 'loop', 'oneshot', 'sustained']
        }
        
        for category, keywords in descriptors.items():
            if any(keyword in filename_lower for keyword in keywords):
                patterns.append(category)
        
        return patterns
    
    def find_similar_files(self, filename: str) -> List[Dict[str, Any]]:
        """Find similar files in learning data"""
        similar = []
        for entry in self.learning_data['classifications']:
            similarity = self.filename_similarity(filename, entry['filename'])
            if similarity > 0.3:
                entry_with_similarity = entry.copy()
                entry_with_similarity['similarity'] = similarity
                similar.append(entry_with_similarity)
        
        # Sort by similarity and return top 5
        similar.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return similar[:5]
    
    def filename_similarity(self, filename1: str, filename2: str) -> float:
        """Calculate similarity between filenames"""
        # Simple word-based similarity
        words1 = set(filename1.lower().replace('_', ' ').replace('-', ' ').split())
        words2 = set(filename2.lower().replace('_', ' ').replace('-', ' ').split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def _init_local_whisper(self):
        """Lazy initialization of the local Whisper model"""
        if self.local_whisper is None and self.use_local_whisper:
            try:
                print("🧠 Loading local faster-whisper model (base)...")
                # Using 'base' for a good balance of speed and accuracy on Mac
                # device="cpu" is safest, compute_type="int8" for efficiency
                self.local_whisper = WhisperModel("base", device="cpu", compute_type="int8")
                print("✅ Local Whisper model loaded.")
            except Exception as e:
                print(f"⚠️ Failed to load local Whisper model: {e}")
                self.use_local_whisper = False
        return self.local_whisper

    def transcribe_audio(self, file_path: Path, project_context: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio using local faster-whisper with OpenAI fallback.
        Returns the full transcript or None if failed.
        """
        # 1. Try local transcription first
        if self.use_local_whisper:
            try:
                model = self._init_local_whisper()
                if model:
                    print(f"🎙️  Transcribing LOCALLY with faster-whisper: {file_path.name}")
                    
                    # initial_prompt helps with context
                    initial_prompt = project_context if project_context else None
                    
                    segments, info = model.transcribe(str(file_path), initial_prompt=initial_prompt, beam_size=5)
                    
                    transcript = "".join([segment.text for segment in segments])
                    return transcript.strip()
            except Exception as e:
                print(f"⚠️ Local transcription failed: {e}. Falling back to API.")

        # 2. Fallback to OpenAI API
        if not self.client:
            return None

        try:
            print(f"🎙️  Transcribing with OpenAI API: {file_path.name}")
            
            # Use project context as a prompt to Whisper to improve name/domain accuracy
            prompt = None
            if project_context:
                prompt = f"Context: {project_context}. Character names and specific terminology should be prioritized."

            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    prompt=prompt,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            print(f"⚠️ OpenAI Transcription failed: {e}")
            return None

    def _retry_openai_call(self, func, *args, max_retries=3, initial_delay=2, **kwargs):
        """Execute an OpenAI call with exponential backoff for rate limits"""
        import time
        import random
        from openai import RateLimitError
        
        retries = 0
        while retries <= max_retries:
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                if retries == max_retries:
                    raise
                
                # Exponential backoff with jitter
                delay = initial_delay * (2 ** retries) + random.uniform(0, 1)
                print(f"⚠️ Rate limited. Retrying in {delay:.2f}s (Attempt {retries + 1}/{max_retries})...")
                time.sleep(delay)
                retries += 1
            except Exception as e:
                # Other errors shouldn't necessarily be retried the same way
                print(f"❌ OpenAI Call Error: {e}")
                raise
    
    def build_adaptive_prompt(self, file_path: Path, metadata: Dict[str, str], transcript: Optional[str] = None) -> str:
        """Build a prompt that learns from previous classifications"""
        
        # Analyze filename patterns
        filename_patterns = self.analyze_filename_patterns(file_path.name)
        
        # Get historical context
        similar_files = self.find_similar_files(file_path.name)
        
        # Build dynamic categories list
        all_categories = list(self.base_categories.keys()) + self.discovered_categories.get('new_categories', [])
        all_moods = []
        for cat_moods in self.base_categories.values():
            all_moods.extend(cat_moods)
        all_moods.extend(self.discovered_categories.get('new_moods', []))
        all_moods = list(set(all_moods))  # Remove duplicates
        
        try:
            file_stats = os.stat(file_path)
            file_size_mb = file_stats.st_size / (1024 * 1024)
        except Exception:
            file_size_mb = 0
        
        context = ""
        if similar_files:
            context = f"\nCONTEXT from similar files:\n"
            for similar in similar_files[:3]:
                classification = similar.get('classification', {})
                context += f"- {similar['filename']}: {classification.get('category', 'unknown')}_{classification.get('mood', 'unknown')}\n"
        
        if filename_patterns:
            context += f"\nFILENAME PATTERNS detected: {', '.join(filename_patterns)}\n"

        if transcript:
            context += f"\n🎙️ AUDIO TRANSCRIPT (Voice/Dialogue):\n\"\"\"\n{transcript}\n\"\"\"\n"
        
        prompt = f"""You are an expert audio librarian with adaptive learning capabilities. Analyze this audio file and classify it, considering both standard categories and potentially discovering new ones.

AUDIO DETAILS:
- Filename: {file_path.name}
- Duration: {metadata['duration']}
- File size: {file_size_mb:.2f} MB
- File type: {file_path.suffix}
{context}

CLASSIFICATION FRAMEWORK:

CONTENT CATEGORIES (choose existing or suggest new):
Existing: {', '.join(all_categories)}
- If this doesn't fit existing categories, suggest a new category in format: category_newname

PRIMARY MOODS (choose existing or suggest new):
Existing: {', '.join(all_moods)}
- If this doesn't fit existing moods, suggest a new mood

INTENSITY LEVELS:
- subtle_background: Unobtrusive, atmospheric support
- narrative_support: Clear presence but supports story
- dramatic_punctuation: Bold, attention-grabbing moments

LEARNING INSTRUCTIONS:
- Be creative and specific in your classifications
- If you detect patterns that don't fit existing categories, suggest new ones
- Consider the creative context of AI consciousness storytelling
- Use filename patterns as clues but don't be limited by them

Return response as JSON:
{{
  "category": "existing_category_or_new_category",
  "mood": "existing_mood_or_new_mood",
  "intensity": "subtle_background|narrative_support|dramatic_punctuation",
  "energy_level": 1-10,
  "tags": ["tag1", "tag2", "tag3"],
  "thematic_notes": "How this could enhance AI consciousness storytelling",
  "suggested_filename": "descriptive_filename",
  "confidence": 0.0-1.0,
  "reasoning": "Why you chose these classifications",
  "discovered_elements": ["any new patterns or categories you noticed"]
}}"""
        
        return prompt
    
    def learn_from_classification(self, file_path: Path, classification: Dict[str, Any]) -> None:
        """Learn from each classification to improve future ones"""
        
        # Store classification
        learning_entry = {
            'filename': file_path.name,
            'classification': classification,
            'timestamp': datetime.now().isoformat(),
            'file_path': str(file_path)
        }
        
        self.learning_data['classifications'].append(learning_entry)
        
        # Track new categories/moods
        category = classification.get('category', '')
        mood = classification.get('mood', '')
        
        # Check for new categories
        if category not in [cat for cats in self.base_categories.keys() for cat in cats]:
            if category not in self.discovered_categories['new_categories']:
                self.discovered_categories['new_categories'].append(category)
                print(f"🆕 Discovered new category: {category}")
        
        # Check for new moods
        all_base_moods = [mood for moods in self.base_categories.values() for mood in moods]
        if mood not in all_base_moods:
            if mood not in self.discovered_categories['new_moods']:
                self.discovered_categories['new_moods'].append(mood)
                print(f"🆕 Discovered new mood: {mood}")
        
        # Update frequency counts
        self.discovered_categories['frequency_counts'][f"{category}_{mood}"] += 1
        
        # Learn filename patterns
        filename_patterns = self.analyze_filename_patterns(file_path.name)
        for pattern in filename_patterns:
            self.learning_data['filename_patterns'][pattern].append({
                'category': category,
                'mood': mood,
                'filename': file_path.name
            })
        
        # Save learning data
        self.save_learning_data()
        self.save_discovered_categories()
        
        # Rebuild folder map with new discoveries
        self.folder_map = self.build_dynamic_folder_map()
    
    def classify_audio_file(self, file_path: Path, user_description: str = "", project_context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Classify audio file with adaptive learning and Whisper transcription"""
        
        if not self.client:
            print("Warning: OpenAI client not available. Cannot perform AI classification.")
            return None
        
        metadata = self.get_audio_metadata(file_path)
        
        # 1. New: High-Fidelity Transcription with Context
        transcript = self.transcribe_audio(file_path, project_context=project_context)
        
        # 2. Build prompt with transcript context
        prompt = self.build_adaptive_prompt(file_path, metadata, transcript)
        
        try:
            response = self._retry_openai_call(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,  # Slightly higher for more creativity
                timeout=15.0  # Prevent indefinite hangs
            )
            
            raw_response = response.choices[0].message.content.strip()
            
            # Handle markdown-wrapped JSON or plain code blocks
            if '```' in raw_response:
                # Extract content inside code blocks
                import re
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_response, re.DOTALL)
                if match:
                    raw_response = match.group(1)
            
            try:
                classification = json.loads(raw_response)
            except json.JSONDecodeError:
                # Fallback: Try to find valid JSON object
                start = raw_response.find('{')
                end = raw_response.rfind('}')
                if start != -1 and end != -1:
                    try:
                        classification = json.loads(raw_response[start:end+1])
                    except:
                        # Fallback 2: Treat as raw category string if it looks like one
                        print(f"⚠️ JSON parsing failed. raw response: {raw_response[:50]}...")
                        classification = {
                            "category": "unknown",
                            "mood": "unknown",
                            "reasoning": f"AI Parsing failed. Raw: {raw_response[:100]}"
                        }
                else:
                    classification = {
                        "category": "unknown",
                        "mood": "unknown",
                        "reasoning": f"AI returned non-JSON: {raw_response[:100]}"
                    }

            # Inject transcript into classification for sidecar persistence
            if transcript:
                classification['transcript'] = transcript

            # Learn from this classification
            self.learn_from_classification(file_path, classification)
            
            return classification
            
        except Exception as e:
            print(f"Classification failed: {e}")
            return None
    
    def determine_target_folder(self, classification: Optional[Dict[str, Any]]) -> str:
        """Determine target folder, creating new ones if needed"""
        if not classification:
            return self.folder_map["default"]
        
        category = classification.get('category', '')
        mood = classification.get('mood', '')
        intensity = classification.get('intensity', '')
        
        
        # Determine the best identifying tag (mood or intensity)
        descriptor = mood if mood and mood != 'unknown' else intensity
        
        # Construct key, avoiding redundancy
        if descriptor and descriptor != 'unknown':
            if descriptor in category: # Avoid "mysterious + mysterious"
                 key = category
            else:
                 key = f"{category}_{descriptor}"
        else:
            key = category

        if key in self.folder_map:
            return self.folder_map[key]
        
        # Create new folder path for discovered categories
        if category.startswith('music_'):
            new_path = f"01_UNIVERSAL_ASSETS/MUSIC_LIBRARY/by_mood/{mood}/"
        elif category.startswith('sfx_'):
            sfx_type = category.replace('sfx_', '')
            new_path = f"01_UNIVERSAL_ASSETS/SFX_LIBRARY/by_category/{sfx_type}/{mood}/"
        elif category.startswith('voice_'):
            new_path = f"01_UNIVERSAL_ASSETS/VOICE_ELEMENTS/{mood}/"
        else:
            new_path = f"01_UNIVERSAL_ASSETS/EXPERIMENTAL/{category}/{mood}/"
        
        # Add to folder map
        self.folder_map[key] = new_path
        print(f"🆕 Created new folder mapping: {key} → {new_path}")
        
        return new_path
    
    def process_file(self, file_path: Path, user_description: str = "", dry_run: bool = True) -> Optional[Dict[str, Any]]:
        """Process file with adaptive learning and return classification results"""
        print(f"\n🔍 Processing: {file_path.name}")
        
        # Check if file is an audio file
        if file_path.suffix.lower() not in self.audio_extensions:
            print(f"  ⚠️  Not an audio file: {file_path.suffix}")
            return None
        
        classification = self.classify_audio_file(file_path, user_description)
        
        if classification:
            target_folder = self.determine_target_folder(classification)
            
            print(f"  📂 Category: {classification.get('category', 'unknown')}")
            print(f"  🎭 Mood: {classification.get('mood', 'unknown')}")
            print(f"  ⚡ Intensity: {classification.get('intensity', 'unknown')}")
            print(f"  🔥 Energy: {classification.get('energy_level', 0)}/10")
            print(f"  🎯 Confidence: {classification.get('confidence', 0):.1%}")
            print(f"  📍 Target: {target_folder}")
            print(f"  🏷️ Tags: {', '.join(classification.get('tags', []))}")
            
            if classification.get('discovered_elements'):
                print(f"  🆕 Discovered: {', '.join(classification.get('discovered_elements', []))}")
            
            # Add target folder to classification result
            classification['target_folder'] = target_folder
            classification['original_path'] = str(file_path)
            
            if not dry_run:
                print(f"  ✅ Would move to: {target_folder}")
            else:
                print(f"  🔄 [DRY RUN] Would move to: {target_folder}")
            
            return classification
        else:
            print(f"  ❌ Classification failed")
            return None
    
    def show_learning_stats(self) -> None:
        """Display learning statistics"""
        print(f"\n📊 AUDIO ANALYZER LEARNING STATISTICS")
        print(f"=" * 50)
        
        total_files = len(self.learning_data['classifications'])
        print(f"Total files processed: {total_files}")
        
        print(f"\n🆕 DISCOVERED CATEGORIES:")
        for category in self.discovered_categories.get('new_categories', []):
            print(f"  - {category}")
        
        print(f"\n🆕 DISCOVERED MOODS:")
        for mood in self.discovered_categories.get('new_moods', []):
            print(f"  - {mood}")
        
        print(f"\n📈 MOST COMMON COMBINATIONS:")
        freq_counts = self.discovered_categories.get('frequency_counts', {})
        for combo, count in sorted(freq_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {combo}: {count} files")
        
        print(f"\n🔍 FILENAME PATTERNS LEARNED:")
        for pattern, examples in list(self.learning_data['filename_patterns'].items())[:5]:
            print(f"  - {pattern}: {len(examples)} examples")
    
    def is_audio_file(self, file_path: Path) -> bool:
        """Check if file is an audio file based on extension"""
        return file_path.suffix.lower() in self.audio_extensions
    
    def get_classification_summary(self, classification: Dict[str, Any]) -> str:
        """Generate a human-readable summary of classification results"""
        if not classification:
            return "No classification available"
        
        category = classification.get('category', 'unknown')
        mood = classification.get('mood', 'unknown')
        confidence = classification.get('confidence', 0)
        energy = classification.get('energy_level', 0)
        
        return f"{category} ({mood}) - Confidence: {confidence:.1%}, Energy: {energy}/10"


if __name__ == "__main__":
    # Basic usage example
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audio_analyzer.py <audio_file_path> [openai_api_key]")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not file_path.exists():
        print(f"Error: File {file_path} not found")
        sys.exit(1)
    
    # Initialize analyzer
    analyzer = AudioAnalyzer(
        base_dir=str(file_path.parent),
        confidence_threshold=0.7,
        openai_api_key=api_key
    )
    
    # Process the file
    result = analyzer.process_file(file_path, dry_run=True)
    
    if result:
        print(f"\n✅ Analysis complete!")
        print(f"Summary: {analyzer.get_classification_summary(result)}")
    else:
        print(f"\n❌ Analysis failed")