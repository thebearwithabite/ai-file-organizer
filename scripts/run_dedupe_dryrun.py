
import sys
from pathlib import Path
sys.path.append('/Users/user/Github/ai-file-organizer')
from bulletproof_deduplication import BulletproofDeduplicator

def run_dedupe():
    deduper = BulletproofDeduplicator()
    
    # Define paths
    gdrive_path = Path('/Users/user/Library/CloudStorage/user@example.com')
    local_paths = [
        Path('/Users/user/Downloads'),
        Path('/Users/user/Desktop'),
        Path('/Users/user/Documents')
    ]
    
    # Run dry run
    print("Running Deduplication Dry Run...")
    deduper.clean_local_duplicates_of_gdrive(
        gdrive_dirs=[gdrive_path],
        local_dirs=local_paths,
        execute=False  # Dry run first
    )

if __name__ == "__main__":
    run_dedupe()
