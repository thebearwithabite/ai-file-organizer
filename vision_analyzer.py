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

from gdrive_integration import get_ai_organizer_root, get_metadata_root

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
    IMAGE_ANALYSIS_PROMPT = """Analyze this image and provide the results in JSON format.
{category_list_str}
{identity_context}

IMPORTANT: Return ONLY a valid JSON object. Do not include any introductory text, preamble, or conversational filler.

Return a valid JSON object with this structure:
{{
    "description": "Detailed description of the image content, including main subjects, setting, and action.",
    "objects_detected": ["list", "of", "main", "objects"],
    "identified_entities": ["list", "of", "people/pets/places", "identified", "by", "ID", "or", "Unknown", "placeholder"],
    "scene_type": "indoor/outdoor/digital/unknown",
    "text_content": "Any visible text extracted verbatim",
    "visual_style": "photo/screenshot/illustration/diagram/etc",
    "emotional_tone": "Mood or tone of the image",
    "suggested_category": "Pick the best ID from the ALLOWED CATEGORIES list",
    "keywords": ["list", "of", "relevant", "keywords", "for", "search"]
}}"""

    SCREENSHOT_TEXT_PROMPT = """This appears to be a screenshot. Please extract ALL visible text from this image.
    
    Include:
    - All readable text, exactly as shown
    - UI elements and button labels
    - Any error messages or notifications
    - Application names or window titles
    
    Format the text clearly, preserving hierarchy when possible."""

    VIDEO_ANALYSIS_PROMPT = """Analyze this video clip and provide the results in JSON format.
{category_list_str}
{identity_context}

IMPORTANT: Return ONLY a valid JSON object. Do not include any introductory text, preamble, or conversational filler.

Return a valid JSON object with this structure:
{{
    "description": "Concise summary of the video content.",
    "objects_detected": ["list", "of", "key", "objects"],
    "identified_entities": ["list", "of", "entities", "recognized"],
    "scene_type": "video/animation/screen_recording",
    "text_content": "Any visible text or captions",
    "visual_style": "cinematic/amateur/professional/etc",
    "mood": "Emotional tone",
    "suggested_category": "Pick the best ID from the ALLOWED CATEGORIES list",
    "keywords": ["list", "of", "relevant", "keywords"]
}}"""

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
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
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
        self.cache_dir = get_metadata_root() /  "vision_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Learning data
        self.learning_dir = get_metadata_root() /  "adaptive_learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        self.vision_patterns_file = self.learning_dir / "vision_patterns.pkl"

        # Load existing patterns
        self.vision_patterns = self._load_vision_patterns()

        # Initialize Identity Service (Phase V4)
        try:
            from identity_service import IdentityService
            self.identity_service = IdentityService(get_metadata_root() / "config")
        except ImportError:
            self.logger.warning("IdentityService not found. Identity recognition will be disabled.")
            self.identity_service = None

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

        # LLM chatter stop words for fallback keyword extraction
        self.llm_stop_words = {
            'here', 'is', 'the', 'analysis', 'structured', 'results', 'image', 'photo',
            'video', 'description', 'objects', 'detected', 'scene', 'type', 'visual',
            'style', 'emotional', 'tone', 'suggested', 'category', 'keywords', 'for',
            'search', 'content', 'analyze', 'provide', 'format', 'json', 'object'
        }

        # Rate limiting for Gemini Free Tier compliance
        # Free tier: 15 RPM (requests per minute), 1,500 requests per day
        self.rate_limit_rpm = 15  # Requests per minute
        self.rate_limit_daily = 1500  # Requests per day
        self.min_request_interval = 4.0  # 4 seconds = 15 requests/minute
        self.last_request_time = 0

        # Daily quota tracking
        self.quota_file = get_metadata_root() /  "gemini_quota.json"
        self.daily_requests = self._load_daily_quota()

        self.logger.info(f"Rate limiting enabled: {self.rate_limit_rpm} RPM, {self.rate_limit_daily} daily")

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

    def _load_daily_quota(self) -> Dict[str, Any]:
        """Load daily quota tracking from file"""
        if self.quota_file.exists():
            try:
                with open(self.quota_file, 'r') as f:
                    quota_data = json.load(f)

                # Check if it's a new day - reset counter
                last_date = quota_data.get('date', '')
                today = datetime.now().strftime('%Y-%m-%d')

                if last_date != today:
                    self.logger.info(f"New day detected - resetting quota counter (was {quota_data.get('requests', 0)})")
                    return {'date': today, 'requests': 0}

                return quota_data
            except Exception as e:
                self.logger.warning(f"Could not load quota file: {e}")

        return {'date': datetime.now().strftime('%Y-%m-%d'), 'requests': 0}

    def _save_daily_quota(self):
        """Save daily quota tracking to file"""
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(self.daily_requests, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save quota file: {e}")

    def _check_rate_limit(self) -> bool:
        """
        Check if we can make an API request within rate limits.

        Returns:
            True if request is allowed, False if quota exceeded
        """
        # Check daily quota
        today = datetime.now().strftime('%Y-%m-%d')
        if self.daily_requests.get('date') != today:
            # New day - reset counter
            self.daily_requests = {'date': today, 'requests': 0}
            self._save_daily_quota()

        current_daily = self.daily_requests.get('requests', 0)
        if current_daily >= self.rate_limit_daily:
            self.logger.error(f"Daily quota exceeded: {current_daily}/{self.rate_limit_daily} requests used today")
            return False

        return True

    def _wait_for_rate_limit(self):
        """
        Enforce rate limiting by waiting if needed.
        Ensures minimum 4 seconds between requests (15 RPM compliance).
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            self.logger.info(f"Rate limiting: waiting {wait_time:.1f}s (15 RPM compliance)")
            time.sleep(wait_time)

        self.last_request_time = time.time()

        # Update daily counter
        self.daily_requests['requests'] = self.daily_requests.get('requests', 0) + 1
        self._save_daily_quota()

        # Log quota status every 10 requests
        if self.daily_requests['requests'] % 10 == 0:
            remaining = self.rate_limit_daily - self.daily_requests['requests']
            self.logger.info(f"Gemini API quota: {self.daily_requests['requests']}/{self.rate_limit_daily} used today ({remaining} remaining)")

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

    def analyze_image(self, image_path: str, project_context: Optional[str] = None, allowed_categories: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Analyze an image using Gemini Vision API.

        Args:
            image_path: Path to the image file
            project_context: Optional description of the creative project context (Phase V4)

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

        # Check cache if not in a specific project context (context might change results)
        if not project_context:
            cache_key = self._get_cache_key(str(image_path_obj)) # Use str() for consistency with _get_cache_key signature
            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                return cached_result
        else:
            # If project_context is present, we consider it a cache miss for the purpose of this block
            # as the context changes the expected output.
            self.cache_misses += 1

        # Check if API is available
        if not self.api_initialized:
            return self._fallback_image_analysis(image_path_obj)

        try:
            # Load and preprocess image
            image = self._load_image(image_path_obj)

            # Check rate limit before API call
            if not self._check_rate_limit():
                return {
                    'success': False,
                    'error': f'Daily API quota exceeded ({self.rate_limit_daily} requests/day)',
                    'content_type': 'image',
                    'confidence_score': 0.0,
                    'quota_exceeded': True
                }

            # Enforce rate limiting (15 RPM)
            self._wait_for_rate_limit()

            # Fetch identity context if available (Phase V4)
            identity_context = ""
            if self.identity_service:
                identity_context = self.identity_service.generate_prompt_context()
            
            # Incorporate Project Context (Phase V4)
            full_context = identity_context
            if project_context:
                full_context += f"\nPROJECT CONTEXT: This file belongs to the project: '{project_context}'. Tailor your descriptions and style analysis to this creative context."

            # Format category list for prompt
            cat_list_str = ""
            if allowed_categories:
                cat_list_str = "ALLOWED CATEGORIES (Pick the best fit from this list):\n"
                for cat in allowed_categories:
                    cat_list_str += f"- {cat['id']}: {cat['name']}\n"

            # Format the prompt
            prompt = self.IMAGE_ANALYSIS_PROMPT.format(
                identity_context=full_context,
                category_list_str=cat_list_str
            )

            # Call Gemini API for analysis
            self.api_calls += 1
            self.logger.info(f"Analyzing image: {image_path_obj.name} (quota: {self.daily_requests['requests']}/{self.rate_limit_daily})")
            response = self.model.generate_content(
                [prompt, image],
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

            # Check rate limit before API call
            if not self._check_rate_limit():
                self.logger.warning(f"Daily quota exceeded - skipping screenshot text extraction")
                return ""

            # Enforce rate limiting (15 RPM)
            self._wait_for_rate_limit()

            # Call Gemini for text extraction
            self.api_calls += 1
            self.logger.info(f"Extracting text from: {image_path_obj.name} (quota: {self.daily_requests['requests']}/{self.rate_limit_daily})")
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

    def analyze_video(self, video_path: str, max_duration: int = 120, project_context: Optional[str] = None, allowed_categories: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
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
            # Check rate limit before API call
            if not self._check_rate_limit():
                return {
                    'success': False,
                    'error': f'Daily API quota exceeded ({self.rate_limit_daily} requests/day)',
                    'content_type': 'video',
                    'confidence_score': 0.0,
                    'quota_exceeded': True
                }

            # Enforce rate limiting (15 RPM)
            self._wait_for_rate_limit()

            # Upload video file to Gemini
            self.logger.info(f"Uploading video {video_path_obj.name} to Gemini... (quota: {self.daily_requests['requests']}/{self.rate_limit_daily})")
            video_file = genai.upload_file(path=str(video_path_obj))

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file.state.name}")

            # Fetch identity context if available (Phase V4)
            identity_context = ""
            if self.identity_service:
                identity_context = self.identity_service.generate_prompt_context()
            
            # Incorporate Project Context (Phase V4)
            full_context = identity_context
            if project_context:
                full_context += f"\nPROJECT CONTEXT: This file belongs to the project: '{project_context}'. Tailor your descriptions and style analysis to this creative context."

            # Format category list for prompt
            cat_list_str = ""
            if allowed_categories:
                cat_list_str = "ALLOWED CATEGORIES (Pick the best fit from this list):\n"
                for cat in allowed_categories:
                    cat_list_str += f"- {cat['id']}: {cat['name']}\n"

            # Format the prompt
            prompt = self.VIDEO_ANALYSIS_PROMPT.format(
                identity_context=full_context,
                category_list_str=cat_list_str
            )

            # Analyze video
            self.api_calls += 1
            self.logger.info(f"Analyzing video: {video_path_obj.name}")
            response = self.model.generate_content(
                [video_file, prompt],
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
        
        try:
            # Clean up potential markdown code blocks and find JSON structure
            clean_text = analysis_text.strip()
            
            # Robust JSON extraction: Find first '{' and last '}'
            import re
            json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(1)
            else:
                # If no clear braces, try standard cleanup
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]
                if clean_text.startswith('```'):
                    clean_text = clean_text[3:]
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Try parsing as JSON first
            data = json.loads(clean_text)
            
            # Extract fields with defaults
            description = data.get('description', '')
            objects = data.get('objects_detected', [])
            entities = data.get('identified_entities', []) # Phase V4
            scene_type = data.get('scene_type', 'unknown')
            text_content = data.get('text_content', '')
            keywords = data.get('keywords', [])
            suggested_category = data.get('suggested_category', 'photo')
            
            # Calculate confidence
            confidence = 0.85 # High base confidence for structured JSON
            if not objects and not description:
                confidence = 0.4
            
            return {
                'success': True,
                'content_type': 'image',
                'description': description,
                'objects_detected': objects,
                'identified_entities': entities, # Phase V4
                'text_content': text_content,
                'scene_type': scene_type,
                'confidence_score': confidence,
                'keywords': keywords,
                'suggested_category': suggested_category,
                'metadata': {
                    'file_name': image_path.name,
                    'file_size': image_path.stat().st_size if image_path.exists() else 0,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'keyword_matches': len(keywords)
                }
            }
            
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse JSON from Gemini response for {image_path.name}. Falling back to text parsing.")
            # Fallback to original text parsing logic
            
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

            # Extract objects/keywords from analysis, filtering out stop words
            words = analysis_text.lower().split()
            keywords = []
            for word in words:
                clean_word = word.strip('.,!?;:"\'()[]{}')
                if len(clean_word) > 4 and clean_word not in self.llm_stop_words:
                    # Also check for possessives or common chatter like "here's"
                    if not (clean_word.endswith("'s") and clean_word[:-2] in self.llm_stop_words):
                        keywords.append(clean_word)
            keywords = keywords[:10]

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
        
        try:
            # Clean up potential markdown code blocks and find JSON structure
            clean_text = analysis_text.strip()
            
            # Robust JSON extraction
            import re
            json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(1)
            else:
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]
                if clean_text.startswith('```'):
                    clean_text = clean_text[3:]
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Try parsing as JSON first
            data = json.loads(clean_text)
            
            # Extract fields with defaults
            description = data.get('description', '')
            objects = data.get('objects_detected', [])
            entities = data.get('identified_entities', []) # Phase V4
            scene_type = data.get('scene_type', 'video')
            keywords = data.get('keywords', [])
            suggested_category = data.get('suggested_category', 'video_recording')
            
            # Calculate confidence
            confidence = 0.85 # High base confidence for structured JSON
            
            return {
                'success': True,
                'content_type': 'video',
                'description': description,
                'objects_detected': objects,
                'identified_entities': entities, # Phase V4
                'text_content': data.get('text_content', ''),
                'scene_type': scene_type,
                'confidence_score': confidence,
                'keywords': keywords,
                'suggested_category': suggested_category,
                'metadata': {
                    'file_name': video_path.name,
                    'file_size': video_path.stat().st_size if video_path.exists() else 0,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'keyword_matches': len(keywords)
                }
            }
            
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse JSON from Gemini response for {video_path.name}. Falling back to text parsing.")
            
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

        # Store identified entities (Phase V4)
        entities = analysis_result.get('identified_entities', [])
        if entities:
            if 'identified_entities' not in self.vision_patterns:
                from collections import defaultdict
                self.vision_patterns['identified_entities'] = defaultdict(list)
            self.vision_patterns['identified_entities'][category].extend(entities)

        # Save updated patterns
        self._save_vision_patterns()

    def analyze_for_veo_prompt(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze video specifically for VEO 3.1 prompt generation.

        This method provides VEO-structured analysis focusing on:
        - Shot type (wide, medium, closeup, etc.)
        - Camera movement (static, pan, dolly, etc.)
        - Lighting conditions (natural, dramatic, golden hour, etc.)
        - Mood and atmosphere
        - Scene context and objects
        - Color palette
        - Audio ambience suggestions

        Args:
            video_path: Path to video file

        Returns:
            VEO-structured analysis dictionary
        """
        video_path_obj = Path(video_path)

        # Validate file
        if not video_path_obj.exists():
            return self._fallback_veo_response(video_path_obj)

        # Check if API is available
        if not self.api_initialized:
            return self._fallback_veo_response(video_path_obj)

        try:
            # Check rate limit before API call
            if not self._check_rate_limit():
                return {
                    'success': False,
                    'error': f'Daily API quota exceeded ({self.rate_limit_daily} requests/day)',
                    'quota_exceeded': True
                }

            # Enforce rate limiting (15 RPM)
            self._wait_for_rate_limit()

            # Upload video to Gemini
            self.logger.info(f"🎬 Uploading video for VEO analysis: {video_path_obj.name} (quota: {self.daily_requests['requests']}/{self.rate_limit_daily})")
            video_file = genai.upload_file(path=str(video_path_obj))

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError(f"Video processing failed: {video_file.state.name}")

            # VEO-specific analysis prompt
            veo_prompt = """Analyze this video for cinematic characteristics. Provide:

1. SHOT TYPE: Describe the framing (extreme wide shot, wide shot, medium shot, close-up, extreme close-up)
2. CAMERA MOVEMENT: Identify camera motion (static, pan, tilt, dolly/tracking, handheld, crane)
3. LIGHTING: Describe lighting conditions (natural/sunlight, artificial/studio, dramatic/low-key, bright/high-key, backlit, golden hour)
4. MOOD: Overall emotional tone (professional, casual, dramatic, energetic, calm, mysterious, etc.)
5. SCENE CONTEXT: Brief description of the setting and what's happening
6. VISUAL STYLE: Cinematographic style (documentary, cinematic, handheld documentary, commercial, etc.)
7. OBJECTS/SUBJECTS: Key visible elements, people, props
8. COLOR PALETTE: Dominant colors and color grading
9. AUDIO AMBIENCE: What kind of ambient sound would match this scene
10. CHARACTER INFO: If people are visible, describe age/gender/appearance/behavior/expression

Format your response clearly with these categories."""

            # Call Gemini API
            self.api_calls += 1
            self.logger.info(f"🎬 Analyzing video for VEO prompt: {video_path_obj.name}")
            response = self.model.generate_content(
                [video_file, veo_prompt],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )

            # Parse response
            analysis_text = response.text
            veo_result = self._parse_veo_analysis(analysis_text, video_path_obj)

            # Clean up uploaded file
            genai.delete_file(video_file.name)

            self.logger.info(f"✅ VEO analysis complete: {video_path_obj.name}")

            return veo_result

        except Exception as e:
            self.logger.error(f"❌ VEO analysis failed: {e}")
            return self._fallback_veo_response(video_path_obj)

    def _parse_veo_analysis(self, analysis_text: str, video_path: Path) -> Dict[str, Any]:
        """
        Parse Gemini's VEO analysis into structured format.

        Args:
            analysis_text: Raw analysis from Gemini
            video_path: Path to video file

        Returns:
            Structured VEO analysis dictionary
        """
        text_lower = analysis_text.lower()

        # Extract shot type
        shot_type = 'Medium'  # Default
        shot_keywords = {
            'Extreme Wide': ['extreme wide', 'establishing', 'aerial view', 'very wide'],
            'Wide': ['wide shot', 'full body', 'entire scene', 'full frame'],
            'Medium': ['medium shot', 'mid shot', 'waist up', 'medium close'],
            'Close-up': ['close-up', 'close up', 'tight on', 'face shot'],
            'Extreme Close-up': ['extreme close', 'extreme closeup', 'macro', 'very close']
        }

        for shot_name, keywords in shot_keywords.items():
            if any(kw in text_lower for kw in keywords):
                shot_type = shot_name
                break

        # Extract camera movement
        camera_movement = 'Static'  # Default
        movement_keywords = {
            'Pan': ['pan', 'panning', 'horizontal sweep'],
            'Tilt': ['tilt', 'tilting', 'vertical movement'],
            'Dolly': ['dolly', 'tracking', 'push in', 'pull out', 'moving forward'],
            'Handheld': ['handheld', 'shaky', 'unstable', 'hand-held'],
            'Crane': ['crane', 'aerial movement', 'rising', 'descending'],
            'Static': ['static', 'stationary', 'fixed', 'still camera']
        }

        for movement_name, keywords in movement_keywords.items():
            if any(kw in text_lower for kw in keywords):
                camera_movement = movement_name
                break

        # Extract lighting
        lighting = 'Natural lighting'  # Default
        lighting_keywords = {
            'Natural daylight': ['natural', 'sunlight', 'daylight', 'outdoor'],
            'Artificial studio lighting': ['artificial', 'studio', 'indoor lights'],
            'Dramatic low-key lighting': ['dramatic', 'low-key', 'shadows', 'moody'],
            'Bright high-key lighting': ['bright', 'high-key', 'well-lit', 'even'],
            'Backlit': ['backlit', 'silhouette', 'rim light'],
            'Golden hour': ['golden hour', 'sunset', 'sunrise', 'warm light']
        }

        for lighting_name, keywords in lighting_keywords.items():
            if any(kw in text_lower for kw in keywords):
                lighting = lighting_name
                break

        # Extract mood
        mood_keywords = ['professional', 'casual', 'dramatic', 'energetic', 'calm',
                        'mysterious', 'tense', 'happy', 'serious', 'playful']
        detected_mood = 'Neutral'
        for mood_word in mood_keywords:
            if mood_word in text_lower:
                detected_mood = mood_word.capitalize()
                break

        # Extract scene context (first 200 chars of analysis)
        scene_context = analysis_text[:200].strip()
        if len(analysis_text) > 200:
            scene_context += "..."

        # Visual style detection
        visual_style = 'Standard video recording'
        style_keywords = {
            'Cinematic realism': ['cinematic', 'film-like', 'movie'],
            'Documentary style': ['documentary', 'observational', 'realistic'],
            'Commercial/advertising': ['commercial', 'polished', 'professional production'],
            'Handheld documentary': ['handheld documentary', 'verite', 'guerrilla'],
            'Music video style': ['music video', 'artistic', 'stylized']
        }

        for style_name, keywords in style_keywords.items():
            if any(kw in text_lower for kw in keywords):
                visual_style = style_name
                break

        # Extract color information
        color_words = ['blue', 'red', 'green', 'yellow', 'orange', 'purple', 'brown',
                      'black', 'white', 'gray', 'warm', 'cool', 'vibrant', 'muted']
        colors_found = [color for color in color_words if color in text_lower]

        # Audio ambience
        audio_ambience = 'Ambient sound'
        if 'quiet' in text_lower or 'silent' in text_lower:
            audio_ambience = 'Quiet atmosphere, minimal sound'
        elif 'music' in text_lower:
            audio_ambience = 'Background music'
        elif 'dialogue' in text_lower or 'speaking' in text_lower:
            audio_ambience = 'Dialogue and conversation'
        elif 'outdoor' in text_lower or 'nature' in text_lower:
            audio_ambience = 'Outdoor ambience, natural sounds'
        elif 'indoor' in text_lower or 'office' in text_lower:
            audio_ambience = 'Indoor ambience, room tone'

        # Character detection
        character_info = ''
        character_description = ''
        behavior = ''
        expression = ''

        if any(word in text_lower for word in ['person', 'people', 'man', 'woman', 'male', 'female']):
            # Extract character information from text
            if 'male' in text_lower or 'man' in text_lower:
                character_info = 'male'
            elif 'female' in text_lower or 'woman' in text_lower:
                character_info = 'female'

            # Age estimation
            age_keywords = ['young', 'adult', 'middle-aged', 'elderly', 'child', 'teenager']
            for age in age_keywords:
                if age in text_lower:
                    character_info += f', {age}'
                    break

            # Behavior
            behavior_keywords = ['sitting', 'standing', 'walking', 'talking', 'working',
                               'typing', 'gesturing', 'looking']
            for beh in behavior_keywords:
                if beh in text_lower:
                    behavior = beh
                    break

            # Expression
            expression_keywords = ['smiling', 'serious', 'focused', 'laughing', 'concentrated']
            for exp in expression_keywords:
                if exp in text_lower:
                    expression = exp
                    break

        # Calculate confidence based on analysis quality
        confidence = 0.7  # Base confidence with AI analysis
        if len(analysis_text) > 200:
            confidence += 0.1
        if colors_found:
            confidence += 0.05
        if character_info:
            confidence += 0.1
        confidence = min(0.95, confidence)

        return {
            'shot_type': shot_type,
            'camera_movement': camera_movement,
            'lighting': lighting,
            'mood': detected_mood,
            'scene_context': scene_context,
            'visual_style': visual_style,
            'objects': [],  # Would need more sophisticated parsing
            'color_palette': colors_found if colors_found else ['unknown'],
            'audio_ambience': audio_ambience,
            'character_info': character_info,
            'character_description': character_description,
            'behavior': behavior,
            'expression': expression,
            'confidence_score': confidence,
            'raw_analysis': analysis_text
        }

    def _fallback_veo_response(self, video_path: Path) -> Dict[str, Any]:
        """Fallback VEO response when API unavailable"""
        return {
            'shot_type': 'Medium',
            'camera_movement': 'Static',
            'lighting': 'Natural lighting',
            'mood': 'Neutral',
            'scene_context': f'Video: {video_path.stem}',
            'visual_style': 'Standard video recording',
            'objects': [],
            'color_palette': ['unknown'],
            'audio_ambience': 'Ambient sound',
            'character_info': '',
            'character_description': '',
            'behavior': '',
            'expression': '',
            'confidence_score': 0.3,
            'fallback_mode': True
        }

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
