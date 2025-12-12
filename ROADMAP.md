
## A. Priority Ladder — What Came First

If you’re low on bandwidth, this is the short version:

**DO FIRST (Unblock everything):**

1. ✅ **Fix Backend Startup**
2. ✅ **Connect Background Monitor → API → Frontend Widget**
3. ✅ **Fix the critical monitor / triage bugs**
4. ✅ **Enforce AI_METADATA_SYSTEM path & kill rogue filesystem behavior**
5. ✅ **Run / verify dedupe & migration integrity scripts**

Everything else is “polish / visibility / UX.”

Now I’ll fold your checklist into a clearer, ordered sprint.

---

## B. Section 0 — Environment / Startup Unblock

**Goal:** Make sure the system actually runs. No monitors, no UI, no learning without this.

**Tasks:**

* **Fix Backend Startup**

  * Fix `NameError: name 'Request' is not defined` in `main.py`.
  * Verify backend starts cleanly with no import/runtime errors.

* **Resolve Port / Process Conflicts**

  * Kill zombie process on port 8000.
  * Confirm `uvicorn`/server binds to 8000 without conflict.

Once this is green, you can move to the monitor + UI integration.

---

## C. Section 1 — Background Monitor & Frontend Integration

**Goal:** The Enhanced/Adaptive background monitor is running, exposed by API, and visible in the frontend widget.

### 1.1 Backend Monitor Wiring

* **Verify Background Monitor API Integration**

  * Check `main.py` for monitor initialization (e.g., `EnhancedBackgroundMonitor` or `AdaptiveBackgroundMonitor` instance).
  * Check `api/` for status endpoint presence (`/api/monitor/status` or equivalent).
  * Ensure `MonitorStatus` type (Pydantic / dataclass) matches the actual backend response.

* **Implement/Fix Monitor Status Endpoint**

  * Create or update API route for monitor status.
  * Wire it directly to the `EnhancedBackgroundMonitor` (or `AdaptiveBackgroundMonitor`) instance.
  * Make sure it returns:

    * Overall health
    * Last processed event
    * Queue length / pending items (if available)
    * Any error flags

### 1.2 Frontend Widget

* **Verify Frontend Monitor Widget**

  * Check `MonitorStatusWidget.tsx`:

    * Data fetching points at the correct endpoint.
    * Types align with `MonitorStatus` from backend.
  * Ensure consistent shape:

    * No optional fields blowing up the UI.
    * Reasonable handling of “loading / error / empty” states.

### 1.3 Fix Core Monitor Bugs

* **Fix `AdaptiveBackgroundMonitor` inheritance bug**

  * Ensure `AdaptiveBackgroundMonitor` correctly extends `EnhancedBackgroundMonitor` (and/or base `background_monitor`).
  * Fix the `_should_process_file` attribute error (stale process/reload issue).
  * Confirm class hierarchy:
    `background_monitor` → `EnhancedBackgroundMonitor` → `AdaptiveBackgroundMonitor`.

* **Explain “0 adaptive rules” behavior**

  * Confirm that “0 rules” on startup is expected (rules generated hourly / requires uptime + events).
  * Make sure the UI doesn’t misrepresent this as a hard error.

**Checkpoint:**
At the end of this section, you should be able to:

* Start backend successfully.
* Hit a monitor status endpoint.
* See live-ish monitor data in `MonitorStatusWidget`.

---

## D. Section 2 — Triage, PDF, and Recent Activity

**Goal:** Triage actually populates, PDF extraction doesn’t crash, and you can see what’s happening.

### 2.1 Triage & PDF

* **Fix PDF metadata JSON serialization error**

  * Ensure PDF metadata → JSON is fully serializable (convert `datetime`, custom objects, etc. to plain types).
  * Harden PDF extraction so persistent error is removed.

* **Verify Triage Population**

  * Confirm that:

    * New files are being picked up.
    * They appear in Triage UI.
    * The data shape matches what the UI expects.

* **Restore 5-Level Deep Classification in Triage UI**

  * Ensure Triage UI can display full nested classification depth (up to 5 levels).
  * Fix any mapping / flattening that was cut off.

* **Restore Predictive Text for Project/Episode fields**

  * Re-enable predictive/auto-complete for Project / Episode input.
  * Make sure it draws from `KNOWN_PROJECTS` or equivalent.

### 2.2 Recent Activity / Visibility

* **Implement Recent Activity UI**

  * Expose a `/api/recent-activity` or equivalent in backend (using RollbackService and/or learning events).
  * Create `RecentActivityWidget` in frontend:

    * Show key events (moves, renames, triage actions, rollbacks).
    * Verify “original → new” tracking is clear.

* **Fix file renaming logic**

  * Confirm that files are **actually** being renamed on disk according to your naming protocol.
  * Fix any mismatch between “planned name” vs actual FS operation.

* **Verify Database Stats / “Recent” Meaning**

  * Make sure the dashboard explains:

    * 1000 learning events vs 5 rollback ops.
    * “Recent = 0” = “No new events in last 7 days,” not “system dead.”

---

## E. Section 3 — Librarian Consolidation

**Goal:** Kill redundant librarian classes and put behavior in one coherent set.

**Tasks:**

* **Analyze and Consolidate Librarian Files**

  * Review:

    * `vector_librarian.py`
    * `hybrid_librarian.py`
    * `gdrive_librarian.py`
    * `enhanced_librarian.py`
  * Decide:

    * Which is the *canonical* librarian.
    * Which ones can be:

      * Merged
      * Deprecated
      * Kept as thin adapters.

* **Move Test Files**

  * Move `test_*.py` files into `tests/` directory.
  * Adjust imports if needed.

This sets up the “one librarian, many adapters” architecture.

---

## F. Section 4 — Drive Status, GDrive, and Broken UI

**Goal:** Google Drive is correctly wired, status is accurate, and key UI surfaces don’t lie.

### 4.1 Drive Status & Events

* **Fix Drive Status in `api/services.py`**

  * Remove hardcoded “local-only” Drive status.
  * Return real Drive status (connected, syncing, error).

* **Investigate Event Count Reset / Persistence**

  * Check why event counts reset.
  * Confirm DB persistence + correct time window for “Recent Activity.”

* **Add “Recent Activity” Visibility**

  * Hook Drive events into the same Recent Activity UI where appropriate.

### 4.2 Investigate Broken UI

* Investigate:

  * Google Drive status not loading.
  * Search not working (API and UI).
  * Rollback Center not working.
  * Settings page “all sinners” bug/text/logic.
  * Triage display issues (e.g., missing rows, bad filters, stale components).

This is the “walk the app and fix what’s obviously broken” pass.

---

## G. Section 5 — Metadata Prime Directive & Path Hygiene

**Goal:** All metadata lives in `AI_METADATA_SYSTEM`. No rogue DBs, no silent path drift.

**Tasks:**

* **Enforce Local Metadata Prime Directive**

  * Audit `bulletproof_deduplication.py` for DB path violations.
  * Fix it to always use `AI_METADATA_SYSTEM` path.
  * Delete legacy `deduplication.db` from GDrive.

* **Audit Other Components**

  * Confirm `gdrive_integration`, `easy_rollback_system`, etc. also respect `AI_METADATA_SYSTEM` and not random locations.

---

## H. Section 6 — iCloud Migration & Deduplication

**Goal:** Deduplicate safely, run migration, verify integrity, then clean up.

### 6.1 Pre-Migration iCloud Dedup

* **Dry Run `bulletproof_deduplication.py` on iCloud (Threshold 0.80)**

  * Found: 5,335 duplicates.
  * Safe to delete: 578 (same as 0.3) → clear separation.
  * Space to recover: 1.8 GB.

* **Review Dry Run Stats**

  * Sanity check: do the numbers make sense?

* **Execute Deduplication**

  * Delete 578 files.
  * Confirm 1.8 GB reclaimed.

### 6.2 Deduplication: `99_STAGING_EMERGENCY`

* **Dry Run on `99_STAGING_EMERGENCY` (Threshold 0.80)**

  * Found 373 duplicates (371 are 0-byte).
  * Safe to delete: 371.
  * Space to recover: ~0.5 MB (small, but important for cleanup).

* **Review Dry Run Stats**

* **Execute Deduplication**

  * Delete 371 files.

### 6.3 Run Live Migration

* **Execute `migrate_icloud.py` (Live Mode)**

  * Monitor progress (prior crash due to timeout / 0-byte files).
  * Ensure logs are written for later integrity checks.

* **Verify Low-Confidence Triage**

  * Manually review low-confidence classifications after migration.

---

## I. Section 7 — Migration Integrity Verification

**Goal:** Prove to yourself nothing important got silently broken.

* **Create `scripts/verify_migration_integrity.py`**

  * Scan `99_STAGING_EMERGENCY/iCloud_Duplicates` for 0-byte files.
  * For each, verify presence of a valid copy in GDrive via `deduplication.db`.
  * Produce a clear report (counts, any discrepancies).

* **Cleanup Safe Duplicates**

  * Create `scripts/cleanup_safe_duplicates.py`.
  * Execute cleanup.
  * Verify 0-byte files are gone.

---

## J. Section 8 — Rogue System Creation & Smart Organization

**Goal:** Fix the Nov 28 rogue system and fold “Smart” organization back into the plan.

### 8.1 Rogue System

* **Identify Source**

  * Confirm `gdrive_integration.py` fallback to `~/Documents`.

* **Disable Fallback**

  * Remove / disable fallback to `~/Documents` in `gdrive_integration.py`.

* **Recover Rogue Files**

  * Move `~/Documents/01_ACTIVE...` etc. to `99_STAGING_EMERGENCY/Recovered_Rogue_System`.

* **Cleanup Rogue Folders**

  * Attempt to delete empty rogue folders in `~/Documents`.

    * Skip non-empty for safety, log paths.

### 8.2 Smart Organization (99_TEMP_PROCESSING)

* **Investigate Smart Organization in `99_TEMP_PROCESSING`**

  * Analyze folder structure (found “Smart” folders).
  * Identify responsible code component (likely `UnifiedClassificationService` + Triage Center).
  * Plan system-wide implementation:

    * Add to `KNOWN_PROJECTS`.
    * Decide which patterns you want to *keep* and scale.

---

## K. Section 9 — Orchestration & System Audit

**Goal:** Wire all these subsystems into a predictable staging workflow and answer your own “Is this thing actually learning?” questions.

* **Orchestrate AI Librarian Staging Workflow**

  * Verify components:

    * `gdrive_integration`
    * `bulletproof_deduplication`
    * `easy_rollback_system`.
  * API Audit:

    * Check `/api/search`, `/api/upload`, `/api/triage/...`, `/api/recent-activity`, `/api/rollback`, etc.
  * Create `scripts/orchestrate_staging.py` to:

    * Run dedup → migration → triage → recent activity snapshot in one pipeline.
  * **Pause** before applying automatic Triage classification to discuss file tree (manual gate).

* **System Audit & Deep Dive**

  * Confirm:

    * `UniversalAdaptiveLearning` is logging events (you saw ~1000 events).
    * “0 rules” for new runs is normal.
    * Background monitor is the base; Adaptive extends Enhanced.
  * Audit display logic so DB stats are **explained**, not confusing.

---

## L. Mini “Start-Now” Strip (If You Have 60–90 Minutes)

If you need something brutally concrete for *right now*, do this:

1. **Fix `Request` import + backend startup.**
2. **Kill port 8000 zombie; restart backend.**
3. **Wire / fix monitor status endpoint in `main.py` + `api/`.**
4. **Align `MonitorStatusWidget.tsx` with backend type.**
5. **Confirm you can see live monitor status in the UI.**

That’s one tight block that moves you from “stuck in notes” → “system actually breathing.”

We are there
Coming next:
* `SPRINT_PLAN.md` (high-level)
* `TODO_ENGINEERING.md` (dev-focused checklist only, no narrative)

so you can just check items off as you go.

[🕒 2025-12-02 02:35]

