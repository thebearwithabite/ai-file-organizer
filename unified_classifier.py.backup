#!/usr/bin/env python3
"""
Unified Classification Service

This service acts as the central "brain" for the AI File Organizer, routing
files to the appropriate analysis engine and integrating adaptive learning.
"""

import os
from pathlib import Path
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

# Import the analysis engines that will be integrated
from content_extractor import ContentExtractor
from audio_analyzer import AudioAnalyzer
from vision_analyzer import VisionAnalyzer
from semantic_text_analyzer import SemanticTextAnalyzer

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
        self._semantic_text_analyzer = None
        self.learning_enabled = True
        self.vision_enabled = True
        self.semantic_text_enabled = True


        # Initialize Taxonomy Service (V3 Source of Truth)
        from taxonomy_service import get_taxonomy_service
        from gdrive_integration import get_metadata_root
        
        config_dir = get_metadata_root() / "config"
        self.taxonomy_service = get_taxonomy_service(config_dir)
        
        # Review Queue Path (Hidden .corpus directory)
        self.review_queue_path = get_metadata_root() / ".AI_LIBRARIAN_CORPUS" / "03_ADAPTIVE_FEEDBACK" / "review_queue.jsonl"
        self.review_queue_path.parent.mkdir(parents=True, exist_ok=True)

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
                
                # Link learning system if enabled
                if self.learning_enabled and self.learning_system:
                    self._vision_analyzer.learning_enabled = True
                    self._vision_analyzer.learning_system = self.learning_system
                
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

    @property
    def semantic_text_analyzer(self):
        """Lazy load semantic text analyzer on first use"""
        if self._semantic_text_analyzer is None and self.semantic_text_enabled:
            try:
                print("📖 Loading semantic text analyzer...")
                self._semantic_text_analyzer = SemanticTextAnalyzer(base_dir=str(self.base_dir))
                self.semantic_text_enabled = self._semantic_text_analyzer.api_initialized
                if self.semantic_text_enabled:
                    print("✅ Semantic text analysis enabled with Gemini API")
                else:
                    print("⚠️  Semantic text analysis disabled (API key missing)")
            except Exception as e:
                self._semantic_text_analyzer = None
                self.semantic_text_enabled = False
                print(f"⚠️  Semantic text analysis disabled: {e}")
        return self._semantic_text_analyzer

    def _normalize_confidence(self, result: Dict[str, Any], file_path: Path, file_type: str) -> Dict[str, Any]:
        """
        Normalize classification results to ALWAYS include a numeric confidence field.
        Also normalizes category strings (Section E: remove + symbols).
        """
        # SECTION E: Normalize category strings - strip + symbols
        category = result.get('category', 'unknown')
        if category and '+' in category:
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
            elif category == 'unknown' or category == 'needs_review':
                confidence = 0.5
            elif file_type == 'audio':
                confidence = 0.7
            elif file_type == 'text':
                confidence = 0.6
            else:
                confidence = 0.4

        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.4

        result['confidence'] = confidence
        if 'confidence_score' in result:
            del result['confidence_score']

        return result

    def _check_obvious_classification(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Check for obvious patterns dynamically using TaxonomyService.
        Returns a classification result if a strong match is found, else None.
        """
        filename = file_path.name.lower()
        extension = file_path.suffix.lower()
        
        # Iterate over Dynamic Taxonomy (V3)
        categories = self.taxonomy_service.get_all_categories()
        
        best_match = None
        
        for cat_id, meta in categories.items():
            # Check Extension Match
            if extension and extension in meta.get("extensions", []):
                return {
                    'source': f'Obvious Pattern ({meta.get("display_name")})',
                    'category': cat_id, # Return ID as category
                    'confidence': meta.get("confidence", 0.90),
                    'reasoning': [f'Extension {extension} matches safe list'],
                    'suggested_filename': file_path.name
                }
                
            # Check Keyword Match
            keywords = meta.get("keywords", [])
            for keyword in keywords:
                if keyword and keyword.lower() in filename:
                    return {
                        'source': f'Obvious Pattern ({meta.get("display_name")})',
                        'category': cat_id,
                        'confidence': meta.get("confidence", 0.95),
                        'reasoning': [f'Filename contains "{keyword}"'],
                        'suggested_filename': file_path.name
                    }
        
        return None




    def _get_history_signal(self, file_path: Path) -> Dict[str, Any]:
        """Check for verified patterns (Placeholder for now)"""
        # In v3.2, this will query LearningSystem for pattern matches
        return {"category": None, "confidence": 0.0, "source": "History"}

    def _detect_hard_conflicts(self, file_type: str, signals: Dict[str, Any]) -> List[str]:
        """Detect blocking conflicts that demand human review"""
        conflicts = []
        
        obvious = signals['obvious']
        modality = signals['modality']
        
        obvious_cat = obvious.get('category')
        modality_cat = modality.get('category')
        
        # 1. Obvious Disagreement (Obvious > 0.9 vs Modality Disagrees)
        if obvious.get('confidence', 0) > 0.9 and modality_cat and modality_cat != 'unknown':
            if obvious_cat != modality_cat:
                conflicts.append(f"Hard Conflict: Obvious says '{obvious_cat}' but Modality says '{modality_cat}'")

        # 2. Type Mismatch
        if file_type == 'audio' and modality_cat and ('image' in modality_cat or 'document' in modality_cat):
             conflicts.append(f"Type Mismatch: Audio file predicted as '{modality_cat}'")
             
        if file_type == 'image' and modality_cat and 'audio' in modality_cat:
             conflicts.append(f"Type Mismatch: Image file predicted as '{modality_cat}'")

        return conflicts

    def _fuse_signals(self, signals: Dict[str, Any], file_type: str) -> Dict[str, Any]:
        """
        Dominance Logic:
        1. Obvious Wins if >= 0.93
        2. Semantic/Modality Wins if >= 0.78 & No Hard Conflicts
        3. History Boosts (Not fully active yet)
        4. Keyword/Weak Modality Demoted
        """
        obvious = signals['obvious']
        modality = signals['modality']
        history = signals['history']
        
        candidates = []
        
        # Add Obvious Candidate
        if obvious.get('confidence', 0) > 0:
            candidates.append({
                "source": "obvious",
                "category": obvious['category'],
                "confidence": obvious['confidence'],
                "weight": 1.0,
                "reasoning": obvious.get('reasoning', [])
            })
            
        # Add Modality Candidate
        if modality.get('confidence', 0) > 0:
            candidates.append({
                "source": "modality",
                "category": modality['category'],
                "confidence": modality['confidence'],
                "weight": 0.8, # Slightly lower weight than obvious
                "reasoning": modality.get('reasoning', []),
                "suggested_filename": modality.get('suggested_filename')
            })

        # Rank Candidates
        candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Detect Conflicts
        conflicts = self._detect_hard_conflicts(file_type, signals)
        
        # Decision Logic
        winner = None
        trace = []
        
        if candidates:
            top = candidates[0]
            
            # Rule 1: Obvious Dominance
            if top['source'] == 'obvious' and top['confidence'] >= 0.93:
                winner = top
                trace.append(f"Obvious({top['confidence']:.2f}) wins (Dominant)")
            
            # Rule 2: Semantic/Modality Win
            elif top['source'] == 'modality' and top['confidence'] >= 0.78:
                if not conflicts:
                    winner = top
                    trace.append(f"Modality({top['confidence']:.2f}) wins (High Conf, No Conflict)")
                else:
                    trace.append(f"Modality({top['confidence']:.2f}) blocked by conflicts: {conflicts}")
            
            # Fallback
            else:
                trace.append(f"Top candidate {top['source']}({top['confidence']:.2f}) below auto-thresholds")
                if not conflicts:
                    # Return it but let the queue logic handle the low confidence
                    winner = top
        
        if not winner:
            winner = {
                "category": "needs_review",
                "confidence": 0.0,
                "source": "Fusion (Fallback)",
                "reasoning": ["No clear winner or blocked by conflicts"]
            }

        return {
            "signals": signals,
            "final": {
                "category": winner.get('category'),
                "confidence": winner.get('confidence', 0.0),
                "decision_trace": " > ".join(trace),
                "winner": winner,
                "candidates": candidates,
                "conflicts": conflicts
            }
        }

    def _add_to_review_queue(self, file_path: Path, result: Dict[str, Any], file_type: str):
        """Add ambiguous/conflicting file to review queue"""
        try:
            stat = file_path.stat()
            file_hash = hashlib.md5(f"{file_path}{stat.st_size}{stat.st_mtime}".encode()).hexdigest()
            
            entry = {
                "timestamp": time.time(),
                "queue_id": file_hash,
                "file_path": str(file_path),
                "file_type": file_type,
                "final_decision": {
                    "category": result['final']['category'],
                    "confidence": result['final']['confidence'],
                    "trace": result['final']['decision_trace']
                },
                "conflicts": result['final']['conflicts'],
                "candidates": [
                    {"src": c['source'], "cat": c['category'], "conf": c['confidence']} 
                    for c in result['final']['candidates']
                ],
                "status": "pending"
            }
            
            with open(self.review_queue_path, 'a') as f:
                f.write(json.dumps(entry) + "\n")
                
        except Exception as e:
            print(f"❌ Failed to write to review queue: {e}")

    def classify_file(self, file_path: Union[str, Path], project_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Classifies a file by routing it to the correct analysis engine.

        GUARANTEED: Returns a dict with a numeric 'confidence' field (0.0 to 1.0).
        This method is the single source of truth for all file classifications.

        Args:
            file_path: The absolute path to the file to classify.
            project_context: Optional string describing the active project (Phase V4).

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

        # 0. Check for obvious patterns first (Fast Path Signal)
        obvious_result = self._check_obvious_classification(file_path)
        
        # 1. Determine file type
        file_type = self._get_file_type(file_path)
        
        # 2. Run modality-specific analysis to get the PRIMARY signal
        modality_signal = self._get_modality_signal(file_path, file_type, project_context)

        # 3. Get History Signal (Verified Patterns)
        history_signal = self._get_history_signal(file_path)

        # 4. Construct Evidence Bundle
        signals = {
            "obvious": obvious_result if obvious_result else {"category": None, "confidence": 0.0},
            "modality": modality_signal,
            "history": history_signal
        }
        
        # 5. FUSE SIGNALS
        fusion_result = self._fuse_signals(signals, file_type)
        
        # 6. Safety & Queueing Checks
        final_confidence = fusion_result['final']['confidence']
        final_category = fusion_result['final']['category']
        conflicts = fusion_result['final']['conflicts']
        
        # Thresholds
        AUTO_ROUTE_THRESHOLD = 0.65 # Lowered from 0.80 to 0.65
        QUEUE_THRESHOLD = 0.65      # Lowered from 0.70 to 0.65
        
        should_queue = False
        
        # Queue Condition 1: Low Confidence
        if final_confidence < QUEUE_THRESHOLD:
            should_queue = True
            
        # Queue Condition 2: "Unknown" or "Needs Review"
        if final_category in ['unknown', 'needs_review']:
            should_queue = True
            
        # Queue Condition 3: Hard Conflicts present
        if conflicts:
            should_queue = True
            
        # Queue Condition 4: "Uncertain Zone" (High enough to predict, low enough to verify)
        # If between 0.72 and 0.80, we might want to queue it BUT still return the category
        if QUEUE_THRESHOLD <= final_confidence < AUTO_ROUTE_THRESHOLD:
             if conflicts:
                should_queue = True

        # Queue Logic
        if should_queue:
            self._add_to_review_queue(file_path, fusion_result, file_type)
            
            # If strictly below queue threshold, force 'needs_review' in final output to prevent auto-move
            if final_confidence < QUEUE_THRESHOLD:
               fusion_result['final']['category'] = 'needs_review'

        # 7. Construct Final Backward-Compatible Result
        winner = fusion_result['final']['winner']
        
        final_result = {
            "category": fusion_result['final']['category'],
            "confidence": fusion_result['final']['confidence'],
            "reasoning": [fusion_result['final']['decision_trace']] + winner.get('reasoning', []),
            "source": winner.get('source', 'Fusion'),
            "suggested_filename": winner.get('suggested_filename', file_path.name),
            "signals": signals,
            "fusion": fusion_result['final']
        }
        
        return final_result

    def _get_file_type(self, file_path: Path) -> str:
        """Determine the general file type (audio, image, video, text, etc.)."""
        extension = file_path.suffix.lower()
        if extension in ['.wav', '.mp3', '.aiff', '.flac', '.m4a']:
            return 'audio'
        if extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.heic', '.heif']:
            return 'image'
        if extension in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']:
            return 'video'
        if extension in ['.pdf', '.docx', '.txt', '.md', '.html', '.htm', '.json', '.xml', '.py', '.js', '.ts', '.tsx', '.css']:
            return 'text'
        return 'generic'

    def _get_modality_signal(self, file_path: Path, file_type: str, project_context: Optional[str] = None) -> Dict[str, Any]:
        """Route to specific handlers based on modality"""
        if file_type == 'text':
            return self._classify_text_document(file_path)
        if file_type == 'image':
            return self._classify_image_file(file_path, project_context)
        if file_type == 'video':
            return self._classify_video_file(file_path, project_context)
        if file_type == 'audio':
            return self._classify_audio_file(file_path, project_context)
        return self._classify_generic_file(file_path)

    def _classify_text_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Classify a text document using Hybrid Intelligence:
        1. FAST: Regex-based keyword matching for obvious cases.
        2. SMART: Semantic AI analysis for ambiguous or complex content.
        
        Algorithm:
        - Extract text content.
        - Run regex keyword check with word boundaries (fixes 'agenda' != 'nda').
        - If Keyword Confidence > 0.85 AND contains 'strong' keywords -> Return fast result.
        - Otherwise -> Send to SemanticTextAnalyzer (Gemini) for deep reading.
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

            full_text = content_data['text']  # Keep original case for AI, lower for keywords
            full_text_lower = full_text.lower()
            filename = file_path.name.lower()
            print(f"DEBUG: Content length: {len(full_text)} chars")

            # --- PHASE 1: Fast Regex Keyword Matching ---
            import json
            import re
            
            best_category = 'unknown'
            best_confidence = 0.0
            reasoning = []
            
            # Load classification rules
            rules_file = Path(__file__).parent / "classification_rules.json"
            if rules_file.exists():
                with open(rules_file, 'r') as f:
                    rules_data = json.load(f)
                rules = rules_data.get('document_types', {})
            else:
                rules = {} # Fallback

            matched_keywords = []

            for category, rule_details in rules.items():
                keyword_matches = 0
                current_matched = []

                for keyword in rule_details.get('keywords', []):
                    # Use Regex Word Boundaries (\b) to prevent partial matches
                    # e.g. Match 'nda' but NOT 'agenda'
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    
                    if re.search(pattern, full_text_lower):
                        keyword_matches += 1
                        current_matched.append(keyword)
                    elif keyword.lower() in filename: # Filenames might not have spaces
                        keyword_matches += 0.5
                        current_matched.append(f"{keyword} (in filename)")
                
                if keyword_matches > 0:
                    # Score Calculation
                    base_confidence = 0.55
                    keyword_bonus = (keyword_matches - 1) * 0.25
                    strong_keywords = ['contract', 'agreement', 'payment', 'script', 'code', 'nda']
                    strong_matches = sum(1 for kw in current_matched if kw.split(' ')[0] in strong_keywords)
                    strong_bonus = 0.15 if strong_matches >= 2 else 0
                    
                    category_confidence = base_confidence + keyword_bonus + strong_bonus
                    
                    if category_confidence > best_confidence:
                        best_confidence = category_confidence
                        best_category = category
                        matched_keywords = current_matched
                        reasoning = [f"Found keywords: {', '.join(matched_keywords)}"]

            # --- PHASE 2: AI Decision Gate ---
            # If confidence is high and we are sure, skip AI to save time/cost.
            # But if it's 'NDA' (often ambiguous) or confidence is low (< 0.85), use AI.
            
            use_ai = False
            
            # Condition 1: Low confidence
            if best_confidence < 0.85:
                use_ai = True
                print(f"DEBUG: Confidence {best_confidence:.2f} < 0.85. Engaging AI.")
                
            # Condition 2: Ambiguous Categories (Short acronyms like NDA can be tricky despite regex)
            if 'nda' in matched_keywords or len(full_text) < 100:
                use_ai = True
                print("DEBUG: Ambiguous content detected. Engaging AI for verification.")

            if use_ai:
                # Fetch valid categories from TaxonomyService to guide the AI
                allowed_categories = []
                if self.taxonomy_service:
                    all_cats = self.taxonomy_service.get_all_categories()
                    allowed_categories = [
                        {"id": cid, "name": meta.get("display_name", cid)} 
                        for cid, meta in all_cats.items()
                    ]
                
                # --- NEW: Offload to Remote Powerhouse (Ollama) if enabled ---
                ai_result = None
                if self.vision_analyzer and self.vision_analyzer.remote_enabled and self.vision_analyzer.remote_ip:
                    print(f"🛰️ Dispatching text analysis to remote 5090 ({self.vision_analyzer.remote_ip})...")
                    ai_result = self._classify_text_remote(full_text, file_path.name, allowed_categories)
                    if ai_result and ai_result.get('success'):
                        ai_result['source'] = f"Remote Powerhouse (Ollama)"
                    else:
                        print("⚠️  Remote text analysis failed, falling back to Gemini.")
                
                # Fallback to SemanticTextAnalyzer (Gemini)
                if not ai_result or not ai_result.get('success'):
                    if self.semantic_text_enabled and self.semantic_text_analyzer:
                        print("✨ Engaging Semantic Text Analyzer (Gemini)...")
                        ai_result = self.semantic_text_analyzer.analyze_text(
                            text_content=full_text,
                            filename=file_path.name,
                            allowed_categories=allowed_categories
                        )
                
                if ai_result and ai_result.get("success"):
                    ai_category = ai_result.get("category")
                    ai_confidence = ai_result.get("confidence", 0.0)
                    
                    print(f"🤖 AI Analysis: Category='{ai_category}', Confidence={ai_confidence}")
                    
                    # Trust AI if it's confident
                    if ai_confidence > best_confidence:
                        best_category = ai_category
                        best_confidence = ai_confidence
                        reasoning = [
                            f"AI Interpretation: {ai_result.get('document_type', 'Document')}",
                            f"Summary: {ai_result.get('summary', '')}",
                            f"Reasoning: {ai_result.get('reasoning', '')}"
                        ]
                        
                        # Use AI suggested filename if available
                        if ai_result.get("suggested_filename"):
                            return {
                                'source': 'Semantic Text Analyzer (Gemini)',
                                'category': best_category,
                                'confidence': best_confidence,
                                'reasoning': reasoning,
                                'suggested_filename': ai_result.get("suggested_filename"),
                                'keywords': ai_result.get("keywords", [])  # Return AI keywords
                            }

            # Final Cleanup
            final_confidence = min(best_confidence, 1.0)
            
            # Generate intelligent filename (Legacy fallback)
            suggested_filename = file_path.name
            if final_confidence > 0.6 and len(matched_keywords) > 0:
                clean_keywords = [k.split(' (')[0].replace(' ', '_') for k in matched_keywords]
                unique_keywords = list(dict.fromkeys(clean_keywords))
                prefix = "_".join(unique_keywords[:2])
                extension = file_path.suffix
                if any(x in filename for x in ["untitled", "doc", "scan"]):
                    suggested_filename = f"{best_category}_{prefix}{extension}"
                else:
                    suggested_filename = f"{file_path.stem}_{prefix}{extension}"
            
            # Record observation for learning system
            if self.learning_enabled and self.learning_system:
                self.learning_system.record_classification(
                    file_path=str(file_path),
                    predicted_category=best_category,
                    confidence=final_confidence,
                    features={
                        'keywords': matched_keywords,
                        'reasoning': reasoning
                    },
                    media_type='document'
                )

            return {
                'source': 'Text Classifier (Hybrid)',
                'category': best_category,
                'confidence': final_confidence,
                'reasoning': reasoning,
                'suggested_filename': suggested_filename,
                'keywords': matched_keywords  # Return discovered keywords for learning system
            }

        except Exception as e:
            print(f"❌ Error in text classification: {e}")
            import traceback
            traceback.print_exc()
            return {
                'source': 'Text Classifier',
                'category': 'unknown',
                'confidence': 0.10,
                'reasoning': [f'Error analyzing document: {str(e)}'],
                'suggested_filename': file_path.name
            }

    def _classify_audio_file(self, file_path: Path, project_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify audio file using the integrated AudioAnalyzer with AI-powered analysis
        and spectral analysis using librosa.
        """
        try:
            # Perform spectral analysis first (works without OpenAI API)
            spectral_result = self.audio_analyzer.analyze_audio_spectral(file_path, max_duration=30)

            # Use AudioAnalyzer for intelligent classification (requires OpenAI API)
            classification_result = self.audio_analyzer.classify_audio_file(file_path, project_context=project_context)

            if classification_result:
                # Merge spectral analysis with AI classification
                metadata = {
                    'mood': classification_result.get('mood'),
                    'intensity': classification_result.get('intensity'),
                    'energy_level': classification_result.get('energy_level'),
                    'tags': classification_result.get('tags', []),
                    'thematic_notes': classification_result.get('thematic_notes'),
                    'target_folder': classification_result.get('target_folder'),
                    'discovered_elements': classification_result.get('discovered_elements', []),
                    'transcript': classification_result.get('transcript')
                }

                # Add spectral analysis data if available
                if spectral_result.get('success'):
                    metadata['bpm'] = spectral_result.get('bpm', 0)
                    metadata['spectral_mood'] = spectral_result.get('mood', 'unknown')
                    metadata['spectral_content_type'] = spectral_result.get('content_type', 'unknown')
                    metadata['spectral_features'] = spectral_result.get('spectral_features', {})
                    metadata['energy_level_spectral'] = spectral_result.get('energy_level_scale', 0)

                # Convert AudioAnalyzer result to unified format
                # Record observation for learning system
                if self.learning_enabled and self.learning_system:
                    self.learning_system.record_classification(
                        file_path=str(file_path),
                        predicted_category=classification_result.get('category', 'audio'),
                        confidence=classification_result.get('confidence', 0.0),
                        features=metadata,
                        media_type='audio'
                    )

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

    def _classify_image_file(self, file_path: Path, project_context: Optional[str] = None) -> Dict[str, Any]:
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
            vision_result = self.vision_analyzer.analyze_image(str(file_path), project_context=project_context)

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
                    'identified_entities': vision_result.get('identified_entities', []), # Phase V4
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
                # Filter out stop words if keyword list exists
                raw_keywords = vision_result.get('keywords', [])
                stop_words = getattr(self.vision_analyzer, 'llm_stop_words', set())
                clean_keywords = [
                    k.replace(' ', '_') 
                    for k in raw_keywords 
                    if k.lower() not in stop_words and len(k) > 2
                ][:3]
                
                if clean_keywords:
                    extension = file_path.suffix
                    suggested_filename = f"{classification['category']}_{'_'.join(clean_keywords)}{extension}"

            classification['suggested_filename'] = suggested_filename

            # Record in learning system if available
            if self.learning_enabled and self.learning_system:
                self.learning_system.record_classification(
                    file_path=str(file_path),
                    predicted_category=classification['category'],
                    confidence=classification['confidence'],
                    features={
                        'keywords': classification['metadata']['keywords'],
                        'identified_entities': vision_result.get('identified_entities', []), # Phase V4
                        'visual_objects': vision_result.get('objects_detected', []),
                        'scene_type': vision_result.get('scene_type', '')
                    },
                    media_type='image'
                )

            return classification

        except Exception as e:
            print(f"❌ Error classifying image {file_path.name}: {e}")
            return self._fallback_classification(file_path, 'image')

    def _classify_video_file(self, file_path: Path, project_context: Optional[str] = None) -> Dict[str, Any]:
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
            vision_result = self.vision_analyzer.analyze_video(str(file_path), project_context=project_context)

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
                    'identified_entities': vision_result.get('identified_entities', []), # Phase V4
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
                        'identified_entities': vision_result.get('identified_entities', []), # Phase V4
                        'video_type': vision_result.get('metadata', {}).get('video_type', 'unknown')
                    },
                    media_type='video'
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

    def save_metadata_sidecar(self, file_path: Path, classification_result: Dict[str, Any]):
        """
        Save classification metadata to a JSON sidecar file.
        
        Args:
            file_path: Path to the organized file
            classification_result: The classification dictionary
        """
        try:
            # Relocate sidecar to hidden .metadata folder to prevent clutter
            # e.g., folder/image.jpg -> folder/.metadata/image.jpg.json
            metadata_dir = file_path.parent / ".metadata"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            sidecar_path = metadata_dir / f"{file_path.name}.json"
            
            # Prepare metadata for saving
            metadata = {
                'original_filename': file_path.name,
                'classification': classification_result,
                'timestamp': time.time(),
                'system_version': '3.1'
            }
            
            with open(sidecar_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            print(f"📝 Saved metadata sidecar to hidden folder: .metadata/{sidecar_path.name}")
            
        except Exception as e:
            print(f"❌ Failed to save metadata sidecar for {file_path.name}: {e}")

    def _classify_text_remote(self, text: str, filename: str, allowed_categories: List[Dict[str, str]]) -> Dict[str, Any]:
        """Dispatch text classification to remote Ollama server (5090)"""
        import requests
        try:
            prompt = f"""
            Analyze this document text and strictly output JSON.
            
            Filename: "{filename}"
            
            ALLOWED CATEGORIES (Pick the best fit from this list):
            {chr(10).join([f"- {c['id']}: {c['name']}" for c in allowed_categories])}
            
            Task:
            1. Determine the exact document type (e.g., "Legal Contract", "Meeting Minutes", "Invoice", "Screenplay", "Technical Spec", "Financial Report").
            2. Assign a confidence score (0.0 to 1.0).
            3. Extract 3-5 key topics/entities.
            4. Suggest the BEST category ID from the list above. If NO category fits, suggest a new slug.
            5. Suggest a descriptive filename (IMPORTANT: preserve the extension).
            
            Text Content (First 2000 chars):
            \"\"\"
            {text[:2000]}
            \"\"\"
            
            Output JSON Format:
            {{
                "category": "category_id",
                "document_type": "Human Readable Type",
                "confidence": 0.85,
                "summary": "1-sentence summary",
                "keywords": ["tag1", "tag2"],
                "reasoning": "Why you chose this category",
                "suggested_filename": "New_Filename.ext"
            }}
            """

            url = f"http://{self.vision_analyzer.remote_ip}:{self.vision_analyzer.remote_ollama_port}/api/generate"
            payload = {
                "model": "qwen2.5:7b", # Using standard Qwen 2.5 for text
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }

            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get("response", "{}")
            
            import json
            parsed = json.loads(response_text)
            parsed["success"] = True
            return parsed

        except Exception as e:
            print(f"Error in remote text classification: {e}")
            return {"success": False, "error": str(e)}
