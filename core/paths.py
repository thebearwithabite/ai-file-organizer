"""
Centralized path resolution for AI File Organizer.
Extracted from gdrive_integration.py — no cloud dependencies.
Metadata root is ALWAYS local (~/.ai-file-organizer/).
"""
import os
from pathlib import Path

# The one true metadata home (per V2 directive)
_METADATA_HOME = Path.home() / ".ai-file-organizer"

# Legacy path from pre-V2 era
_LEGACY_METADATA = Path.home() / "AI_METADATA_SYSTEM"


def get_metadata_root() -> Path:
    """
    Return the local metadata root directory.
    Creates it if it doesn't exist.
    Migrates from legacy location if needed.
    """
    # If legacy exists and new doesn't, move it
    if _LEGACY_METADATA.exists() and not _METADATA_HOME.exists():
        import shutil
        shutil.move(str(_LEGACY_METADATA), str(_METADATA_HOME))

    _METADATA_HOME.mkdir(parents=True, exist_ok=True)
    return _METADATA_HOME


def get_ai_organizer_root() -> Path:
    """
    Get the PRIMARY root directory for organized files.
    Post-V2: always local. Cloud tiering is handled by StorageProvider,
    not by mounting a sync directory.
    """
    # 1. Environment variable override
    env_root = os.environ.get("AI_ORGANIZER_BASE")
    if env_root:
        path = Path(env_root).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 2. Config file (if present)
    config_path = _METADATA_HOME / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f)
            root = cfg.get("storage", {}).get("root")
            if root:
                path = Path(root).expanduser().resolve()
                path.mkdir(parents=True, exist_ok=True)
                return path
        except Exception:
            pass

    # 3. Default: ~/Documents/AI-Organized
    default = Path.home() / "Documents" / "AI-Organized"
    default.mkdir(parents=True, exist_ok=True)
    return default


def ensure_safe_local_path(path: Path) -> Path:
    """
    Validate a path is strictly local — not cloud-synced.
    Raises RuntimeError if unsafe.
    """
    resolved = str(path.resolve())
    unsafe = [
        "GoogleDrive", "Google Drive", "CloudStorage",
        "/Volumes/GoogleDrive", "My Drive",
        "OneDrive", "Dropbox", "iCloud", "Box Sync",
    ]
    for indicator in unsafe:
        if indicator in resolved:
            raise RuntimeError(
                f"Unsafe path detected: {resolved}\n"
                f"SQLite/metadata must live on local disk, not a synced directory.\n"
                f"Use get_metadata_root() which always returns ~/.ai-file-organizer/"
            )
    return path
