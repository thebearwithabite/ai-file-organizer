#!/usr/bin/env python3
"""
Multimedia Content Analysis System for AI File Organizer
Analyzes video, images, audio, and GIFs for intelligent organization
Based on AudioAI patterns but expanded for visual and multimedia content
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import sqlite3
import hashlib

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

@dataclass
class MultimediaAnalysis:
    """Results of multimedia content analysis"""
    file_path: Path
    media_type: str  # 'image', 'video', 'audio', 'gif'
    duration_seconds: float = 0.0
    resolution: Optional[Tuple[int, int]] = None
    file_size_mb: float = 0.0
    
    # Technical metadata
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    frame_rate: Optional[float] = None
    color_space: Optional[str] = None
    
    # Content analysis
    estimated_content_type: Optional[str] = None  # 'interview', 'scene', 'music', 'voice', 'screenshot'
    audio_characteristics: Dict[str, Any] = None
    visual_characteristics: Dict[str, Any] = None
    
    # AI-enhanced analysis
    scene_description: Optional[str] = None
    people_detected: List[str] = None
    objects_detected: List[str] = None
    text_detected: List[str] = None
    
    # Organization suggestions
    suggested_category: Optional[str] = None
    confidence_score: float = 0.0
    tags: List[str] = None

class MultimediaAnalyzer:
    """
    Analyzes multimedia files for intelligent organization
    Like AudioAI but for video, images, and other visual content
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.analysis_dir = self.base_dir / "04_METADATA_SYSTEM" / "multimedia_analysis"
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for multimedia analysis results
        self.db_path = self.analysis_dir / "multimedia_analysis.db"
        self._init_analysis_db()
        
        # Supported file types
        self.supported_types = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic'],
            'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'],
            'audio': ['.mp3', '.wav', '.aiff', '.m4a', '.flac', '.ogg', '.wma', '.aac']
        }
        
        # Content type patterns
        self.content_patterns = {
            'interview': {
                'audio_indicators': ['voice', 'speech', 'conversation'],
                'filename_patterns': ['interview', 'conversation', 'talk', 'discussion'],
                'duration_range': (60, 3600)  # 1 minute to 1 hour
            },
            'scene': {
                'video_indicators': ['high_motion', 'multiple_cuts', 'dramatic_lighting'],
                'filename_patterns': ['scene', 'take', 'shot', 'footage'],
                'duration_range': (10, 600)  # 10 seconds to 10 minutes
            },
            'music': {
                'audio_indicators': ['music', 'instrumental', 'song'],
                'filename_patterns': ['music', 'song', 'track', 'audio'],
                'duration_range': (30, 600)  # 30 seconds to 10 minutes
            },
            'voice_sample': {
                'audio_indicators': ['voice', 'speech', 'narration'],
                'filename_patterns': ['voice', 'narration', 'voiceover', 'sample'],
                'duration_range': (5, 180)  # 5 seconds to 3 minutes
            },
            'screenshot': {
                'image_indicators': ['screenshot', 'screen_capture'],
                'filename_patterns': ['screenshot', 'screen', 'capture', 'shot'],
                'resolution_indicators': [(1920, 1080), (2560, 1440), (3840, 2160)]
            }
        }
    
    def _init_analysis_db(self):
        """Initialize SQLite database for multimedia analysis"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS multimedia_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_name TEXT,
                    file_extension TEXT,
                    media_type TEXT,
                    file_size_mb REAL,
                    
                    -- Technical metadata
                    duration_seconds REAL,
                    resolution_width INTEGER,
                    resolution_height INTEGER,
                    codec TEXT,
                    bitrate INTEGER,
                    frame_rate REAL,
                    color_space TEXT,
                    
                    -- Content analysis
                    estimated_content_type TEXT,
                    audio_characteristics TEXT,  -- JSON
                    visual_characteristics TEXT,  -- JSON
                    
                    -- AI analysis (placeholder for future enhancement)
                    scene_description TEXT,
                    people_detected TEXT,  -- JSON array
                    objects_detected TEXT,  -- JSON array
                    text_detected TEXT,    -- JSON array
                    
                    -- Organization
                    suggested_category TEXT,
                    confidence_score REAL,
                    tags TEXT,  -- JSON array
                    
                    -- Tracking
                    analyzed_date TEXT,
                    file_hash TEXT,
                    analysis_version TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    files_analyzed INTEGER,
                    successful_analyses INTEGER,
                    failed_analyses INTEGER,
                    analysis_mode TEXT
                )
            """)
            
            conn.commit()
    
    def get_media_type(self, file_path: Path) -> Optional[str]:
        """Determine media type from file extension"""
        ext = file_path.suffix.lower()
        
        for media_type, extensions in self.supported_types.items():
            if ext in extensions:
                return media_type
        
        return None
    
    def analyze_file(self, file_path: Path) -> MultimediaAnalysis:
        """Analyze a multimedia file comprehensively"""
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        media_type = self.get_media_type(file_path)
        if not media_type:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        # Initialize analysis result
        analysis = MultimediaAnalysis(
            file_path=file_path,
            media_type=media_type,
            file_size_mb=file_path.stat().st_size / (1024 * 1024),
            audio_characteristics={},
            visual_characteristics={},
            people_detected=[],
            objects_detected=[],
            text_detected=[],
            tags=[]
        )
        
        try:
            # Get basic technical metadata
            if media_type in ['video', 'audio']:
                self._analyze_av_metadata(analysis)
            elif media_type == 'image':
                self._analyze_image_metadata(analysis)
            
            # Content type analysis
            self._analyze_content_type(analysis)
            
            # Generate tags and suggestions
            self._generate_organization_suggestions(analysis)
            
        except Exception as e:
            print(f"⚠️  Error analyzing {file_path.name}: {e}")
            analysis.confidence_score = 0.0
        
        return analysis
    
    def _analyze_av_metadata(self, analysis: MultimediaAnalysis):
        """Analyze audio/video metadata using basic file inspection"""
        
        file_path = analysis.file_path
        
        # Try to get duration using file stat and estimation
        # This is a basic approach - in practice you'd use ffprobe or similar
        file_size = analysis.file_size_mb
        
        # Rough duration estimation based on file size and type
        if analysis.media_type == 'video':
            # Assume ~1MB per 10 seconds for typical video
            estimated_duration = file_size * 10
            analysis.duration_seconds = min(estimated_duration, 3600)  # Cap at 1 hour
            
            # Typical video resolution defaults
            if file_size > 100:  # Large file, probably HD
                analysis.resolution = (1920, 1080)
            elif file_size > 10:  # Medium file, probably SD
                analysis.resolution = (1280, 720)
            else:  # Small file
                analysis.resolution = (640, 480)
                
            analysis.visual_characteristics = {
                'estimated_quality': 'HD' if file_size > 100 else 'SD',
                'estimated_bitrate': int(file_size * 8 * 1024 / max(analysis.duration_seconds, 1))
            }
            
        elif analysis.media_type == 'audio':
            # Assume ~1MB per 60 seconds for typical audio
            estimated_duration = file_size * 60
            analysis.duration_seconds = min(estimated_duration, 7200)  # Cap at 2 hours
            
            analysis.audio_characteristics = {
                'estimated_bitrate': int(file_size * 8 * 1024 / max(analysis.duration_seconds, 1)),
                'estimated_quality': 'High' if file_size > 10 else 'Standard'
            }
        
        # Set codec based on extension
        ext = file_path.suffix.lower()
        codec_map = {
            '.mp4': 'H.264', '.mov': 'H.264', '.avi': 'Various',
            '.mp3': 'MP3', '.wav': 'PCM', '.m4a': 'AAC', '.flac': 'FLAC'
        }
        analysis.codec = codec_map.get(ext, 'Unknown')
    
    def _analyze_image_metadata(self, analysis: MultimediaAnalysis):
        """Analyze image metadata"""
        
        # Basic image analysis without external libraries
        file_size = analysis.file_size_mb
        
        # Estimate resolution based on file size (very rough)
        if file_size > 5:  # Large image file
            analysis.resolution = (3840, 2160)  # 4K estimate
        elif file_size > 1:  # Medium image file
            analysis.resolution = (1920, 1080)  # HD estimate
        else:  # Small image file
            analysis.resolution = (1280, 720)   # SD estimate
        
        analysis.visual_characteristics = {
            'estimated_quality': 'High' if file_size > 1 else 'Standard',
            'format': analysis.file_path.suffix.upper().replace('.', '')
        }
    
    def _analyze_content_type(self, analysis: MultimediaAnalysis):
        """Analyze content type based on filename and characteristics"""
        
        filename_lower = analysis.file_path.name.lower()
        best_match = None
        best_score = 0.0
        
        for content_type, patterns in self.content_patterns.items():
            score = 0.0
            
            # Check filename patterns
            for pattern in patterns.get('filename_patterns', []):
                if pattern in filename_lower:
                    score += 0.4
            
            # Check duration if applicable
            if 'duration_range' in patterns and analysis.duration_seconds > 0:
                min_dur, max_dur = patterns['duration_range']
                if min_dur <= analysis.duration_seconds <= max_dur:
                    score += 0.3
            
            # Check resolution for images
            if 'resolution_indicators' in patterns and analysis.resolution:
                for res in patterns['resolution_indicators']:
                    if analysis.resolution == res:
                        score += 0.3
                        break
            
            # Special patterns for file characteristics
            if analysis.media_type == 'audio':
                if 'voice' in filename_lower or 'speech' in filename_lower:
                    if content_type in ['interview', 'voice_sample']:
                        score += 0.2
                if 'music' in filename_lower or 'song' in filename_lower:
                    if content_type == 'music':
                        score += 0.2
            
            if analysis.media_type == 'image':
                if 'screen' in filename_lower or 'shot' in filename_lower:
                    if content_type == 'screenshot':
                        score += 0.3
            
            if score > best_score:
                best_score = score
                best_match = content_type
        
        if best_match and best_score > 0.3:
            analysis.estimated_content_type = best_match
            analysis.confidence_score = min(best_score, 1.0)
        else:
            analysis.estimated_content_type = 'general'
            analysis.confidence_score = 0.1
    
    def _generate_organization_suggestions(self, analysis: MultimediaAnalysis):
        """Generate organization suggestions and tags"""
        
        tags = []
        suggested_category = None
        
        # Add media type tag
        tags.append(analysis.media_type.title())
        
        # Add content type tags
        if analysis.estimated_content_type:
            tags.append(analysis.estimated_content_type.replace('_', ' ').title())
        
        # Add quality tags
        if analysis.visual_characteristics:
            quality = analysis.visual_characteristics.get('estimated_quality')
            if quality:
                tags.append(quality)
        
        # Add duration-based tags
        if analysis.duration_seconds > 0:
            if analysis.duration_seconds < 30:
                tags.append('Short')
            elif analysis.duration_seconds < 300:  # 5 minutes
                tags.append('Medium')
            else:
                tags.append('Long')
        
        # Suggest organization category
        if analysis.estimated_content_type == 'interview':
            suggested_category = 'interviews'
        elif analysis.estimated_content_type == 'scene':
            suggested_category = 'footage'
        elif analysis.estimated_content_type == 'music':
            suggested_category = 'music'
        elif analysis.estimated_content_type == 'voice_sample':
            suggested_category = 'voice_samples'
        elif analysis.estimated_content_type == 'screenshot':
            suggested_category = 'screenshots'
        else:
            # Default categories by media type
            if analysis.media_type == 'video':
                suggested_category = 'video_content'
            elif analysis.media_type == 'audio':
                suggested_category = 'audio_content'
            elif analysis.media_type == 'image':
                suggested_category = 'images'
        
        # Add project-specific tags from filename
        filename_lower = analysis.file_path.name.lower()
        project_indicators = {
            'stranger things': ['stranger', 'things', 'netflix', 'hawkins'],
            'creative project': ['creative', 'project', 'podcast', 'consciousness'],
            'client work': ['client', 'management', 'contract']
        }
        
        for project, indicators in project_indicators.items():
            if any(indicator in filename_lower for indicator in indicators):
                tags.append(project.title())
                break
        
        analysis.tags = list(set(tags))  # Remove duplicates
        analysis.suggested_category = suggested_category
    
    def save_analysis(self, analysis: MultimediaAnalysis) -> bool:
        """Save analysis results to database"""
        
        try:
            file_hash = self._calculate_file_hash(analysis.file_path)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO multimedia_analysis
                    (file_path, file_name, file_extension, media_type, file_size_mb,
                     duration_seconds, resolution_width, resolution_height, codec,
                     bitrate, frame_rate, color_space, estimated_content_type,
                     audio_characteristics, visual_characteristics, scene_description,
                     people_detected, objects_detected, text_detected, suggested_category,
                     confidence_score, tags, analyzed_date, file_hash, analysis_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(analysis.file_path),
                    analysis.file_path.name,
                    analysis.file_path.suffix.lower(),
                    analysis.media_type,
                    analysis.file_size_mb,
                    analysis.duration_seconds,
                    analysis.resolution[0] if analysis.resolution else None,
                    analysis.resolution[1] if analysis.resolution else None,
                    analysis.codec,
                    analysis.bitrate,
                    analysis.frame_rate,
                    analysis.color_space,
                    analysis.estimated_content_type,
                    json.dumps(analysis.audio_characteristics),
                    json.dumps(analysis.visual_characteristics),
                    analysis.scene_description,
                    json.dumps(analysis.people_detected),
                    json.dumps(analysis.objects_detected),
                    json.dumps(analysis.text_detected),
                    analysis.suggested_category,
                    analysis.confidence_score,
                    json.dumps(analysis.tags),
                    datetime.now().isoformat(),
                    file_hash,
                    "1.0"
                ))
                conn.commit()
            
            return True
        
        except Exception as e:
            print(f"❌ Error saving analysis: {e}")
            return False
    
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
    
    def analyze_directory(self, directory: Path, recursive: bool = True) -> List[MultimediaAnalysis]:
        """Analyze all multimedia files in a directory"""
        
        print(f"📁 Analyzing multimedia files in: {directory}")
        print("=" * 60)
        
        # Find multimedia files
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        all_files = []
        for file_type, extensions in self.supported_types.items():
            for ext in extensions:
                all_files.extend(directory.glob(f"{pattern}{ext}"))
                all_files.extend(directory.glob(f"{pattern}{ext.upper()}"))
        
        multimedia_files = [f for f in all_files if f.is_file()]
        
        if not multimedia_files:
            print("❌ No multimedia files found")
            return []
        
        print(f"🔍 Found {len(multimedia_files)} multimedia files")
        
        analyses = []
        successful = 0
        failed = 0
        
        for i, file_path in enumerate(multimedia_files, 1):
            print(f"\n📄 [{i}/{len(multimedia_files)}] {file_path.name}")
            
            try:
                analysis = self.analyze_file(file_path)
                analyses.append(analysis)
                
                # Save to database
                if self.save_analysis(analysis):
                    successful += 1
                    print(f"   ✅ {analysis.media_type.title()} - {analysis.estimated_content_type}")
                    print(f"   🎯 Confidence: {analysis.confidence_score:.1%}")
                    print(f"   🏷️  Tags: {', '.join(analysis.tags[:3])}")
                    
                    if analysis.duration_seconds > 0:
                        print(f"   ⏱️  Duration: {analysis.duration_seconds/60:.1f} minutes")
                else:
                    failed += 1
                
            except Exception as e:
                failed += 1
                print(f"   ❌ Error: {e}")
        
        print(f"\n📊 Analysis Summary:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        
        return analyses
    
    def get_analysis_results(self, days_back: int = 30) -> List[Dict]:
        """Get recent analysis results from database"""
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM multimedia_analysis
                WHERE analyzed_date > ?
                ORDER BY analyzed_date DESC
            """, (cutoff_date,))
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                results.append(result)
            
            return results

def test_multimedia_analyzer():
    """Test the multimedia analyzer system"""
    
    print("🧪 Testing Multimedia Content Analyzer")
    print("=" * 50)
    
    analyzer = MultimediaAnalyzer()
    
    # Find test files in common locations
    test_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Desktop", 
        Path.home() / "Movies",
        Path.home() / "Music",
        Path.home() / "Pictures"
    ]
    
    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            # Look for multimedia files
            for file_type, extensions in analyzer.supported_types.items():
                for ext in extensions[:2]:  # Test first 2 extensions per type
                    files = list(test_dir.glob(f"*{ext}"))
                    test_files.extend(files[:1])  # Max 1 per extension
                    if len(test_files) >= 3:
                        break
                if len(test_files) >= 3:
                    break
        if len(test_files) >= 3:
            break
    
    if test_files:
        print(f"📁 Testing with {len(test_files)} sample files...")
        
        for test_file in test_files:
            print(f"\n🔍 Analyzing: {test_file.name}")
            
            try:
                analysis = analyzer.analyze_file(test_file)
                
                print(f"   Type: {analysis.media_type}")
                print(f"   Content: {analysis.estimated_content_type}")
                print(f"   Size: {analysis.file_size_mb:.1f} MB")
                
                if analysis.duration_seconds > 0:
                    print(f"   Duration: {analysis.duration_seconds/60:.1f} minutes")
                
                if analysis.resolution:
                    print(f"   Resolution: {analysis.resolution[0]}x{analysis.resolution[1]}")
                
                print(f"   Category: {analysis.suggested_category}")
                print(f"   Confidence: {analysis.confidence_score:.1%}")
                print(f"   Tags: {', '.join(analysis.tags)}")
                
                # Save analysis
                success = analyzer.save_analysis(analysis)
                print(f"   Saved: {'✅' if success else '❌'}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    else:
        print("❌ No multimedia test files found")
        print("💡 Try placing some .mp4, .jpg, or .mp3 files in Downloads or Desktop")

if __name__ == "__main__":
    test_multimedia_analyzer()