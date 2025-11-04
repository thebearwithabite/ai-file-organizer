# API Documentation

AI File Organizer v3.2 - FastAPI REST API Reference

**Base URL**: `http://localhost:8000`

---

## Table of Contents

1. [System Health & Status](#system-health--status)
2. [Search & Discovery](#search--discovery)
3. [File Organization & Triage](#file-organization--triage)
4. [Settings & Learning System](#settings--learning-system)
5. [File Operations](#file-operations)
6. [Data Models](#data-models)
7. [Error Handling](#error-handling)

---

## System Health & Status

### Health Check

Check if the API server is running and operational.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy"
}
```

**Status Codes**:
- `200 OK`: Service is healthy

---

### System Status

Get real-time system statistics including file counts, database status, and Google Drive integration.

**Endpoint**: `GET /api/system/status`

**Response**:
```json
{
  "total_files_indexed": 1523,
  "google_drive_connected": true,
  "files_pending_review": 12,
  "storage_used_gb": 45.3,
  "last_scan": "2025-10-31T14:32:00Z",
  "confidence_mode": "smart",
  "database_status": "operational"
}
```

**Status Codes**:
- `200 OK`: Status retrieved successfully
- `500 Internal Server Error`: System error

---

## Search & Discovery

### Semantic Search

Search files using natural language queries with AI-powered semantic understanding.

**Endpoint**: `GET /api/search`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Natural language search query |
| `mode` | string | No | Search mode: `semantic`, `fast`, or `auto` (default: `auto`) |
| `limit` | integer | No | Maximum number of results (default: 20) |

**Example Requests**:
```bash
# Semantic search (AI understanding)
GET /api/search?q=Client Name%20contracts&mode=semantic

# Fast keyword search
GET /api/search?q=payment%20terms&mode=fast

# Auto mode (intelligent selection)
GET /api/search?q=creative%20project%20audio
```

**Response**:
```json
{
  "query": "Client Name contracts",
  "mode": "semantic",
  "results_count": 5,
  "results": [
    {
      "file_id": "abc123",
      "filename": "Client_Name_Management_Agreement_2024.pdf",
      "relevance_score": 0.94,
      "matching_content": "This agreement between Client Name and Management Company...",
      "file_category": "entertainment",
      "file_size": 2457600,
      "last_modified": "2024-09-15T10:30:00Z",
      "local_path": "/Users/user/GoogleDrive/AI_Organizer/01_ACTIVE_PROJECTS/Entertainment_Industry/Contracts/",
      "drive_path": "AI_Organizer/01_ACTIVE_PROJECTS/Entertainment_Industry/Contracts/",
      "availability": "local",
      "can_stream": true,
      "sync_status": "synced",
      "reasoning": [
        "Contract document for Client Name",
        "Entertainment industry management agreement",
        "High confidence match on client name and contract terms"
      ]
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Search successful
- `400 Bad Request`: Missing or invalid query parameter
- `500 Internal Server Error`: Search error

---

## File Organization & Triage

### Trigger Triage Scan

Manually trigger a scan for files that need review (low confidence classifications).

**Endpoint**: `GET /api/triage/scan`

**Response**:
```json
{
  "scan_timestamp": "2025-10-31T14:32:00Z",
  "files_found": 12,
  "files": [
    {
      "file_id": "xyz789",
      "file_name": "papers_that_dream_ep02_scene1.mp4",
      "file_path": "/Users/user/Downloads/papers_that_dream_ep02_scene1.mp4",
      "classification": {
        "category": "creative",
        "confidence": 0.72,
        "reasoning": "Video file related to creative project 'The Papers That Dream', episode 2 detected",
        "needs_review": true
      },
      "status": "pending_review"
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Scan completed successfully
- `500 Internal Server Error`: Scan failed

**Notes**:
- Results are cached in the backend
- No auto-refresh to prevent performance issues
- Returns files immediately instead of triggering background fetch

---

### Get Files for Review

Retrieve cached list of files pending manual review (from previous scan).

**Endpoint**: `GET /api/triage/files_to_review`

**Response**:
```json
{
  "files_count": 12,
  "files": [
    {
      "file_id": "xyz789",
      "file_name": "papers_that_dream_ep02_scene1.mp4",
      "file_path": "/Users/user/Downloads/papers_that_dream_ep02_scene1.mp4",
      "classification": {
        "category": "creative",
        "confidence": 0.72,
        "reasoning": "Video file related to creative project",
        "needs_review": true
      },
      "status": "pending_review"
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Files retrieved successfully
- `500 Internal Server Error`: Retrieval failed

**Notes**:
- Returns cached results from last `/api/triage/scan` call
- Does not trigger new scan
- Use `/api/triage/scan` to refresh the list

---

### Classify File

Confirm classification for a file and organize it with optional hierarchical structure.

**Endpoint**: `POST /api/triage/classify`

**Request Body**:
```json
{
  "file_path": "/Users/user/Downloads/papers_that_dream_ep02_scene1.mp4",
  "confirmed_category": "creative",
  "project": "The_Papers_That_Dream",
  "episode": "Episode_02"
}
```

**Request Schema** (`ClassificationRequest`):
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path` | string | Yes | Absolute path to file |
| `confirmed_category` | string | Yes | Category: `entertainment`, `financial`, `creative`, `development`, `audio`, `image`, `text_document` |
| `project` | string | No | Manual project name override (e.g., "The_Papers_That_Dream") |
| `episode` | string | No | Manual episode name override (e.g., "Episode_02") |

**Response**:
```json
{
  "success": true,
  "file_path": "/Users/user/Downloads/papers_that_dream_ep02_scene1.mp4",
  "destination_path": "/Users/user/GoogleDrive/AI_Organizer/01_ACTIVE_PROJECTS/Creative_Projects/The_Papers_That_Dream/Episode_02/Video/papers_that_dream_ep02_scene1.mp4",
  "hierarchical_metadata": {
    "project": "The_Papers_That_Dream",
    "episode": "Episode_02",
    "media_type": "Video",
    "hierarchy_level": 5,
    "reasoning": "Project detected: The_Papers_That_Dream | Episode detected: Episode_02 | Media type: Video | Organization depth: Level 5"
  },
  "operation_id": 12345,
  "rollback_available": true
}
```

**Status Codes**:
- `200 OK`: File classified and organized successfully
- `400 Bad Request`: Invalid request body or file path
- `404 Not Found`: File not found
- `500 Internal Server Error`: Classification failed

**Hierarchical Organization**:
The system creates a 5-level folder structure:
1. Base category (e.g., `01_ACTIVE_PROJECTS`)
2. Category type (e.g., `Creative_Projects`)
3. Project name (e.g., `The_Papers_That_Dream`)
4. Episode name (e.g., `Episode_02_AttentionIsland`)
5. Media type (e.g., `Video`, `Audio`, `Images`)

---

## Settings & Learning System

### Get Learning Statistics

Retrieve comprehensive statistics from the Universal Adaptive Learning System.

**Endpoint**: `GET /api/settings/learning-stats`

**Response**:
```json
{
  "total_learning_events": 1523,
  "image_events": 342,
  "video_events": 156,
  "audio_events": 89,
  "document_events": 936,
  "unique_categories_learned": 12,
  "most_common_category": "creative",
  "top_confidence_average": 0.87,
  "media_type_breakdown": {
    "images": 342,
    "videos": 156,
    "audio": 89,
    "documents": 936
  },
  "category_distribution": {
    "creative": 456,
    "entertainment": 287,
    "financial": 134,
    "development": 98,
    "audio": 89,
    "image": 342,
    "text_document": 117
  }
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `total_learning_events` | integer | Total number of learning events recorded |
| `image_events` | integer | Number of image classification learning events |
| `video_events` | integer | Number of video classification learning events |
| `audio_events` | integer | Number of audio classification learning events |
| `document_events` | integer | Number of document classification learning events |
| `unique_categories_learned` | integer | Number of distinct categories the system has learned |
| `most_common_category` | string | Most frequently learned category |
| `top_confidence_average` | number | Average confidence score across all learning events (0-1) |
| `media_type_breakdown` | object | Breakdown of events by media type |
| `category_distribution` | object | Distribution of events by category |

**Status Codes**:
- `200 OK`: Statistics retrieved successfully
- `500 Internal Server Error`: Failed to retrieve statistics

**Example Request**:
```bash
curl http://localhost:8000/api/settings/learning-stats
```

**Notes**:
- Returns statistics from `universal_adaptive_learning.py`
- Uses efficient Counter-based aggregation
- Handles empty database gracefully (returns zeros)
- Updated in real-time as system learns from user interactions
- Includes both media type and category breakdowns
- Confidence scores are averaged across all learning events

**Empty Database Response**:
```json
{
  "total_learning_events": 0,
  "image_events": 0,
  "video_events": 0,
  "audio_events": 0,
  "document_events": 0,
  "unique_categories_learned": 0,
  "most_common_category": "None",
  "top_confidence_average": 0.0,
  "media_type_breakdown": {
    "images": 0,
    "videos": 0,
    "audio": 0,
    "documents": 0
  },
  "category_distribution": {}
}
```

---

## File Operations

### Upload File

Upload a file for automatic classification and organization.

**Endpoint**: `POST /api/upload`

**Request**: `multipart/form-data`

**Form Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `file` | file | File to upload |

**Example**:
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/document.pdf"
```

**Response**:
```json
{
  "file_id": "hash123",
  "file_name": "document.pdf",
  "file_path": "/tmp/uploads/document.pdf",
  "classification": {
    "category": "text_document",
    "confidence": 0.88,
    "reasoning": "PDF document with business content",
    "needs_review": false
  },
  "status": "organized",
  "destination_path": "/Users/user/GoogleDrive/AI_Organizer/02_REFERENCE/Documents/document.pdf",
  "operation_id": 12346
}
```

**Status Codes**:
- `200 OK`: File uploaded and classified successfully
- `400 Bad Request`: No file provided or invalid file
- `500 Internal Server Error`: Upload or classification failed

---

### Open File

Open a file in the default application (macOS only).

**Endpoint**: `POST /api/open_file`

**Request Body**:
```json
{
  "file_path": "/Users/user/GoogleDrive/AI_Organizer/01_ACTIVE_PROJECTS/Creative_Projects/document.pdf"
}
```

**Response**:
```json
{
  "success": true,
  "message": "File opened successfully",
  "file_path": "/Users/user/GoogleDrive/AI_Organizer/01_ACTIVE_PROJECTS/Creative_Projects/document.pdf"
}
```

**Status Codes**:
- `200 OK`: File opened successfully
- `400 Bad Request`: Invalid file path
- `404 Not Found`: File not found
- `500 Internal Server Error`: Failed to open file

**Platform Support**:
- macOS: Uses `open` command
- Linux: Uses `xdg-open` command
- Windows: Uses `start` command

---

## Data Models

### TriageFile

```typescript
interface TriageFile {
  file_id: string              // Unique file identifier
  file_name: string            // Original filename
  file_path: string            // Absolute file path
  classification: {
    category: string           // AI-detected category
    confidence: number         // Confidence score (0-1)
    reasoning: string          // AI reasoning for classification
    needs_review: boolean      // True if confidence < 0.85
  }
  status: string              // "pending_review" | "organized" | "error"
}
```

### SearchResult

```typescript
interface SearchResult {
  file_id: string              // Unique file identifier
  filename: string             // Original filename
  relevance_score: number      // Semantic relevance (0-1)
  matching_content: string     // Excerpt of matching content
  file_category: string        // File category
  file_size: number           // Size in bytes
  last_modified: string       // ISO 8601 timestamp
  local_path: string          // Local file path
  drive_path: string          // Google Drive path
  availability: string        // "local" | "cloud" | "both"
  can_stream: boolean         // True if streamable from cloud
  sync_status: string         // "synced" | "syncing" | "offline"
  reasoning: string[]         // Array of reasoning strings
}
```

### ClassificationRequest

```typescript
interface ClassificationRequest {
  file_path: string           // Absolute file path (required)
  confirmed_category: string  // Category to classify as (required)
  project?: string           // Optional project name
  episode?: string           // Optional episode name
}
```

### HierarchicalMetadata

```typescript
interface HierarchicalMetadata {
  project: string | null      // Detected or manual project name
  episode: string | null      // Detected or manual episode name
  media_type: string         // Video | Audio | Images | Scripts | JSON_Prompts | Documents | Other
  hierarchy_level: number    // Depth of organization (2-5)
  reasoning: string          // Human-readable organization reasoning
}
```

### LearningStats

```typescript
interface LearningStats {
  total_learning_events: number           // Total number of learning events
  image_events: number                   // Image classification events
  video_events: number                   // Video classification events
  audio_events: number                   // Audio classification events
  document_events: number                // Document classification events
  unique_categories_learned: number      // Number of distinct categories
  most_common_category: string          // Most frequently learned category
  top_confidence_average: number        // Average confidence score (0-1)
  media_type_breakdown: {
    images: number
    videos: number
    audio: number
    documents: number
  }
  category_distribution: {
    [category: string]: number          // Category name to event count mapping
  }
}
```

---

## Error Handling

### Standard Error Response

All API errors follow this format:

```json
{
  "error": "Error type",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional context or validation errors"
  }
}
```

### Common Error Codes

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| `400 Bad Request` | Invalid request | Missing required fields, invalid parameters |
| `404 Not Found` | Resource not found | File path doesn't exist, invalid file ID |
| `500 Internal Server Error` | Server error | Database error, filesystem error, AI service error |

### Error Examples

**Missing Query Parameter**:
```json
{
  "error": "ValidationError",
  "message": "Query parameter 'q' is required for search",
  "details": {}
}
```

**File Not Found**:
```json
{
  "error": "FileNotFoundError",
  "message": "File not found at specified path",
  "details": {
    "file_path": "/invalid/path/file.pdf"
  }
}
```

**Classification Failed**:
```json
{
  "error": "ClassificationError",
  "message": "Failed to classify file due to AI service error",
  "details": {
    "ai_service": "Gemini Vision API timeout"
  }
}
```

---

## Rate Limiting

The API currently does not implement rate limiting, but future versions may include:

- **Gemini API**: Lazy initialization, rate limit handling built-in
- **Search queries**: No limits (local processing)
- **File operations**: No limits (local filesystem)

---

## Authentication

Currently, the API does not require authentication as it's designed for local use.

**Security Considerations**:
- API runs on `localhost:8000` by default
- Not exposed to external networks
- File operations restricted to user's filesystem
- No data leaves the local machine except Google Drive sync

---

## WebSocket Support

Not currently implemented. All communication is via REST API.

---

## API Versioning

Current version: **v3.2**

API versioning follows the main project version. Breaking changes will increment the major version.

---

## Support & Issues

- **Documentation**: [CLAUDE.md](CLAUDE.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Issues**: [GitHub Issues](https://github.com/thebearwithabite/ai-file-organizer/issues)

---

*Last Updated: November 3, 2025*
*Version: 3.2.1*
