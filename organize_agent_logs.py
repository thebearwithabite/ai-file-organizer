
import os
import json
import glob
import shutil
from datetime import datetime

# Configuration
SOURCE_GEMINI_TMP = os.path.expanduser("~/.gemini/tmp")
SOURCE_BRAIN = os.path.expanduser("~/.gemini/antigravity/brain")
DEST_DIR = "Antigravity-Agent-Logs"

def setup_directories():
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        print(f"Created directory: {DEST_DIR}")

def process_session_logs():
    print("Scanning for session logs...")
    session_files = []
    for root, dirs, files in os.walk(SOURCE_GEMINI_TMP):
        for file in files:
            if file.startswith("session-") and file.endswith(".json"):
                session_files.append(os.path.join(root, file))
    
    print(f"Found {len(session_files)} session files.")
    
    for file_path in session_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract metadata for filename
            session_id = data.get("sessionId", "unknown_session")
            timestamp = data.get("startTime", datetime.now().isoformat()).replace(":", "-").replace(".", "-")
            
            # Create a descriptive filename
            filename = f"session_{timestamp}_{session_id}.json"
            dest_path = os.path.join(DEST_DIR, filename)
            
            # Write structured data
            output_data = {
                "source_file": file_path,
                "type": "session_log",
                "content": data
            }
            
            with open(dest_path, 'w') as f:
                json.dump(output_data, f, indent=2)
                
            print(f"Processed session log: {filename}")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

def process_brain_items():
    print("Scanning for brain items...")
    # Find all conversation folders in SOURCE_BRAIN
    if not os.path.exists(SOURCE_BRAIN):
        print(f"Brain directory not found: {SOURCE_BRAIN}")
        return

    # Iterate over directories in brain
    for item in os.listdir(SOURCE_BRAIN):
        item_path = os.path.join(SOURCE_BRAIN, item)
        if os.path.isdir(item_path):
            conversation_id = item
            
            # Process generic files in the conversation folder (task.md, metadata, etc.)
            for filename in os.listdir(item_path):
                file_path = os.path.join(item_path, filename)
                
                if os.path.isfile(file_path):
                    try:
                        content = ""
                        is_json = False
                        
                        # Try to read as JSON first
                        try:
                            with open(file_path, 'r') as f:
                                content = json.load(f)
                            is_json = True
                        except json.JSONDecodeError:
                            # Fallback to text reading
                            with open(file_path, 'r') as f:
                                content = f.read()
                        
                        # Create descriptive filename
                        safe_filename = filename.replace(".", "_")
                        dest_filename = f"brain_{conversation_id}_{safe_filename}.json"
                        dest_path = os.path.join(DEST_DIR, dest_filename)
                        
                        output_data = {
                            "source_file": file_path,
                            "type": "brain_item",
                            "brain_context_id": conversation_id,
                            "original_filename": filename,
                            "content": content
                        }
                        
                        with open(dest_path, 'w') as f:
                            json.dump(output_data, f, indent=2)
                            
                        print(f"Processed brain item: {dest_filename}")
                        
                    except Exception as e:
                        print(f"Error processing brain item {file_path}: {e}")

def main():
    setup_directories()
    process_session_logs()
    process_brain_items()
    print("Organization complete.")

if __name__ == "__main__":
    main()
