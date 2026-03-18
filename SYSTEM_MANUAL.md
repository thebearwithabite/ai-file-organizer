# AI File Organizer - System Manual

This document is the canonical source of truth for the system's architecture, rules, and cross-machine coordination.

## 🏛️ Core Architecture: The "Hybrid Hub"

The system operates across a mobile Mac and a high-performance PC (5090 RTX) using a "Local-First, Cloud-Synced" model.

### 1. Unified Metadata Engine
- **Precedence**: **Supabase** state is the absolute Source of Truth. It always overrides SQLite caches, JSON sidecars, and filesystem inference.
- **Sidecars**: JSON sidecars (`.veo.json`, `.meta.json`) are **Non-authoritative Exports/Backups** only.
- **ChromaDB**: All vector databases MUST live under `~/Documents/AI_METADATA_SYSTEM/chroma_db/`. They must NEVER be initialized relative to `base_dir` or the CWD.

### 2. Intelligence Distribution
- **Heavy Workers (PC/5090)**: Local LLMs (Ollama/Qwen 2.5), Vision-Language analysis (**Qwen 2.5-VL**), Video analysis (Flux/VEO), High-fidelity Whisper.
- **Coordination**: Machines communicate via **Tailscale** and **Supabase** real-time events.
- **Review Queue**: Persisted in Supabase and mirrored locally for offline resolution.
- **Future Fusion**: Planned merge with `VEO-Prompt-Machine-V3` for automated cinematic metadata generation.

---

## 📜 The Golden Rules

> [!IMPORTANT]
> These rules are non-negotiable and must be upheld by all agents and developers.

1. **NEVER** write database files (SQLite, ChromaDB) into Google Drive or any cloud-synced directory. Use `get_metadata_root()`.
2. **NEVER** allow live references to the legacy `04_METADATA_SYSTEM` path.
3. **FAIL-FAST** on storage: If a safe local database path cannot be established, the system must crash immediately.
4. **TRASH, DON'T DELETE**: Destructive operations (deletions) must use `safe_file_recycling.py` to move files to the system trash.
5. **ALWAYS LOG**: Every file move or rename must be logged to the `EasyRollbackSystem`.
6. **CONFIDENCE FIRST**: Automatic organization only triggers at **0.90+ confidence**. Everything else goes to the Review Queue.

---

## 📂 Data Taxonomy & Storage

### Metadata Root (`~/Documents/AI_METADATA_SYSTEM`)
| Subdir | Purpose |
| :--- | :--- |
| `databases/` | Unified metadata, learning logs, and rollback state. |
| `chroma_db/` | Vector embeddings for semantic search. |
| `vision_cache/` | Cached Gemini/Local Vision analysis. |
| `config/` | Machine-specific identities and API credentials. |

---

## 🚀 Workflows

### 1. VEO Prompt Machine
- Video files are analyzed for lighting, camera, character, and mood.
- Results are saved to the `veo_prompts` table and exported as `.veo.json`.
- The 5090 machine specializes in batch-processing these prompts.

### 2. Interactive Batch Processing
- Groups files by Duplicates, Similar Content, or File Type.
- Uses **ChromaDB** with `sentence-transformers` for global similarity search.
- Falls back to Jaccard (keyword) similarity if vector models are offline.

### 3. Emergency Overflow Handling
- Triggered when `Downloads` or `Desktop` exceed 200 files.
- High-confidence files are auto-organized.
- Remainder is cleared to `99_TEMP_PROCESSING/Emergency_Overflow_{Timestamp}`.
- **Rule**: Files routed through Emergency Overflow **do not trigger learning** unless explicitly confirmed by the user during review.

### 4. VEO Studio Workflow
- **Session Identity**: Every session uses a persistent `veo_session_id` (Supabase + Local mirror).
- **Keyframe Authority**: Generated keyframes are primary managed assets. Exported images/JSON are **non-authoritative**.
- **Rendering Fallback**: Flux (Local PC) is preferred; Gemini is the secondary fallback only if Flux is unavailable.
- **Indexing**: VEO assets reach the global index only after a full **session commit**.
- **Resolve Authority**: Resolve is a **write-only target**. VEO never mutates existing timelines unless explicitly instructed. Resolve state is NOT synced back to Supabase.

---

## 🚫 Appendix: Known Anti-Patterns
To prevent architectural drift, agents must NEVER:
1.  **Write Databases relative to `base_dir`**: Always use `get_metadata_root()`.
2.  **Treat Sidecars as Authoritative**: Sidecars are for portability; the DB is the Truth.
3.  **Silent Fallback on Unsafe Paths**: If a metadata path is invalid or on CloudStorage, the system must FAIL-FAST with an error.
4.  **Leak PII**: Metadata sent to Supabase or Gemini must be scrubbed of sensitive local usernames or project IDs.
