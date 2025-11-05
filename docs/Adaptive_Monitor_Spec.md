---
title: "Adaptive Monitor Behavior & Configuration Specification"
date: 2025-11-05
status: Active
phase: 3.2 → 3.3
owner: Ryan Thomson
---

# 🔭 Adaptive Monitor Behavior & Configuration

## Purpose

Clarify exactly what the `AdaptiveBackgroundMonitor` does, which folders it watches, and how it will evolve in Sprint 3.3.

---

## Current Behavior (v3.2) ✅

**Constructor:** `AdaptiveBackgroundMonitor(base_dir=None, interval=5)`

**Default Root:** `get_ai_organizer_root()` (e.g. `~/Documents/GDRIVE_STAGING`)

**Automatically Watches:**
- `${base_dir}/Downloads_Staging`
- `${base_dir}/Desktop_Staging`
- `${base_dir}/Documents_Staging`

**Learns From:**
- Manual file moves/renames within those staging folders
- System-initiated changes the organizer makes (via the rollback logger)

**Limitations:**
- Does not yet monitor the real OS Desktop or Downloads
- Does not auto-start unless triggered by FastAPI startup event
- Health status available only in logs, not via API

---

## Intended Behavior (v3.3 / upcoming) 🎯

### Multi-Path Support
Accept explicit folder list through `AUTO_MONITOR_PATHS` (comma-separated).

**Example:**
```bash
AUTO_MONITOR_PATHS=~/Desktop,~/Downloads,~/Documents/GDRIVE_STAGING
```

### Daemon Startup
Each path spawns its own watcher thread on API startup.

### Health Endpoint
`/api/system/monitor-status` → returns:
- Active paths being monitored
- Uptime for each watcher
- Last event timestamp per path
- Learning statistics

**Example Response:**
```json
{
  "status": "active",
  "watchers": [
    {
      "path": "/Users/ryan/Desktop",
      "status": "running",
      "uptime_seconds": 3600,
      "last_event": "2025-11-05T10:30:15Z",
      "events_processed": 42
    },
    {
      "path": "/Users/ryan/Downloads",
      "status": "running",
      "uptime_seconds": 3600,
      "last_event": "2025-11-05T10:45:22Z",
      "events_processed": 18
    }
  ],
  "total_events": 60,
  "learning_system_active": true
}
```

### UI Integration
Dashboard widget displays:
- Monitor activity indicator (green = active, gray = inactive)
- Real-time event stream
- Learning statistics (files observed, patterns discovered)
- Quick controls (pause/resume monitoring)

---

## Design Rationale

The monitor is meant to be the **"always-on subconscious"** of the organizer:

1. **Observe** manual activity (what the user does instinctively)
2. **Learn** those preferences (feed `UniversalAdaptiveLearning`)
3. **Apply** learned rules proactively (auto-file new items)

It should feel **invisible but responsive** — like your filesystem quietly taking notes for you.

### ADHD-Friendly Design Principles

- **Zero cognitive load:** Works in background without user intervention
- **Non-intrusive:** Never blocks or interrupts workflow
- **Transparent:** Clear visibility into what it's learning
- **Forgiving:** Easy to pause/disable if needed
- **Helpful:** Reduces manual organization burden over time

---

## Implementation Notes

### Refactored Constructor

`AdaptiveBackgroundMonitor` will be refactored to accept either:

```python
# Single base directory (current v3.2 behavior)
AdaptiveBackgroundMonitor(base_dir="...")

# Multiple explicit paths (v3.3 enhancement)
AdaptiveBackgroundMonitor.from_paths(["~/Desktop", "~/Downloads"])
```

### Internal Architecture

**Shared Watcher Logic:**
- Move to a shared `_watch_path()` method
- Each path gets its own thread with independent lifecycle
- Thread-safe event queue for processing

**Event Tagging:**
Logs will tag events with `SOURCE=manual|auto|external` for cleaner analytics:
- `manual`: User moved/renamed file directly
- `auto`: System organized file via classifier
- `external`: Changes from other apps (iCloud, Dropbox, etc.)

### Configuration Management

**Environment Variables:**
```bash
# Enable/disable monitoring
ADAPTIVE_MONITOR_ENABLED=true

# Paths to watch (comma-separated, supports ~ expansion)
AUTO_MONITOR_PATHS=~/Desktop,~/Downloads

# Scan interval in seconds
AUTO_MONITOR_INTERVAL=5

# Event processing batch size
MONITOR_BATCH_SIZE=10
```

**Runtime Configuration:**
```python
# Via API (Sprint 3.3)
POST /api/system/monitor-config
{
  "enabled": true,
  "paths": ["/Users/ryan/Desktop", "/Users/ryan/Downloads"],
  "interval": 5
}
```

---

## Integration Points

### Phase 1 Systems (Current)
- ✅ `UniversalAdaptiveLearning` — Receives classification events
- ✅ `ADHDFriendlyConfidenceSystem` — Uses learned patterns for confidence scoring
- ✅ `EmergencySpaceProtection` — Monitors for disk space issues

### Phase 2 Systems (Current)
- ✅ `VisionAnalyzer` — Processes image/video files
- ✅ `AudioAnalyzer` — Processes audio files

### Phase 3 Systems (Sprint 3.3)
- 🔄 Dashboard UI — Real-time status widget
- 🔄 Settings UI — Configuration controls
- 🔄 Triage UI — Manual override for uncertain classifications

---

## Testing Strategy

### Unit Tests
```python
def test_monitor_single_path():
    """Verify monitor watches single directory"""

def test_monitor_multiple_paths():
    """Verify monitor handles multiple directories"""

def test_monitor_learns_from_moves():
    """Verify manual moves trigger learning events"""

def test_monitor_respects_confidence_threshold():
    """Verify monitor uses confidence system correctly"""
```

### Integration Tests
```python
def test_monitor_with_classifier():
    """Verify end-to-end file detection → classification → learning"""

def test_monitor_api_health_endpoint():
    """Verify /api/system/monitor-status returns correct data"""

def test_monitor_config_persistence():
    """Verify configuration survives restarts"""
```

### User Acceptance Tests
1. Drop file in monitored folder → verify event logged
2. Manually move file → verify learning event recorded
3. Check dashboard → verify monitor status shows active
4. Pause monitor via UI → verify monitoring stops
5. Resume monitor → verify monitoring resumes

---

## Performance Considerations

### Resource Usage
- Each watcher thread: ~2-5MB memory
- Event processing: ~100-500 events/second
- Learning updates: Async, non-blocking

### Optimization Strategies
1. **Debouncing:** Batch rapid file changes (e.g., bulk downloads)
2. **Throttling:** Limit learning updates to 1/second max
3. **Lazy Loading:** Only load classifiers when needed
4. **Event Filtering:** Ignore temp files, system files, hidden files

### Scaling Limits
- Recommended: ≤5 monitored paths
- Maximum: 10 paths (beyond this, use multiple instances)
- File event rate: Designed for <1000 events/hour per path

---

## Security & Privacy

### Data Collection
- **What's collected:** File paths, timestamps, classification results
- **What's NOT collected:** File contents, user identity, metadata
- **Storage:** Local only (no cloud sync of learning data)

### Path Safety
- All paths validated against base directory
- Symlink traversal protection
- Hidden file/folder exclusion by default

### User Control
- Full transparency via health endpoint
- Easy pause/disable controls
- Export/delete learning data on demand

---

## Migration Path (v3.2 → v3.3)

### Phase 1: Backend Enhancement (Current Sprint)
- ✅ Fix initialization bug (commit 15c4ddc)
- ✅ Verify monitor starts without errors
- ✅ Confirm learning events recorded

### Phase 2: Multi-Path Support (Sprint 3.3)
- Refactor constructor to accept path list
- Add health endpoint `/api/system/monitor-status`
- Update `.env` parsing for comma-separated paths
- Add runtime configuration API

### Phase 3: UI Integration (Sprint 3.3)
- Dashboard widget for monitor status
- Settings page for configuration
- Real-time event stream display
- Pause/resume controls

### Phase 4: Advanced Features (Future)
- Pattern visualization dashboard
- Learning effectiveness metrics
- Suggested organizational rules
- Export learning data to Excel

---

## Success Metrics

### Technical Metrics
- Monitor uptime: >99% when enabled
- Event processing latency: <100ms average
- Learning update frequency: 1-5/minute during active use
- Memory footprint: <50MB total for all watchers

### User Experience Metrics
- Files auto-organized: % increase over manual organization
- Confidence improvement: Learning system accuracy over time
- User corrections: Decreasing over time (system learning)
- Time saved: Reduction in manual file management time

### ADHD Impact Metrics
- Reduced decision fatigue (fewer manual choices needed)
- Improved file findability (semantic search success rate)
- Lower organizational anxiety (fewer misplaced files)
- Increased trust (accurate auto-organization)

---

## Related Documents

- [`Sprint_3.2_Directive.md`](./Sprint_3.2_Directive.md) - Backend implementation tasks
- [`universal_adaptive_learning.py`](../universal_adaptive_learning.py) - Learning system integration
- [`confidence_system.py`](../confidence_system.py) - Confidence threshold logic
- [`adaptive_background_monitor.py`](../adaptive_background_monitor.py) - Monitor implementation

---

*Last updated: 2025-11-05*
*Status: Active — guiding Sprint 3.3 implementation*
*Next review: Upon completion of Sprint 3.3*
