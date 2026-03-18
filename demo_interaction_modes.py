#!/usr/bin/env python3
"""
Demo of Interaction Modes with AI File Organizer
Shows how different modes affect classification behavior
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interactive_classifier import InteractiveClassifier
from interaction_modes import InteractionMode

def demo_interaction_modes():
    """Demonstrate how interaction modes change behavior"""

    print("🎛️  AI File Organizer - Interaction Modes Demo")
    print("=" * 60)
    print("Based on AudioAI organizer patterns - different levels of interaction")

    classifier = InteractiveClassifier()

    # Test file (simulated)
    test_file = Path("/tmp/sample_agreement.pdf")

    print(f"\n📄 Demo: Classifying 'sample_agreement.pdf'")
    print(f"   (Simulated file with varying confidence levels)")

    # Demo each mode
    modes_to_demo = [
        (InteractionMode.NEVER, "Bulk processing mode"),
        (InteractionMode.MINIMAL, "Experienced user mode"),
        (InteractionMode.SMART, "Recommended daily use"),
        (InteractionMode.ALWAYS, "Maximum accuracy mode")
    ]

    for mode, description in modes_to_demo:
        print(f"\n" + "="*50)
        print(f"🎛️  MODE: {mode.value.upper()}")
        print(f"📝 {description}")
        print("="*50)

        # Set the mode
        classifier.set_interaction_mode(mode)

        # Simulate different confidence scenarios
        confidence_scenarios = [
            (95, "High confidence - clear entertainment contract"),
            (75, "Medium confidence - contract vs business doc"),
            (45, "Low confidence - unclear document type"),
            (25, "Very low confidence - ambiguous content")
        ]

        for confidence, scenario in confidence_scenarios:
            print(f"\n📊 Scenario: {scenario}")
            print(f"   Confidence: {confidence}%")

            # Check what the mode would do
            should_ask = classifier.interaction_manager.should_ask_user(confidence / 100)
            threshold = classifier.interaction_manager.get_confidence_threshold()

            if should_ask:
                print(f"   ❓ Action: ASK USER (below {threshold:.0%} threshold)")
                print(f"      Would show: 'Is this entertainment or business?'")
            else:
                print(f"   ✅ Action: AUTO-PROCESS (meets {threshold:.0%} threshold)")
                print(f"      Would file automatically")

        # Show mode statistics
        print(f"\n📈 Mode Performance:")
        config = classifier.interaction_manager.mode_configs[mode]
        print(f"   Threshold: {config['confidence_threshold']:.0%}")
        print(f"   Batch friendly: {'Yes' if config['batch_friendly'] else 'No'}")
        print(f"   Best for: {', '.join(config['suitable_for'][:2])}")

def demo_mode_switching():
    """Show how to switch between modes like AudioAI"""

    print(f"\n🔄 Mode Switching Demo (AudioAI Style)")
    print("=" * 50)

    classifier = InteractiveClassifier()

    # Show all available modes
    print(f"\n📋 Available Modes:")
    classifier.show_available_modes()

    # Demonstrate switching
    print(f"\n🔄 Mode Switching Examples:")

    scenarios = [
        (InteractionMode.SMART, "Starting daily work"),
        (InteractionMode.MINIMAL, "Processing trusted source"),
        (InteractionMode.NEVER, "Bulk importing 500 files"),
        (InteractionMode.ALWAYS, "Important contracts"),
        (InteractionMode.SMART, "Back to normal work")
    ]

    for mode, reason in scenarios:
        classifier.set_interaction_mode(mode)
        print(f"   Switched to {mode.value} mode for: {reason}")

    # Show final statistics
    print(f"\n📊 Usage Statistics:")
    classifier.show_interaction_stats()

def demo_real_world_usage():
    """Show real-world usage patterns"""

    print(f"\n🌍 Real-World Usage Examples")
    print("=" * 50)

    scenarios = [
        {
            'situation': 'Morning routine - organizing yesterday\'s downloads',
            'mode': InteractionMode.SMART,
            'files': 15,
            'rationale': 'Mixed content, want balance of speed and accuracy'
        },
        {
            'situation': 'Bulk importing old project files',
            'mode': InteractionMode.MINIMAL,
            'files': 200,
            'rationale': 'Known content source, prioritize speed'
        },
        {
            'situation': 'Processing critical contract documents',
            'mode': InteractionMode.ALWAYS,
            'files': 5,
            'rationale': 'Need perfect accuracy, time not critical'
        },
        {
            'situation': 'Background processing while working',
            'mode': InteractionMode.NEVER,
            'files': 50,
            'rationale': 'No interruptions needed, auto-organize'
        }
    ]

    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['situation']}")
        print(f"   📁 Files: {scenario['files']}")
        print(f"   🎛️  Mode: {scenario['mode'].value}")
        print(f"   💭 Why: {scenario['rationale']}")

        # Show what would happen
        classifier = InteractiveClassifier()
        classifier.set_interaction_mode(scenario['mode'])
        config = classifier.interaction_manager.get_processing_strategy()

        print(f"   📊 Threshold: {config['confidence_threshold']:.0%}")
        print(f"   ⚡ Auto-process: {'Yes' if config['auto_process'] else 'No'}")

if __name__ == "__main__":
    demo_interaction_modes()
    demo_mode_switching()
    demo_real_world_usage()

    print(f"\n🎉 Interaction Modes Demo Complete!")
    print(f"   Now your AI File Organizer works like AudioAI with flexible interaction levels")