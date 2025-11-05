# API Endpoints Reference

Complete REST API specification for all backend services.

## Architecture

**Strategy:** Wrap existing Python CLI tools with FastAPI services, **do NOT rewrite logic**.

```
backend/
├── main.py                    # FastAPI entry point
├── api/                       # API routes
│   ├── organize.py
│   ├── search.py
│   ├── analysis.py
│   ├── veo.py
│   ├── system.py
│   ├── rollback.py
│   ├── settings.py
│   ├── learning.py
│   └── deduplicate.py
└── services/                  # Python module wrappers
    ├── organizer_service.py   # Wraps interactive_organizer.py
    ├── classifier_service.py  # Wraps unified_classifier.py
    ├── vision_service.py      # Wraps vision_analyzer.py
    ├── audio_service.py       # Wraps audio_analyzer.py
    ├── veo_service.py         # Wraps veo_prompt_generator.py
    ├── rollback_service.py    # Wraps easy_rollback_system.py
    ├── learning_service.py    # Wraps universal_adaptive_learning.py
    ├── confidence_service.py  # Wraps confidence_system.py
    ├── space_service.py       # Wraps emergency_space_protection.py
    └── gdrive_service.py      # Wraps gdrive_integration.py
```

---

## 1. Organization APIs

### POST /api/organize/upload
Upload and classify a single file.

**Python CLI Equivalent:** `python interactive_organizer.py file "/path/to/file.pdf"`

**Request:**
```typescript
// multipart/form-data
file: File
```

**Response:**
```typescript
{
  file_id: string
  file_name: string
  classification: {
    category: string           // e.g., "Entertainment/Contracts/Management"
    confidence: number         // 0.0 - 1.0
    reasoning: string          // AI explanation
    needs_review: boolean      // true if confidence < threshold
  }
  status: "organized" | "pending_review"
  destination_path?: string   // if organized
  operation_id?: number        // for rollback
}
```

**Implementation:**
```python
# backend/api/organize.py
from fastapi import APIRouter, UploadFile
from services.organizer_service import OrganizerService

router = APIRouter(prefix="/api/organize")

@router.post("/upload")
async def upload_file(file: UploadFile):
    service = OrganizerService()
    result = await service.classify_and_organize(file)
    return result
```

---

### POST /api/organize/batch
Batch process multiple files from a folder.

**Python CLI Equivalent:** `python interactive_batch_processor.py process /path`

**Request:**
```typescript
{
  folder_path: string
  mode: "preview" | "execute"
}
```

**Response:**
```typescript
{
  batch_id: string
  total_files: number
  processed: number
  pending_review: number
  status: "processing" | "complete"
  files: Array<{
    file_name: string
    status: "organized" | "pending_review" | "error"
    classification?: Classification
    error?: string
  }>
}
```

---

### POST /api/organize/confirm
Confirm classification for a pending file.

**Request:**
```typescript
{
  file_id: string
  confirmed_category: string
}
```

**Response:**
```typescript
{
  success: boolean
  destination_path: string
  operation_id: number      // for rollback
}
```

---

### POST /api/organize/reclassify
Re-classify a file with user-provided category.

**Request:**
```typescript
{
  file_id: string
  new_category: string
  user_feedback?: string    // optional notes
}
```

---

## 2. Search APIs

### GET /api/search
Unified search across files, emails, and VEO clips.

**Python CLI Equivalent:** `python enhanced_librarian.py search "query" --mode auto`

**Request:**
```typescript
GET /api/search?q=finn%20contracts&mode=auto&filter[category]=contracts&filter[date_from]=2024-01-01&limit=50
```

**Query Parameters:**
- `q`: search query (required)
- `mode`: `fast` | `semantic` | `auto` (default: `auto`)
- `filter[category]`: category filter (optional)
- `filter[file_type]`: file type filter (optional)
- `filter[date_from]`: start date (optional)
- `filter[date_to]`: end date (optional)
- `filter[location]`: `local` | `cloud` | `all` (default: `all`)
- `limit`: max results (default: 50)

**Response:**
```typescript
{
  query: string
  mode_used: "fast" | "semantic"
  total_results: number
  results: Array<{
    type: "file" | "email" | "veo_clip"
    id: string
    title: string
    path: string
    snippet: string           // matched content preview
    relevance_score: number   // 0.0 - 1.0
    metadata: {
      date: string
      size?: number
      category?: string
      // type-specific fields
    }
  }>
}
```

---

## 3. Analysis APIs

### POST /api/analysis/vision
Analyze image or video with Gemini Vision.

**Python CLI Equivalent:** `python vision_analyzer.py analyze file.jpg`

**Request:**
```typescript
// multipart/form-data
file: File
analysis_type?: "full" | "quick" | "veo"
```

**Response:**
```typescript
{
  analysis_id: string
  file_name: string
  content_type: "screenshot" | "photo" | "video" | "design" | "creative"
  description: string        // Gemini Vision output
  confidence: number
  metadata: {
    detected_objects?: string[]
    scene_type?: string
    mood?: string
    // image-specific fields
  }
  suggested_category: string
}
```

**Implementation Wraps:** `vision_analyzer.py:analyze_for_veo_prompt()` or `analyze()`

---

### POST /api/analysis/audio
Analyze audio file (BPM, mood, spectral features).

**Python CLI Equivalent:** `python audio_analyzer.py analyze file.mp3`

**Request:**
```typescript
// multipart/form-data
file: File
```

**Response:**
```typescript
{
  analysis_id: string
  file_name: string
  bpm: number
  mood: string              // "contemplative", "energetic", etc.
  energy_level: number      // 1-10
  brightness: number        // 1-10
  spectral_features: {
    texture: string
    harmonic_content: string
  }
  suggested_category: string
  confidence: number
}
```

**Implementation Wraps:** `audio_analyzer.py:analyze_audio()`

---

### GET /api/analysis/results
List all analysis results.

**Request:**
```typescript
GET /api/analysis/results?type=vision&limit=50&offset=0
```

**Query Parameters:**
- `type`: `vision` | `audio` | `all` (default: `all`)
- `limit`: max results (default: 50)
- `offset`: pagination offset (default: 0)

---

## 4. VEO APIs

### POST /api/veo/generate
Generate VEO 3.1 JSON from video clip.

**Python CLI Equivalent:** `python veo_prompt_generator.py video.mp4`

**Request:**
```typescript
// multipart/form-data
file: File  // video file
```

**Response:**
```typescript
{
  clip_id: number
  shot_id: string
  veo_json: VeoSchema       // Full VEO 3.1 schema
  confidence_score: number
  file_path: string
  json_file_path: string    // path to saved JSON
}
```

**Implementation Wraps:** `veo_prompt_generator.py:generate_veo_prompt()`

---

### POST /api/veo/batch
Batch process multiple videos.

**Request:**
```typescript
{
  folder_path: string
}
```

**Response:**
```typescript
{
  batch_id: string
  total_videos: number
  processed: number
  status: "processing" | "complete"
  clips: Array<{
    video_name: string
    status: "success" | "error"
    clip_id?: number
    error?: string
  }>
}
```

---

### GET /api/veo/clips
List all VEO clips (existing endpoint).

**Response:**
```typescript
Array<{
  id: number
  file_path: string
  shot_id: string
  confidence_score: number
  mood?: string
  lighting_type?: string
}>
```

---

### GET /api/veo/clip/:id
Get full VEO JSON for a clip (existing endpoint).

**Response:**
```typescript
VeoSchema  // Full VEO 3.1 JSON
```

---

### POST /api/veo/clip/:id/update
Save edited VEO JSON (existing endpoint).

**Request:**
```typescript
VeoSchema  // Modified VEO JSON
```

---

### POST /api/veo/clip/:id/reanalyze
Trigger Gemini Vision re-analysis (existing placeholder).

**Response:**
```typescript
{
  status: "queued"
  clip_id: number
}
```

---

### GET /api/veo/manifest/:project
Get continuity data for project (existing endpoint).

**Response:**
```typescript
{
  project_name: string
  clips: Array<{shot_id: string, ...}>
  continuity: Array<{
    source: string   // shot_id
    target: string   // shot_id
    score: number    // 0.0 - 1.0 continuity score
  }>
}
```

---

## 5. Rollback APIs

### GET /api/rollback/operations
List file operations with filters.

**Python CLI Equivalent:** `python easy_rollback_system.py --list`

**Request:**
```typescript
GET /api/rollback/operations?date_from=2024-10-29&limit=50&search=contract
```

**Query Parameters:**
- `date_from`: filter by date (default: all time)
- `date_to`: end date filter
- `limit`: max results (default: 50)
- `offset`: pagination
- `search`: search in filenames

**Response:**
```typescript
{
  total_operations: number
  operations: Array<{
    operation_id: number
    timestamp: string
    operation_type: "organize" | "batch" | "delete" | "move"
    file_count: number
    files: Array<{
      original_path: string
      new_path: string
      filename: string
    }>
    can_undo: boolean
  }>
}
```

**Implementation Wraps:** `easy_rollback_system.py:list_operations()`

---

### POST /api/rollback/undo/:operation_id
Undo a specific operation.

**Python CLI Equivalent:** `python easy_rollback_system.py --undo 123`

**Response:**
```typescript
{
  success: boolean
  operation_id: number
  files_restored: number
  message: string
}
```

**Implementation Wraps:** `easy_rollback_system.py:undo_operation(operation_id)`

---

### POST /api/rollback/undo-today
Emergency: undo all today's operations.

**Python CLI Equivalent:** `python easy_rollback_system.py --undo-today`

**Response:**
```typescript
{
  success: boolean
  operations_undone: number
  files_restored: number
  message: string
}
```

---

## 6. Settings APIs

### GET /api/settings/confidence
Get current confidence mode.

**Python CLI Equivalent:** `python confidence_system.py status`

**Response:**
```typescript
{
  current_mode: "never" | "minimal" | "smart" | "always"
  threshold_percentage: number  // 0, 40, 70, or 100
  statistics: {
    files_processed_today: number
    questions_asked_today: number
    auto_organized_today: number
  }
}
```

---

### POST /api/settings/confidence
Set confidence mode.

**Python CLI Equivalent:** `python confidence_system.py set smart`

**Request:**
```typescript
{
  mode: "never" | "minimal" | "smart" | "always"
}
```

**Response:**
```typescript
{
  success: boolean
  new_mode: string
  threshold_percentage: number
}
```

**Implementation Wraps:** `confidence_system.py:set_mode(mode)`

---

### GET /api/settings/gdrive
Get Google Drive status.

**Python CLI Equivalent:** `python gdrive_integration.py`

**Response:**
```typescript
{
  connected: boolean
  last_sync: string          // ISO timestamp
  storage_used: number       // bytes
  storage_total: number      // bytes
  sync_status: "synced" | "syncing" | "paused" | "error"
  error_message?: string
}
```

---

### POST /api/settings/gdrive/reconnect
Trigger OAuth reconnect.

**Response:**
```typescript
{
  auth_url: string           // OAuth URL to redirect user to
}
```

---

### POST /api/settings/gdrive/pause
Pause sync temporarily.

---

### POST /api/settings/gdrive/resume
Resume sync.

---

### GET /api/settings/space
Get disk space status.

**Python CLI Equivalent:** `python emergency_space_protection.py status`

**Response:**
```typescript
{
  free_space_gb: number
  total_space_gb: number
  warning_threshold_gb: number
  status: "safe" | "warning" | "critical"
  emergency_staging_enabled: boolean
  history: Array<{
    timestamp: string
    event_type: "warning" | "emergency_staging"
    free_space_gb: number
  }>
}
```

**Implementation Wraps:** `emergency_space_protection.py:get_status()`

---

### POST /api/settings/space/threshold
Update warning threshold.

**Request:**
```typescript
{
  threshold_gb: number
}
```

---

### GET /api/settings/services
List background services status.

**Response:**
```typescript
{
  services: Array<{
    name: "adaptive_monitor" | "staging_monitor" | "drive_sync"
    status: "running" | "stopped" | "error"
    uptime_seconds?: number
    last_activity?: string
    error_message?: string
  }>
}
```

---

### POST /api/settings/services/:name/restart
Restart a specific background service.

---

### POST /api/settings/services/restart-all
Restart all background services.

---

### GET /api/settings/services/:name/logs
Get recent logs for a service.

**Response:**
```typescript
{
  service_name: string
  logs: Array<{
    timestamp: string
    level: "info" | "warning" | "error"
    message: string
  }>
}
```

---

## 7. Learning APIs

### GET /api/learning/stats
Get adaptive learning statistics.

**Python CLI Equivalent:** `python universal_adaptive_learning.py status`

**Response:**
```typescript
{
  total_classifications: number
  user_corrections: number
  patterns_learned: number
  accuracy_improvement: number  // percentage
  top_categories: Array<{
    category: string
    count: number
    average_confidence: number
  }>
}
```

**Implementation Wraps:** `universal_adaptive_learning.py:get_current_summary()`

---

### GET /api/learning/patterns
List learned patterns.

**Python CLI Equivalent:** `python universal_adaptive_learning.py patterns`

**Response:**
```typescript
{
  patterns: Array<{
    pattern_id: string
    description: string      // e.g., "Files mentioning 'Finn' + 'contract'"
    category: string
    confidence: number
    usage_count: number
    last_used: string
  }>
}
```

---

### POST /api/learning/export
Download learning data.

**Python CLI Equivalent:** `python universal_adaptive_learning.py export`

**Response:**
```typescript
// File download (.pkl or .json)
```

---

### POST /api/learning/import
Upload learning data.

**Request:**
```typescript
// multipart/form-data
file: File  // .pkl or .json
```

---

### POST /api/learning/reset
Clear all learning data (dangerous).

**Request:**
```typescript
{
  confirm: boolean
}
```

---

## 8. Deduplication APIs

### POST /api/dedup/scan
Scan for duplicate files.

**Python CLI Equivalent:** `python automated_deduplication_service.py scan`

**Response:**
```typescript
{
  scan_id: string
  status: "scanning" | "complete"
  files_scanned: number
  duplicate_groups: Array<{
    hash: string
    files: Array<{
      path: string
      size: number
      modified: string
    }>
    total_size: number
  }>
  potential_space_saved: number  // bytes
}
```

**Implementation Wraps:** `automated_deduplication_service.py:scan_for_duplicates()`

---

### POST /api/dedup/clean
Remove selected duplicates.

**Python CLI Equivalent:** `python automated_deduplication_service.py clean`

**Request:**
```typescript
{
  duplicate_groups: Array<{
    hash: string
    files_to_keep: string[]    // paths
    files_to_remove: string[]  // paths
  }>
}
```

**Response:**
```typescript
{
  success: boolean
  files_removed: number
  space_freed: number          // bytes
  operation_id: number         // for rollback
}
```

---

### GET /api/dedup/stats
Get deduplication statistics.

**Python CLI Equivalent:** `python automated_deduplication_service.py stats`

**Response:**
```typescript
{
  total_scans: number
  duplicates_removed: number
  space_freed_total: number    // bytes
  last_scan: string
}
```

---

## 9. System APIs

### GET /api/system/status
Get overall system status (existing, may enhance).

**Response:**
```typescript
{
  google_drive: {
    connected: boolean
    sync_status: string
  }
  disk_space: {
    free_gb: number
    status: "safe" | "warning" | "critical"
  }
  background_services: {
    adaptive_monitor: "running" | "stopped"
    staging_monitor: "running" | "stopped"
    drive_sync: "running" | "stopped"
  }
  learning: {
    patterns_count: number
    classifications_today: number
  }
  confidence_mode: "never" | "minimal" | "smart" | "always"
}
```

---

## Implementation Example

```python
# backend/services/organizer_service.py
from interactive_organizer import InteractiveOrganizer
from unified_classifier import UnifiedClassifier
from easy_rollback_system import EasyRollbackSystem

class OrganizerService:
    """Wraps existing CLI tools for API use."""

    def __init__(self):
        self.organizer = InteractiveOrganizer()
        self.classifier = UnifiedClassifier()
        self.rollback = EasyRollbackSystem()

    async def classify_and_organize(self, file_path: str):
        """Classify and optionally organize a file."""
        # 1. Classify
        result = await self.classifier.classify(file_path)

        # 2. Check confidence threshold
        if result['confidence'] >= self.get_threshold():
            # Auto-organize
            new_path = await self.organizer.organize(
                file_path,
                result['category']
            )
            # Log for rollback
            operation_id = self.rollback.log_operation(
                original_path=file_path,
                new_path=new_path,
                operation_type='organize'
            )
            return {
                'status': 'organized',
                'destination_path': new_path,
                'operation_id': operation_id,
                'classification': result
            }
        else:
            # Needs user review
            return {
                'status': 'pending_review',
                'classification': result
            }
```

---

## Error Handling

All endpoints should return consistent error format:

```typescript
{
  error: {
    code: string              // "FILE_NOT_FOUND", "INSUFFICIENT_SPACE", etc.
    message: string           // Human-readable error
    details?: any             // Optional debug info
    suggested_action?: string // What user should do
  }
}
```

**HTTP Status Codes:**
- 200: Success
- 400: Bad request (invalid parameters)
- 404: Resource not found
- 409: Conflict (e.g., file already exists)
- 500: Internal server error
- 503: Service unavailable (e.g., Google Drive disconnected)

---

## CORS Configuration

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

*Last Updated: 2025-10-29*
*Version: 1.0*
