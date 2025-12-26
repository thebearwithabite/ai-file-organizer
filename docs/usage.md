# Usage Guide

## Interactive Organizer

The Interactive Organizer routes:
- 🖼️ Images to Gemini Vision Adapter
- 🎞️ Videos to the VEO system
- 📂 Automatically renames and organizes files
- 🧠 Feeds the learning system to improve over time

## Getting Started
1. Upload files via the UI or `/api/triage/upload`
2. Confirm categories using the organizer interface
3. Files are classified and relocated
4. Learning system records patterns and updates stats
5. **Direct Organization**: You can also organize files manually in Google Drive. The **Adaptive Background Monitor** watches these movements and treats them as "Verified Examples" to train the AI on your preferences automatically.

## Backend Systems
- **Gemini Vision Adapter**: Handles static images
- **VEO Prompt System**: Processes videos
- **Learning System**: Stores adaptive behavior and confidence
