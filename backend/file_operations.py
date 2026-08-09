"""
FileOperationsService — the SINGLE write path for all file operations.

Phase 3 hard rule: every API endpoint routes through this service.
No endpoint touches shutil, os.rename, or any storage SDK directly.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from core.paths import get_metadata_root, get_ai_organizer_root

logger = logging.getLogger(__name__)


class FileOperationsService:
    """
    Centralized file operations. Every move, copy, delete, and organize
    action goes through here. This is the single source of truth.

    Usage:
        ops = FileOperationsService()
        ops.move_to_organized(source_path, category="invoices")
    """

    def __init__(self, root: Optional[Path] = None):
        self.root = root or get_ai_organizer_root()
        self.metadata_root = get_metadata_root()
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # File movement
    # ------------------------------------------------------------------

    def move_to_organized(
        self,
        source: Path,
        category: str,
        new_filename: Optional[str] = None,
    ) -> Path:
        """
        Move a file into the organized directory structure.
        Returns the destination path.
        """
        source = Path(source).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        # Determine destination
        dest_dir = self.root / category
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_name = new_filename or source.name
        dest = dest_dir / dest_name

        # Handle name collisions
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        shutil.move(str(source), str(dest))
        logger.info(f"Moved: {source} -> {dest}")
        return dest

    def copy_to_staging(self, source: Path) -> Path:
        """Copy a file to the staging area for review."""
        staging = self.metadata_root / "staging"
        staging.mkdir(parents=True, exist_ok=True)

        dest = staging / source.name
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = staging / f"{stem}_{counter}{suffix}"
                counter += 1

        shutil.copy2(str(source), str(dest))
        logger.info(f"Staged: {source} -> {dest}")
        return dest

    def safe_delete(self, path: Path) -> None:
        """Move a file to trash/staging instead of permanent delete."""
        trash = self.metadata_root / "trash"
        trash.mkdir(parents=True, exist_ok=True)

        dest = trash / path.name
        if dest.exists():
            dest.unlink()  # overwrite old trash

        shutil.move(str(path), str(dest))
        logger.info(f"Trashed: {path} -> {dest}")

    # ------------------------------------------------------------------
    # Disk utilities
    # ------------------------------------------------------------------

    def disk_usage(self, path: Optional[Path] = None) -> dict:
        """Get disk usage for a path or the organizer root."""
        target = path or self.root
        usage = shutil.disk_usage(str(target))
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "free_gb": round(usage.free / (1024 ** 3), 1),
            "total_gb": round(usage.total / (1024 ** 3), 1),
            "percent_used": round(usage.used / usage.total * 100, 1),
        }

    def list_staging_files(self) -> list[dict]:
        """List files in the staging area awaiting review."""
        staging = self.metadata_root / "staging"
        if not staging.exists():
            return []

        files = []
        for entry in staging.iterdir():
            if entry.is_file():
                st = entry.stat()
                files.append({
                    "name": entry.name,
                    "path": str(entry),
                    "size_bytes": st.st_size,
                    "modified": st.st_mtime,
                })
        return sorted(files, key=lambda f: f["modified"], reverse=True)

    def list_organized_files(self, category: Optional[str] = None) -> list[dict]:
        """List files in the organized directory."""
        search_dir = self.root / category if category else self.root
        if not search_dir.exists():
            return []

        files = []
        for entry in search_dir.rglob("*"):
            if entry.is_file():
                st = entry.stat()
                rel = entry.relative_to(self.root)
                files.append({
                    "name": entry.name,
                    "path": str(entry),
                    "relative_path": str(rel),
                    "category": rel.parts[0] if len(rel.parts) > 1 else "root",
                    "size_bytes": st.st_size,
                    "modified": st.st_mtime,
                })
        return sorted(files, key=lambda f: f["modified"], reverse=True)


# Singleton instance
_file_ops: Optional[FileOperationsService] = None


def get_file_operations() -> FileOperationsService:
    """Get or create the singleton FileOperationsService."""
    global _file_ops
    if _file_ops is None:
        _file_ops = FileOperationsService()
    return _file_ops
