#!/usr/bin/env python3
"""
Interactive File Classification System - ADHD-FRIENDLY VERSION
Fixed critical accessibility bugs:
- Proper Ctrl+C handling
- No meaningless choices
- Obvious files get high confidence
- No infinite loops

Created by: RT Max
"""

import os
import json
import signal
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import re

from classification_engine import FileClassificationEngine, ClassificationResult
from gdrive_integration import get_ai_organizer_root, get_metadata_root

@dataclass
class ClassificationQuestion:
    """A question to resolve classification uncertainty"""
    question_text: str
    options: List[Dict[str, Any]]
    reasoning: str
    uncertainty_type: str

@dataclass 
class UserResponse:
    """User's response to a classification question"""
    selected_option: Dict[str, Any]
    timestamp: datetime
    question_id: str

class ADHDFriendlyClassifier:
    """
    ADHD-Friendly Classification System
    - No meaningless choices
    - Obvious files auto-organize
    - Easy escape with Ctrl+C
    - No infinite loops
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        self.base_classifier = FileClassificationEngine(str(self.base_dir))
        
        # Learning system
        self.learning_file = get_metadata_root() /  "user_preferences.json"
        self.user_preferences = self._load_user_preferences()
        
        # ADHD-friendly settings
        self.target_confidence = 85.0
        self.max_questions = 2  # Reduce from 3 to 2
        self.auto_organize_confidence = 90.0  # Higher threshold for auto-organize
        
        # Set up signal handler for Ctrl+C
        signal.signal(signal.SIGINT, self._signal_handler)
        self.interrupted = False
        
        # Enhanced obvious file patterns
        self._init_obvious_patterns()
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n🚪 Exiting gracefully... (Ctrl+C detected)")
        print("💡 Tip: Use '--auto' mode to skip questions entirely")
        self.interrupted = True
        sys.exit(0)
    
    def _init_obvious_patterns(self):
        """Patterns for files that should have 95%+ confidence"""
        self.obvious_patterns = {
            # Creative/Portfolio Content
            "demo_reel": {
                "patterns": [r"demo.*reel", r"reel.*demo", r"showreel", r"portfolio.*video"],
                "category": "creative",
                "subcategory": "portfolio", 
                "confidence": 98.0,
                "reasoning": "Demo reel - clearly creative portfolio content"
            },
            "podcast": {
                "patterns": [r"podcast", r"episode.*\d+", r"interview.*audio", r".*\.mp3.*podcast"],
                "category": "creative",
                "subcategory": "podcast",
                "confidence": 95.0,
                "reasoning": "Podcast content detected"
            },
            # Business Documents
            "contract": {
                "patterns": [r"contract", r"agreement", r"terms.*conditions", r".*\.pdf.*contract"],
                "category": "business",
                "subcategory": "contracts",
                "confidence": 92.0,
                "reasoning": "Legal contract document"
            },
            "invoice": {
                "patterns": [r"invoice", r"bill", r"payment.*due", r"receipt"],
                "category": "business", 
                "subcategory": "financial",
                "confidence": 95.0,
                "reasoning": "Financial document - invoice/billing"
            },
            # Media Files
            "screenshot": {
                "patterns": [r"screenshot", r"screen.*shot", r"capture.*\d+"],
                "category": "visual",
                "subcategory": "screenshots",
                "confidence": 99.0,
                "reasoning": "Screenshot - visual reference material"
            }
        }
    
    def _check_obvious_classification(self, file_path: Path, content: str = "") -> Optional[ClassificationResult]:
        """Check if this is an obviously classifiable file"""
        filename = file_path.name.lower()
        content_lower = content.lower()
        
        for pattern_name, pattern_info in self.obvious_patterns.items():
            # Check filename patterns
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, filename) or (content and re.search(pattern, content_lower)):
                    # This is an obvious file!
                    return ClassificationResult(
                        category=pattern_info["category"],
                        subcategory=pattern_info["subcategory"],
                        confidence=pattern_info["confidence"],
                        suggested_path=self._get_path_for_category(pattern_info["category"], pattern_info["subcategory"]),
                        reasoning=[pattern_info["reasoning"], f"Matched pattern: {pattern}"],
                        tags=[pattern_info["category"], pattern_info["subcategory"]],
                        people=[],
                        projects=[]
                    )
        
        return None
    
    def _get_path_for_category(self, category: str, subcategory: str) -> str:
        """Get file path for category/subcategory"""
        base_paths = {
            "creative": "01_ACTIVE_PROJECTS/Creative_Projects",
            "business": "01_ACTIVE_PROJECTS/Business_Operations", 
            "visual": "02_MEDIA_ASSETS/Visual_Assets",
            "audio": "02_MEDIA_ASSETS/Audio_Library"
        }
        
        base = base_paths.get(category, "99_TEMP_PROCESSING")
        if subcategory:
            return f"{base}/{subcategory.title()}"
        return base
    
    def classify_with_questions(self, file_path: Path, content: str = "") -> ClassificationResult:
        """
        Classify file with ADHD-friendly questioning
        
        IMPROVEMENTS:
        - Checks obvious patterns first (95%+ confidence)
        - No meaningless choices ("Unknown or .")
        - Proper Ctrl+C handling
        - Max 2 questions per file
        """
        
        if self.interrupted:
            sys.exit(0)
        
        print(f"\n🤔 Classifying: {file_path.name}")
        
        # STEP 1: Check obvious patterns first
        obvious_result = self._check_obvious_classification(file_path, content)
        if obvious_result:
            print(f"✅ Obvious classification: {obvious_result.category} ({obvious_result.confidence:.1f}% confidence)")
            print(f"   📁 Path: {obvious_result.suggested_path}")
            print(f"   💡 {obvious_result.reasoning[0]}")
            return obvious_result
        
        # STEP 2: Use base classifier
        result = self.base_classifier.classify_file(file_path)
        print(f"Initial confidence: {result.confidence:.1f}%")
        
        # STEP 3: Check if we need questions
        if result.confidence >= self.target_confidence:
            print(f"✅ High confidence - auto-organizing")
            return result
        
        if result.confidence < 20.0:
            print(f"⚠️  Very low confidence - manual review recommended")
            print(f"   💡 Consider moving to: 99_TEMP_PROCESSING/Manual_Review/")
            # Return a safe default
            result.category = "unknown"
            result.subcategory = "manual_review"
            result.suggested_path = "99_TEMP_PROCESSING/Manual_Review"
            result.confidence = 20.0
            return result
        
        # STEP 4: Ask targeted questions (max 2)
        questions_asked = 0
        while result.confidence < self.target_confidence and questions_asked < self.max_questions:
            if self.interrupted:
                sys.exit(0)
                
            question = self._create_smart_question(result)
            
            # CRITICAL FIX: Validate question has meaningful options
            if len(question.options) <= 1 or any(not opt.get("label") or opt.get("label") == "Unknown" for opt in question.options):
                print(f"⚠️  Unable to create meaningful question - using current classification")
                break
            
            try:
                response = self._ask_user_question(question)
                result = self._apply_user_response(result, response, question)
                questions_asked += 1
                print(f"Updated confidence: {result.confidence:.1f}%")
                
            except KeyboardInterrupt:
                print(f"\n🚪 Skipping classification - using default")
                break
            except Exception as e:
                print(f"⚠️  Question error: {e}")
                break
        
        return result
    
    def _create_smart_question(self, result: ClassificationResult) -> ClassificationQuestion:
        """Create meaningful questions - NO 'Unknown or .' garbage"""
        
        # Get meaningful alternatives based on file analysis
        alternatives = []
        
        # Add category alternatives based on detected keywords/content
        if result.projects:
            alternatives.extend(["creative", "entertainment", "business"])
        if result.people:
            alternatives.extend(["business", "entertainment"])  
        
        # Content-based alternatives
        content_indicators = {
            "contract": ["business", "legal"], 
            "creative": ["creative", "entertainment"],
            "demo": ["creative", "portfolio"],
            "podcast": ["creative", "audio"],
            "invoice": ["business", "financial"]
        }
        
        for indicator, categories in content_indicators.items():
            if indicator in result.reasoning:
                alternatives.extend(categories)
        
        # Remove duplicates and current category
        alternatives = list(set(alternatives))
        if result.category in alternatives:
            alternatives.remove(result.category)
        
        # CRITICAL FIX: Ensure we have valid alternatives
        if not alternatives:
            # Create meaningful alternatives based on common categories
            alternatives = ["creative", "business", "visual"] if result.category != "creative" else ["business", "visual"]
        
        # Filter out empty/None values
        alternatives = [alt for alt in alternatives if alt and alt.strip()]
        
        # CRITICAL FIX: If still no good alternatives, don't ask
        if len(alternatives) == 0:
            alternatives = ["manual_review"]
        
        options = [
            {"label": result.category.title(), "impact": {"category": result.category, "confidence_boost": 20}},
        ]
        
        for alt in alternatives[:2]:  # Max 3 options total
            options.append({
                "label": alt.title(), 
                "impact": {"category": alt, "confidence_boost": 25}
            })
        
        # Create question with valid alternatives
        alt_text = ", ".join([alt.title() for alt in alternatives[:2]])
        
        return ClassificationQuestion(
            question_text=f"This file could be classified as {result.category.title()} or {alt_text}. Which category fits best?",
            options=options,
            reasoning="Multiple category indicators detected",
            uncertainty_type="category_conflict"
        )
    
    def _ask_user_question(self, question: ClassificationQuestion) -> UserResponse:
        """Present question to user with proper Ctrl+C handling"""
        
        print(f"\n❓ {question.question_text}")
        print(f"   Reason: {question.reasoning}")
        print("\nOptions:")
        
        for i, option in enumerate(question.options, 1):
            print(f"  {i}. {option['label']}")
        
        print(f"\n💡 Tip: Press Ctrl+C to exit anytime")
        
        while True:
            if self.interrupted:
                raise KeyboardInterrupt()
                
            try:
                choice = input(f"\nEnter choice (1-{len(question.options)}) or 'q' to quit: ").strip().lower()
                
                if choice == 'q' or choice == 'quit':
                    raise KeyboardInterrupt()
                
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(question.options):
                    selected = question.options[choice_num - 1]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(question.options)}")
                    
            except ValueError:
                print("Please enter a valid number (or 'q' to quit)")
            except (KeyboardInterrupt, EOFError):
                print(f"\n🚪 Using first option as default...")
                selected = question.options[0]
                break
        
        return UserResponse(
            selected_option=selected,
            timestamp=datetime.now(),
            question_id=f"{question.uncertainty_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    def _apply_user_response(self, result: ClassificationResult, response: UserResponse, question: ClassificationQuestion) -> ClassificationResult:
        """Apply user's response to update classification"""
        
        impact = response.selected_option["impact"]
        
        # Apply changes from user choice
        if "category" in impact:
            result.category = impact["category"]
        if "subcategory" in impact:
            result.subcategory = impact["subcategory"]
        if "primary_person" in impact:
            if impact["primary_person"] not in result.people:
                result.people.insert(0, impact["primary_person"])
        
        # Apply confidence boost
        confidence_boost = impact.get("confidence_boost", 20)
        result.confidence = min(100.0, result.confidence + confidence_boost)
        
        # Update reasoning
        result.reasoning.append(f"User selected: {response.selected_option['label']}")
        
        # Learn from this decision
        self._learn_from_response(result, response)
        
        return result
    
    def _learn_from_response(self, result: ClassificationResult, response: UserResponse):
        """Learn from user's response for future classifications"""
        # Store decision in learning history
        decision = {
            "timestamp": str(response.timestamp),
            "category": result.category,
            "confidence": result.confidence,
            "user_choice": response.selected_option["label"],
            "question_type": response.question_id.split("_")[0]
        }
        
        self.user_preferences["decision_history"].append(decision)
        
        # Update category preferences
        choice_label = response.selected_option["label"].lower()
        if choice_label not in self.user_preferences["category_preferences"]:
            self.user_preferences["category_preferences"][choice_label] = 0
        self.user_preferences["category_preferences"][choice_label] += 1
        
        # Save preferences
        self._save_user_preferences()
    
    def _load_user_preferences(self) -> Dict:
        """Load user's classification preferences from previous decisions"""
        if self.learning_file.exists():
            try:
                with open(self.learning_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "category_preferences": {},
            "person_preferences": {},
            "project_preferences": {},
            "keyword_boosts": {},
            "decision_history": []
        }
    
    def _save_user_preferences(self):
        """Save learned preferences"""
        os.makedirs(self.learning_file.parent, exist_ok=True)
        with open(self.learning_file, 'w') as f:
            json.dump(self.user_preferences, f, indent=2, default=str)

def main():
    """Test the ADHD-friendly classifier"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ADHD-Friendly Interactive Classifier')
    parser.add_argument('file', help='File to classify')
    parser.add_argument('--base-dir', help='Base directory')
    
    args = parser.parse_args()
    
    classifier = ADHDFriendlyClassifier(args.base_dir)
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    try:
        result = classifier.classify_with_questions(file_path)
        print(f"\n✅ FINAL CLASSIFICATION:")
        print(f"   📁 Category: {result.category}")
        print(f"   📂 Subcategory: {result.subcategory}")
        print(f"   📊 Confidence: {result.confidence:.1f}%")
        print(f"   📍 Suggested path: {result.suggested_path}")
        print(f"   💭 Reasoning: {'; '.join(result.reasoning)}")
        
    except KeyboardInterrupt:
        print(f"\n👋 Goodbye!")

if __name__ == "__main__":
    main()