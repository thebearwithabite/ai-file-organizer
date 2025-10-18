#!/usr/bin/env python3
"""
Unified Classification Service

This service acts as the central "brain" for the AI File Organizer, routing
files to the appropriate analysis engine and integrating adaptive learning.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Import the analysis engines that will be integrated
from content_extractor import ContentExtractor
from audio_analyzer import AudioAnalyzer
# from vision_analyzer import VisionAnalyzer # Future implementation

# Import the learning system
# from unified_learning_service import UnifiedLearningService # Will be created

class UnifiedClassificationService:
    """
    A single, intelligent service to handle classification for any file type.
    """

    def __init__(self):
        """Initialize all necessary subsystems."""
        print("Initializing Unified Classification Service...")
        # self.learning_service = UnifiedLearningService()
        self.text_analyzer = ContentExtractor()
        
        # Initialize AudioAnalyzer with OpenAI API key from environment
        openai_api_key = os.getenv('OPENAI_API_KEY')
        base_dir = getattr(self.text_analyzer, 'base_dir', os.getcwd())
        self.audio_analyzer = AudioAnalyzer(
            base_dir=base_dir,
            confidence_threshold=0.7,
            openai_api_key=openai_api_key
        )
        
        # self.vision_analyzer = VisionAnalyzer() # Placeholder
        print("Unified Classification Service Ready.")

    def classify_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Classifies a file by routing it to the correct analysis engine.

        Args:
            file_path: The absolute path to the file to classify.

        Returns:
            A dictionary containing the classification result.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": "File not found"}

        # 1. Determine file type (e.g., by MIME type or extension)
        file_type = self._get_file_type(file_path)

        # 2. Consult the Learning Service for historical context (Future Step)
        # historical_context = self.learning_service.get_context(file_path)

        # 3. Route to the appropriate analysis engine
        if file_type == 'audio':
            result = self._classify_audio_file(file_path)
        elif file_type == 'image':
            result = self._classify_image_file(file_path)
        elif file_type == 'text':
            result = self._classify_text_document(file_path)
        else:
            result = self._classify_generic_file(file_path)

        # 4. Blend analysis with historical context (Future Step)
        # final_result = self.learning_service.blend_with_history(result, historical_context)

        return result

    def _get_file_type(self, file_path: Path) -> str:
        """Determine the general file type (audio, image, text, etc.)."""
        extension = file_path.suffix.lower()
        if extension in ['.wav', '.mp3', '.aiff', '.flac', '.m4a']:
            return 'audio'
        if extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            return 'image'
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

            return {
                'source': 'Text Classifier',
                'category': best_category,
                'confidence': final_confidence,
                'reasoning': reasoning,
                'suggested_filename': file_path.name
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
        Classify audio file using the integrated AudioAnalyzer with AI-powered analysis.
        """
        try:
            # Use AudioAnalyzer for intelligent classification
            classification_result = self.audio_analyzer.classify_audio_file(file_path)
            
            if classification_result:
                # Convert AudioAnalyzer result to unified format
                return {
                    'source': 'Audio Classifier (AI-Powered)',
                    'category': classification_result.get('category', 'audio'),
                    'confidence': classification_result.get('confidence', 0.0),
                    'reasoning': [
                        classification_result.get('reasoning', 'AI-powered audio analysis'),
                        f"Mood: {classification_result.get('mood', 'unknown')}",
                        f"Intensity: {classification_result.get('intensity', 'unknown')}",
                        f"Energy Level: {classification_result.get('energy_level', 0)}/10",
                        f"Tags: {', '.join(classification_result.get('tags', []))}"
                    ],
                    'suggested_filename': classification_result.get('suggested_filename', file_path.name),
                    'metadata': {
                        'mood': classification_result.get('mood'),
                        'intensity': classification_result.get('intensity'),
                        'energy_level': classification_result.get('energy_level'),
                        'tags': classification_result.get('tags', []),
                        'thematic_notes': classification_result.get('thematic_notes'),
                        'target_folder': classification_result.get('target_folder'),
                        'discovered_elements': classification_result.get('discovered_elements', [])
                    }
                }
            else:
                # Fallback if AudioAnalyzer fails
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
        Interim image classification using filename analysis only.
        This will be replaced with computer vision analysis.
        """
        try:
            # Analyze filename for category hints
            filename = file_path.name.lower()
            stem = file_path.stem.lower()

            category = 'image'  # Default category
            confidence = 0.3    # Low confidence as this is interim
            reasoning = ['Computer vision not yet integrated, using filename analysis only']

            # Simple keyword analysis for category detection
            if any(keyword in filename for keyword in ['screenshot', 'screen_shot', 'screencap']):
                category = 'screenshot'
                confidence = 0.4
                reasoning.append("Filename contains screenshot keywords")
            elif any(keyword in filename for keyword in ['headshot', 'portrait', 'profile']):
                category = 'headshot'
                confidence = 0.4
                reasoning.append("Filename contains headshot/portrait keywords")
            elif any(keyword in filename for keyword in ['logo', 'brand', 'branding']):
                category = 'logo'
                confidence = 0.4
                reasoning.append("Filename contains logo/brand keywords")
            elif any(keyword in filename for keyword in ['photo', 'picture', 'pic', 'img']):
                category = 'photo'
                confidence = 0.3
                reasoning.append("Filename contains photo keywords")
            else:
                reasoning.append("No specific category keywords found in filename")

            # Include file format information
            file_format = file_path.suffix.lower().lstrip('.')
            reasoning.append(f"Image format: {file_format}")

            # Note that this is placeholder logic
            reasoning.append("Note: Full computer vision analysis will be implemented in future updates")

            return {
                'source': 'Image Classifier (Interim)',
                'category': category,
                'confidence': confidence,
                'reasoning': reasoning,
                'suggested_filename': file_path.name
            }

        except Exception as e:
            # Fallback for any errors
            return {
                'source': 'Image Classifier (Interim - Error Fallback)',
                'category': 'image',
                'confidence': 0.2,
                'reasoning': [f'Error during image analysis: {str(e)}', 'Using basic fallback classification'],
                'suggested_filename': file_path.name
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