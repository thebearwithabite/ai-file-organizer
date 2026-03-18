# DISTRO DIRECTIVE — Canonical Spec for M1.5 → M2

**Issued by:** Claude (Architectural Oversight)
**For:** Cosmo (Director) → Jeeves (Builder)
**Date:** 2026-02-12
**Status:** APPROVED — All decisions final. Execute in order.

---

## Decisions Locked

| Decision | Resolution |
|----------|-----------|
| License | MIT |
| Package name | `ai-file-organizer` (keep existing) |
| Distribution | GitHub-only (no PyPI for now) |
| Min Python | 3.10+ |
| Branch strategy | `main` becomes the clean distro. Ryan's personal/creative work moves to `studio` branch. Public-facing default = distributable. |
| Module count | ~27 (full dependency tree, not just main.py imports) |
| Plugin interface | Ship in M2, not M4. Must exist in repo at launch. |

---

## M1.5: Blockers — Execute These First

These are **blocking**. M2 cannot start until all three are resolved.

### BLOCKER 1: Split `api/veo_api.py`

**Problem:** `main.py` imports `api/veo_api.py`. At line 678, there's a module-level `from veo_brain import ...`. If `veo_brain.py` is removed for distro, the server crashes on startup.

**Fix:**
1. Create `api/veo_prompts_api.py` — contains prompt management endpoints (CORE). This includes the prompt CRUD, the `init_veo_prompts_table()` function, and the `GeminiVisionAdapter` integration.
2. Create `api/veo_brain_api.py` — contains brain generation endpoints (PLUGIN). This includes everything below the `# ===== VEO Brain Generation Endpoints =====` comment at line 676.
3. Update `main.py`:
   - Import `veo_prompts_router` from `api/veo_prompts_api.py`
   - Remove import of `clip_router` and `veo_studio_router`
   - VEO brain/studio routers become optional plugin imports behind try/except

**Success criteria:** Server starts cleanly with `veo_brain.py` deleted from the filesystem.

### BLOCKER 2: Abstract `emergency_space_protection.py` paths

**Problem:** Lines 116-119 have a hardcoded fallback list including `thebearwithabite` Google Drive path. This bypasses the centralized path resolution in `gdrive_integration.py`.

**Fix:**
1. Replace the hardcoded `possible_gdrive_paths` list with a call to `get_ai_organizer_root()` wrapped in try/except
2. Add a config key `gdrive_fallback_paths` to `config.yaml` for users who need custom paths
3. Default behavior with no config: detect standard Google Drive mount points (`~/Library/CloudStorage/GoogleDrive-*/My Drive` on macOS, equivalent on Linux/Windows)

**Success criteria:** `grep -r "thebearwithabite" *.py` returns zero results in core modules.

### BLOCKER 3: Verify full dependency tree

**Problem:** Cosmo's M1 found 12 direct imports. The real core is ~27 modules when you trace the full tree.

**Full dependency chain (Jeeves must know this exists):**
```
main.py
├── api/services.py
│   ├── taxonomy_service.py
│   ├── google_drive_auth.py
│   ├── unified_librarian.py
│   │   ├── librarian_policy.py
│   │   ├── gdrive_librarian.py
│   │   └── unified_classifier.py
│   │       ├── content_extractor.py
│   │       ├── audio_analyzer.py
│   │       ├── vision_analyzer.py
│   │       ├── semantic_text_analyzer.py
│   │       └── taxonomy_service.py
│   ├── hierarchical_organizer.py
│   └── universal_adaptive_learning.py
├── api/rollback_service.py
├── api/veo_prompts_api.py (after split)
│   └── gemini_vision_adapter.py
├── api/taxonomy_router.py
├── api/identity_router.py
├── gdrive_integration.py
├── security_utils.py
├── universal_adaptive_learning.py
├── easy_rollback_system.py
├── adaptive_background_monitor.py
├── confidence_system.py
├── automated_deduplication_service.py
│   └── bulletproof_deduplication.py
├── emergency_space_protection.py
├── orchestrate_staging.py
└── pid_lock.py
```

**Action:** Jeeves confirms this tree is accurate by running an import trace. Any module not on this list that gets pulled in = flag it immediately.

**Also verify:** `local_metadata_store.py` — it imports `get_metadata_root` but may be dead code. If any core module imports it, add it to the tree. If nothing imports it, exclude it.

---

## M2: Core Extraction — Execution Plan

### Step 1: Branch Setup
1. Create `studio` branch from current `main` (preserves Ryan's full codebase)
2. On `main`, begin extraction work
3. All commits on `main` from this point forward serve the distro goal

### Step 2: Config Schema (DO THIS BEFORE CODING)

Create `config.yaml` with this structure. This is the architectural keystone — every hardcoded assumption routes through here.

```yaml
# AI File Organizer Configuration
# Copy this file to config.yaml and customize

# Where your organized files live
storage:
  # Primary storage root (local path or Google Drive mount)
  root: ~/Documents/AI-Organized
  # Metadata/database storage (must be local, never cloud-synced)
  metadata: ~/.ai-file-organizer
  # Staging area for new files (7-day observation)
  staging: ~/.ai-file-organizer/staging

# Folders to watch for new files
monitor:
  paths:
    - ~/Downloads
    - ~/Desktop
  interval_seconds: 5

# Google Drive integration (optional)
gdrive:
  enabled: false
  # mount_path: auto-detected if not set
  # fallback_paths: []

# Classification confidence
confidence:
  # NEVER = always ask, MINIMAL = quick decisions,
  # SMART = confirm uncertain, ALWAYS = full auto
  mode: SMART

# Server
server:
  host: 0.0.0.0
  port: 8000

# Plugins (optional extensions)
plugins:
  # List of plugin module paths to load
  enabled: []
```

**Rule:** No module may read a path, threshold, or feature flag from anywhere other than this config (or environment variables that override it). `gdrive_integration.py`'s `.env.local` loading is acceptable as a secondary override mechanism.

### Step 3: Plugin Interface Scaffold

Create this structure in the repo:

```
plugins/
  README.md          # "How to build a plugin"
  example_classifier/
    __init__.py      # registers with taxonomy_service via entry point
    classifier.py    # implements classify(file_path) -> ClassificationResult
```

The plugin contract is simple:
- A plugin is a Python package in `plugins/`
- It must expose a `register(app, config)` function
- For classifiers: implement `classify(file_path: Path) -> dict` with keys `category`, `confidence`, `reasoning`
- Plugins are loaded at startup if listed in `config.yaml` under `plugins.enabled`

This doesn't need to be sophisticated. It needs to exist so forkers see the extension point.

### Step 4: Extract and Clean
1. Remove all files in the OUT list from `main` branch
2. Run the three blocker fixes
3. Replace all remaining hardcoded paths with config lookups
4. Verify server starts on a clean checkout with only `config.yaml` configured
5. Run existing tests, fix what breaks

### Step 5: Ship Test
**The definition of done for M2:** Clone the repo fresh on a machine with zero Ryan-specific config. Run `pip install -r requirements.txt`, copy `config.example.yaml` to `config.yaml`, run `python main.py`. Server starts. Triage UI loads. Drop a file in `~/Downloads`. It gets classified.

---

## Constraints for Jeeves

1. **No refactoring beyond what's required for extraction.** If a module works, don't rewrite it. Clean the interfaces, don't redesign them.
2. **Small sequential tasks.** One module or one concern per work session. Do not attempt to refactor the entire codebase in a single pass.
3. **Test after every change.** Server must start after every commit. If it doesn't, fix before moving on.
4. **When in doubt, ask Cosmo.** Don't invent solutions to ambiguous problems. Flag them.
5. **Preserve the rollback system.** `easy_rollback_system.py` is the safety net. It must work at every stage of extraction. Non-negotiable.

---

## Verification Checkpoints

Cosmo reviews at each of these gates:

| Gate | Criteria |
|------|----------|
| After M1.5 | Server starts without veo_brain.py. Zero hardcoded personal paths in core. |
| After M2 Step 2 | config.yaml schema reviewed and approved before any code changes. |
| After M2 Step 4 | `grep -r "ryanthomson\|thebearwithabite\|papersthatdream" *.py api/*.py` returns zero results. |
| After M2 Step 5 | Fresh-machine ship test passes. |

---

*This document is the single source of truth for the distro extraction. If it conflicts with PROJECT-PLAN.md, this document wins.*
