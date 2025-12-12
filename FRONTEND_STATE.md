# Frontend State — Control Center (v2)

## Current Reality

- Single frontend: `frontend_v2` (React).
- Built assets served by FastAPI:

  - `frontend_v2/dist/index.html` → `/`
  - `frontend_v2/dist/assets` → `/assets`

- Port 8000:
  - Serves the **React app** (Control Center v2).
  - No static Vanilla JS frontend exists anymore.

## Components of Interest

- `SystemStateStrip.tsx`
  - Canonical “System State” UI (backend, monitor, orchestration).
- `Dashboard.tsx`
  - Main landing view; consumes system state + other widgets.

## Legacy

- The old `frontend/` directory was removed in Phase 6 ("Consolidation").
- Any references to:
  - `frontend/index.html`
  - `frontend/app.js`
  - `frontend/style.css`
  
  are historical and should not be revived.
