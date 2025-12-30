# VEO Studio - Quick Reference Card

## 🎯 What Is VEO Studio?
VEO Studio transforms film/TV scripts into VEO 3.1 JSON prompts for AI video generation. It's now integrated into the AI File Organizer as a unified creative workflow.

---

## ⚡ Quick Start

### 1. Start the System
```bash
# Terminal 1: Backend
python main.py

# Terminal 2: Frontend  
cd frontend_v2 && npm run dev
```

### 2. Navigate to VEO Studio
- Open browser: `http://localhost:5173`
- Click "VEO Studio" in sidebar

### 3. Analyze Your First Script
```
INT. OFFICE - DAY

JOHN
Hello, world!
```
- Paste script → Click "Analyze Script"
- View results in Assets tab

---

## 🎨 UI Overview

### Script Tab
- 📝 Text editor for script input
- 📁 File upload (.txt, .fountain, .pdf)
- 🪄 Analyze Script button
- 🎬 Generate Shot List button
- ✅ Real-time analysis results

### Assets Tab
- 👤 Characters (with occurrence count)
- 📍 Locations (grouped by type)
- 🎬 Props (if detected)
- Grid layout with cards

### Shots Tab
- 📋 Complete shot list
- ⏱️ Duration estimates
- 📍 Location per shot
- 🖼️ Generate Keyframe (Phase 2)
- Click to select shot

### Shot Book Tab
- 🎥 Selected shot details
- 🖼️ Keyframe placeholder (Phase 2)
- 📝 VEO JSON preview
- 👥 Characters involved
- 🎯 Assets needed

---

## 🔌 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/veo-studio/analyze-script` | POST | Extract assets, count scenes |
| `/api/veo-studio/generate-shot-list` | POST | Generate shot list from script |
| `/api/veo-studio/generate-keyframe` | POST | Generate keyframe (stub) |
| `/api/veo-studio/projects` | GET | List all projects |
| `/api/veo-studio/projects` | POST | Create new project |

---

## 🧪 Testing

### Run Integration Tests
```bash
python test_veo_studio_integration.py
# Expected: All tests passing ✅
```

### Test Sample Script
```bash
python -c "
from api.veo_studio_api import extract_assets_from_script
script = 'INT. OFFICE - DAY\n\nJOHN\nHello!'
assets = extract_assets_from_script(script)
print(f'Found {len(assets)} assets')
"
```

### View UI Mockup
```bash
python veo_studio_mockup.py
# Displays ASCII art UI
```

---

## 📊 Sample Results

**Input Script:**
```
INT. SPACESHIP BRIDGE - DAY
The CAPTAIN stands at the helm...

CAPTAIN
We need to reach the planet!

EXT. ALIEN PLANET - DUSK
The ship lands...
```

**Output:**
- Scenes: 2
- Estimated Shots: 8
- Characters: CAPTAIN (1x)
- Locations: SPACESHIP BRIDGE (1x), ALIEN PLANET (1x)

---

## 🗄️ Database Tables

### veo_projects
- project_name, script_content
- shot_count, status
- Timestamps

### veo_shots
- shot_id, description
- scene_number, shot_number
- duration_estimate, location
- characters[], assets_needed[]
- veo_json, keyframe_path

### veo_assets
- asset_type, asset_name
- description, occurrences
- reference_image_path

---

## 🔧 Troubleshooting

### Backend won't start
```bash
pip install -r requirements.txt
python main.py
```

### Frontend errors
```bash
cd frontend_v2
npm install
npm run dev
```

### Database issues
- Check: `~/Library/Application Support/AI_Organizer/metadata.db`
- Tables auto-create on first API call

### Import errors
```bash
pip install fastapi pydantic uvicorn
```

---

## 📝 Script Format Tips

### Supported Elements
✅ Scene headers: `INT./EXT. LOCATION - TIME`  
✅ Character names: `ALL CAPS` on own line  
✅ Dialogue: Text under character name  
✅ Action lines: Scene descriptions  

### Example Format
```
INT. ROOM - DAY

Character walks in.

CHARACTER
Hello, world!

ANOTHER CHARACTER
(excited)
Amazing!

EXT. PARK - NIGHT

The sun sets over the horizon.
```

---

## 🚀 Export Workflow

1. Analyze script
2. Review assets and shots
3. Click "Export Project"
4. Download: `projectname_2025-12-30.json`

**JSON Contains:**
- Full script text
- All detected assets
- Complete shot list
- Metadata and timestamps

---

## 📅 Roadmap

### Phase 1 (COMPLETE ✅)
- Script analysis
- Asset extraction
- Shot list generation
- UI implementation

### Phase 2 (PLANNED)
- Local Flux keyframe generation
- RTX 5090 integration
- Enhanced VEO JSON
- Camera angle detection

### Phase 3 (PLANNED)
- Full workflow unification
- Advanced NLP parsing
- Video preview integration
- Asset library management

---

## 🆘 Support

### Documentation
- `INTEGRATION_SUMMARY.md` - Full integration guide
- `VEO_STUDIO_UI_DOCUMENTATION.md` - UI features
- `test_veo_studio_integration.py` - Usage examples

### Quick Help
```bash
# View available endpoints
curl http://localhost:8000/docs

# Test backend health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs
```

---

## 💡 Pro Tips

1. **Start Simple:** Test with 1-2 scene scripts first
2. **Use Proper Format:** Follow screenplay formatting conventions
3. **Check Assets:** Review extracted assets for accuracy
4. **Export Often:** Download JSON backups of your work
5. **Phase 2 Ready:** Keyframe buttons already in UI (stubbed)

---

## 🎬 Example Use Cases

### Film Production
- Break down scripts into shots
- Track character appearances
- Estimate scene durations
- Generate VEO prompts for previsualization

### Animation
- Storyboard generation
- Asset tracking
- Scene planning
- Shot continuity

### Commercial/Corporate
- Script breakdowns
- Asset requirements
- Production planning
- Client presentations

---

**Status:** Phase 1 Complete ✅  
**Version:** 1.0  
**Last Updated:** December 30, 2025  
**Ready For:** Production Testing
