import sys
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.append(str(Path(__file__).parent.absolute()))

def check_learning_system():
    print("Checking Learning System...")
    try:
        from universal_adaptive_learning import UniversalAdaptiveLearning
        ual = UniversalAdaptiveLearning()
        stats = ual.get_learning_statistics()
        print(f"Total Learning Events: {stats.get('total_events', 0)}")
        print("Learning System OK.\\n")
    except Exception as e:
        print(f"Learning System check failed: {e}\\n")

def check_deduplication():
    print("Checking Deduplication Service...")
    try:
        from bulletproof_deduplication import BulletproofDeduplicator
        from gdrive_integration import get_ai_organizer_root
        
        root = get_ai_organizer_root()
        dedup = BulletproofDeduplicator(str(root))
        
        # Test directory (Downloads)
        test_dir = Path.home() / "Downloads"
        
        print(f"Running dry-run deduplication scan on {test_dir}...")
        results = dedup.scan_directory(test_dir, execute=False)
        print(f"Found {results.get('duplicate_groups', 0)} duplicate groups.")
        print(f"Files scanned: {results.get('metrics', {}).get('files_scanned', 0)}")
        print("Deduplication System OK.\\n")
    except Exception as e:
        print(f"Deduplication System check failed: {e}\\n")

def main():
    print(f"--- Phase 3 Verification ({datetime.now()}) ---")
    check_learning_system()
    check_deduplication()
    print("--- Background Monitor ---")
    print("Background monitor requires server start (main.py) to check via UI at http://localhost:8000/api/system/monitor-status.")

if __name__ == '__main__':
    main()
