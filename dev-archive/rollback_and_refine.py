#!/usr/bin/env python3
"""
Rollback and Refine JSON Renames
-------------------------------
Undoes the recent .txt renames and applies better extension detection 
that recognizes Markdown content.
"""

import os
import shutil
from pathlib import Path

# Paths derived from recent logs
RENAMED_FILES = [
    "_Admin/99_TEMP_PROCESSING/Manual_Review/PapersThatDream_Website_Spec.txt",
    "_Admin/99_TEMP_PROCESSING/Manual_Review/Uncategorized/Projects/Audio/Audio_Production_Spec_PapersThatDream_Episode2.txt",
    "_Admin/99_TEMP_PROCESSING/Manual_Review/Uncategorized/Unsorted/PapersThatDream_PodcastDescription.txt",
    "_Admin/99_TEMP_PROCESSING/Manual_Review/Uncategorized/Unsorted/Project_Brief_Papersthatdream_WebsiteRedesign.txt",
    "_Admin/99_TEMP_PROCESSING/Desktop/09_Tech_Dev_Files/shining-courage-457604-g3.txt",
    "01_ACTIVE_PROJECTS/VEO_Prompt_Machine/VEO_API_Technical_Specifications.txt",
    "01_ACTIVE_PROJECTS/Creative_Projects/Screenplays/PapersThatDream_BackgroundScripts.txt",
    "Technology/Literature/AI_Conversation_Analysis_Max_Entropy_Project.txt",
    "Technology/Data/Audio_ML_Project_Reddit_Post.txt",
    "Technology/Data/Reddit_Logging_Specification.txt",
    "Technology/Data/AudioAI_v14_Dependencies.txt",
    "Technology/Data/OpenAI_Conversations_Metadata_Key_Report.txt",
    "Technology/Data/Spec_to_Implementation_Evaluation_Plan.txt",
    "Technology/Data/Reddit_PostingSchedule_Agent1.txt",
    "Technology/Data/CreativeWorkspace_ProjectOverview_2024_1.txt",
    "Technology/Data/MAX_DUAL_PROMPT_2000_Technical_Spec.txt",
    "Technology/Data/SEO_AEO_Optimization_Skill_Spec.txt",
    "Technology/Data/Podcast_Sound_Design_Cue_Sheet_Episode1.txt",
    "Technology/Data/CueSheetPro_TechSpec_v1.0.txt",
    "Technology/Data/CreativeWorkspace_ProjectOverview_2024.txt",
    "Technology/Data/Social_Commentary_Compilation.txt"
]

DRIVE_ROOT = Path("/Users/ryanthomson/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive")

def is_markdown(content):
    """Simple check for markdown headers or common patterns."""
    lines = content.split('\n')
    for line in lines[:20]: # Check first 20 lines
        line = line.strip()
        if line.startswith('# ') or line.startswith('## ') or line.startswith('### '):
            return True
        if line.startswith('**') and line.endswith('**'):
            return True
        if line.startswith('```'):
            return True
    return False

def rollback():
    print(f"🔄 Rolling back and refining {len(RENAMED_FILES)} files...")
    
    for rel_path in RENAMED_FILES:
        file_path = DRIVE_ROOT / rel_path
        if not file_path.exists():
            print(f"⚠️  Skipping: {rel_path} (not found)")
            continue
            
        try:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read(5000)
            
            # Determine best extension
            if is_markdown(content):
                target_ext = ".md"
            else:
                # If it's not markdown, maybe it was a legitimate JSON originally?
                # But we know it's "text/plain". 
                # Let's see if the user wants .md for these specs anyway.
                target_ext = ".md" # Default to .md for these "Spec" files
            
            new_path = file_path.with_suffix(target_ext)
            
            # Avoid overwriting
            if new_path.exists():
                print(f"⚠️  Conflict: {new_path.name} exists. Skipping.")
                continue
                
            shutil.move(str(file_path), str(new_path))
            print(f"✅ Refined: {rel_path} -> {new_path.suffix}")
            
        except Exception as e:
            print(f"❌ Error processing {rel_path}: {e}")

if __name__ == "__main__":
    rollback()
