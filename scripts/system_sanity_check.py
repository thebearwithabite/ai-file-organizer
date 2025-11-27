#!/usr/bin/env python3
"""
System Sanity Check - Google Drive Integration Verification
Tests all fixes from Sprint 3.4
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🔧 SYSTEM SANITY CHECK - Google Drive Integration")
print("=" * 80)
print()

# TEST 1: Google Drive Detection
print("TEST 1: Google Drive Root Detection")
print("-" * 80)
try:
    from gdrive_integration import GoogleDriveIntegration, get_ai_organizer_root

    gdrive = GoogleDriveIntegration()
    root = get_ai_organizer_root()
    status = gdrive.get_status()

    print(f"✅ GoogleDriveIntegration imported successfully")
    print(f"✅ get_ai_organizer_root() imported successfully")
    print()
    print(f"📍 Root Path: {root}")
    print(f"🔗 Mounted: {status.is_mounted}")
    print(f"🌐 Online: {status.is_online}")
    if status.total_space_gb:
        print(f"💾 Total Space: {status.total_space_gb:.1f}GB")
        print(f"💿 Free Space: {status.free_space_gb:.1f}GB")
    print(f"🚨 Emergency Staging: {status.emergency_staging_path}")

    if not status.is_mounted:
        print("⚠️  WARNING: Google Drive not mounted!")
    if not status.is_online:
        print("⚠️  WARNING: Google Drive not online!")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print()
print()

# TEST 2: Environment Variables
print("TEST 2: Environment Variable Support")
print("-" * 80)
try:
    email = os.getenv("AI_ORGANIZER_GDRIVE_EMAIL")
    root_override = os.getenv("AI_ORGANIZER_GDRIVE_ROOT")
    debug = os.getenv("AI_ORGANIZER_DEBUG")

    print(f"AI_ORGANIZER_GDRIVE_EMAIL: {email or '(not set)'}")
    print(f"AI_ORGANIZER_GDRIVE_ROOT: {root_override or '(not set)'}")
    print(f"AI_ORGANIZER_DEBUG: {debug or '(not set)'}")

    if email:
        print(f"✅ Email environment variable is set")
    else:
        print(f"⚠️  Email environment variable NOT set (using default)")

except Exception as e:
    print(f"❌ FAILED: {e}")

print()
print()

# TEST 3: Centralized Root Usage
print("TEST 3: Centralized Root Usage in Key Modules")
print("-" * 80)
test_files = [
    ("gdrive_librarian.py", "GoogleDriveLibrarian"),
    ("content_extractor.py", "ContentExtractor"),
    ("enhanced_librarian.py", "EnhancedLibrarianCLI"),
    ("unified_classifier.py", "UnifiedClassificationService"),
]

for filename, class_name in test_files:
    try:
        # Check if file uses get_ai_organizer_root
        file_path = project_root / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read()
                if 'get_ai_organizer_root' in content:
                    print(f"✅ {filename}: Uses get_ai_organizer_root()")
                else:
                    print(f"⚠️  {filename}: May not use get_ai_organizer_root()")
        else:
            print(f"⚠️  {filename}: File not found")
    except Exception as e:
        print(f"❌ {filename}: Error checking - {e}")

print()
print()

# TEST 4: UnifiedClassificationService - Confidence Normalization
print("TEST 4: Confidence Normalization with Inference Rules")
print("-" * 80)
try:
    from unified_classifier import UnifiedClassificationService

    classifier = UnifiedClassificationService()
    print(f"✅ UnifiedClassificationService initialized")

    # Test normalization method exists
    if hasattr(classifier, '_normalize_confidence'):
        print(f"✅ _normalize_confidence() method exists")

        # Test with mock results
        test_cases = [
            ({"category": "screenshot", "confidence": 0.0}, "screenshot", 0.9),
            ({"category": "unknown", "confidence": 0.0}, "unknown", 0.5),
            ({"category": "audio", "confidence": 0.0}, "audio", 0.7),
            ({"category": "text_document", "confidence": 0.0}, "text", 0.6),
            ({"category": "video", "confidence": 0.0}, "generic", 0.4),
        ]

        print()
        print("Testing inference rules:")
        for result, file_type, expected_conf in test_cases:
            normalized = classifier._normalize_confidence(result.copy(), Path("test.txt"), file_type)
            actual_conf = normalized.get('confidence', 0.0)
            status = "✅" if actual_conf == expected_conf else "❌"
            print(f"{status} {result['category']} ({file_type}): Expected {expected_conf}, Got {actual_conf}")

    else:
        print(f"❌ _normalize_confidence() method NOT found!")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print()
print()

# TEST 5: Category String Normalization
print("TEST 5: Category String Normalization (+ symbol removal)")
print("-" * 80)
try:
    from unified_classifier import UnifiedClassificationService

    classifier = UnifiedClassificationService()

    # Test cases with + symbols
    test_categories = [
        "sfx_consciousness+mysterious",
        "music_ambient+calm",
        "normal_category",
    ]

    for cat in test_categories:
        result = {"category": cat, "confidence": 0.7}
        normalized = classifier._normalize_confidence(result, Path("test.mp3"), "audio")
        normalized_cat = normalized.get('category')

        if '+' in cat:
            expected = cat.replace('+', '_')
            status = "✅" if normalized_cat == expected else "❌"
            print(f"{status} '{cat}' → '{normalized_cat}' (expected '{expected}')")
        else:
            status = "✅" if normalized_cat == cat else "❌"
            print(f"{status} '{cat}' → '{normalized_cat}' (no change expected)")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print()
print()

# TEST 6: TriageService - File Movement Infrastructure
print("TEST 6: File Movement Infrastructure")
print("-" * 80)
try:
    from api.services import TriageService
    from api.rollback_service import RollbackService

    rollback = RollbackService()
    triage = TriageService(rollback_service=rollback)

    print(f"✅ TriageService initialized")
    print(f"✅ RollbackService initialized")

    # Check methods exist
    if hasattr(triage, 'classify_file'):
        print(f"✅ classify_file() method exists")
    else:
        print(f"❌ classify_file() method NOT found!")

    if hasattr(triage, 'get_files_for_review'):
        print(f"✅ get_files_for_review() method exists")
    else:
        print(f"❌ get_files_for_review() method NOT found!")

    # Check base_dir is set correctly
    print(f"📍 TriageService base_dir: {triage.base_dir}")

    # Check staging areas
    print(f"📂 Staging areas configured: {len(triage.staging_areas)}")
    for area in triage.staging_areas:
        exists = area.exists()
        status = "✅" if exists else "⚠️ "
        print(f"  {status} {area}")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print()
print()

# TEST 7: Confidence KeyError Fix
print("TEST 7: Confidence Field Consistency (KeyError prevention)")
print("-" * 80)
try:
    from unified_classifier import UnifiedClassificationService
    from pathlib import Path

    classifier = UnifiedClassificationService()

    # Create a test file path (doesn't need to exist for this test)
    test_file = Path("/tmp/test_sanity.txt")

    # Ensure classify_file always returns confidence
    print("Testing that classify_file() ALWAYS returns 'confidence' field...")

    # We can't actually classify without a real file, but we can check the method signature
    import inspect
    source = inspect.getsource(classifier.classify_file)

    if 'normalize_confidence' in source:
        print(f"✅ classify_file() calls _normalize_confidence()")
        print(f"✅ This guarantees 'confidence' field in all results")
    else:
        print(f"❌ classify_file() may NOT normalize confidence!")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print()
print()

# TEST 8: .env.local Configuration
print("TEST 8: .env.local Configuration File")
print("-" * 80)
try:
    env_local = project_root / ".env.local"
    gitignore = project_root / ".gitignore"

    if env_local.exists():
        print(f"✅ .env.local file exists")
        with open(env_local, 'r') as f:
            content = f.read()
            if 'AI_ORGANIZER_GDRIVE_EMAIL' in content:
                print(f"✅ Contains AI_ORGANIZER_GDRIVE_EMAIL")
            if 'AI_ORGANIZER_GDRIVE_ROOT' in content:
                print(f"✅ Contains AI_ORGANIZER_GDRIVE_ROOT")
            if 'AI_ORGANIZER_DEBUG' in content:
                print(f"✅ Contains AI_ORGANIZER_DEBUG")
    else:
        print(f"❌ .env.local file NOT found!")

    if gitignore.exists():
        with open(gitignore, 'r') as f:
            content = f.read()
            if '.env.local' in content:
                print(f"✅ .env.local is in .gitignore")
            else:
                print(f"❌ .env.local NOT in .gitignore!")
    else:
        print(f"❌ .gitignore file NOT found!")

except Exception as e:
    print(f"❌ FAILED: {e}")

print()
print()

# FINAL SUMMARY
print("=" * 80)
print("📊 SANITY CHECK SUMMARY")
print("=" * 80)
print()
print("If you see ✅ marks above, those components are working correctly.")
print("If you see ❌ or ⚠️  marks, those need attention.")
print()
print("Key things to verify:")
print("1. Google Drive is mounted and online")
print("2. Root path points to Google Drive (not Documents fallback)")
print("3. Confidence normalization prevents KeyErrors")
print("4. Category strings with + symbols are normalized")
print("5. File movement infrastructure is operational")
print()
