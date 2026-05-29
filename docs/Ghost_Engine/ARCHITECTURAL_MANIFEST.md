# Ghost Engine Architectural Manifest

## System Overview
The Ghost Engine is an autonomous multi-agent pipeline designed for high-fidelity narrative and visual production. It bridges local GPU resources (RTX 5090) with cloud-based management (Google Drive) and AI-driven classification.

## Core Components
- **Narrative Agent:** Generates shot-by-shot manifests for production.
- **Visual Agent:** Orchestrates LTX generation batches on remote nodes.
- **Infrastructure Agent:** Manages proxy connections, sync, and VRAM hygiene.
- **Unified Librarian:** Handles file organization and semantic routing.

## Production Grounding: Interlude 8.1
- **Status:** Active
- **Aesthetic:** New Machine Cinema
  - **Noir Contrast:** High dynamic range, deep blacks.
  - **Phosphor Bloom:** Subtle glowing edges on highlights.
  - **Cinematic Framing:** Dramatic angles, rule of thirds.
  - **Grain Integrity:** Film-like grain, zero digital artifacting.
  - **Character Consistency:** Locked Jonah/Marsh archetypes.

## Active Paths
- **Local Workspace:** `~/Github/ai-file-organizer`
- **Metadata Root:** `~/AI_METADATA_SYSTEM`
- **Gdrive Projects:** `Business Management/Contracts/Quotes/` (Taxonomy: `biz_quotes`)
- **Scout Root:** `~/Github/scout`
- **Visual Host:** `rtx-win` (Direct Windows SSH)

## Current Directives
1. **Stabilize Sync:** Fixed `LocalMetadataStore` attribute error in `BackgroundSyncService`.
2. **Taxonomy Enforcement:** Verified `biz_quotes` routing for financial documents.
3. **Visual Continuity:** Audited Ep 8.1 manifest; all 9 shots generated.

---
*Last Updated: 2026-05-05*
*Truth Level: NOMINAL*
