# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# User's AI File Organizer

## 🎯 **Why This System Exists**

User has ADHD and managing file organization is genuinely difficult. This system creates an **intelligent librarian** that:
- Knows User and his work intimately
- Finds things quickly without perfect organization
- Helps connect related documents and ideas
- Works intuitively within macOS
- Reduces the cognitive load of staying organized

**Core Philosophy:** Make finding and organizing files as effortless as having a conversation.

## 👤 **About User**

**Professional Roles:**
- Entertainment Manager (Client Name, TV Show)
- Creative Producer (The Creative Project podcast - AI consciousness content)
- Business Owner (Management Company)
- Developer (building AI tools)

**Types of Content:.**
- Entertainment contracts and agreements (SAG-AFTRA, management deals)
- Creative scripts and AI research papers
- Business documents (invoices, tax records, commissions)
- Email communications
- Creative project files (audio, documents)

**Current Projects:**
- Managing Client Name's career
- "The Creative Project" podcast about AI consciousness
- Various creative writing and film projects

## 🧠 **How User Uses This System**

### Daily Workflows:
1. **"Where's that contract?"** - Semantic search across PDFs and emails
2. **"What did we discuss about this project?"** - Cross-reference emails and documents
3. **"I need similar documents"** - Find related contracts or creative content
4. **"Clean up my Downloads folder"** - Auto-organize and deduplicate files

### ADHD-Friendly Features:
- **Natural language search**: "Find Client Name's payment terms" instead of remembering exact filenames
- **Smart categorization**: Files get organized automatically by content, not manual sorting
- **Interactive questioning**: System asks clarifying questions until 85% confident about file placement
- **Learning preferences**: Remembers your decisions to reduce future questions
- **Duplicate detection**: Prevents the anxiety of "did I already save this?"
- **Apple Script integration**: Works within macOS workflow, no context switching

## 🏗️ **System Architecture**

```
📁 AI File Organizer v3.1 - Intelligent Learning Organizer (Phase 1 COMPLETE)/
├── 🧠 Vector Database (ChromaDB)         # Semantic search engine
├── 📧 Email Integration (.emlx files)    # macOS Mail integration
├── 📄 Document Processing               # PDFs, DOCX, scripts
├── ☁️ Google Drive Hybrid Integration    # 2TB cloud storage with local caching
├── 🌊 File Streaming Service            # On-demand cloud file access
├── 🔄 Background Sync Service           # Continuous synchronization
├── 🔍 Smart Search Interface           # Natural language queries (local + cloud)
├── 🍎 AppleScript GUI                  # Native macOS integration
├── 🤔 Interactive Classification       # Asks questions until 85% confident
├── 🛡️ Easy Rollback System             # Complete file operation safety net
├── 🗂️ Intelligent Organization         # Auto-categorization with learning
└── 🎓 Phase 1 Core Intelligence (NEW - OPERATIONAL)
    ├── Universal Adaptive Learning      # Learns from all user interactions
    ├── 4-Level Confidence System       # NEVER/MINIMAL/SMART/ALWAYS modes
    ├── Adaptive Background Monitor     # Observes manual file movements
    ├── Emergency Space Protection      # Proactive disk management
    ├── Interactive Batch Processor     # Multi-file handling with preview
    └── Automated Deduplication Service # Intelligent duplicate detection
```

### Key Components:

**Core Foundation:**
- **enhanced_librarian.py**: Advanced semantic search with hybrid cloud/local capability
- **gdrive_integration.py**: Google Drive hybrid architecture (2TB cloud storage)
- **vector_librarian.py**: The brain - semantic search with smart chunking
- **email_extractor.py**: Reads macOS Mail for unified search
- **interactive_classifier.py**: Asks questions until 85% confident, learns preferences
- **interactive_organizer.py**: Main organization workflow with questioning
- **easy_rollback_system.py**: Complete rollback safety net for all file operations
- **Enhanced_Search_GUI.applescript**: Native Mac search interface
- **content_extractor.py**: Handles PDFs, DOCX, text files
- **staging_monitor.py**: Auto-organizes new files
- **gdrive_streamer.py**: On-demand file streaming from Google Drive
- **background_sync_service.py**: Continuous local/cloud synchronization

**Phase 1 Core Intelligence (OPERATIONAL - October 24, 2025):**
- **universal_adaptive_learning.py**: Learns from all user interactions and corrections (1,087 lines)
- **confidence_system.py**: 4-level ADHD-friendly confidence modes - NEVER/MINIMAL/SMART/ALWAYS (892 lines)
- **adaptive_background_monitor.py**: Observes and learns from manual file movements (1,456 lines)
- **emergency_space_protection.py**: Proactive disk space monitoring and protection (987 lines)
- **interactive_batch_processor.py**: Multi-file handling with content preview (1,529 lines)
- **automated_deduplication_service.py**: Intelligent duplicate detection with rollback (1,203 lines)
- **integration_test_suite.py**: Comprehensive component verification
- **final_verification.py**: End-to-end system validation

### Audio Organizer Inspiration Features:
- **audio_analyzer.py**: Audio content analysis (BPM, brightness, texture, energy levels)
- **audioai_organizer.py**: Core adaptive learning system from audio-ai-organizer
- **Spectral Analysis**: Advanced audio understanding using librosa
- **Adaptive Learning System**: Learns user patterns and improves over time
- **Confidence-Based Processing**: Smart interaction modes (smart/minimal/always/never)
- **Metadata Export**: Excel spreadsheets with comprehensive analysis data

## 🛠️ **Development Commands**

### Setup & Dependencies
```bash
# Install Python dependencies
pip install -r requirements_v3.txt  # Main requirements for v3 system
pip install -r requirements.txt      # Core dependencies (PyPDF2, chromadb, etc)

# Start web server
python main.py  # Runs FastAPI server on http://localhost:8000
```

### Testing Commands
```bash
# Run individual test files
python test_integration.py          # Test complete system integration
python test_hybrid_architecture.py  # Test Google Drive hybrid setup
python test_single_file.py         # Test single file classification
python test_7day_rule.py           # Test 7-day staging rule
python test_email_integration.py   # Test email extraction

# Phase 1 verification (NEW - OPERATIONAL)
python integration_test_suite.py   # Verify all Phase 1 components
python final_verification.py       # End-to-end system validation
```

### Phase 1 Core Intelligence Commands (NEW - OPERATIONAL)
```bash
# Universal Adaptive Learning
python universal_adaptive_learning.py status          # Show learning statistics
python universal_adaptive_learning.py export          # Export learning data
python universal_adaptive_learning.py patterns        # View discovered patterns

# 4-Level Confidence System
python confidence_system.py set smart                 # Set SMART mode (70% confidence)
python confidence_system.py set minimal               # Set MINIMAL mode (40% confidence)
python confidence_system.py set always                # Set ALWAYS mode (100% confidence)
python confidence_system.py set never                 # Set NEVER mode (0% confidence)
python confidence_system.py status                    # Show current mode

# Adaptive Background Monitor
python adaptive_background_monitor.py start           # Start learning from file movements
python adaptive_background_monitor.py stats           # Show learning statistics
python adaptive_background_monitor.py patterns        # View learned patterns

# Emergency Space Protection
python emergency_space_protection.py status           # Check disk space status
python emergency_space_protection.py protect          # Enable proactive protection
python emergency_space_protection.py history          # View protection history

# Interactive Batch Processor
python interactive_batch_processor.py process /path   # Process multiple files
python interactive_batch_processor.py preview /path   # Preview batch operations

# Automated Deduplication Service
python automated_deduplication_service.py scan        # Scan for duplicates
python automated_deduplication_service.py clean       # Clean duplicates with rollback
python automated_deduplication_service.py stats       # Show deduplication statistics
```

### Audio Analysis Commands (Inspired by audio-ai-organizer)
```bash
# Audio content analysis and organization
python audio_analyzer.py analyze file.mp3    # BPM, brightness, texture analysis
python audioai_organizer.py --mode smart     # Smart interaction mode (70% confidence)
python audioai_organizer.py --mode minimal   # Minimal questions (40% confidence)
python audioai_organizer.py --mode always    # Always ask (100% confidence)
python audioai_organizer.py --mode never     # Fully automatic (0% confidence)

# Learning system operations
python audioai_organizer.py --export-learning    # Export classification patterns
python audioai_organizer.py --import-learning    # Import previous patterns
python audioai_organizer.py --learning-stats     # Show learning statistics
```

### 🚨 **MANDATORY PROCESS: Check Critical Files First**
**BEFORE starting ANY task, read these files for context and process requirements:**

1. **`MANDATORY_WORKFLOW_CHECKLIST.md`** - Process requirements for all work
2. **`PM_SYSTEM_ANALYSIS_MEMO.md`** - Current project priorities and status  
3. **`CRITICAL_PROCESS_REFERENCE_INDEX.md`** - Quick navigation and templates

### 🤖 **MANDATORY: Agent Usage Requirements**
**AFTER checking critical files, use this agent checklist:**

```bash
# Agent Selection Checklist (ALWAYS use before starting work):
# □ Multi-step task (>3 steps)? → task-orchestrator
# □ Code implementation/verification? → testing-debugging-expert  
# □ Documentation work? → documentation-expert
# □ UI/UX improvements? → ux-fullstack-designer
# □ Google Drive operations? → google-drive-api-expert
# □ Complex research/search? → general-purpose

# Examples of MANDATORY agent use:
python -c "# Multi-step implementation" # → Use task-orchestrator
python -c "# After any code changes" # → Use testing-debugging-expert
python -c "# Any documentation updates" # → Use documentation-expert
python -c "# Any web interface work" # → Use ux-fullstack-designer
python -c "# Any Google Drive issues" # → Use google-drive-api-expert
```

### 📋 **Workflow Automation**
Use templates from `TODO_TEMPLATES_AGENT_INTEGRATION.py` for automatic agent integration in TodoWrite.

### Development Tips
- **Agent-First Workflow** - Use specialized agents rather than manual work
- **No formal linting setup** - maintain clean Python code style
- **No package manager** - use pip with requirements files
- **FastAPI server** - Main entry point is `main.py`
- **Test files** - Individual test scripts, no test framework
- **Audio Analysis** - Uses librosa, mutagen, OpenAI for spectral analysis
- **Adaptive Learning** - Pickle files store classification patterns and user corrections

## 🚀 **How to Use**

### Quick Search (GUI):
1. Double-click "Enhanced AI Search.app" 
2. Type natural language: "Client Name contracts"
3. Choose search mode: Fast/Semantic/Auto
4. Get results with context and reasoning

### Command Line Search (Hybrid Cloud + Local):
```bash
# Unified search across Google Drive + local files
python enhanced_librarian.py search "AI consciousness papers" --mode semantic
python enhanced_librarian.py search "payment terms" --mode fast  
python enhanced_librarian.py search "meeting schedules" --mode auto

# Google Drive specific commands
python gdrive_integration.py  # Check Google Drive status and create directory structure
```

### Interactive File Organization:
```bash
# Organize files with smart questions (ADHD-friendly)
python interactive_organizer.py organize --live     # Actually move files
python interactive_organizer.py organize --dry-run  # Preview only

# Quick organize specific folder
python interactive_organizer.py quick /Users/user/Downloads --live

# Test single file
python interactive_organizer.py file "/path/to/document.pdf" --live
```

### Index New Content (Hybrid Architecture):
```bash
# Index from Google Drive primary storage
python enhanced_librarian.py index --folder "/Users/user/GoogleDrive/AI_Organizer/01_ACTIVE_PROJECTS"
python vector_librarian.py  # Index emails + documents with smart chunking across cloud and local

# Check Google Drive integration status
python gdrive_integration.py  # Shows Google Drive mount status and creates directory structure
```

### Easy Rollback System (CRITICAL - ALWAYS USE WHEN FILE OPERATIONS GO WRONG):
```bash
# FIRST: Always check what AI operations happened recently
python easy_rollback_system.py --list

# If you see mysterious/wrong file operations, undo them immediately:
python easy_rollback_system.py --undo 123      # Undo specific operation ID
python easy_rollback_system.py --undo-today    # Emergency: undo all today's operations

# Search for specific file operations that went wrong:
python easy_rollback_system.py --search "contract"  # Find operations on files containing "contract"

# Show today's operations only (helpful for debugging):
python easy_rollback_system.py --today
```

## 💡 **Real Examples**

### Typical Searches User Makes:
- `"TV Show contract exclusivity"`
- `"Creative Project episode about attention mechanisms"`
- `"emails about creative collaboration"`
- `"commission payments from last quarter"`
- `"SAG-AFTRA agreement terms"`

### What Makes This Different:
- **Understands context**: Knows "Client Name" means Client Name
- **Connects ideas**: Links creative projects to business documents
- **Learns patterns**: Recognizes User's work style and priorities
- **Reduces friction**: No manual tagging or complex folder structures

## 🏛️ **High-Level Architecture**

### Core System Flow
1. **File Ingestion** → Files enter through Downloads/Desktop monitoring or manual input
2. **Content Extraction** → `content_extractor.py` processes PDFs, DOCX, emails
3. **Semantic Analysis** → `vector_librarian.py` creates embeddings with ChromaDB
4. **Classification** → `interactive_classifier.py` determines categories with confidence scores
5. **User Interaction** → Low-confidence files trigger questions via web UI or CLI
6. **Organization** → `interactive_organizer.py` moves files to appropriate locations
7. **Rollback Safety** → `easy_rollback_system.py` logs all operations for undo

### Key Design Patterns
- **Hybrid Storage**: Google Drive as primary with local caching/streaming
- **Confidence-Based Actions**: 85% threshold for automatic filing
- **Learning System**: Tracks user corrections to improve future classifications
- **ADHD-Optimized UX**: Minimal decisions, visual feedback, easy rollback

### Service Architecture (FastAPI)
- **SystemService**: Manages system status and Google Drive integration
- **SearchService**: Handles semantic and keyword search queries
- **TriageService**: Manages low-confidence file reviews
- **Web Frontend**: Glassmorphic UI in `/frontend` directory

### Audio-AI-Organizer Inspired Features (Target Implementation)

#### Adaptive Learning System
```python
# From audio_organizer_source/audioai_organizer.py - core learning patterns
class AdaptiveAudioOrganizer:
    - Pickle-based learning data storage (learning_data.pkl)
    - Dynamic category discovery (discovered_categories.json)
    - User correction tracking and pattern recognition
    - Confidence calibration based on historical accuracy
```

#### Interaction Modes (4 Levels)
- **SMART Mode (70% confidence)**: Balanced operation, asks when genuinely uncertain
- **MINIMAL Mode (40% confidence)**: Quick processing, only very uncertain files
- **ALWAYS Mode (100% confidence)**: Maximum accuracy, every file gets review
- **NEVER Mode (0% confidence)**: Fully automatic, bulk processing

#### Advanced Audio Analysis Pipeline
1. **Spectral Analysis**: librosa extracts tempo, brightness, texture, energy
2. **Content Classification**: ML distinguishes music/SFX/voice/documents
3. **Mood Detection**: Energy and harmonic analysis for emotional context
4. **Pattern Recognition**: Compares against learned user preferences
5. **Confidence Scoring**: Determines if human input needed

#### Metadata Export System
- **Excel Spreadsheets**: Comprehensive analysis data with timestamps
- **Learning Statistics**: Track system improvement over time
- **Original Filename Preservation**: Complete traceability for rollback
- **Cross-Reference System**: Files can belong to multiple categories

## 🧠 **Critical Missing Features from Audio-AI-Organizer (SYSTEM-WIDE)**

**Based on analysis of `/Users/user/Github/AI-Audio-Organizer/`, these features should be implemented SYSTEM-WIDE for ALL file types (documents, emails, images, audio, etc.):**

### Universal Adaptive Learning System (Currently Missing)
```bash
# SYSTEM-WIDE learning for ALL file types - not just audio
pip install librosa mutagen pandas openpyxl  # Required dependencies

# Content analysis for any file type
python content_analyzer.py extract_features file.pdf     # Contract analysis, mood detection
python content_analyzer.py detect_mood file.mp3         # Audio: contemplative, mysterious, energetic  
python content_analyzer.py classify_content file.jpg    # Image: professional, creative, personal
python content_analyzer.py analyze_email message.emlx   # Email: project-related, client communication
python content_analyzer.py detect_patterns file.docx    # Document: script, contract, creative writing
```

### Universal Adaptive Learning System Architecture
```python
# Adapted from AI-Audio-Organizer: SYSTEM-WIDE for ALL file types
04_METADATA_SYSTEM/
├── learning_data.pkl          # ALL file type classification history
├── discovered_categories.json # Dynamic category discovery (contracts, creative, etc.)
├── file_metadata_YYYYMMDD.xlsx   # Excel export for ALL files
├── email_patterns.pkl         # Email-specific learning patterns
├── document_patterns.pkl      # PDF/DOCX learning patterns  
└── multimedia_patterns.pkl    # Audio/image/video patterns

# UNIVERSAL learning data structure for ALL file types:
learning_data = {
    'classifications': [],      # AI decisions for PDFs, emails, audio, images, etc.
    'user_corrections': [],     # User feedback for ALL file types
    'patterns': defaultdict(list),  # Contract patterns, creative patterns, etc.
    'filename_patterns': defaultdict(list),  # Patterns across ALL file types
    'content_patterns': defaultdict(list),   # Document content, email themes, etc.
    'client_patterns': defaultdict(list),    # Entertainment industry client patterns
    'project_patterns': defaultdict(list)    # Creative project patterns
}
```

### Smart Folder Structure (Target Implementation)
```
01_UNIVERSAL_ASSETS/
├── MUSIC_LIBRARY/by_mood/
│   ├── contemplative/
│   ├── tension_building/
│   ├── mysterious/
│   └── wonder_discovery/
├── SFX_LIBRARY/by_category/
│   ├── consciousness/thought_processing/
│   ├── human_elements/breathing_heartbeat/
│   ├── environmental/abstract_conceptual/
│   └── technology/digital_synthetic/
└── VOICE_ELEMENTS/
    ├── narrator_banks/
    ├── processed_vocals/
    └── character_voices/
```

### Filename Enhancement System
```python
# Semantic preservation with metadata integration
# Before: "88bpm_play playful_childlike_beat_ES_February_Moon.mp3"
# After:  "playful_childlike_February_Moon_Instrumental_MUS_88bpm_CONT_E7.mp3"

# Enhancement includes:
- Original semantic meaning preservation
- BPM detection and tagging
- Energy level classification (E1-E10)
- Mood abbreviations (CONT=contemplative, MYST=mysterious)
- Content type codes (MUS=music, SFX=sound effects, VOX=voice)
```

### Universal Interactive Batch Processing
```python
# SYSTEM-WIDE interactive processing for ALL file types
organizer.interactive_batch_process(
    file_list,  # Can be PDFs, emails, audio, images, any file type
    confidence_threshold=0.7,  # Ask when uncertain about ANY file
    preview_content=True,      # Preview PDFs, play audio, show images
    dry_run=True              # Test mode for all file types
)

# Universal interaction modes for ALL file types:
# SMART (70%) - Ask about uncertain contracts, emails, audio, etc.
# MINIMAL (40%) - Only ask about very uncertain files of any type
# ALWAYS (100%) - Human review for every file (contracts, creative, etc.)
# NEVER (0%) - Fully automatic for all file types

# Examples of system-wide learning:
- "Client contract" patterns learned and applied to new contracts
- "Creative project" email patterns applied to similar communications  
- "Podcast episode" file patterns for creative content organization
- "Business document" classification improving over time
```

### Advanced Pattern Recognition
```python
# Filename pattern analysis for content hints
descriptors = {
    'ambient': ['ambient', 'atmosphere', 'background'],
    'percussion': ['drum', 'beat', 'rhythm', 'kick'],
    'vocal': ['vocal', 'voice', 'speech', 'dialogue'], 
    'nature': ['nature', 'wind', 'rain', 'forest'],
    'mechanical': ['robot', 'machine', 'tech', 'digital'],
    'emotional': ['sad', 'happy', 'dark', 'calm', 'tense']
}
```

## 🚨 **Implementation Priority for SYSTEM-WIDE Features**

1. **Universal Content Analysis Pipeline**: 
   - Audio: librosa integration for BPM/mood detection
   - Documents: PDF content analysis, contract section detection
   - Emails: Subject/sender pattern recognition
   - Images: Computer vision for professional vs creative content

2. **Universal Adaptive Learning System**: 
   - Pickle-based learning with user corrections for ALL file types
   - Cross-file-type pattern recognition (email→document→audio connections)
   - Entertainment industry specific learning (client names, project types)

3. **System-Wide Interaction Modes**: 
   - 4-level confidence system (SMART/MINIMAL/ALWAYS/NEVER) for ALL files
   - ADHD-friendly questioning for contracts, creative files, emails, etc.

4. **Universal Metadata Export**: 
   - Excel spreadsheets with analysis data for ALL file types
   - Cross-reference system linking related documents/emails/audio

5. **Dynamic Category Discovery**: 
   - Auto-discover new categories from ALL content types
   - Learn entertainment industry patterns, creative project themes

6. **Universal Filename Enhancement**: 
   - Semantic preservation + metadata integration for ALL file types
   - Client-aware naming (entertainment industry context)

**The goal: The system learns from your corrections on a contract and applies that knowledge to emails, creative files, and audio - creating a truly intelligent, unified file management system.**

## 🎯 **Phase 1 Implementation Status (COMPLETE - October 24, 2025)**

**MAJOR MILESTONE ACHIEVED**: The system has been successfully transformed from a reactive file organizer into an "Intelligent Learning Organizer" with proactive capabilities.

### **What's Now Operational:**

1. **Universal Adaptive Learning System** - COMPLETE
   - Learns from all user file movements and corrections
   - Builds pattern recognition across all file types
   - Stores learning data in pickle format for persistence
   - Discovers new categories dynamically based on user behavior

2. **4-Level ADHD-Friendly Confidence System** - COMPLETE
   - NEVER mode (0%): Fully automatic, no questions
   - MINIMAL mode (40%): Only ask about very uncertain files
   - SMART mode (70%): Balanced operation, default for ADHD users
   - ALWAYS mode (100%): Human review for every file

3. **Adaptive Background Monitor** - COMPLETE
   - Observes manual file movements in real-time
   - Learns organizational patterns from user behavior
   - Improves classification confidence over time
   - Runs continuously in background without cognitive load

4. **Emergency Space Protection** - COMPLETE
   - Proactive disk space monitoring
   - Prevents "disk full" crises before they happen
   - Automatic emergency staging when space runs low
   - ADHD-friendly: eliminates panic moments from sudden space issues

5. **Interactive Batch Processor** - COMPLETE
   - Handles multiple files with content preview
   - ADHD-friendly interaction modes
   - Dry-run mode for safe testing
   - Integrated with confidence system for smart decisions

6. **Automated Deduplication Service** - COMPLETE
   - SHA-256 based duplicate detection
   - Rollback safety for all duplicate operations
   - Learning system integration
   - Prevents ADHD paralysis from duplicate files

### **Verification Status:**
- ✅ All 6 components implemented (7,154 lines total)
- ✅ Independent verification completed
- ✅ All imports and integrations tested
- ✅ CLI commands validated and corrected
- ✅ Database initialization verified
- ✅ Directory structure confirmed
- ✅ Production-ready for daily use

### **Next Steps for Phase 2:**
- User testing and feedback collection
- Social media announcements
- Community engagement
- Real-world usage pattern analysis
- Feature refinement based on actual user behavior
- Planning for advanced features (audio analysis, computer vision)

## 🔧 **Technical Details**

### Hybrid Cloud Architecture:
- **Primary Storage**: Google Drive (2TB) serves as the main storage root
- **Local Caching**: Intelligent file streaming with local metadata store
- **Background Sync**: Continuous synchronization between local and cloud
- **Emergency Staging**: 99_STAGING_EMERGENCY folder for space management
- **Unified Search**: Single search interface across local files and Google Drive

### File Types Supported:
- **Documents**: PDF, DOCX, Pages, TXT, MD
- **Emails**: macOS Mail (.emlx files)
- **Code**: Python, JavaScript, Jupyter notebooks
- **Creative**: Scripts, research papers, audio specs
- **Cloud Files**: Full Google Drive integration with on-demand streaming

### Smart Chunking System:
- **Contracts**: Chunks by sections (compensation, terms, exclusivity)
- **Scripts**: Chunks by scenes and dialogue
- **Emails**: Separates headers from body content
- **Research**: Preserves academic paper structure
- **Cloud Content**: Maintains smart chunking across local and cloud files

### Search Modes:
- **Fast**: Keyword matching (good for names, dates)
- **Semantic**: AI understanding (good for concepts, themes)
- **Auto**: Intelligently chooses best approach
- **Hybrid**: Combines both local and cloud sources for comprehensive results

## 🎯 **ADHD-Specific Design Decisions**

1. **Interactive questioning**: Asks clarifying questions instead of guessing
2. **85% confidence threshold**: Won't file until genuinely confident
3. **Learning system**: Remembers your decisions to reduce future questions
4. **Binary choices**: Simple "A or B" questions, not overwhelming options
5. **Immediate feedback**: Search results show instantly
6. **Forgiving search**: Works even with imprecise queries
7. **Visual context**: Shows file types, dates, relevance scores
8. **No manual organization**: System learns from content, not folders
9. **Native integration**: Feels like part of macOS, not separate app

### Example Interactive Questions:
- *"This looks like a contract for Client Name. Should I file it under Entertainment Industry or Business Operations?"*
- *"I found mentions of creative project and business terms. Is this more about the creative work or the business side?"*
- *"This document mentions multiple people. Who is it primarily about?"*

## 📝 **Development Notes**

### When Adding Features:
- Prioritize reducing cognitive load over adding complexity
- Test with User's actual files and workflows
- Maintain the "conversation with a librarian" feel
- Keep the Apple Script GUI simple and fast

### Key Principles:
- **Content over structure**: Organize by what files contain, not where they are
- **Semantic over syntactic**: Understand meaning, not just keywords  
- **Intuitive over precise**: Better to find something close than nothing at all
- **Unified over fragmented**: One search across all content types

## 🚨 **Important Context for AI Assistants**

When working on this system:

1. **User has ADHD** - organization systems must be low-friction and intuitive
2. **Entertainment industry focus** - understand contracts, talent management, creative projects
3. **Hybrid architecture** - primary storage is now Google Drive, test with actual documents from cloud and local sources
4. **macOS integration essential** - must work seamlessly within existing workflow
5. **Privacy conscious** - all processing happens locally, Google Drive is only for storage and file operations

## 🛡️ **CRITICAL: Rollback System for Trust and Safety**

**MANDATORY PRACTICE**: After any file organization operations, ALWAYS check the rollback system to ensure nothing went wrong:

```bash
# After running any organizer commands, ALWAYS run this:
python easy_rollback_system.py --today    # Check today's operations

# If operations look wrong (low confidence, bad filenames, etc.), undo immediately:
python easy_rollback_system.py --undo-today    # Emergency rollback all today's operations
```

**Why This Matters:**
- The user discovered AI systems had been renaming files with random names, creating "a real mess"
- This violated ADHD-friendly design and broke user trust
- The rollback system provides the "easy to find and navigate way of simply undoing mis-files" that was desperately needed
- NEVER perform file operations without ensuring the user can easily undo them

**Trust Recovery Protocol:**
1. Any file operation creates rollback entries automatically
2. User can see exactly what changed with before/after names
3. One-click undo for any operation that went wrong
4. Works with both local files and Google Drive operations
5. ADHD-friendly design with visual interfaces and simple commands

This isn't just a file organizer - it's an accessibility tool that makes information management possible for someone with ADHD working in a complex, document-heavy industry.

---

*Last updated: 2025-10-24*
*Version: 3.1 - Phase 1 Core Intelligence COMPLETE*
*Milestone: Transformation into "Intelligent Learning Organizer" achieved with 7,154 lines of verified production code*
