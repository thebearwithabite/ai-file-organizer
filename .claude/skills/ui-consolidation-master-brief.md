# AI File Organizer: Complete UI Consolidation Master Brief

## 🎯 Executive Summary

**Mission:** Transform the AI File Organizer from a collection of 70+ CLI tools into a unified, beautiful, ADHD-friendly web application that eliminates all terminal interactions.

**User:** Ryan (Entertainment Manager + Creative Producer with ADHD)

**Critical Context:** Ryan has not been able to use this powerful system because context-switching between 70+ CLI commands creates insurmountable cognitive load. This consolidation is not a "nice-to-have" — it's the difference between a system that works and one that doesn't.

**Timeline:** 4 weeks (aggressive but achievable)

**Success Metric:** Ryan can organize files, search content, manage VEO prompts, and control system settings **without ever opening the terminal**.

---

## 🎨 Design Philosophy: "Liquid Glass" + ADHD-Friendly

### Core Aesthetic Principles

1. **Liquid Glass (macOS Big Sur/Monterey inspired)**
   - Translucent frosted glass cards (`backdrop-blur-xl`)
   - Subtle borders (`border-white/10`)
   - Soft shadows for depth
   - Smooth animations (300ms ease-in-out)

2. **ADHD-Optimized Interaction Design**
   - **Binary choices** over complex menus
   - **Immediate visual feedback** for every action
   - **Undo always visible** (Rollback Center prominent)
   - **Loading states** that reduce anxiety ("Processing 3 of 10 files...")
   - **Confidence scores visual** (progress bars, not just numbers)
   - **No surprises** - every action is predictable and reversible

3. **Color System**
   ```css
   --accent-blue: #0A84FF;      /* Primary actions (Organize, Search) */
   --accent-green: #30D158;     /* Success (File organized, Sync complete) */
   --accent-yellow: #FFD60A;    /* Warnings (Low space, Uncertain classification) */
   --accent-red: #FF453A;       /* Destructive (Undo, Delete) */
   --accent-purple: #BF5AF2;    /* Special (VEO, AI features) */
   ```

4. **Typography**
   - Headings: `SF Pro Display` (macOS native) or `Inter` fallback
   - Body: `SF Pro Text` or `Inter`
   - Code/JSON: `SF Mono` or `Menlo`

---

## 🏗️ Technical Architecture

### Frontend Stack

```json
{
  "framework": "React 18.3+",
  "build-tool": "Vite 5.0+",
  "styling": "Tailwind CSS 3.4+",
  "components": "ShadCN UI (headless, customizable)",
  "state": {
    "server": "TanStack Query v5 (React Query)",
    "client": "Zustand",
    "forms": "React Hook Form + Zod"
  },
  "routing": "React Router v6.20+",
  "animations": "Framer Motion",
  "visualization": "D3.js (VEO continuity graph)",
  "icons": "Lucide React",
  "notifications": "Sonner (minimal toast)",
  "file-upload": "react-dropzone",
  "code-editor": "Monaco Editor (for VEO JSON)"
}
```

### Backend Structure

```
backend/
├── main.py                    # FastAPI entry point
├── api/
│   ├── organize.py            # File organization endpoints
│   ├── search.py              # Unified search (existing + enhanced)
│   ├── analysis.py            # Vision + Audio analysis
│   ├── veo.py                 # VEO prompt generation (existing + enhanced)
│   ├── system.py              # System status (existing + enhanced)
│   ├── rollback.py            # Rollback history & undo
│   ├── settings.py            # All settings management
│   ├── learning.py            # Adaptive learning stats
│   └── deduplicate.py         # Deduplication service
├── services/
│   ├── organizer_service.py   # Wraps interactive_organizer.py
│   ├── classifier_service.py  # Wraps unified_classifier.py + interactive_classifier.py
│   ├── vision_service.py      # Wraps vision_analyzer.py
│   ├── audio_service.py       # Wraps audio_analyzer.py
│   ├── veo_service.py         # Wraps veo_prompt_generator.py
│   ├── rollback_service.py    # Wraps easy_rollback_system.py
│   ├── learning_service.py    # Wraps universal_adaptive_learning.py
│   ├── confidence_service.py  # Wraps confidence_system.py
│   ├── space_service.py       # Wraps emergency_space_protection.py
│   └── gdrive_service.py      # Wraps gdrive_integration.py
└── models/
    ├── schemas.py             # Pydantic models for all API I/O
    └── database.py            # SQLite connection management
```

---

## 📐 Complete Component Map

### 1. Layout Components

```jsx
// App Shell
<BrowserRouter>
  <Layout>
    <Sidebar />              {/* Persistent navigation */}
    <MainContent>
      <Header />             {/* Breadcrumbs, user menu, notifications */}
      <Outlet />             {/* Route content */}
    </MainContent>
  </Layout>
</BrowserRouter>
```

### 2. Dashboard (Landing Page)

**Route:** `/`

**Components:**
- `SystemStatusCard` - Shows Drive sync, disk space, services
- `QuickActionPanel` - Upload, Search, Rollback buttons
- `RecentActivityFeed` - Live stream of file operations
- `MetricsGrid` - Learning patterns count, files organized today, confidence mode

**API Calls:**
- `GET /api/system/status` (existing, may enhance)
- `GET /api/rollback/operations?limit=10` (new)
- `GET /api/learning/stats` (new)

### 3. Organize Section

**Route:** `/organize`

**Components:**
- `FileUploadZone` - Drag & drop with `react-dropzone`
- `ClassificationQueue` - Shows files being processed
- `ConfidenceModeSelector` - Radio buttons: NEVER / MINIMAL / SMART / ALWAYS
- `InteractiveQuestionModal` - Appears when AI needs input
  - "Is this about Finn or business?" [A] [B]
  - Shows file preview, confidence score, reasoning
- `BatchProcessingPanel` - Upload folder, show progress
- `LearningStatsPanel` - Collapsible sidebar with patterns learned

**API Endpoints (NEW):**
```python
POST   /api/organize/upload           # Single file classification
POST   /api/organize/batch             # Batch folder processing
GET    /api/organize/queue             # Pending classifications
POST   /api/organize/confirm           # User confirms classification
POST   /api/organize/reclassify        # User rejects, provides correct category
GET    /api/organize/stats             # Files organized today, confidence distribution
```

**Backend Services Required:**
- `organizer_service.py` wrapping `interactive_organizer.py`
- `classifier_service.py` wrapping `unified_classifier.py` + `interactive_classifier.py`
- `learning_service.py` wrapping `universal_adaptive_learning.py`

**Key UX Flows:**

*Flow 1: Single File Upload*
1. User drags `contract.pdf` to upload zone
2. Spinner shows "Analyzing content..."
3. Classification preview appears: "Entertainment → Contracts → Management (85% confident)"
4. If >85%, auto-files with success toast
5. If <85%, modal asks: "Is this about Finn or general business?" [A] [B]
6. User clicks [A], file organized, system learns

*Flow 2: Batch Processing*
1. User clicks "Batch Process Folder"
2. Folder picker appears (native file dialog)
3. Progress bar: "Processing 7 of 23 files..."
4. List shows: ✅ Organized (18), 🤔 Needs Review (5)
5. User reviews 5 uncertain files one-by-one
6. Final summary: "23 files organized, learned 3 new patterns"

### 4. Search Section

**Route:** `/search`

**Components:**
- `SearchBar` - Large input with mode toggle [🚀 Fast] [🧠 Semantic] [🤖 Auto]
- `FilterPanel` - Date range, categories, file types, location (local/cloud)
- `ResultsList` - Virtualized list (react-window for performance)
  - `FileResultCard` - PDF/DOCX with snippet
  - `EmailResultCard` - Subject, sender, preview
  - `ClipResultCard` - VEO thumbnail, metadata
- `PreviewSidebar` - Shows full file preview on hover/click

**API Endpoints (ENHANCE EXISTING):**
```python
GET    /api/search?q=query&mode=auto&filter[category]=contracts&filter[date_from]=2024-01-01
# Returns unified results from files, emails, VEO clips
```

**Backend:** Existing `enhanced_librarian.py` + `search.py` work, may need to add filters

### 5. VEO Studio Section

**Route:** `/veo`

**Sub-routes:**
- `/veo` - Library grid view
- `/veo/:id` - Clip detail + editor
- `/veo/continuity` - Continuity graph view
- `/veo/upload` - Batch upload

**Components:**
- `ClipLibrary` - Grid of `ClipCard` components
  - Thumbnail (video frame)
  - Shot ID, mood, lighting, confidence
- `ClipDetailView` (`/veo/:id`)
  - Video player (left)
  - Monaco JSON editor (right) with schema validation
  - Metadata panel (bottom): Shot type, camera movement, characters
  - [Save] [Reanalyze] [Delete] buttons
- `ContinuityGraph` (existing, enhance)
  - D3 force-directed graph
  - Nodes = clips (size = confidence)
  - Edges = continuity links (thickness = score)
  - Hover tooltip with metadata
  - Click node → navigate to `/veo/:id`
- `BatchUploadModal`
  - Multi-file picker
  - Progress: "Analyzing shot 4 of 12... (Gemini Vision API)"

**API Endpoints (ENHANCE EXISTING + NEW):**
```python
POST   /api/veo/generate               # Generate VEO JSON from video (existing)
POST   /api/veo/batch                  # Batch process multiple videos (new)
GET    /api/veo/clips                  # List all clips (existing)
GET    /api/veo/clip/:id               # Get clip + full VEO JSON (existing)
POST   /api/veo/clip/:id/update        # Save edited JSON (existing)
POST   /api/veo/clip/:id/reanalyze     # Trigger Gemini re-analysis (existing)
GET    /api/veo/manifest/:project      # Get continuity data (existing)
DELETE /api/veo/clip/:id               # Delete clip (new)
```

### 6. Analysis Section

**Route:** `/analysis`

**Components:**
- `AnalysisQueue` - Files awaiting vision/audio analysis
- `ResultsGallery` - Grid of analysis results
  - `VisionResultCard` - Image thumbnail + Gemini description
  - `AudioResultCard` - Waveform visualization + BPM/mood
- `FilterPanel` - Type (image/audio), confidence range, date
- `AnalysisDetailModal` - Full analysis view
  - Original file preview
  - AI-generated description
  - Metadata (BPM, mood, lighting, etc.)
  - Confidence score
  - [Reclassify] [Export Data] buttons

**API Endpoints (NEW):**
```python
POST   /api/analysis/vision            # Analyze image/video (wraps vision_analyzer.py)
POST   /api/analysis/audio             # Analyze audio (wraps audio_analyzer.py)
GET    /api/analysis/results           # List all analysis results
GET    /api/analysis/result/:id        # Get specific result details
POST   /api/analysis/reclassify/:id    # Re-trigger analysis
```

### 7. Rollback Center

**Route:** `/rollback`

**Components:**
- `OperationTimeline` - Chronological list of file operations
- `OperationCard` - Expandable card
  - Timestamp
  - Operation type (Organize, Batch, Delete, etc.)
  - File count
  - Preview: "contract.pdf: Downloads → Entertainment/Contracts"
  - [🔄 Undo This Operation] button
- `FilterBar` - [Today] [This Week] [This Month] [All Time]
- `SearchBar` - "Find operations involving 'contract'"
- `EmergencyUndoButton` - Big red button: "🚨 UNDO ALL TODAY'S OPERATIONS"

**API Endpoints (NEW):**
```python
GET    /api/rollback/operations        # List operations (filterable by date, search term)
POST   /api/rollback/undo/:id          # Undo specific operation
POST   /api/rollback/undo-today        # Emergency: undo all today
GET    /api/rollback/search?q=contract # Search operations by filename
```

**Backend:** Wraps `easy_rollback_system.py`

**Critical UX:** This is the **trust mechanism** for ADHD users. If file operations go wrong, this must be **instantly accessible** and **foolproof**.

### 8. Settings Section

**Route:** `/settings`

**Tabs:**
1. Google Drive
2. Space Protection
3. Background Services
4. Adaptive Learning
5. Confidence System
6. Deduplication

**Tab 1: Google Drive**

Components:
- `DriveStatusCard` - Sync status, last sync time, storage used/total
- `ReconnectButton` - If disconnected
- `PauseSyncButton` - Temporarily pause syncing
- `SettingsForm` - Configure sync folders, auto-upload

API:
```python
GET    /api/settings/gdrive            # Current status
POST   /api/settings/gdrive/reconnect  # Trigger OAuth
POST   /api/settings/gdrive/pause      # Pause sync
POST   /api/settings/gdrive/resume     # Resume sync
```

**Tab 2: Space Protection**

Components:
- `FreeSpaceIndicator` - Large visual gauge (like macOS Storage)
- `ThresholdSlider` - Set warning threshold (default 50GB)
- `HistoryLog` - Past emergency staging events

API:
```python
GET    /api/settings/space             # Free space, threshold, history
POST   /api/settings/space/threshold   # Update threshold
GET    /api/settings/space/history     # Emergency staging history
```

**Tab 3: Background Services**

Components:
- `ServiceStatusList` - Table of services with status indicators
  - Adaptive Background Monitor: 🟢 Running
  - Staging Monitor: 🟢 Running
  - Drive Sync: 🟢 Running
- `LogViewer` - Collapsible panel showing recent logs
- `RestartButton` - Per-service restart
- `RestartAllButton` - Nuclear option

API:
```python
GET    /api/settings/services          # List all services + status
POST   /api/settings/services/:name/restart
POST   /api/settings/services/restart-all
GET    /api/settings/services/:name/logs
```

**Tab 4: Adaptive Learning**

Components:
- `StatsCard` - Total patterns learned, classifications made, corrections applied
- `PatternsTable` - List of discovered patterns
  - Pattern: "Files mentioning 'Finn' + 'contract' → Entertainment/Contracts"
  - Confidence: 94%
  - Used: 47 times
- `ExportButton` - Download learning data (JSON)
- `ImportButton` - Upload previous learning data
- `ResetButton` - Clear all learning (confirmation modal)

API:
```python
GET    /api/learning/stats             # Overall statistics
GET    /api/learning/patterns          # List learned patterns
POST   /api/learning/export            # Download JSON file
POST   /api/learning/import            # Upload JSON file
POST   /api/learning/reset             # Clear learning data (dangerous)
```

**Tab 5: Confidence System**

Components:
- `ModeSelector` - Large radio buttons with descriptions
  - 🔴 NEVER (0%): "Fully automatic, no questions"
  - 🟡 MINIMAL (40%): "Only ask about very uncertain files"
  - 🟢 SMART (70%): "Balanced operation (recommended for ADHD)" ✓
  - 🔵 ALWAYS (100%): "Review every single file"
- `StatisticsPanel` - How often each mode was used this week

API:
```python
GET    /api/settings/confidence        # Current mode + stats
POST   /api/settings/confidence        # Set mode
```

**Tab 6: Deduplication**

Components:
- `ScanButton` - "Scan for Duplicates"
- `ProgressBar` - While scanning
- `DuplicatesList` - Groups of duplicate files
  - Show file sizes, paths
  - Checkbox to select which to keep
- `CleanButton` - Remove selected duplicates (with rollback)
- `StatsCard` - Space saved, duplicates removed

API:
```python
POST   /api/dedup/scan                 # Scan for duplicates
GET    /api/dedup/results              # List duplicate groups
POST   /api/dedup/clean                # Remove selected duplicates
GET    /api/dedup/stats                # Space saved, history
```

---

## 🎯 ADHD-Specific Design Requirements

### 1. Cognitive Load Reduction

**Problem:** Too many choices create paralysis.

**Solution:**
- Binary questions ("A or B") not multiple choice
- Confidence mode selector: 4 clear options, not a slider
- Hide advanced options behind "Advanced ▼" expanders

### 2. Immediate Feedback

**Problem:** Uncertainty causes anxiety ("Did that work?")

**Solution:**
- Toast notifications for EVERY action
- Loading states with progress ("Processing 3 of 10...")
- Visual confirmation: green checkmark, success animation
- No silent failures - always show errors with suggestions

### 3. Forgiving Interactions

**Problem:** Fear of making mistakes prevents action.

**Solution:**
- Rollback Center always in navigation
- "Undo" button on every confirmation toast
- Confirmation modals only for truly destructive actions
- Draft/preview modes before committing

### 4. Visual Hierarchy

**Problem:** Can't distinguish important from unimportant.

**Solution:**
- Primary actions: Large blue buttons
- Destructive actions: Red with confirmation
- Secondary actions: Ghost buttons (outline)
- Tertiary actions: Text links

### 5. Persistent Context

**Problem:** Losing place causes frustration.

**Solution:**
- Breadcrumbs in header
- URL reflects state (search query, filters persist)
- "Recently viewed" sidebar
- Auto-save form state (no lost data)

### 6. Reduced Motion Support

**Problem:** Animations can be distracting for some.

**Solution:**
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 📅 4-Week Implementation Plan

### Week 1: Foundation + Dashboard + Basic Organize

**Days 1-2: Project Setup**
- [ ] Initialize Vite + React + TypeScript
- [ ] Install Tailwind CSS + ShadCN UI
- [ ] Create design tokens (`tailwind.config.ts`)
- [ ] Set up TanStack Query + Zustand
- [ ] Create Layout component (Sidebar + Header)
- [ ] Implement routing structure

**Days 3-4: Dashboard**
- [ ] `SystemStatusCard` component + `/api/system/status` enhancement
- [ ] `QuickActionPanel` component
- [ ] `RecentActivityFeed` component + `/api/rollback/operations?limit=10`
- [ ] `MetricsGrid` component + `/api/learning/stats`

**Days 5-7: Basic Organize**
- [ ] `FileUploadZone` with react-dropzone
- [ ] `/api/organize/upload` endpoint (backend)
- [ ] `organizer_service.py` wrapping `interactive_organizer.py`
- [ ] Classification preview UI
- [ ] Success/error toast notifications
- [ ] Test: Upload single file → see it organized

**Week 1 Deliverable:** ✅ Working dashboard + can upload & organize single file

---

### Week 2: Advanced Organize + Rollback Center

**Days 1-2: Confidence System + Interactive Questions**
- [ ] `ConfidenceModeSelector` component
- [ ] `/api/settings/confidence` endpoints
- [ ] `confidence_service.py` wrapping `confidence_system.py`
- [ ] `InteractiveQuestionModal` component
- [ ] `/api/organize/confirm` and `/api/organize/reclassify` endpoints
- [ ] Test: Low-confidence file triggers question modal

**Days 3-4: Batch Processing**
- [ ] `BatchProcessingPanel` component
- [ ] `/api/organize/batch` endpoint
- [ ] Progress bar with file count
- [ ] Pause/cancel functionality
- [ ] Test: Process folder of 20 files

**Days 5-7: Rollback Center (CRITICAL)**
- [ ] `OperationTimeline` component
- [ ] `OperationCard` component (expandable)
- [ ] `/api/rollback/operations`, `/undo/:id`, `/undo-today` endpoints
- [ ] `rollback_service.py` wrapping `easy_rollback_system.py`
- [ ] Search/filter functionality
- [ ] Emergency undo button with confirmation
- [ ] Test: Organize files, undo operation, verify restoration

**Week 2 Deliverable:** ✅ Full organize workflow + bulletproof rollback system

---

### Week 3: Search + Analysis + VEO

**Days 1-2: Unified Search**
- [ ] `SearchBar` component with mode toggle
- [ ] `FilterPanel` component
- [ ] `ResultsList` with virtualization (react-window)
- [ ] `FileResultCard`, `EmailResultCard`, `ClipResultCard`
- [ ] Enhance `/api/search` to accept filters
- [ ] Test: Search for "Finn contracts", see PDF + email results

**Days 3-4: Analysis Section**
- [ ] `AnalysisQueue` component
- [ ] `VisionResultCard` + `AudioResultCard`
- [ ] `/api/analysis/vision`, `/audio`, `/results` endpoints
- [ ] `vision_service.py` wrapping `vision_analyzer.py`
- [ ] `audio_service.py` wrapping `audio_analyzer.py`
- [ ] Test: Analyze image, see Gemini Vision result

**Days 5-7: VEO Studio**
- [ ] `ClipLibrary` grid view
- [ ] `ClipDetailView` with Monaco JSON editor
- [ ] Enhance existing `/api/veo/*` endpoints
- [ ] `ContinuityGraph` improvements (hover tooltips, click navigation)
- [ ] `BatchUploadModal` for videos
- [ ] Test: Upload video, edit JSON, save, view continuity graph

**Week 3 Deliverable:** ✅ Can search everything, see analysis results, manage VEO library

---

### Week 4: Settings + Polish + Launch

**Days 1-2: Settings Tabs**
- [ ] Google Drive panel + `/api/settings/gdrive` endpoints
- [ ] Space Protection panel + `/api/settings/space` endpoints
- [ ] Background Services panel + `/api/settings/services` endpoints
- [ ] Adaptive Learning panel (use existing `/api/learning/*`)
- [ ] Deduplication panel + `/api/dedup/*` endpoints
- [ ] Test: Change confidence mode, reconnect Drive, view service logs

**Days 3-4: Polish & Animations**
- [ ] Implement Framer Motion animations
- [ ] Keyboard shortcuts (Cmd+K for search, Cmd+U for upload, etc.)
- [ ] Mobile responsive adjustments (Tailwind breakpoints)
- [ ] Dark/light mode toggle (optional, default dark)
- [ ] Loading skeletons for all async content
- [ ] Error boundaries for graceful failures

**Days 5-7: Testing & Optimization**
- [ ] E2E test critical flows (upload → classify → undo)
- [ ] Performance: Code splitting, lazy loading
- [ ] Accessibility: ARIA labels, keyboard navigation
- [ ] Final UI polish: spacing, colors, animations
- [ ] User testing with Ryan
- [ ] Bug fixes + refinements

**Week 4 Deliverable:** ✅ Production-ready UI replacing all 70+ CLI tools

---

## ✅ Success Criteria

### Functional Requirements

- [ ] **Zero CLI needed** - Every command has UI equivalent
- [ ] **File upload** - Drag & drop any file type
- [ ] **Classification** - Interactive questions when uncertain
- [ ] **Batch processing** - Organize 100+ files at once
- [ ] **Search** - Unified search across files, emails, VEO clips
- [ ] **Rollback** - Undo any operation, even weeks later
- [ ] **Analysis** - See Gemini Vision + audio analysis results
- [ ] **VEO management** - Upload, edit, organize video prompts
- [ ] **Settings control** - Manage all system settings visually
- [ ] **Service monitoring** - See status of background services

### UX Requirements

- [ ] **Liquid glass aesthetic** - Frosted glass cards, subtle animations
- [ ] **ADHD-friendly** - Binary choices, immediate feedback, forgiving
- [ ] **Fast** - <100ms UI response, lazy loading for heavy content
- [ ] **Accessible** - Keyboard navigation, screen reader support
- [ ] **Mobile-responsive** - Works on tablet (not phone priority)
- [ ] **Reliable** - Error boundaries, graceful degradation

### Technical Requirements

- [ ] **TypeScript** - 100% typed (no `any`)
- [ ] **React Query** - All API calls cached, optimistic updates
- [ ] **Zod validation** - All forms validated client-side
- [ ] **Code splitting** - Route-based, <500KB initial bundle
- [ ] **Testing** - Unit tests for critical utils, E2E for main flows

---

## 🚀 Development Workflow

### Starting Point

Current codebase:
- `frontend/` exists with `index.html`, `app.js`, `style.css` (old UI)
- `backend/main.py` runs FastAPI with some existing endpoints
- 70+ Python modules in root directory (the CLI tools)

### Phase 1 Approach: Parallel Development

**Option A: Fresh Frontend (Recommended)**
1. Create `frontend_v2/` directory with Vite
2. Keep old `frontend/` until new one is complete
3. FastAPI serves both: `/old` and `/` (new)
4. Gradual migration, low risk

**Option B: In-Place Upgrade**
1. Backup `frontend/` to `frontend_legacy/`
2. Replace with Vite setup in `frontend/`
3. Higher risk but cleaner

**Recommendation:** Option A - fresh start, less risk

### Backend Service Layer Strategy

Instead of rewriting Python modules, **wrap them**:

```python
# backend/services/organizer_service.py
from interactive_organizer import InteractiveOrganizer
from unified_classifier import UnifiedClassifier

class OrganizerService:
    """Wraps existing CLI tools for API use."""

    def __init__(self):
        self.organizer = InteractiveOrganizer()
        self.classifier = UnifiedClassifier()

    async def classify_file(self, file_path: str) -> ClassificationResult:
        """Classify a single file."""
        # Call existing methods
        result = await self.classifier.classify(file_path)
        return ClassificationResult(
            category=result['category'],
            confidence=result['confidence'],
            reasoning=result['reasoning']
        )

    async def organize_file(self, file_path: str, category: str):
        """Move file to organized location."""
        await self.organizer.organize(file_path, category)
```

**Benefits:**
- Reuse battle-tested Python logic
- Faster development (don't rewrite 31,415 lines)
- Easier debugging (Python code unchanged)

### API-First Development

For each feature:
1. **Design API contract** (OpenAPI schema)
2. **Implement backend service** (wrap Python module)
3. **Create API endpoint** (FastAPI route)
4. **Test with curl/Postman**
5. **Build frontend component** (React)
6. **Integrate with React Query**

### State Management Pattern

```typescript
// hooks/useFileOrganizer.ts
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function useFileOrganizer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/organize/upload', {
        method: 'POST',
        body: formData
      })
      return res.json()
    },
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries(['recent-activity'])
      queryClient.invalidateQueries(['organize-stats'])
    }
  })
}

// Usage in component
function FileUpload() {
  const { mutate, isLoading, isError } = useFileOrganizer()

  const handleDrop = (files: File[]) => {
    files.forEach(file => mutate(file))
  }

  return <Dropzone onDrop={handleDrop} />
}
```

---

## 📚 Reference Materials

### Design Inspiration
- [macOS Big Sur Design](https://www.apple.com/macos/big-sur/) - Frosted glass aesthetic
- [Raycast UI](https://raycast.com) - Command palette, keyboard shortcuts
- [Linear](https://linear.app) - Clean, fast, purposeful animations
- [ShadCN UI](https://ui.shadcn.com) - Component library

### Code Examples
- [TanStack Query Docs](https://tanstack.com/query/latest) - Server state management
- [Framer Motion Gallery](https://www.framer.com/motion/) - Animation examples
- [Tailwind UI](https://tailwindui.com) - Component patterns

### Existing Codebase References
- `CLAUDE.md` - Complete system documentation
- `AUDIO_ANALYSIS_USAGE_GUIDE.md` - Audio analyzer CLI usage
- `GEMINI_VISION_SETUP.md` - Vision analyzer setup
- `backend/library_api.py` - Existing VEO API endpoints
- `frontend/ui_library/index.tsx` - Started VEO UI

---

## 🔥 Critical Success Factors

### 1. Start with Dashboard + Basic Organize
Don't try to build everything at once. Get the core loop working:
- Upload file → Classify → Organize → See it in Dashboard

### 2. Rollback Center is Non-Negotiable
This is the trust mechanism. If this doesn't work flawlessly, the whole system fails.

### 3. Test with Real Files
Use Ryan's actual PDFs, contracts, emails, audio files. Don't test with `test.txt`.

### 4. ADHD-First UX Review
After each component:
- Can I do this without thinking?
- Is it obvious what will happen when I click?
- Can I undo it if I'm wrong?
- Does it cause anxiety? (If yes, redesign)

### 5. Performance Matters
Ryan has ADHD - slow UIs create frustration and abandonment.
- Target: <100ms UI response for all interactions
- Use optimistic updates (React Query)
- Lazy load heavy components (Monaco editor, D3 graph)

---

## 🎬 Next Steps

1. **Create Vite project**: `npm create vite@latest frontend_v2 -- --template react-ts`
2. **Install dependencies**: See Frontend Stack section
3. **Create design tokens**: `tailwind.config.ts` with liquid glass variables
4. **Build Layout component**: Sidebar + Header + Outlet
5. **Implement Dashboard**: First page Ryan will see
6. **Start with Day 1 tasks**: Follow Week 1 plan above

---

## 📞 Communication Protocol

### Daily Updates
Post in project channel:
- What shipped today
- Blockers (if any)
- Next day's goals

### Questions
When stuck:
1. Check existing Python code (it probably does what you need)
2. Review `CLAUDE.md` for system architecture
3. Ask specific questions with context

### Demos
Weekly demo to Ryan:
- Screen recording of new features
- Request feedback on UX
- Adjust based on his ADHD experience

---

## 🏆 Definition of Done

This project is complete when:

1. ✅ Ryan can use the system for 1 week without opening the terminal
2. ✅ All 70+ CLI commands have UI equivalents
3. ✅ Rollback system works flawlessly (tested with real mistakes)
4. ✅ Search finds files across all sources (local, Drive, emails, VEO)
5. ✅ UI feels fast, beautiful, and calming (not overwhelming)
6. ✅ System status is always visible (no "is this even working?" anxiety)

**Final Test:** Ask Ryan: "Would you recommend this to another person with ADHD?"

If yes, **mission accomplished**. 🎉

---

*Last Updated: 2025-10-29*
*Version: 1.0*
*Status: Ready for implementation*
