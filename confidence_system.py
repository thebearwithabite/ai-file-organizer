#!/usr/bin/env python3
"""
4-Level Confidence System for ADHD-Friendly File Organization
Part of AI File Organizer v3.1 - Adaptive Emergency Prevention System

Confidence Levels:
- SMART (70%): Smart suggestions with single confirmation
- MINIMAL (40%): Minimal questions, quick decisions  
- ALWAYS (100%): Always ask before moving files
- NEVER (0%): Never move files automatically

Designed to reduce cognitive load while maintaining user control

Created by: RT Max / Claude Code
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from enum import Enum

# Import existing system components
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from universal_adaptive_learning import UniversalAdaptiveLearning
from gdrive_integration import get_ai_organizer_root

class ConfidenceLevel(Enum):
    """Confidence levels for ADHD-friendly interaction"""
    NEVER = 0      # Never move automatically, always ask
    MINIMAL = 40   # Minimal questions, quick decisions
    SMART = 70     # Smart suggestions with confirmation  
    ALWAYS = 100   # Move automatically when very confident

@dataclass
class ConfidenceDecision:
    """A decision made by the confidence system"""
    file_path: str
    confidence_level: ConfidenceLevel
    predicted_action: Dict[str, Any]
    system_confidence: float
    requires_user_input: bool
    question_text: Optional[str] = None
    suggested_actions: List[Dict[str, Any]] = None
    reasoning: str = ""
    emergency_prevention: bool = False

class ADHDFriendlyConfidenceSystem:
    """
    4-level confidence system designed specifically for ADHD users
    
    Balances automation with user control to reduce cognitive load
    while preventing file organization emergencies
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        
        # Initialize adaptive learning system
        self.learning_system = UniversalAdaptiveLearning(str(self.base_dir))
        
        # Configuration file for user preferences
        self.config_file = self.base_dir / "04_METADATA_SYSTEM" / "confidence_settings.json"
        self.user_config = self._load_user_config()
        
        # Default confidence thresholds
        self.thresholds = {
            ConfidenceLevel.NEVER: {
                "auto_move": False,
                "max_questions": 1,
                "question_style": "binary",
                "preview_required": True
            },
            ConfidenceLevel.MINIMAL: {
                "auto_move_threshold": 0.85,
                "max_questions": 1, 
                "question_style": "quick",
                "preview_required": False,
                "emergency_override": True
            },
            ConfidenceLevel.SMART: {
                "auto_move_threshold": 0.80,
                "max_questions": 2,
                "question_style": "informed",
                "preview_required": False,
                "emergency_override": True
            },
            ConfidenceLevel.ALWAYS: {
                "auto_move_threshold": 0.75,
                "max_questions": 0,
                "question_style": None,
                "preview_required": False,
                "emergency_override": True
            }
        }
        
        # Emergency prevention triggers
        self.emergency_triggers = {
            "disk_space_critical": 0.95,    # 95% disk usage
            "duplicate_crisis": 50,         # 50+ duplicates detected
            "downloads_overflow": 100,      # 100+ files in downloads
            "staging_overflow": 200,        # 200+ files in staging
            "lost_file_pattern": 5          # 5+ "where is my file" searches
        }
        
        # Set up logging
        self.logger = logging.getLogger(__name__)

    def _load_user_config(self) -> Dict[str, Any]:
        """Load user's confidence system preferences"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load confidence config: {e}")
        
        # Default configuration
        return {
            "default_level": "SMART",
            "emergency_override_enabled": True,
            "learning_enabled": True,
            "context_specific_levels": {
                "downloads": "MINIMAL",
                "desktop": "SMART", 
                "staging": "ALWAYS",
                "documents": "SMART"
            },
            "file_type_levels": {
                ".pdf": "SMART",
                ".docx": "SMART", 
                ".jpg": "MINIMAL",
                ".png": "MINIMAL",
                ".mp3": "ALWAYS",
                ".zip": "MINIMAL"
            },
            "time_based_adjustments": {
                "weekend": "MINIMAL",      # Less interruption on weekends
                "evening": "MINIMAL",      # Less interruption in evening
                "work_hours": "SMART"      # More thoughtful during work
            }
        }

    def save_user_config(self):
        """Save user configuration"""
        os.makedirs(self.config_file.parent, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.user_config, f, indent=2)

    def determine_confidence_level(self, file_path: str, context: Dict[str, Any] = None) -> ConfidenceLevel:
        """
        Determine appropriate confidence level for a file based on multiple factors
        
        Args:
            file_path: Path to the file
            context: Additional context about the file
            
        Returns:
            Appropriate confidence level
        """
        
        # Start with default level
        default_level_name = self.user_config.get("default_level", "SMART")
        current_level = ConfidenceLevel[default_level_name]
        
        # Factor 1: Location-based adjustment
        location_level = self._get_location_based_level(file_path)
        if location_level:
            current_level = location_level
        
        # Factor 2: File type adjustment
        file_type_level = self._get_file_type_level(file_path)
        if file_type_level:
            current_level = file_type_level
        
        # Factor 3: Time-based adjustment
        time_level = self._get_time_based_level()
        if time_level:
            current_level = self._combine_levels(current_level, time_level)
        
        # Factor 4: Emergency override
        if self._check_emergency_conditions(file_path, context):
            self.logger.info(f"Emergency conditions detected - overriding to ALWAYS level")
            return ConfidenceLevel.ALWAYS
        
        # Factor 5: Learning system adjustment
        if self.user_config.get("learning_enabled", True):
            learned_level = self._get_learned_level(file_path, context)
            if learned_level:
                current_level = self._combine_levels(current_level, learned_level)
        
        self.logger.info(f"Determined confidence level for {Path(file_path).name}: {current_level.name}")
        return current_level

    def _get_location_based_level(self, file_path: str) -> Optional[ConfidenceLevel]:
        """Get confidence level based on file location"""
        path_str = str(file_path).lower()
        
        for location, level_name in self.user_config.get("context_specific_levels", {}).items():
            if location.lower() in path_str:
                return ConfidenceLevel[level_name]
        
        return None

    def _get_file_type_level(self, file_path: str) -> Optional[ConfidenceLevel]:
        """Get confidence level based on file type"""
        file_ext = Path(file_path).suffix.lower()
        
        level_name = self.user_config.get("file_type_levels", {}).get(file_ext)
        if level_name:
            return ConfidenceLevel[level_name]
        
        return None

    def _get_time_based_level(self) -> Optional[ConfidenceLevel]:
        """Get confidence level based on current time"""
        now = datetime.now()
        adjustments = self.user_config.get("time_based_adjustments", {})
        
        # Weekend adjustment
        if now.weekday() >= 5 and "weekend" in adjustments:
            return ConfidenceLevel[adjustments["weekend"]]
        
        # Time of day adjustment
        if 18 <= now.hour <= 23 and "evening" in adjustments:
            return ConfidenceLevel[adjustments["evening"]]
        elif 9 <= now.hour <= 17 and "work_hours" in adjustments:
            return ConfidenceLevel[adjustments["work_hours"]]
        
        return None

    def _get_learned_level(self, file_path: str, context: Dict[str, Any] = None) -> Optional[ConfidenceLevel]:
        """Get confidence level based on learned patterns"""
        
        # Get prediction from learning system
        prediction = self.learning_system.predict_user_action(file_path, context)
        
        if not prediction or prediction["confidence"] < 0.3:
            return None
        
        # Convert learning system confidence to confidence level
        confidence = prediction["confidence"]
        
        if confidence >= 0.9:
            return ConfidenceLevel.ALWAYS
        elif confidence >= 0.7:
            return ConfidenceLevel.SMART
        elif confidence >= 0.5:
            return ConfidenceLevel.MINIMAL
        else:
            return ConfidenceLevel.NEVER

    def _combine_levels(self, level1: ConfidenceLevel, level2: ConfidenceLevel) -> ConfidenceLevel:
        """Combine two confidence levels (take the more conservative one)"""
        return min(level1, level2, key=lambda x: x.value)

    def _check_emergency_conditions(self, file_path: str, context: Dict[str, Any] = None) -> bool:
        """Check if emergency conditions require immediate action"""
        
        # Check disk space
        if self._check_disk_space_emergency(file_path):
            return True
        
        # Check for duplicate crisis
        if self._check_duplicate_emergency(context):
            return True
        
        # Check for overflow conditions
        if self._check_overflow_emergency(file_path):
            return True
        
        return False

    def _check_disk_space_emergency(self, file_path: str) -> bool:
        """Check if disk space is critically low"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(Path(file_path).parent)
            usage_ratio = used / total
            
            return usage_ratio >= self.emergency_triggers["disk_space_critical"]
        except:
            return False

    def _check_duplicate_emergency(self, context: Dict[str, Any] = None) -> bool:
        """Check if there's a duplicate file crisis"""
        if not context or "duplicate_count" not in context:
            return False
        
        return context["duplicate_count"] >= self.emergency_triggers["duplicate_crisis"]

    def _check_overflow_emergency(self, file_path: str) -> bool:
        """Check for folder overflow conditions"""
        parent_dir = Path(file_path).parent
        
        try:
            file_count = len(list(parent_dir.iterdir()))
            
            # Check for downloads overflow
            if "downloads" in str(parent_dir).lower():
                return file_count >= self.emergency_triggers["downloads_overflow"]
            
            # Check for staging overflow
            if "staging" in str(parent_dir).lower():
                return file_count >= self.emergency_triggers["staging_overflow"]
            
        except:
            pass
        
        return False

    def make_confidence_decision(self, 
                               file_path: str, 
                               predicted_action: Dict[str, Any],
                               system_confidence: float,
                               context: Dict[str, Any] = None) -> ConfidenceDecision:
        """
        Make a decision about how to handle a file based on confidence system
        
        Args:
            file_path: Path to the file
            predicted_action: What the system thinks should be done
            system_confidence: How confident the system is (0.0-1.0)
            context: Additional context
            
        Returns:
            ConfidenceDecision with instructions for handling
        """
        
        # Determine confidence level
        confidence_level = self.determine_confidence_level(file_path, context)
        threshold_config = self.thresholds[confidence_level]
        
        # Check for emergency override
        emergency_prevention = self._check_emergency_conditions(file_path, context)
        
        if emergency_prevention and self.user_config.get("emergency_override_enabled", True):
            self.logger.warning(f"Emergency override activated for {Path(file_path).name}")
            confidence_level = ConfidenceLevel.ALWAYS
            threshold_config = self.thresholds[confidence_level]
        
        # Make decision based on confidence level
        decision = self._make_level_specific_decision(
            file_path, predicted_action, system_confidence, 
            confidence_level, threshold_config, emergency_prevention
        )
        
        # Learn from this decision
        if self.user_config.get("learning_enabled", True):
            self._record_confidence_decision(decision, context)
        
        return decision

    def _make_level_specific_decision(self, 
                                    file_path: str,
                                    predicted_action: Dict[str, Any], 
                                    system_confidence: float,
                                    confidence_level: ConfidenceLevel,
                                    threshold_config: Dict[str, Any],
                                    emergency_prevention: bool) -> ConfidenceDecision:
        """Make decision specific to confidence level"""
        
        filename = Path(file_path).name
        auto_move_threshold = threshold_config.get("auto_move_threshold", 1.0)
        
        if confidence_level == ConfidenceLevel.NEVER:
            return ConfidenceDecision(
                file_path=file_path,
                confidence_level=confidence_level,
                predicted_action=predicted_action,
                system_confidence=system_confidence,
                requires_user_input=True,
                question_text=f"What should I do with '{filename}'?",
                suggested_actions=[
                    {"action": "organize", "label": f"Move to {predicted_action.get('target_location', 'suggested location')}"},
                    {"action": "skip", "label": "Leave it where it is"},
                    {"action": "delete", "label": "Delete this file"}
                ],
                reasoning="NEVER mode - always ask user",
                emergency_prevention=emergency_prevention
            )
        
        elif confidence_level == ConfidenceLevel.MINIMAL:
            if system_confidence >= auto_move_threshold:
                return ConfidenceDecision(
                    file_path=file_path,
                    confidence_level=confidence_level,
                    predicted_action=predicted_action,
                    system_confidence=system_confidence,
                    requires_user_input=False,
                    reasoning=f"MINIMAL mode - high confidence ({system_confidence:.1%}), moving automatically",
                    emergency_prevention=emergency_prevention
                )
            else:
                return ConfidenceDecision(
                    file_path=file_path,
                    confidence_level=confidence_level,
                    predicted_action=predicted_action,
                    system_confidence=system_confidence,
                    requires_user_input=True,
                    question_text=f"Quick decision: Move '{filename}' to {predicted_action.get('target_category', 'suggested category')}?",
                    suggested_actions=[
                        {"action": "yes", "label": "Yes, move it"},
                        {"action": "no", "label": "No, leave it"}
                    ],
                    reasoning="MINIMAL mode - needs quick confirmation",
                    emergency_prevention=emergency_prevention
                )
        
        elif confidence_level == ConfidenceLevel.SMART:
            if system_confidence >= auto_move_threshold:
                return ConfidenceDecision(
                    file_path=file_path,
                    confidence_level=confidence_level,
                    predicted_action=predicted_action,
                    system_confidence=system_confidence,
                    requires_user_input=False,
                    reasoning=f"SMART mode - confident prediction ({system_confidence:.1%}), moving automatically",
                    emergency_prevention=emergency_prevention
                )
            else:
                # Generate smart question based on uncertainty
                question_text, actions = self._generate_smart_question(file_path, predicted_action, system_confidence)
                
                return ConfidenceDecision(
                    file_path=file_path,
                    confidence_level=confidence_level,
                    predicted_action=predicted_action,
                    system_confidence=system_confidence,
                    requires_user_input=True,
                    question_text=question_text,
                    suggested_actions=actions,
                    reasoning="SMART mode - needs informed decision",
                    emergency_prevention=emergency_prevention
                )
        
        elif confidence_level == ConfidenceLevel.ALWAYS:
            return ConfidenceDecision(
                file_path=file_path,
                confidence_level=confidence_level,
                predicted_action=predicted_action,
                system_confidence=system_confidence,
                requires_user_input=False,
                reasoning="ALWAYS mode - moving automatically regardless of confidence",
                emergency_prevention=emergency_prevention
            )

    def _generate_smart_question(self, file_path: str, predicted_action: Dict[str, Any], confidence: float) -> Tuple[str, List[Dict[str, Any]]]:
        """Generate an intelligent question for SMART mode"""
        
        filename = Path(file_path).name
        target_category = predicted_action.get("target_category", "unknown")
        target_location = predicted_action.get("target_location", "")
        
        # Determine what the system is uncertain about
        if confidence < 0.5:
            question_text = f"I'm not sure about '{filename}'. What type of document is this?"
            actions = [
                {"action": "business", "label": "Business document"},
                {"action": "personal", "label": "Personal document"},
                {"action": "creative", "label": "Creative work"},
                {"action": "entertainment", "label": "Entertainment industry"},
                {"action": "skip", "label": "Skip for now"}
            ]
        elif confidence < 0.65:
            question_text = f"I think '{filename}' belongs in {target_category}. Does this look right?"
            actions = [
                {"action": "confirm", "label": f"Yes, move to {target_category}"},
                {"action": "business", "label": "Actually, it's business related"},
                {"action": "personal", "label": "Actually, it's personal"},
                {"action": "skip", "label": "Leave it where it is"}
            ]
        else:
            # High confidence but below auto-move threshold
            short_location = Path(target_location).name if target_location else target_category
            question_text = f"Move '{filename}' to {short_location}?"
            actions = [
                {"action": "confirm", "label": "Yes, move it"},
                {"action": "different", "label": "Move somewhere else"},
                {"action": "skip", "label": "Not now"}
            ]
        
        return question_text, actions

    def _record_confidence_decision(self, decision: ConfidenceDecision, context: Dict[str, Any] = None):
        """Record confidence decision for learning"""
        
        # Create a learning event if user input was required
        if decision.requires_user_input:
            # This will be completed when user responds
            pass
        else:
            # Record automatic decision
            self.learning_system.record_learning_event(
                event_type="confidence_decision",
                file_path=decision.file_path,
                original_prediction={"confidence_level": decision.confidence_level.name},
                user_action=decision.predicted_action,
                confidence_before=decision.system_confidence,
                context={
                    "confidence_level": decision.confidence_level.name,
                    "emergency_prevention": decision.emergency_prevention,
                    "automatic_action": True,
                    **(context or {})
                }
            )

    def update_user_preference(self, preference_type: str, value: Any):
        """Update user preferences for confidence system"""
        
        if preference_type == "default_level":
            if value in [level.name for level in ConfidenceLevel]:
                self.user_config["default_level"] = value
        elif preference_type == "emergency_override":
            self.user_config["emergency_override_enabled"] = bool(value)
        elif preference_type == "learning_enabled":
            self.user_config["learning_enabled"] = bool(value)
        elif preference_type.startswith("context_"):
            context = preference_type.replace("context_", "")
            if "context_specific_levels" not in self.user_config:
                self.user_config["context_specific_levels"] = {}
            self.user_config["context_specific_levels"][context] = value
        elif preference_type.startswith("filetype_"):
            filetype = preference_type.replace("filetype_", "")
            if "file_type_levels" not in self.user_config:
                self.user_config["file_type_levels"] = {}
            self.user_config["file_type_levels"][filetype] = value
        
        self.save_user_config()
        self.logger.info(f"Updated preference {preference_type} to {value}")

    def get_confidence_stats(self) -> Dict[str, Any]:
        """Get statistics about confidence system usage"""
        
        # Get learning events related to confidence decisions
        confidence_events = [
            event for event in self.learning_system.learning_events
            if event.event_type == "confidence_decision"
        ]
        
        # Calculate stats
        total_decisions = len(confidence_events)
        automatic_decisions = sum(1 for event in confidence_events 
                                if event.context and event.context.get("automatic_action", False))
        
        emergency_overrides = sum(1 for event in confidence_events
                                if event.context and event.context.get("emergency_prevention", False))
        
        level_usage = {}
        for level in ConfidenceLevel:
            level_usage[level.name] = sum(1 for event in confidence_events
                                        if event.context and event.context.get("confidence_level") == level.name)
        
        return {
            "total_decisions": total_decisions,
            "automatic_decisions": automatic_decisions,
            "user_input_decisions": total_decisions - automatic_decisions,
            "emergency_overrides": emergency_overrides,
            "automation_rate": automatic_decisions / total_decisions if total_decisions > 0 else 0,
            "level_usage": level_usage,
            "current_config": self.user_config,
            "emergency_triggers": self.emergency_triggers
        }

# Testing and CLI interface
def main():
    """Command line interface for confidence system testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ADHD-Friendly Confidence System')
    parser.add_argument('--test', action='store_true', help='Run test cases')
    parser.add_argument('--config', help='Show or update configuration')
    parser.add_argument('--stats', action='store_true', help='Show confidence statistics')
    parser.add_argument('--file', help='Test confidence decision for a specific file')
    
    args = parser.parse_args()
    
    confidence_system = ADHDFriendlyConfidenceSystem()
    
    if args.test:
        test_confidence_system(confidence_system)
    elif args.stats:
        stats = confidence_system.get_confidence_stats()
        print("🧠 Confidence System Statistics:")
        print(json.dumps(stats, indent=2, default=str))
    elif args.file:
        test_file_decision(confidence_system, args.file)
    else:
        print("🧠 ADHD-Friendly Confidence System")
        print("Use --help for options")

def test_confidence_system(confidence_system: ADHDFriendlyConfidenceSystem):
    """Test the confidence system with various scenarios"""
    print("🧠 Testing ADHD-Friendly Confidence System...")
    
    test_files = [
        {
            "path": "/Users/user/Downloads/Client Name_contract_2024.pdf",
            "predicted_action": {"target_category": "entertainment_industry", "target_location": "/Users/user/GoogleDrive/AI_Organizer/01_ACTIVE_PROJECTS/Entertainment_Industry/Client Name"},
            "confidence": 0.85,
            "context": {"file_size": 2048000, "content_keywords": ["contract", "exclusivity", "Client Name"]}
        },
        {
            "path": "/Users/user/Downloads/random_screenshot.png", 
            "predicted_action": {"target_category": "misc", "target_location": "/Users/user/Documents/Screenshots"},
            "confidence": 0.45,
            "context": {"file_size": 500000}
        },
        {
            "path": "/Users/user/Desktop/urgent_business_proposal.docx",
            "predicted_action": {"target_category": "business", "target_location": "/Users/user/Documents/Business"},
            "confidence": 0.75,
            "context": {"file_size": 1024000, "content_keywords": ["proposal", "business", "urgent"]}
        }
    ]
    
    for i, test_file in enumerate(test_files, 1):
        print(f"\n📋 Test Case {i}: {Path(test_file['path']).name}")
        
        decision = confidence_system.make_confidence_decision(
            file_path=test_file["path"],
            predicted_action=test_file["predicted_action"],
            system_confidence=test_file["confidence"],
            context=test_file["context"]
        )
        
        print(f"  Confidence Level: {decision.confidence_level.name}")
        print(f"  Requires User Input: {decision.requires_user_input}")
        if decision.question_text:
            print(f"  Question: {decision.question_text}")
        print(f"  Reasoning: {decision.reasoning}")
        if decision.emergency_prevention:
            print(f"  🚨 Emergency prevention activated!")
    
    print("\n✅ Confidence system test completed!")

def test_file_decision(confidence_system: ADHDFriendlyConfidenceSystem, file_path: str):
    """Test confidence decision for a specific file"""
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"🧠 Testing confidence decision for: {Path(file_path).name}")
    
    # Mock prediction (in real use this would come from classification system)
    predicted_action = {
        "target_category": "documents",
        "target_location": "/Users/user/Documents/General"
    }
    
    decision = confidence_system.make_confidence_decision(
        file_path=file_path,
        predicted_action=predicted_action,
        system_confidence=0.65,
        context={"file_size": Path(file_path).stat().st_size}
    )
    
    print(f"  Confidence Level: {decision.confidence_level.name}")
    print(f"  Requires User Input: {decision.requires_user_input}")
    if decision.question_text:
        print(f"  Question: {decision.question_text}")
        if decision.suggested_actions:
            print("  Options:")
            for action in decision.suggested_actions:
                print(f"    - {action['label']}")
    print(f"  Reasoning: {decision.reasoning}")

if __name__ == "__main__":
    main()