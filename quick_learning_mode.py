#!/usr/bin/env python3
"""
Quick Learning Mode Activator
Sets the AI File Organizer to aggressive learning mode for faster training
"""

import sys
from pathlib import Path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interaction_modes import InteractionModeManager, InteractionMode

def enable_learning_mode():
    """Enable aggressive learning mode for faster training"""
    
    print("🚀 Activating LEARNING MODE for rapid system training")
    print("=" * 60)
    
    manager = InteractionModeManager()
    manager.set_interaction_mode(InteractionMode.LEARNING)
    
    print("\n📚 LEARNING MODE ACTIVE:")
    print(f"   • Confidence threshold: 85% (will ask about most files)")
    print(f"   • Purpose: Build intelligence quickly from your decisions")
    print(f"   • Expected: 15-30 files per project for smart suggestions")
    print(f"   • Timeline: 2-3 organization sessions to get intelligent")
    
    print("\n💡 Learning Tips:")
    print(f"   • Organize your most representative files first")
    print(f"   • Mix file types (PDFs, images, videos, docs)")
    print(f"   • Use consistent folder names")
    print(f"   • The system learns from EVERY file you organize")
    
    print("\n🔄 Switch back when ready:")
    print(f"   python quick_learning_mode.py --smart")
    
    return True

def enable_smart_mode():
    """Switch back to smart mode after learning"""
    
    print("🎯 Switching to SMART MODE (normal operation)")
    print("=" * 50)
    
    manager = InteractionModeManager()
    manager.set_interaction_mode(InteractionMode.SMART)
    
    print("\n✅ SMART MODE ACTIVE:")
    print(f"   • Confidence threshold: 75%")
    print(f"   • Balanced questioning and automation")
    print(f"   • Uses learned patterns from training")

def show_status():
    """Show current interaction mode status"""
    
    manager = InteractionModeManager()
    current_mode = manager.get_interaction_mode()
    threshold = manager.get_confidence_threshold()
    description = manager.get_mode_description()
    
    print("📊 Current AI File Organizer Status:")
    print("=" * 40)
    print(f"Mode: {current_mode.value.upper()}")
    print(f"Confidence threshold: {threshold:.0%}")
    print(f"Description: {description}")
    
    # Show learning progress estimate
    try:
        from video_project_trainer import VideoProjectTrainer
        trainer = VideoProjectTrainer()
        
        # Get learning stats (this would need to be implemented)
        print(f"\n🧠 Learning Progress:")
        print(f"   Database: {trainer.db_path}")
        print(f"   Ready for pattern recognition")
        
    except Exception as e:
        print(f"\n⚠️  Learning system status: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI File Organizer Learning Mode Controller")
    parser.add_argument("--smart", action="store_true", help="Switch to smart mode")
    parser.add_argument("--learning", action="store_true", help="Switch to learning mode")  
    parser.add_argument("--status", action="store_true", help="Show current status")
    
    args = parser.parse_args()
    
    if args.smart:
        enable_smart_mode()
    elif args.learning:
        enable_learning_mode()
    elif args.status:
        show_status()
    else:
        # Default: enable learning mode
        enable_learning_mode()