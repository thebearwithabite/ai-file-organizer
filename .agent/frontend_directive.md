STATE GUARD RAILS — FRONTEND

1. Before you propose any TODO or file changes, you MUST:
   - Run `ls` at repo root.
   - Run `ls` inside any mentioned frontend directories.
   - If a path doesn’t exist, you MUST NOT propose editing it.

2. The ONLY active frontend is:
   - `frontend_v2` (React), built and served on port 8000.

3. You MUST treat the React app as:
   - "Control Center (v2)"
   - The canonical place to add status strips, dashboards, and new UI.

4. You MUST treat any mention of `frontend/` (Vanilla JS) as:
   - Legacy.
   - Historical only.
   - NOT to be re-created unless I explicitly say: 
     "Rebuild the legacy static frontend."

5. If you detect contradictions between a TODO and the filesystem:
   - Generate a **State Contradiction Report**.
   - Propose an updated TODO that matches the actual files.
   - Do NOT execute instructions that target non-existent paths.
