import asyncio
import os
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hybrid_librarian import HybridLibrarian

def verify_remote_embeddings():
    print("🧪 Verifying Remote Embeddings (nomic-embed-text)...")
    print("-" * 50)
    
    librarian = HybridLibrarian()
    
    # Check if remote is reported as enabled
    if not librarian.remote_enabled:
        print("❌ Remote embeddings offloading is DISABLED in configuration.")
        return

    print(f"📡 Worker IP: {librarian.remote_ip}")
    print(f"🧠 Model: {librarian.remote_model}")
    print("-" * 50)
    
    test_text = "How do I organize my creative film project files for the AI consciousness podcast?"
    
    print(f"📝 Test Input: \"{test_text}\"")
    print("⏳ Requesting remote embedding from 5090 worker...")
    
    try:
        embedding = librarian._generate_embedding(test_text)
        
        if embedding is not None and isinstance(embedding, np.ndarray):
            print(f"✅ EMBEDDING SUCCESSFUL!")
            print(f"📏 Dimensions: {embedding.shape}")
            print(f"🔢 Sample (First 5): {embedding[:5]}")
            print("-" * 50)
            print("🚀 Remote Powerhouse is OFFICIALLY working for Semantic Search!")
        else:
            print("❌ Embedding generation returned invalid result.")
            
    except Exception as e:
        print(f"❌ Error during embedding generation: {e}")

if __name__ == "__main__":
    verify_remote_embeddings()
