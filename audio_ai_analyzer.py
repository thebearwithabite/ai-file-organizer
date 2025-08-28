#!/usr/bin/env python3
"""
Audio AI Analysis System for AI File Organizer
Complete integration of AudioAI capabilities with librosa for intelligent audio analysis
Analyzes audio content for organization, transcription, and creative workflow optimization
"""

import sys
import os
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import sqlite3
import hashlib
import warnings
warnings.filterwarnings('ignore')

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Audio processing imports
try:
    import librosa
    import librosa.display
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

@dataclass
class AudioAnalysis:
    """Comprehensive audio analysis results"""
    file_path: Path
    file_size_mb: float
    duration_seconds: float
    
    # Technical audio characteristics
    sample_rate: int
    channels: int
    bit_depth: Optional[int] = None
    bitrate: Optional[int] = None
    codec: Optional[str] = None
    
    # Audio quality assessment
    audio_quality: str = "unknown"  # excellent, good, fair, poor
    noise_level: float = 0.0  # 0-1 scale
    dynamic_range: float = 0.0
    
    # Content type classification
    content_type: str = "unknown"  # speech, music, interview, scene, ambient, mixed
    confidence_score: float = 0.0
    
    # Speech analysis
    has_speech: bool = False
    speech_segments: List[Tuple[float, float]] = None  # (start, end) times
    estimated_speakers: int = 0
    speech_clarity: float = 0.0  # 0-1 scale
    transcription: Optional[str] = None
    
    # Music analysis  
    has_music: bool = False
    tempo: Optional[float] = None
    key: Optional[str] = None
    energy: float = 0.0
    danceability: float = 0.0
    
    # Creative workflow tags
    creative_tags: List[str] = None
    project_context: Optional[str] = None
    suggested_category: Optional[str] = None
    
    # Organization metadata
    importance_score: float = 0.0
    auto_tags: List[str] = None
    analyzed_date: datetime = None

class AudioAIAnalyzer:
    """
    Advanced audio analysis system combining AudioAI patterns with librosa
    Provides intelligent audio file organization for creative workflows
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.audio_ai_dir = self.base_dir / "04_METADATA_SYSTEM" / "audio_ai_analysis"
        self.audio_ai_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for audio analysis
        self.db_path = self.audio_ai_dir / "audio_ai_analysis.db"
        self._init_audio_db()
        
        # Supported audio formats
        self.supported_formats = {
            '.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', 
            '.wma', '.aiff', '.au', '.mp2', '.opus'
        }
        
        # Content type classifiers
        self.content_classifiers = {
            'interview': {
                'speech_ratio_min': 0.8,
                'music_ratio_max': 0.2,
                'speaker_count': (2, 5),
                'duration_range': (300, 7200),  # 5 minutes to 2 hours
                'filename_keywords': ['interview', 'conversation', 'discussion', 'talk', 'podcast']
            },
            'music': {
                'music_ratio_min': 0.7,
                'has_rhythm': True,
                'tempo_range': (60, 200),
                'duration_range': (30, 600),  # 30 seconds to 10 minutes
                'filename_keywords': ['music', 'song', 'track', 'beat', 'instrumental']
            },
            'voice_sample': {
                'speech_ratio_min': 0.9,
                'single_speaker': True,
                'duration_range': (5, 180),  # 5 seconds to 3 minutes
                'filename_keywords': ['voice', 'sample', 'audition', 'read', 'monologue']
            },
            'scene_audio': {
                'mixed_content': True,
                'has_dialogue': True,
                'has_background': True,
                'duration_range': (60, 1800),  # 1 to 30 minutes
                'filename_keywords': ['scene', 'take', 'footage', 'clip', 'recording']
            },
            'ambient': {
                'speech_ratio_max': 0.1,
                'music_ratio_max': 0.3,
                'low_energy': True,
                'filename_keywords': ['ambient', 'background', 'atmosphere', 'room', 'tone']
            }
        }
        
        # Creative project patterns
        self.project_patterns = {
            'stranger_things': ['stranger', 'things', 'hawkins', 'eleven', 'upside', 'down'],
            'creative_project': ['creative', 'project', 'consciousness', 'ai', 'podcast'],
            'client_work': ['client', 'management', 'talent', 'representation'],
            'personal': ['personal', 'own', 'test', 'demo', 'practice']
        }
        
        # Initialize speech recognizer if available
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
    
    def _init_audio_db(self):
        """Initialize SQLite database for audio analysis"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audio_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_name TEXT,
                    file_hash TEXT,
                    file_size_mb REAL,
                    duration_seconds REAL,
                    
                    -- Technical characteristics
                    sample_rate INTEGER,
                    channels INTEGER,
                    bit_depth INTEGER,
                    bitrate INTEGER,
                    codec TEXT,
                    
                    -- Quality metrics
                    audio_quality TEXT,
                    noise_level REAL,
                    dynamic_range REAL,
                    
                    -- Content classification
                    content_type TEXT,
                    confidence_score REAL,
                    
                    -- Speech analysis
                    has_speech BOOLEAN,
                    speech_segments TEXT,  -- JSON
                    estimated_speakers INTEGER,
                    speech_clarity REAL,
                    transcription TEXT,
                    
                    -- Music analysis
                    has_music BOOLEAN,
                    tempo REAL,
                    music_key TEXT,
                    energy REAL,
                    danceability REAL,
                    
                    -- Organization
                    creative_tags TEXT,  -- JSON
                    project_context TEXT,
                    suggested_category TEXT,
                    importance_score REAL,
                    auto_tags TEXT,  -- JSON
                    
                    -- Metadata
                    analyzed_date TEXT,
                    analysis_version TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audio_transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    transcript_text TEXT,
                    confidence REAL,
                    language TEXT,
                    speaker_segments TEXT,  -- JSON
                    created_date TEXT,
                    FOREIGN KEY (file_path) REFERENCES audio_analysis (file_path)
                )
            """)
            
            conn.commit()
    
    def analyze_audio_file(self, file_path: Path) -> AudioAnalysis:
        """Perform comprehensive audio analysis"""
        
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        if file_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {file_path.suffix}")
        
        print(f"🎵 Analyzing audio: {file_path.name}")
        
        # Initialize analysis object
        analysis = AudioAnalysis(
            file_path=file_path,
            file_size_mb=file_path.stat().st_size / (1024 * 1024),
            duration_seconds=0.0,
            sample_rate=0,
            channels=0,
            speech_segments=[],
            creative_tags=[],
            auto_tags=[],
            analyzed_date=datetime.now()
        )
        
        try:
            # Load audio file
            if LIBROSA_AVAILABLE:
                y, sr = librosa.load(str(file_path), sr=None)
                analysis.sample_rate = sr
                analysis.duration_seconds = len(y) / sr
                analysis.channels = 1  # librosa loads as mono by default
                
                # Perform detailed audio analysis
                self._analyze_audio_characteristics(analysis, y, sr)
                self._classify_content_type(analysis, y, sr)
                self._extract_speech_features(analysis, y, sr)
                self._extract_music_features(analysis, y, sr)
                
            else:
                print("⚠️  librosa not available - using basic analysis")
                self._basic_audio_analysis(analysis)
            
            # Generate creative tags and suggestions
            self._generate_creative_tags(analysis)
            self._determine_project_context(analysis)
            self._calculate_importance_score(analysis)
            
        except Exception as e:
            print(f"❌ Error analyzing audio: {e}")
            analysis.confidence_score = 0.0
        
        return analysis
    
    def _analyze_audio_characteristics(self, analysis: AudioAnalysis, y: np.ndarray, sr: int):
        """Analyze technical audio characteristics"""
        
        # Dynamic range analysis
        rms = librosa.feature.rms(y=y)[0]
        dynamic_range = np.max(rms) - np.min(rms[rms > 0])
        analysis.dynamic_range = float(dynamic_range)
        
        # Noise estimation
        spectral_flatness = librosa.feature.spectral_flatness(y=y)[0]
        analysis.noise_level = float(np.mean(spectral_flatness))
        
        # Quality assessment based on multiple factors
        if analysis.sample_rate >= 44100 and analysis.dynamic_range > 0.1 and analysis.noise_level < 0.5:
            analysis.audio_quality = "excellent"
        elif analysis.sample_rate >= 22050 and analysis.dynamic_range > 0.05:
            analysis.audio_quality = "good"
        elif analysis.sample_rate >= 16000:
            analysis.audio_quality = "fair"
        else:
            analysis.audio_quality = "poor"
        
        print(f"   🎯 Quality: {analysis.audio_quality}")
        print(f"   📊 Dynamic range: {analysis.dynamic_range:.3f}")
        print(f"   🔊 Noise level: {analysis.noise_level:.3f}")
    
    def _classify_content_type(self, analysis: AudioAnalysis, y: np.ndarray, sr: int):
        """Classify audio content type using librosa analysis"""
        
        filename_lower = analysis.file_path.name.lower()
        best_match = "unknown"
        best_score = 0.0
        
        # Extract audio features for classification
        features = self._extract_classification_features(y, sr)
        
        for content_type, criteria in self.content_classifiers.items():
            score = 0.0
            
            # Check filename keywords
            for keyword in criteria.get('filename_keywords', []):
                if keyword in filename_lower:
                    score += 0.3
            
            # Check duration
            if 'duration_range' in criteria:
                min_dur, max_dur = criteria['duration_range']
                if min_dur <= analysis.duration_seconds <= max_dur:
                    score += 0.2
            
            # Check audio characteristics
            if 'speech_ratio_min' in criteria and features['speech_ratio'] >= criteria['speech_ratio_min']:
                score += 0.3
            
            if 'music_ratio_min' in criteria and features['music_ratio'] >= criteria['music_ratio_min']:
                score += 0.3
            
            if 'has_rhythm' in criteria and features['rhythmic_strength'] > 0.5:
                score += 0.2
            
            if 'tempo_range' in criteria and features['tempo']:
                min_tempo, max_tempo = criteria['tempo_range']
                if min_tempo <= features['tempo'] <= max_tempo:
                    score += 0.2
            
            if score > best_score:
                best_score = score
                best_match = content_type
        
        analysis.content_type = best_match
        analysis.confidence_score = min(best_score, 1.0)
        
        print(f"   🎭 Content type: {analysis.content_type} (confidence: {analysis.confidence_score:.2f})")
    
    def _extract_classification_features(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Extract features for content type classification"""
        
        features = {}
        
        # Spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # Zero crossing rate (speech indicator)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        
        # Tempo and rhythm
        try:
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            features['tempo'] = float(tempo)
            features['rhythmic_strength'] = len(beats) / (len(y) / sr) if len(y) > 0 else 0
        except:
            features['tempo'] = None
            features['rhythmic_strength'] = 0.0
        
        # Speech vs music heuristics
        zcr_mean = np.mean(zcr)
        spectral_centroid_mean = np.mean(spectral_centroids)
        
        # Speech typically has higher ZCR and lower spectral centroid
        if zcr_mean > 0.1 and spectral_centroid_mean < 3000:
            speech_score = 0.8
        elif zcr_mean > 0.05:
            speech_score = 0.5
        else:
            speech_score = 0.2
            
        # Music typically has more consistent rhythm and broader spectral content
        if features['rhythmic_strength'] > 0.3 and spectral_centroid_mean > 2000:
            music_score = 0.8
        elif features['rhythmic_strength'] > 0.1:
            music_score = 0.5
        else:
            music_score = 0.2
        
        features['speech_ratio'] = speech_score
        features['music_ratio'] = music_score
        features['mfcc_mean'] = np.mean(mfccs, axis=1).tolist()
        
        return features
    
    def _extract_speech_features(self, analysis: AudioAnalysis, y: np.ndarray, sr: int):
        """Extract speech-specific features"""
        
        if analysis.content_type in ['interview', 'voice_sample', 'scene_audio']:
            analysis.has_speech = True
            
            # Voice activity detection using energy
            hop_length = 512
            frame_length = 2048
            
            # Compute short-time energy
            energy = librosa.feature.rms(y=y, hop_length=hop_length, frame_length=frame_length)[0]
            
            # Find speech segments (simple energy-based VAD)
            energy_threshold = np.percentile(energy, 30)  # Bottom 30% is likely silence
            speech_frames = energy > energy_threshold
            
            # Convert frame indices to time segments
            frame_times = librosa.frames_to_time(np.arange(len(speech_frames)), sr=sr, hop_length=hop_length)
            speech_segments = []
            
            in_speech = False
            start_time = 0
            
            for i, is_speech in enumerate(speech_frames):
                if is_speech and not in_speech:
                    start_time = frame_times[i]
                    in_speech = True
                elif not is_speech and in_speech:
                    end_time = frame_times[i]
                    if end_time - start_time > 0.5:  # Minimum 0.5 second segments
                        speech_segments.append((float(start_time), float(end_time)))
                    in_speech = False
            
            analysis.speech_segments = speech_segments
            
            # Estimate number of speakers (very basic)
            if len(speech_segments) > 0:
                total_speech_time = sum(end - start for start, end in speech_segments)
                speech_density = total_speech_time / analysis.duration_seconds
                
                if speech_density > 0.8:
                    analysis.estimated_speakers = 1  # Monologue
                elif speech_density > 0.5:
                    analysis.estimated_speakers = 2  # Dialogue
                else:
                    analysis.estimated_speakers = min(3, max(1, len(speech_segments) // 5))
            
            # Speech clarity (based on spectral clarity)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
            
            clarity_score = 1.0 - (np.std(spectral_centroid) / np.mean(spectral_centroid))
            analysis.speech_clarity = max(0.0, min(1.0, clarity_score))
            
            print(f"   🗣️  Speech segments: {len(analysis.speech_segments)}")
            print(f"   👥 Estimated speakers: {analysis.estimated_speakers}")
            print(f"   🎙️  Speech clarity: {analysis.speech_clarity:.2f}")
    
    def _extract_music_features(self, analysis: AudioAnalysis, y: np.ndarray, sr: int):
        """Extract music-specific features"""
        
        if analysis.content_type in ['music', 'scene_audio']:
            analysis.has_music = True
            
            try:
                # Tempo detection
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                analysis.tempo = float(tempo)
                
                # Key estimation (basic)
                chroma = librosa.feature.chroma_stft(y=y, sr=sr)
                chroma_mean = np.mean(chroma, axis=1)
                key_index = np.argmax(chroma_mean)
                key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                analysis.key = key_names[key_index]
                
                # Energy and danceability
                rms = librosa.feature.rms(y=y)[0]
                analysis.energy = float(np.mean(rms))
                
                # Danceability (simplified - based on tempo and rhythm consistency)
                if 90 <= analysis.tempo <= 150:  # Dance tempo range
                    beat_consistency = 1.0 - (np.std(np.diff(beats)) / np.mean(np.diff(beats))) if len(beats) > 1 else 0.0
                    analysis.danceability = min(1.0, max(0.0, beat_consistency * analysis.energy * 2))
                else:
                    analysis.danceability = 0.2
                
                print(f"   🎵 Tempo: {analysis.tempo:.1f} BPM")
                print(f"   🎹 Key: {analysis.key}")
                print(f"   ⚡ Energy: {analysis.energy:.2f}")
                print(f"   💃 Danceability: {analysis.danceability:.2f}")
                
            except Exception as e:
                print(f"   ⚠️  Music feature extraction failed: {e}")
                analysis.has_music = False
    
    def _basic_audio_analysis(self, analysis: AudioAnalysis):
        """Basic audio analysis when librosa is not available"""
        
        try:
            if PYDUB_AVAILABLE:
                audio = AudioSegment.from_file(str(analysis.file_path))
                analysis.duration_seconds = len(audio) / 1000.0
                analysis.sample_rate = audio.frame_rate
                analysis.channels = audio.channels
                analysis.audio_quality = "good" if audio.frame_rate >= 44100 else "fair"
            else:
                # Estimate from file size (very rough)
                analysis.duration_seconds = analysis.file_size_mb * 60  # Assume ~1MB per minute
                analysis.sample_rate = 44100  # Assume CD quality
                analysis.channels = 2
                analysis.audio_quality = "unknown"
                
        except Exception as e:
            print(f"   ⚠️  Basic analysis failed: {e}")
            analysis.duration_seconds = 0
            analysis.confidence_score = 0.0
    
    def _generate_creative_tags(self, analysis: AudioAnalysis):
        """Generate creative workflow tags"""
        
        tags = []
        filename_lower = analysis.file_path.name.lower()
        
        # Add content type tag
        if analysis.content_type != "unknown":
            tags.append(analysis.content_type.replace('_', ' ').title())
        
        # Add quality tags
        if analysis.audio_quality in ['excellent', 'good']:
            tags.append('High Quality')
        elif analysis.audio_quality == 'poor':
            tags.append('Low Quality')
        
        # Add duration-based tags
        if analysis.duration_seconds < 30:
            tags.append('Short Clip')
        elif analysis.duration_seconds > 1800:  # 30 minutes
            tags.append('Long Form')
        elif analysis.duration_seconds > 300:   # 5 minutes
            tags.append('Medium Length')
        
        # Add speech-specific tags
        if analysis.has_speech:
            if analysis.estimated_speakers == 1:
                tags.append('Monologue')
            elif analysis.estimated_speakers >= 2:
                tags.append('Dialogue')
            
            if analysis.speech_clarity > 0.7:
                tags.append('Clear Speech')
        
        # Add music-specific tags
        if analysis.has_music and analysis.tempo:
            if analysis.tempo < 90:
                tags.append('Slow Tempo')
            elif analysis.tempo > 140:
                tags.append('Fast Tempo')
            else:
                tags.append('Medium Tempo')
            
            if analysis.danceability > 0.6:
                tags.append('Danceable')
        
        # Entertainment industry specific tags
        if any(word in filename_lower for word in ['audition', 'casting', 'read']):
            tags.append('Audition Material')
        
        if any(word in filename_lower for word in ['scene', 'take', 'footage']):
            tags.append('Scene Work')
        
        if any(word in filename_lower for word in ['interview', 'press', 'promo']):
            tags.append('Interview/Press')
        
        analysis.creative_tags = tags
        analysis.auto_tags = tags.copy()
        
        print(f"   🏷️  Generated tags: {', '.join(tags[:5])}")
    
    def _determine_project_context(self, analysis: AudioAnalysis):
        """Determine which creative project this audio belongs to"""
        
        filename_lower = analysis.file_path.name.lower()
        path_lower = str(analysis.file_path).lower()
        
        for project, keywords in self.project_patterns.items():
            for keyword in keywords:
                if keyword in filename_lower or keyword in path_lower:
                    analysis.project_context = project
                    analysis.creative_tags.append(f"Project: {project.title()}")
                    break
            
            if analysis.project_context:
                break
        
        if not analysis.project_context:
            analysis.project_context = "unassigned"
    
    def _calculate_importance_score(self, analysis: AudioAnalysis):
        """Calculate importance score for organization priority"""
        
        score = 0.0
        
        # Base score from content type
        content_scores = {
            'interview': 0.8,
            'voice_sample': 0.7,
            'scene_audio': 0.9,
            'music': 0.6,
            'ambient': 0.3
        }
        score += content_scores.get(analysis.content_type, 0.5)
        
        # Quality bonus
        quality_scores = {'excellent': 0.2, 'good': 0.1, 'fair': 0.0, 'poor': -0.1}
        score += quality_scores.get(analysis.audio_quality, 0.0)
        
        # Duration considerations
        if 60 <= analysis.duration_seconds <= 3600:  # 1 minute to 1 hour is ideal
            score += 0.1
        
        # Speech clarity bonus
        if analysis.has_speech and analysis.speech_clarity > 0.7:
            score += 0.1
        
        # Project context bonus
        if analysis.project_context and analysis.project_context != "unassigned":
            score += 0.1
        
        analysis.importance_score = max(0.0, min(1.0, score))
    
    def transcribe_audio(self, analysis: AudioAnalysis, language: str = "en-US") -> Optional[str]:
        """Transcribe speech to text if speech recognition is available"""
        
        if not SPEECH_RECOGNITION_AVAILABLE or not analysis.has_speech:
            return None
        
        try:
            print(f"   🎙️  Attempting transcription...")
            
            # Convert audio to WAV format for speech recognition
            if PYDUB_AVAILABLE:
                audio = AudioSegment.from_file(str(analysis.file_path))
                
                # Convert to mono, 16kHz for better speech recognition
                audio = audio.set_channels(1).set_frame_rate(16000)
                
                # Export to temporary WAV file
                temp_wav = analysis.file_path.parent / f"{analysis.file_path.stem}_temp.wav"
                audio.export(str(temp_wav), format="wav")
                
                # Use speech recognition
                with sr.AudioFile(str(temp_wav)) as source:
                    audio_data = self.recognizer.record(source, duration=min(60, analysis.duration_seconds))
                    
                try:
                    transcript = self.recognizer.recognize_google(audio_data, language=language)
                    analysis.transcription = transcript
                    
                    print(f"   ✅ Transcription successful: {len(transcript)} characters")
                    
                    # Clean up temp file
                    temp_wav.unlink()
                    
                    return transcript
                    
                except sr.UnknownValueError:
                    print(f"   ⚠️  Could not understand audio")
                except sr.RequestError as e:
                    print(f"   ⚠️  Transcription service error: {e}")
                
                # Clean up temp file
                if temp_wav.exists():
                    temp_wav.unlink()
        
        except Exception as e:
            print(f"   ❌ Transcription failed: {e}")
        
        return None
    
    def save_analysis(self, analysis: AudioAnalysis) -> bool:
        """Save audio analysis to database"""
        
        try:
            file_hash = self._calculate_file_hash(analysis.file_path)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO audio_analysis
                    (file_path, file_name, file_hash, file_size_mb, duration_seconds,
                     sample_rate, channels, bit_depth, bitrate, codec,
                     audio_quality, noise_level, dynamic_range,
                     content_type, confidence_score,
                     has_speech, speech_segments, estimated_speakers, speech_clarity, transcription,
                     has_music, tempo, music_key, energy, danceability,
                     creative_tags, project_context, suggested_category, importance_score, auto_tags,
                     analyzed_date, analysis_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(analysis.file_path), analysis.file_path.name, file_hash,
                    analysis.file_size_mb, analysis.duration_seconds,
                    analysis.sample_rate, analysis.channels, analysis.bit_depth, 
                    analysis.bitrate, analysis.codec,
                    analysis.audio_quality, analysis.noise_level, analysis.dynamic_range,
                    analysis.content_type, analysis.confidence_score,
                    analysis.has_speech, json.dumps(analysis.speech_segments), 
                    analysis.estimated_speakers, analysis.speech_clarity, analysis.transcription,
                    analysis.has_music, analysis.tempo, analysis.key, 
                    analysis.energy, analysis.danceability,
                    json.dumps(analysis.creative_tags), analysis.project_context, 
                    analysis.suggested_category, analysis.importance_score, json.dumps(analysis.auto_tags),
                    analysis.analyzed_date.isoformat(), "1.0"
                ))
                
                # Save transcription separately if available
                if analysis.transcription:
                    conn.execute("""
                        INSERT OR REPLACE INTO audio_transcripts
                        (file_path, transcript_text, confidence, language, created_date)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        str(analysis.file_path), analysis.transcription, 
                        analysis.confidence_score, "en-US", 
                        analysis.analyzed_date.isoformat()
                    ))
                
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving analysis: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for change detection"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return ""
    
    def get_analysis(self, file_path: Path) -> Optional[AudioAnalysis]:
        """Retrieve existing analysis from database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM audio_analysis WHERE file_path = ?
                """, (str(file_path),))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    data = dict(zip(columns, row))
                    
                    # Convert back to AudioAnalysis object
                    analysis = AudioAnalysis(
                        file_path=Path(data['file_path']),
                        file_size_mb=data['file_size_mb'],
                        duration_seconds=data['duration_seconds'],
                        sample_rate=data['sample_rate'],
                        channels=data['channels'],
                        bit_depth=data['bit_depth'],
                        bitrate=data['bitrate'],
                        codec=data['codec'],
                        audio_quality=data['audio_quality'],
                        noise_level=data['noise_level'],
                        dynamic_range=data['dynamic_range'],
                        content_type=data['content_type'],
                        confidence_score=data['confidence_score'],
                        has_speech=bool(data['has_speech']),
                        speech_segments=json.loads(data['speech_segments']) if data['speech_segments'] else [],
                        estimated_speakers=data['estimated_speakers'],
                        speech_clarity=data['speech_clarity'],
                        transcription=data['transcription'],
                        has_music=bool(data['has_music']),
                        tempo=data['tempo'],
                        key=data['music_key'],
                        energy=data['energy'],
                        danceability=data['danceability'],
                        creative_tags=json.loads(data['creative_tags']) if data['creative_tags'] else [],
                        project_context=data['project_context'],
                        suggested_category=data['suggested_category'],
                        importance_score=data['importance_score'],
                        auto_tags=json.loads(data['auto_tags']) if data['auto_tags'] else [],
                        analyzed_date=datetime.fromisoformat(data['analyzed_date'])
                    )
                    
                    return analysis
        
        except Exception as e:
            print(f"❌ Error retrieving analysis: {e}")
        
        return None

def test_audio_ai_analyzer():
    """Test the audio AI analyzer system"""
    
    print("🎵 Testing Audio AI Analyzer")
    print("=" * 50)
    
    # Check dependencies
    print("📦 Checking dependencies...")
    print(f"   librosa: {'✅' if LIBROSA_AVAILABLE else '❌'}")
    print(f"   speech_recognition: {'✅' if SPEECH_RECOGNITION_AVAILABLE else '❌'}")
    print(f"   pydub: {'✅' if PYDUB_AVAILABLE else '❌'}")
    print(f"   soundfile: {'✅' if SOUNDFILE_AVAILABLE else '❌'}")
    
    analyzer = AudioAIAnalyzer()
    
    # Find test audio files
    test_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Desktop", 
        Path.home() / "Music",
        Path("/Users/user/Github/ai-file-organizer")
    ]
    
    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            for ext in ['.mp3', '.wav', '.m4a', '.aiff']:
                files = list(test_dir.glob(f"*{ext}"))
                test_files.extend(files[:1])  # One file per type
                if len(test_files) >= 2:
                    break
        if len(test_files) >= 2:
            break
    
    if not test_files:
        print("❌ No audio files found for testing")
        print("💡 Place some .mp3 or .wav files in Downloads or Desktop to test")
        return
    
    print(f"\n🎯 Testing with {len(test_files)} audio files...")
    
    for i, audio_file in enumerate(test_files[:2], 1):
        print(f"\n📄 [{i}] Testing: {audio_file.name}")
        
        try:
            # Analyze audio
            analysis = analyzer.analyze_audio_file(audio_file)
            
            print(f"   ⏱️  Duration: {analysis.duration_seconds:.1f}s")
            print(f"   🎭 Content: {analysis.content_type}")
            print(f"   🎯 Confidence: {analysis.confidence_score:.2f}")
            print(f"   ⭐ Importance: {analysis.importance_score:.2f}")
            
            # Try transcription for speech content
            if analysis.has_speech:
                transcript = analyzer.transcribe_audio(analysis)
                if transcript:
                    print(f"   📝 Transcript: {transcript[:50]}...")
            
            # Save analysis
            success = analyzer.save_analysis(analysis)
            print(f"   💾 Saved: {'✅' if success else '❌'}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n✅ Audio AI analyzer test completed!")

if __name__ == "__main__":
    test_audio_ai_analyzer()