# Legacy Command Line Interface

This document contains comprehensive command-line documentation for power users who prefer CLI tools over the web interface.

> **Note:** The modern web interface at `http://localhost:8000` is the recommended way to use AI File Organizer v3.0. These commands remain available for automation and advanced use cases.

## Advanced Setup

### Google Drive Integration (Optional)

To enable Google Drive hybrid storage:

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create/Select Project**: Create new project or select existing
3. **Enable Google Drive API**:
   - Go to "APIs & Services" > "Library" 
   - Search "Google Drive API" and enable it
4. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Choose "Desktop Application"
   - Download the JSON file
5. **Save Credentials**: Save as `gdrive_credentials.json` in project root

### Cloud Dependencies

```bash
# Install cloud storage dependencies (optional)
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Complete Command Reference

### Search & Discovery Commands

```bash
# Semantic search with hybrid cloud support
python enhanced_librarian.py search "client contract terms" --mode semantic
python enhanced_librarian.py search "consciousness podcast episodes" --mode hybrid

# System status and health checks
python gdrive_integration.py
python test_hybrid_architecture.py --quick
```

### Organization & Processing Commands

```bash
# Interactive file organization
python interactive_organizer.py organize --live     # Full organization
python interactive_organizer.py quick ~/Downloads --live  # Specific folder

# Rollback system safety net
python easy_rollback_system.py --today    # Check recent operations
python easy_rollback_system.py --list     # Show all operations
python easy_rollback_system.py --undo-today    # Emergency undo
```

### Computer Vision & Media Analysis

```bash
# AI-powered image and video analysis
python vision_cli.py analyze screenshot.png --context professional
python video_project_trainer.py analyze ~/Videos --project "creative-content"
python audio_cli.py analyze podcast_episode.mp3 --transcribe
```

### Google Drive Hybrid Management

```bash
# Cloud storage integration
python gdrive_integration.py
python test_hybrid_architecture.py --quick
python enhanced_librarian.py search "professional contract" --mode hybrid
```

### Tagging & Metadata Commands

```bash
# Automatic tagging and metadata extraction
python tagging_cli.py directory ~/Documents --auto-tag
python metadata_cli.py analyze ~/Documents
python metadata_cli.py search "entertainment" --detailed
```

### Background Services

```bash
# Proactive system monitoring
python background_monitor.py start    # Monitors all file changes 24/7
python staging_monitor.py             # Processes files after 7-day ADHD window
python gdrive_cli.py emergency --auto # Auto space recovery when storage < 5GB
```

### File Management Commands

```bash
# Interactive classification modes
python quick_learning_mode.py --learning   # Aggressive learning (85% confidence)
python quick_learning_mode.py --smart      # Balanced operation (75% confidence)  
python quick_learning_mode.py --minimal    # Minimal questions (40% confidence)
python quick_learning_mode.py --status     # Check current mode
```

### Debugging & Troubleshooting

```bash
# System diagnostics
python test_hybrid_architecture.py --auth-only  # Test Google Drive auth
python test_indexing.py                         # Test search indexing
python test_integration.py                      # Full system test

# Debug specific files
python test_single_file.py /path/to/file.pdf   # Test single file processing
python show_questions.py                       # Show classification questions
```

## Legacy Architecture Information

### V2 System Components (Archived)

The v2 system used these components, now consolidated into the v3 web interface:

- **Desktop/Downloads monitor** (AppleScript) → Now: Web-based Triage Center
- **Classification engine** (Python) → Now: Unified API backend  
- **7-day staging workflow** → Now: Confidence-based review system
- **Separate CLI tools** → Now: Unified web interface + API

### File Processing Pipeline

```python
# Legacy processing flow (now handled automatically by web interface)
1. File Detection → Background monitoring
2. Content Extraction → Automatic analysis  
3. Classification → AI categorization with confidence scores
4. User Interaction → Web-based triage center
5. Organization → Automatic filing or manual review
```

## Migration from V2 to V3

If upgrading from v2:

1. **Install v3 dependencies**: `pip install -r requirements_v3.txt`
2. **Start web server**: `python main.py`
3. **Open browser**: Navigate to `http://localhost:8000`
4. **Import existing data**: The v3 system will detect and use existing indices

The web interface provides all functionality previously available through separate CLI tools, with improved usability and ADHD-friendly design.