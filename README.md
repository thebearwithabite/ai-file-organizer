# AI File Organizer - Local LLM Librarian

## Overview
An intelligent file organization and search system that uses natural language processing to automatically organize your MacBook files while respecting your workflow patterns.

## 🎯 Core Philosophy: Natural Transition Design
**Key Insight:** Let files sit in Desktop/Downloads for 7 days while actively using them. This allows natural workflow adaptation rather than forcing immediate perfection of folder knowledge.

### 7-Day Staging Approach
- **Days 1-7:** Files remain in Desktop/Downloads for active access
- **Day 7:** Gentle suggestion to organize (non-intrusive)
- **Gradual learning:** Users naturally become experts in folder structure
- **ADHD-friendly:** Works with natural patterns, not against them

## Core Components

### `librarian.py`
Main CLI interface providing:
- Natural language file search
- System status and statistics
- File organization commands
- Content indexing

### `staging_monitor.py`
7-day staging system that:
- Monitors Desktop/Downloads folders
- Tracks file age and usage patterns
- Provides gentle organization suggestions
- Learns from user behavior

### `content_extractor.py`
Content processing engine:
- Extracts text from various file formats
- Builds searchable content index
- Supports PDF, DOCX, TXT, MD, and more

### `classification_engine.py`
AI-powered file classification:
- Categorizes files based on content and metadata
- Provides organization recommendations
- Learns from user feedback

### `query_interface.py`
Natural language search interface:
- Processes search queries in plain English
- Returns relevant files with reasoning
- Provides search suggestions

## System Operation

### Testing Protocol
🧪 **Test after each completed step** - Ensure reliability and accuracy at every phase

### Confidence Levels
- **0.8+**: Auto-move files (high confidence) - **TEST:** >90% accuracy required
- **0.6-0.8**: Suggest moves (medium confidence) - **TEST:** User satisfaction >80%
- **0.4-0.6**: Manual review required (low confidence) - **TEST:** Clear reasoning provided
- **<0.4**: Mark as uncertain for human classification - **TEST:** No false positives

### Staging Workflow
- **Monitor Phase:** Days 1-7, observe file usage patterns
- **Suggestion Phase:** Day 7, gentle organization prompts  
- **Learning Phase:** Adapt based on user responses
- **Automation Phase:** High-confidence files auto-organize

### Learning System
The system learns from your organization patterns:
1. **Feedback Integration**: When you move files manually, it learns your preferences
2. **Pattern Discovery**: Identifies new organizational themes automatically
3. **Category Evolution**: Discovers new meaningful groupings over time
4. **Confidence Calibration**: Learns when to be more/less certain

## Usage

### Quick Start
```bash
# Search for files
python librarian.py search "Find Finn Wolfhard contracts"

# Check system status
python librarian.py status

# Organize files (dry run)
python librarian.py organize --dry-run

# Index files for search
python librarian.py index
```

### Commands
- `search "query"` - Natural language file search
- `status` - Show system statistics
- `organize` - Organize files from staging folders
- `index` - Build content search index
- `suggest "partial"` - Get search suggestions

## Backup & Recovery
All file movements are logged in `file_organization_log.csv`, allowing you to:
- Trace any file back to its original location
- Understand why classification decisions were made
- Recover from any organizational mistakes
- Monitor system performance over time

---
*System initialized: 2025-08-13*
*Based on AI-Audio-Organizer principles*