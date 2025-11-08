# AI File Organizer v3.1

## 🎯 **What This System Actually Does**

An ADHD-friendly AI file organizer that helps manage complex document workflows with semantic search, interactive classification, and complete safety rollbacks.

**Core Philosophy:** Make finding and organizing files as effortless as having a conversation with an intelligent librarian who knows your work.

---

## 🚀 **Quick Start**

### 1. Install & Start

**Recommended: Use Virtual Environment**
```bash
git clone https://github.com/thebearwithabite/ai-file-organizer
cd ai-file-organizer

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR: venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements_v3.txt
pip install -r requirements_cloud.txt  # Google Drive integration

# Start the system
python main.py
```

**Quick Start (without venv)**
```bash
git clone https://github.com/thebearwithabite/ai-file-organizer
cd ai-file-organizer
pip install -r requirements_v3.txt
pip install -r requirements_cloud.txt  # Google Drive integration
python main.py
```

### 2. Use the Web Interface
Navigate to **http://localhost:8000** for the modern web interface with:
- 🔍 **Natural language search** - "find client contract terms"
- 📋 **Triage center** - review AI classifications with confidence scores
- 📂 **One-click file opening** - click any result to open files directly
- 🧠 **Real-time status** - live system stats and file counts

---

## 🔧 **Local Environment Setup**

### Prerequisites
- Python 3.8+ with pip
- Git for version control
- (Optional) TruffleHog, detect-secrets for security scanning

### Clean Install Steps

1. **Clone and setup virtual environment:**
```bash
git clone https://github.com/thebearwithabite/ai-file-organizer
cd ai-file-organizer

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR: venv\Scripts\activate  # Windows
```

2. **Install Python dependencies:**
```bash
pip install -r requirements_v3.txt
pip install -r requirements_cloud.txt  # For Google Drive integration
pip install pytest pytest-asyncio httpx  # For testing
pip install detect-secrets  # For PII/secrets scanning
```

3. **Configure environment variables:**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env to set your paths (optional)
# AUTO_MONITOR_PATHS=~/Downloads,~/Desktop
# AUTO_MONITOR_INTERVAL=5
```

4. **Verify installation:**
```bash
# Run comprehensive validation suite
./scripts/run_all_tests.sh

# This runs:
# - Integration tests (pytest)
# - PII/secrets scan (detect-secrets)
# - Python syntax checks
```

5. **Start the server:**
```bash
python main.py
# Navigate to http://localhost:8000
```

### Security & Testing

**One-Command Validation:**
```bash
./scripts/run_all_tests.sh
```

This validation script automatically runs:
- Integration tests for all API endpoints
- PII/secrets scanning with detect-secrets
- Python syntax validation
- Git pre-push hooks verification

**Security Tools (Optional but Recommended):**
```bash
# Install TruffleHog for verified secrets detection
brew install trufflesecurity/trufflehog/trufflehog

# Install git-secrets for additional protection
brew install git-secrets
```

**Pre-Push Hooks:**
The repository includes git pre-push hooks that automatically scan for:
- Verified secrets (TruffleHog)
- Personal identifiers (detect-secrets)
- Sensitive data patterns (git-secrets)

These hooks run automatically on `git push` to prevent accidental exposure.

---

## ✅ **What Actually Works Today**

Based on verified codebase analysis (October 31, 2025):

### **Production Ready Systems:**
- ✅ **FastAPI V3 Backend** - Verified operational web server (`main.py`)
- ✅ **Modern React Web Interface** - Search, Triage, and Organize pages (`frontend_v2/`)
- ✅ **Hierarchical Organization** - 5-level deep folder structure (Project → Episode → Media Type)
- ✅ **Search Page** - Full natural language semantic search with example queries
- ✅ **Triage Center** - Fixed infinite spinner, manual scan trigger, hierarchical inputs
- ✅ **Easy Rollback System** - Complete file operation safety net (`easy_rollback_system.py`)
- ✅ **Phase 1 Core Intelligence** - Universal adaptive learning system (7,154 lines of production code)
- ✅ **Phase 2a Vision Integration** - Gemini Computer Vision for images/videos (`vision_analyzer.py`)
- ✅ **Phase 2b Vision System Integration** - Full integration with classifier and learning system
- ✅ **Phase 2c Audio Analysis** - BPM detection, mood analysis, spectral features (`audio_analyzer.py`)
- ✅ **Phase 3a VEO Prompt Builder** - Video to VEO 3.1 JSON transformation (`veo_prompt_generator.py`)
- ✅ **Unified Classification** - Content-based intelligent file categorization (`unified_classifier.py`)
- ✅ **Google Drive Integration** - Hybrid cloud architecture (`gdrive_integration.py`)
- ✅ **Bulletproof Deduplication** - SHA-256 duplicate detection (`bulletproof_deduplication.py`)

### **API Endpoints (Verified Working):**
| Endpoint | Purpose |
|----------|---------|
| `/health` | System health check |
| `/api/system/status` | Real-time system status |
| `/api/search?q={query}` | Semantic search with natural language |
| `/api/triage/scan` | Trigger manual triage scan (returns files immediately) |
| `/api/triage/files_to_review` | Files requiring manual review (cached results) |
| `/api/triage/classify` | Confirm file categorization with optional project/episode |
| `/api/upload` | Upload and classify file |
| `/api/open_file` | Open file in default application |

---

## 🛡️ **Easy Rollback System - Your Safety Net**

**CRITICAL FEATURE:** Never fear AI file operations again. One-click undo for any operation that went wrong.

```bash
# See what the AI did recently
python easy_rollback_system.py --list

# Undo a specific operation
python easy_rollback_system.py --undo 123

# Emergency: Undo ALL today's operations
python easy_rollback_system.py --undo-today
```

**Visual Protection:**
```
🔴 [123] 14:32:15
    📁 Original: 'Client_Contract_2024_Final.pdf'
    ➡️  Renamed: 'random_filename_abc123.pdf'  ← OOPS!
    🔴 Confidence: 45.2% (Low confidence = likely wrong)
    🔧 Rollback: python easy_rollback_system.py --undo 123
```

---

## 🧠 **Phase 1 Core Intelligence (COMPLETE - October 24, 2025)**

Revolutionary adaptive learning system that learns from your file movements and decisions. Phase 1 has been successfully implemented, tested, and independently verified with 7,154 lines of production-ready code.

## 🔮 **Phase 2 Advanced Content Analysis (COMPLETE - October 25, 2025)**

Gemini Vision API integration for advanced image/video analysis, plus comprehensive audio analysis pipeline. Phase 2 adds visual and audio understanding capabilities to the intelligent file organizer.

### **Operational Components:**
- ✅ **Universal Adaptive Learning** (`universal_adaptive_learning.py`) - 1,087 lines - Learns from all user interactions
- ✅ **4-Level Confidence System** (`confidence_system.py`) - 892 lines - NEVER/MINIMAL/SMART/ALWAYS modes
- ✅ **Adaptive Background Monitor** (`adaptive_background_monitor.py`) - 1,456 lines - Observes file movements
- ✅ **Emergency Space Protection** (`emergency_space_protection.py`) - 987 lines - Proactive disk management
- ✅ **Interactive Batch Processor** (`interactive_batch_processor.py`) - 1,529 lines - Multi-file handling
- ✅ **Automated Deduplication Service** (`automated_deduplication_service.py`) - 1,203 lines - Intelligent duplicates

### **ADHD-Friendly Design (Production Ready):**
- 🎯 **85% confidence threshold** - Only acts when genuinely certain
- 🤔 **Interactive questioning** - Asks clarifying questions until confident
- 📊 **Visual confidence indicators** - Color-coded trust levels (🟢🟡🔴)
- 🔄 **Learning from corrections** - Remembers your decisions and improves over time
- ⚡ **Background learning** - Observes your manual file movements automatically
- 🛡️ **Proactive protection** - Prevents disk space emergencies before they happen

---

## 🔍 **How to Search and Organize**

### **Web Interface (Recommended):**
1. Start server: `python main.py`
2. Open browser: `http://localhost:8000`
3. Search naturally: "client contract terms"
4. Review suggestions in triage center
5. One-click to open or organize files

### **Command Line (Power Users):**
```bash
# Search files semantically
python enhanced_librarian.py search "client contract terms" --mode semantic

# Organize files interactively
python interactive_organizer.py organize --live

# Check recent AI operations
python easy_rollback_system.py --today
```

---

## 🏗️ **System Architecture**

```
📁 AI File Organizer v3.1/
├── 🌐 FastAPI Web Server (main.py)
├── 🧠 Phase 1 Core Intelligence (7,154 lines)
├── 🛡️ Easy Rollback System 
├── ☁️ Google Drive Hybrid Integration
├── 🔍 Enhanced Semantic Search
├── 📄 Content-Based Classification
└── 🎯 ADHD-Friendly Interactive Design
```

**Core Files:**
- `main.py` - FastAPI web server
- `universal_adaptive_learning.py` - Main intelligence system
- `easy_rollback_system.py` - Safety rollback system
- `unified_classifier.py` - Content-based classification
- `enhanced_librarian.py` - Semantic search
- `gdrive_integration.py` - Google Drive hybrid storage

---

## 🎯 **ADHD-Friendly Design Philosophy**

### **Why This Works for ADHD Brains:**
✅ **Reduces decision paralysis** - 4 confidence modes let you choose cognitive load  
✅ **Natural language search** - "Find client payment terms" vs folder navigation  
✅ **Learning system** - Reduces questions over time as it learns patterns  
✅ **Visual feedback** - Clear confidence scores and progress indicators  
✅ **Complete safety** - Easy rollback prevents organization anxiety  
✅ **Background operation** - Works while you sleep, 7-day grace period for active files  

### **Real ADHD Benefits:**
- **Eliminate filing anxiety** - Smart confidence modes prevent overwhelming decisions
- **Reduce search frustration** - Semantic search finds things with imprecise queries
- **Professional organization** - Entertainment industry-specific workflows
- **Build knowledge effortlessly** - Automatic learning creates searchable library

---

## 🔧 **Technical Specifications**

### **Supported File Types:**
- **Documents**: PDF, DOCX, Pages, TXT, MD
- **Emails**: macOS Mail (.emlx files)
- **Code**: Python, JavaScript, Jupyter notebooks
- **Images/Video**: PNG, JPG, MP4, MOV (Gemini Vision analysis)
- **Audio**: MP3, WAV, M4A, FLAC, OGG (BPM, mood, spectral analysis)

### **AI Pipeline:**
- **Semantic Search**: ChromaDB with sentence-transformers
- **Content Analysis**: Intelligent text extraction and chunking
- **Learning System**: Pickle-based pattern discovery
- **Classification**: Confidence-based categorization

### **Performance (Verified):**
- **Search Speed**: < 2 seconds for semantic queries
- **Classification**: ~1-2 seconds per file
- **Memory Usage**: ~2-3GB during active processing
- **System Reliability**: 99%+ uptime in testing

---

## 📋 **Current System Status (October 31, 2025)**

### **✅ Production Ready - Phase 1, 2 & 3a COMPLETE + Web Interface Improvements + Sprint 2.5:**
- **FastAPI V3 Backend** - All endpoints operational and verified
- **Modern React Web Interface** - Search, Triage, Organize, and Settings pages fully functional
- **Sprint 2.5: Learning Stats API & UI** - COMPLETE (November 3, 2025)
  - GET `/api/settings/learning-stats` endpoint with 10 key metrics
  - Dynamic Settings UI with learning statistics dashboard
  - Real-time media type breakdown and category distribution
  - 9/9 comprehensive tests passing (100% success rate)
- **Hierarchical Organization System** - 5-level deep folder structure operational
- **Search Page** - Full natural language semantic search with example queries
- **Triage Center** - Critical bug fixes (infinite spinner resolved, manual scan trigger)
- **Phase 1 Core Intelligence** - COMPLETE and independently verified (7,154 lines)
- **Phase 2a Computer Vision** - COMPLETE with Gemini Vision integration
- **Phase 2b Vision Integration** - COMPLETE with classifier/learning system
- **Phase 2c Audio Analysis** - COMPLETE with BPM, mood, spectral features (6/6 tests passing)
- **Phase 3a VEO Prompt Builder** - COMPLETE with video to VEO 3.1 JSON transformation
- **Universal Adaptive Learning** - Operational and learning from user behavior
- **4-Level Confidence System** - ADHD-friendly interaction modes active
- **Easy Rollback System** - Complete safety net integrated throughout
- **Google Drive Integration** - Hybrid cloud architecture operational
- **Emergency Space Protection** - Proactive disk management preventing crises

### **🎯 Recent Achievements:**

**November 3, 2025 - Sprint 2.5: Learning Stats API & UI Integration:**
- **Backend API**: GET `/api/settings/learning-stats` endpoint with 10 key metrics
- **Frontend Dashboard**: Dynamic Settings page with animated learning statistics
- **Comprehensive Testing**: 9/9 tests passing (100% success rate)
- **Real-time Metrics**: Total events, media type breakdown, category distribution, confidence scores
- **ADHD-Friendly UI**: Visual indicators, loading states, empty state handling

**October 31, 2025 - Web Interface Improvements:**
- **New Search Page**: Full-featured semantic search interface with natural language queries
- **Triage Bug Fixes**: Resolved infinite spinner from expensive auto-refresh, manual scan trigger
- **Hierarchical Organization**: Project → Episode → Media Type folder structure
- **API Improvements**: Updated classification endpoints with hierarchical parameters
- **Data Structure Fixes**: Resolved frontend/backend data format mismatches
- **Performance Optimization**: Scan results caching, no expensive auto-refreshes

### **🎬 Phase 3a Achievements (VEO Prompt Builder):**
- Video to VEO 3.1 JSON transformation operational
- Shot type, camera movement, lighting, mood detection
- 8/8 comprehensive tests passing with real video files
- Database integration for VEO prompt library
- Confidence scoring: 0.95 with full AI analysis

### **🔵 Next Steps:**
- Phase 3b: Batch VEO processing, continuity detection, web interface
- Enhanced hierarchical organization with project templates
- Mobile interface development (API ready)
- Team collaboration features (foundation exists)
- User testing and feedback collection

---

## 🤝 **Contributing & Support**

This is a specialized tool built for complex document workflows and ADHD accessibility.

**Questions or Issues:**
- [Open an issue](https://github.com/thebearwithabite/ai-file-organizer/issues)
- Email: [user@example.com](mailto:user@example.com)

**Development Priorities:**
- Enhanced entertainment industry templates
- Advanced content analysis
- Mobile companion app
- Team collaboration features

---

## 📜 **License**

MIT License - Built with ❤️ for creative minds and anyone managing complex content workflows with ADHD.

---

*From document chaos to intelligent organization. An AI librarian that learns your work patterns and keeps your files safely organized.*