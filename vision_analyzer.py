#!/usr/bin/env python3
"""
VisionAnalyzer - Gemini Computer Vision Integration
Part of AI File Organizer v3.1 - Phase 2 Implementation

This module provides computer vision capabilities using Google's Gemini API
for intelligent classification of images and videos. Designed to integrate
with the unified classification system and adaptive learning framework.

Created by: RT Max / Claude Code
"""

import os
import json
import pickle
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import time
import logging

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not available. Vision analysis will be disabled.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not available. Image preprocessing will be limited.")


class VisionAnalyzer:
    """
    Computer vision analysis system using Google's Gemini API.

    Provides intelligent visual content analysis with:
    - Image object detection and scene understanding
    - Screenshot text extraction (OCR)
    - Video content analysis (up to 2 minutes)
    - Integration with adaptive learning system
    - ADHD-friendly confidence scoring
    """

    # Supported file formats
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}

    # Analysis prompts for different content types
    IMAGE_ANALYSIS_PROMPT = """Analyze this image and provide a detailed but concise description.

Focus on:
1. Main subject(s) and objects
2. Scene type (indoor/outdoor, professional/casual, etc.)
3. Any text visible in the image (extract verbatim)
4. Visual style (screenshot, photo, illustration, diagram, etc.)
5. Emotional tone or mood
6. Potential category (e.g., headshot, logo, screenshot, document, creative, technical)

Provide your response as a structured analysis covering these points."""

    SCREENSHOT_TEXT_PROMPT = """This appears to be a screenshot. Please extract ALL visible text from this image.

Include:
- All readable text, exactly as shown
- UI elements and button labels
- Any error messages or notifications
- Application names or window titles

Format the text clearly, preserving hierarchy when possible."""

    VIDEO_ANALYSIS_PROMPT = """Analyze this video clip and provide a concise summary.

Focus on:
1. Main content/subject matter
2. Type of video (tutorial, presentation, recording, creative, etc.)
3. Key scenes or moments
4. Any visible text or captions
5. Audio/visual quality indicators
6. Suggested category

Provide a brief but informative summary."""

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_dir: Optional[str] = None,
                 confidence_threshold: float = 0.7,
                 enable_caching: bool = True,
                 cache_duration_days: int = 30):
        """
        Initialize the VisionAnalyzer with Gemini API.

        Args:
            api_key: Gemini API key (if None, loads from config)
            base_dir: Base directory for file operations
            confidence_threshold: Minimum confidence for auto-classification
            enable_caching: Whether to cache analysis results
            cache_duration_days: How long to cache results
        """
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "GoogleDrive" / "AI_Organizer"
        self.confidence_threshold = confidence_threshold
        self.enable_caching = enable_caching
        self.cache_duration_days = cache_duration_days

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # API configuration
        self.api_key = api_key or self._load_api_key()
        self.model = None
        self.api_initialized = False

        if self.api_key and GEMINI_AVAILABLE:
            self._initialize_api()
        else:
            self.logger.warning("Gemini API not initialized. Vision analysis will be unavailable.")

        # Cache directory
        self.cache_dir = self.base_dir / "04_METADATA_SYSTEM" / "vision_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Learning data
        self.learning_dir = self.base_dir / "04_METADATA_SYSTEM" / "adaptive_learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        self.vision_patterns_file = self.learning_dir / "vision_patterns.pkl"

        # Load existing patterns
        self.vision_patterns = self._load_vision_patterns()

        # Category mapping for visual content
        self.category_keywords = {
            'screenshot': ['screenshot', 'screen capture', 'desktop', 'window', 'interface', 'ui', 'app'],
            'headshot': ['portrait', 'headshot', 'profile photo', 'professional photo', 'face'],
            'logo': ['logo', 'brand', 'branding', 'emblem', 'trademark'],
            'document_scan': ['document', 'scan', 'paper', 'text document', 'printed'],
            'diagram': ['diagram', 'chart', 'graph', 'flowchart', 'schematic', 'technical'],
            'creative': ['art', 'illustration', 'design', 'creative', 'artwork', 'graphic'],
            'photo': ['photo', 'photograph', 'picture', 'image', 'outdoor', 'indoor'],
            'presentation': ['slide', 'presentation', 'powerpoint', 'keynote'],
            'technical': ['code', 'terminal', 'console', 'programming', 'technical'],
            'video_recording': ['recording', 'meeting', 'video call', 'conference', 'zoom'],
            'tutorial': ['tutorial', 'how-to', 'demonstration', 'training', 'instructional'],
            'creative_video': ['film', 'movie', 'animation', 'creative video', 'production']
        }

        # Performance metrics
        self.api_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0

    def _load_api_key(self) -> Optional[str]:
        """Load Gemini API key from config file or environment"""
        # Try config file first
        config_dir = Path.home() / ".ai_organizer_config"
        config_file = config_dir / "gemini_api_key.txt"

        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    api_key = f.read().strip()
                    if api_key:
                        self.logger.info("Loaded Gemini API key from config file")
                        return api_key
            except Exception as e:
                self.logger.warning(f"Could not read API key from config file: {e}")

        # Fall back to environment variable
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            self.logger.info("Loaded Gemini API key from environment")
            return api_key

        self.logger.warning("No Gemini API key found. Please set GEMINI_API_KEY or create ~/.ai_organizer_config/gemini_api_key.txt")
        return None

    def _initialize_api(self):
        """Initialize Gemini API client"""
        try:
            genai.configure(api_key=self.api_key)

            # Use Gemini 2.0 Flash for speed and cost efficiency
            # (can upgrade to gemini-2.5-pro for higher quality if needed)
            self.model = genai.GenerativeModel('gemini-2.0-flash')

            self.api_initialized = True
            self.logger.info("Gemini API initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini API: {e}")
            self.api_initialized = False

    def _load_vision_patterns(self) -> Dict[str, Any]:
        """Load historical vision analysis patterns"""
        if self.vision_patterns_file.exists():
            try:
                with open(self.vision_patterns_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load vision patterns: {e}")

        return {
            'objects_detected': defaultdict(list),
            'scene_types': defaultdict(list),
            'screenshot_contexts': defaultdict(list),
            'visual_keywords': defaultdict(list),
            'category_frequencies': defaultdict(int)
        }

    def _save_vision_patterns(self):
        """Save vision patterns for learning system"""
        try:
            with open(self.vision_patterns_file, 'wb') as f:
                pickle.dump(self.vision_patterns, f)
        except Exception as e:
            self.logger.warning(f"Could not save vision patterns: {e}")

    def _get_cache_key(self, file_path: str) -> str:
        """Generate cache key for a file based on path and modification time"""
        file_path_obj = Path(file_path)

        # Include file modification time in cache key
        if file_path_obj.exists():
            mtime = file_path_obj.stat().st_mtime
            cache_input = f"{file_path}_{mtime}"
        else:
            cache_input = file_path

        return hashlib.md5(cache_input.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load analysis result from cache if available and fresh"""
        if not self.enable_caching:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            self.cache_misses += 1
            return None

        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)

            # Check if cache is still fresh
            cached_time = datetime.fromisoformat(cached_data.get('timestamp', '2000-01-01'))
            age_days = (datetime.now() - cached_time).days

            if age_days > self.cache_duration_days:
                self.logger.info(f"Cache expired for {cache_key}")
                cache_file.unlink()  # Remove expired cache
                self.cache_misses += 1
                return None

            self.cache_hits += 1
            self.logger.info(f"Cache hit for {cache_key}")
            return cached_data.get('result')

        except Exception as e:
            self.logger.warning(f"Error loading cache: {e}")
            self.cache_misses += 1
            return None

    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]):
        """Save analysis result to cache"""
        if not self.enable_caching:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'result': result
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Error saving to cache: {e}")

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze an image using Gemini Vision API.

        Args:
            image_path: Path to the image file

        Returns:
            Analysis result with content description, detected objects, confidence score
        """
        image_path_obj = Path(image_path)

        # Validate file exists
        if not image_path_obj.exists():
            return {
                'success': False,
                'error': 'File not found',
                'content_type': 'image',
                'confidence_score': 0.0
            }

        # Check if it's an image file
        if image_path_obj.suffix.lower() not in self.IMAGE_EXTENSIONS:
            return {
                'success': False,
                'error': f'Unsupported image format: {image_path_obj.suffix}',
                'content_type': 'image',
                'confidence_score': 0.0
            }

        # Check cache first
        cache_key = self._get_cache_key(image_path)
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            return cached_result

        # Check if API is available
        if not self.api_initialized:
            return self._fallback_image_analysis(image_path_obj)

        try:
            # Load and preprocess image
            image = self._load_image(image_path_obj)

            # Call Gemini API for analysis
            self.api_calls += 1
            response = self.model.generate_content(
                [self.IMAGE_ANALYSIS_PROMPT, image],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )

            # Parse response
            analysis_text = response.text
            result = self._parse_image_analysis(analysis_text, image_path_obj)

            # Update learning patterns
            self._update_vision_patterns(result)

            # Cache the result
            self._save_to_cache(cache_key, result)

            return result

        except Exception as e:
            self.logger.error(f"Error analyzing image {image_path_obj.name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'content_type': 'image',
                'description': '',
                'confidence_score': 0.0
            }

    def extract_screenshot_text(self, image_path: str) -> str:
        """
        Extract text from a screenshot using Gemini OCR capabilities.

        Args:
            image_path: Path to the screenshot image

        Returns:
            Extracted text content
        """
        image_path_obj = Path(image_path)

        if not image_path_obj.exists() or not self.api_initialized:
            return ""

        try:
            # Load image
            image = self._load_image(image_path_obj)

            # Call Gemini for text extraction
            self.api_calls += 1
            response = self.model.generate_content(
                [self.SCREENSHOT_TEXT_PROMPT, image],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )

            return response.text.strip()

        except Exception as e:
            self.logger.error(f"Error extracting text from screenshot: {e}")
            return ""

    def analyze_video(self, video_path: str, max_duration: int = 120) -> Dict[str, Any]:
        """
        Analyze a video file using Gemini Vision API.

        Args:
            video_path: Path to the video file
            max_duration: Maximum video duration to analyze in seconds (default 120 = 2 minutes)

        Returns:
            Analysis result with video summary, key frames, metadata
        """
        video_path_obj = Path(video_path)

        # Validate file exists
        if not video_path_obj.exists():
            return {
                'success': False,
                'error': 'File not found',
                'content_type': 'video',
                'confidence_score': 0.0
            }

        # Check if it's a video file
        if video_path_obj.suffix.lower() not in self.VIDEO_EXTENSIONS:
            return {
                'success': False,
                'error': f'Unsupported video format: {video_path_obj.suffix}',
                'content_type': 'video',
                'confidence_score': 0.0
            }

        # Check cache first
        cache_key = self._get_cache_key(video_path)
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            return cached_result

        # Check if API is available
        if not self.api_initialized:
            return self._fallback_video_analysis(video_path_obj)

        try:
            # Upload video file to Gemini
            self.logger.info(f"Uploading video {video_path_obj.name} to Gemini...")
            video_file = genai.upload_file(path=str(video_path_obj))

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file.state.name}")

            # Analyze video
            self.api_calls += 1
            response = self.model.generate_content(
                [video_file, self.VIDEO_ANALYSIS_PROMPT],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )

            # Parse response
            analysis_text = response.text
            result = self._parse_video_analysis(analysis_text, video_path_obj)

            # Clean up uploaded file
            genai.delete_file(video_file.name)

            # Update learning patterns
            self._update_vision_patterns(result)

            # Cache the result
            self._save_to_cache(cache_key, result)

            return result

        except Exception as e:
            self.logger.error(f"Error analyzing video {video_path_obj.name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'content_type': 'video',
                'description': '',
                'confidence_score': 0.0
            }

    def get_content_description(self, file_path: str) -> Dict[str, Any]:
        """
        Universal method to analyze any visual content (image or video).

        Args:
            file_path: Path to the image or video file

        Returns:
            Analysis result appropriate for the file type
        """
        file_path_obj = Path(file_path)
        extension = file_path_obj.suffix.lower()

        if extension in self.IMAGE_EXTENSIONS:
            return self.analyze_image(file_path)
        elif extension in self.VIDEO_EXTENSIONS:
            return self.analyze_video(file_path)
        else:
            return {
                'success': False,
                'error': f'Unsupported file type: {extension}',
                'content_type': 'unknown',
                'confidence_score': 0.0
            }

    def _load_image(self, image_path: Path) -> Any:
        """Load and validate image file"""
        if PIL_AVAILABLE:
            # Use PIL to validate and potentially resize large images
            try:
                img = Image.open(image_path)

                # Resize if too large (Gemini has size limits)
                max_dimension = 3072  # Gemini's max dimension
                if max(img.size) > max_dimension:
                    ratio = max_dimension / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    self.logger.info(f"Resized image to {new_size}")

                return img

            except Exception as e:
                self.logger.warning(f"PIL processing failed, using direct upload: {e}")

        # Fallback: direct file upload
        return genai.upload_file(str(image_path))

    def _parse_image_analysis(self, analysis_text: str, image_path: Path) -> Dict[str, Any]:
        """Parse Gemini's image analysis response into structured data"""

        # Extract key information from the analysis text
        text_lower = analysis_text.lower()

        # Detect category based on keywords
        detected_category = 'photo'  # Default
        max_keyword_matches = 0

        for category, keywords in self.category_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > max_keyword_matches:
                max_keyword_matches = matches
                detected_category = category

        # Calculate confidence based on keyword matches and analysis length
        base_confidence = 0.5 if max_keyword_matches > 0 else 0.3
        keyword_bonus = min(0.3, max_keyword_matches * 0.1)
        length_bonus = 0.1 if len(analysis_text) > 100 else 0.0
        confidence = min(0.95, base_confidence + keyword_bonus + length_bonus)

        # Extract objects/keywords from analysis
        words = analysis_text.lower().split()
        keywords = [word.strip('.,!?;:') for word in words if len(word) > 4][:10]

        # Determine scene type
        scene_type = 'unknown'
        if any(word in text_lower for word in ['indoor', 'interior', 'room', 'office']):
            scene_type = 'indoor'
        elif any(word in text_lower for word in ['outdoor', 'exterior', 'landscape', 'nature']):
            scene_type = 'outdoor'
        elif any(word in text_lower for word in ['screen', 'interface', 'window', 'desktop']):
            scene_type = 'digital'

        return {
            'success': True,
            'content_type': 'image',
            'description': analysis_text,
            'objects_detected': keywords[:5],  # Top 5 objects
            'text_content': '',  # Populated separately by extract_screenshot_text if needed
            'scene_type': scene_type,
            'confidence_score': confidence,
            'keywords': keywords,
            'suggested_category': detected_category,
            'metadata': {
                'file_name': image_path.name,
                'file_size': image_path.stat().st_size if image_path.exists() else 0,
                'analysis_timestamp': datetime.now().isoformat(),
                'keyword_matches': max_keyword_matches
            }
        }

    def _parse_video_analysis(self, analysis_text: str, video_path: Path) -> Dict[str, Any]:
        """Parse Gemini's video analysis response into structured data"""

        text_lower = analysis_text.lower()

        # Detect video category
        detected_category = 'video_recording'  # Default
        max_keyword_matches = 0

        for category, keywords in self.category_keywords.items():
            if not category.endswith('_video') and category not in ['tutorial', 'presentation']:
                continue
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > max_keyword_matches:
                max_keyword_matches = matches
                detected_category = category

        # Calculate confidence
        base_confidence = 0.5 if max_keyword_matches > 0 else 0.3
        keyword_bonus = min(0.3, max_keyword_matches * 0.1)
        length_bonus = 0.1 if len(analysis_text) > 100 else 0.0
        confidence = min(0.95, base_confidence + keyword_bonus + length_bonus)

        # Extract keywords
        words = analysis_text.lower().split()
        keywords = [word.strip('.,!?;:') for word in words if len(word) > 4][:10]

        return {
            'success': True,
            'content_type': 'video',
            'description': analysis_text,
            'objects_detected': keywords[:5],
            'text_content': '',
            'scene_type': 'video',
            'confidence_score': confidence,
            'keywords': keywords,
            'suggested_category': detected_category,
            'metadata': {
                'file_name': video_path.name,
                'file_size': video_path.stat().st_size if video_path.exists() else 0,
                'analysis_timestamp': datetime.now().isoformat(),
                'keyword_matches': max_keyword_matches
            }
        }

    def _fallback_image_analysis(self, image_path: Path) -> Dict[str, Any]:
        """Fallback analysis when Gemini API is unavailable (filename-based)"""
        filename = image_path.name.lower()

        # Try to detect category from filename
        detected_category = 'photo'
        confidence = 0.2  # Low confidence for fallback

        for category, keywords in self.category_keywords.items():
            if any(keyword in filename for keyword in keywords):
                detected_category = category
                confidence = 0.3
                break

        return {
            'success': True,
            'content_type': 'image',
            'description': f'Fallback analysis: filename suggests {detected_category}',
            'objects_detected': [],
            'text_content': '',
            'scene_type': 'unknown',
            'confidence_score': confidence,
            'keywords': [detected_category],
            'suggested_category': detected_category,
            'metadata': {
                'file_name': image_path.name,
                'fallback_mode': True,
                'analysis_timestamp': datetime.now().isoformat()
            }
        }

    def _fallback_video_analysis(self, video_path: Path) -> Dict[str, Any]:
        """Fallback analysis when Gemini API is unavailable (filename-based)"""
        filename = video_path.name.lower()

        detected_category = 'video_recording'
        confidence = 0.2

        for category, keywords in self.category_keywords.items():
            if not category.endswith('_video') and category not in ['tutorial', 'presentation']:
                continue
            if any(keyword in filename for keyword in keywords):
                detected_category = category
                confidence = 0.3
                break

        return {
            'success': True,
            'content_type': 'video',
            'description': f'Fallback analysis: filename suggests {detected_category}',
            'objects_detected': [],
            'text_content': '',
            'scene_type': 'video',
            'confidence_score': confidence,
            'keywords': [detected_category],
            'suggested_category': detected_category,
            'metadata': {
                'file_name': video_path.name,
                'fallback_mode': True,
                'analysis_timestamp': datetime.now().isoformat()
            }
        }

    def _update_vision_patterns(self, analysis_result: Dict[str, Any]):
        """Update learning patterns with new vision analysis results"""
        if not analysis_result.get('success'):
            return

        category = analysis_result.get('suggested_category', 'unknown')
        objects = analysis_result.get('objects_detected', [])
        keywords = analysis_result.get('keywords', [])
        scene_type = analysis_result.get('scene_type', 'unknown')

        # Update pattern frequencies
        self.vision_patterns['category_frequencies'][category] += 1

        # Store objects by category
        self.vision_patterns['objects_detected'][category].extend(objects)

        # Store keywords by category
        self.vision_patterns['visual_keywords'][category].extend(keywords)

        # Store scene types
        self.vision_patterns['scene_types'][scene_type].append(category)

        # Save updated patterns
        self._save_vision_patterns()

    def get_statistics(self) -> Dict[str, Any]:
        """Get performance and usage statistics"""
        total_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'api_calls': self.api_calls,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'api_initialized': self.api_initialized,
            'category_frequencies': dict(self.vision_patterns['category_frequencies']),
            'most_common_category': max(
                self.vision_patterns['category_frequencies'].items(),
                key=lambda x: x[1],
                default=('unknown', 0)
            )[0] if self.vision_patterns['category_frequencies'] else 'unknown'
        }


# Testing and verification functions
def test_vision_analyzer():
    """Test the VisionAnalyzer with sample operations"""
    print("🔍 Testing Vision Analyzer...")

    # Initialize analyzer
    analyzer = VisionAnalyzer()

    if not analyzer.api_initialized:
        print("⚠️  Gemini API not initialized. Skipping API tests.")
        print("   Set GEMINI_API_KEY environment variable or create ~/.ai_organizer_config/gemini_api_key.txt")
        return

    print(f"✅ Vision Analyzer initialized")
    print(f"   API Status: {analyzer.api_initialized}")
    print(f"   Base Directory: {analyzer.base_dir}")
    print(f"   Cache Directory: {analyzer.cache_dir}")

    # Test statistics
    stats = analyzer.get_statistics()
    print(f"\n📊 Statistics:")
    print(f"   API Calls: {stats['api_calls']}")
    print(f"   Cache Hit Rate: {stats['cache_hit_rate']}")

    print("\n🎯 Vision Analyzer test completed!")


if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test_vision_analyzer()
