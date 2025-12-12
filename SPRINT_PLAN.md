# Sprint Plan: System Consolidation & Orchestration

**Goal:** Move from "it runs" to "it learns and organizes reliably." We are shifting from unblocking startup to consolidating architecture and verifying the core loop.

## Phase 1: Architecture Consolidation (The "Librarian" Fix)
**Objective:** Eliminate redundant logic. We have too many "Librarians" (`vector`, `hybrid`, `gdrive`, `enhanced`). We need ONE canonical source of truth for file operations and learning.

*   **Consolidate Librarian Classes:**
    *   Identify `HybridLibrarian` (or `EnhancedLibrarian`) as the core.
    *   Deprecate/Merge `vector_librarian.py` and `gdrive_librarian.py` into the core or make them thin wrappers.
    *   Ensure `UniversalAdaptiveLearning` talks to *one* librarian interface.
*   **Standardize Metadata Paths:**
    *   Enforce `AI_METADATA_SYSTEM` across all new consolidated code.
    *   Kill any remaining hardcoded paths to `~/Documents` or `~/Library`.

## Phase 2: Visibility & Trust (The "UI" Fix)
**Objective:** The user needs to *see* what the system is doing. "Recent Activity" must be real.

*   **Fix Drive Status:**
    *   `api/services.py` must report real Google Drive sync status, not hardcoded "Local".
*   **Implement Recent Activity:**
    *   Backend: Expose event log (moves, renames, learning events) via API.
    *   Frontend: Build `RecentActivityWidget` to show this log.
*   **Fix Broken UI Surfaces:**
    *   Triage Center display issues.
    *   Settings page text/logic errors.

## Phase 3: The "Smart" Core (Orchestration)
**Objective:** Prove the loop works. Dedupe -> Migrate -> Triage -> Learn.

*   **Orchestration Script (`scripts/orchestrate_staging.py`):**
    *   Chain the subsystems: `bulletproof_deduplication` -> `migrate_icloud` -> `UnifiedClassificationService`.
    *   Add a "Manual Gate" before applying changes (dry run first).
*   **Verify Learning:**
    *   Confirm `UniversalAdaptiveLearning` records events during this flow.
    *   Verify "0 rules" startup behavior is handled gracefully in UI.

## Phase 4: Cleanup & Integrity
**Objective:** Leave the place cleaner than we found it.

*   **Rogue System Cleanup:**
    *   Recover files from `~/Documents` rogue folders.
    *   Nuke empty rogue directories.
*   **Migration Integrity:**
    *   Verify no 0-byte files left behind.
    *   Confirm all moved files exist in destination.

---
**Next Immediate Step:** Phase 1 - Librarian Consolidation.
