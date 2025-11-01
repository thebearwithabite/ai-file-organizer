# Changelog

All notable changes to the AI File Organizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2025-10-31

### Added - Hierarchical Organization System

- **hierarchical_organizer.py**: New 5-level deep folder structure system
  - Automatic project detection from filenames (e.g., "The_Papers_That_Dream")
  - Automatic episode detection (e.g., "Episode_02_AttentionIsland")
  - Media type classification (Video, Audio, Images, Scripts, JSON_Prompts)
  - Folder structure: `01_ACTIVE_PROJECTS/Creative_Projects/Project/Episode/MediaType/`
  - Known projects database with pattern matching
  - Manual override support via API

### Added - Search Page

- **frontend_v2/src/pages/Search.tsx**: Full-featured semantic search interface
  - Natural language query input with example suggestions
  - Relevance scoring with visual indicators
  - File metadata display (size, date, category)
  - "Why this matches" reasoning display
  - One-click file opening and path copying
  - Integration with GoogleDriveLibrarian backend
  - Support for both local and Google Drive files

### Fixed - Triage Page Critical Bugs

- **Infinite Spinner Issue**: Removed expensive 10-second auto-refresh on page load
  - Changed to manual scan trigger only (Scan Now button)
  - Eliminated performance lag from constant background fetching
- **Data Structure Mismatch**: Fixed inconsistency between frontend TypeScript and backend Python
  - Backend now returns proper `TriageFile` format with nested `classification` object
  - Frontend expects: `{ classification: { category, confidence, reasoning, needs_review } }`
  - Previously was flat structure causing undefined errors
- **Scan Results Caching**: Scan results are now cached instead of refetching
  - `/api/triage/scan` returns files immediately
  - `/api/triage/files_to_review` serves cached results
  - Prevents unnecessary repeated scans

### Added - Hierarchical Organization in UI

- **Triage.tsx**: Added optional project and episode input fields
  - User can manually specify project name (e.g., "The_Papers_That_Dream")
  - User can manually specify episode name (e.g., "Episode_02")
  - Inputs integrate with hierarchical_organizer.py
- **ClassificationPreview.tsx**: Real-time hierarchical path display
  - Shows complete destination path with project/episode/media type
  - Visual hierarchy level indicator
- **Organize.tsx**: Hierarchical organization support in drag-and-drop interface

### Changed - API Endpoints

- **ClassificationRequest Model**: Added optional fields
  - `project: Optional[str] = None` - Manual project override
  - `episode: Optional[str] = None` - Manual episode override
- **POST /api/triage/classify**: Now accepts hierarchical parameters
  ```json
  {
    "file_path": "/path/to/file.mp4",
    "confirmed_category": "creative",
    "project": "The_Papers_That_Dream",
    "episode": "Episode_02"
  }
  ```
- **TriageService.classify_file()**: Modified to support hierarchical paths
  - Calls `hierarchical_organizer.build_hierarchical_path()`
  - Returns complete 5-level path structure

### Changed - Frontend Performance

- **Removed Auto-Refresh**: Triage page no longer auto-fetches on mount
  - `enabled: false` in useQuery for triage-files
  - Manual trigger only via Scan Now button
- **Optimized Data Flow**: Single source of truth for scan results
  - Scan mutation updates query cache directly
  - No redundant API calls

### Documentation

- **CLAUDE.md**: Updated with hierarchical organization system documentation
- **CLAUDE.md**: Added Web Interface Updates section with bug fixes
- **CLAUDE.md**: Updated API endpoints documentation
- **README.md**: Updated production ready systems list
- **README.md**: Updated current system status to v3.2

---

## [3.1.0] - 2025-10-28

### Added - Phase 3a: VEO Prompt Builder (MVP)

- **veo_prompt_generator.py**: Transform video clips into VEO 3.1 JSON descriptions
  - ffprobe integration for video metadata extraction
  - Shot ID generation with unique hashing
  - Database storage in veo_prompts table
  - JSON file output: `<clip_name>_veo.json`
- **vision_analyzer.py**: New `analyze_for_veo_prompt()` method
  - Shot type detection (Extreme Wide → Extreme Close-up)
  - Camera movement recognition (Static, Pan, Tilt, Dolly, etc.)
  - Lighting classification (Natural, Dramatic, Golden Hour, etc.)
  - Mood and atmosphere analysis
  - Character detection (gender, age, behavior, expression)
  - Scene context extraction from Gemini Vision
  - Audio ambience suggestions
- **VEO Database Schema**: veo_prompts table
  - Searchable by shot type, camera movement, lighting, mood
  - Confidence scoring for analysis quality
  - Timestamps for tracking and validation

### Test Results

- 8/8 comprehensive tests passing
- Real video processing: 3 test clips analyzed successfully
- Confidence scores: 0.95 with full AI analysis
- Processing time: ~15-30 seconds per video
- VEO 3.1 schema compliance validated

---

## [3.0.0] - 2025-10-25

### Added - Phase 2c: Audio Analysis Pipeline

- **audio_analyzer.py**: Comprehensive audio content analysis
  - BPM detection using librosa
  - Mood analysis (energy, brightness, texture)
  - Spectral feature extraction
  - Integration with unified_classifier and adaptive learning
  - 6/6 tests passing with real audio files

### Added - Phase 2b: Vision Integration

- Seamless integration with unified_classifier.py
- Visual pattern learning in universal_adaptive_learning.py
- Works with 4-level confidence system
- Rollback safety for vision-based operations
- Background monitoring of image/video files

### Added - Phase 2a: Vision Analyzer Foundation

- **vision_analyzer.py**: Gemini Vision API integration
  - Image/video content analysis
  - Detects content type (screenshot, photo, video, design, creative)
  - Entertainment industry context understanding
  - Client/project recognition in visual content
  - Confidence scoring for visual classifications

---

## [2.0.0] - 2025-10-24

### Added - Phase 1 Core Intelligence (7,154 lines)

Revolutionary adaptive learning system that learns from file movements and decisions.

#### Universal Adaptive Learning System
- **universal_adaptive_learning.py** (1,087 lines)
  - Learns from all user interactions and corrections
  - Builds pattern recognition across all file types
  - Stores learning data in pickle format for persistence
  - Discovers new categories dynamically based on user behavior

#### 4-Level ADHD-Friendly Confidence System
- **confidence_system.py** (892 lines)
  - NEVER mode (0%): Fully automatic, no questions
  - MINIMAL mode (40%): Only ask about very uncertain files
  - SMART mode (70%): Balanced operation, default for ADHD users
  - ALWAYS mode (100%): Human review for every file

#### Adaptive Background Monitor
- **adaptive_background_monitor.py** (1,456 lines)
  - Observes manual file movements in real-time
  - Learns organizational patterns from user behavior
  - Improves classification confidence over time
  - Runs continuously in background without cognitive load

#### Emergency Space Protection
- **emergency_space_protection.py** (987 lines)
  - Proactive disk space monitoring
  - Prevents "disk full" crises before they happen
  - Automatic emergency staging when space runs low
  - ADHD-friendly: eliminates panic moments from sudden space issues

#### Interactive Batch Processor
- **interactive_batch_processor.py** (1,529 lines)
  - Handles multiple files with content preview
  - ADHD-friendly interaction modes
  - Dry-run mode for safe testing
  - Integrated with confidence system for smart decisions

#### Automated Deduplication Service
- **automated_deduplication_service.py** (1,203 lines)
  - SHA-256 based duplicate detection
  - Rollback safety for all duplicate operations
  - Learning system integration
  - Prevents ADHD paralysis from duplicate files

### Verification Status

- All 6 components implemented and tested
- Independent verification completed
- All imports and integrations tested
- CLI commands validated and corrected
- Database initialization verified
- Directory structure confirmed
- Production-ready for daily use

---

## [1.0.0] - 2025-10-01

### Initial Release

- FastAPI V3 backend with web server
- Web interface with triage center
- Easy rollback system for file operations
- Google Drive hybrid integration
- Semantic search with ChromaDB
- Content-based classification
- Email integration (.emlx files)
- macOS AppleScript GUI

---

## Versioning Strategy

- **Major version (X.0.0)**: Phase completions, breaking changes
- **Minor version (0.X.0)**: New features, significant improvements
- **Patch version (0.0.X)**: Bug fixes, minor improvements

## Links

- [Repository](https://github.com/thebearwithabite/ai-file-organizer)
- [Documentation](CLAUDE.md)
- [Issues](https://github.com/thebearwithabite/ai-file-organizer/issues)
