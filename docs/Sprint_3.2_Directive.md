---
title: "Sprint 3.2 — Full Wiring Pass"
date: 2025-11-04
status: In Progress
phase: 3.2
owner: the user Thomson
---

# 🧭 Sprint 3.2 — Full Wiring Pass

**Objective:**
Finalize the backend integration and UI wiring needed to make the system *self-learning*, *auto-monitoring*, and *feature-complete* between CLI and web.

---

## ✅ Context Summary

- Fixed `/api/settings/database-stats` to return zeros instead of 500s on fresh installs.
- Next: auto-create missing tables, hook up learning event recording, and enable background monitor.
- This sprint completes backend prerequisites for the ADHD-friendly UI sprint that follows.

---

## ⚙️ Backend Tasks

### 1. Learning Hook Integration
**Files:** `api/services.py`, `universal_adaptive_learning.py`

Hook the learning system into every confirmed classification:

```python
learning_system.record_classification(
    file_path=path,
    predicted_category=suggested_category,
    confirmed_category=user_choice,
    confidence=confidence_score,
)
```

Auto-init `learning_events.db` if missing.
**Test:** Move a file → `/api/settings/learning-stats` increments counters.

---

### 2. Rollback DB Auto-Init

**Files:** `easy_rollback_system.py`, `main.py`

Create helper:

```python
def ensure_rollback_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS file_operations (...columns...)""")
```

Call on startup.
**Test:** Fresh install → `/api/settings/database-stats` returns valid zeros, no error.

---

### 3. Background Monitor Auto-Start

**Files:** `adaptive_background_monitor.py`, `main.py`

```python
from adaptive_background_monitor import AdaptiveBackgroundMonitor
threading.Thread(target=AdaptiveBackgroundMonitor.start, daemon=True).start()
```

Optional config: `AUTO_MONITOR_PATHS` in `.env`
**Test:** Log shows monitor startup; dropping file in staging triggers auto-classification.

---

### 4. API Endpoints

| Endpoint                        | Description           | Backend Bind                                  |
| ------------------------------- | --------------------- | --------------------------------------------- |
| `/api/settings/confidence-mode` | GET/POST current mode | `confidence_system.get/set()`                 |
| `/api/system/deduplicate`       | Scan for duplicates   | `automated_deduplication_service.scan()`      |
| `/api/system/space-protection`  | Disk status / cleanup | `emergency_space_protection.status/protect()` |

All return `{status, message, data}`.

---

## 🖥 Frontend Tasks

### 5. Settings → Confidence Mode Switcher

Dropdown with modes (Never, Minimal, Smart, Always).
Sync to `/api/settings/confidence-mode`.

### 6. New Duplicates Page

List duplicate groups, allow safe clean-up via API.
Integrate safe recycler for undo.

### 7. Dashboard → Disk Space Widget

Fetch `/api/system/space-protection`.
Visual gauge + "Free Up Space" button.

### 8. Settings → Rollback Panel

Fetch rollback history, show Undo buttons.
Hook into new `/api/rollback` endpoints.

---

## 🧩 Acceptance Criteria

| # | Scenario               | Expected Result               |
| - | ---------------------- | ----------------------------- |
| 1 | Organize file via UI   | Learning stats increment      |
| 2 | Switch confidence mode | Config persists + toast       |
| 3 | Disk usage >95%        | Alert + cleanup reduces usage |
| 4 | Duplicate scan         | Groups display + safe delete  |
| 5 | Rollback panel         | Undo restores file            |
| 6 | Background monitor     | Auto-classifies new files     |

---

## 🧱 Next Steps

1. Commit existing database-stats fix ✅
2. Implement **Tasks 1-3** (learning hooks + auto-init + monitor)
3. Verify stats update and monitor logs
4. Then start **Frontend Sprint 3.3 — UI Integration and Controls**

---

## 📝 Progress Log

### 2025-11-05
- ✅ **Fixed database stats endpoint** (commit 36a8071)
  - Added try/except for missing tables
  - Endpoint now gracefully returns zeros for fresh installations
  - No more 500 errors when tables don't exist yet
- ✅ **Created Sprint 3.2 directive** (commit d9028c5)
  - Comprehensive sprint plan with 9 tasks
  - Acceptance criteria and progress tracking
  - Updated with enhanced formatting (YAML front matter)

---

*Logged by Claude (backend agent) · Drafted by the user Thomson · Reviewed by Max (system supervisor)*
