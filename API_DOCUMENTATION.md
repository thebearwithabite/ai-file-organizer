# AI File Organizer V3 API Documentation

## Overview

The AI File Organizer V3 is a **web-first** application built with FastAPI that provides both a beautiful web interface and a comprehensive REST API. The primary way to use the system is through the web interface at `http://localhost:8000`, which offers an intuitive, ADHD-friendly experience for file search and organization.

**Web Interface:** `http://localhost:8000` (Primary interface)  
**API Documentation:** `http://localhost:8000/docs` (For developers and automation)  
**Alternative API Docs:** `http://localhost:8000/redoc`

The API enables integration with custom tools, automation scripts, and third-party applications while maintaining the same design principles as the web interface.

## Design Philosophy

### ADHD-Friendly API Design
- **Natural Language**: Search with queries like "client contract terms"
 instead of complex syntax
- **Confidence-Based Filtering**: Only surface files that genuinely need
 attention
- **Predictable Patterns**: Consistent request/response formats reduce
cognitive load
- **Clear Error Messages**: Actionable feedback when things go wrong

### Enterprise Ready
- **FastAPI Framework**: Auto-generated docs, request validation, async
support
- **Service Architecture**: Clean separation between API layer and
business logic
- **Google Drive Integration**: Real-time data from 2TB hybrid cloud
storage
- **Comprehensive Logging**: Full audit trail for all operations

## Authentication

Currently, the API uses the existing Google Drive authentication
configured in the AI File Organizer system. No additional API keys
required for local development.

## Endpoints

### Basic Endpoints

#### `GET /`
Serves the main web interface.

**Response:**
Returns the HTML file for the AI File Organizer web interface. Open your browser to http://localhost:8000 to access the full web experience.

#### `GET /health`

Service health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "AI File Organizer API"
}
```

### System Status

#### `GET /api/system/status`

Get real-time system status from the AI File Organizer's
GoogleDriveLibrarian.

**Response:**
```json
{
  "indexed_files": 1247,
  "files_in_staging": 12,
  "last_run": "2025-09-10T18:00:00Z",
  "authentication_status": "authenticated",
  "google_drive_user": "user@example.com",
  "cache_size_mb": 1024.5,
  "sync_service_status": "active"
}
```

**Response Fields:**
- `indexed_files` (integer): Total files in the metadata store
- `files_in_staging` (integer): Files cached locally awaiting processing
- `last_run` (string): ISO timestamp of last Google Drive scan
- `authentication_status` (string): "authenticated" or "unauthenticated"
- `google_drive_user` (string): Email of authenticated Google Drive user
- `cache_size_mb` (number): Current cache size in megabytes
- `sync_service_status` (string): Status of background sync service

**Error Response:**
```json
{
  "status": "error",
  "message": "GoogleDriveLibrarian not initialized",
  "error": "Authentication failed",
  "indexed_files": 0,
  "files_in_staging": 0,
  "last_run": null
}
```

**`curl` Example:**
```bash
curl http://localhost:8000/api/system/status
```

### File Search

#### `GET /api/search`

Search files using the AI File Organizer's hybrid semantic search.

**Query Parameters:**
- `q` (required): Search query string (minimum 1 character)

**Example Request:**
```bash
curl "http://localhost:8000/api/search?q=client%20contract%20terms"
```

**Response:**
```json
{
  "query": "client contract terms",
  "results": [
    {
      "file_id": "1BxR7V8kF3J2Lp9Mz4N0Qw8E6Y5U1I7O3",
      "filename": "Client_Agreement_2024.pdf",
      "relevance_score": 0.92,
      "matching_content": "...exclusive representation terms for television and film projects...",
      "file_category": "contracts",
      "file_size": 2048576,
      "last_modified": "2024-09-01T10:30:00Z",
      "local_path": "/Users/user/Documents/Entertainment/Client_Agreement_2024.pdf",
      "drive_path": "/01_ACTIVE_PROJECTS/Entertainment_Industry/Client_Agreement_2024.pdf",
      "availability": "local_and_cloud",
      "can_stream": true,
      "sync_status": "synced",
      "reasoning": [
        "High keyword match for 'contract terms'",
        "Document category matches entertainment industry"
      ]
    }
  ],
  "count": 1
}
```

**Response Fields:**
- `query` (string): The search query that was executed
- `results` (array): Array of search result objects
- `count` (integer): Number of results returned

**Search Result Object:**
- `file_id` (string): Unique file identifier
- `filename` (string): Display name of the file
- `relevance_score` (float): Relevance score (0.0 to 1.0)
- `matching_content` (string): Excerpt showing why this file matched
- `file_category` (string): AI-determined category
- `file_size` (integer): File size in bytes
- `last_modified` (string): ISO timestamp of last modification
- `local_path` (string): Local filesystem path (if available)
- `drive_path` (string): Google Drive path
- `availability` (string): "local_only", "cloud_only", or "local_and_cloud"
- `can_stream` (boolean): Whether file can be streamed from cloud
- `sync_status` (string): Synchronization status
- `reasoning` (array): AI explanations for why this file was returned

**Error Responses:**

- **400 Bad Request** - Empty query:
  ```json
  {
    "detail": "Query parameter 'q' cannot be empty"
  }
  ```

- **500 Internal Server Error** - Search failure:
  ```json
  {
    "detail": "Search failed: GoogleDriveLibrarian not available"
  }
  ```

### File Triage

#### `GET /api/triage/files_to_review`

Get files that require manual review due to low confidence categorization.

**Response:**
```json
{
  "files": [
    {
      "file_path": "/Users/user/Documents/Entertainment/Client_Agreement_2024.pdf",
      "suggested_category": "contracts",
      "confidence": 0.65
    },
    {
      "file_path": "/Users/user/Downloads/Creative_Project_Episode_Script.docx",
      "suggested_category": "creative_projects",
      "confidence": 0.58
    }
  ],
  "count": 2,
  "message": "Found 2 files requiring review"
}
```

**Response Fields:**
- `files` (array): Array of files needing review
- `count` (integer): Number of files requiring review
- `message` (string): Human-readable summary

**File Review Object:**
- `file_path` (string): Full path to the file
- `suggested_category` (string): AI's best guess at category
- `confidence` (float): Confidence score (0.0 to 1.0, values under 0.85 need review)

**`curl` Example:**
```bash
curl http://localhost:8000/api/triage/files_to_review
```

#### `POST /api/triage/classify`

Classify a file with user-confirmed category.

**Request Body:**
```json
{
  "file_path": "/Users/user/Documents/Entertainment/Client_Agreement_2024.pdf",
  "confirmed_category": "contracts"
}
```

**Request Fields:**
- `file_path` (string, required): Full path to the file being classified
- `confirmed_category` (string, required): Category confirmed by the user

**Response:**
```json
{
  "status": "success",
  "message": "File '/Users/user/Documents/Entertainment/Client_Agreement_2024.pdf' classified as 'contracts'."
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Failed to classify file '/path/to/file.pdf': File not found"
}
```

**`curl` Example:**
```bash
curl -X POST "http://localhost:8000/api/triage/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/Users/user/Documents/Entertainment/Client_Agreement_2024.pdf",
    "confirmed_category": "contracts"
  }'
```

### File Operations

#### `POST /api/open-file`

Open a file using the operating system's default application.

**Request Body:**
```json
{
  "path": "/Users/user/Documents/Entertainment/Client_Agreement_2024.pdf"
}
```

**Request Fields:**
- `path` (string, required): Full path to the file to open

**Response:**
```json
{
  "success": true,
  "message": "Successfully opened file: Client_Agreement_2024.pdf",
  "path": "/Users/user/Documents/Entertainment/Client_Agreement_2024.pdf"
}
```

**Error Response:**
```json
{
  "detail": "Failed to open file: No such file or directory"
}
```

**`curl` Example:**
```bash
curl -X POST "http://localhost:8000/api/open-file" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/Users/user/Documents/Entertainment/Client_Agreement_2024.pdf"
  }'
```

## Error Handling

The API uses standard HTTP status codes:

- **200 OK**: Successful request
- **400 Bad Request**: Invalid request parameters
- **422 Unprocessable Entity**: Request validation failed (invalid JSON/missing required fields)
- **500 Internal Server Error**: Server-side error

Error responses follow this format:
```json
{
  "detail": "Error description"
}
```

For validation errors (422), the response includes field-specific details:
```json
{
  "detail": [
    {
      "loc": ["body", "file_path"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Integration Examples

### Python Client Example

```python
import requests

# Search for files
response = requests.get(
    "http://localhost:8000/api/search",
    params={"q": "client contracts"}
)
results = response.json()

# Get files needing review
response = requests.get("http://localhost:8000/api/triage/files_to_review")
files_to_review = response.json()

# Classify a file
response = requests.post(
    "http://localhost:8000/api/triage/classify",
    json={
        "file_path": "/path/to/file.pdf",
        "confirmed_category": "contracts"
    }
)
status = response.json()
```

### JavaScript/Web App Example

```javascript
// Search files
const searchFiles = async (query) => {
  const response = await fetch(
    `http://localhost:8000/api/search?q=${encodeURIComponent(query)}`
  );
  return response.json();
};

// Get system status
const getSystemStatus = async () => {
  const response = await fetch('http://localhost:8000/api/system/status');
  return response.json();
};

// Classify file
const classifyFile = async (filePath, category) => {
  const response = await fetch('http://localhost:8000/api/triage/classify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      file_path: filePath,
      confirmed_category: category
    })
  });
  return response.json();
};
```

## Performance & Scalability

### Response Times
- **System Status:** < 100ms (cached data)
- **File Search:** 200ms - 2s (depending on query complexity and result count)
- **Files to Review:** < 50ms (static data)
- **File Classification:** < 100ms (logging operation)

### Rate Limiting

Currently no rate limiting implemented. For production use, consider implementing rate limiting based on your usage patterns.

### Caching
- System status data is cached for improved performance
- Search results leverage the AI File Organizer's intelligent caching system
- `GoogleDriveLibrarian` instance is shared across all requests to avoid re-initialization

## Development Setup

### Prerequisites

```bash
# Install dependencies
pip install -r requirements_v3.txt
```

### Running the Server

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

The API inherits configuration from the AI File Organizer system:
- Google Drive authentication via existing token files
- Base directory configuration from `GoogleDriveIntegration`
- Logging configuration from service modules

## Troubleshooting

### Common Issues

- **`GoogleDriveLibrarian` not initialized**
  - Ensure Google Drive authentication is configured
  - Check that Google Drive is mounted and accessible
  - Verify network connectivity to Google Drive API

- **Search returns empty results**
  - Confirm files are indexed in the metadata store
  - Check search query spelling and syntax
  - Verify `GoogleDriveLibrarian` is properly initialized

- **File classification fails**
  - Ensure file path exists and is accessible
  - Check file permissions
  - Verify category name matches expected values

### Debug Mode

Set logging level to `DEBUG` for detailed request/response logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checking

Use the `/health` endpoint to verify the API is responding:
```bash
curl http://localhost:8000/health
```

## API Versioning

This is version 1.0.0 of the V3 API. Future versions will maintain backward compatibility where possible, with breaking changes indicated by major version increments.

## Support

For issues related to the AI File Organizer system itself, refer to the main project documentation. For API-specific questions, the interactive documentation at `/docs` provides additional details and allows for testing endpoints directly.
