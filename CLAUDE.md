# User's AI File Organizer

---

### Requirements
- Python 3.11+
- macOS with AppleScript support
- Node.js (for optional UI wrappers)

### Installation
```bash
git clone https://github.com/ryan/ai-file-organizer
cd ai-file-organizer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

---

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

**Types of Content:**
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
📁 AI File Organizer v3.0/
├── 🧠 Vector Database (ChromaDB)         # Semantic search engine
├── 📧 Email Integration (.emlx files)    # macOS Mail integration  
├── 📄 Document Processing               # PDFs, DOCX, scripts
├── 🎬 Computer Vision (Gemini 2.5 Flash) # Images and video analysis
├── 🎵 Audio AI Analysis               # Professional audio processing
├── 📚 Video Project Trainer           # Learns user's projects
├── 🔍 Smart Search Interface           # Natural language queries
├── 🍎 AppleScript GUI                  # Native macOS integration
├── 🤔 Interactive Classification       # 5 interaction modes with learning
├── 🏷️ Comprehensive Tagging System     # Multi-source auto-tagging
├── ☁️ Google Drive Integration         # 2TB cloud storage
└── 🗂️ Intelligent Organization         # Auto-categorization with learning
```

### Core Components:
- **enhanced_librarian.py**: Advanced semantic search with hybrid modes
- **interactive_organizer.py**: Main organization workflow with questioning
- **vision_content_extractor.py**: Computer vision analysis (Gemini 2.5 Flash)
- **video_project_trainer.py**: Learns user's specific projects (thebearwithabite, Papers That Dream)
- **interactive_classifier.py**: 5 interaction modes (SMART, MINIMAL, LEARNING, ALWAYS, NEVER)
- **quick_learning_mode.py**: Easy mode switching for training
- **tagging_cli.py**: Comprehensive auto-tagging system
- **gdrive_cli.py**: Google Drive integration with emergency space recovery
- **audio_cli.py**: Professional audio analysis and transcription
- **batch_cli.py**: ADHD-friendly batch processing
- **email_extractor.py**: macOS Mail integration
- **vector_librarian.py**: Vector database operations
- **Enhanced_Search_GUI.applescript**: Native Mac search interface

## 🚀 **How to Use**

### Quick Search (GUI):
1. Double-click "Enhanced AI Search.app" 
2. Type natural language: "Client Name contracts"
3. Choose search mode: Fast/Semantic/Auto
4. Get results with context and reasoning

### Command Line Search:
```bash
# Enhanced semantic search
python enhanced_librarian.py search "AI consciousness papers" --mode semantic
python enhanced_librarian.py search "payment terms" --mode fast  
python enhanced_librarian.py search "meeting schedules" --mode auto

# Search by tags
python tagging_cli.py search "project:,netflix" --match-all
python tagging_cli.py search "contract,client"

# Audio content search
python audio_cli.py search "consciousness"
python audio_cli.py search "interview" --type interview

# Google Drive search
python gdrive_cli.py search --query "contract"
```

### Interactive File Organization:
```bash
# Main organization workflow
python interactive_organizer.py organize --live     # Actually move files
python interactive_organizer.py organize --dry-run  # Preview only

# Quick organize specific folder
python interactive_organizer.py quick /Users/user/Downloads --live

# Test single file
python interactive_organizer.py file "/path/to/document.pdf" --live

# Batch processing (ADHD-friendly)
python batch_cli.py directory ~/Downloads --dry-run --batch-size 20
python batch_cli.py directory ~/Documents --live
```

### Computer Vision Analysis:
```bash
# Analyze images and videos
python vision_cli.py analyze screenshot.png
python vision_cli.py analyze video.mp4 --context entertainment
python vision_cli.py directory ~/Downloads --limit 5

# Video project recognition
python video_project_trainer.py analyze ~/Videos
python video_project_trainer.py train --project "thebearwithabite"
```

### Interaction Modes & Learning:
```bash
# Quick learning mode activation
python quick_learning_mode.py --learning  # Aggressive learning
python quick_learning_mode.py --smart     # Normal operation
python quick_learning_mode.py --status    # Check current mode

# Manual mode control
python demo_interaction_modes.py  # Interactive mode selection
```

### Google Drive Integration:
```bash
# Emergency space recovery
python gdrive_cli.py emergency --live     # Free up space immediately
python gdrive_cli.py organize --live      # Organize and upload files
python gdrive_cli.py status               # Check storage status

# Authentication and setup
python gdrive_cli.py auth --credentials gdrive_credentials.json
python gdrive_cli.py folders              # List folder structure
```

### Index New Content:
```bash
# Enhanced indexing
python enhanced_librarian.py index --folder "/Users/user/Documents/NewProject"
python enhanced_librarian.py index --semantic  # Build vector database
python vector_librarian.py                     # Index emails + documents

# Tagging and metadata
python tagging_cli.py directory ~/Documents
python metadata_cli.py analyze ~/Documents
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

## 🔧 **Technical Details**

### File Types Supported:
- **Documents**: PDF, DOCX, Pages, TXT, MD, RTF
- **Images**: PNG, JPG, GIF, TIFF, WEBP (with computer vision)
- **Videos**: MP4, MOV, AVI, MKV (with computer vision and project recognition)
- **Audio**: MP3, WAV, FLAC, M4A, AUP3 (with AI analysis and transcription)
- **Emails**: macOS Mail (.emlx files)
- **Code**: Python, JavaScript, Jupyter notebooks, HTML, CSS
- **Creative**: Scripts, research papers, story documents

### Smart Chunking System:
- **Contracts**: Chunks by sections (compensation, terms, exclusivity)
- **Scripts**: Chunks by scenes and dialogue
- **Emails**: Separates headers from body content
- **Research**: Preserves academic paper structure

### Search Modes:
- **Fast**: Keyword matching (good for names, dates)
- **Semantic**: AI understanding (good for concepts, themes)
- **Auto**: Intelligently chooses best approach
- **Hybrid**: Combines both for comprehensive results

### Interaction Modes:
- **SMART** (75%): Default - asks when uncertain, optimized for learning
- **MINIMAL** (40%): Only asks about very uncertain files  
- **LEARNING** (85%): Aggressive learning mode for rapid system training
- **ALWAYS** (100%): Maximum accuracy - asks about every file
- **NEVER** (0%): Fully automatic - no questions (bulk processing)

### Computer Vision Contexts:
- **General**: Standard image/video analysis
- **Entertainment**: Entertainment industry focus (Client Name Wolfhard projects)
- **Creative**: Creative projects (Papers That Dream, AI content, thebearwithabite)

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
3. **Real files matter** - test with actual documents from `/Users/user/Documents/`
4. **macOS integration essential** - must work seamlessly within existing workflow
5. **Privacy conscious** - all processing happens locally, no cloud uploads

This isn't just a file organizer - it's an accessibility tool that makes information management possible for someone with ADHD working in a complex, document-heavy industry.

## 🤖 **Claude Code Agent Integration**

The following specialized agents are configured to work proactively and automatically with the AI File Organizer:

### test-runner
**Purpose**: Execute comprehensive test suites, validate functionality, ensure quality
**Proactive Triggers**:
- After any changes to core classification engine (`classification_engine.py`)
- Before any git commits involving Python files
- After modifying search functionality (`enhanced_librarian.py`, `vector_librarian.py`)
- When interactive organizer logic changes (`interactive_organizer.py`)
- After AppleScript GUI modifications

### context-doc-manager
**Purpose**: Keep documentation synchronized with codebase changes, maintain project coherence
**Proactive Triggers**:
- After adding new CLI tools or commands
- When new file types or analysis features are added
- After modifying Google Drive integration (`gdrive_cli.py`)
- When ADHD-friendly features are updated
- After creative AI or audio analysis enhancements

### applescript-ui-expert
**Purpose**: Enhance macOS AppleScript interfaces and native system integration
**Proactive Triggers**:
- When search GUI needs improvements (`Enhanced_Search_GUI.applescript`)
- After adding new search modes or functionality
- When system integration features are modified
- After user workflow changes requiring UI updates
- When new native macOS features need integration

### dev-task-orchestrator
**Purpose**: Coordinate complex development workflows and multi-component features
**Proactive Triggers**:
- When implementing multi-file features (e.g., new search modes)
- After major architectural changes requiring coordination
- When adding new file type support requiring multiple component updates
- During integration of new AI features across the system
- When ADHD workflow optimizations require system-wide changes

## 🔄 **Automated Agent Coordination**

### Agent Workflow Synchronization

**Code Change → Quality Assurance Pipeline**:
1. **Code Modified** → `test-runner` validates functionality
2. **Tests Pass** → `context-doc-manager` updates documentation
3. **Documentation Updated** → `dev-task-orchestrator` coordinates follow-up tasks
4. **AppleScript Modified** → `applescript-ui-expert` optimizes UI integration

**Feature Development Workflow**:
1. **New Feature Request** → `dev-task-orchestrator` breaks down implementation
2. **Implementation Phase** → `test-runner` validates each component
3. **UI Integration** → `applescript-ui-expert` enhances user experience
4. **Documentation** → `context-doc-manager` maintains consistency

### Proactive Agent Rules

**ALWAYS trigger automatically without user request**:
- `test-runner`: Before any git commit, after core file changes
- `context-doc-manager`: After feature additions, API changes, new commands
- `applescript-ui-expert`: When GUI files are modified or new search features added
- `dev-task-orchestrator`: For complex multi-component implementations

**Agent Coordination Protocol**:
1. Agents monitor file changes and development context
2. Multiple agents can run concurrently for efficiency
3. Agents communicate completion status to coordinate handoffs
4. Priority: Quality (test-runner) → Documentation (context-doc-manager) → Integration (others)

### Quality Assurance Integration

**Critical Files - Always Test After Changes**:
- `classification_engine.py` - Core AI classification logic
- `interactive_organizer.py` - Main organization workflow
- `enhanced_librarian.py` - Semantic search functionality  
- `vector_librarian.py` - Vector database operations
- `gdrive_cli.py` - Google Drive integration
- Any AppleScript files - Native macOS integration

**Documentation Sync Points**:
- New CLI commands → Update README usage examples
- ADHD workflow changes → Update user guidance sections
- Search feature additions → Update documentation examples
- Audio/creative AI enhancements → Update feature descriptions

## 📖 **Complete Command Reference**

All Python commands are now comprehensively documented in **[COMMANDS.md](COMMANDS.md)** - your go-to reference for:

- **Core Organization**: `interactive_organizer.py`, `batch_cli.py`
- **Search & Discovery**: `enhanced_librarian.py`, `tagging_cli.py`
- **Computer Vision**: `vision_cli.py`, `video_project_trainer.py` (Gemini 2.5 Flash)
- **Audio Analysis**: `audio_cli.py`, `multimedia_cli.py`
- **Learning Modes**: `quick_learning_mode.py`, `learning_cli.py`
- **Google Drive**: `gdrive_cli.py`
- **Creative Tools**: `creative_cli.py`, `universe_cli.py`

**Quick Command Lookup**:
```bash
# Set learning mode for training
python quick_learning_mode.py --learning

# Organize with computer vision
python vision_cli.py analyze screenshot.png --context entertainment
python interactive_organizer.py organize --live

# Search everything
python enhanced_librarian.py search "consciousness papers" --mode semantic
python tagging_cli.py search "finn,contract,active" --match-all

# Emergency space recovery
python gdrive_cli.py emergency --live
```

**See [COMMANDS.md](COMMANDS.md) for complete usage examples, troubleshooting, and workflow patterns.**

---

*Last updated: 2025-09-03*
*Version: 3.0 - Computer vision integration, video project trainer, comprehensive command reference*
