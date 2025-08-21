#!/usr/bin/env python3
"""
Interactive File Classification System
Asks clarifying questions until reaching 85% confidence
Designed for ADHD-friendly decision making
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import re

from classification_engine import FileClassificationEngine, ClassificationResult

@dataclass
class ClassificationQuestion:
    """A question to resolve classification uncertainty"""
    question_text: str
    options: List[Dict[str, Any]]  # [{"label": "Entertainment", "impact": {"category": "entertainment", "confidence_boost": 30}}]
    reasoning: str
    uncertainty_type: str  # "category", "subcategory", "person", "project"

@dataclass 
class UserResponse:
    """User's response to a classification question"""
    selected_option: Dict[str, Any]
    timestamp: datetime
    question_id: str

class InteractiveClassifier:
    """
    Classification system that asks questions until confident
    Maintains learning history for Ryan's preferences
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents"
        self.base_classifier = FileClassificationEngine(str(self.base_dir))
        
        # Learning system
        self.learning_file = self.base_dir / "04_METADATA_SYSTEM" / "user_preferences.json"
        self.user_preferences = self._load_user_preferences()
        
        # Confidence threshold
        self.target_confidence = 85.0
        self.max_questions = 3  # Prevent endless questioning
        
        # Question templates for different uncertainty types
        self._init_question_templates()
    
    def _load_user_preferences(self) -> Dict:
        """Load Ryan's classification preferences from previous decisions"""
        if self.learning_file.exists():
            try:
                with open(self.learning_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "category_preferences": {},  # {"entertainment": {"Client Name": 0.9}}
            "person_preferences": {},    # {"finn": "entertainment"}
            "project_preferences": {},   # {"TV Show": "entertainment"}
            "keyword_boosts": {},        # {"contract": {"entertainment": 20}}
            "decision_history": []       # Track all decisions for learning
        }
    
    def _save_user_preferences(self):
        """Save learned preferences"""
        os.makedirs(self.learning_file.parent, exist_ok=True)
        with open(self.learning_file, 'w') as f:
            json.dump(self.user_preferences, f, indent=2, default=str)
    
    def _init_question_templates(self):
        """Initialize question templates for different uncertainty types"""
        self.question_templates = {
            "category_conflict": {
                "template": "This file mentions {keywords}. It could be filed under {categories}. Which category fits best?",
                "reasoning": "Multiple category indicators found"
            },
            "person_identification": {
                "template": "I found references to {people}. Who is this document primarily about?",
                "reasoning": "Multiple people mentioned, need primary focus"
            },
            "project_classification": {
                "template": "This seems related to {projects}. Which project should I associate this with?",
                "reasoning": "Multiple project contexts detected"
            },
            "business_vs_creative": {
                "template": "This has both business terms ({business_terms}) and creative elements ({creative_terms}). Is this primarily about the business side or the creative work?",
                "reasoning": "Mixed business and creative content"
            },
            "entertainment_specific": {
                "template": "This appears to be about {person} and mentions {content_type}. Should I file this under:\n• Current active projects (Entertainment Industry)\n• General entertainment reference\n• Business operations?",
                "reasoning": "Entertainment content needs specific categorization"
            }
        }
    
    def classify_with_questions(self, file_path: Path, content: str = "") -> ClassificationResult:
        """
        Classify file with interactive questioning until confident
        
        Args:
            file_path: Path to file being classified
            content: Optional pre-extracted content
            
        Returns:
            ClassificationResult with high confidence
        """
        print(f"\n🤔 Classifying: {file_path.name}")
        
        # Get initial classification
        initial_result = self.base_classifier.classify_file(file_path)
        current_result = initial_result
        questions_asked = 0
        
        # Apply learned preferences to boost confidence
        current_result = self._apply_learned_preferences(current_result, file_path, content)
        
        print(f"Initial confidence: {current_result.confidence:.1f}%")
        
        # Ask questions until confident or max questions reached
        while current_result.confidence < self.target_confidence and questions_asked < self.max_questions:
            question = self._generate_question(current_result, file_path, content)
            
            if not question:
                print("No more questions available - using current classification")
                break
            
            response = self._ask_user_question(question)
            current_result = self._apply_user_response(current_result, response, question)
            
            # Learn from this decision
            self._learn_from_response(response, question, file_path, content)
            
            questions_asked += 1
            print(f"Updated confidence: {current_result.confidence:.1f}%")
        
        # Final result
        if current_result.confidence >= self.target_confidence:
            print(f"✅ Classification complete with {current_result.confidence:.1f}% confidence")
        else:
            print(f"⚠️  Proceeding with {current_result.confidence:.1f}% confidence after {questions_asked} questions")
        
        return current_result
    
    def _apply_learned_preferences(self, result: ClassificationResult, file_path: Path, content: str) -> ClassificationResult:
        """Boost confidence based on learned user preferences"""
        confidence_boost = 0
        
        # Check person preferences
        for person in result.people:
            person_lower = person.lower()
            if person_lower in self.user_preferences.get("person_preferences", {}):
                preferred_category = self.user_preferences["person_preferences"][person_lower]
                if preferred_category == result.category:
                    confidence_boost += 15
                    result.reasoning.append(f"Learned: {person} usually goes in {preferred_category}")
        
        # Check keyword preferences
        content_lower = content.lower() if content else file_path.name.lower()
        for keyword, category_boosts in self.user_preferences.get("keyword_boosts", {}).items():
            if keyword in content_lower:
                if result.category in category_boosts:
                    boost = category_boosts[result.category]
                    confidence_boost += boost
                    result.reasoning.append(f"Learned: '{keyword}' usually indicates {result.category}")
        
        # Apply boost
        result.confidence = min(100.0, result.confidence + confidence_boost)
        
        return result
    
    def _generate_question(self, result: ClassificationResult, file_path: Path, content: str) -> Optional[ClassificationQuestion]:
        """Generate the most helpful question for current uncertainty"""
        
        # Analyze what's causing low confidence
        uncertainty_type = self._identify_uncertainty_type(result, content)
        
        if uncertainty_type == "category_conflict":
            return self._create_category_question(result, content)
        elif uncertainty_type == "person_identification":
            return self._create_person_question(result)
        elif uncertainty_type == "business_vs_creative":
            return self._create_business_creative_question(result, content)
        elif uncertainty_type == "entertainment_specific":
            return self._create_entertainment_question(result, content)
        
        return None
    
    def _identify_uncertainty_type(self, result: ClassificationResult, content: str) -> str:
        """Identify what's causing classification uncertainty"""
        
        # Check for multiple people
        if len(result.people) > 1:
            return "person_identification"
        
        # Check for business vs creative conflict
        business_terms = ["payment", "contract", "agreement", "commission", "invoice"]
        creative_terms = ["script", "episode", "creative", "story", "production"]
        
        content_lower = content.lower() if content else ""
        has_business = any(term in content_lower for term in business_terms)
        has_creative = any(term in content_lower for term in creative_terms)
        
        if has_business and has_creative:
            return "business_vs_creative"
        
        # Check for entertainment industry specifics
        if result.category == "entertainment" or any(person in ["finn", "Client"] for person in [p.lower() for p in result.people]):
            return "entertainment_specific"
        
        return "category_conflict"
    
    def _create_category_question(self, result: ClassificationResult, content: str) -> ClassificationQuestion:
        """Create question for category uncertainty"""
        
        # Generate alternative categories based on content
        alternatives = []
        if "contract" in content.lower() or "agreement" in content.lower():
            alternatives.extend(["entertainment", "business"])
        if "creative" in content.lower() or "script" in content.lower():
            alternatives.extend(["creative", "entertainment"])
        if "invoice" in content.lower() or "payment" in content.lower():
            alternatives.extend(["business", "financial"])
        
        # Remove duplicates and current category
        alternatives = list(set(alternatives))
        if result.category in alternatives:
            alternatives.remove(result.category)
        
        options = [
            {"label": result.category.title(), "impact": {"category": result.category, "confidence_boost": 20}},
        ]
        
        for alt in alternatives[:2]:  # Max 3 options total
            options.append({
                "label": alt.title(), 
                "impact": {"category": alt, "confidence_boost": 25}
            })
        
        return ClassificationQuestion(
            question_text=f"This file could be classified as {result.category.title()} or {', '.join(alternatives)}. Which category fits best?",
            options=options,
            reasoning="Multiple category indicators detected",
            uncertainty_type="category_conflict"
        )
    
    def _create_person_question(self, result: ClassificationResult) -> ClassificationQuestion:
        """Create question for person identification"""
        
        options = []
        for person in result.people[:3]:  # Max 3 people
            options.append({
                "label": person,
                "impact": {"primary_person": person, "confidence_boost": 30}
            })
        
        return ClassificationQuestion(
            question_text=f"This document mentions {', '.join(result.people)}. Who is it primarily about?",
            options=options,
            reasoning="Multiple people mentioned",
            uncertainty_type="person_identification"
        )
    
    def _create_business_creative_question(self, result: ClassificationResult, content: str) -> ClassificationQuestion:
        """Create question for business vs creative classification"""
        
        options = [
            {
                "label": "Business Operations (contracts, payments, legal)",
                "impact": {"category": "business", "confidence_boost": 35}
            },
            {
                "label": "Creative Projects (scripts, production, artistic)",
                "impact": {"category": "creative", "confidence_boost": 35}
            },
            {
                "label": "Entertainment Industry (talent management, deals)",
                "impact": {"category": "entertainment", "confidence_boost": 35}
            }
        ]
        
        return ClassificationQuestion(
            question_text="This document has both business and creative elements. What's the primary focus?",
            options=options,
            reasoning="Mixed business and creative content",
            uncertainty_type="business_vs_creative"
        )
    
    def _create_entertainment_question(self, result: ClassificationResult, content: str) -> ClassificationQuestion:
        """Create entertainment industry specific question"""
        
        options = [
            {
                "label": "Active Entertainment Projects (current contracts, ongoing work)",
                "impact": {"subcategory": "current_projects", "confidence_boost": 30}
            },
            {
                "label": "Entertainment Business Operations (payments, legal, admin)",
                "impact": {"category": "business", "subcategory": "entertainment_business", "confidence_boost": 30}
            },
            {
                "label": "Entertainment Reference/Archive (past projects, reference)",
                "impact": {"subcategory": "archive", "confidence_boost": 25}
            }
        ]
        
        return ClassificationQuestion(
            question_text="This entertainment industry document should be filed under:",
            options=options,
            reasoning="Entertainment content needs specific categorization",
            uncertainty_type="entertainment_specific"
        )
    
    def _ask_user_question(self, question: ClassificationQuestion) -> UserResponse:
        """Present question to user and get response"""
        
        print(f"\n❓ {question.question_text}")
        print(f"   Reason: {question.reasoning}")
        print("\nOptions:")
        
        for i, option in enumerate(question.options, 1):
            print(f"  {i}. {option['label']}")
        
        while True:
            try:
                choice = input(f"\nEnter choice (1-{len(question.options)}): ").strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(question.options):
                    selected = question.options[choice_num - 1]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(question.options)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\nUsing default option...")
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
            # Move primary person to front of list
            person = impact["primary_person"]
            if person in result.people:
                result.people.remove(person)
            result.people.insert(0, person)
        
        # Boost confidence
        confidence_boost = impact.get("confidence_boost", 20)
        result.confidence = min(100.0, result.confidence + confidence_boost)
        
        # Add reasoning
        result.reasoning.append(f"User confirmed: {response.selected_option['label']}")
        
        return result
    
    def _learn_from_response(self, response: UserResponse, question: ClassificationQuestion, file_path: Path, content: str):
        """Learn from user's decision for future classifications"""
        
        impact = response.selected_option["impact"]
        
        # Record decision
        decision = {
            "timestamp": response.timestamp.isoformat(),
            "file_name": file_path.name,
            "question_type": question.uncertainty_type,
            "user_choice": response.selected_option["label"],
            "impact": impact
        }
        
        self.user_preferences["decision_history"].append(decision)
        
        # Update specific preferences
        if question.uncertainty_type == "person_identification" and "primary_person" in impact:
            person = impact["primary_person"].lower()
            category = impact.get("category", "entertainment")  # Default for person questions
            self.user_preferences["person_preferences"][person] = category
        
        if question.uncertainty_type == "category_conflict" and "category" in impact:
            # Learn keyword associations
            content_lower = content.lower() if content else file_path.name.lower()
            keywords = ["contract", "agreement", "payment", "script", "creative", "invoice"]
            
            for keyword in keywords:
                if keyword in content_lower:
                    if keyword not in self.user_preferences["keyword_boosts"]:
                        self.user_preferences["keyword_boosts"][keyword] = {}
                    
                    category = impact["category"]
                    if category not in self.user_preferences["keyword_boosts"][keyword]:
                        self.user_preferences["keyword_boosts"][keyword][category] = 0
                    
                    self.user_preferences["keyword_boosts"][keyword][category] += 5
        
        # Save preferences
        self._save_user_preferences()

def test_interactive_classifier():
    """Test the interactive classification system"""
    print("🧪 Testing Interactive Classification System")
    print("=" * 60)
    
    classifier = InteractiveClassifier()
    
    # Test with a sample file
    test_file = Path("/Users/user/Documents/SAMPLE_AGREEMENT_2018.pdf")
    
    if test_file.exists():
        print(f"Testing with: {test_file.name}")
        result = classifier.classify_with_questions(test_file)
        
        print(f"\n✅ Final Classification:")
        print(f"   Category: {result.category}")
        print(f"   Subcategory: {result.subcategory}")
        print(f"   Confidence: {result.confidence:.1f}%")
        print(f"   Path: {result.suggested_path}")
        print(f"   People: {', '.join(result.people)}")
        print(f"   Tags: {', '.join(result.tags)}")
    else:
        print("❌ Test file not found")

if __name__ == "__main__":
    test_interactive_classifier()