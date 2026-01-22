# AI File Organizer - Complete Command Reference

This is your comprehensive reference for all Python commands in the AI File Organizer. Use this when you need to look up specific commands, arguments, and usage examples.

## Quick Reference Index

- [Core Organization](#core-organization) - Main file organization commands
- [Search & Discovery](#search--discovery) - Finding files and content
- [Computer Vision](#computer-vision) - Image and video analysis
- [Audio Analysis](#audio-analysis) - Audio processing and transcription
- [Tagging System](#tagging-system) - Comprehensive file tagging
- [Google Drive](#google-drive) - Cloud storage integration
- [Learning & Modes](#learning--modes) - System learning and interaction modes
- [Batch Processing](#batch-processing) - ADHD-friendly bulk operations
- [Creative Tools](#creative-tools) - Story and creative content tools
- [System Management](#system-management) - Status, monitoring, and maintenance
- [Troubleshooting](#troubleshooting) - Common issues and solutions

---

## Core Organization

### interactive_organizer.py - Main Organization Workflow

**Purpose**: Primary file organization with interactive questioning and 85% confidence threshold.

```bash
# Basic usage
python interactive_organizer.py organize --dry-run    # Preview mode (safe)
python interactive_organizer.py organize --live       # Actually move files

# Quick organize specific folder
python interactive_organizer.py quick /Users/user/Downloads --dry-run
python interactive_organizer.py quick /Users/user/Downloads --live

# Test single file
python interactive_organizer.py file "/path/to/document.pdf" --dry-run
python interactive_organizer.py file "/path/to/document.pdf" --live

# With custom base directory
python interactive_organizer.py --base-dir /Users/user/CustomBase organize --live
```

**Arguments**:
- `organize` - Process staging areas with interactive questions
- `quick <folder>` - Organize specific folder
- `file <path>` - Process single file
- `--live` - Actually perform operations (default is dry-run)
- `--dry-run` - Preview only, no actual file moves
- `--base-dir` - Custom base directory

**ADHD-Friendly Features**:
- Only asks questions when confidence < 85%
- Learns from your decisions
- Clear preview of what will happen
- Rollback capabilities

---

## Search & Discovery

### enhanced_librarian.py - Advanced Semantic Search

**Purpose**: Hybrid search combining keyword matching and semantic understanding.

```bash
# Search with different modes
python enhanced_librarian.py search "Client Name contracts" --mode semantic
python enhanced_librarian.py search "payment terms" --mode fast
python enhanced_librarian.py search "AI consciousness papers" --mode auto
python enhanced_librarian.py search "meeting schedules" --mode hybrid

# Advanced search options
python enhanced_librarian.py search "creative collaboration" --limit 20 --verbose
python enhanced_librarian.py search "stranger things" --mode semantic --limit 5

# System operations
python enhanced_librarian.py status           # Show system status
python enhanced_librarian.py index            # Build search index
python enhanced_librarian.py index --semantic # Build vector database
python enhanced_librarian.py organize --live  # Organize staging files
python enhanced_librarian.py suggest "AI"     # Get search suggestions
```

**Search Modes**:
- `semantic` - AI understanding of meaning and context
- `fast` - Quick keyword matching
- `auto` - Intelligently chooses best approach
- `hybrid` - Combines semantic and fast search

**Arguments**:
- `search <query>` - Search for files
- `--mode <mode>` - Search mode (semantic/fast/auto/hybrid)
- `--limit <n>` - Maximum results (default: 10)
- `--verbose` - Detailed output
- `status` - System status and statistics
- `index` - Build search indexes
- `organize` - File organization
- `suggest <query>` - Get search suggestions

### vector_librarian.py - Vector Database Operations

**Purpose**: Build and manage the ChromaDB vector database for semantic search.

```bash
# Build vector database (includes emails and documents)
python vector_librarian.py

# Custom operations (no CLI interface - run as module)
# This script primarily operates as a backend component
```

---

## Computer Vision

### vision_cli.py - Image and Video Analysis (Gemini 2.5 Flash)

**Purpose**: Analyze images and videos for intelligent content understanding and organization.

```bash
# Analyze single files
python vision_cli.py analyze screenshot.png
python vision_cli.py analyze document_photo.jpg
python vision_cli.py analyze video.mp4 --context entertainment

# Directory analysis
python vision_cli.py directory ~/Downloads
python vision_cli.py directory ~/Pictures --limit 10
python vision_cli.py directory ~/Videos --context creative

# System operations
python vision_cli.py test                    # Test with sample files
python vision_cli.py setup                  # Show API key setup
```

**Context Options**:
- `general` - Standard image/video analysis
- `entertainment` - Entertainment industry focus (Client Name Wolfhard, projects)
- `creative` - Creative projects (Papers That Dream, AI content)

**Arguments**:
- `analyze <file>` - Analyze single image/video
- `directory <path>` - Analyze all images/videos in directory
- `--context <type>` - Analysis context (general/entertainment/creative)
- `--limit <n>` - Maximum files to process
- `test` - Test system with samples
- `setup` - Show setup instructions

**Setup Required**:
```bash
export GEMINI_API_KEY='your-api-key-here'
pip install google-generativeai
```

### video_project_trainer.py - Project Recognition Learning

**Purpose**: Learns to automatically classify video generations into correct projects.

```bash
# Analyze videos and learn patterns
python video_project_trainer.py analyze ~/Videos
python video_project_trainer.py analyze ~/Downloads --pattern "*.mp4"

# Train on specific projects
python video_project_trainer.py train --project "thebearwithabite"
python video_project_trainer.py train --project "Papers That Dream"

# View learned patterns and statistics
python video_project_trainer.py patterns
python video_project_trainer.py stats
```

---

## Audio Analysis

### audio_cli.py - Professional Audio Analysis

**Purpose**: Analyze audio files for content type, quality, and transcription.

```bash
# Analyze single audio file
python audio_cli.py analyze interview.mp3
python audio_cli.py analyze scene_audio.wav --transcribe --details
python audio_cli.py analyze podcast_episode.m4a --transcribe

# Directory analysis
python audio_cli.py directory /Users/user/Audio
python audio_cli.py directory /Users/user/Downloads --transcribe
python audio_cli.py directory ~/Podcasts --details

# Search analyzed audio
python audio_cli.py search "consciousness"
python audio_cli.py search "interview" --type interview
python audio_cli.py search "music" --type music

# System statistics
python audio_cli.py stats
```

**Audio Analysis Features**:
- Content type detection (interview, music, voice sample, scene audio)
- Technical analysis (quality, noise levels, dynamic range)
- Speech processing (voice activity, speaker estimation)
- Music analysis (tempo, key, energy, danceability)
- Automatic transcription

**Arguments**:
- `analyze <file>` - Analyze single audio file
- `directory <path>` - Analyze directory of audio files
- `search <query>` - Search analyzed audio content
- `--transcribe` - Include speech-to-text transcription
- `--details` - Detailed technical analysis
- `--type <type>` - Filter by content type
- `stats` - Show analysis statistics

---

## Tagging System

### tagging_cli.py - Comprehensive Auto-Tagging

**Purpose**: Multi-source automatic tagging system with confidence scores.

```bash
# Tag single file
python tagging_cli.py tag document.pdf
python tagging_cli.py tag script.docx --user-tags "draft,client-work,important"
python tagging_cli.py tag contract.pdf --confidence-threshold 0.8

# Tag directory
python tagging_cli.py directory /Users/user/Downloads
python tagging_cli.py directory /Users/user/Documents --pattern "*.pdf"
python tagging_cli.py directory ~/Projects --recursive

# Search by tags
python tagging_cli.py search "project:,netflix"
python tagging_cli.py search "contract,client" --match-all
python tagging_cli.py search "creative,consciousness,AI" --match-any

# View file information
python tagging_cli.py show document.pdf        # Show all tags for file
python tagging_cli.py suggest new_file.docx   # Get tag suggestions
python tagging_cli.py stats                   # System statistics

# Advanced operations
python tagging_cli.py verify ~/Documents      # Verify tag accuracy
python tagging_cli.py cleanup                 # Remove orphaned tags
```

**Tag Categories**:
- **People**: finn, client_name, ryan, etc.
- **Projects**: stranger_things, creative_project, papers_that_dream
- **Document Types**: contract, script, invoice, email
- **Content**: creative, consciousness, business, entertainment
- **Status**: active, draft, completed, archived
- **Industry**: entertainment, creative, business, technical

**Arguments**:
- `tag <file>` - Tag single file
- `directory <path>` - Tag all files in directory
- `search <tags>` - Search by tags
- `show <file>` - Show file's tags
- `suggest <file>` - Get tag suggestions
- `stats` - Tagging statistics
- `--user-tags <tags>` - Add custom tags
- `--pattern <pattern>` - File pattern filter
- `--match-all` - All tags must match
- `--match-any` - Any tag can match
- `--confidence-threshold <float>` - Minimum confidence

---

## Google Drive

### gdrive_cli.py - Cloud Storage Integration

**Purpose**: 2TB Google Drive integration with intelligent organization and emergency space recovery.

```bash
# First-time setup
python gdrive_cli.py auth --credentials gdrive_credentials.json

# Emergency space recovery
python gdrive_cli.py emergency                 # Preview what would be uploaded
python gdrive_cli.py emergency --live          # Actually free up space

# File organization
python gdrive_cli.py organize                  # Preview organization
python gdrive_cli.py organize --live           # Upload and organize
python gdrive_cli.py organize --file contract.pdf --folder "Legal Documents"

# Search and status
python gdrive_cli.py search --query "contract"
python gdrive_cli.py search --query "finn" --folder "Entertainment_Industry"
python gdrive_cli.py status                    # Storage status
python gdrive_cli.py folders                  # List folder structure

# Advanced operations
python gdrive_cli.py sync                      # Sync local changes
python gdrive_cli.py backup ~/Documents       # Backup specific folder
```

**46-Folder Structure**: Includes organized folders for entertainment industry, creative projects, business operations, and more.

**Arguments**:
- `auth` - Authenticate with Google Drive
- `emergency` - Emergency space recovery
- `organize` - Organize and upload files
- `search` - Search cloud files
- `status` - Storage and system status
- `folders` - List drive folders
- `--credentials <file>` - OAuth credentials file
- `--live` - Actually perform operations
- `--file <path>` - Specific file to upload
- `--folder <name>` - Target folder
- `--query <text>` - Search query

---

## Learning & Modes

### quick_learning_mode.py - Easy Mode Switching

**Purpose**: Quick switching between interaction modes for different use cases.

```bash
# Mode switching
python quick_learning_mode.py --learning      # Activate learning mode (85% threshold)
python quick_learning_mode.py --smart         # Switch to smart mode (75% threshold)
python quick_learning_mode.py --status        # Check current mode

# Alternative: Use demo interface
python demo_interaction_modes.py             # Interactive mode selection
```

**Interaction Modes**:
- **LEARNING** (85%): Aggressive learning mode for rapid training
- **SMART** (75%): Default balanced mode
- **MINIMAL** (40%): Only very uncertain files
- **ALWAYS** (100%): Ask about every file
- **NEVER** (0%): Fully automatic

### learning_cli.py - Learning System Management

**Purpose**: View and manage the learning system's progress and statistics.

```bash
# View learning statistics
python learning_cli.py stats

# Learning operations
python learning_cli.py analyze               # Analyze learning patterns
python learning_cli.py export               # Export learning data
python learning_cli.py reset                # Reset learning (careful!)
```

---

## Batch Processing

### batch_cli.py - ADHD-Friendly Bulk Operations

**Purpose**: Process large numbers of files in manageable chunks to prevent cognitive overload.

```bash
# Directory processing
python batch_cli.py directory ~/Downloads --dry-run
python batch_cli.py directory ~/Downloads --live --batch-size 20
python batch_cli.py directory ~/Archives --dry-run --batch-size 10

# File list processing
python batch_cli.py filelist file_list.txt --dry-run
python batch_cli.py filelist important_files.txt --live

# Job management
python batch_cli.py jobs                     # List batch jobs
python batch_cli.py help                     # Detailed help

# Advanced options
python batch_cli.py directory ~/Documents --live --backup-enabled --verbose
```

**ADHD Features**:
- Processes files in small, manageable chunks
- Clear progress indicators
- Backup and rollback capabilities
- Pause and resume functionality

**Arguments**:
- `directory <path>` - Process directory
- `filelist <file>` - Process files from list
- `jobs` - Show batch job status
- `help` - Detailed help
- `--batch-size <n>` - Files per batch (default: 20)
- `--backup-enabled` - Enable automatic backups
- `--verbose` - Detailed output

---

## Creative Tools

### creative_cli.py - Creative Content Analysis

**Purpose**: Advanced analysis of creative content, characters, and story elements.

```bash
# Analyze creative content
python creative_cli.py analyze script.pdf --details
python creative_cli.py analyze story.docx --characters --themes
python creative_cli.py analyze ~/Creative --recursive

# Character analysis
python creative_cli.py character "protagonist name"
python creative_cli.py character "Client Name Wolfhard" --projects

# Theme and story analysis
python creative_cli.py themes ~/Scripts
python creative_cli.py connections "main character" --depth 3
```

### universe_cli.py - Story Universe Management

**Purpose**: Create and manage knowledge graphs of story universes and character connections.

```bash
# Build story universe
python universe_cli.py build
python universe_cli.py build --source ~/Scripts --update

# Explore connections
python universe_cli.py overview --detailed
python universe_cli.py connections "character name" --depth 3
python universe_cli.py themes --visual

# Creative suggestions
python universe_cli.py suggest --focus "character development"
python universe_cli.py suggest --theme "consciousness"
python universe_cli.py suggest --project "new screenplay"

# Export and sharing
python universe_cli.py export --format json
python universe_cli.py export --format html --visual
```

---

## System Management

### metadata_cli.py - Metadata Management

**Purpose**: Generate and manage comprehensive file metadata.

```bash
# Analyze and generate metadata
python metadata_cli.py analyze ~/Documents
python metadata_cli.py analyze ~/Projects --pattern "*.pdf" --deep

# Generate reports
python metadata_cli.py report
python metadata_cli.py report --format html --output metadata_report.html

# Maintenance operations
python metadata_cli.py verify ~/Documents   # Verify metadata accuracy
python metadata_cli.py cleanup              # Remove orphaned metadata
python metadata_cli.py rebuild              # Rebuild metadata database
```

### categories_cli.py - Custom Categories

**Purpose**: Create and manage custom file classification categories.

```bash
# Category management
python categories_cli.py list                # List all categories
python categories_cli.py add "Legal Documents" --keywords "contract,agreement,legal"
python categories_cli.py train "Legal Documents" --examples ~/Legal/

# Category operations
python categories_cli.py test ~/Downloads    # Test category classification
python categories_cli.py stats              # Category statistics
python categories_cli.py export categories.json
```

### mover_cli.py - Safe File Operations

**Purpose**: Safe file moving operations with backup and rollback capabilities.

```bash
# Safe file operations
python mover_cli.py move ~/Downloads/*.pdf --dest ~/Documents --backup
python mover_cli.py move large_files.txt --dest ~/Archive --backup-enabled

# Rollback operations
python mover_cli.py rollback --backup rollback_backup_20250831_142315.csv
python mover_cli.py list-backups
```

### multimedia_cli.py - Multimedia Processing

**Purpose**: Comprehensive multimedia file analysis and processing.

```bash
# Process multimedia content
python multimedia_cli.py process ~/Creative --auto-tag
python multimedia_cli.py process ~/Downloads --analyze --transcribe

# Multimedia analysis
python multimedia_cli.py analyze video.mp4 --extract-audio --transcribe
python multimedia_cli.py stats ~/Media
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "Permission denied" errors
```bash
# Fix file permissions
chmod +x *.py
python3 interactive_organizer.py organize --dry-run
```

#### 2. "Module not found" errors
```bash
# Ensure you're in the project directory
cd /path/to/ai-file-organizer
source .venv/bin/activate
pip install -r requirements.txt
```

#### 3. Google Drive authentication issues
```bash
# Re-authenticate
python gdrive_cli.py auth --credentials gdrive_credentials.json
# Check credentials file exists and has correct permissions
```

#### 4. Vision API setup
```bash
# Set up Gemini API key
export GEMINI_API_KEY='your-api-key-here'
pip install google-generativeai
python vision_cli.py setup  # Verify setup
```

#### 5. Audio processing errors
```bash
# Install audio dependencies
pip install librosa soundfile
# For macOS: brew install ffmpeg
```

#### 6. Vector database issues
```bash
# Rebuild vector database
python enhanced_librarian.py index --semantic
python vector_librarian.py
```

### Debug Mode

Most commands support verbose/debug output:
```bash
python interactive_organizer.py organize --dry-run --verbose
python enhanced_librarian.py search "query" --mode semantic --verbose
python tagging_cli.py directory ~/Downloads --verbose
```

### System Status Commands

Check system health and status:
```bash
python enhanced_librarian.py status
python gdrive_cli.py status  
python audio_cli.py stats
python tagging_cli.py stats
python learning_cli.py stats
```

---

## Usage Patterns for Different Workflows

### Daily ADHD-Friendly Workflow
```bash
# 1. Quick learning mode for new content
python quick_learning_mode.py --learning

# 2. Organize Downloads folder
python interactive_organizer.py quick ~/Downloads --dry-run
python interactive_organizer.py quick ~/Downloads --live

# 3. Switch back to smart mode
python quick_learning_mode.py --smart

# 4. Search for what you need
python enhanced_librarian.py search "today's meetings" --mode auto
```

### Entertainment Industry Workflow
```bash
# 1. Analyze new contract
python vision_cli.py analyze contract_scan.pdf --context entertainment

# 2. Tag for easy finding
python tagging_cli.py tag contract.pdf --user-tags "finn,active,2025"

# 3. Organize to correct location
python interactive_organizer.py file contract.pdf --live

# 4. Upload to Google Drive
python gdrive_cli.py organize --file contract.pdf --folder "01_ENTERTAINMENT_MANAGEMENT"
```

### Creative Project Workflow  
```bash
# 1. Analyze creative content
python creative_cli.py analyze new_script.pdf --details

# 2. Build story universe
python universe_cli.py build --source ~/Scripts --update

# 3. Get creative suggestions
python universe_cli.py suggest --focus "character development"

# 4. Organize and tag
python tagging_cli.py tag new_script.pdf --user-tags "creative,draft,papers-that-dream"
```

### Bulk Processing Workflow
```bash
# 1. Emergency space recovery
python gdrive_cli.py emergency --live

# 2. Batch process large folder
python batch_cli.py directory ~/Archives --live --batch-size 15

# 3. Comprehensive tagging
python tagging_cli.py directory ~/Documents --recursive

# 4. Build search indexes
python enhanced_librarian.py index --semantic
```

---

This command reference covers all major functionality in the AI File Organizer. Use the Quick Reference Index at the top to jump to specific sections, and remember that most commands support `--help` for additional details.

**Always start with `--dry-run` when learning a new command!**