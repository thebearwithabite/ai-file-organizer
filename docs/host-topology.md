# Host Topology — Prompt Machine (v1.2)

**Applies to:** the Prompt Machine pipeline (`../PROMPT-MACHINE-DIRECTIVE.md`, v1.2, amended 2026-08-09).
**Audited:** 2026-10-01 (Phase 0). The table below mirrors the directive verbatim — if the topology moves, update both files in the same commit.

**Host topology (v1.2 — changed):**

| Component | Host | Path |
| --- | --- | --- |
| Orchestrator (`ai-file-organizer`) | WSL2 / Ubuntu | `~/Projects/ai-file-organizer` |
| Renderer (WanGP) | **native Windows** | `C:\Users\thebe\AppData\Roaming\wan2gp-desktop\Wan2GP\Wan2GP` — installed + updated by [wan2gp-desktop launcher](https://github.com/GKartist75/wan2gp-desktop) |
| Model/output stores | Windows | `D:\Wan2GP\{ckpts,loras,outputs}` — mapped into the launcher install |
| ComfyUI | as-is | `~/projects/ComfyUI` |

> **`D:\Wan2GP` is the retired Sparge fork, not the renderer.** It still holds `ckpts/`, `loras/`, and `outputs/`, which the live install maps to — everything else in it is dead (see `../PROMPT-MACHINE-DIRECTIVE.md`, Appendix B).
>
> Note `D:\Wan2GP` and `/mnt/d/wan2gp` are the **same directory** (Windows is case-insensitive). Any cleanup script that removes the lowercase path destroys the working install.

## Operational notes

- **Orchestrator** — WSL2/Ubuntu. Repo code, tests, and services run here (`.venv`, Python 3.12). The orchestrator never edits WanGP source; it reaches the renderer only over MCP (`--mcp --mcp-transport streamable-http`).
- **Renderer** — native Windows, launcher-managed. The launcher overwrites source on every update; `git status --porcelain --untracked-files=no` in the live install must stay empty. venv: `env_uv`. Launch command, MCP protocol details, LTX-2.3 recipes, and VRAM etiquette live in [`../.claude/skills/wangp-operator/SKILL.md`](../.claude/skills/wangp-operator/SKILL.md).
- **Model/output stores** — `D:\Wan2GP\{ckpts,loras,outputs}` stay on Windows and are mapped into the live install via `wgp_config.json`. Never delete or relocate them from the WSL side.
- **ComfyUI** — `~/projects/ComfyUI`, reached via Gateway REST (`:3000`) only.

## Path-safety rule (enforced)

Windows paths (`D:\...`) and WSL paths (`/mnt/d/...`) name the same files. Before removing **anything**, a cleanup script must call the guard:

```python
from core.path_guard import assert_deletable

assert_deletable(path)  # raises ProtectedPathError for protected roots
```

Shell callers: `python -m core.path_guard "$path" && rm -rf -- "$path"`.

Protected by default: `D:\Wan2GP` (== `/mnt/d/wan2gp`; model/output stores + retired fork) and `C:\Users\thebe\AppData\Roaming\wan2gp-desktop` (launcher-managed install). The guard is case-insensitive and slash-agnostic by design (fail closed). Implementation: `../core/path_guard.py`. Tests: `../tests/test_path_guard.py`.

## Deprecation record — Docker/WSL WanGP build

The Docker/WSL WanGP build was abandoned 2026-08-09 (the three lessons are recorded in `../PROMPT-MACHINE-DIRECTIVE.md` §Appendix B). Phase 0 audit result, 2026-10-01:

- No `Dockerfile*`, `docker-compose*`, `Makefile*`, or WSL-clone build script is present in the repo (tracked-file scan: zero matches).
- No CI job references a forked WanGP clone or local source patches — `.github/workflows/` contains only `eslint.yml` (frontend lint).
- `system_storage_cleanup.py` mentions Docker only as macOS Docker Desktop housekeeping; unrelated to WanGP.
- Remaining mentions of the retired build are historical records (the directive itself, `DISTRO-DIRECTIVE.md`), not instructions.

**Rule:** if a build file (Dockerfile, compose file, Makefile target, CI job) referencing a Docker/WSL WanGP build ever appears, mark it deprecated with a TODO pointing at this document. Do not resurrect the containerized renderer.
