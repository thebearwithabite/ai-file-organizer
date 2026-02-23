# TRIAGE UX DIRECTIVE — Make Triage Center Actually Usable

**Issued by:** Claude (Architectural Oversight)
**For:** Ryan → Gemini 3.1
**Date:** 2026-02-21
**Status:** APPROVED
**Branch:** `studio`
**Prerequisite:** Stabilization Directive Gate 1 PASSED

## Context

The Triage Center backend works. Files scan, classify, and move. Rollback logs entries. Gate 2 passed mechanically. But the UI creates more cognitive load than manual file management. For an ADHD-optimized system, that's a failure.

Four specific UX problems must be fixed before this is a usable daily tool.

## Problem 1: Hardcoded Category Dropdown (CRITICAL)

**Current state:** `Triage.tsx` renders a `<select>` with 7 hardcoded categories: `entertainment`, `financial`, `creative`, `development`, `audio`, `image`, `text_document`.

**The API works.** `/api/taxonomy/` (trailing slash required) returns 17 real categories with rich metadata:
```json
{
  "audio_vox": { "display_name": "VOX", "folder_name": "VOX", "parent_path": "Projects", ... },
  "audio_sfx": { "display_name": "SFX", ... },
  "creative_video": { "display_name": "Video", ... },
  ...
}
```

**Fix:**
1. On page load (or on scan complete), fetch `/api/taxonomy/`
2. Replace the hardcoded `<select>` options with categories from the API response
3. Use `display_name` as the visible label, category `id` as the value
4. Pre-select the AI's suggested category
5. Group by `parent_path` if possible (e.g., "Projects > VOX", "Projects > SFX")

**Success criteria:** The dropdown shows all 17 categories from the taxonomy API. No hardcoded category strings remain in `Triage.tsx`.

**Verification:**
```bash
grep -n "entertainment\|financial\|creative\|development\|audio\|image\|text_document" frontend_v2/src/pages/Triage.tsx
# Should return zero hardcoded category matches (only dynamic references)
```

## Problem 2: No File Preview (CRITICAL)

**Current state:** Each triage card shows the filename and AI confidence. You cannot see the actual file content. For images and screenshots, this makes classification impossible without opening Finder separately.

**Fix:**
1. Add a preview section to each triage card
2. For images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.heic`): Show an inline thumbnail (max 300px wide). The backend already serves files — use the existing file serving endpoint or add one at `/api/triage/preview/{file_id}`.
3. For PDFs: Show a clickable "Open File" button that opens the file in a new tab or triggers the system file opener
4. For all other files: Show a clickable filename that opens the file via the existing `/api/open-file` endpoint
5. The preview should be collapsible (default open for images, default closed for documents) to keep the page scannable

**Backend support needed:** Check if an endpoint exists to serve file content/thumbnails. If not, add:
```
GET /api/triage/preview/{file_id}
```
That returns the file content with the correct MIME type. For images, optionally resize to thumbnail dimensions server-side to keep page load fast.

**Success criteria:** Images show inline thumbnails in triage cards. All files have a clickable way to view them without leaving the page.

## Problem 3: No Destination Preview (IMPORTANT)

**Current state:** When you click "Confirm & Organize", the file just disappears. You have no idea where it went. There's no suggested rename shown.

**Fix:**
1. Below the category dropdown, show a **destination preview** line:
   ```
   📁 → Google Drive / Projects / Video / creative_video_contraband_drop.pdf
   ```
2. This should update dynamically when the user changes the category dropdown
3. The path is constructed from: `taxonomy[selectedCategory].parent_path` + `taxonomy[selectedCategory].folder_name` + filename
4. If the classifier returned a `suggested_filename`, show it:
   ```
   📝 Suggested rename: creative_video_contraband_drop.pdf
   ✏️  [Edit] or [Keep Original]
   ```
5. If the user filled in Project/Episode, show the hierarchical path:
   ```
   📁 → Google Drive / Projects / The_Papers_That_Dream / Episode_03 / Video / creative_video_contraband_drop.pdf
   ```

**Success criteria:** Before confirming, the user can see exactly where the file will go and what it will be named.

## Problem 4: Project/Episode Fields Are Useless Free-Text (IMPORTANT)

**Current state:** "Project Name" and "Episode/Version" are free-text inputs with placeholder examples. Every file requires manual typing.

**Fix:**
1. Replace "Project Name" free-text with a searchable dropdown/combobox
2. Populate from existing folder names in the Drive root (scan `/api/taxonomy/` parent paths or add endpoint to list existing project folders)
3. Allow typing a new project name that doesn't exist yet (combobox, not strict dropdown)
4. When a project is selected, populate "Episode/Version" dropdown with existing subfolders from that project
5. If the classifier detected a project (e.g., from filename "PTD" → "Papers That Dream"), pre-select it

**Minimum viable version:** Even just a datalist (HTML `<datalist>`) populated from the API would be a massive improvement over bare free-text.

**Success criteria:** User can select from existing projects without typing. New project names are still allowed.

## Execution Order

| Priority | Task | Reason |
|----------|------|--------|
| 1 | Fix category dropdown (Problem 1) | Blocks correct classification |
| 2 | Add file preview (Problem 2) | Blocks informed classification decisions |
| 3 | Add destination preview (Problem 3) | Prevents "where did my file go" confusion |
| 4 | Wire project/episode dropdowns (Problem 4) | Reduces cognitive load |

Tasks 1 and 2 are **required**. Tasks 3 and 4 are **strongly recommended** but can be follow-up if time is short.

## Files to Modify

| File | Changes |
|------|---------|
| `frontend_v2/src/pages/Triage.tsx` | All 4 problems — main work happens here |
| `api/services.py` | May need preview endpoint, project listing endpoint |
| `api/taxonomy_router.py` | May need endpoint to list project folders from Drive |

## Files NOT to Modify

- `unified_classifier.py` — classification logic is working
- `easy_rollback_system.py` — safety net, hands off
- `main.py` — server startup is stable, don't touch
- `taxonomy_service.py` — taxonomy loading works
- `config.yaml` — leave as-is

## Constraints

1. **No backend refactoring** — Add endpoints if needed, don't restructure existing ones
2. **No new npm dependencies** unless absolutely necessary (prefer native HTML elements)
3. **After every change, verify:** `cd frontend_v2 && npm run build` succeeds and the server still serves the UI
4. **The trailing slash matters:** The taxonomy API is at `/api/taxonomy/` not `/api/taxonomy`
5. **Keep the existing Confirm & Organize flow** — just enhance what the user sees before clicking it
6. **Test with actual files** — don't mock data, use the live server with real files in staging

## Verification Gate

After all changes:

1. Start server: `cd ~/Github/ai-file-organizer && source venv/bin/activate && python main.py`
2. Open `http://localhost:8000/triage`
3. Click "Scan Downloads"
4. Verify: Category dropdown shows 17+ categories from API (not 7 hardcoded)
5. Verify: Image files show inline thumbnail previews
6. Verify: All files have clickable preview/open option
7. Verify: Destination path shown before confirming
8. Verify: Selecting a different category updates the destination preview
9. Verify: "Confirm & Organize" still works (file moves, rollback entry created)
10. Verify: `npm run build` completes without errors

---

*This directive is scoped to Triage Center UX only. No other pages, no new features, no backend restructuring.*
