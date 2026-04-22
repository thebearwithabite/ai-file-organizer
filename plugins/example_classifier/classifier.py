"""Example classifier implementation."""

from pathlib import Path
from typing import Dict, Any


def classify(file_path: Path) -> Dict[str, Any]:
    """
    Classify a file based on its extension.
    
    This is a simple example - real classifiers would use
    content analysis, ML models, etc.
    
    Args:
        file_path: Path to the file to classify
        
    Returns:
        Classification result with category, confidence, reasoning
    """
    ext = file_path.suffix.lower()
    
    # Simple extension-based classification
    categories = {
        ".pdf": ("documents", 0.8, "PDF files are typically documents"),
        ".doc": ("documents", 0.8, "Word documents"),
        ".docx": ("documents", 0.8, "Word documents"),
        ".jpg": ("images", 0.9, "JPEG image file"),
        ".png": ("images", 0.9, "PNG image file"),
        ".mp3": ("audio", 0.9, "MP3 audio file"),
        ".mp4": ("video", 0.9, "MP4 video file"),
    }
    
    if ext in categories:
        cat, conf, reason = categories[ext]
        return {
            "category": cat,
            "confidence": conf,
            "reasoning": reason
        }
    
    return {
        "category": "unknown",
        "confidence": 0.1,
        "reasoning": f"Unknown file extension: {ext}"
    }
