#!/usr/bin/env python3
"""
Test script for hierarchical file organization
Demonstrates project → episode → media type organization
"""

from pathlib import Path
from hierarchical_organizer import HierarchicalOrganizer

def test_hierarchical_organization():
    """Test the hierarchical organization system with various filenames"""
    organizer = HierarchicalOrganizer()

    # Test cases with different filename patterns
    test_files = [
        # VEO project files
        ("veo_prompt_Episode_02_AttentionIsland_scene1.mp4", "creative"),
        ("The_Papers_That_Dream_ep03_contrast_catastrophe.jpg", "creative"),
        ("episode_02_attention_island_audio_mix.mp3", "creative"),

        # Development project files
        ("ai_file_organizer_bug_fix.py", "development"),
        ("calibration_vector_v2.js", "development"),

        # Generic creative files
        ("my_creative_video.mp4", "creative"),
        ("soundtrack_final.mp3", "audio"),
        ("design_mockup.png", "image"),

        # Business files
        ("contract_finn_jones.pdf", "financial"),
    ]

    print("🧪 Testing Hierarchical Organization System\n")
    print("=" * 80)

    for filename, category in test_files:
        file_path = Path(f"/tmp/test/{filename}")

        print(f"\n📄 File: {filename}")
        print(f"📂 Category: {category}")

        # Get hierarchical organization suggestion
        suggestion = organizer.suggest_organization(file_path, category)

        print(f"✨ Suggested Path: {suggestion['suggested_path']}")
        print(f"   Project: {suggestion['project'] or 'Not detected'}")
        print(f"   Episode: {suggestion['episode'] or 'Not detected'}")
        print(f"   Media Type: {suggestion['media_type']}")
        print(f"   Hierarchy Level: {suggestion['hierarchy_level']}")
        print(f"   Reasoning: {suggestion['reasoning']}")

    print("\n" + "=" * 80)
    print("\n✅ Hierarchical organization test complete!")
    print("\nExample folder structure created:")
    print("""
01_ACTIVE_PROJECTS/
├── Creative_Projects/
│   ├── The_Papers_That_Dream/
│   │   ├── Episode_02_AttentionIsland/
│   │   │   ├── Video/
│   │   │   ├── Audio/
│   │   │   └── Images/
│   │   └── Episode_03_ContrastCatastrophe/
│   │       ├── Video/
│   │       └── Images/
│   └── VEO_Prompt_Machine/
│       └── Video/
└── Development_Projects/
    ├── AI_File_Organizer/
    │   └── Scripts/
    └── Calibration_Vector/
        └── Scripts/
    """)

if __name__ == "__main__":
    test_hierarchical_organization()
