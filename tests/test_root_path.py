
from gdrive_integration import get_ai_organizer_root
from pathlib import Path

root = get_ai_organizer_root()
print(f"AI Organizer Root: {root}")

expected = Path("/Users/ryanthomson/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive")
if root == expected:
    print("SUCCESS: Root matches Google Drive path.")
else:
    print("FAIL: Root does not match Google Drive path.")
