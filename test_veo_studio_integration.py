#!/usr/bin/env python3
"""
VEO Studio Integration Test
Tests the VEO Studio API endpoints and script analysis functionality

Usage:
    python test_veo_studio_integration.py
"""

from api.veo_studio_api import (
    extract_assets_from_script,
    count_scenes_and_shots,
    Asset,
)
)

# Sample script for testing
SAMPLE_SCRIPT = """
INT. SPACESHIP BRIDGE - DAY

The CAPTAIN stands at the helm, looking at the viewscreen.

CAPTAIN
(determined)
We need to reach the planet before sunset.

ENGINEER enters, carrying a datapad.

ENGINEER
Captain, I've found the problem. The warp drive is offline.

CAPTAIN
Can you fix it?

ENGINEER
Give me ten minutes.

EXT. ALIEN PLANET - DUSK

The spaceship lands on a barren landscape. Dust swirls around the landing gear.

INT. SPACESHIP CORRIDOR - CONTINUOUS

CAPTAIN and ENGINEER walk quickly toward the airlock.

CAPTAIN
Remember, we're here for the artifact. Nothing else matters.
"""


def test_asset_extraction():
    """Test asset extraction from script"""
    print("=" * 60)
    print("TEST 1: Asset Extraction")
    print("=" * 60)
    
    assets = extract_assets_from_script(SAMPLE_SCRIPT)
    
    print(f"\nTotal assets found: {len(assets)}")
    print("\nAssets by type:")
    
    # Group by type
    by_type = {}
    for asset in assets:
        if asset.type not in by_type:
            by_type[asset.type] = []
        by_type[asset.type].append(asset)
    
    for asset_type, items in by_type.items():
        print(f"\n  {asset_type.upper()} ({len(items)}):")
        for item in items:
            print(f"    - {item.name} (mentioned {item.occurrences}x)")
    
    # Assertions
    assert len(assets) > 0, "Should find at least some assets"
    assert any(a.name == "CAPTAIN" for a in assets), "Should find CAPTAIN character"
    assert any(a.name == "ENGINEER" for a in assets), "Should find ENGINEER character"
    assert any(a.type == "location" for a in assets), "Should find location assets"
    
    print("\n✅ Asset extraction test PASSED")
    return True


def test_scene_counting():
    """Test scene and shot counting"""
    print("\n" + "=" * 60)
    print("TEST 2: Scene and Shot Counting")
    print("=" * 60)
    
    scene_count, shot_count = count_scenes_and_shots(SAMPLE_SCRIPT)
    
    print(f"\nScenes detected: {scene_count}")
    print(f"Estimated shots: {shot_count}")
    print(f"Average shots per scene: {shot_count / scene_count:.1f}")
    
    # Assertions
    assert scene_count > 0, "Should find at least one scene"
    assert shot_count >= scene_count, "Shots should be >= scenes"
    assert scene_count == 3, "Sample script has 3 scenes"
    
    print("\n✅ Scene counting test PASSED")
    return True


def test_integration():
    """Test complete integration workflow"""
    print("\n" + "=" * 60)
    print("TEST 3: Integration Workflow")
    print("=" * 60)
    
    # Step 1: Analyze script
    print("\nStep 1: Analyzing script...")
    assets = extract_assets_from_script(SAMPLE_SCRIPT)
    scene_count, shot_count = count_scenes_and_shots(SAMPLE_SCRIPT)
    
    print(f"  ✓ Found {len(assets)} assets")
    print(f"  ✓ Detected {scene_count} scenes")
    print(f"  ✓ Estimated {shot_count} shots")
    
    # Step 2: Verify asset types
    print("\nStep 2: Verifying asset types...")
    character_count = len([a for a in assets if a.type == 'character'])
    location_count = len([a for a in assets if a.type == 'location'])
    
    print(f"  ✓ Characters: {character_count}")
    print(f"  ✓ Locations: {location_count}")
    
    # Step 3: Verify data structure
    print("\nStep 3: Verifying data structures...")
    assert all(isinstance(a, Asset) for a in assets), "All assets should be Asset objects"
    assert all(hasattr(a, 'type') for a in assets), "Assets should have type"
    assert all(hasattr(a, 'name') for a in assets), "Assets should have name"
    assert all(hasattr(a, 'occurrences') for a in assets), "Assets should have occurrences"
    
    print("  ✓ All assets have required fields")
    print("  ✓ Data structures valid")
    
    print("\n✅ Integration test PASSED")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("VEO STUDIO INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        # Run tests
        test_asset_extraction()
        test_scene_counting()
        test_integration()
        
        # Summary
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✅")
        print("=" * 60)
        print("\nVEO Studio backend is working correctly!")
        print("Ready for frontend integration.")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
