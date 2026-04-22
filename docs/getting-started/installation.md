# Installation Guide

## Prerequisites

Before installing the AI File Organizer, ensure you have:

- **Python 3.8+** (Python 3.9 or 3.10 recommended)
- **Git** for cloning the repository
- **macOS, Linux, or Windows** (macOS recommended for full Apple Script integration)
- **10GB free disk space** for dependencies and initial cache
- **Internet connection** for API services (OpenAI, Google Gemini)

---

## Quick Installation

### Option 1: With Virtual Environment (Recommended)

Virtual environments prevent dependency conflicts and keep your system Python clean.

```bash
# Clone the repository
git clone https://github.com/thebearwithabite/ai-file-organizer
cd ai-file-organizer

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements_v3.txt
pip install -r requirements_cloud.txt  # Google Drive integration

# Start the system
python main.py
```

**Deactivate venv when done:**
```bash
deactivate
```

---

### Option 2: Direct Installation

If you prefer to install globally or already manage Python environments:

```bash
# Clone the repository
git clone https://github.com/thebearwithabite/ai-file-organizer
cd ai-file-organizer

# Install dependencies
pip install -r requirements_v3.txt
pip install -r requirements_cloud.txt  # Google Drive integration

# Start the system
python main.py
```

---

## Environment Setup

### Required API Keys

The AI File Organizer requires API keys for various services:

1. **OpenAI API Key** (for GPT-4 classification and audio analysis)
2. **Google Gemini API Key** (for vision analysis)
3. **Google Drive Credentials** (for cloud storage integration)

### Setting Up Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Google Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Google Drive Configuration (optional)
GOOGLE_DRIVE_CREDENTIALS_PATH=/path/to/credentials.json

# System Configuration
BASE_DIR=/Users/yourname/GoogleDrive/AI_Organizer  # Adjust to your path
```

### Obtaining API Keys

**OpenAI API Key:**
1. Visit [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Create a new API key
4. Copy and paste into `.env` file

**Google Gemini API Key:**
1. Visit [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy and paste into `.env` file

**Google Drive Credentials:**
- See [Gemini Vision Setup Guide](gemini-vision-setup.md) for detailed instructions
- Required for Google Drive cloud storage integration
- Optional if using local-only storage

---

## Dependency Installation

### Core Requirements (requirements_v3.txt)

```txt
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6
chromadb>=0.4.15
sentence-transformers>=2.2.2
openai>=1.3.0
PyPDF2>=3.0.1
python-docx>=1.0.1
mutagen>=1.47.0
librosa>=0.10.1
google-generativeai>=0.3.0
python-dotenv>=1.0.0
pathlib>=1.0.1
pandas>=2.1.0
openpyxl>=3.1.2
Pillow>=10.1.0
```

### Cloud Requirements (requirements_cloud.txt)

```txt
google-api-python-client>=2.100.0
google-auth-httplib2>=0.1.1
google-auth-oauthlib>=1.1.0
```

### Audio Analysis Requirements

For full audio analysis capabilities (BPM, mood, spectral features):

```bash
# macOS
brew install ffmpeg portaudio

# Ubuntu/Debian
sudo apt-get install ffmpeg portaudio19-dev

# Windows
# Download ffmpeg from https://ffmpeg.org/download.html
# Install portaudio via conda or pre-built wheels
```

---

## Verification

### Test Installation

```bash
# Start the server
python main.py

# You should see:
# INFO: Application startup complete.
# INFO: Uvicorn running on http://0.0.0.0:8000
```

### Test Web Interface

1. Open browser: `http://localhost:8000`
2. You should see the AI File Organizer web interface
3. Try a search query to verify functionality

### Test API Health

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy"}
```

### Test System Status

```bash
# Check system status
curl http://localhost:8000/api/system/status

# Expected response includes:
# {
#   "status": "operational",
#   "google_drive": {...},
#   "librarian": {...}
# }
```

---

## Directory Structure Setup

The AI File Organizer creates this directory structure in your base directory:

```
AI_Organizer/
├── 01_ACTIVE_PROJECTS/
│   ├── PROJECT_NAME/
│   │   ├── EPISODE_NAME/
│   │   │   ├── footage/
│   │   │   ├── audio/
│   │   │   ├── images/
│   │   │   ├── documents/
│   │   │   └── exports/
├── 02_ENTERTAINMENT_INDUSTRY/
│   ├── contracts/
│   ├── talent_management/
│   └── industry_docs/
├── 03_BUSINESS_OPERATIONS/
│   ├── invoices/
│   ├── tax_records/
│   └── agreements/
├── 04_METADATA_SYSTEM/ (DEPRECATED - now at ~/Documents/AI_METADATA_SYSTEM)
│   ├── learning_data.pkl
│   ├── discovered_categories.json
│   └── classification_history/
├── 05_VEO_PROMPTS/
│   └── veo_library/
└── 99_STAGING_EMERGENCY/
    └── emergency_staging/
```

**Automatic Creation:**
The system creates these directories on first run. You can customize the structure by editing `gdrive_integration.py`.

---

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Error: ModuleNotFoundError: No module named 'chromadb'
# Solution: Ensure all requirements are installed
pip install -r requirements_v3.txt
```

**2. Port Already in Use**
```bash
# Error: [Errno 48] Address already in use
# Solution: Kill existing process or use different port
python main.py --port 8001
```

**3. API Key Errors**
```bash
# Error: openai.error.AuthenticationError
# Solution: Check .env file has correct API keys
cat .env | grep OPENAI_API_KEY
```

**4. Google Drive Authentication**
```bash
# Error: google.auth.exceptions.RefreshError
# Solution: Re-authenticate Google Drive
rm token.json
python gdrive_integration.py
```

**5. Audio Analysis Errors**
```bash
# Error: librosa.util.exceptions.ParameterError
# Solution: Install ffmpeg
brew install ffmpeg  # macOS
```

---

## Platform-Specific Notes

### macOS

**Apple Script Integration:**
The system includes native macOS integration via Apple Script for file opening and search interfaces.

```bash
# Test Apple Script integration
osascript -e 'tell application "Finder" to get POSIX path of (choose file)'
```

**Permissions:**
Grant Terminal or your IDE full disk access:
1. System Preferences → Security & Privacy → Privacy
2. Full Disk Access → Add Terminal/IDE

---

### Linux

**Dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-pip python3-venv ffmpeg portaudio19-dev

# Fedora/RHEL
sudo dnf install python3-pip python3-virtualenv ffmpeg portaudio-devel
```

---

### Windows

**Dependencies:**
```powershell
# Install Python 3.9+ from python.org
# Install Git from git-scm.com
# Install ffmpeg from ffmpeg.org

# Create virtual environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements_v3.txt
```

**Note:** Some Apple Script features are macOS-only. The web interface and API work fully on Windows.

---

## Performance Optimization

### Recommended Settings

**For Fast Startup (ADHD-Friendly):**
- System starts in ~15-20 seconds with lazy loading
- No automatic scanning on startup
- Manual triage trigger when needed

**For Large Libraries:**
- Increase cache size in `gdrive_librarian.py`: `cache_size_gb=5.0`
- Use SSD for local cache directory
- Enable background sync for Google Drive

**For Low Memory Systems:**
- Reduce SentenceTransformer batch size
- Disable vision analysis for large videos
- Use file size limits (default: 10MB)

---

## Next Steps

After installation, proceed to:

1. **[Gemini Vision Setup](gemini-vision-setup.md)** - Configure vision analysis
2. **[Audio Analysis Guide](audio-analysis-guide.md)** - Set up audio features
3. **[Usage Guide](../usage.md)** - Learn how to use the system
4. **[API Documentation](../guides/api-documentation.md)** - Explore API endpoints

---

## Uninstallation

To completely remove the AI File Organizer:

```bash
# Deactivate virtual environment (if using)
deactivate

# Remove the repository
cd ..
rm -rf ai-file-organizer

# Remove virtual environment
rm -rf venv

# Optional: Remove configuration files
rm ~/.config/ai-file-organizer/*
```

**Note:** Your organized files are NOT deleted during uninstallation. They remain in your file system at their organized locations.

---

*Installation guide last updated: November 4, 2025*
