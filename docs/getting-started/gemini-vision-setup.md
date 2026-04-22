# Gemini Vision API Setup Guide

## Phase 2: Computer Vision Integration for AI File Organizer v3.1

This guide walks through setting up Google's Gemini API for intelligent image and video classification.

---

## 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud account (free tier available)
- AI File Organizer v3.1 codebase

---

## 🔑 Step 1: Get Your Gemini API Key

### Option A: Google AI Studio (Recommended - Free Tier Available)

1. **Visit Google AI Studio**
   - Go to: https://aistudio.google.com/
   - Sign in with your Google account

2. **Get API Key**
   - Click "Get API Key" in the left sidebar
   - Click "Create API Key"
   - Choose "Create API key in new project" (or select existing project)
   - **IMPORTANT**: Copy the API key immediately (you won't be able to see it again)

3. **API Key Format**
   ```
   AIza...  (typically starts with "AIza" and is ~39 characters)
   ```

### Option B: Google Cloud Console (For Production Use)

1. **Create Google Cloud Project**
   - Go to: https://console.cloud.google.com/
   - Create new project or select existing one

2. **Enable Gemini API**
   - Navigate to "APIs & Services" > "Library"
   - Search for "Generative Language API"
   - Click "Enable"

3. **Create API Key**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy the generated API key

4. **Configure API Key Restrictions (Recommended)**
   - Click "Edit API Key"
   - Set application restrictions (IP addresses, HTTP referrers)
   - Restrict API key to "Generative Language API" only
   - Save changes

---

## 🛠️ Step 2: Configure API Key for AI File Organizer

### Method 1: Configuration File (Recommended for Daily Use)

1. **Create config directory** (if not already exists):
   ```bash
   mkdir -p ~/.ai_organizer_config
   ```

2. **Save API key to file**:
   ```bash
   echo 'YOUR_API_KEY_HERE' > ~/.ai_organizer_config/gemini_api_key.txt
   ```

3. **Set correct permissions** (security):
   ```bash
   chmod 600 ~/.ai_organizer_config/gemini_api_key.txt
   ```

4. **Verify**:
   ```bash
   cat ~/.ai_organizer_config/gemini_api_key.txt
   ```

### Method 2: Environment Variable (For Testing/Development)

1. **Set environment variable** (temporary - current session only):
   ```bash
   export GEMINI_API_KEY='YOUR_API_KEY_HERE'
   ```

2. **Make permanent** (add to shell config):

   **For Zsh (macOS default):**
   ```bash
   echo 'export GEMINI_API_KEY="YOUR_API_KEY_HERE"' >> ~/.zshrc
   source ~/.zshrc
   ```

   **For Bash:**
   ```bash
   echo 'export GEMINI_API_KEY="YOUR_API_KEY_HERE"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Verify**:
   ```bash
   echo $GEMINI_API_KEY
   ```

---

## 📦 Step 3: Install Dependencies

1. **Navigate to project directory**:
   ```bash
   cd /Users/user/Github/ai-file-organizer
   ```

2. **Install required packages**:
   ```bash
   pip install -r requirements_v3.txt
   ```

   This installs:
   - `google-generativeai>=0.3.0` - Gemini API client
   - `Pillow>=10.0.0` - Image processing

3. **Verify installation**:
   ```bash
   python -c "import google.generativeai as genai; print('Gemini SDK installed:', genai.__version__)"
   ```

---

## ✅ Step 4: Test Your Setup

### Quick Test

Run the built-in test:
```bash
python vision_analyzer.py
```

**Expected output if configured correctly:**
```
🔍 Testing Vision Analyzer...
✅ Vision Analyzer initialized
   API Status: True
   Base Directory: /Users/user/GoogleDrive/AI_Organizer
   Cache Directory: .../04_METADATA_SYSTEM/vision_cache (DEPRECATED - now in ~/Documents/AI_METADATA_SYSTEM)

📊 Statistics:
   API Calls: 0
   Cache Hit Rate: 0.0%

🎯 Vision Analyzer test completed!
```

### Comprehensive Test Suite

Run the full integration test:
```bash
python test_vision_integration.py
```

This will test:
- ✅ API initialization and connection
- ✅ Image analysis with sample images
- ✅ Caching system
- ✅ Learning pattern storage
- ✅ Integration with unified classifier

---

## 🖼️ Step 5: Test with Real Images

### Analyze a Screenshot

```bash
python -c "
from vision_analyzer import VisionAnalyzer
analyzer = VisionAnalyzer()
result = analyzer.analyze_image('Screenshot 2025-09-26 at 12.23.57 PM.png')
print(f'Category: {result[\"suggested_category\"]}')
print(f'Confidence: {result[\"confidence_score\"]:.2f}')
print(f'Description: {result[\"description\"][:200]}...')
"
```

### Extract Text from Screenshot

```bash
python -c "
from vision_analyzer import VisionAnalyzer
analyzer = VisionAnalyzer()
text = analyzer.extract_screenshot_text('sreenshot.jpg')
print(f'Extracted text:\\n{text}')
"
```

### Analyze Any Image

```python
from vision_analyzer import VisionAnalyzer

analyzer = VisionAnalyzer()

# Analyze image
result = analyzer.analyze_image('/path/to/your/image.jpg')

print(f"Success: {result['success']}")
print(f"Category: {result['suggested_category']}")
print(f"Confidence: {result['confidence_score']:.2f}")
print(f"Scene Type: {result['scene_type']}")
print(f"Objects: {result['objects_detected']}")
print(f"Description: {result['description']}")
```

---

## 🔍 Understanding the Results

### Result Structure

```python
{
    'success': True,
    'content_type': 'image',
    'description': 'Detailed AI-generated description...',
    'objects_detected': ['object1', 'object2', ...],
    'text_content': 'Extracted text (for screenshots)',
    'scene_type': 'indoor' | 'outdoor' | 'digital' | 'unknown',
    'confidence_score': 0.85,  # 0.0 to 1.0
    'keywords': ['keyword1', 'keyword2', ...],
    'suggested_category': 'screenshot' | 'headshot' | 'logo' | ...,
    'metadata': {
        'file_name': 'image.jpg',
        'file_size': 12345,
        'analysis_timestamp': '2025-10-24T...',
        'keyword_matches': 3
    }
}
```

### Confidence Scoring (ADHD-Friendly Design)

- **0.85+**: High confidence - automatic classification
- **0.70-0.84**: Medium confidence - suggest classification
- **0.40-0.69**: Low confidence - ask user for confirmation
- **<0.40**: Very low confidence - manual review required

---

## 📊 API Usage and Costs

### Free Tier Limits (Google AI Studio)

- **60 requests per minute**
- **1,500 requests per day**
- **No cost** for moderate use

### Cost Optimization Features

1. **Caching System**
   - Results cached for 30 days (configurable)
   - Avoids re-analyzing same files
   - Significant API call reduction

2. **Gemini 1.5 Flash Model**
   - Faster processing
   - Lower cost than Pro model
   - Excellent quality for file organization

3. **Smart Fallback**
   - Falls back to filename analysis if API unavailable
   - No errors when quota exceeded

### Monitor Your Usage

```bash
python -c "
from vision_analyzer import VisionAnalyzer
analyzer = VisionAnalyzer()
stats = analyzer.get_statistics()
print(f'API Calls: {stats[\"api_calls\"]}')
print(f'Cache Hit Rate: {stats[\"cache_hit_rate\"]}')
"
```

---

## 🐛 Troubleshooting

### "No API key found" Error

**Problem**: Vision analyzer can't find API key

**Solutions**:
1. Check config file exists:
   ```bash
   ls -la ~/.ai_organizer_config/gemini_api_key.txt
   ```

2. Check environment variable:
   ```bash
   echo $GEMINI_API_KEY
   ```

3. Verify API key format (should start with "AIza...")

### "API initialization failed" Error

**Problem**: API key is invalid or API not enabled

**Solutions**:
1. Verify API key is correct (copy-paste from Google AI Studio)
2. Check if Generative Language API is enabled in your Google Cloud project
3. Wait 1-2 minutes after creating new API key

### "Rate limit exceeded" Error

**Problem**: Too many API calls

**Solutions**:
1. Wait 1 minute for rate limit to reset
2. Enable caching: `analyzer = VisionAnalyzer(enable_caching=True)`
3. Check cache hit rate: `analyzer.get_statistics()`

### "Image processing failed" Error

**Problem**: Image format not supported or file corrupted

**Solutions**:
1. Verify image format is supported (jpg, png, gif, bmp, webp)
2. Try opening image in Preview/Photos to verify it's not corrupted
3. Check file size (Gemini has max image size limits)

### PIL/Pillow Import Error

**Problem**: Pillow not installed

**Solution**:
```bash
pip install Pillow>=10.0.0
```

---

## 🔒 Security Best Practices

### API Key Protection

1. **Never commit API keys to Git**:
   ```bash
   # Add to .gitignore
   echo '.ai_organizer_config/' >> .gitignore
   echo 'gemini_api_key.txt' >> .gitignore
   ```

2. **Use environment variables for CI/CD**:
   - Set `GEMINI_API_KEY` in GitHub Secrets
   - Never hardcode keys in code

3. **Rotate API keys regularly**:
   - Create new API key every 90 days
   - Delete old keys from Google Cloud Console

4. **Restrict API key usage** (Google Cloud Console):
   - Set IP address restrictions
   - Limit to Generative Language API only
   - Set quota limits

---

## 📈 Performance Tips

### Optimize API Usage

1. **Enable caching** (enabled by default):
   ```python
   analyzer = VisionAnalyzer(enable_caching=True, cache_duration_days=30)
   ```

2. **Batch process images**:
   - Process multiple images in one session
   - Cache warming reduces future API calls

3. **Use fallback mode for quick scans**:
   - Filename-based classification is instant
   - Save API calls for uncertain files

### Monitor Performance

```python
from vision_analyzer import VisionAnalyzer

analyzer = VisionAnalyzer()

# ... process images ...

stats = analyzer.get_statistics()
print(f"API Calls: {stats['api_calls']}")
print(f"Cache Hit Rate: {stats['cache_hit_rate']}")
print(f"Most Common Category: {stats['most_common_category']}")
```

---

## 🚀 Next Steps (Phase 2b)

After successful Phase 2a setup:

1. **Integrate with Unified Classifier**
   - Update `unified_classifier.py` to use `VisionAnalyzer`
   - Add vision analysis to `_classify_image_file()` method

2. **Update Adaptive Learning**
   - Integrate visual patterns into `universal_adaptive_learning.py`
   - Store user corrections for vision classifications

3. **Test End-to-End**
   - Run full integration tests
   - Verify files are classified correctly

4. **UI Integration** (Future)
   - Add visual previews for low-confidence images
   - Show extracted text in interactive questions

---

## 📚 Resources

- **Google AI Studio**: https://aistudio.google.com/
- **Gemini API Docs**: https://ai.google.dev/docs
- **Python SDK**: https://github.com/google/generative-ai-python
- **Pricing**: https://ai.google.dev/pricing

---

## ❓ Support

If you encounter issues:

1. Run diagnostic test:
   ```bash
   python test_vision_integration.py
   ```

2. Check logs in:
   - `~/.ai_organizer_config/`
   - Console output from test scripts

3. Verify setup:
   - API key configured correctly
   - Dependencies installed
   - Google Cloud API enabled

---

**Version**: Phase 2a - Foundation
**Last Updated**: 2025-10-24
**Status**: Ready for Testing
