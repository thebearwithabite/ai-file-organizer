# User's AI File Organizer

## 🎯 **Why This System Exists**

Ryan has ADHD and managing file organization is genuinely difficult. This system creates an **intelligent librarian** that:
- Knows Ryan and his work intimately
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

## 🧠 **How Ryan Uses This System**

### Daily Workflows:
1. **"Where's that contract?"** - Semantic search across PDFs and emails
2. **"What did we discuss about this project?"** - Cross-reference emails and documents
3. **"I need similar documents"** - Find related contracts or creative content
4. **"Clean up my Downloads folder"** - Auto-organize and deduplicate files

### ADHD-Friendly Features:
- **Natural language search**: "Find Finn's payment terms" instead of remembering exact filenames
- **Smart categorization**: Files get organized automatically by content, not manual sorting
- **Interactive questioning**: System asks clarifying questions until 85% confident about file placement
- **Learning preferences**: Remembers your decisions to reduce future questions
- **Duplicate detection**: Prevents the anxiety of "did I already save this?"
- **Apple Script integration**: Works within macOS workflow, no context switching

## 🏗️ **System Architecture**

```
📁 AI File Organizer/
├── 🧠 Vector Database (ChromaDB)         # Semantic search engine
├── 📧 Email Integration (.emlx files)    # macOS Mail integration  
├── 📄 Document Processing               # PDFs, DOCX, scripts
├── 🔍 Smart Search Interface           # Natural language queries
├── 🍎 AppleScript GUI                  # Native macOS integration
├── 🤔 Interactive Classification       # Asks questions until 85% confident
└── 🗂️ Intelligent Organization         # Auto-categorization with learning
```

### Key Components:
- **vector_librarian.py**: The brain - semantic search with smart chunking
- **email_extractor.py**: Reads macOS Mail for unified search
- **interactive_classifier.py**: Asks questions until 85% confident, learns preferences
- **interactive_organizer.py**: Main organization workflow with questioning
- **Enhanced_Search_GUI.applescript**: Native Mac search interface
- **content_extractor.py**: Handles PDFs, DOCX, text files
- **staging_monitor.py**: Auto-organizes new files

## 🚀 **How to Use**

### Quick Search (GUI):
1. Double-click "Enhanced AI Search.app" 
2. Type natural language: "Client Name contracts"
3. Choose search mode: Fast/Semantic/Auto
4. Get results with context and reasoning

### Command Line Search:
```bash
python enhanced_librarian.py search "AI consciousness papers" --mode semantic
python enhanced_librarian.py search "payment terms" --mode fast  
python enhanced_librarian.py search "meeting schedules" --mode auto
```

### Interactive File Organization:
```bash
# Organize files with smart questions (ADHD-friendly)
python interactive_organizer.py organize --live     # Actually move files
python interactive_organizer.py organize --dry-run  # Preview only

# Quick organize specific folder
python interactive_organizer.py quick /Users/ryan/Downloads --live

# Test single file
python interactive_organizer.py file "/path/to/document.pdf" --live
```

### Index New Content:
```bash
python enhanced_librarian.py index --folder "/Users/user/Documents/NewProject"
python vector_librarian.py  # Index emails + documents with smart chunking
```

## 💡 **Real Examples**

### Typical Searches Ryan Makes:
- `"TV Show contract exclusivity"`
- `"Creative Project episode about attention mechanisms"`
- `"emails about creative collaboration"`
- `"commission payments from last quarter"`
- `"SAG-AFTRA agreement terms"`

### What Makes This Different:
- **Understands context**: Knows "Finn" means Client Name
- **Connects ideas**: Links creative projects to business documents
- **Learns patterns**: Recognizes Ryan's work style and priorities
- **Reduces friction**: No manual tagging or complex folder structures

## 🔧 **Technical Details**

### File Types Supported:
- **Documents**: PDF, DOCX, Pages, TXT, MD
- **Emails**: macOS Mail (.emlx files)
- **Code**: Python, JavaScript, Jupyter notebooks
- **Creative**: Scripts, research papers, audio specs

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
- Test with Ryan's actual files and workflows
- Maintain the "conversation with a librarian" feel
- Keep the Apple Script GUI simple and fast

### Key Principles:
- **Content over structure**: Organize by what files contain, not where they are
- **Semantic over syntactic**: Understand meaning, not just keywords  
- **Intuitive over precise**: Better to find something close than nothing at all
- **Unified over fragmented**: One search across all content types

## 🚨 **Important Context for AI Assistants**

When working on this system:

1. **Ryan has ADHD** - organization systems must be low-friction and intuitive
2. **Entertainment industry focus** - understand contracts, talent management, creative projects
3. **Real files matter** - test with actual documents from `/Users/user/Documents/`
4. **macOS integration essential** - must work seamlessly within existing workflow
5. **Privacy conscious** - all processing happens locally, no cloud uploads

This isn't just a file organizer - it's an accessibility tool that makes information management possible for someone with ADHD working in a complex, document-heavy industry.

---

*Last updated: 2025-08-21*
*Version: 2.0 - Now with email integration and vector search*