import sys
import os
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyVertex")

# Add project root to path
sys.path.append(str(Path(__file__).parent))

try:
    from vision_analyzer import VisionAnalyzer
    
    print("\n🔒 Testing Vertex AI / Service Account Auth Integration...")
    
    # Initialize analyzer
    analyzer = VisionAnalyzer()
    
    print(f"   API Initialized: {analyzer.api_initialized}")
    print(f"   Using Vertex AI: {analyzer.use_vertex}")
    
    if not analyzer.api_initialized:
        print("❌ Error: VisionAnalyzer failed to initialize.")
        sys.exit(1)
        
    if not analyzer.use_vertex:
        print("⚠️ Warning: VisionAnalyzer initialized but NOT using Vertex AI (Service Account).")
        print("   Falling back to standard Gemini API Key.")
    else:
        print("✅ SUCCESS: VisionAnalyzer is using Vertex AI via Service Account.")
        
    # Optional: Run a test analysis on a dummy or existing image if available
    # For now, just checking the initialization and model object
    if analyzer.model:
        print(f"   Model Initialized: {analyzer.model.model_name}")
    else:
        print("❌ Error: Model object is missing.")
        sys.exit(1)

except Exception as e:
    print(f"❌ Exception during verification: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
