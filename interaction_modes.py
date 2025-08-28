#!/usr/bin/env python3
"""
Interaction Modes for AI File Organizer
Based on AudioAI organizer patterns - provides different levels of user interaction
"""

from enum import Enum
from typing import Dict, Any
import json
from pathlib import Path

class InteractionMode(Enum):
    """Different interaction modes for file organization"""
    SMART = "smart"       # 70% confidence threshold - asks when uncertain (recommended)
    MINIMAL = "minimal"   # 40% confidence threshold - only very uncertain files
    ALWAYS = "always"     # 100% threshold - asks about every file (maximum accuracy)  
    NEVER = "never"       # 0% threshold - fully automatic (bulk processing)

class InteractionModeManager:
    """
    Manages interaction modes and confidence thresholds
    Based on AudioAI organizer interaction patterns
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.config_file = self.base_dir / "interaction_config.json"
        
        # Default mode configuration (matching AudioAI patterns)
        self.mode_configs = {
            InteractionMode.SMART: {
                'confidence_threshold': 0.70,
                'description': 'Asks when uncertain (recommended)',
                'auto_process': True,
                'ask_threshold': 0.70,
                'batch_friendly': True,
                'suitable_for': ['daily_use', 'mixed_content', 'learning_phase']
            },
            InteractionMode.MINIMAL: {
                'confidence_threshold': 0.40,
                'description': 'Only very uncertain files',
                'auto_process': True,
                'ask_threshold': 0.40,
                'batch_friendly': True,
                'suitable_for': ['experienced_users', 'bulk_processing', 'trusted_content']
            },
            InteractionMode.ALWAYS: {
                'confidence_threshold': 1.0,
                'description': 'Maximum accuracy - asks about every file',
                'auto_process': False,
                'ask_threshold': 0.0,
                'batch_friendly': False,
                'suitable_for': ['critical_content', 'learning_system', 'perfect_accuracy']
            },
            InteractionMode.NEVER: {
                'confidence_threshold': 0.0,
                'description': 'Fully automatic - no questions',
                'auto_process': True,
                'ask_threshold': 1.0,  # Never ask
                'batch_friendly': True,
                'suitable_for': ['bulk_import', 'trusted_sources', 'background_processing']
            }
        }
        
        # Load current configuration
        self.current_mode = self.load_interaction_mode()
        
        # Statistics tracking (like AudioAI)
        self.stats = self.load_interaction_stats()
    
    def load_interaction_mode(self) -> InteractionMode:
        """Load saved interaction mode or return default"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    mode_name = config.get('current_mode', 'smart')
                    return InteractionMode(mode_name)
        except Exception:
            pass
        
        return InteractionMode.SMART  # Default to smart mode
    
    def save_interaction_mode(self, mode: InteractionMode):
        """Save interaction mode to config file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                'current_mode': mode.value,
                'last_updated': self._get_timestamp(),
                'mode_history': self.stats.get('mode_history', [])
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save interaction mode: {e}")
    
    def set_interaction_mode(self, mode: InteractionMode):
        """Set the interaction mode (like AudioAI organizer)"""
        old_mode = self.current_mode
        self.current_mode = mode
        
        # Save the change
        self.save_interaction_mode(mode)
        
        # Update statistics
        self.stats['mode_changes'] = self.stats.get('mode_changes', 0) + 1
        self.stats['mode_history'] = self.stats.get('mode_history', [])
        self.stats['mode_history'].append({
            'from': old_mode.value if old_mode else None,
            'to': mode.value,
            'timestamp': self._get_timestamp()
        })
        
        self.save_interaction_stats()
        
        print(f"✅ Interaction mode changed to: {mode.value}")
        print(f"   Confidence threshold: {self.get_confidence_threshold():.0%}")
        print(f"   {self.get_mode_description()}")
    
    def get_interaction_mode(self) -> InteractionMode:
        """Get current interaction mode"""
        return self.current_mode
    
    def get_confidence_threshold(self) -> float:
        """Get confidence threshold for current mode"""
        return self.mode_configs[self.current_mode]['confidence_threshold']
    
    def get_mode_description(self) -> str:
        """Get description of current mode"""
        return self.mode_configs[self.current_mode]['description']
    
    def should_ask_user(self, confidence: float) -> bool:
        """Determine if we should ask the user based on current mode and confidence"""
        threshold = self.get_confidence_threshold()
        
        if self.current_mode == InteractionMode.ALWAYS:
            return True
        elif self.current_mode == InteractionMode.NEVER:
            return False
        else:
            return confidence < threshold
    
    def get_processing_strategy(self) -> Dict[str, Any]:
        """Get processing strategy for current mode"""
        config = self.mode_configs[self.current_mode].copy()
        config['mode'] = self.current_mode.value
        return config
    
    def show_mode_info(self):
        """Display current mode information (like AudioAI)"""
        print(f"\n🎛️  Current Interaction Mode: {self.current_mode.value.upper()}")
        print("=" * 50)
        
        config = self.mode_configs[self.current_mode]
        
        print(f"📊 Confidence Threshold: {config['confidence_threshold']:.0%}")
        print(f"📝 Description: {config['description']}")
        print(f"⚡ Auto-process high confidence: {'Yes' if config['auto_process'] else 'No'}")
        print(f"📦 Batch processing friendly: {'Yes' if config['batch_friendly'] else 'No'}")
        print(f"🎯 Best for: {', '.join(config['suitable_for'])}")
        
        # Show statistics
        if self.stats.get('files_processed', 0) > 0:
            print(f"\n📈 Usage Statistics:")
            print(f"   Files processed in this mode: {self.stats.get('files_processed', 0)}")
            print(f"   Questions asked: {self.stats.get('questions_asked', 0)}")
            print(f"   Auto-processed: {self.stats.get('auto_processed', 0)}")
            
            if self.stats.get('questions_asked', 0) > 0:
                question_rate = self.stats['questions_asked'] / self.stats['files_processed'] * 100
                print(f"   Question rate: {question_rate:.1f}%")
    
    def show_all_modes(self):
        """Display information about all available modes"""
        print(f"\n🎛️  Available Interaction Modes")
        print("=" * 60)
        
        for mode, config in self.mode_configs.items():
            current = " (CURRENT)" if mode == self.current_mode else ""
            print(f"\n{mode.value.upper()}{current}:")
            print(f"   📊 Confidence: {config['confidence_threshold']:.0%}")
            print(f"   📝 {config['description']}")
            print(f"   🎯 Best for: {', '.join(config['suitable_for'][:2])}")
    
    def recommend_mode(self, file_count: int = 0, content_type: str = "mixed") -> InteractionMode:
        """Recommend interaction mode based on context"""
        
        # Large batch processing
        if file_count > 100:
            if content_type == "trusted":
                return InteractionMode.MINIMAL
            else:
                return InteractionMode.SMART
        
        # Small batch or single files
        elif file_count <= 10:
            return InteractionMode.SMART
        
        # Medium batch
        else:
            return InteractionMode.SMART
    
    def load_interaction_stats(self) -> Dict:
        """Load interaction statistics"""
        stats_file = self.base_dir / "interaction_stats.json"
        
        try:
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return {
            'files_processed': 0,
            'questions_asked': 0,
            'auto_processed': 0,
            'mode_changes': 0,
            'mode_history': []
        }
    
    def save_interaction_stats(self):
        """Save interaction statistics"""
        stats_file = self.base_dir / "interaction_stats.json"
        
        try:
            stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception:
            pass
    
    def update_stats(self, asked_question: bool, auto_processed: bool):
        """Update processing statistics"""
        self.stats['files_processed'] = self.stats.get('files_processed', 0) + 1
        
        if asked_question:
            self.stats['questions_asked'] = self.stats.get('questions_asked', 0) + 1
        
        if auto_processed:
            self.stats['auto_processed'] = self.stats.get('auto_processed', 0) + 1
        
        self.save_interaction_stats()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

def test_interaction_modes():
    """Test the interaction mode system"""
    print("🧪 Testing Interaction Modes")
    print("=" * 50)
    
    manager = InteractionModeManager()
    
    # Show current mode
    manager.show_mode_info()
    
    # Show all modes
    manager.show_all_modes()
    
    # Test mode switching
    print(f"\n🔄 Testing Mode Switching:")
    
    test_modes = [InteractionMode.MINIMAL, InteractionMode.ALWAYS, InteractionMode.NEVER, InteractionMode.SMART]
    
    for mode in test_modes:
        print(f"\n   Testing {mode.value} mode:")
        manager.set_interaction_mode(mode)
        
        # Test confidence thresholds
        test_confidences = [0.2, 0.5, 0.8, 0.95]
        for confidence in test_confidences:
            should_ask = manager.should_ask_user(confidence)
            status = "ASK" if should_ask else "AUTO"
            print(f"      {confidence:.0%} confidence → {status}")
    
    # Test recommendations
    print(f"\n💡 Mode Recommendations:")
    scenarios = [
        (5, "mixed", "Small batch mixed content"),
        (50, "trusted", "Medium batch trusted content"), 
        (500, "mixed", "Large batch mixed content"),
        (1000, "trusted", "Bulk import trusted content")
    ]
    
    for file_count, content_type, description in scenarios:
        recommended = manager.recommend_mode(file_count, content_type)
        print(f"   {description}: {recommended.value}")

if __name__ == "__main__":
    test_interaction_modes()