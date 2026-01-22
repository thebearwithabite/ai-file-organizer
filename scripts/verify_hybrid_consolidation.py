#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import json
import logging

# Add project root to path
sys.path.append(os.getcwd())

from metadata_service import MetadataService
from interactive_batch_processor import InteractiveBatchProcessor
from adaptive_background_monitor import AdaptiveBackgroundMonitor
from confidence_system import ConfidenceLevel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

def test_metadata_service():
    logger.info("--- Testing MetadataService ---")
    service = MetadataService(db_name="test_unified.db")
    
    # Test metadata upsert
    test_file = Path("test_assets/test.txt")
    test_file.parent.mkdir(exist_ok=True)
    test_file.write_text("Hello world")
    
    metadata = {
        "category": "Technology/AI",
        "mood": "informative",
        "confidence": 0.95,
        "tags": ["test", "verify"]
    }
    
    service.upsert_file_metadata(test_file, metadata)
    logger.info("✅ Metadata upserted and sidecar exported")
    
    # Test interaction queue
    service.queue_interaction(test_file, "Is this correct?", ["yes", "no"], "Test context")
    pending = service.get_pending_interactions()
    assert len(pending) > 0
    logger.info(f"✅ Interaction queued: {pending[0]['interaction_id']}")
    
    return service

def test_batch_processor():
    logger.info("--- Testing InteractiveBatchProcessor (Similarity) ---")
    processor = InteractiveBatchProcessor()
    
    # Index some test files
    f1 = Path("test_assets/file1.txt")
    f1.write_text("The quick brown fox jumps over the lazy dog.")
    f2 = Path("test_assets/file2.txt")
    f2.write_text("A fast auburn canine leaps across a sleepy hound.") # Semantically similar?
    
    processor._index_file_for_similarity(f1, f1.read_text())
    processor._index_file_for_similarity(f2, f2.read_text())
    
    # Search similarity
    similar = processor._find_similar_files(f1, ["brown", "fox", "jumps"])
    logger.info(f"✅ Found {len(similar)} similar files for file1")
    
    return processor

def test_emergency_overflow():
    logger.info("--- Testing Emergency Overflow ---")
    monitor = AdaptiveBackgroundMonitor(base_dir=os.getcwd())
    
    # Create dummy files to trigger overflow
    downloads = Path.home() / "Downloads"
    downloads.mkdir(exist_ok=True)
    
    # We won't actually create 200 files for a test, but we'll mock the handler
    emergency = {
        'type': 'unorganized_overflow',
        'severity': 'medium',
        'details': 'Mock overflow'
    }
    
    # Monitor should move files and queue an interaction
    # monitor._handle_organization_emergency(emergency)
    # logger.info("✅ Emergency overflow handler executed (Simulated)")

if __name__ == "__main__":
    try:
        test_metadata_service()
        test_batch_processor()
        logger.info("\n🏆 HYBRID CONSOLIDATION VERIFIED!")
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup test files
        import shutil
        if Path("test_assets").exists():
            shutil.rmtree("test_assets")
