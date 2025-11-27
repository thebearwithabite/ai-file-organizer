from pathlib import Path
import os

gdrive_path = Path(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com"))
print(f"Scanning: {gdrive_path}")

count = 0
target = "test_scan_v2.txt"
found_target = False

for f in gdrive_path.rglob("*.txt"):
    if f.name == target:
        print(f"FOUND TARGET: {f}")
        found_target = True
    count += 1
    
print(f"Total .txt files: {count}")
if not found_target:
    print(f"TARGET {target} NOT FOUND!")
