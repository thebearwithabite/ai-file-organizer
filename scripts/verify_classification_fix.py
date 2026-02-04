#!/usr/bin/env python3
"""
Quick verification script for the classification pipeline fixes.
Run this after updating hybrid_config.json with the correct IP.

Usage:
    python scripts/verify_classification_fix.py [path_to_test_file]
"""

import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("Classification Pipeline Verification")
    print("=" * 60)
    
    # 1. Check config
    print("\n1. Checking hybrid_config.json...")
    try:
        from gdrive_integration import get_metadata_root
        import json
        config_path = get_metadata_root() / "config" / "hybrid_config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            remote = config.get("remote_powerhouse", {})
            if remote.get("enabled"):
                ip = remote.get("services", {}).get("ollama", {}).get("ip") or remote.get("ip")
                print(f"   ✅ Remote Ollama enabled at: {ip}")
                if "192.168.86.23" in str(ip):
                    print("   ⚠️  WARNING: Still using OLD IP (.23) - update to .26!")
            else:
                print("   ℹ️  Remote powerhouse disabled - using local/fallback")
        else:
            print(f"   ❌ Config not found at {config_path}")
    except Exception as e:
        print(f"   ❌ Error loading config: {e}")

    # 2. Check Ollama connectivity
    print("\n2. Checking Ollama connectivity...")
    try:
        import requests
        from gdrive_integration import get_metadata_root
        import json
        config_path = get_metadata_root() / "config" / "hybrid_config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            remote = config.get("remote_powerhouse", {})
            ip = remote.get("services", {}).get("ollama", {}).get("ip") or remote.get("ip", "localhost")
            port = remote.get("services", {}).get("ollama", {}).get("port", 11434)
            
            url = f"http://{ip}:{port}/api/tags"
            response = requests.get(url, timeout=5)
            if response.ok:
                models = response.json().get("models", [])
                print(f"   ✅ Ollama reachable at {ip}:{port}")
                print(f"   📦 Models: {', '.join(m['name'] for m in models[:4])}")
            else:
                print(f"   ❌ Ollama returned {response.status_code}")
        else:
            print("   ⏭️  Skipping (no config)")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to Ollama at {ip}:{port}")
        print("      Check: Is the IP correct? Is Ollama running?")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 3. Check classifier import
    print("\n3. Checking UnifiedClassificationService...")
    try:
        from unified_classifier import UnifiedClassificationService
        classifier = UnifiedClassificationService()
        print("   ✅ Classifier initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return 1

    # 4. Test classification if file provided
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
        print(f"\n4. Testing classification on: {test_file.name}")
        if test_file.exists():
            try:
                result = classifier.classify_file(test_file)
                print(f"   Category: {result.get('category', 'unknown')}")
                print(f"   Confidence: {result.get('confidence', 0):.0%}")
                print(f"   Source: {result.get('source', 'unknown')}")
                if result.get('confidence', 0) >= 0.7:
                    print("   ✅ High confidence classification!")
                else:
                    print("   ⚠️  Low confidence - check Ollama/Gemini connectivity")
            except Exception as e:
                print(f"   ❌ Classification failed: {e}")
        else:
            print(f"   ❌ File not found: {test_file}")
    else:
        print("\n4. No test file provided (optional)")
        print("   Usage: python verify_classification_fix.py /path/to/image.png")

    print("\n" + "=" * 60)
    print("Done!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
