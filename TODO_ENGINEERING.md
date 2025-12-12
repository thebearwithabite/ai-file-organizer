# TODO_ENGINEERING (DEPRECATED)

> State: DEPRECATED — 2025-12-05

This file describes tasks for a previous architecture where:
- `frontend/` (Vanilla JS) existed and was served on port 8000
- `frontend_v2` (React) was considered "Legacy"

As of Phase 6 (Consolidation):

- `frontend/` has been removed.
- `frontend_v2` (React) is the *only* frontend.
- React is served on **port 8000** and is the canonical **Control Center (v2)**.

Do **not** implement this file's instructions. It is kept only as historical context.

---

# Original Content Below (DO NOT EXECUTE)

# TODO — Control Center (v2) & System State

This file is ONLY for the **Control Center (v2)** (static HTML on port 8000) and the **System State strip**. Everything else goes in Roadmap or other TODOs.

---

## 0. Canonical Frontend Declaration

- [ ] Confirm static HTML frontend (port 8000) is treated as **Control Center (v2)**.
- [ ] Confirm React frontend (port 5173) is labeled as **Legacy (v1)** in code and/or UI.
- [ ] Update any README or comments that still suggest the React app is primary.

---

## 1. System State Strip — Frontend

### 1.1 HTML & Structure

- [ ] In `frontend/index.html`, rename the app title/header to:  
      `AI File Organizer — Control Center (v2)`
- [ ] Add a `#system-state-strip` container near the top of the body, before the main nav.
- [ ] Inside `#system-state-strip`, add placeholders for:
  - [ ] Backend status (text + status dot)
  - [ ] Monitor status (`Watching X folders · Y rules` / error)
  - [ ] Last orchestration (`Last run: <timestamp> · <N> files` / “No runs yet”)

### 1.2 CSS

- [ ] In `frontend/style.css`, add styles for `#system-state-strip`:
  - [ ] Layout: flex row, aligned center, gap between items.
  - [ ] Background: subtle, distinct from page (e.g. slightly darker or bordered).
  - [ ] Status dots:
    - [ ] `.status-dot.ok`
    - [ ] `.status-dot.error`
    - [ ] `.status-dot.unknown` (fallback)
- [ ] Ensure strip looks good on small widths (no overflow, wraps gracefully).

### 1.3 JS Logic

- [ ] In `frontend/app.js` (or equivalent):
  - [ ] Implement `updateSystemState()` that:
    - [ ] Calls `/api/system/status`
    - [ ] Parses backend response into:
      - `backendStatus`
      - `diskSpaceStatus` (if present)
      - `monitorStatus` (watching folders, rules)
      - `lastOrchestration` (timestamp + files)
    - [ ] Updates DOM elements in `#system-state-strip`.
  - [ ] Add a `setInterval(updateSystemState, 30000)` (30s) poll.
  - [ ] Call `updateSystemState()` once on page load.

- [ ] Implement error handling:
  - [ ] If fetch fails:
    - [ ] Set Backend: `Offline`
    - [ ] Monitor: `Unavailable`
    - [ ] Last Orchestration: `-`
    - [ ] Add CSS class for “error state” to the strip.

---

## 2. System Status Endpoint — Backend

### 2.1 API Shape

- [ ] In `api/services.py` (or wherever SystemService lives), ensure `get_status()` returns a dict with keys:

  - [ ] `backend_status` (e.g. `"online"` / `"degraded"` / `"offline"`)
  - [ ] `disk_space`:
        ```json
        {
          "ok": true,
          "critical_paths": [],
          "last_check": "ISO-8601"
        }
        ```
  - [ ] `monitor`:
        ```json
        {
          "running": true,
          "watching_folders": ["..."],
          "rules_loaded": 0,
          "stats": {
            "processed_files": 0,
            "error_files": 0,
            "scans_24h": 0,
            "files_processed_24h": 0,
            "errors_24h": 0,
            "last_scan": "ISO-8601 or null"
          }
        }
        ```
  - [ ] `last_orchestration`:
        ```json
        {
          "timestamp": "ISO-8601 or null",
          "files_touched": 0
        }
        ```

- [ ] Make sure `get_status()` does **not** crash if:
  - [ ] Monitor isn’t initialized yet.
  - [ ] Orchestration has never run.
  - [ ] Disk space checker returns partial data.

### 2.2 Missing Import / Exceptions

- [ ] Confirm `datetime` is imported wherever it’s used for timestamps.
- [ ] Wrap internal calls in `try/except`:
  - [ ] If any sub-component fails (monitor, space protection, etc.), still return a valid JSON with:
    - [ ] `backend_status: "degraded"`
    - [ ] `error` field set with a short description (for logs / debugging).

---

## 3. Monitor Status Endpoint (If Separate)

If `monitor-status` is its own endpoint:

- [ ] Implement `/api/system/monitor-status` route (FastAPI) that:
  - [ ] Returns monitor stats only (subset of `get_status()`).
  - [ ] Never raises unhandled exceptions — always returns a safe JSON payload.

- [ ] Update frontend (if it uses this endpoint directly) to:
  - [ ] Handle both success and failure states gracefully.
  - [ ] Fall back to “Monitor: Unavailable” if call fails.

---

## 4. UX Copy & Error States

### 4.1 System Strip Messages

- [ ] Standardize messages to:

  - [ ] Disk space:
    - Success: e.g. `Disk: OK`
    - Error: `Failed to load disk space status.`
  - [ ] Monitor:
    - Success: `Watching X folders · Y rules`
    - Error: `Failed to load monitor status.`
  - [ ] Backend:
    - Success: `Backend: Online`
    - Offline: `Backend: Offline`
    - Degraded: `Backend: Degraded`

- [ ] Ensure messages are **only** shown when relevant:
  - [ ] No phantom “Failed to load…” if the request hasn’t even fired yet.

### 4.2 Dashboard “Loading…” Text

- [ ] Locate the “Loading system status…” text in the Dashboard.
- [ ] Replace with behavior:
  - [ ] While `updateSystemState()` first run in progress → show “Loading system status…”
  - [ ] On success → hide this text entirely (state lives in the strip).
  - [ ] On error → replace with:
        `System status unavailable. Backend may be offline.`

---

## 5. Testing & Verification

### 5.1 Manual API Tests

- [ ] Run backend (`python main.py` or equivalent).
- [ ] Hit `/api/system/status` directly in browser or curl:
  - [ ] Verify shape matches frontend expectations.
  - [ ] Verify `Content-Type` is `application/json`.

- [ ] If present, hit `/api/system/monitor-status`:
  - [ ] Verify payload and error handling.

### 5.2 Frontend Behavior

- [ ] With backend running:
  - [ ] Open `http://localhost:8000`.
  - [ ] Confirm:
    - [ ] System State strip renders with green/OK backend indicator.
    - [ ] Monitor shows correct X folders / Y rules (or a valid “no rules yet” message).
    - [ ] Last orchestration field shows either:
      - [ ] A real timestamp + file count, or
      - [ ] “No runs yet.”

- [ ] Stop backend:
  - [ ] Refresh `http://localhost:8000`.
  - [ ] Confirm:
    - [ ] Backend shows “Offline”.
    - [ ] Disk + monitor messages show failure variants.
    - [ ] No infinite “Loading system status…” text.

- [ ] (Optional) Trigger orchestration:
  - [ ] Confirm `last_orchestration` updates in the strip within 30s.
  - [ ] Confirm correct number of files touched is displayed.

---

## 6. Cleanup / Guardrails

- [ ] Add a short comment at the top of `app.js`:

  ```js
  // NOTE: Control Center (v2) is the primary UI.
  // The System State strip is the single source of truth
  // for backend/monitor/orchestration status.
  // Keep this file small and focused; other UI experiments
  // belong in the Legacy (v1) React app or separate views.
