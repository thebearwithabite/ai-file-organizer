# 🧭 **Sprint 3.2 — Full Wiring Pass**

**Goal:** Make the system fully self-contained and "actually learning" by connecting all backend learning hooks, background monitors, and missing UI toggles.

**Status:** 🚧 In Progress

---

## 🎯 OBJECTIVE

Bring AI File Organizer v3.1 to functional parity between CLI and UI:

* ✅ Fix empty database issues (learning + rollback)
* ✅ Ensure background automation runs continuously
* ✅ Expose critical CLI features through clean UI controls
* ✅ Eliminate ADHD friction points: missing toggles, invisible automation, silent failures

---

## ⚙️ BACKEND TASKS

### 1 — **Learning Hook Integration**

**Status:** ⏳ Pending
**Files:** `api/services.py`, `universal_adaptive_learning.py`

On every classification confirmation in `TriageService.classify_file()` or `confirm_classification()`, call:

```python
learning_system.record_classification(
    file_path=path,
    predicted_category=suggested_category,
    confirmed_category=user_choice,
    confidence=confidence_score
)
```

If DB missing → auto-initialize (`learning_events.db`).

**Acceptance Test:**
- Move ≥ 1 file through triage
- `/api/settings/learning-stats` should show non-zero counts

---

### 2 — **Rollback DB Auto-Init**

**Status:** 🔄 Partially Complete
**Files:** `easy_rollback_system.py`, `main.py`

**✅ Completed:**
- Added error handling for missing tables in stats endpoint (commit 36a8071)
- Endpoint now returns zeros instead of 500 errors

**⏳ Still Needed:**
- On startup, verify/create `rollback.db` with `file_operations` table
- Add helper:

```python
def ensure_rollback_tables():
    conn.execute("""CREATE TABLE IF NOT EXISTS file_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        operation_type TEXT NOT NULL,
        source_path TEXT NOT NULL,
        destination_path TEXT,
        file_name TEXT NOT NULL,
        metadata TEXT
    )""")
```

- Call in `main.py` on app init

**Acceptance Test:**
Fresh install → `/api/settings/database-stats` returns 0-values (not error) ✅

---

### 3 — **Launch Adaptive Background Monitor on Server Start**

**Status:** ⏳ Pending
**Files:** `adaptive_background_monitor.py`, `main.py`

Import and start in daemon thread:

```python
from adaptive_background_monitor import AdaptiveBackgroundMonitor
threading.Thread(target=AdaptiveBackgroundMonitor.start, daemon=True).start()
```

Make path configurable via `.env` or `config.json` (`AUTO_MONITOR_PATHS`).

**Acceptance Test:**
- Logs show: `INFO: AdaptiveBackgroundMonitor started (watching …)`
- File drops into Downloads → auto-classified

---

### 4 — **New API Endpoints**

**Status:** ⏳ Pending

| Endpoint                        | Action   | Backend Binding                                 | Status | Notes                  |
| ------------------------------- | -------- | ----------------------------------------------- | ------ | ---------------------- |
| `/api/settings/confidence-mode` | GET/POST | `confidence_system.get()/set()`                 | ⏳      | Toggle current mode    |
| `/api/system/deduplicate`       | POST     | `automated_deduplication_service.scan()`        | ⏳      | Return duplicates list |
| `/api/system/space-protection`  | GET/POST | `emergency_space_protection.status()/protect()` | ⏳      | Show / trigger cleanup |

Return JSON payloads with `{status,message,data}`.

**Acceptance Test:**
All three endpoints return 200 and correct keys in response.

---

## 🖥 FRONTEND TASKS

### 5 — **Settings Page: Confidence Mode Switcher**

**Status:** ⏳ Pending
**Files:** `frontend_v2/src/pages/Settings.tsx`

- Add dropdown with four modes (`Never`, `Minimal`, `Smart`, `Always`)
- Fetch & POST to `/api/settings/confidence-mode`
- Show color indicator (🟥 Never → 🟩 Always)

**Acceptance Test:**
Switching modes updates backend config + toast confirmation.

---

### 6 — **Duplicates Dashboard**

**Status:** ⏳ Pending
**Files:** `frontend_v2/src/pages/Duplicates.tsx` (new)

- Fetch from `/api/system/deduplicate`
- Display duplicate groups: filename, path, size, preview
- Buttons: **"Keep 1 / Clean Others"**, **"View In Finder"**
- Confirm → POST clean action (moves to safe recycler)

**Acceptance Test:**
Run scan → list shows groups → click Clean → toast success → files gone.

---

### 7 — **Disk Space Widget (Dashboard)**

**Status:** ⏳ Pending
**Files:** `frontend_v2/src/pages/Dashboard.tsx`

- Add horizontal bar indicator using `/api/system/space-protection`
- Color-code thresholds (🟢 <80%, 🟡 80-95%, 🔴 >95%)
- Add **"Free Up Space"** button → POST protect

**Acceptance Test:**
At >90%, shows alert; click button reduces usage % in follow-up call.

---

### 8 — **Rollback History Panel**

**Status:** ⏳ Pending
**Files:** `frontend_v2/src/pages/Settings.tsx` (after Database Stats section)

- Fetch `/api/rollback/list` (later added to backend)
- Table columns: Time | Action | File | Undo Button
- On Undo → POST `/api/rollback/undo/<id>`

**Acceptance Test:**
Click Undo → file returns to original path; toast shows "Restored".

---

## 🔄 DEVOPS / CONFIG

### 9 — **Autostart Sequence**

**Status:** ⏳ Pending

- Ensure `.ai_organizer_config` folder exists at launch
- Add startup log:

```
✅ System Ready: Learning + Rollback DBs initialized | Monitor active
```

---

## ✅ DELIVERABLES

- [ ] Updated `main.py` with auto-init + monitor thread
- [ ] New API routes (3)
- [ ] Updated Settings.tsx (UI switcher + rollback panel + space widget)
- [ ] New Duplicates page
- [ ] Confirmed learning writes and database stats no longer zero

---

## 🧩 ACCEPTANCE CRITERIA

| Test # | Scenario                                              | Expected Result | Status |
| ------ | ----------------------------------------------------- | --------------- | ------ |
| 1      | Organize a file via UI → Learning stats increment     | ✅               | ⏳      |
| 2      | Switch confidence mode → Persistent change in config  | ✅               | ⏳      |
| 3      | Disk usage > 95% → UI alert + cleanup works           | ✅               | ⏳      |
| 4      | Duplicate scan shows groups → Safe delete works       | ✅               | ⏳      |
| 5      | Rollback history panel lists ops → Undo restores file | ✅               | ⏳      |
| 6      | Adaptive monitor auto-classifies new files            | ✅               | ⏳      |

---

## 📝 PROGRESS LOG

### 2025-11-05
- ✅ **Fixed database stats endpoint** (commit 36a8071)
  - Added try/except for missing tables
  - Endpoint now gracefully returns zeros for fresh installations
  - No more 500 errors when tables don't exist yet

---

## 🔗 RELATED DOCUMENTS

- [CLAUDE.md](/CLAUDE.md) - System architecture overview
- [Phase 1 Implementation](/docs/Phase_1_Implementation.md)
- [Phase 2 Vision Integration](/docs/Phase_2_Vision_Integration.md)

---

**Last Updated:** 2025-11-05
**Sprint Lead:** Claude Code AI Assistant
