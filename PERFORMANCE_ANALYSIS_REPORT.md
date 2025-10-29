# AI File Organizer - Performance Analysis Report

**Date:** 2025-10-28
**Issue:** System extremely slow on startup, "doesn't work" according to user
**Target:** Server startup in < 5 seconds, no auto-processing

---

## Critical Performance Bottlenecks Identified

### 1. TriageService Auto-Scanning Downloads Folder (CRITICAL)
**Location:** `api/services.py:194-274`

**Problem:**
- On every server startup, `TriageService.get_files_for_review()` is called
- Scans multiple staging areas: Downloads, Desktop, Manual_Review folders
- **Processing up to 20 files** through full AI classification pipeline
- Each file classification involves:
  - Content extraction
  - OpenAI API calls
  - Vision analysis (if image/video)
  - Audio analysis (if audio file)

**Evidence from logs:**
```
INFO: Scanning /Users/user/Downloads for files needing review
Uploading video _shot_id_ep3_co_shot7_202510281820 (2).mp4
Uploading video Multi-Head Attention Explained (2).mp4
```

**Impact:** 1-5 minutes of startup delay (depending on files in Downloads)

**Fix Required:**
- Disable automatic scanning on server startup
- Make scanning user-triggered via API endpoint (already exists: `/api/triage/files_to_review`)
- Move to background task queue for async processing

---

### 2. GoogleDriveLibrarian Initialization Scan (HIGH)
**Location:** `gdrive_librarian.py:233-276`

**Problem:**
```python
def initialize(self) -> bool:
    # Step 4: Initial Drive scan (lightweight)
    logger.info("   🔍 Performing initial Drive scan...")
    self._scan_drive_metadata()  # <-- BLOCKS STARTUP
```

**What it does:**
- Fetches 100 most recent files from Google Drive API
- Caches metadata for each file
- Happens on EVERY server startup

**Impact:** 5-30 seconds depending on API latency

**Fix Required:**
- Make Drive scan lazy (only on first search request)
- Or make it optional via `lazy_init=True` parameter
- Background task for refresh, not blocking startup

---

### 3. Vision Analysis Auto-Processing Large Videos (CRITICAL)
**Location:** `vision_analyzer.py` + `unified_classifier.py`

**Problem:**
- Videos in Downloads are being automatically uploaded to Gemini Vision API
- Large video files (10MB+) cause massive delays
- No file size checks before processing

**Evidence from logs:**
```
Uploading video _shot_id_ep3_co_shot7_202510281820 (2).mp4
Uploading video Multi-Head Attention Explained (2).mp4
```

**Impact:** 30 seconds - 5 minutes per video file

**Fix Required:**
- Add file size limit check (skip files > 10MB for auto-processing)
- Disable vision analysis for files in staging areas
- Only run vision analysis when user explicitly requests it

---

### 4. UnifiedClassificationService Initialization (MEDIUM)
**Location:** `unified_classifier.py:26-66`

**Problem:**
- Initializes multiple heavy components on import:
  - `ContentExtractor`
  - `AudioAnalyzer` (with OpenAI client)
  - `VisionAnalyzer` (with Gemini client)
  - `UniversalAdaptiveLearning` system
- All initialized even if not used

**Impact:** 2-5 seconds

**Fix Required:**
- Lazy initialization of analyzers (only create when needed)
- Singleton pattern to avoid multiple instances

---

### 5. Background Sync Service Auto-Start (MEDIUM)
**Location:** `gdrive_librarian.py:154-160`

**Problem:**
```python
if auto_sync:
    self.sync_service = BackgroundSyncService(...)
```

Currently `auto_sync=False` in `api/services.py:36`, but if enabled would cause:
- Continuous background Drive API calls
- File synchronization during startup

**Impact:** Not currently active, but potential issue

**Status:** Already disabled in code, but needs documentation

---

## Recommended Performance Optimizations

### Priority 1: Disable Auto-Scanning (IMMEDIATE)

**File:** `api/services.py`

**Change 1: Remove auto-scan from initialization**
```python
# api/services.py:165-193
class TriageService:
    def __init__(self):
        """Initialize TriageService with classification engine"""
        try:
            self.base_dir = get_ai_organizer_root()
            self.classifier = UnifiedClassificationService()
            self.staging_areas = [
                Path.home() / "Downloads",
                Path.home() / "Desktop",
                self.base_dir / "99_TEMP_PROCESSING" / "Downloads_Staging",
                self.base_dir / "99_TEMP_PROCESSING" / "Desktop_Staging",
                self.base_dir / "99_TEMP_PROCESSING" / "Manual_Review"
            ]

            # DO NOT auto-scan on initialization - let user trigger it
            logger.info("TriageService initialized (no auto-scan)")

        except Exception as e:
            logger.error(f"Failed to initialize TriageService: {e}")
            self.classifier = None
            self.staging_areas = []
            self.base_dir = None
```

**Change 2: Update frontend to trigger scan manually**
Frontend should call `/api/triage/trigger_scan` endpoint when user navigates to triage page.

---

### Priority 2: Lazy Google Drive Initialization

**File:** `api/services.py`

**Change:**
```python
# api/services.py:29-42
class SystemService:
    def __init__(self):
        """Initialize SystemService with lazy Google Drive loading"""
        if SystemService._librarian_instance is None:
            try:
                logger.info("Initializing GoogleDriveLibrarian (lazy mode)...")
                SystemService._librarian_instance = GoogleDriveLibrarian(
                    cache_size_gb=2.0,
                    auto_sync=False
                )
                # DO NOT call initialize() here - defer until first use
                logger.info("GoogleDriveLibrarian created (not initialized)")
            except Exception as e:
                SystemService._initialization_error = str(e)
                logger.error(f"Failed to create GoogleDriveLibrarian: {e}")
                SystemService._librarian_instance = None
```

**File:** `gdrive_librarian.py`

**Add lazy initialization method:**
```python
def initialize_lazy(self):
    """Initialize on first use, not at construction time"""
    if self._authenticated:
        return True  # Already initialized

    return self.initialize()
```

**Update search methods to call `initialize_lazy()` before use.**

---

### Priority 3: Add File Size Limits

**File:** `unified_classifier.py`

**Add file size check before vision analysis:**
```python
# unified_classifier.py:90-94
def classify_file(self, file_path: Path) -> Dict[str, Any]:
    file_path = Path(file_path)
    if not file_path.exists():
        return {"error": "File not found"}

    # SKIP large files to avoid performance issues
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    MAX_AUTO_PROCESS_SIZE_MB = 10

    if file_size_mb > MAX_AUTO_PROCESS_SIZE_MB:
        logger.info(f"Skipping {file_path.name} ({file_size_mb:.1f}MB) - too large for auto-processing")
        return {
            'category': 'unknown',
            'confidence': 0.0,
            'reasoning': [f'File too large ({file_size_mb:.1f}MB) for automatic processing'],
            'suggested_filename': file_path.name,
            'source': 'FileSize Check'
        }

    # Continue with normal classification...
    file_type = self._get_file_type(file_path)
    # ...
```

**File:** `api/services.py`

**Add file size check in triage service:**
```python
# api/services.py:226-230
try:
    file_stat = file_path.stat()
    file_size_mb = file_stat.st_size / (1024 * 1024)

    # Skip very large files to avoid processing delays
    if file_size_mb > 10:  # 10MB limit
        logger.info(f"Skipping {file_path.name} ({file_size_mb:.1f}MB) - too large")
        continue
```

---

### Priority 4: Lazy Analyzer Initialization

**File:** `unified_classifier.py`

**Change to lazy property pattern:**
```python
class UnifiedClassificationService:
    def __init__(self):
        """Initialize with minimal overhead"""
        print("Initializing Unified Classification Service (lazy mode)...")

        self.base_dir = Path(os.getcwd())

        # Don't initialize analyzers until needed
        self._audio_analyzer = None
        self._vision_analyzer = None
        self._text_analyzer = None
        self._learning_system = None

        print("Unified Classification Service Ready (lazy mode).")

    @property
    def audio_analyzer(self):
        """Lazy load audio analyzer on first use"""
        if self._audio_analyzer is None:
            openai_api_key = os.getenv('OPENAI_API_KEY')
            self._audio_analyzer = AudioAnalyzer(
                base_dir=str(self.base_dir),
                confidence_threshold=0.7,
                openai_api_key=openai_api_key
            )
        return self._audio_analyzer

    @property
    def vision_analyzer(self):
        """Lazy load vision analyzer on first use"""
        if self._vision_analyzer is None:
            try:
                self._vision_analyzer = VisionAnalyzer(base_dir=str(self.base_dir))
            except Exception as e:
                logger.error(f"Vision analyzer initialization failed: {e}")
        return self._vision_analyzer

    # Similar for other analyzers...
```

---

## Expected Performance Improvements

| Optimization | Current Time | Target Time | Improvement |
|--------------|--------------|-------------|-------------|
| Disable auto-scanning | 1-5 minutes | 0 seconds | 100% |
| Lazy Drive init | 5-30 seconds | 0 seconds | 100% |
| File size limits | 30s-5min (per video) | 0 seconds | 100% |
| Lazy analyzers | 2-5 seconds | 0.5 seconds | 70-90% |
| **TOTAL STARTUP** | **2-10 minutes** | **< 5 seconds** | **95%+** |

---

## Implementation Plan

### Phase 1: Emergency Fixes (Today)
1. Comment out auto-scanning in `TriageService.__init__()`
2. Add file size check before vision analysis (10MB limit)
3. Remove `initialize()` call from `SystemService.__init__()`

### Phase 2: Proper Architecture (This Week)
1. Implement lazy initialization pattern for all heavy components
2. Add background task queue for scanning operations
3. Update frontend to trigger scans explicitly
4. Add API endpoint for scan status

### Phase 3: Long-term Optimization (Future)
1. Implement Redis/Celery for background tasks
2. Add progress indicators for long-running operations
3. Implement caching layer for classification results
4. Add rate limiting for API calls

---

## Testing Protocol

### Before Optimizations:
```bash
time python main.py &
# Wait for server to start
curl http://localhost:8000/health
# Measure time to first successful response
```

### After Optimizations:
```bash
time python main.py &
# Should start in < 5 seconds
curl http://localhost:8000/health
# Should respond immediately
```

### Verify No Regression:
```bash
# Test search still works
curl "http://localhost:8000/api/search?q=test"

# Test manual triage scan
curl http://localhost:8000/api/triage/trigger_scan

# Verify Google Drive auth
curl http://localhost:8000/api/system/status
```

---

## ADHD-Friendly Design Principles Restored

1. **Instant feedback** - Server starts immediately
2. **Progressive disclosure** - Scan only when user needs it
3. **No surprises** - User explicitly triggers expensive operations
4. **Low cognitive load** - System doesn't "work in background" unexpectedly
5. **Trust through transparency** - User sees what's happening when

---

## Next Steps

1. Implement Priority 1 fixes immediately (disable auto-scanning)
2. Test with user's actual Downloads folder
3. Verify server startup < 5 seconds
4. User validates system is "working again"
5. Implement remaining optimizations incrementally

---

*Report generated by: Claude Code (Google Drive API Expert mode)*
*Issue tracker: User reports "crazy slow" and "doesn't work"*
*Target: Make system snappy and ADHD-friendly again*
