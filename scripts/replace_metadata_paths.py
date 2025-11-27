#!/usr/bin/env python3
"""
Script to replace all 04_METADATA_SYSTEM references with get_metadata_root()
This is part of the full-reset workflow STEP 4.
"""
import re
from pathlib import Path

# Files to update (from grep results)
FILES_TO_UPDATE = [
    "gdrive_integration.py",
    "automated_deduplication_service.py",
    "background_monitor.py",
    "enhanced_librarian.py",
    "adaptive_background_monitor.py",
    "interactive_batch_processor.py",
    "integrated_organizer.py",
    "universal_adaptive_learning.py",
    "vision_analyzer.py",
    "librarian.py",
    "interactive_classifier_fixed.py",
    "veo_prompt_generator.py",
    "audio_analyzer.py",
    "emergency_space_protection.py",
    "confidence_system.py",
    "vector_librarian.py",
    "interactive_classifier.py",
    "classification_engine.py",
]

def update_file(file_path: Path):
    """Update a single file with metadata path replacements"""
    print(f"Processing: {file_path.name}")

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Pattern 1: get_ai_organizer_root() / "04_METADATA_SYSTEM" → get_metadata_root()
    content = re.sub(
        r'get_ai_organizer_root\(\)\s*/\s*"04_METADATA_SYSTEM"',
        'get_metadata_root()',
        content
    )

    # Pattern 2: self.base_dir / "04_METADATA_SYSTEM" / ... → get_metadata_root() / ...
    content = re.sub(
        r'self\.base_dir\s*/\s*"04_METADATA_SYSTEM"\s*/',
        'get_metadata_root() / ',
        content
    )

    # Pattern 3: base_dir / "04_METADATA_SYSTEM" / ... → get_metadata_root() / ...
    content = re.sub(
        r'(?<![.])\bbase_dir\s*/\s*"04_METADATA_SYSTEM"\s*/',
        'get_metadata_root() / ',
        content
    )

    # Check if we need to add import for get_metadata_root
    if 'get_metadata_root' in content and 'from gdrive_integration import' in content:
        # Update existing import
        content = re.sub(
            r'from gdrive_integration import get_ai_organizer_root',
            'from gdrive_integration import get_ai_organizer_root, get_metadata_root',
            content
        )

    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Updated {file_path.name}")
        return True
    else:
        print(f"  ⏭️  No changes needed for {file_path.name}")
        return False

def main():
    project_root = Path("/Users/ryanthomson/Github/ai-file-organizer")

    print("=" * 60)
    print("METADATA PATH REPLACEMENT SCRIPT")
    print("=" * 60)
    print()

    updated_count = 0
    for filename in FILES_TO_UPDATE:
        file_path = project_root / filename
        if file_path.exists():
            if update_file(file_path):
                updated_count += 1
        else:
            print(f"⚠️  File not found: {filename}")

    print()
    print("=" * 60)
    print(f"COMPLETE: Updated {updated_count}/{len(FILES_TO_UPDATE)} files")
    print("=" * 60)

if __name__ == "__main__":
    main()
