
import sys
from pathlib import Path
sys.path.append('/Users/ryanthomson/Github/ai-file-organizer')
from bulletproof_deduplication import BulletproofDeduplicator

def run_dedupe():
    deduper = BulletproofDeduplicator()
    
    # Define paths
    gdrive_path = Path('/Users/ryanthomson/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com')
    local_paths = [
        Path('/Users/ryanthomson/Downloads'),
        Path('/Users/ryanthomson/Desktop'),
        Path('/Users/ryanthomson/Documents')
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
