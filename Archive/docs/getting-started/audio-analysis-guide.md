# Audio Analysis Usage Guide

Quick reference for using the audio analysis pipeline in the AI File Organizer v3.1.

---

## Quick Start

### 1. Analyze a Single Audio File

```python
from pathlib import Path
from unified_classifier import UnifiedClassificationService

# Initialize service
service = UnifiedClassificationService()

# Classify audio file
audio_file = Path("/path/to/your/audio.wav")
result = service.classify_file(audio_file)

# View results
print(f"Category: {result['category']}")
print(f"Confidence: {result['confidence']:.1%}")
print(f"Mood: {result['metadata']['mood']}")
print(f"BPM: {result['metadata']['bpm']:.1f}")
print(f"Energy: {result['metadata']['energy_level']}/10")
```

### 2. Run Test Suite

```bash
python3 test_audio_analysis.py
```

This will:
- Test all audio analysis components
- Analyze a sample file from Downloads
- Verify learning system integration
- Display comprehensive results

### 3. Spectral Analysis Only (No API Required)

```python
from pathlib import Path
from audio_analyzer import AudioAnalyzer

# Initialize without OpenAI API
analyzer = AudioAnalyzer(base_dir="/path/to/project", confidence_threshold=0.7)

# Analyze audio file
audio_file = Path("/path/to/audio.wav")
spectral_result = analyzer.analyze_audio_spectral(audio_file, max_duration=30)

# View spectral features
print(f"BPM: {spectral_result['bpm']:.1f}")
print(f"Mood: {spectral_result['mood']}")
print(f"Content Type: {spectral_result['content_type']}")
print(f"Energy Level: {spectral_result['energy_level_scale']}/10")
print(f"Texture: {spectral_result['spectral_features']['texture']}")
```

---

## Understanding Results

### Classification Output Structure

```python
{
    'source': 'Audio Classifier (AI + Spectral Analysis)',
    'category': 'music_ambient',          # Main category
    'confidence': 0.85,                   # 0.0 to 1.0
    'reasoning': [                        # Why this classification
        "AI-powered audio analysis",
        "Mood: contemplative",
        "BPM: 90.7"
    ],
    'suggested_filename': 'filename.wav',
    'metadata': {
        'mood': 'contemplative',          # Detected mood
        'intensity': 'subtle_background', # Intensity level
        'energy_level': 4,                # 0-10 scale
        'bpm': 90.7,                      # Beats per minute
        'spectral_content_type': 'music', # music/sfx/voice/ambient
        'tags': ['ambient', 'calm'],      # Keywords
        'spectral_features': {            # Raw spectral data
            'brightness': 2500.0,
            'texture': 'smooth',
            'harmonic_ratio': 0.75
        }
    }
}
```

### Mood Types
- **contemplative**: Low energy, slow tempo, dark tones
- **calm**: Low energy, slow tempo, bright tones
- **mysterious**: Low harmonic ratio, slow tempo
- **tense**: Moderate energy, dissonant sounds
- **melancholic**: Moderate tempo and energy
- **energetic**: High energy, fast tempo
- **uplifting**: High energy, moderate tempo
- **ambient**: Default for atmospheric sounds

### Content Types
- **music**: High harmonic content (songs, instrumentals)
- **sfx**: Sound effects (beeps, alerts, environmental sounds)
- **voice**: Speech or vocals (specific harmonic characteristics)
- **ambient**: Atmospheric background sounds

### Categories (Auto-discovered)
- `music_ambient`: Ambient music and atmospheric tracks
- `sfx_technology`: Technology-related sound effects
- `sfx_environmental`: Environmental and nature sounds
- `sfx_consciousness`: AI/consciousness-themed effects
- `voice_element`: Voice recordings and spoken content

---

## Common Use Cases

### 1. Organize Music Library by Mood

```python
from pathlib import Path
from unified_classifier import UnifiedClassificationService

service = UnifiedClassificationService()
music_dir = Path("/path/to/music")

for audio_file in music_dir.glob("*.wav"):
    result = service.classify_file(audio_file)
    mood = result['metadata']['mood']
    bpm = result['metadata']['bpm']

    print(f"{audio_file.name}: {mood}, {bpm:.1f} BPM")
```

### 2. Find High-Energy Tracks

```python
from pathlib import Path
from audio_analyzer import AudioAnalyzer

analyzer = AudioAnalyzer(base_dir=".", confidence_threshold=0.7)
downloads = Path.home() / "Downloads"

high_energy_files = []

for audio_file in downloads.glob("*.wav"):
    spectral = analyzer.analyze_audio_spectral(audio_file)
    if spectral['energy_level_scale'] >= 7:
        high_energy_files.append({
            'file': audio_file.name,
            'energy': spectral['energy_level_scale'],
            'bpm': spectral['bpm']
        })

for track in sorted(high_energy_files, key=lambda x: x['energy'], reverse=True):
    print(f"{track['file']}: Energy {track['energy']}/10, {track['bpm']:.1f} BPM")
```

### 3. Check Learning Statistics

```python
from universal_adaptive_learning import UniversalAdaptiveLearning

learning = UniversalAdaptiveLearning()

# Get audio patterns
print("BPM Ranges by Category:")
for category, bpm_list in learning.audio_patterns['bpm_ranges'].items():
    if bpm_list:
        avg_bpm = sum(bpm_list) / len(bpm_list)
        print(f"  {category}: {avg_bpm:.1f} BPM (avg)")

print("\nMoods by Category:")
for category, moods in learning.audio_patterns['moods'].items():
    print(f"  {category}: {', '.join(moods)}")

# Get overall statistics
summary = learning.get_learning_summary()
print(f"\nTotal learning events: {summary['total_learning_events']}")
print(f"Patterns discovered: {summary['patterns_discovered']}")
```

---

## Command-Line Usage

### Analyze Single File

```bash
python3 audio_analyzer.py /path/to/audio.wav [OPENAI_API_KEY]
```

### Run Full Test Suite

```bash
python3 test_audio_analysis.py
```

### Check System Status

```python
from unified_classifier import UnifiedClassificationService

service = UnifiedClassificationService()
# Will print initialization status including audio analyzer availability
```

---

## Troubleshooting

### Issue: "librosa not available"
**Solution**: Install audio dependencies
```bash
pip install librosa mutagen soundfile
```

### Issue: "OpenAI not available"
**Solution**:
1. Set environment variable: `export OPENAI_API_KEY="your-key-here"`
2. Or use spectral-only mode (no API required)

### Issue: BPM shows as 0.0
**Reason**: File is a sound effect or ambient track without detectable beat
**Solution**: This is expected behavior for non-musical audio

### Issue: Low confidence scores
**Reason**: File doesn't match known patterns yet
**Solution**: System will improve with more files as adaptive learning trains

### Issue: Google Drive timeout warnings
**Reason**: Learning data stored on Google Drive is slow to access
**Solution**: Data is also stored locally in `~/.ai_file_organizer/databases/`

---

## Performance Tips

### 1. Batch Processing
Process multiple files in one session to reuse initialized service:

```python
service = UnifiedClassificationService()  # Initialize once

for audio_file in audio_files:
    result = service.classify_file(audio_file)  # Reuse service
```

### 2. Limit Analysis Duration
For long audio files, limit spectral analysis to save time:

```python
analyzer.analyze_audio_spectral(audio_file, max_duration=30)  # Only analyze first 30 seconds
```

### 3. Use Spectral-Only Mode
When API access is slow or unavailable:

```python
# Disable AI classification, use only librosa
spectral_result = analyzer.analyze_audio_spectral(audio_file)
category = spectral_result['content_type']  # music/sfx/voice/ambient
```

---

## Advanced Features

### 1. Custom Category Discovery

The system automatically discovers new categories based on file content:

```python
# System detects new category patterns
analyzer.classify_audio_file(file)  # May discover "sfx_nature", "music_electronic", etc.

# Check discovered categories
print(analyzer.discovered_categories['new_categories'])
```

### 2. Pattern-Based Predictions

After processing multiple files, the system predicts classifications:

```python
from universal_adaptive_learning import UniversalAdaptiveLearning

learning = UniversalAdaptiveLearning()

# Predict action for new file
prediction = learning.predict_user_action(
    file_path="/path/to/new/audio.wav",
    context={'content_keywords': ['ambient', 'calm', 'atmospheric']}
)

print(f"Predicted category: {prediction['predicted_action']}")
print(f"Confidence: {prediction['confidence']:.1%}")
print(f"Based on {prediction['pattern_count']} patterns")
```

### 3. Export Learning Data

```python
learning = UniversalAdaptiveLearning()

# Get comprehensive summary
summary = learning.get_learning_summary()

# Save to file for analysis
import json
with open('learning_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)
```

---

## Integration with File Organizer

### Auto-Organize Audio Files

```python
from pathlib import Path
from unified_classifier import UnifiedClassificationService

service = UnifiedClassificationService()
downloads = Path.home() / "Downloads"

# Get all audio files
audio_files = []
for ext in ['.wav', '.mp3', '.m4a', '.flac', '.aiff']:
    audio_files.extend(downloads.glob(f"*{ext}"))

# Classify and suggest organization
for audio_file in audio_files:
    result = service.classify_file(audio_file)

    if result['confidence'] >= 0.85:  # High confidence
        category = result['category']
        mood = result['metadata']['mood']

        # Suggest folder structure
        target_folder = f"01_UNIVERSAL_ASSETS/{category}/{mood}/"
        print(f"Move {audio_file.name} -> {target_folder}")
    else:
        print(f"Review needed: {audio_file.name} ({result['confidence']:.1%})")
```

---

## API Reference

### AudioAnalyzer Methods

```python
# Initialize
analyzer = AudioAnalyzer(base_dir, confidence_threshold=0.7, openai_api_key=None)

# Spectral analysis (no API required)
spectral_result = analyzer.analyze_audio_spectral(file_path, max_duration=60)

# Get metadata
metadata = analyzer.get_audio_metadata(file_path)

# AI classification (requires OpenAI API)
classification = analyzer.classify_audio_file(file_path, user_description="")

# Check if file is audio
is_audio = analyzer.is_audio_file(file_path)

# Show learning stats
analyzer.show_learning_stats()
```

### UnifiedClassificationService Methods

```python
# Initialize
service = UnifiedClassificationService()

# Classify any file (audio, image, video, document)
result = service.classify_file(file_path)

# Access learning system
learning_summary = service.learning_system.get_learning_summary()
```

---

## Support

For issues or questions:
1. Check `/Users/user/Github/ai-file-organizer/PHASE_2C_AUDIO_ANALYSIS_COMPLETE.md`
2. Run test suite: `python3 test_audio_analysis.py`
3. Review CLAUDE.md for project context

---

**Last Updated**: 2025-10-25
**Version**: Phase 2c Complete
