import sqlite3
import os

db_path = "/Users/ryanthomson/Documents/AI_METADATA_SYSTEM/background_monitor.db"
gdrive_path = os.path.expanduser("~/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive/test_gdrive_sync.txt")

try:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT * FROM processed_files WHERE file_path = ?", (gdrive_path,))
        row = cursor.fetchone()
        if row:
            print(f"File found in DB: {row}")
        else:
            print("File NOT found in DB")
            
        # List all processed files from GDrive
        print("\nAll processed GDrive files:")
        cursor = conn.execute("SELECT file_path FROM processed_files WHERE file_path LIKE '%GoogleDrive%'")
        for r in cursor.fetchall():
            print(r[0])
            
except Exception as e:
    print(f"Error: {e}")
