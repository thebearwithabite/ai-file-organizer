#!/usr/bin/env python3
"""
Unified Classification Service

This service acts as the central "brain" for the AI File Organizer, routing
files to the appropriate analysis engine and integrating adaptive learning.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Import the analysis engines that will be integrated
from content_extractor import ContentExtractor
from audio_analyzer import AudioAnalyzer
from vision_analyzer import VisionAnalyzer

# Import the learning system
from universal_adaptive_learning import UniversalAdaptiveLearning

class UnifiedClassificationService:
    """
    A single, intelligent service to handle classification for any file type.
    """

    def __init__(self):
        """Initialize with minimal overhead - lazy load heavy components."""
        print("Initializing Unified Classification Service (lazy mode)...")

        # Initialize base directory
        self.text_analyzer = ContentExtractor()
        base_dir = getattr(self.text_analyzer, 'base_dir', os.getcwd())
        self.base_dir = Path(base_dir)

        # Lazy-loaded components (initialized on first use)
        self._learning_system = None
        self._audio_analyzer = None
        self._vision_analyzer = None
        self.learning_enabled = True
        self.vision_enabled = True

        # Initialize obvious patterns for fast classification
        self._init_obvious_patterns()

        print("✅ Unified Classification Service Ready (lazy mode - analyzers will load on demand)")

    @property
    def learning_system(self):
        """Lazy load learning system on first use"""
        if self._learning_system is None and self.learning_enabled:
            try:
                print("🧠 Loading adaptive learning system...")
                self._learning_system = UniversalAdaptiveLearning(base_dir=str(self.base_dir))
                print("✅ Adaptive learning system initialized")
            except Exception as e:
                self._learning_system = None
                self.learning_enabled = False
                print(f"⚠️  Adaptive learning disabled: {e}")
        return self._learning_system

    @property
    def audio_analyzer(self):
        """Lazy load audio analyzer on first use"""
        if self._audio_analyzer is None:
            print("🎵 Loading audio analyzer...")
            openai_api_key = os.getenv('OPENAI_API_KEY')
            self._audio_analyzer = AudioAnalyzer(
                base_dir=str(self.base_dir),
                confidence_threshold=0.7,
                openai_api_key=openai_api_key
            )
            print("✅ Audio analyzer loaded")
        return self._audio_analyzer

    @property
    def vision_analyzer(self):
        """Lazy load vision analyzer on first use"""
        if self._vision_analyzer is None and self.vision_enabled:
            try:
                print("👁️  Loading vision analyzer...")
                self._vision_analyzer = VisionAnalyzer(base_dir=str(self.base_dir))
                self.vision_enabled = self._vision_analyzer.api_initialized
                if self.vision_enabled:
                    print("✅ Vision analysis enabled with Gemini API")
                else:
                    print("⚠️  Vision analysis enabled (fallback mode only)")
            except Exception as e:
                self._vision_analyzer = None
                self.vision_enabled = False
                print(f"⚠️  Vision analysis disabled: {e}")
        return self._vision_analyzer

    def _normalize_confidence(self, result: Dict[str, Any], file_path: Path, file_type: str) -> Dict[str, Any]:
        """
        Normalize classification results to ALWAYS include a numeric confidence field.
        Also normalizes category strings (Section E: remove + symbols).

        Implements inference rules from Section D requirements.

        Inference Rules:
        - Screenshots detected → confidence = 0.9
        - Unknown category → confidence = 0.5
        - Audio files → confidence = 0.7 (if not already set higher)
        - Text/PDF files → confidence = 0.6 (if not already set higher)
        - Fallback for any classification → confidence = 0.4

        Category Normalization (Section E):
        - Strip "+" symbols and replace with underscores
        - Example: "sfx_consciousness+mysterious" → "sfx_consciousness_mysterious"
        - Ensures categories can be properly routed through category_mapping

        Args:
            result: Classification result from any analyzer
            file_path: Path to file being classified
            file_type: Detected file type (audio, image, video, text, generic)

        Returns:
            Normalized result with guaranteed confidence field and normalized category
        """
        # SECTION E: Normalize category strings - strip + symbols
        category = result.get('category', 'unknown')
        if category and '+' in category:
            # Replace + with underscore to make valid category identifier
            normalized_category = category.replace('+', '_')
            print(f"📝 Category normalization: '{category}' → '{normalized_category}'")
            result['category'] = normalized_category
            category = normalized_category

        # Check if confidence field exists (handle both 'confidence' and 'confidence_score')
        confidence = result.get('confidence')
        if confidence is None:
            confidence = result.get('confidence_score')

        # Apply inference rules if confidence is missing or zero
        if confidence is None or confidence == 0.0:
            source = result.get('source', '')

            # Rule 1: Screenshots → 0.9
            if 'screenshot' in category.lower() or 'screenshot' in source.lower():
                confidence = 0.9

            # Rule 2: Unknown category → 0.5
            elif category == 'unknown' or category == 'needs_review':
                confidence = 0.5

            # Rule 3: Audio files → 0.7
            elif file_type == 'audio':
                confidence = 0.7

            # Rule 4: Text/PDF files → 0.6
            elif file_type == 'text':
                confidence = 0.6

            # Rule 5: Fallback → 0.4
            else:
                confidence = 0.4

        # Ensure confidence is a float between 0.0 and 1.0
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.4  # Fallback if conversion fails

        # Update result with normalized confidence
        result['confidence'] = confidence

        # Remove confidence_score if it exists to avoid confusion
        if 'confidence_score' in result:
            del result['confidence_score']

        return result

    def _init_obvious_patterns(self):
        """Initialize obvious patterns for fast, rule-based classification"""
        self.obvious_patterns = {
            'screenshot': {
                'keywords': ['screenshot', 'screen shot', 'screen_shot'],
                'category': 'visual_assets_screenshots',
                'confidence': 0.95
            },
            'installer': {
                'extensions': ['.dmg', '.pkg', '.iso'],
                'keywords': ['installer', 'setup', 'install'],
                'category': 'installers',
                'confidence': 0.95
            },
            'archive': {
                'extensions': ['.zip', '.rar', '.7z', '.tar', '.gz'],
                'category': 'archives',
                'confidence': 0.90
            },
            'document': {
                'extensions': ['.pdf', '.docx', '.doc', '.txt', '.md', '.pages'],
                'category': 'documents',
                'confidence': 0.60  # Lower confidence to allow content analysis to override
            },
            'image': {
                'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic'],
                'category': 'images',
                'confidence': 0.60  # Lower confidence to allow vision analysis to override
            },
            'audio': {
                'extensions': ['.mp3', '.wav', '.m4a', '.flac', '.aiff'],
                'category': 'audio',
                'confidence': 0.70  # Moderate confidence
            },
            'video': {
                'extensions': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
                'category': 'video',
                'confidence': 0.70  # Moderate confidence
            }
        }

    def _check_obvious_classification(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Check for obvious patterns that don't require AI analysis.
        Returns a classification result if a strong match is found, else None.
        """
        filename = file_path.name.lower()
        extension = file_path.suffix.lower()
        
        # Check specific patterns first
        
        # 1. Screenshots (High Confidence)
        if 'screenshot' in filename:
            return {
                'source': 'Obvious Pattern (Screenshot)',
                'category': 'visual_assets_screenshots',
                'confidence': 0.95,
                'reasoning': ['Filename contains "screenshot"'],
                'suggested_filename': file_path.name
            }
            
        # 2. Installers (High Confidence)
        if extension in self.obvious_patterns['installer']['extensions']:
            return {
                'source': 'Obvious Pattern (Installer)',
                'category': 'installers',
                'confidence': 0.95,
                'reasoning': [f'Extension {extension} indicates installer'],
                'suggested_filename': file_path.name
            }
            
        # 3. Archives (High Confidence)
        if extension in self.obvious_patterns['archive']['extensions']:
            return {
                'source': 'Obvious Pattern (Archive)',
                'category': 'archives',
                'confidence': 0.90,
                'reasoning': [f'Extension {extension} indicates archive'],
                'suggested_filename': file_path.name
            }

        return None

    def classify_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Classifies a file by routing it to the correct analysis engine.

        GUARANTEED: Returns a dict with a numeric 'confidence' field (0.0 to 1.0).
        This method is the single source of truth for all file classifications.

        Args:
            file_path: The absolute path to the file to classify.

        Returns:
            A dictionary containing the classification result with guaranteed 'confidence' field.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return self._normalize_confidence(
                {"error": "File not found", "category": "unknown", "confidence": 0.0},
                file_path,
                "unknown"
            )

        # 0. Check for obvious patterns first (Fast Path)
        obvious_result = self._check_obvious_classification(file_path)
        if obvious_result:
            print(f"⚡ Fast classification for {file_path.name}: {obvious_result['category']}")
            return self._normalize_confidence(obvious_result, file_path, "generic")

        # PERFORMANCE OPTIMIZATION: Skip large files to avoid slow vision/audio analysis
        try:
            file_size_bytes = file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            MAX_AUTO_PROCESS_SIZE_MB = 10  # 10MB limit for automatic processing

            if file_size_mb > MAX_AUTO_PROCESS_SIZE_MB:
                print(f"⚠️  Skipping {file_path.name} ({file_size_mb:.1f}MB) - too large for automatic processing")
                return self._normalize_confidence(
                    {
                        'category': 'unknown',
                        'confidence': 0.0,
                        'reasoning': [
                            f'File too large ({file_size_mb:.1f}MB) for automatic processing',
                            'Large files should be manually organized to avoid performance issues'
                        ],
                        'suggested_filename': file_path.name,
                        'source': 'FileSize Check (Performance Protection)'
                    },
                    file_path,
                    "unknown"
                )
        except (OSError, PermissionError) as e:
            print(f"⚠️  Could not check file size for {file_path.name}: {e}")

        # 1. Determine file type (e.g., by MIME type or extension)
        file_type = self._get_file_type(file_path)

        # 2. Consult the Learning Service for historical context (Future Step)
        # historical_context = self.learning_service.get_context(file_path)

        # 3. Route to the appropriate analysis engine
        if file_type == 'audio':
            result = self._classify_audio_file(file_path)
        elif file_type == 'image':
            result = self._classify_image_file(file_path)
        elif file_type == 'video':
            result = self._classify_video_file(file_path)
        elif file_type == 'text':
            result = self._classify_text_document(file_path)
        else:
            result = self._classify_generic_file(file_path)

        # 4. Normalize confidence to guarantee it exists
        result = self._normalize_confidence(result, file_path, file_type)

        # 5. Blend analysis with historical context (Future Step)
        # final_result = self.learning_service.blend_with_history(result, historical_context)

        return result

    def _get_file_type(self, file_path: Path) -> str:
        """Determine the general file type (audio, image, video, text, etc.)."""
        extension = file_path.suffix.lower()
        if extension in ['.wav', '.mp3', '.aiff', '.flac', '.m4a']:
            return 'audio'
        if extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.heic', '.heif']:
            return 'image'
        if extension in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']:
            return 'video'
        if extension in ['.pdf', '.docx', '.txt', '.md']:
            return 'text'
        return 'generic'

    def _classify_text_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Classify a text document using full content analysis.
        Uses ContentExtractor to read document content and applies keyword analysis.
        
        Confidence Scoring Algorithm:
        - Base confidence: 55% for any keyword match
        - Keyword bonus: +25% for each additional keyword beyond the first
        - Strong keyword bonus: +15% for documents with 2+ strong keywords (contract, agreement, payment, script, code)
        - Content bonus: +10% for keywords found in document content (not just filename)
        - 85% threshold for ADHD-friendly auto-classification without user intervention
        - Files with "contract" + "agreement" keywords achieve 100% confidence
        """
        print(f"DEBUG: --- Classifying Text Document: {file_path.name} ---")
        try:
            # Extract the full content of the document
            content_data = self.text_analyzer.extract_content(file_path)

            if not content_data or not content_data.get('text'):
                print("DEBUG: Failed to extract content or content is empty.")
                return {
                    'source': 'Text Classifier',
                    'category': 'unknown',
                    'confidence': 0.10,
                    'reasoning': ['Failed to extract document content'],
                    'suggested_filename': file_path.name
                }

            full_text = content_data['text'].lower()
            filename = file_path.name.lower()
            print(f"DEBUG: Content length: {len(full_text)} chars")

            best_category = 'unknown'
            best_confidence = 0.0
            reasoning = []

            # Load classification rules directly from JSON file
            import json
            rules_file = Path(__file__).parent / "classification_rules.json"
            if rules_file.exists():
                with open(rules_file, 'r') as f:
                    rules_data = json.load(f)
                rules = rules_data.get('document_types', {})
            else:
                # Fallback rules if file doesn't exist
                rules = {
                    'contracts': {
                        'keywords': ['contract', 'agreement', 'deal memo', 'nda']
                    },
                    'financial': {
                        'keywords': ['payment', 'report', 'residual', 'tax', 'invoice']
                    }
                }
            print(f"DEBUG: Loaded {len(rules)} classification rules.")

            for category, rule_details in rules.items():
                keyword_matches = 0
                matched_keywords = []

                for keyword in rule_details.get('keywords', []):
                    if keyword.lower() in full_text:
                        keyword_matches += 1
                        matched_keywords.append(keyword)
                    elif keyword.lower() in filename:
                        keyword_matches += 0.5
                        matched_keywords.append(f"{keyword} (in filename)")
                
                category_confidence = 0.0
                if keyword_matches > 0:
                    print(f"DEBUG: [{category}] Found {keyword_matches} keyword matches: {matched_keywords}")
                    base_confidence = 0.55
                    keyword_bonus = (keyword_matches - 1) * 0.25
                    
                    strong_keywords = ['contract', 'agreement', 'payment', 'script', 'code']
                    strong_matches = sum(1 for kw in matched_keywords if kw.split(' ')[0] in strong_keywords)

                    strong_bonus = 0.15 if strong_matches >= 2 else 0
                    content_bonus = 0.1 if any('(in filename)' not in kw for kw in matched_keywords) else 0

                    # Calculate final confidence score for ADHD-friendly auto-classification
                    # Confidence >= 85% enables automatic file organization without user questions
                    category_confidence = base_confidence + keyword_bonus + strong_bonus + content_bonus
                    print(f"DEBUG: [{category}] Base: {base_confidence}, Bonus: {keyword_bonus}, Strong: {strong_bonus}, Content: {content_bonus} -> Total: {category_confidence}")

                if category_confidence > best_confidence:
                    print(f"DEBUG: [{category}] New best category! Score: {category_confidence:.2f}")
                    best_confidence = category_confidence
                    best_category = category
                    reasoning = [f"Found content keywords: {', '.join(matched_keywords[:3])}"]

            if best_confidence < 0.2:
                print("DEBUG: No strong matches found. Defaulting to 'text_document' with 0.2 confidence.")
                best_category = 'text_document'
                best_confidence = 0.2
                reasoning = ['Document contains text but no specific category indicators']

            final_confidence = min(best_confidence, 1.0)
            print(f"DEBUG: Final decision: Category='{best_category}', Confidence={final_confidence:.2f}")

            # Generate intelligent filename if we have strong keywords
            suggested_filename = file_path.name
            if best_confidence > 0.6 and len(matched_keywords) > 0:
                # Use the top 2 keywords to form a descriptive name
                # Clean keywords (remove 'in filename' suffix)
                clean_keywords = [k.split(' (')[0].replace(' ', '_') for k in matched_keywords]
                # Remove duplicates while preserving order
                unique_keywords = list(dict.fromkeys(clean_keywords))
                
                # Create descriptive prefix
                prefix = "_".join(unique_keywords[:2])
                
                # Preserve original extension
                extension = file_path.suffix
                
                # If original name is generic (e.g. "Untitled", "Doc"), replace it entirely
                if "untitled" in filename or "doc" in filename or "scan" in filename:
                    suggested_filename = f"{best_category}_{prefix}{extension}"
                else:
                    # Otherwise append category/keywords to original name
                    suggested_filename = f"{file_path.stem}_{prefix}{extension}"
            
            return {
                'source': 'Text Classifier',
                'category': best_category,
                'confidence': final_confidence,
                'reasoning': reasoning,
                'suggested_filename': suggested_filename
            }

        except Exception as e:
            return {
                'source': 'Text Classifier',
                'category': 'unknown',
                'confidence': 0.10,
                'reasoning': [f'Error analyzing document: {str(e)}'],
                'suggested_filename': file_path.name
            }

    def _classify_audio_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Classify audio file using the integrated AudioAnalyzer with AI-powered analysis
        and spectral analysis using librosa.
        """
        try:
            # Perform spectral analysis first (works without OpenAI API)
            spectral_result = self.audio_analyzer.analyze_audio_spectral(file_path, max_duration=30)

            # Use AudioAnalyzer for intelligent classification (requires OpenAI API)
            classification_result = self.audio_analyzer.classify_audio_file(file_path)

            if classification_result:
                # Merge spectral analysis with AI classification
                metadata = {
                    'mood': classification_result.get('mood'),
                    'intensity': classification_result.get('intensity'),
                    'energy_level': classification_result.get('energy_level'),
                    'tags': classification_result.get('tags', []),
                    'thematic_notes': classification_result.get('thematic_notes'),
                    'target_folder': classification_result.get('target_folder'),
                    'discovered_elements': classification_result.get('discovered_elements', [])
                }

                # Add spectral analysis data if available
                if spectral_result.get('success'):
                    metadata['bpm'] = spectral_result.get('bpm', 0)
                    metadata['spectral_mood'] = spectral_result.get('mood', 'unknown')
                    metadata['spectral_content_type'] = spectral_result.get('content_type', 'unknown')
                    metadata['spectral_features'] = spectral_result.get('spectral_features', {})
                    metadata['energy_level_spectral'] = spectral_result.get('energy_level_scale', 0)

                # Convert AudioAnalyzer result to unified format
                return {
                    'source': 'Audio Classifier (AI + Spectral Analysis)',
                    'category': classification_result.get('category', 'audio'),
                    'confidence': classification_result.get('confidence', 0.0),
                    'reasoning': [
                        classification_result.get('reasoning', 'AI-powered audio analysis'),
                        f"Mood: {classification_result.get('mood', 'unknown')}",
                        f"Intensity: {classification_result.get('intensity', 'unknown')}",
                        f"Energy Level: {classification_result.get('energy_level', 0)}/10",
                        f"BPM: {spectral_result.get('bpm', 0):.1f}" if spectral_result.get('success') else "",
                        f"Spectral Content: {spectral_result.get('content_type', 'unknown')}" if spectral_result.get('success') else "",
                        f"Tags: {', '.join(classification_result.get('tags', []))}"
                    ],
                    'suggested_filename': classification_result.get('suggested_filename', file_path.name),
                    'metadata': metadata
                }

            # Fallback to spectral-only classification if AI classification unavailable
            elif spectral_result.get('success'):
                return self._classify_audio_spectral_only(file_path, spectral_result)

            else:
                # Both analyses failed - use basic fallback
                return self._classify_audio_fallback(file_path)

        except Exception as e:
            # Error handling - fallback to basic analysis
            return {
                'source': 'Audio Classifier (Error Fallback)',
                'category': 'audio',
                'confidence': 0.2,
                'reasoning': [f'AudioAnalyzer error: {str(e)}', 'Using basic fallback classification'],
                'suggested_filename': file_path.name
            }

    def _classify_audio_spectral_only(self, file_path: Path, spectral_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify audio file using only spectral analysis (when AI classification unavailable)
        """
        content_type = spectral_result.get('content_type', 'audio')
        mood = spectral_result.get('mood', 'ambient')
        bpm = spectral_result.get('bpm', 0)
        energy_level = spectral_result.get('energy_level_scale', 0)

        # Map content type to category
        category_map = {
            'music': 'music_ambient',
            'sfx': 'sfx_environmental',
            'voice': 'voice_element',
            'ambient': 'music_ambient'
        }
        category = category_map.get(content_type, 'audio')

        # Calculate confidence based on spectral analysis quality
        confidence = 0.6 if spectral_result.get('success') else 0.3

        return {
            'source': 'Audio Classifier (Spectral Analysis Only)',
            'category': category,
            'confidence': confidence,
            'reasoning': [
                f"Spectral analysis detected: {content_type}",
                f"Mood: {mood}",
                f"BPM: {bpm:.1f}",
                f"Energy Level: {energy_level}/10",
                "Note: AI classification unavailable, using spectral analysis only"
            ],
            'suggested_filename': file_path.name,
            'metadata': {
                'mood': mood,
                'bpm': bpm,
                'content_type': content_type,
                'energy_level': energy_level,
                'spectral_features': spectral_result.get('spectral_features', {}),
                'spectral_only': True
            }
        }

    def _classify_audio_fallback(self, file_path: Path) -> Dict[str, Any]:
        """
        Fallback method for audio classification when AudioAnalyzer is unavailable.
        Uses basic filename and metadata analysis.
        """
        filename = file_path.name.lower()
        category = 'audio'
        confidence = 0.2  # Lower confidence without AI analysis
        reasoning = ['AudioAnalyzer unavailable, using fallback analysis']

        # Simple keyword matching
        if any(keyword in filename for keyword in ['sfx', 'sound_effect', 'effect', 'fx']):
            category = 'sfx'
            confidence = 0.3
            reasoning.append("Filename contains sound effect keywords")
        elif any(keyword in filename for keyword in ['music', 'song', 'track', 'ambient']):
            category = 'music'
            confidence = 0.3
            reasoning.append("Filename contains music keywords")
        elif any(keyword in filename for keyword in ['voice', 'vocal', 'speech', 'dialogue']):
            category = 'voice'
            confidence = 0.3
            reasoning.append("Filename contains voice keywords")
        elif any(keyword in filename for keyword in ['podcast', 'interview', 'conversation']):
            category = 'voice'
            confidence = 0.3
            reasoning.append("Filename suggests spoken content")

        # Add file format information
        file_format = file_path.suffix.lower().lstrip('.')
        reasoning.append(f"Audio format: {file_format}")

        return {
            'source': 'Audio Classifier (Fallback)',
            'category': category,
            'confidence': confidence,
            'reasoning': reasoning,
            'suggested_filename': file_path.name
        }

    def _classify_image_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Classify image file using Gemini Vision API

        Args:
            file_path: Path to image file

        Returns:
            Classification result with vision analysis
        """
        if not self.vision_enabled or not self.vision_analyzer:
            # Fallback to basic classification
            return self._fallback_classification(file_path, 'image')

        try:
            # Analyze image with Gemini Vision
            vision_result = self.vision_analyzer.analyze_image(str(file_path))

            if not vision_result.get('success'):
                print(f"⚠️  Vision analysis failed for {file_path.name}, using fallback")
                return self._fallback_classification(file_path, 'image')

            # Map vision results to unified classification format
            classification = {
                'source': 'Image Classifier (Gemini Vision)',
                'category': vision_result.get('suggested_category', 'image'),
                'confidence': vision_result.get('confidence_score', 0.0),
                'reasoning': [
                    vision_result.get('description', '')[:200],  # Truncate description
                    f"Scene type: {vision_result.get('scene_type', 'unknown')}",
                    f"Objects detected: {', '.join(vision_result.get('objects_detected', [])[:3])}"
                ],
                'suggested_filename': file_path.name,
                'metadata': {
                    'keywords': vision_result.get('keywords', []),
                    'objects_detected': vision_result.get('objects_detected', []),
                    'scene_type': vision_result.get('scene_type', 'unknown'),
                    'text_content': vision_result.get('text_content', ''),
                    'analysis_timestamp': vision_result.get('metadata', {}).get('analysis_timestamp', '')
                }
            }

            # Generate intelligent filename from vision results
            suggested_filename = file_path.name
            if vision_result.get('suggested_filename'):
                suggested_filename = vision_result.get('suggested_filename')
            elif vision_result.get('keywords'):
                # Fallback: construct from keywords if vision didn't suggest a name
                keywords = [k.replace(' ', '_') for k in vision_result.get('keywords', [])[:3]]
                if keywords:
                    extension = file_path.suffix
                    suggested_filename = f"{classification['category']}_{'_'.join(keywords)}{extension}"

            classification['suggested_filename'] = suggested_filename

            # Record in learning system if available
            if self.learning_enabled and self.learning_system:
                self.learning_system.record_classification(
                    file_path=str(file_path),
                    predicted_category=classification['category'],
                    confidence=classification['confidence'],
                    features={
                        'keywords': classification['metadata']['keywords'],
                        'visual_objects': vision_result.get('objects_detected', []),
                        'scene_type': vision_result.get('scene_type', '')
                    }
                )

            return classification

        except Exception as e:
            print(f"❌ Error classifying image {file_path.name}: {e}")
            return self._fallback_classification(file_path, 'image')

    def _classify_video_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Classify video file using Gemini Vision API

        Args:
            file_path: Path to video file

        Returns:
            Classification result with vision analysis
        """
        if not self.vision_enabled or not self.vision_analyzer:
            return self._fallback_classification(file_path, 'video')

        try:
            # Analyze video with Gemini Vision (2 minute limit)
            vision_result = self.vision_analyzer.analyze_video(str(file_path))

            if not vision_result.get('success'):
                print(f"⚠️  Vision analysis failed for {file_path.name}, using fallback")
                return self._fallback_classification(file_path, 'video')

            # Map vision results to unified classification format
            classification = {
                'source': 'Video Classifier (Gemini Vision)',
                'category': vision_result.get('suggested_category', 'video'),
                'confidence': vision_result.get('confidence_score', 0.0),
                'reasoning': [
                    vision_result.get('description', '')[:200],  # Truncate description
                    f"Video type detected"
                ],
                'suggested_filename': file_path.name,
                'metadata': {
                    'keywords': vision_result.get('keywords', []),
                    'video_type': vision_result.get('metadata', {}).get('video_type', 'unknown'),
                    'analysis_timestamp': vision_result.get('metadata', {}).get('analysis_timestamp', '')
                }
            }

            # Record in learning system if available
            if self.learning_enabled and self.learning_system:
                self.learning_system.record_classification(
                    file_path=str(file_path),
                    predicted_category=classification['category'],
                    confidence=classification['confidence'],
                    features={
                        'keywords': classification['metadata']['keywords'],
                        'video_type': vision_result.get('metadata', {}).get('video_type', 'unknown')
                    }
                )

            return classification

        except Exception as e:
            print(f"❌ Error classifying video {file_path.name}: {e}")
            return self._fallback_classification(file_path, 'video')

    def _fallback_classification(self, file_path: Path, file_type: str) -> Dict[str, Any]:
        """Fallback classification when vision analysis unavailable"""
        return {
            'source': f'{file_type.capitalize()} Classifier (Fallback)',
            'category': 'needs_review',
            'confidence': 0.3,
            'reasoning': [f'Vision analysis unavailable, manual review needed for {file_type}'],
            'suggested_filename': file_path.name,
            'metadata': {
                'fallback_mode': True,
                'file_type': file_type
            }
        }

    def _classify_generic_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Fallback for unknown file types.
        """
        print(f"DEBUG: Routing {file_path.name} to GENERIC classifier.")
        return {
            'source': 'Generic Classifier',
            'category': 'unknown',
            'confidence': 0.10,
            'suggested_filename': file_path.name
        }

def save_metadata_sidecar(file_path: Path, classification_result: Dict[str, Any]):
    """
    Save classification metadata to a JSON sidecar file.
    
    Args:
        file_path: Path to the organized file
        classification_result: The classification dictionary
    """
    try:
        # Create sidecar path (e.g., image.jpg -> image.jpg.json)
        sidecar_path = file_path.with_name(f"{file_path.name}.json")
        
        # Prepare metadata for saving
        metadata = {
            'original_filename': file_path.name,
            'classification': classification_result,
            'timestamp': datetime.now().isoformat(),
            'system_version': '3.1'
        }
        
        import json
        from datetime import datetime
        
        with open(sidecar_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        print(f"📝 Saved metadata sidecar: {sidecar_path.name}")
        
    except Exception as e:
        print(f"❌ Failed to save metadata sidecar for {file_path.name}: {e}")