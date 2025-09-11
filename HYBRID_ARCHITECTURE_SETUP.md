# Hybrid Architecture Setup Guide
**AI File Organizer v3.0 - Complete Google Drive + Local Integration**

## Overview

The hybrid architecture provides seamless integration between local file management and Google Drive cloud storage, offering:

- **On-demand file streaming** from Google Drive
- **Intelligent caching** with smart eviction policies
- **Background synchronization** with conflict resolution
- **Unified search** across local and cloud files
- **ADHD-friendly** progressive disclosure and simple interactions

## Quick Start

### 1. Install Dependencies

```bash
# Install cloud requirements
pip install -r requirements_cloud.txt

# Or install individual packages
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install sentence-transformers chromadb
pip install requests numpy python-dateutil tqdm colorama
```

### 2. Google Drive API Setup

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create/Select Project**: Create new project or select existing
3. **Enable Google Drive API**:
   - Go to "APIs & Services" > "Library"
   - Search "Google Drive API" and enable it
4. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Choose "Desktop Application"
   - Download the JSON file
5. **Save Credentials**: Save as `gdrive_credentials.json` in project root

### 3. Quick Test

```bash
# Test authentication and basic functionality
python test_hybrid_architecture.py --quick

# Test only authentication
python test_hybrid_architecture.py --auth-only
```

### 4. Initialize System

```python
from gdrive_librarian import GoogleDriveLibrarian

# Initialize the complete system
librarian = GoogleDriveLibrarian(
    cache_size_gb=5.0,      # Adjust based on available space
    auto_sync=True,         # Enable background sync
    sync_interval=300       # Sync every 5 minutes
)

# Initialize all components
if librarian.initialize():
    print("✅ Hybrid architecture ready!")
    
    # Search across local and cloud
    results = librarian.search("contract documents")
    
    # Get file content (streams from cloud if needed)
    content = librarian.get_file_content(results[0].file_id)
```

## Architecture Components

### Core Components

```
📁 Hybrid Architecture/
├── 🔐 google_drive_auth.py          # OAuth 2.0 authentication
├── 📊 local_metadata_store.py       # Local file metadata database
├── 🌊 gdrive_streamer.py           # On-demand file streaming
├── 🔄 background_sync_service.py   # Continuous synchronization
├── 🔍 gdrive_librarian.py          # Complete search system
└── 📁 gdrive_integration.py        # Drive folder structure
```

### Key Features

1. **Authentication (`google_drive_auth.py`)**
   - OAuth 2.0 flow with automatic token refresh
   - Secure credential storage
   - Comprehensive error handling

2. **File Streaming (`gdrive_streamer.py`)**
   - Chunked downloads for large files
   - Smart caching with usage-based scoring
   - Memory-efficient streaming
   - ADHD-friendly progress indicators

3. **Background Sync (`background_sync_service.py`)**
   - Continuous metadata synchronization
   - Intelligent conflict resolution
   - Change detection and propagation
   - Minimal user interruption

4. **Unified Search (`gdrive_librarian.py`)**
   - Search across local and cloud files
   - Automatic scope selection
   - Real-time availability status
   - Semantic and keyword search

## Configuration

### Default Configuration

The system creates a configuration file at `~/.ai_organizer_config/librarian_config.json`:

```json
{
  "search_preferences": {
    "default_scope": "hybrid",
    "max_results": 50,
    "enable_semantic_search": true,
    "auto_download_threshold_mb": 10
  },
  "sync_preferences": {
    "conflict_resolution": "newer_wins",
    "auto_resolve_conflicts": true,
    "sync_file_types": [
      "application/pdf",
      "text/",
      "application/vnd.openxmlformats-officedocument"
    ]
  },
  "adhd_features": {
    "progressive_disclosure": true,
    "simple_questions": true,
    "immediate_feedback": true,
    "confidence_threshold": 85
  }
}
```

### Customization

```python
# Custom configuration
librarian = GoogleDriveLibrarian(
    cache_size_gb=2.0,                    # Smaller cache
    auto_sync=False,                      # Manual sync only
    sync_interval=600                     # 10-minute intervals
)

# Update configuration
librarian.config['adhd_features']['confidence_threshold'] = 90
```

## Usage Examples

### Search Operations

```python
from gdrive_librarian import GoogleDriveLibrarian, SearchScope

librarian = GoogleDriveLibrarian()
librarian.initialize()

# Automatic scope selection
results = librarian.search("Client Name contracts")

# Specific scope search
results = librarian.search(
    "Creative Project episodes", 
    scope=SearchScope.CLOUD_ONLY,
    limit=10
)

# Filtered search
results = librarian.search(
    "meeting notes",
    file_types=['pdf', 'docx'],
    date_range=(datetime(2024, 1, 1), datetime.now())
)
```

### File Access

```python
# Get file content (auto-streams if needed)
content = librarian.get_file_content("drive_file_id")

# Ensure file is available locally
local_path = librarian.ensure_file_available("drive_file_id")

# Check file availability
for result in results:
    print(f"{result.filename}: {result.availability.value}")
    if result.availability == FileAvailability.DOWNLOADING:
        print(f"  Progress: {result.download_progress}%")
```

### System Monitoring

```python
# Get comprehensive system status
status = librarian.get_system_status()

print(f"Authenticated: {status['authenticated']}")
print(f"Cache: {status['components']['cache']['files_cached']} files")
print(f"Sync running: {status['components']['sync_service']['is_running']}")
```

## ADHD-Friendly Features

### Progressive Disclosure
- Search results show basic info first
- Detailed information available on demand
- Minimal cognitive load

### Simple Interactions
- Binary choices (not overwhelming options)
- Clear success/failure feedback
- Immediate response indicators

### Smart Defaults
- Automatic scope selection for searches
- Intelligent conflict resolution
- Reasonable confidence thresholds (85%)

### Example ADHD-Friendly Workflow

```python
# Simple search with immediate results
results = librarian.search("contracts")  # Auto-determines best approach

# Results show availability immediately
for result in results:
    print(f"📄 {result.filename}")
    print(f"   📅 Modified: {result.last_modified.strftime('%Y-%m-%d')}")
    print(f"   📍 Available: {result.availability.value}")
    print(f"   💯 Relevance: {result.relevance_score:.0f}%")
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```bash
   # Re-download credentials from Google Cloud Console
   # Ensure credentials file is named 'gdrive_credentials.json'
   python test_hybrid_architecture.py --auth-only
   ```

2. **Drive Not Detected**
   ```python
   from gdrive_integration import GoogleDriveIntegration
   
   integration = GoogleDriveIntegration()
   status = integration.get_status()
   print(f"Drive mounted: {status.is_mounted}")
   print(f"Drive path: {status.drive_path}")
   ```

3. **Cache Issues**
   ```python
   # Clear cache if corrupted
   librarian.streamer.clear_cache(older_than_days=0)
   
   # Check cache status
   cache_size = librarian.streamer.cache_manager.get_cache_size()
   print(f"Cache size: {cache_size / 1024 / 1024:.1f}MB")
   ```

4. **Sync Problems**
   ```python
   # Check sync status
   sync_status = librarian.sync_service.get_sync_status()
   print(f"Conflicts: {sync_status['unresolved_conflicts']}")
   print(f"Pending operations: {sync_status['pending_operations']}")
   ```

### Performance Optimization

1. **Adjust Cache Size**
   ```python
   # For low-storage systems
   librarian = GoogleDriveLibrarian(cache_size_gb=1.0)
   
   # For high-speed systems
   librarian = GoogleDriveLibrarian(cache_size_gb=10.0)
   ```

2. **Optimize Sync Interval**
   ```python
   # More frequent sync (uses more bandwidth)
   librarian = GoogleDriveLibrarian(sync_interval=60)
   
   # Less frequent sync (saves bandwidth)
   librarian = GoogleDriveLibrarian(sync_interval=1800)  # 30 minutes
   ```

3. **Selective File Types**
   ```python
   # Only sync specific file types
   librarian.config['sync_preferences']['sync_file_types'] = [
       'application/pdf',
       'text/plain'
   ]
   ```

## Testing

### Quick Test
```bash
python test_hybrid_architecture.py --quick
```

### Full Test Suite
```bash
python test_hybrid_architecture.py --full
```

### Individual Component Tests
```bash
# Test authentication only
python google_drive_auth.py

# Test streaming
python gdrive_streamer.py

# Test background sync
python background_sync_service.py
```

## Security Considerations

1. **Credential Storage**: OAuth tokens stored securely in `~/.ai_organizer_config/`
2. **File Permissions**: Cache files have restricted permissions (600)
3. **Local Processing**: All AI processing happens locally (no cloud uploads)
4. **Encryption**: Sensitive data encrypted at rest

## Performance Monitoring

```python
# Monitor system performance
status = librarian.get_system_status()

# Cache efficiency
cache_hit_rate = status['components']['cache']['hit_rate']

# Sync performance
sync_ops = status['components']['sync_service']['active_operations']

# Storage usage
storage_used = status['auth_info']['storage_used_gb']
storage_total = status['auth_info']['storage_quota_gb']
```

## Support and Maintenance

### Logs
- Authentication: `~/.ai_organizer_config/auth.log`
- Sync operations: `~/.ai_organizer_config/sync.log`
- Cache operations: `~/.ai_organizer_config/cache.log`

### Backup and Recovery
```python
# Backup metadata
librarian.metadata_store.backup_to_file("metadata_backup.db")

# Clear and rebuild cache
librarian.streamer.cache_manager.evict_cache_intelligently(float('inf'))
```

### Updates and Migration
The system is designed for forward compatibility. Configuration and metadata schemas include version information for smooth upgrades.

---

**Created by**: RT Max for AI File Organizer v3.0  
**Last Updated**: 2025-09-10  
**Version**: 3.0.0