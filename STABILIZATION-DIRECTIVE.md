# STABILIZATION DIRECTIVE — Ship the AI File Organizer

**Issued by:** Claude (Architectural Oversight)
**For:** Gemini 3.1 (Builder)
**Date:** 2026-02-21
**Status:** APPROVED — Execute in sequence. Do not skip gates.

---

## Context

The AI File Organizer has been through 3+ sprints of feature development, a distro extraction (M1.5→M2), and multiple agent handoffs. The `master` branch has a clean distro with README, MIT license, plugin scaffold, and config template. The `studio` branch (where we are now) has the full-featured Ryan-specific build.

**The goal of this directive is simple:** Make the `studio` branch work end-to-end. Server starts, files get classified, triage UI shows results, rollback works. No new features. No refactoring. Just make what exists actually function.

---

## Current State (Audit Results — 2026-02-21)

| Component | Status | Issue |
|-----------|--------|-------|
| `main.py` (1,449 lines) | Parses OK | FastAPI app, ~30+ endpoints |
| `unified_classifier.py` (1,119 lines) | Imports OK (with venv) | Uses deprecated `google.generativeai` — FutureWarning |
| `easy_rollback_system.py` (685 lines) | ✅ Imports OK | Drive rollback disabled (local only) |
| `confidence_system.py` (674 lines) | ✅ Imports OK | Export is `ADHDFriendlyConfidenceSystem`, not `ConfidenceSystem` |
| `api/services.py` (1,021 lines) | ✅ Imports OK | Triage service functional |
| `hierarchical_organizer.py` (516 lines) | ✅ Imports OK | — |
| `gdrive_integration.py` (479 lines) | ✅ Works | Root: `~/Library/CloudStorage/GoogleDrive-*/My Drive` |
| `taxonomy_service.py` | ✅ Imports OK | No `taxonomy.json` file found — will seed defaults |
| `adaptive_background_monitor.py` | ✅ Imports OK | — |
| `orchestrate_staging.py` | ❌ No `StagingOrchestrator` class | Class name mismatch or missing |
| Frontend (`frontend_v2/`) | Built (`dist/` exists) | 9 pages, 2,311 lines TSX |
| `config.yaml` | ❌ Missing on `studio` | Exists as `config.example.yaml` on `master` only |
| `plugins/` directory | ❌ Missing on `studio` | Exists on `master` only |
| `vision_analyzer.py` | FutureWarning | Uses `google.generativeai` (deprecated, switch to `google.genai`) |
| Hardcoded paths | 7 files | `veo_brain.py`, `proactive_hooks.py`, `video_project_trainer.py`, + 4 scripts |
| Git branch | `studio` | 1 commit ahead of `master` (`_1_1_1_1` suffix fix) |

### What Works
- Core module imports (with `venv` activated)
- FastAPI app structure and endpoint registration
- Google Drive path resolution
- Frontend build artifacts
- M1.5 blockers resolved (veo_api split done, veo_prompts_api.py + veo_brain_api.py exist)

### What's Broken or Missing
1. **No `taxonomy.json`** — TaxonomyService will seed defaults, but those defaults may not match the 46-folder Drive structure
2. **Deprecated Gemini API** — `google.generativeai` is end-of-life. Must migrate to `google.genai`
3. **`orchestrate_staging.py`** — Export name doesn't match what other modules expect
4. **`config.yaml` not on `studio`** — Backend has no unified config to read from
5. **Server hasn't been tested end-to-end** — No confirmation it starts and serves the UI

---

## Decisions Locked

| Decision | Resolution |
|----------|-----------|
| Target branch | `studio` (Ryan's personal build) |
| Scope | Fix what's broken. Zero new features. |
| Gemini API | Migrate `google.generativeai` → `google.genai` in all 4 files |
| Config | Cherry-pick `config.example.yaml` from `master`, adapt for `studio` |
| Taxonomy | Generate `taxonomy.json` from the actual Google Drive folder structure |
| Testing method | Server start + manual file drop + triage UI verification |
| Rollback safety | `easy_rollback_system.py` must pass import + basic function test at every gate |
| Vision backend | Gemini API (primary), Qwen via Ollama (fallback) — no changes to this logic |
| venv | Use existing `venv/` (not `.venv/`). Python in `venv/bin/python3` |

---

## Phase 1: Foundation (Execute First — All Blocking)

### Task 1.1: Fix the Gemini API Deprecation

**The problem:** `google.generativeai` is deprecated and will stop working. Four files use it.

**Files to update:**
- `vision_analyzer.py` (primary — this is the vision brain)
- `vision_content_extractor.py`
- `vision_cli.py`
- `semantic_text_analyzer.py`

**What to do:**
1. Replace `import google.generativeai as genai` with the equivalent `google.genai` import
2. Update model initialization (`genai.GenerativeModel` → new API equivalent)
3. Update `genai.configure(api_key=...)` to new auth pattern
4. Update `genai.upload_file` calls in video analysis
5. Preserve all existing logic — only change the API surface

**Migration reference:** https://github.com/google-gemini/deprecated-generative-ai-python/blob/main/README.md

**Success criteria:**
```bash
grep -rn "google.generativeai" --include="*.py" | grep -v __pycache__ | grep -v venv
# Returns zero results
```
Server starts without FutureWarning.

### Task 1.2: Create `config.yaml` on Studio Branch

**What to do:**
1. Cherry-pick or copy `config.example.yaml` from `master` branch
2. Create `config.yaml` (gitignored) with Ryan's actual values:

```yaml
storage:
  root: ~/Library/CloudStorage/GoogleDrive-thebearwithabite@gmail.com/My Drive
  metadata: ~/.ai-file-organizer
  staging: ~/.ai-file-organizer/staging

monitor:
  paths:
    - ~/Downloads
    - ~/Desktop
  interval_seconds: 5

gdrive:
  enabled: true

confidence:
  mode: SMART

server:
  host: 0.0.0.0
  port: 8000

plugins:
  enabled: []
```

3. Verify `path_config.py` reads from this config (or add a thin loader if it doesn't)

**Success criteria:** `python3 -c "from path_config import PathConfig; pc = PathConfig(); print(pc.base_paths)"` returns real paths.

### Task 1.3: Generate Taxonomy from Drive Structure

**What to do:**
1. Scan the actual Google Drive folder structure at `get_ai_organizer_root()`
2. Generate `taxonomy.json` with the real categories (the 46-folder structure)
3. Place it where `TaxonomyService` expects it (check `self.taxonomy_path` in `taxonomy_service.py`)

**The taxonomy must reflect reality, not defaults.** The classification engine needs to know about the actual destination folders.

**Success criteria:**
```python
from taxonomy_service import TaxonomyService
ts = TaxonomyService.get_instance(Path("."))
print(len(ts.categories))  # Should be ~46, not 0 or some default count
```

### Task 1.4: Fix `orchestrate_staging.py` Export

**What to do:**
1. Check what class/function `orchestrate_staging.py` actually exports: `grep "^class \|^def " orchestrate_staging.py`
2. Check what other modules expect to import: `grep -rn "orchestrate_staging" --include="*.py"`
3. Fix the mismatch — either rename the class or update the imports

**Success criteria:** `from orchestrate_staging import <whatever_the_class_is>` works.

---

## Gate 1: Foundation Check

**STOP HERE.** Before proceeding, verify ALL of the following:

```bash
cd ~/Github/ai-file-organizer && source venv/bin/activate

# 1. Server starts
python main.py &
sleep 5
curl -s http://localhost:8000/health | python3 -m json.tool
# Must return valid JSON with status

# 2. Core imports clean
python3 -c "from unified_classifier import UnifiedClassificationService; print('OK')"
python3 -c "from confidence_system import ADHDFriendlyConfidenceSystem; print('OK')"
python3 -c "from taxonomy_service import TaxonomyService; from pathlib import Path; ts = TaxonomyService.get_instance(Path('.')); print(f'{len(ts.categories)} categories')"

# 3. No deprecation warnings
python3 -c "from vision_analyzer import VisionAnalyzer" 2>&1 | grep -i "deprecat"
# Must return nothing

# 4. Rollback safety
python3 -c "from easy_rollback_system import EasyRollbackSystem; print('Rollback OK')"

# Kill the server
kill %1
```

**All 4 must pass. Do not proceed to Phase 2 until they do.**

---

## Phase 2: End-to-End Flow

### Task 2.1: Server Start → UI Loads

**What to do:**
1. Start the server: `python main.py`
2. Verify `http://localhost:8000` serves the React UI
3. Verify the System State strip shows real data (not "Monitor disabled" / "No database statistics")
4. If the frontend `dist/` is stale, rebuild: `cd frontend_v2 && npm run build`

**Fix anything that prevents the UI from loading.** This is the user's primary interface.

### Task 2.2: File Classification Pipeline

**What to do:**
1. Drop a test file into `~/Downloads` (e.g., a PDF, an image, a text doc)
2. Trigger a scan: `curl -X POST http://localhost:8000/api/triage/trigger_scan`
3. Verify the file appears in the Triage UI (`http://localhost:8000` → Triage page)
4. Verify the classification result includes:
   - A real category from `taxonomy.json` (not "unknown" or "uncategorized")
   - A confidence score > 0
   - Reasoning text

**If classification returns "unknown":** Trace through `unified_classifier.py` → `classify_file()` → check if it reaches the Gemini API or falls back. The `GEMINI_API_KEY` must be set in `.env.local` or environment.

### Task 2.3: Triage → Approve → File Moves

**What to do:**
1. In the Triage UI, approve a classified file
2. Verify the file moves to the correct destination folder in Google Drive
3. Verify a rollback entry is created: `python3 easy_rollback_system.py --list`
4. Verify the rollback entry shows the correct source and destination

**This is the money shot.** If this works, the core system is functional.

### Task 2.4: Rollback Verification

**What to do:**
1. Use the rollback system to undo the move from Task 2.3
2. Verify the file returns to its original location
3. Verify the rollback entry is marked as undone

**Success criteria:** File goes back. No data loss. No orphaned records.

---

## Gate 2: End-to-End Check

**STOP HERE.** The system must demonstrate this complete loop:

```
New file in ~/Downloads
  → Scan detects it
  → Classifier analyzes it (via Gemini or fallback)
  → Triage UI shows result with category + confidence
  → User approves
  → File moves to correct Drive folder
  → Rollback entry logged
  → Rollback undoes the move successfully
```

**If this loop works, Phase 2 is complete.**

---

## Phase 3: Polish (Only After Phase 2 Passes)

### Task 3.1: Background Monitor

Verify the adaptive background monitor starts automatically and watches `~/Downloads` and `~/Desktop`. It should detect new files without requiring a manual scan trigger.

### Task 3.2: Learning System

Verify `UniversalAdaptiveLearning` records events when files are classified and moved. Check that the 10,000 existing `ai_observation` events are accessible.

### Task 3.3: Deduplication

Verify `automated_deduplication_service.py` can scan and identify duplicates without false positives. Dry-run mode only — no auto-deletion.

---

## Constraints

1. **No refactoring.** Fix bugs, don't redesign modules.
2. **No new features.** The scope is: make existing features work.
3. **No touching `easy_rollback_system.py` internals.** It's the safety net. Verify it works, don't modify it.
4. **Small commits.** One logical change per commit. Server must start after every commit.
5. **Use `venv/`, not `.venv/`.** The working virtual environment is `venv/`.
6. **Preserve `.env.local`.** It contains API keys and sensitive config. Never commit it.
7. **Do not delete any files.** If something should be excluded, add to `.gitignore` or move to `Archive/`.
8. **When in doubt, stop and report.** Don't invent solutions to ambiguous problems. Flag them in a comment at the top of the file or in a `TODO:` annotation and move on.

---

## Verification Summary

| Gate | Pass Criteria |
|------|--------------|
| Gate 1 | Server starts, imports clean, no deprecation warnings, rollback imports OK |
| Gate 2 | Full loop: scan → classify → triage → approve → move → rollback works |
| Gate 3 | Monitor auto-starts, learning records events, dedup dry-run clean |

---

## Files the Builder Must Not Modify

These are stable and working. Hands off unless a bug is discovered that blocks a gate:

- `easy_rollback_system.py`
- `security_utils.py`
- `gdrive_integration.py`
- `path_config.py`
- `pid_lock.py`
- `api/rollback_service.py`

---

## Files the Builder Will Likely Need to Touch

| File | Reason |
|------|--------|
| `vision_analyzer.py` | Gemini API migration |
| `vision_content_extractor.py` | Gemini API migration |
| `vision_cli.py` | Gemini API migration |
| `semantic_text_analyzer.py` | Gemini API migration |
| `main.py` | Config loading, startup sequence fixes |
| `taxonomy_service.py` | Taxonomy generation from Drive |
| `orchestrate_staging.py` | Export name fix |
| `unified_classifier.py` | Only if classification pipeline is broken |
| `api/services.py` | Only if triage endpoints return bad data |
| `frontend_v2/src/pages/Triage.tsx` | Only if UI doesn't render classified files |
| `config.yaml` (new) | Create from template |

---

---

## Appendix A: Gemini API Migration Complexity Warning

Task 1.1 is the hardest task in this directive. `vision_analyzer.py` is NOT a simple import swap. The video analysis section (approximately lines 873-936) has deeply intertwined logic:

- `genai.upload_file()` for video upload
- `genai.get_file()` for status polling
- Model switching between Vertex AI (`vertexai.GenerativeModel`) and consumer `genai.GenerativeModel`
- Fallback logic that creates a separate `genai.GenerativeModel('gemini-1.5-flash')` when Vertex is active but video needs consumer API upload

**Do not attempt a global find-and-replace.** Read the `google.genai` migration guide first. Map each call site. Test video analysis separately from image analysis. If the migration is too complex for a single pass, migrate image analysis first (the happy path) and wrap video analysis in a try/except with a `TODO: complete genai migration` comment. Shipping with working image classification and broken video classification is acceptable. Shipping with nothing working is not.

---

## Appendix B: Post-Stabilization Architecture — Dash/Agno Retrieval Loop

**DO NOT IMPLEMENT THIS NOW.** This is a breadcrumb for future work.

After the system is stable and the full classification loop works end-to-end, the next major enhancement is a retrieval-augmented classification step inspired by the [Dash framework](https://github.com/agno-agi/dash). The core idea:

**Current flow:** File → Classify → Move → (maybe) Record learning event
**Target flow:** File → Retrieve past learnings → Classify with context → Move → Record learning event

The key architectural changes (future sprint):
1. Split `adaptive_learning.db` into two tiers: `confirmed_patterns` (user-approved) and `discovered_gotchas` (AI-discovered errors)
2. Before calling the Gemini API, query both tiers for similar files
3. Include retrieved patterns in the classification prompt as context
4. When users correct classifications in Triage, save the correction to `confirmed_patterns`

The existing `UniversalAdaptiveLearning` system already records 10,000+ `ai_observation` events. The missing piece is **retrieval at decision time** — using those events to inform new classifications rather than just logging them.

The plugin scaffold on `master` branch is the correct extension point for this. A retrieval-augmented classifier could be implemented as a plugin without modifying core classification logic.

**Do not modify any learning system code during stabilization. Just make sure it still records events.**

---

*This directive supersedes all previous sprint plans. The single goal is: make it work.*