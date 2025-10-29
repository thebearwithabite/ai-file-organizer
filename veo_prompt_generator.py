#!/usr/bin/env python3
"""
VEO Prompt Generator - Phase 3a Implementation
AI File Organizer v3.1 - Reverse Prompt Builder (MVP)

This module generates VEO 3.1 JSON descriptions from video clips by analyzing
them with Gemini Vision API and extracting visual/audio characteristics.

Created by: RT Max / Claude Code
Date: October 28, 2025
"""

import os
import json
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
import hashlib

# Import vision analyzer for video analysis
from vision_analyzer import VisionAnalyzer
from gdrive_integration import get_ai_organizer_root

# VEO 3.1 Schema Template
VEO_SCHEMA_TEMPLATE = {
    "unit_type": "shot",
    "veo_shot": {
        "shot_id": "",
        "scene": {
            "context": "",
            "visual_style": "",
            "lighting": "",
            "mood": "",
            "aspect_ratio": "",
            "duration_s": 0
        },
        "character": {
            "name": "unknown",
            "gender_age": "",
            "description_lock": "",
            "behavior": "",
            "expression": ""
        },
        "camera": {
            "shot_call": "",
            "movement": "",
            "negatives": ""
        },
        "audio": {
            "dialogue": "",
            "delivery": "",
            "ambience": "",
            "sfx": ""
        },
        "flags": {
            "continuity_lock": False,
            "do_not": [],
            "anti_artifacts": [],
            "conflicts": [],
            "warnings": [],
            "cv_updates": []
        }
    },
    "confidence_score": 0.0
}


class VEOPromptGenerator:
    """
    Generates VEO 3.1 JSON prompts from video clips using Gemini Vision API.

    This class analyzes video files and produces structured VEO descriptions
    suitable for video generation systems like Google's VEO.
    """

    # Supported video formats
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}

    # Shot type mapping keywords
    SHOT_TYPES = {
        'extreme_wide': ['landscape', 'establishing', 'aerial', 'wide angle', 'panoramic'],
        'wide': ['full body', 'entire scene', 'room', 'environment'],
        'medium': ['waist up', 'medium shot', 'mid shot', 'torso'],
        'closeup': ['face', 'close up', 'detail', 'tight'],
        'extreme_closeup': ['eyes', 'extreme close', 'macro', 'very close']
    }

    # Camera movement keywords
    CAMERA_MOVEMENTS = {
        'static': ['still', 'stationary', 'fixed', 'no movement'],
        'pan': ['panning', 'horizontal movement', 'sweeping'],
        'tilt': ['tilting', 'vertical movement', 'up down'],
        'dolly': ['tracking', 'moving forward', 'moving backward', 'push in', 'pull out'],
        'handheld': ['shaky', 'handheld', 'unstable', 'dynamic'],
        'crane': ['crane shot', 'aerial movement', 'rising', 'descending']
    }

    # Lighting keywords
    LIGHTING_TYPES = {
        'natural': ['sunlight', 'daylight', 'window light', 'outdoor'],
        'artificial': ['indoor lighting', 'studio lights', 'lamps'],
        'low_key': ['dramatic', 'dark', 'shadows', 'moody', 'noir'],
        'high_key': ['bright', 'well-lit', 'even lighting', 'flat'],
        'backlit': ['backlight', 'silhouette', 'rim light'],
        'golden_hour': ['sunset', 'sunrise', 'warm light', 'golden']
    }

    def __init__(self,
                 base_dir: Optional[str] = None,
                 db_path: Optional[str] = None,
                 output_dir: Optional[str] = None):
        """
        Initialize the VEO Prompt Generator.

        Args:
            base_dir: Base directory for file operations
            db_path: Path to SQLite database for storing VEO prompts
            output_dir: Directory to save generated JSON files
        """
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        self.db_path = Path(db_path) if db_path else self.base_dir / "04_METADATA_SYSTEM" / "metadata.db"
        self.output_dir = Path(output_dir) if output_dir else self.base_dir / "05_VEO_PROMPTS"

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Initialize vision analyzer
        try:
            self.vision_analyzer = VisionAnalyzer(base_dir=str(self.base_dir))
            self.vision_enabled = self.vision_analyzer.api_initialized
            if self.vision_enabled:
                self.logger.info("✅ Gemini Vision API initialized for VEO analysis")
            else:
                self.logger.warning("⚠️  Vision API unavailable, VEO generation will be limited")
        except Exception as e:
            self.vision_analyzer = None
            self.vision_enabled = False
            self.logger.error(f"❌ Failed to initialize Vision Analyzer: {e}")

        # Initialize database
        self._init_database()

        # Performance metrics
        self.videos_analyzed = 0
        self.prompts_generated = 0

    def _init_database(self):
        """Initialize SQLite database with veo_prompts table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create veo_prompts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS veo_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    veo_json TEXT NOT NULL,
                    shot_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence_score REAL,
                    validated BOOLEAN DEFAULT 0,
                    aspect_ratio TEXT,
                    duration_s REAL,
                    shot_type TEXT,
                    camera_movement TEXT,
                    lighting_type TEXT,
                    mood TEXT,
                    scene_context TEXT,
                    frame_samples INTEGER,
                    analysis_timestamp TEXT
                )
            """)

            conn.commit()
            conn.close()
            self.logger.info("✅ Database initialized with veo_prompts table")

        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")

    def generate_reverse_veo_json(self, video_path: str) -> Dict[str, Any]:
        """
        Generate VEO 3.1 JSON from a video file.

        This is the main entry point that:
        1. Validates the video file
        2. Extracts metadata with ffprobe
        3. Samples frames for analysis
        4. Calls vision_analyzer for VEO-specific features
        5. Assembles complete VEO JSON
        6. Saves to database and disk

        Args:
            video_path: Path to video file

        Returns:
            Complete VEO 3.1 JSON structure with confidence score
        """
        video_path = Path(video_path)

        # Validate file
        if not video_path.exists():
            return {
                'success': False,
                'error': f'Video file not found: {video_path}',
                'confidence_score': 0.0
            }

        if video_path.suffix.lower() not in self.VIDEO_EXTENSIONS:
            return {
                'success': False,
                'error': f'Unsupported video format: {video_path.suffix}',
                'confidence_score': 0.0
            }

        self.logger.info(f"🎬 Analyzing video: {video_path.name}")

        try:
            # Step 1: Extract video metadata
            metadata = self._extract_video_metadata(video_path)
            if not metadata.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to extract metadata: {metadata.get('error')}",
                    'confidence_score': 0.0
                }

            # Step 2: Analyze with Vision API for VEO features
            if self.vision_enabled and self.vision_analyzer and hasattr(self.vision_analyzer, 'analyze_for_veo_prompt'):
                veo_analysis = self.vision_analyzer.analyze_for_veo_prompt(str(video_path))
            else:
                # Fallback analysis without API
                veo_analysis = self._fallback_veo_analysis(video_path, metadata)

            # Step 3: Assemble VEO JSON
            veo_json = self._assemble_veo_json(video_path, metadata, veo_analysis)

            # Step 4: Generate unique shot ID
            veo_json['veo_shot']['shot_id'] = self._generate_shot_id(video_path)

            # Step 5: Save to database
            self._save_to_database(video_path, veo_json)

            # Step 6: Save JSON to disk
            json_path = self._save_json_to_disk(video_path, veo_json)

            self.videos_analyzed += 1
            self.prompts_generated += 1

            self.logger.info(f"✅ VEO JSON generated: {json_path}")

            return {
                'success': True,
                'veo_json': veo_json,
                'json_path': str(json_path),
                'confidence_score': veo_json.get('confidence_score', 0.0)
            }

        except Exception as e:
            self.logger.error(f"❌ Error generating VEO JSON: {e}")
            return {
                'success': False,
                'error': str(e),
                'confidence_score': 0.0
            }

    def _extract_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """
        Extract video metadata using ffprobe.

        Returns:
            Metadata dictionary with duration, resolution, fps, aspect ratio
        """
        try:
            # Use ffprobe to get video metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'ffprobe failed: {result.stderr}'
                }

            data = json.loads(result.stdout)

            # Extract video stream info
            video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
            audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), None)

            if not video_stream:
                return {
                    'success': False,
                    'error': 'No video stream found'
                }

            # Calculate aspect ratio
            width = video_stream.get('width', 1920)
            height = video_stream.get('height', 1080)
            aspect_ratio = self._calculate_aspect_ratio(width, height)

            # Get duration
            duration = float(data.get('format', {}).get('duration', 0))

            # Get frame rate
            fps_str = video_stream.get('r_frame_rate', '30/1')
            try:
                num, denom = map(int, fps_str.split('/'))
                fps = num / denom if denom != 0 else 30.0
            except:
                fps = 30.0

            return {
                'success': True,
                'duration': duration,
                'width': width,
                'height': height,
                'aspect_ratio': aspect_ratio,
                'fps': fps,
                'codec': video_stream.get('codec_name', 'unknown'),
                'has_audio': audio_stream is not None,
                'file_size': int(data.get('format', {}).get('size', 0))
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'ffprobe timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _calculate_aspect_ratio(self, width: int, height: int) -> str:
        """
        Calculate aspect ratio from width and height.

        Returns:
            String like "16:9", "4:3", "1:1", etc.
        """
        from math import gcd

        divisor = gcd(width, height)
        ratio_w = width // divisor
        ratio_h = height // divisor

        # Common ratios
        if (ratio_w, ratio_h) == (16, 9):
            return "16:9"
        elif (ratio_w, ratio_h) == (4, 3):
            return "4:3"
        elif (ratio_w, ratio_h) == (1, 1):
            return "1:1"
        elif (ratio_w, ratio_h) == (21, 9):
            return "21:9"
        else:
            return f"{ratio_w}:{ratio_h}"

    def _fallback_veo_analysis(self, video_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback VEO analysis when Vision API unavailable.
        Uses filename and metadata for basic analysis.
        """
        filename = video_path.name.lower()

        return {
            'shot_type': 'Medium',
            'camera_movement': 'Static',
            'lighting': 'Natural lighting',
            'mood': 'Neutral',
            'scene_context': f'Video content: {video_path.stem}',
            'visual_style': 'Standard video recording',
            'objects': [],
            'color_palette': ['unknown'],
            'audio_ambience': 'Ambient sound' if metadata.get('has_audio') else 'No audio',
            'confidence_score': 0.3,
            'fallback_mode': True
        }

    def _assemble_veo_json(self,
                           video_path: Path,
                           metadata: Dict[str, Any],
                           veo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assemble complete VEO 3.1 JSON structure from analysis results.

        Args:
            video_path: Path to video file
            metadata: Video metadata from ffprobe
            veo_analysis: VEO-specific analysis from vision_analyzer

        Returns:
            Complete VEO JSON structure
        """
        # Start with template
        veo_json = json.loads(json.dumps(VEO_SCHEMA_TEMPLATE))  # Deep copy

        # Fill in scene details
        veo_json['veo_shot']['scene']['context'] = veo_analysis.get('scene_context', 'Video scene')
        veo_json['veo_shot']['scene']['visual_style'] = veo_analysis.get('visual_style', 'Standard video')
        veo_json['veo_shot']['scene']['lighting'] = veo_analysis.get('lighting', 'Natural lighting')
        veo_json['veo_shot']['scene']['mood'] = veo_analysis.get('mood', 'Neutral')
        veo_json['veo_shot']['scene']['aspect_ratio'] = metadata.get('aspect_ratio', '16:9')
        veo_json['veo_shot']['scene']['duration_s'] = int(metadata.get('duration', 0))

        # Character detection (basic)
        veo_json['veo_shot']['character']['name'] = 'unknown'
        veo_json['veo_shot']['character']['gender_age'] = veo_analysis.get('character_info', '')
        veo_json['veo_shot']['character']['description_lock'] = veo_analysis.get('character_description', '')
        veo_json['veo_shot']['character']['behavior'] = veo_analysis.get('behavior', '')
        veo_json['veo_shot']['character']['expression'] = veo_analysis.get('expression', '')

        # Camera details
        veo_json['veo_shot']['camera']['shot_call'] = veo_analysis.get('shot_type', 'Medium')
        veo_json['veo_shot']['camera']['movement'] = veo_analysis.get('camera_movement', 'Static')
        veo_json['veo_shot']['camera']['negatives'] = ''

        # Audio details
        veo_json['veo_shot']['audio']['dialogue'] = ''
        veo_json['veo_shot']['audio']['delivery'] = ''
        veo_json['veo_shot']['audio']['ambience'] = veo_analysis.get('audio_ambience', 'Ambient sound')
        veo_json['veo_shot']['audio']['sfx'] = veo_analysis.get('sfx', '')

        # Confidence score
        veo_json['confidence_score'] = veo_analysis.get('confidence_score', 0.5)

        return veo_json

    def _generate_shot_id(self, video_path: Path) -> str:
        """
        Generate unique shot ID from video path.

        Format: auto_shot_{hash}
        """
        # Use first 8 chars of file hash for uniqueness
        file_hash = hashlib.md5(str(video_path).encode()).hexdigest()[:8]
        return f"auto_shot_{file_hash}"

    def _save_to_database(self, video_path: Path, veo_json: Dict[str, Any]):
        """Save VEO JSON to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Extract key fields for indexing
            shot = veo_json['veo_shot']
            scene = shot['scene']
            camera = shot['camera']

            cursor.execute("""
                INSERT OR REPLACE INTO veo_prompts (
                    file_path, veo_json, shot_id, confidence_score,
                    aspect_ratio, duration_s, shot_type, camera_movement,
                    lighting_type, mood, scene_context, analysis_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(video_path),
                json.dumps(veo_json, indent=2),
                shot['shot_id'],
                veo_json['confidence_score'],
                scene['aspect_ratio'],
                scene['duration_s'],
                camera['shot_call'],
                camera['movement'],
                scene['lighting'],
                scene['mood'],
                scene['context'],
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            self.logger.info(f"✅ Saved to database: {shot['shot_id']}")

        except Exception as e:
            self.logger.error(f"❌ Database save failed: {e}")

    def _save_json_to_disk(self, video_path: Path, veo_json: Dict[str, Any]) -> Path:
        """
        Save VEO JSON to disk with naming convention.

        Format: <clip_name>_veo.json
        """
        output_filename = f"{video_path.stem}_veo.json"
        output_path = self.output_dir / output_filename

        try:
            with open(output_path, 'w') as f:
                json.dump(veo_json, f, indent=2)

            return output_path

        except Exception as e:
            self.logger.error(f"❌ Failed to save JSON to disk: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'videos_analyzed': self.videos_analyzed,
            'prompts_generated': self.prompts_generated,
            'vision_api_enabled': self.vision_enabled,
            'output_directory': str(self.output_dir),
            'database_path': str(self.db_path)
        }


# Command-line interface
def main():
    """Main CLI for VEO Prompt Generator"""
    import argparse

    parser = argparse.ArgumentParser(
        description='VEO Prompt Generator - Generate VEO 3.1 JSON from video clips'
    )
    parser.add_argument('video_path', help='Path to video file to analyze')
    parser.add_argument('--output-dir', help='Output directory for JSON files')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Set up logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize generator
    generator = VEOPromptGenerator(output_dir=args.output_dir)

    # Generate VEO JSON
    result = generator.generate_reverse_veo_json(args.video_path)

    if result.get('success'):
        print(f"✅ VEO JSON generated successfully!")
        print(f"📄 JSON file: {result['json_path']}")
        print(f"🎯 Confidence score: {result['confidence_score']:.2f}")
        print(f"\n📊 Shot ID: {result['veo_json']['veo_shot']['shot_id']}")
    else:
        print(f"❌ Failed to generate VEO JSON: {result.get('error')}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
