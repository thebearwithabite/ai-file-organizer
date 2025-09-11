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
📁 AI File Organizer v3.0 - Hybrid Cloud Architecture/
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
└── 🗂️ Intelligent Organization         # Auto-categorization with learning
```

### Key Components:
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

*Last updated: 2025-09-10*
*Version: 3.0 - Now with Google Drive Hybrid Architecture and Complete Rollback System*
