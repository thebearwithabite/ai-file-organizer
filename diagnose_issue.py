
import sys
from pathlib import Path

# Add project root to path
project_root = Path("/Users/ryanthomson/Github/ai-file-organizer")
sys.path.insert(0, str(project_root))

from gdrive_integration import get_ai_organizer_root, get_metadata_root
from api.services import SystemService, TriageService

print(f"AI Organizer Root: {get_ai_organizer_root()}")
print(f"Metadata Root: {get_metadata_root()}")

print("\n--- SystemService Inspection ---")
service = SystemService()
librarian = service.get_librarian()
if librarian:
    print(f"Librarian Config Dir: {librarian.config_dir}")
    print(f"Librarian Authenticated: {librarian._authenticated}")
    print(f"Librarian DB Path: {librarian.metadata_store.db_path}")
else:
    print("Librarian not initialized!")

print("\n--- TriageService Inspection ---")
triage = TriageService()
print(f"Base Dir: {triage.base_dir}")
print("Staging Areas:")
for area in triage.staging_areas:
    print(f"  - {area}")

print("\n--- Database Check ---")
import sqlite3
db_paths = [
    get_metadata_root() / "databases" / "metadata.db",
    get_metadata_root() / "databases" / "rollback.db",
    Path.home() / ".ai_organizer_config" / "file_metadata.db",
    Path.home() / ".ai_organizer_config" / "rollback.db"
]

for path in db_paths:
    if path.exists():
        print(f"DB EXISTS: {path}")
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"  Tables: {tables}")
            conn.close()
        except Exception as e:
            print(f"  ERROR CONNECTING: {e}")
    else:
        print(f"DB MISSING: {path}")
