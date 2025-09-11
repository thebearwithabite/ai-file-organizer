# 🚀 Setup Instructions: Hybrid Cloud-First Architecture

## **Quick Start Guide**

### **Prerequisites**
- Python 3.11+
- Google Account with Google Drive
- ~500MB local storage for cache/metadata
- Internet connection for Google Drive API

### **1. Install Dependencies**

```bash
# Install required packages
pip install -r requirements_cloud.txt

# Or install manually:
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib numpy requests aiohttp
```

### **2. Google Drive API Setup**

#### **Step 1: Create Google Cloud Project**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Name it "AI File Organizer" or similar

#### **Step 2: Enable Google Drive API**

1. In the Cloud Console, go to **APIs & Services > Library**
2. Search for "Google Drive API"
3. Click **Enable**

#### **Step 3: Create OAuth 2.0 Credentials**

1. Go to **APIs & Services > Credentials**
2. Click **+ CREATE CREDENTIALS > OAuth 2.0 Client ID**
3. If prompted, configure OAuth consent screen:
   - User Type: **External** (unless you have Google Workspace)
   - App name: "AI File Organizer"
   - User support email: Your email
   - Scopes: Add `../auth/drive` and `../auth/drive.file`
4. Application type: **Desktop application**
5. Name: "AI File Organizer Desktop"
6. Click **Create**

#### **Step 4: Download Credentials**

1. Click the **Download** button (⬇️) next to your OAuth 2.0 Client ID
2. Save the file as `gdrive_credentials.json` in your project root
3. **Important**: Keep this file secure and never commit to version control

### **3. Test the Setup**

```bash
# Test Google Drive authentication
python google_drive_auth.py

# Test local metadata store
python local_metadata_store.py
```

Expected output:
```
🔐 Google Drive Authentication Test
==================================================
✅ Authentication successful!
   👤 User: Your Name (your.email@gmail.com)
   💾 Total storage: 2000.0 GB
   📊 Used storage: 45.2 GB
   💿 Free storage: 1954.8 GB
   📁 Files accessible: 5
```

### **4. Initialize the System**

```bash
# Create a simple test script
cat > test_cloud_system.py << 'EOF'
#!/usr/bin/env python3
from google_drive_auth import GoogleDriveAuth
from local_metadata_store import LocalMetadataStore
from datetime import datetime

def main():
    print("🚀 AI File Organizer v3.0 - Cloud Architecture Test")
    
    # Test Google Drive authentication
    auth = GoogleDriveAuth()
    test_results = auth.test_authentication()
    
    if test_results['success']:
        print(f"✅ Google Drive connected: {test_results['user_email']}")
        print(f"💾 Available storage: {test_results['free_storage_gb']:.1f} GB")
    else:
        print("❌ Google Drive authentication failed")
        return
    
    # Test local metadata store
    store = LocalMetadataStore()
    
    # Add test file metadata
    test_file = {
        'google_drive_id': 'test_file_123',
        'file_path': 'documents/test.pdf',
        'file_name': 'test.pdf',
        'size_bytes': 1024 * 1024,  # 1MB
        'mime_type': 'application/pdf',
        'modified_time': datetime.now(),
        'created_time': datetime.now(),
        'category': 'business',
        'confidence': 0.9,
        'tags': ['test', 'document']
    }
    
    file_id = store.add_file(test_file)
    print(f"✅ Test file added to metadata store: {file_id}")
    
    # Search test
    results = store.search_files(query="test", category="business")
    print(f"✅ Search test: Found {len(results)} results")
    
    # Statistics
    stats = store.get_statistics()
    print(f"📊 Database: {stats['total_files']} files, {stats['db_size_mb']:.1f}MB")
    
    print("\n🎉 System initialization successful!")

if __name__ == "__main__":
    main()
EOF

# Run the test
python test_cloud_system.py
```

## **Configuration Options**

### **Environment Variables (Optional)**

Create `.env` file in project root:
```bash
# Google Drive API settings
GOOGLE_DRIVE_CREDENTIALS_FILE=gdrive_credentials.json
GOOGLE_DRIVE_TOKEN_FILE=.ai_organizer_config/google_drive_token.json

# Local storage settings
MAX_CACHE_SIZE_MB=500
METADATA_DB_PATH=.ai_organizer_config/metadata.db

# Performance settings
WAL_CHECKPOINT_INTERVAL=1000
ENABLE_COMPRESSION=true
```

### **Directory Structure**

After setup, your project will have:
```
ai-file-organizer/
├── gdrive_credentials.json          # Google OAuth credentials (secret!)
├── google_drive_auth.py             # Authentication module
├── local_metadata_store.py          # Metadata database
├── requirements_cloud.txt           # Dependencies
├── .ai_organizer_config/            # Local configuration
│   ├── google_drive_token.json     # Access tokens (auto-generated)
│   ├── metadata.db                 # SQLite database
│   └── cache/                      # File cache (< 500MB)
└── .gitignore                      # Ignore credentials and cache
```

## **Security & Privacy**

### **Important Security Notes**

1. **Never commit credentials**: Add to `.gitignore`:
   ```gitignore
   gdrive_credentials.json
   .ai_organizer_config/
   *.log
   __pycache__/
   ```

2. **Token security**: Access tokens are stored locally with restricted permissions (600)

3. **Local data**: All processing happens locally - no data sent to third parties

4. **Google Drive permissions**: The app only accesses files it creates or that you explicitly grant access to

### **Data Storage Locations**

- **Google Drive**: Primary file storage (your 2TB)
- **Local Cache**: `~/.ai_organizer_config/cache/` (< 500MB)
- **Metadata**: `~/.ai_organizer_config/metadata.db` (< 100MB)
- **Logs**: `~/.ai_organizer_config/logs/` (< 50MB)

## **Usage Examples**

### **Basic File Operations**

```python
from google_drive_auth import GoogleDriveAuth
from local_metadata_store import LocalMetadataStore

# Authenticate
auth = GoogleDriveAuth()
service = auth.get_authenticated_service()

# Access metadata
store = LocalMetadataStore()

# Search files
business_files = store.search_files(category="business", limit=10)
recent_files = store.get_recently_accessed_files(days=7)
cached_files = store.get_cached_files()
```

### **Performance Monitoring**

```python
# Get system statistics
stats = store.get_statistics()
print(f"Files tracked: {stats['total_files']}")
print(f"Cache usage: {stats['cached_size_bytes'] / (1024**2):.1f} MB")
print(f"Hit rate: {(stats['cached_files'] / stats['total_files']) * 100:.1f}%")
```

## **Troubleshooting**

### **Common Issues**

**1. Authentication Failed**
```
❌ Credentials file not found: gdrive_credentials.json
```
**Solution**: Download OAuth credentials from Google Cloud Console

**2. Permission Denied**
```
❌ Failed to save credentials: [Errno 13] Permission denied
```
**Solution**: Check file permissions on config directory

**3. Database Locked**
```
❌ database is locked
```
**Solution**: Close any other instances of the application

**4. Network Errors**
```
❌ Failed to refresh credentials
```
**Solution**: Check internet connection and Google API status

### **Debug Mode**

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run your code
auth = GoogleDriveAuth()
# ... detailed logs will appear
```

### **Reset System**

To completely reset:
```bash
# Remove all local data
rm -rf .ai_organizer_config/

# Keep credentials, remove tokens only
rm .ai_organizer_config/google_drive_token.json
```

## **Next Steps**

After successful setup:

1. **Implement file streaming system**
2. **Add smart caching logic**  
3. **Create background sync service**
4. **Integrate with existing AI classification**
5. **Build user interface**

Your system now has:
- ✅ Google Drive API authentication with automatic refresh
- ✅ High-performance local metadata store with SQLite
- ✅ Vector embedding support for semantic search
- ✅ Cache management with intelligent policies
- ✅ Full-text search capabilities
- ✅ ADHD-friendly minimal local storage (< 500MB total)

The foundation for your 2TB cloud-first file management system is ready! 🎉