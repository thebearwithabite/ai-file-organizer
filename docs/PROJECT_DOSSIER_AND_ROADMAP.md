# AI File Organizer — Project Dossier & Roadmap

**Codename:** Antigravity
**Repo:** `github.com/thebearwithabite/ai-file-organizer`
**Owner:** Ryan Thomson (@RT Max / @The Bear With A Bite)
**Dossier Date:** February 7, 2026
**Purpose:** Onboard a new project overseer (OpenClaw) with full institutional context, then define the stabilization-to-expansion roadmap.

---

## Part 1: What This Project Is

Antigravity is a distributed, AI-powered creative operating system that began as a smart file organizer and is evolving into a multi-modal creative pipeline. Ryan built it because he has ADHD and file organization is genuinely hard — the system creates an intelligent librarian that knows him and his work intimately, reduces cognitive load, and connects related documents and ideas.

It uses local LLMs (Qwen 2.5 via Ollama), cloud models (Gemini), vision analysis, and a living taxonomy to classify, route, and organize files across Ryan's creative workspace — then extends that intelligence into video generation (VEO), editing (DaVinci Resolve), and image synthesis (ComfyUI/Flux).

The system runs across two machines connected via Tailscale:

- **MacBook (Controller):** FastAPI backend, React frontend (Triage Center), orchestration logic, taxonomy service, Gemini Flash fallback
- **Windows RTX 5090 (Muscle):** Ollama/Qwen for classification and vision, Flux for keyframe generation, DaVinci Resolve for timeline assembly, heavy compute

State lives in Supabase (cloud PostgreSQL) as source of truth, with SQLite as a local execution cache and JSON sidecars for exports only. All metadata is confined to `~/Documents/AI_METADATA_SYSTEM` — never cloud-synced directories.

---

## Part 2: Architecture at a Glance

### Core Components

| Component | Role | Key Rule |
|-----------|------|----------|
| **UnifiedLibrarian** | Conductor — composes all specialized modules | Never reimplements logic; only orchestrates |
| **LibrarianPolicyEngine** | Pure decision brain — no IO, no side effects | Returns frozen `PolicyDecision` dataclass objects |
| **CloudLibrarian** | Dumb cloud adapter — upload/sync only | Cannot think; acts on explicit instructions |
| **UnifiedClassificationService** | Intelligence layer — routes files to categories | Confidence ≥ 0.90 for auto-organization |
| **VisionAnalyzer** | Remote vision processing via Qwen 2.5-VL | Runs on Windows via Tailscale tunnel |
| **HybridLibrarian** | Semantic search engine (ChromaDB) | Read-only; never mutates |
| **TaxonomyService** | Living category schema — single source of truth | Atomic writes, fingerprint collision detection, locked categories |
| **StagingMonitor** | Watches file staging area | DB in ~/Documents/AI_METADATA_SYSTEM only |
| **SafeFileRecycling** | Trash-don't-delete with recovery | Logged to EasyRollbackSystem |
| **VEO Brain** | Script analysis → shot lists → keyframe rendering | Session identity via Supabase `veo_session_id` |

### Authority Hierarchy

```
Supabase (Cloud PostgreSQL) — absolute Source of Truth
       ↓
taxonomy.json (Authoritative schema, local)
       ↓
Classification Logic (Consumer — reads taxonomy, applies rules)
       ↓
Filesystem Effects (Observable — never authoritative)
       ↓
JSON Sidecars (.veo.json, .meta.json) — Non-authoritative exports only
```

Changes flow downward. Filesystem observations can trigger taxonomy sync (e.g., manual folder renames), but Supabase and taxonomy always hold authority.

### Classification Pipeline

```
File → Qwen 2.5 (Ollama on RTX 5090)
         ↓ (fallback)
       Gemini Flash (API)
         ↓ (fallback)
       Default/UNSORTED → Review Queue
```

Known fragility: entire pipeline depends on remote Ollama. Circuit breaker needed.

### Intelligence Distribution

| Machine | Role | Models |
|---------|------|--------|
| **MacBook** | Coordination, API, UI, ChromaDB | Gemini Flash (fallback) |
| **Windows 5090** | Heavy compute, local inference | Qwen 2.5 (text), Qwen 2.5-VL (vision), Flux (keyframes), Whisper |

Connected via Tailscale + Supabase real-time events.

---

## Part 3: Git History & Contributors

### Repository: `github.com/thebearwithabite/ai-file-organizer`

**Active Contributors (last 80 commits):**

| Contributor | Role | Commit Pattern |
|-------------|------|----------------|
| **RT Max** (Ryan) | Owner, architect, integrator | Merges, refactors, critical fixes, conflict resolution |
| **The Bear With A Bite** (Ryan's GH) | Same, via GitHub UI | Direct edits, gitignore, config |
| **google-labs-jules[bot]** | Automated perf optimizer | `⚡ Bolt:` prefixed commits — DB connection reuse, scandir, lazy hashing, dedup optimization |
| **copilot-swe-agent[bot]** | Automated code agent | Unit tests, safety gate fixes, sub-PR work |
| **Copilot** | VEO integration | Phase 1 VEO Prompt Machine integration (PR #39) |

### Commit Timeline (Jan 22 – Feb 6, 2026)

**Jan 22:** Massive merge day — 20+ branch merges including safe-recycling, emergency dedup, adaptive monitor, VEO integration (PR #39), keyword extraction, emergency space protection. Major refactor and repo cleanup (`38c215f`).

**Jan 23–26:** Jules bot performance sprint — dedup path optimization, StagingMonitor SQLite reuse, file protection optimization, hashing optimization. Copilot adds safety gate tests.

**Jan 27:** Dedup regex optimization merged. Code splitting for Frontend v2.

**Jan 28–Feb 1:** Continued perf work — adaptive monitor scan loop, staging hash deferral, background scanner path checks, directory scanning optimization.

**Feb 2:** Frontend route-based code splitting merged.

**Feb 3:** Triage UI taxonomy integration + path consolidation (`b75bc5d`), Skip button in Triage UI (`8c367d5`). Lazy hashing and scanner optimization PRs merged.

**Feb 4:** RGBA-to-RGB fix for Gemini compatibility, migration of hybrid_librarian to UnifiedClassificationService, verification script for classification pipeline, detailed logging for remote Ollama analysis. **Most recent master commit.**

**Feb 6:** Jules bot: tagging system DB performance optimization (on branch, not yet merged).

### Branch State

- **master** at `c21e693` — merged local changes with upstream fixes
- **origin/master** at `ff5394c` — debug logging for Ollama
- **3 unmerged optimization branches** from Jules bot (tagging, batch content extraction, staging scandir)

---

## Part 4: What's Been Built (Completed Work)

Based on 41 agent sessions (1,274 logged artifacts), PM thread analysis, and git history:

**Architecture & Stabilization:**
- Unified 6+ scattered librarian scripts into single conductor (UnifiedLibrarian)
- Separated mechanism from policy (LibrarianPolicyEngine with frozen dataclasses)
- FastAPI lifespan manager replacing deprecated `on_event`
- True singletons for GoogleDriveAuth and TaxonomyService
- Metadata isolation — moved all DBs from Google Drive to `~/Documents/AI_METADATA_SYSTEM`
- Drift metrics monitoring via `drift_metrics.py`
- Major refactor and conflict resolution (Jan 22)

**Performance Sprint (Jan 22 – Feb 6, via Jules bot):**
- SQLite connection reuse across StagingMonitor, AdaptiveBackgroundMonitor, InteractiveBatchProcessor
- `os.scandir` replacing `os.listdir` in directory scanning
- Lazy/deferred hash calculation in StagingMonitor
- Regex pre-compilation in deduplication
- 64KB buffer optimization in file hashing
- `executemany` for adaptive learning sync
- Route-based code splitting in Frontend v2

**Frontend & Triage:**
- Triage Center with 4 preview components and glassmorphic UI
- Classification persistence wired to API
- 40+ taxonomy categories with UI integration
- Skip button in Triage UI
- Path truncation for GDrive paths

**VEO Integration (89% complete across 10 phases):**
- Phase 1 integrated via PR #39 (Copilot)
- Script ingestion → shot list generation → keyframe rendering pipeline
- Multi-shot generation (breaking scenes into ~4 shots)
- Session persistence in Supabase
- DaVinci Resolve bridge: project-per-session scaffolding active

**Agent Statistics (from Antigravity logs):**
- 41 agent sessions analyzed
- 82.5% average completion rate
- 48.8% of sessions completed 100% of assigned tasks
- 21.9% honestly blocked with documented reasons
- 7.3% abandoned (planning without execution)

---

## Part 5: Known Issues & Debt

### Critical (Blocking)

1. **Ollama server unreachable** — Remote server at 192.168.86.23 intermittently down. Classification cascades through failing fallbacks with no circuit breaker.
2. **Gemini fallback broken** — PIL RGBA→RGB format error. Fixed in `d7b7dc0` but needs verification in production.
3. **Control panel offline** — `NameError: name 'system_service' is not defined` in main.py. Redundant code blocks and conflicting initialization.
4. **DaVinci Resolve MCP transport mismatch** — Server configured with SSE, Cowork attempting POST (405 errors). Needs protocol alignment.

### Medium (Architectural Debt)

5. **Path management fragility** — Directive issued to consolidate to `~/Documents/AI_METADATA_SYSTEM`, partially executed (`b75bc5d`). Three competing resolution strategies still coexist in some modules.
6. **Frontend hardcoding** — Triage.tsx still has hardcoded categories in places; TaxonomyService API wiring incomplete.
7. **Agent drift pattern** — Multi-agent workflows can introduce concurrent drift. Agents sometimes create 8 initiatives masquerading as a single sprint.
8. **Adaptive learning not firing** — System records `ai_observation` events instead of `manual_move`, so rule generation doesn't trigger.
9. **3 unmerged Jules branches** — Tagging DB optimization, batch content extraction, staging scandir. Need review and merge.

### Low (Cosmetic / Non-blocking)

10. **Naming confusion** — HybridLibrarian vs UnifiedLibrarian naming overlap
11. **Legacy LaunchAgents** — Obsolete `com.modelrealignment.daemon.plist` daemons still registered
12. **Log/temp file sprawl** — Multiple `final_startup_*.log`, `server_startup.log` (3.2MB), `compile_log.txt` (720KB) in repo root

---

## Part 6: The Golden Rules

These are codified in `SYSTEM_MANUAL.md` and enforced through hard-won experience:

1. **Metadata Locality:** All databases (SQLite, ChromaDB) must live in `~/Documents/AI_METADATA_SYSTEM`. NEVER in Google Drive or any cloud-synced directory. Use `get_metadata_root()`.
2. **Supabase Is Truth:** Supabase state always overrides SQLite caches, JSON sidecars, and filesystem inference.
3. **Fail-Fast on Storage:** If a safe local database path cannot be established, the system must crash immediately. No silent fallback.
4. **Trash, Don't Delete:** All destructive operations go through `safe_file_recycling.py` with recovery logging.
5. **Always Log:** Every file move or rename must be logged to `EasyRollbackSystem`.
6. **Confidence Gating:** Only auto-organize at ≥ 0.90 confidence. Everything else → Review Queue for human review.
7. **No Legacy Paths:** Never allow live references to the old `04_METADATA_SYSTEM` path.
8. **No PII Leakage:** Metadata sent to Supabase or Gemini must be scrubbed of sensitive local usernames or project IDs.
9. **Resolve Is Write-Only:** VEO never mutates existing Resolve timelines unless explicitly instructed. Resolve state is NOT synced back.

---

## Part 7: Existing Documentation Index

The repo already has these docs. The overseer should read them in this order:

| Document | Location | Purpose |
|----------|----------|---------|
| **SYSTEM_MANUAL.md** | repo root | Canonical architecture, golden rules, workflows |
| **CLAUDE.md** | repo root | Code of conduct for AI agents + full architecture overview |
| **ROADMAP.md** | repo root | Detailed sprint plan (Sections 0–9) from Dec 2025, mostly complete |
| **README.md** | repo root | Project overview and setup instructions |
| **COMMANDS.md** | repo root | Available CLI commands and API endpoints |
| **GEMINI.md** | repo root | Gemini integration details |
| **agents.md** | repo root | Agent coordination documentation |
| **VEO_STUDIO_QUICK_REFERENCE.md** | repo root | VEO Studio operations guide |
| **VEO_STUDIO_UI_DOCUMENTATION.md** | repo root | VEO Studio UI component docs |
| **VERSION_2_FEATURES.md** | repo root | Frontend v2 feature list |
| **SPRINT_PLAN.md** | repo root | High-level sprint checklist |
| **FRONTEND_STATE.md** | repo root | Frontend state management docs |

---

## Part 8: The People and Roles

| Role | Entity | Responsibility |
|------|--------|---------------|
| **Vision & Direction** | Ryan Thomson | Strategic direction, business rules, final approval. Handles merges, architectural decisions, and conflict resolution. |
| **Project Overseer** | OpenClaw (Claude) | Architectural review, drift detection, institutional memory, scope enforcement. Reviews and critiques — does NOT write code directly. |
| **Builder (primary)** | Coding agent (to be assigned) | Executes approved designs, writes Python/React, subject to architectural review |
| **Perf Optimizer** | Jules (google-labs-jules[bot]) | Automated performance optimization PRs. Currently generating unmerged branches — needs oversight. |
| **Safety/Test Agent** | Copilot (copilot-swe-agent[bot]) | Unit tests, safety gates, sub-PRs |

**Oversight Protocol:**
1. **Sanity Check** (before code): Analyze proposed tasks for alignment with current phase goals
2. **Code Review** (after code): Check for drift, hallucinations, over-engineering, rule violations
3. **Integration & Safety** (before merge): Verify safety nets, hybrid connectivity, data integrity
4. **Jules Branch Review**: Review and merge/reject automated optimization branches regularly

---

## Part 9: Roadmap — Now / Next / Later

### NOW — Stabilize & Memorialize (Weeks 1–3)

Goal: Make ai-file-organizer a self-documenting, standalone GitHub project that a new contributor (human or AI) can onboard to without chat archaeology.

| # | Item | Description | Status | Owner |
|---|------|-------------|--------|-------|
| 1 | **Fix Ollama connectivity** | Restore classification pipeline to RTX 5090. Implement circuit breaker so failures are graceful, not cascading. | Blocked | Builder |
| 2 | **Verify Gemini fallback** | Confirm RGBA→RGB fix (`d7b7dc0`) works in production. End-to-end test of Qwen→Gemini→UNSORTED cascade. | Not Started | Builder |
| 3 | **Clean main.py** | Remove redundant code blocks, fix initialization race condition, resolve `system_service` NameError. | Not Started | Builder |
| 4 | **Wire Triage to TaxonomyService** | Replace remaining hardcoded categories in Triage.tsx with live API call. | Partial (`b75bc5d`) | Builder |
| 5 | **Fix adaptive learning trigger** | Change event type from `ai_observation` to `manual_move` so rule generation fires. | Not Started | Builder |
| 6 | **Review & merge Jules branches** | 3 unmerged optimization PRs. Review, test, merge or close. | Not Started | Overseer + Ryan |
| 7 | **Externalize architecture docs** | Write canonical `ARCHITECTURE.md` and `DECISIONS.md`. This dossier is the seed. Existing docs (SYSTEM_MANUAL, CLAUDE.md, ROADMAP.md) to be reconciled. | Not Started | Overseer + Ryan |
| 8 | **Audit and tag stable baseline** | Run full smoke test, tag a `v0.1-stable` release on GitHub. | Not Started | Overseer + Builder |
| 9 | **Complete path consolidation** | Finish migration to `~/Documents/AI_METADATA_SYSTEM`. Remove competing fallback patterns. Add `ensure_not_cloud_path()` guard to all modules. | Partial | Builder |
| 10 | **Repo hygiene** | Remove log files from repo root (server.log, compile_log.txt, startup_*.log). Clean up .gitignore. Archive dead code. | Not Started | Builder |
| 11 | **Clean up LaunchAgents** | Remove obsolete `com.modelrealignment.daemon.plist` entries. | Not Started | Ryan |

**Exit Criteria:** Backend starts cleanly, classification pipeline handles Ollama-down gracefully, Triage shows real taxonomy, all architecture is documented in-repo, GitHub release tagged, no stale branches.

---

### NEXT — VEO Prompt Machine + Resolve Integration (Weeks 4–8)

Goal: Activate the creative pipeline — from script analysis through shot list generation to keyframe rendering and DaVinci Resolve timeline assembly.

| # | Item | Description | Status | Owner |
|---|------|-------------|--------|-------|
| 1 | **Fix DaVinci Resolve MCP transport** | Resolve SSE vs streamable-http mismatch. Get Cowork ↔ Resolve communication working over Cloudflare tunnel. | Blocked (405) | Builder |
| 2 | **End-to-end VEO pipeline test** | Script → shot list → keyframes → Resolve timeline. Verify full chain with real content. | Not Started | Overseer + Builder |
| 3 | **ComfyUI MCP connector** | Stand up ComfyUI on RTX 5090, create MCP bridge for image generation workflows. Integrate as alternative/complement to Flux keyframe path. | Not Started | Builder |
| 4 | **VEO session UI** | Frontend for managing VEO sessions — view shot lists, preview keyframes, trigger Resolve export. | Not Started | Builder |
| 5 | **Resolve nested bin organization** | Implement per-session bins with shot markers, keyframe stills on tracks, organized project structure. | Partial | Builder |
| 6 | **Multi-angle keyframe support** | Generate multiple keyframe variants per shot for creative exploration. | Not Started | Builder |
| 7 | **Semantic search across VEO sessions** | Index VEO session data in ChromaDB for cross-session search and pattern discovery. | Not Started | Builder |
| 8 | **Read-only Resolve metadata import** | Import Resolve project metadata back for learning refinement. One-way read, no write-back (per Golden Rule #9). | Not Started | Builder |

**Exit Criteria:** A complete script-to-timeline pipeline runs end-to-end. ComfyUI generates keyframes alongside Flux. Resolve receives structured creative intent and assembles timelines automatically.

---

### LATER — World Model Module Build-Out (Weeks 9+)

Goal: The system develops a persistent understanding of Ryan's creative world — projects, themes, visual vocabulary, narrative patterns — and uses that understanding to anticipate, suggest, and generate.

| # | Item | Description | Status | Owner |
|---|------|-------------|--------|-------|
| 1 | **World model schema design** | Define data structures for Ryan's creative universe: projects, characters, locations, visual themes, narrative arcs, asset relationships. | Not Started | Overseer + Ryan |
| 2 | **Observation → Learning loop** | System watches classification patterns, VEO sessions, manual corrections, and builds a model of creative preferences. Requires fixing adaptive learning trigger (NOW #5). | Blocked | Builder |
| 3 | **Cross-modal linking** | Connect files, VEO sessions, Resolve timelines, and taxonomy into a unified knowledge graph. A character mentioned in a script links to their reference images, scenes, and taxonomy category. | Not Started | Builder |
| 4 | **Proactive suggestion engine** | Based on world model, suggest: relevant reference files during VEO sessions, similar past shots during Resolve editing, taxonomy categories for new content. | Not Started | Builder |
| 5 | **Creative memory & context** | System remembers what Ryan has worked on, aesthetic choices made, active narrative threads — surfaces relevant context automatically. | Not Started | Overseer + Builder |
| 6 | **Public/private repo split** | Separate public spine (architecture, interfaces, core organizer) from private organs (Ryan's taxonomy rules, creative data, API keys). | Not Started | Ryan + Overseer |
| 7 | **Agent accountability framework** | Formalize anti-drift system: artifact-gated logging, zero-result escalation, decision checkpoints, narrative compression. Bake into agent instructions. | Not Started | Overseer |

**Exit Criteria:** The system has a persistent model of Ryan's creative practice that improves over time. New files, scripts, and sessions are contextualized against existing knowledge. Suggestions are relevant and non-intrusive.

---

## Part 10: Overseer Onboarding Checklist

For the new project overseer (OpenClaw), internalize before approving any work:

- [ ] Read this dossier in full
- [ ] Read `SYSTEM_MANUAL.md` — the golden rules are non-negotiable
- [ ] Read `CLAUDE.md` — the code of conduct for AI agents working in this repo
- [ ] Review `ROADMAP.md` — understand what was planned vs. what was completed
- [ ] Understand the authority hierarchy (Part 2) — Supabase > taxonomy > classification > filesystem
- [ ] Know the golden rules (Part 6) — violations have historically caused cascading failures
- [ ] Check current blockers (Part 5) — don't approve work that depends on broken infrastructure
- [ ] Understand the oversight protocol (Part 8) — your role is review, not implementation
- [ ] Review unmerged Jules branches — automated optimization that needs human oversight
- [ ] Verify VEO pipeline status — 89% complete but needs end-to-end testing
- [ ] Familiarize with the Antigravity pattern — agents logging motion without state change is the primary drift risk
- [ ] Know the agent stats — 82.5% avg completion, watch for the 7.3% that plan without executing

---

## Part 11: Source Index

This dossier was synthesized from:

**Git History:**
- 80 commits analyzed (Jan 22 – Feb 6, 2026)
- 4 contributors: RT Max, The Bear With A Bite, google-labs-jules[bot], copilot-swe-agent[bot]
- Repo: `github.com/thebearwithabite/ai-file-organizer`

**Existing Repo Documentation:**
- `CLAUDE.md` (52KB) — Agent code of conduct and full architecture
- `SYSTEM_MANUAL.md` — Golden rules, workflows, anti-patterns
- `ROADMAP.md` — 12-section sprint plan from Dec 2025
- `README.md`, `COMMANDS.md`, `GEMINI.md`, `agents.md`, `VEO_STUDIO_*.md`

**ChatGPT PM Threads (9 files):**
- `AI-FILE-ORGANIZER_manifest.json` — Project manifest and component inventory
- `AI-file-organizer-project-review-and-architecture-insights` — Architecture deep dive
- `Agent_accountability_review.json` — Agent drift pattern analysis
- `Anti-Drift_Architecture_Review.json` — Structural integrity audit
- `Antigravity_in_Progress_Logs.json` — Agent behavior meta-analysis
- `Read_and_compress_context.json` — Context compression for handoffs
- `System_Manual_Review.json` — Operational constitution review
- `Taxonomy_Sync_Plan.json` — V3 living taxonomy design
- `VEO_prompt_machine_review.json` — VEO Studio vision and Resolve integration

**Claude PM Threads (5 files):**
- `AI-file-organizer-project-review` — Cowork/Antigravity coordination and Taxonomy V4
- `Backend-access-issues-with-startup` — 676-file queue fix, agent drift incident, field mapping bugs
- `Installing-DaVinci-Resolve-MCP-server-on-Windows` — MCP transport setup and blockers
- `Investigating-rogue-database-files-in-Google-Drive` — Path consolidation directive
- `Qwen-censoring-files-and-changing-filenames` — Trust boundary investigation (resolved: iOS localization artifacts)

**Antigravity Agent Logs (1,274 artifacts):**
- 41 agent sessions with implementation plans, task tracking, and resolution logs
- Coverage: path consolidation, VEO integration (10 phases), triage UI, classification persistence, hybrid architecture

---

*This document is the canonical onboarding reference for the AI File Organizer project. It should be versioned in the repository and updated as the roadmap progresses.*
