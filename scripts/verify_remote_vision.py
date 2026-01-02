import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vision_analyzer import VisionAnalyzer

def verify_remote_vision():
    print("🧪 Verifying Remote Vision (Qwen 2.5 VL)...")
    print("-" * 50)
    
    analyzer = VisionAnalyzer()
    
    # Check if remote is reported as enabled
    if not analyzer.remote_enabled:
        print("❌ Remote vision offloading is DISABLED in configuration.")
        return

    print(f"📡 Worker IP: {analyzer.remote_ip}")
    print(f"🧠 Model: {analyzer.remote_model}")
    print("-" * 50)
    
    # Use the local screenshot for testing
    test_image = project_root / "sreenshot.jpg"
    if not test_image.exists():
        print(f"❌ Test image not found at {test_image}")
        return

    print(f"📸 Analyzing image: {test_image.name}")
    print("⏳ This may take a moment (offloading to RTX 5090)...")
    
    try:
        # VisionAnalyzer.analyze_image is synchronous
        result = analyzer.analyze_image(str(test_image))
        
        if result and result.get('success', False):
            print(f"✅ ANALYSIS SUCCESSFUL!")
            print(f"📄 Description: {result.get('description', '')[:200]}...")
            print("-" * 50)
            print("🚀 Remote Powerhouse is OFFICIALLY working for Vision!")
        else:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

if __name__ == "__main__":
    verify_remote_vision()
